#!/usr/bin/env python
"""
Intersite application enables policies to be applied across multiple ACI fabrics
For documentation, refer to http://acitoolkit.readthedocs.org/en/latest/intersite.html
"""
from acitoolkit.acitoolkit import (Tenant, OutsideL3, OutsideEPG, OutsideNetwork,
                                   IPEndpoint, Session, Contract, ContractInterface,
                                   Taboo)
import json
import re
import threading
import logging
from logging.handlers import RotatingFileHandler
import cmd
import sys
import socket
import subprocess
from requests.exceptions import ConnectionError, Timeout
import time
import os

# Imports from standalone mode
import argparse

# TODO documentation
# TODO docstrings

# Maximum number of endpoints to handle in a single burst
MAX_ENDPOINTS = 500

endpoint_db_lock = threading.Lock()


class IntersiteTag(object):
    """
    This class deals with the tagInst instances stored in the APIC
    Used to re-derive the application state after booting
    """
    def __init__(self, tenant_name, app_name, epg_name, remote_site):
        """
        Class instance  initialization

        :param tenant_name: String containing the Tenant name. Used to scope the EPG.
        :param app_name: String containing the Application Profile name. Used to scope the EPG.
        :param epg_name: String containing the EPG name.
        :param remote_site:  String containing the remote site name
        """
        self._tenant_name = tenant_name
        self._app_name = app_name
        self._epg_name = epg_name
        self._remote_site = remote_site

    @staticmethod
    def is_intersite_tag(tag):
        """
        Indicates whether the tag is an intersite tag

        :param tag: String containing the tag from the APIC
        :returns: True or False.  True if the tag is considered a
                  intersite tag. False otherwise.
        """
        return re.match(r'isite:.*:.*:.*:.*', tag)

    @classmethod
    def fromstring(cls, tag):
        """
        Extract the intersite tag from a string

        :param tag: String containing the intersite tag
        :returns: New instance of IntersiteTag
        """
        if not cls.is_intersite_tag(tag):
            assert cls.is_intersite_tag(tag)
            return None
        tag_data = tag.split(':')
        tenant_name = tag_data[1]
        app_name = tag_data[2]
        epg_name = tag_data[3]
        remote_site_name = tag_data[4]
        new_tag = cls(tenant_name, app_name, epg_name, remote_site_name)
        return new_tag

    def __str__(self):
        """
        Convert the intersite tag into a string

        :returns: String containing the intersite tag
        """
        return 'isite:' + self._tenant_name + ':' + self._app_name + ':' + self._epg_name + ':' + self._remote_site

    def get_tenant_name(self):
        """
        Get the tenant name

        :returns: string containing the tenant name
        """
        return self._tenant_name

    def get_app_name(self):
        """
        Get the application profile name

        :returns: string containing the application profile name
        """
        return self._app_name

    def get_epg_name(self):
        """
        Get the EPG name

        :returns: string containing the EPG name
        """
        return self._epg_name

    def get_remote_site_name(self):
        """
        Get the remote site name

        :returns: string containing the remote site name
        """
        return self._remote_site


class EndpointHandler(object):
    """
    Class responsible for tracking the Endpoints during processing.
    Used to queue bursts of Endpoint events before sending to the APIC
    """
    def __init__(self, my_monitor):
        self.db = {}  # Indexed by remote site
        self.addresses = {}
        self.mac_tracker = {}
        self.endpoint_add_events = 0
        self.endpoint_del_events = 0
        self._monitor = my_monitor

    def _remove_queued_endpoint(self, remote_site, l3out_policy, endpoint):
        if remote_site not in self.db:
            return
        # Find the remote site's list of tenant JSONs
        db_entry = self.db[remote_site]
        # Find the l3outs we should be looking at based on the policy
        for tenant_json in db_entry:
            if tenant_json['fvTenant']['attributes']['name'] != l3out_policy.tenant:
                continue
            for l3out in tenant_json['fvTenant']['children']:
                if 'l3extOut' not in l3out:
                    continue
                if l3out['l3extOut']['attributes']['name'] != l3out_policy.name:
                    continue
                for l3instp in l3out['l3extOut']['children']:
                    if 'l3extInstP' not in l3instp:
                        continue
                    remove_list = []
                    for ep in l3instp['l3extInstP']['children']:
                        if 'l3extSubnet' not in ep:
                            continue
                        if ep['l3extSubnet']['attributes']['name'] == '':
                            logging.warning('Endpoint JSON has no name %s', ep)
                        if endpoint.ip == '':
                            logging.warning('Endpoint has no IP %s %s', endpoint.name, endpoint.ip)
                        if ep['l3extSubnet']['attributes']['name'] == endpoint.ip:
                            remove_list.append(ep)
                    for ep in remove_list:
                        l3instp['l3extInstP']['children'].remove(ep)

    def _merge_tenant_json(self, remote_site, new_json):
        """
        Merge the JSON for the endpoint with the rest of the endpoints
        already processed

        :param remote_site: String containing the remote site to push the endpoint
        :param new_json: JSON dictionary containing the JSON for the endpoint
        """
        # Add the remote site if the first endpoint for that site
        if remote_site not in self.db:
            self.db[remote_site] = [new_json]
            return

        # Look for the tenant JSON
        db_json = self.db[remote_site]
        tenant_found = False
        for tenant_json in db_json:
            if tenant_json['fvTenant']['attributes']['name'] == new_json['fvTenant']['attributes']['name']:
                tenant_found = True
                break

        # Add the tenant if the first endpoint for this tenant
        if not tenant_found:
            self.db[remote_site].append(new_json)
            return

        new_l3out = new_json['fvTenant']['children'][0]
        assert 'l3extOut' in new_l3out

        # Find the l3out in the existing JSON
        l3out_found = False
        for l3out in tenant_json['fvTenant']['children']:
            if 'l3extOut' not in l3out:
                continue
            if l3out['l3extOut']['attributes']['name'] == new_l3out['l3extOut']['attributes']['name']:
                l3out_found = True
                break

        # Add the l3out JSON if the first endpoint for this tenant's l3out
        if not l3out_found:
            tenant_json['fvTenant']['children'].append(new_l3out)
            return

        new_outside_epg = new_l3out['l3extOut']['children'][0]
        assert 'l3extInstP' in new_outside_epg

        # Find the Outside EPG in the existing JSON
        epg_found = False
        for outside_epg in l3out['l3extOut']['children']:
            if 'l3extInstP' not in outside_epg:
                continue
            if outside_epg['l3extInstP']['attributes']['name'] == new_outside_epg['l3extInstP']['attributes']['name']:
                epg_found = True
                break

        if not epg_found:
            l3out['l3extOut']['children'].append(new_outside_epg)
            return

        # Add the endpoint configuration with the existing JSON
        new_endpoint = new_outside_epg['l3extInstP']['children'][0]
        assert 'l3extSubnet' in new_endpoint
        if new_endpoint not in outside_epg['l3extInstP']['children']:
            outside_epg['l3extInstP']['children'].append(new_endpoint)

    def add_endpoint(self, endpoint, local_site):
        """
        Add an endpoint to the temporary database to be pushed to the remote sites

        :param endpoint: Instance of IPEndpoint
        :param local_site: Instance of LocalSite
        """
        try:
            epg = endpoint.get_parent()
            app = epg.get_parent()
            tenant = app.get_parent()
        except AttributeError as e:
            return
        logging.info('endpoint: %s epg: %s app: %s tenant: %s', endpoint.name, epg.name, app.name, tenant.name)

        # Ignore events without IP addresses
        if endpoint.ip == '0.0.0.0':
            return

        # Ignore MAC moves i.e. Same IP address appears on different MAC address.
        # This is the case in situations such as loadbalancer failover.
        if (tenant.name, app.name, epg.name, endpoint.name) in self.mac_tracker:
            expected_mac = self.mac_tracker[(tenant.name, app.name, epg.name, endpoint.name)]
            if endpoint.mac != expected_mac and endpoint.is_deleted():
                # Ignore this event since it is the old MAC being deleted on a MAC move
                return
        if endpoint.is_deleted():
            if (tenant.name, app.name, epg.name, endpoint.name) in self.mac_tracker:
                del self.mac_tracker[(tenant.name, app.name, epg.name, endpoint.name)]
        else:
            self.mac_tracker[(tenant.name, app.name, epg.name, endpoint.name)] = endpoint.mac

        # Track the IP to (Tenant, App, EPG)
        # This is in case the IPs are moving from 1 EPG to another EPG then we want to
        # send the currently queued endpoints before handling this endpoint to avoid
        # a subnet already present error
        if endpoint.name in self.addresses:
            if self.addresses[endpoint.name] != (tenant.name, app.name, epg.name):
                self.push_to_remote_sites(self._monitor._my_collector)
        else:
            self.addresses[endpoint.name] = (tenant.name, app.name, epg.name)

        # Get the policy for the EPG
        policy = local_site.get_policy_for_epg(tenant.name, app.name, epg.name)
        if policy is None:
            logging.info('Ignoring endpoint as there is no policy defined for its EPG (epg: %s app: %s tenant: %s)',
                         epg.name, app.name, tenant.name)
            return

        logging.info('Need to process endpoint %s', endpoint.name)
        # Track the number of endpoint events
        if endpoint.is_deleted():
            self.endpoint_del_events += 1
        else:
            self.endpoint_add_events += 1

        # Process the endpoint policy
        for remote_site_policy in policy.get_site_policies():
            for l3out_policy in remote_site_policy.get_interfaces():
                # Remove existing JSON for the endpoint if any already queued since this
                # update will override that
                self._remove_queued_endpoint(remote_site_policy.name, l3out_policy, endpoint)

                # Create the JSON
                tag = IntersiteTag(tenant.name, app.name, epg.name, local_site.name)
                remote_tenant = Tenant(l3out_policy.tenant)
                remote_l3out = OutsideL3(l3out_policy.name, remote_tenant)
                remote_epg = OutsideEPG(policy.remote_epg, remote_l3out)
                if ':' in endpoint.name:
                    remote_ep_ip = endpoint.name + '/128'
                else:
                    remote_ep_ip = endpoint.name + '/32'
                remote_ep = OutsideNetwork(endpoint.name, remote_epg, address=remote_ep_ip)
                if endpoint.is_deleted():
                    remote_ep.mark_as_deleted()
                tenant_json = remote_tenant.get_json()

                # Add to the database
                self._merge_tenant_json(remote_site_policy.name, tenant_json)

    def check_and_remove_duplicate(self, session, tenant_json, response):
        """
        Check for duplicate entry error response message
        If present, delete the offending subnet from the APIC
        """
        logging.debug('')
        if 'imdata' not in response or len(response['imdata']) == 0:
            return False
        response = response['imdata'][0]
        if 'error' not in response or 'attributes' not in response['error']:
            return False
        response = response['error']['attributes']
        if 'text' not in response or 'Invalid Configuration - External Subnet:' not in response['text']:
            return False
        response = response['text']
        if ' already defined in L3 Outside: ' not in response and ' already present at : ' not in response:
            return False

        tenant_name = tenant_json['fvTenant']['attributes']['name']

        # Find all of the OutsideL3s, OutsideEPGs, and the OutsideNetworks defined in the JSON being pushed
        pushed_db = {}
        for child in tenant_json['fvTenant']['children']:
            if 'l3extOut' in child:
                if 'status' in child['l3extOut']['attributes'] and child['l3extOut']['attributes']['status'] == 'deleted':
                    continue
                l3out_name = child['l3extOut']['attributes']['name']
                if l3out_name not in pushed_db:
                    pushed_db[l3out_name] = {}
                for l3out_child in child['l3extOut']['children']:
                    if 'l3extInstP' in l3out_child:
                        if 'status' in l3out_child['l3extInstP']['attributes'] and l3out_child['l3extInstP']['attributes']['status'] == 'deleted':
                            continue
                        l3epg_name = l3out_child['l3extInstP']['attributes']['name']
                        if l3epg_name not in pushed_db[l3out_name]:
                            pushed_db[l3out_name][l3epg_name] = []
                        for epg_child in l3out_child['l3extInstP']['children']:
                            if 'l3extSubnet' in epg_child:
                                if 'status' in epg_child['l3extSubnet']['attributes'] and epg_child['l3extSubnet']['attributes']['status'] == 'deleted':
                                    continue
                                network_name = epg_child['l3extSubnet']['attributes']['ip']
                                if network_name not in pushed_db[l3out_name][l3epg_name]:
                                    pushed_db[l3out_name][l3epg_name].append(network_name)

        # Find all of the OutsideL3s, OutsideEPGs, and the OutsideNetworks defined in the remote APIC
        remote_db = {}
        for l3out_name in pushed_db:
            # Find the InstP that has the duplicate entry
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?rsp-subtree=full&rsp-subtree-class=l3extSubnet'
                         '&rsp-subtree-include=no-scoped' % (tenant_name, l3out_name))
            resp = session.get(query_url)
            if resp.ok and 'totalCount' in resp.text:
                if l3out_name not in remote_db:
                    remote_db[l3out_name] = {}
                if resp.json()['totalCount'] == '0':
                    continue
                for subnet in resp.json()['imdata']:
                    dn = subnet['l3extSubnet']['attributes']['dn']
                    outside_epg_name = dn.partition('/instP-')[2].partition('/')[0]
                    if outside_epg_name not in remote_db[l3out_name]:
                        remote_db[l3out_name][outside_epg_name] = []
                    subnet_name = dn.partition('/extsubnet-[')[-1].partition(']')[0]
                    if subnet_name not in remote_db[l3out_name][outside_epg_name]:
                        remote_db[l3out_name][outside_epg_name].append(subnet_name)

        # Compare the 2 DBs for duplicates and generate the JSON to delete them
        found_duplicates = False
        tenant = Tenant(tenant_name)
        for pushed_l3out in pushed_db:
            if pushed_l3out not in remote_db:
                continue
            l3out = None
            for pushed_l3epg in pushed_db[pushed_l3out]:
                l3epg = None
                for subnet in pushed_db[pushed_l3out][pushed_l3epg]:
                    for remote_epg in remote_db[pushed_l3out]:
                        if remote_epg == pushed_l3epg:
                            continue
                        if subnet in remote_db[pushed_l3out][remote_epg]:
                            # Found duplicate
                            found_duplicates = True
                            if l3out is None:
                                l3out = OutsideL3(pushed_l3out, tenant)
                            if l3epg is None:
                                l3epg = OutsideEPG(remote_epg, l3out)
                            outside_network = OutsideNetwork(subnet.partition('/')[0], l3epg, address=subnet)
                            outside_network.mark_as_deleted()

        # Push the completed JSON to the remote site
        if not found_duplicates:
            logging.warning('Could not find any duplicates.')
            return False
        resp = tenant.push_to_apic(session)
        if resp.ok:
            logging.warning('Deleted duplicate entries: %s', tenant.get_json())
        else:
            logging.error('Could not delete duplicate entries: %s %s', resp, resp.text)
            return False
        return found_duplicates

    def push_to_remote_sites(self, collector):
        """
        Push the endpoints to the remote sites
        """
        logging.debug('')
        for remote_site in self.db:
            remote_site_obj = collector.get_site(remote_site)
            assert remote_site_obj is not None
            remote_session = remote_site_obj.session
            for tenant_json in self.db[remote_site]:
                keep_trying = True
                while keep_trying:
                    try:
                        resp = remote_session.push_to_apic(Tenant.get_url(), tenant_json)
                    except Timeout:
                        logging.error('Timeout error when attempting configuration push')
                        return
                    keep_trying = False
                    if not resp.ok:
                        logging.warning('Could not push to remote site: %s %s', resp, resp.text)
                        if resp.status_code == 400:
                            keep_trying = self.check_and_remove_duplicate(remote_session,
                                                                          tenant_json,
                                                                          resp.json())
        self.db = {}
        self.addresses = {}


class MultisiteMonitor(threading.Thread):
    """
    Monitor thread responsible for subscribing for local Endpoints and EPG notifications.
    """
    def __init__(self, session, local_site, my_collector):
        threading.Thread.__init__(self)
        self._session = session
        self._local_site = local_site
        self._exit = False
        self._my_collector = my_collector
        self._endpoints = EndpointHandler(self)

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def verify_policy(self, export_policy):
        for site in export_policy.get_site_policies():
            site_obj = self._my_collector.get_site(site.name)
            if site_obj is None:
                logging.error('Could not find remote site %s', site.name)
                continue
            for l3out in site.get_interfaces():
                if l3out.noclean:
                    continue

                itag = IntersiteTag(export_policy.tenant, export_policy.app, export_policy.epg,
                                    self._local_site.name)

                # Get the l3extInstP with the tag
                query_url = ('/api/mo/uni/tn-%s/out-%s/instP-%s.json?query-target=children&'
                             'rsp-subtree=children' % (l3out.tenant, l3out.name, export_policy.remote_epg))
                resp = site_obj.session.get(query_url)
                if not resp.ok:
                    logging.warning('Could not get remote site entries %s %s', resp, resp.text)
                    return
                if resp.json()['totalCount'] == '0':
                    continue

                # Check that each entry matches the current policy
                for child in resp.json()['imdata']:
                    dirty = False
                    dirty_children = []
                    if 'fvRsProv' in child:
                        if export_policy.provides(site.name, l3out.name, l3out.tenant,
                                                  child['fvRsProv']['attributes']['tnVzBrCPName']):
                            continue
                        dirty = True
                        dirty_children.append({'fvRsProv': {'attributes': {'tnVzBrCPName': child['fvRsProv']['attributes']['tnVzBrCPName'],
                                                                           'status': 'deleted'}}})
                    elif 'fvRsCons' in child:
                        if export_policy.consumes(site.name, l3out.name, l3out.tenant,
                                                  child['fvRsCons']['attributes']['tnVzBrCPName']):
                            continue
                        dirty = True
                        dirty_children.append({'fvRsCons': {'attributes': {'tnVzBrCPName': child['fvRsCons']['attributes']['tnVzBrCPName'],
                                                                           'status': 'deleted'}}})
                    elif 'fvRsProtBy' in child:
                        if export_policy.protected_by(site.name, l3out.name, l3out.tenant,
                                                      child['fvRsProtBy']['attributes']['tnVzTabooName']):
                            continue
                        dirty = True
                        dirty_children.append({'fvRsProtBy': {'attributes': {'tnVzTabooName': child['fvRsProtBy']['attributes']['tnVzTabooName'],
                                                                             'status': 'deleted'}}})
                    elif 'fvRsConsIf' in child:
                        if export_policy.consumes_cif(site.name, l3out.name, l3out.tenant,
                                                      child['fvRsConsIf']['attributes']['tnVzCPIfName']):
                            continue
                        dirty = True
                        dirty_children.append({'fvRsConsIf': {'attributes': {'tnVzCPIfName': child['fvRsConsIf']['attributes']['tnVzCPIfName'],
                                                                             'status': 'deleted'}}})
                    if dirty:
                        logging.debug('cleaning dirty entry')
                        url = '/api/mo/uni/tn-%s/out-%s.json' % (l3out.tenant, l3out.name)
                        data = {'l3extInstP': {'attributes': {'name': export_policy.remote_epg},
                                               'children': dirty_children}}
                        resp = site_obj.session.push_to_apic(url, data)
                        if not resp.ok:
                            logging.warning('Could not push modified entry to remote site %s %s', resp, resp.text)

    def handle_existing_endpoints(self, policy):
        logging.info('for tenant: %s app_name: %s epg_name: %s',
                     policy.tenant, policy.app, policy.epg)
        try:
            self.verify_policy(policy)
            endpoints = IPEndpoint.get_all_by_epg(self._session,
                                                  policy.tenant, policy.app, policy.epg)
        except ConnectionError:
            logging.error('Could not connect to APIC to get all endpoints for the EPG')
            return
        num_eps = MAX_ENDPOINTS
        for endpoint in endpoints:
            self._endpoints.add_endpoint(endpoint, self._local_site)
            num_eps -= 1
            if num_eps == 0:
                self._endpoints.push_to_remote_sites(self._my_collector)
                num_eps = MAX_ENDPOINTS

    def handle_endpoint_event(self):
        num_eps = MAX_ENDPOINTS
        while IPEndpoint.has_events(self._session) and num_eps:
            ep = IPEndpoint.get_event(self._session)
            logging.info('for Endpoint: %s', ep.name)
            self._endpoints.add_endpoint(ep, self._local_site)
            num_eps -= 1
        self._endpoints.push_to_remote_sites(self._my_collector)

    def run(self):
        # Subscribe to endpoints
        IPEndpoint.subscribe(self._session)

        while not self._exit:
            if IPEndpoint.has_events(self._session):
                with endpoint_db_lock:
                    try:
                        self.handle_endpoint_event()
                    except ConnectionError:
                        logging.error('Could not handle endpoint event due to ConnectionError')
            else:
                time.sleep(0.05)


class SiteLoginCredentials(object):
    def __init__(self, ip_address, user_name, password, use_https):
        self.ip_address = ip_address
        self.user_name = user_name
        self.password = password
        self.use_https = use_https


class Site(object):
    def __init__(self, name, credentials, local=False):
        self.name = name
        self.local = local
        self.credentials = credentials
        self.session = None

    def get_credentials(self):
        return self.credentials

    def login(self):
        url = self.credentials.ip_address
        if self.credentials.use_https:
            url = 'https://' + url
        else:
            url = 'http://' + url
        self.session = Session(url, self.credentials.user_name, self.credentials.password, relogin_forever=True)
        resp = self.session.login()
        return resp

    def __eq__(self, other):
        if self.name == other.name:
            return True
        else:
            return False

    def __ne__(self, other):
        return not self == other

    def shutdown(self):
        pass

    def start(self):
        resp = self.login()
        if not resp.ok:
            logging.warning('Could not login to site: %s due to: %s', self.name, resp.text)
            print('%% Could not login to APIC on Site', self.name)
        else:
            logging.info('%% Logged into Site %s', self.name)
        return resp

    def remove_old_policies(self, local_site):
        pass


class IntersiteConfiguration(object):
    def __init__(self, config):
        self.site_policies = []
        self.export_policies = []

        if 'config' not in config:
            raise ValueError('Expected "config" in configuration')

        for item in config['config']:
            if 'site' in item:
                site_policy = SitePolicy(item)
                if site_policy is not None:
                    self.site_policies.append(site_policy)
            elif 'export' in item:
                export_policy = ExportPolicy(item)
                if export_policy is not None:
                    self.export_policies.append(export_policy)
        self._validate_unique_epgs()

    def _validate_unique_epgs(self):
        for policy in self.export_policies:
            count = 0
            for other_policy in self.export_policies:
                if other_policy.has_same_epg(policy):
                    count += 1
            if count > 1:
                raise ValueError('Duplicate EPG export policy found for tenant:%s app:%s epg:%s' % (policy.tenant, policy.app, policy.epg))

    def get_config(self):
        policies = []
        for policy in self.site_policies:
            policies.append(policy._policy)
        for policy in self.export_policies:
            policies.append(policy._policy)
        return {'config': policies}


class ConfigObject(object):
    def __init__(self, policy):
        self._policy = policy
        self.validate()

    def _validate_string(self, item):
        if sys.version_info < (3, 0, 0):
            if isinstance(item, unicode):
                return
        if not isinstance(item, str):
            raise ValueError(self.__class__.__name__ + ': Expected string')

    def _validate_non_empty_string(self, item):
        if sys.version_info < (3, 0, 0):
            if isinstance(item, unicode):
                if len(item) < 1 or len(item) > 64:
                    raise ValueError(self.__class__.__name__ + ': Expected string of correct size %s' % item)
                return
        if not isinstance(item, str):
            raise ValueError(self.__class__.__name__ + ': Expected string')
        elif len(item) < 1 or len(item) > 64:
            raise ValueError(self.__class__.__name__ + ': Expected string of correct size %s' % item)

    def _validate_ip_address(self, item):
        try:
            if sys.version_info < (3, 0, 0):
                if isinstance(item, unicode):
                    item = str(item)
            socket.inet_aton(item)
        except socket.error:
            raise ValueError(self.__class__.__name__ + ': Expected IP address')

    def _validate_boolean_string(self, item):
        if item not in ['True', 'False']:
            raise ValueError(self.__class__.__name__ + ': Expected "True" or "False"')

    def _validate_list(self, item):
        if not isinstance(item, list):
            raise ValueError(self.__class__.__name__ + ': Expected list')

    def validate(self):
        raise NotImplementedError


class SitePolicy(ConfigObject):
    @property
    def username(self):
        return self._policy['site']['username']

    @username.setter
    def username(self, username):
        self._policy['site']['username'] = username

    @property
    def name(self):
        return self._policy['site']['name']

    @name.setter
    def name(self, name):
        self._policy['site']['name'] = name

    @property
    def ip_address(self):
        return self._policy['site']['ip_address']

    @ip_address.setter
    def ip_address(self, ip_address):
        self._policy['site']['ip_address'] = ip_address

    @property
    def password(self):
        return self._policy['site']['password']

    @password.setter
    def password(self, password):
        self._policy['site']['password'] = password

    @property
    def local(self):
        return self._policy['site']['local']

    @local.setter
    def local(self, local):
        self._policy['site']['local'] = local

    @property
    def use_https(self):
        return self._policy['site']['use_https']

    @use_https.setter
    def use_https(self, use_https):
        self._policy['site']['use_https'] = use_https

    def __eq__(self, other):
        if self.username != other.username or self.ip_address != other.ip_address:
            return False
        if self.password != other.password or self.local != other.local:
            return False
        if self.use_https != other.use_https:
            return False
        else:
            return True

    def __ne__(self, other):
        return not self == other

    def validate(self):
        if 'site' not in self._policy:
            raise ValueError(self.__class__.__name__, 'Expecting "site" in configuration')
        policy = self._policy['site']
        for item in policy:
            keyword_validators = {'username': '_validate_non_empty_string',
                                  'name': '_validate_non_empty_string',
                                  'ip_address': '_validate_ip_address',
                                  'password': '_validate_string',
                                  'local': '_validate_boolean_string',
                                  'use_https': '_validate_boolean_string'}
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])


class ProvidedContractPolicy(ConfigObject):
    @property
    def contract_name(self):
        return self._policy['contract_name']

    def validate(self):
        if 'contract_name' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "contract_name" in contract policy')
        self._validate_non_empty_string(self._policy['contract_name'])


class ConsumedContractPolicy(ProvidedContractPolicy):
    pass


class ProtectedByPolicy(ConfigObject):
    @property
    def taboo_name(self):
        return self._policy['taboo_name']

    def validate(self):
        if 'taboo_name' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "taboo_name" in protected by policy')
        self._validate_non_empty_string(self._policy['taboo_name'])


class ConsumedInterfacePolicy(ConfigObject):
    @property
    def consumes_interface(self):
        return self._policy['cif_name']

    def validate(self):
        if 'cif_name' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "cif_name" in consumed interface policy')
        self._validate_non_empty_string(self._policy['cif_name'])


class L3OutPolicy(ConfigObject):
    @property
    def name(self):
        return self._policy['l3out']['name']

    @property
    def tenant(self):
        return self._policy['l3out']['tenant']

    @property
    def noclean(self):
        return 'noclean' in self._policy['l3out'] and self._policy['l3out']['noclean'] == "True"

    def validate(self):
        if 'l3out' not in self._policy:
            raise ValueError('Expecting "l3out" in interface policy')
        policy = self._policy['l3out']
        for item in policy:
            keyword_validators = {'name': '_validate_non_empty_string',
                                  'tenant': '_validate_non_empty_string',
                                  'provides': '_validate_list',
                                  'consumes': '_validate_list',
                                  'protected_by': '_validate_list',
                                  'consumes_interface': '_validate_list',
                                  'noclean': '_validate_boolean_string',
                                  }
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])
            self.get_provided_contract_policies()
            self.get_consumed_contract_policies()
            self.get_protected_by_policies()
            self.get_consumes_interface_policies()

    def _get_policies(self, cls, keyword):
        policies = []
        if keyword not in self._policy['l3out']:
            return policies
        for policy in self._policy['l3out'][keyword]:
            policies.append(cls(policy))
        return policies

    def get_provided_contract_policies(self):
        return self._get_policies(ProvidedContractPolicy, 'provides')

    def get_consumed_contract_policies(self):
        return self._get_policies(ConsumedContractPolicy, 'consumes')

    def get_protected_by_policies(self):
        return self._get_policies(ProtectedByPolicy, 'protected_by')

    def get_consumes_interface_policies(self):
        return self._get_policies(ConsumedInterfacePolicy, 'consumes_interface')


class RemoteSitePolicy(ConfigObject):
    @property
    def name(self):
        return self._policy['site']['name']

    def validate(self):
        if 'site' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "site" in remote site policy')
        policy = self._policy['site']
        for item in policy:
            keyword_validators = {'name': '_validate_non_empty_string',
                                  'interfaces': '_validate_list'}
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])
            self.get_interfaces()

    def get_interfaces(self):
        interfaces = []
        try:
            for interface in self._policy['site']['interfaces']:
                interfaces.append(L3OutPolicy(interface))
        except KeyError:
            logging.warning('No interfaces in JSON for Site %s', self._policy['site']['name'])
        return interfaces

    def has_interface_policy(self, interface_policy_name):
        for interface_policy in self.get_interfaces():
            if interface_policy.name == interface_policy_name:
                return True
        return False

    def remove_interface_policy(self, interface_policy_name):
        for interface_policy in self._policy['site']['interfaces']:
            if interface_policy['l3out']['name'] == interface_policy_name:
                self._policy['site']['interfaces'].remove(interface_policy)


class ExportPolicy(ConfigObject):
    @property
    def tenant(self):
        return self._policy['export']['tenant']

    @property
    def app(self):
        return self._policy['export']['app']

    @property
    def epg(self):
        return self._policy['export']['epg']

    @property
    def remote_epg(self):
        return self._policy['export']['remote_epg']

    def validate(self):
        if 'export' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "export" in configuration')
        policy = self._policy['export']
        remote_site_names = []
        try:
            for remote_site in policy['remote_sites']:
                remote_site_name = remote_site['site']['name']
                remote_site_names.append(remote_site_name)
        except KeyError:
            raise ValueError(self.__class__.__name__ + ': Expecting named remote sites in export policy.')
        try:
            for remote_site_name in remote_site_names:
                tag = IntersiteTag(policy['tenant'], policy['app'], policy['epg'], remote_site_name)
                if len(str(tag)) > 64:
                    error_string = ('Tenant, App, EPG name, Remote site name combined '
                                    'must not exceed %s characters' % str(64 - len(str(IntersiteTag('','','','')))))
                    raise ValueError(self.__class__.__name__ + ': ' + error_string)
        except KeyError:
            raise ValueError(self.__class__.__name__ + ': Expecting tenant, app, and epg in export policy.')
        for item in policy:
            keyword_validators = {'tenant': '_validate_string',
                                  'app': '_validate_string',
                                  'epg': '_validate_string',
                                  'remote_epg': '_validate_string',
                                  'remote_sites': '_validate_list'}
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])
            self.get_site_policies()

    def has_same_epg(self, policy):
        assert isinstance(policy, ExportPolicy)
        if self.tenant != policy.tenant or self.app != policy.app or self.epg != policy.epg:
            return False
        return True

    def has_same_epg_and_remote_epg(self, policy):
        assert isinstance(policy, ExportPolicy)
        if self.tenant != policy.tenant or self.app != policy.app or self.epg != policy.epg or self.remote_epg != policy.remote_epg:
            return False
        return True

    def has_remote_epg(self, remote_site_name, l3out_name, l3instp_name):
        # Check that the Remote EPG is that being used by the policy
        if l3instp_name != self.remote_epg:
            return False
        # Check that the Remote Site is being used by the policy
        site_found = False
        for site_policy in self.get_site_policies():
            if site_policy.name == remote_site_name:
                site_found = True
                break
        if not site_found:
            return False
        # Check that the L3Out is being used by the policy
        for interface in site_policy.get_interfaces():
            if interface.name == l3out_name:
                return True
        return False

    def get_site_policies(self):
        sites = []
        for site in self._policy['export']['remote_sites']:
            sites.append(RemoteSitePolicy(site))
        return sites

    def _get_l3out_policy(self, site_name, l3out_name, l3out_tenant):
        for site in self.get_site_policies():
            if site.name == site_name:
                for l3out in site.get_interfaces():
                    if l3out.name == l3out_name and l3out.tenant == l3out_tenant:
                        return l3out

    def provides(self, site_name, l3out_name, l3out_tenant, contract_name):
        l3out = self._get_l3out_policy(site_name, l3out_name, l3out_tenant)
        if l3out is None:
            return False
        for contract in l3out.get_provided_contract_policies():
            if contract.contract_name == contract_name:
                return True
        return False

    def consumes(self, site_name, l3out_name, l3out_tenant, contract_name):
        l3out = self._get_l3out_policy(site_name, l3out_name, l3out_tenant)
        if l3out is None:
            return False
        for contract in l3out.get_consumed_contract_policies():
            if contract.contract_name == contract_name:
                return True
        return False

    def protected_by(self, site_name, l3out_name, l3out_tenant, taboo_name):
        l3out = self._get_l3out_policy(site_name, l3out_name, l3out_tenant)
        if l3out is None:
            return False
        for taboo in l3out.get_protected_by_policies():
            if taboo.taboo_name == taboo_name:
                return True
        return False

    def consumes_cif(self, site_name, l3out_name, l3out_tenant, consumes_interface):
        l3out = self._get_l3out_policy(site_name, l3out_name, l3out_tenant)
        if l3out is None:
            return False
        for contract_if in l3out.get_consumes_interface_policies():
            if contract_if.consumes_interface == consumes_interface:
                return True
        return False

    def has_site_policy(self, site_policy_name):
        for site_policy in self.get_site_policies():
            if site_policy.name == site_policy_name:
                return True
        return False

    def get_site_policy(self, site_policy_name):
        for site_policy in self.get_site_policies():
            if site_policy.name == site_policy_name:
                return site_policy
        return None

    def remove_l3outs(self, new_policy):
        for new_site_policy in new_policy.get_site_policies():
            if not self.has_site_policy(new_site_policy.name):
                continue
            my_site_policy = self.get_site_policy(new_site_policy.name)
            for new_interface_policy in new_site_policy.get_interfaces():
                if my_site_policy.has_interface_policy(new_interface_policy.name):
                    my_site_policy.remove_interface_policy(new_interface_policy.name)


class LocalSite(Site):
    def __init__(self, name, credentials, parent):
        super(LocalSite, self).__init__(name, credentials, local=True)
        self.my_collector = parent
        self.monitor = None
        self.policy_db = []
        self.policy_queue = []
        self.policy_tenant_queue = {}

    def start(self):
        resp = super(LocalSite, self).start()
        self.monitor = MultisiteMonitor(self.session, self, self.my_collector)
        self.monitor.daemon = True
        self.monitor.start()

    def remove_stale_entries(self, policy):
        logging.info('')
        # Get all of the local APIC entries
        try:
            endpoints = IPEndpoint.get_all_by_epg(self.session,
                                                  policy.tenant, policy.app, policy.epg)
        except ConnectionError:
            logging.error('Could not remove stale entries in site %s', self.name)
            return
        local_endpoints = []
        for ep in endpoints:
            local_endpoints.append(ep.name)
        # For each remote site, get all of the L3out entries using this policy
        for site_policy in policy.get_site_policies():
            site = self.my_collector.get_site(site_policy.name)
            if site is None:
                logging.error('Could not find remote site %s', site_policy.name)
                continue
            for l3out in site_policy.get_interfaces():
                query = ('/api/mo/uni/tn-%s/out-%s/instP-%s.json?query-target=children&'
                         'target-subtree-class=l3extSubnet&'
                         'rsp-subtree=children' % (l3out.tenant, l3out.name,
                                                   policy.remote_epg))
                resp = site.session.get(query)
                if not resp.ok:
                    logging.warning('Could not get remote site entries to check for stale entries')
                else:
                    children = []
                    for item in resp.json()['imdata']:
                        try:
                            ip_addr = item['l3extSubnet']['attributes']['ip'].rpartition('-')[-1]
                        except KeyError:
                            continue
                        if '/32' in ip_addr:
                            search_ip_addr = ip_addr.rpartition('/32')[0]
                        else:
                            search_ip_addr = ip_addr
                        if search_ip_addr not in local_endpoints:
                            # Delete this L3out entry
                            data = {'l3extSubnet': {'attributes': {'ip': ip_addr,
                                                                   'status': 'deleted'}}}
                            children.append(data)
                    if len(children):
                        url = '/api/mo/uni/tn-%s/out-%s.json' % (l3out.tenant, l3out.name)
                        l3out_data = {'l3extInstP': {'attributes': {'name': policy.remote_epg}, 'children': children}}
                        resp = site.session.push_to_apic(url, l3out_data)
                        if not resp.ok:
                            logging.warning('Could not delete stale entry %s', ip_addr)
                        else:
                            logging.info('Found stale entry for %s on l3out %s in remote site %s. Deleting...',
                                         ip_addr, l3out.name, site.name)

    def push_policy_to_queue(self, policy):
        logging.info('')
        tag = IntersiteTag(policy.tenant, policy.app, policy.epg, self.name)
        for site_policy in policy.get_site_policies():
            if site_policy.name not in self.policy_tenant_queue:
                self.policy_tenant_queue[site_policy.name] = []
            for l3out_policy in site_policy.get_interfaces():
                queued_tenant_exists = False
                for queued_tenant in self.policy_tenant_queue[site_policy.name]:
                    if queued_tenant.name == l3out_policy.tenant:
                        remote_tenant = queued_tenant
                        queued_tenant_exists = True
                        break
                if not queued_tenant_exists:
                    remote_tenant = Tenant(l3out_policy.tenant)
                    self.policy_tenant_queue[site_policy.name].append(remote_tenant)
                l3out_already_exists = False
                for existing_l3out in remote_tenant.get_children(only_class=OutsideL3):
                    if existing_l3out.name == l3out_policy.name:
                        remote_l3out = existing_l3out
                        l3out_already_exists = True
                        break
                if not l3out_already_exists:
                    remote_l3out = OutsideL3(l3out_policy.name, remote_tenant)
                remote_epg = OutsideEPG(policy.remote_epg, remote_l3out)
                for provided_contract in l3out_policy.get_provided_contract_policies():
                    contract = Contract(provided_contract.contract_name)
                    remote_epg.provide(contract)
                for consumed_contract in l3out_policy.get_consumed_contract_policies():
                    contract = Contract(consumed_contract.contract_name)
                    remote_epg.consume(contract)
                for protecting_taboo in l3out_policy.get_protected_by_policies():
                    taboo = Taboo(protecting_taboo.taboo_name)
                    remote_epg.protect(taboo)
                for consumes_interface in l3out_policy.get_consumes_interface_policies():
                    cif = ContractInterface(consumes_interface.consumes_interface)
                    remote_epg.consume_cif(cif)
                remote_epg.add_tag(str(tag))
                self.policy_queue.append(policy)

    def add_policy(self, policy):
        logging.info('')
        old_policy = self.get_policy_for_epg(policy.tenant,
                                             policy.app,
                                             policy.epg)
        if old_policy is not None:
            self.policy_db.remove(old_policy)
        if policy not in self.policy_db:
            self.policy_db.append(policy)
            try:
                self.push_policy_to_queue(policy)
            except ConnectionError:
                logging.error('Could not push policy for %s %s %s', policy.tenant, policy.app, policy.epg)
                return

    def process_policy_queue(self):
        # Send the processed tenant JSONs
        for site_name in self.policy_tenant_queue:
            site = self.my_collector.get_site(site_name)
            if site is None:
                logging.error('Could not find remote site %s', site_name)
                continue
            for remote_tenant in self.policy_tenant_queue[site_name]:
                resp = remote_tenant.push_to_apic(site.session)
                if not resp.ok:
                    logging.warning('Could not push policy to remote site: %s', resp.text)
        # Clear the queue
        self.policy_tenant_queue = {}
        # Handle the cleanup for each policy
        with endpoint_db_lock:
            for policy in self.policy_queue:
                self.remove_stale_entries(policy)
                self.monitor.handle_existing_endpoints(policy)
            self.monitor._endpoints.push_to_remote_sites(self.monitor._my_collector)
        # Clear the queue
        self.policy_queue = []

    def remove_policy(self, policy):
        logging.info('')
        if policy in self.policy_db:
            self.policy_db.remove(policy)
        for site_policy in policy.get_site_policies():
            if site_policy.name not in self.policy_tenant_queue:
                self.policy_tenant_queue[site_policy.name] = []
            for l3out_policy in site_policy.get_interfaces():
                queued_tenant_exists = False
                for queued_tenant in self.policy_tenant_queue[site_policy.name]:
                    if queued_tenant.name == l3out_policy.tenant:
                        remote_tenant = queued_tenant
                        queued_tenant_exists = True
                        break
                if not queued_tenant_exists:
                    remote_tenant = Tenant(l3out_policy.tenant)
                    self.policy_tenant_queue[site_policy.name].append(remote_tenant)
                l3out_already_exists = False
                for existing_l3out in remote_tenant.get_children(only_class=OutsideL3):
                    if existing_l3out.name == l3out_policy.name:
                        remote_l3out = existing_l3out
                        l3out_already_exists = True
                        break
                if not l3out_already_exists:
                    remote_l3out = OutsideL3(l3out_policy.name, remote_tenant)
                remote_epg = OutsideEPG(policy.remote_epg, remote_l3out)
                remote_epg.mark_as_deleted()

    def get_policy_for_epg(self, tenant_name, app_name, epg_name):
        """
        Get the policy for the specific EPG
        :param tenant_name: String containing the tenant name
        :param app_name: String containing the application profile name
        :param epg_name: String containing the EPG name
        :return:
        """
        for policy in self.policy_db:
            if policy.tenant == tenant_name and policy.app == app_name and policy.epg == epg_name:
                return policy
        return None


class RemoteSite(Site):
    """
    Remote site
    """
    def __init__(self, name, credentials):
        super(RemoteSite, self).__init__(name, credentials, local=False)

    def remove_old_policies(self, local_site):
        logging.info('remote_site: %s', self.name)
        query_url = '/api/node/class/tagInst.json?query-target-filter=wcard(tagInst.name,"%s")' % local_site.name
        resp = self.session.get(query_url)
        if not resp.ok:
            logging.error('Could not communicate with remote site to check for old policies')
            return
        tags = resp.json()['imdata']
        for tag in tags:
            if not IntersiteTag.is_intersite_tag(tag['tagInst']['attributes']['name']):
                continue
            itag = IntersiteTag.fromstring(tag['tagInst']['attributes']['name'])
            export_policy = local_site.get_policy_for_epg(itag.get_tenant_name(), itag.get_app_name(), itag.get_epg_name())
            l3out_name = tag['tagInst']['attributes']['dn'].split('/out-')[1].split('/')[0]
            l3instp_name = tag['tagInst']['attributes']['dn'].split('/instP-')[1].split('/')[0]
            if export_policy is None or not export_policy.has_remote_epg(self.name, l3out_name, l3instp_name):
                dn = tag['tagInst']['attributes']['dn'].split('/instP-')[0]
                url = '/api/mo/' + dn + '.json'
                data = {'l3extInstP': {'attributes': {'name': l3instp_name,
                                                      'status': 'deleted'}}}
                resp = self.session.push_to_apic(url, data)
                if not resp.ok:
                    logging.error('Could not communicate with remote site to remove old policy')
                    return
                logging.info('Deleted old policy for %s', str(itag))


class MultisiteCollector(object):
    """
    Collector: Holds all of the LocalSite and RemoteSite objects.
    Normally, one collector exists per tool. Multiple collectors can be used in test
    scripts to emulate multiple datacenters.
    """
    def __init__(self):
        self.sites = []
        self.config = None
        self.config_filename = None

    def initialize_local_site(self):
        """
        Initialize the local site
        """
        local_site = self.get_local_site()
        if local_site is None:
            print '%% No local site configured'
            return

        # Export all of the configured exported contracts
        for export_policy in self.config.export_policies:
            local_site.add_policy(export_policy)
        for attempt in range(0, 10):
            try:
                local_site.process_policy_queue()
            except ConnectionError:
                logging.error('Could not process policy queue. Preparing to retry in 10 seconds.')
                time.sleep(10)
                continue
            else:
                break

    def get_sites(self, local_only=False, remote_only=False):
        """
        Get the LocalSite and/or RemoteSite instances

        :param local_only: True or False. True if only the local sites are desired.
        :param remote_only: True or False. True if only the remote sites are desired.
        :return: List of LocalSite and/or RemoteSite instances
        """
        assert not (local_only and remote_only)
        if local_only:
            locals = []
            for site in self.sites:
                if site.local:
                    locals.append(site)
            return locals
        if remote_only:
            remotes = []
            for site in self.sites:
                if not site.local:
                    remotes.append(site)
            return remotes
        else:
            return self.sites

    def get_local_site(self):
        """
        Get the LocalSite

        :return: LocalSite instance or None
        """
        local_sites = self.get_sites(local_only=True)
        if len(local_sites):
            return local_sites[0]
        else:
            return None

    def get_site(self, name):
        """
        Get the LocalSite or RemoteSite instance specified by name

        :param name: String containing the desired site name
        """
        for site in self.sites:
            if site.name == name:
                return site

    def get_num_sites(self):
        """
        Get the number of sites configured in this Collector

        :returns: Integer containing the number of sites
        """
        return len(self.sites)

    def add_site(self, name, credentials, local):
        """
        Add a site
        :param name: String containing the name of the site
        :param credentials: SiteLoginCredentials instance
        :param local: Boolean indicating whether the site is local or not
        :return: None
        """
        logging.info('name:%s local:%s', name, local)
        self.delete_site(name)
        if local:
            site = LocalSite(name, credentials, self)
        else:
            site = RemoteSite(name, credentials)
        self.sites.append(site)
        site.start()
        site.session.register_login_callback(self.login_callback)

    def add_site_from_config(self, site):
        """
        Add site from config
        :param site: SiteLoginCredentials instance
        :return: None
        """
        if site.use_https == 'True':
            use_https = True
        else:
            use_https = False
        creds = SiteLoginCredentials(site.ip_address,
                                     site.username,
                                     site.password,
                                     use_https)
        if site.local == 'True':
            is_local = True
        else:
            is_local = False
        self.add_site(site.name, creds, is_local)

    def delete_site(self, name):
        """
        Delete the site from the Collector

        :param name: String containing the name of the site to be deleted
        """
        logging.info('name:%s', name)
        for site in self.sites:
            if name == site.name:
                site.shutdown()
                self.sites.remove(site)

    def print_sites(self):
        """
        Print the site information
        """
        print 'Number of sites:', len(self.sites)
        for site in self.sites:
            print site.name, site.credentials.ip_address

    def _reload_sites(self, old_config, new_config):
        """
        Reload the site configurations
        :param old_config: Instance of IntersiteConfiguration
        :param new_config: Instance of IntersiteConfiguration
        :return: True or False. True if added local site
        """
        added_local_site = False
        # Check the old sites for deleted sites or changed configs
        logging.info('Loading site configurations...')
        for old_site in old_config.site_policies:
            found_site = False
            for new_site in new_config.site_policies:
                if new_site == old_site:
                    if new_site != old_site:
                        logging.info('Site config for site %s has changed.', new_site.name)
                        # Something changed, remove the old site and add the new site
                        self.delete_site(new_site.name)
                        self.add_site_from_config(new_site)
                        if new_site.local == 'True':
                            added_local_site = True
                    else:
                        logging.info('Site config for site %s is the same so no change.', new_site.name)
                        found_site = True
                        break
            if not found_site:
                # Old site is not in new sites
                logging.info('Could not find site config for site %s.  Deleting site...', old_site.name)
                self.delete_site(old_site.name)

        # Loop back through and check for new sites that didn't exist previously
        for new_site in new_config.site_policies:
            site_found = False
            for old_site in old_config.site_policies:
                if new_site.name == old_site.name:
                    site_found = True
                    break
            if not site_found:
                logging.info('Could not find site config for site %s.  Adding site...', new_site.name)
                self.add_site_from_config(new_site)
                if new_site.local == 'True':
                    added_local_site = True
        return added_local_site

    def reload_config(self):
        """
        Reload the configuration
        :return: True or False. True if successful.
        """
        logging.info('')
        try:
            with open(self.config_filename) as config_file:
                new_config = json.load(config_file)
        except IOError:
            print '%% Could not load configuration file'
            return False
        except ValueError as e:
            print 'Could not load improperly formatted configuration file'
            print e
            return False
        if 'config' not in new_config:
            print '%% Invalid configuration file'
            return False
        old_config = self.config
        logging.debug('Old configuration: %s', self.config.get_config())
        try:
            new_config = IntersiteConfiguration(new_config)
        except ValueError as e:
            print 'Could not load improperly formatted configuration file'
            print e
            return False
        # Handle any changes in site configuration
        added_local_site = self._reload_sites(old_config, new_config)
        self.config = new_config
        logging.debug('New configuration: %s', self.config.get_config())
        if added_local_site:
            logging.info('New local site added')
            self.initialize_local_site()

        local_site = self.get_local_site()
        if local_site is None:
            print '%% No local site configured'
            return False

        # Handle any policies that have been deleted
        for old_policy in old_config.export_policies:
            policy_found = False
            for new_policy in new_config.export_policies:
                if old_policy.has_same_epg_and_remote_epg(new_policy):
                    policy_found = True
                    break
            if policy_found:
                # Handle any old L3Outs that may have been removed
                old_policy.remove_l3outs(new_policy)
            local_site.remove_policy(old_policy)
        local_site.process_policy_queue()

        # Handle any export policies for new EPGs
        for new_policy in new_config.export_policies:
            local_site.add_policy(new_policy)
        local_site.process_policy_queue()
        return True

    def save_config(self, config):
        """
        Save the config
        :param config: Dictionary containing the configuration
        :return: String indicating 'OK' if successful, otherwise a string containing the error message
        """
        logging.info('')
        try:
            new_config = IntersiteConfiguration(config)
        except ValueError as e:
            error = 'Could not load improperly formatted configuration ' + str(e)
            logging.warning(error)
            return error

        with open(self.config_filename, 'w') as config_file:
            config_file.write(json.dumps(config, indent=4, separators=(',', ':')))
        return 'OK'

    def login_callback(self, session):
        """
        Callback function for site re-login
        :param session: Session instance assumed to be logged into the APIC
        :return: None
        """
        logging.info('')
        my_policies = []
        local_site = self.get_local_site()
        for policy in local_site.policy_db:
            my_policies.append(policy)
        for policy in my_policies:
            local_site.add_policy(policy)
        local_site.process_policy_queue()
        remote_sites = self.get_sites(remote_only=True)
        for remote_site in remote_sites:
            remote_site.remove_old_policies(local_site)


def initialize_tool(config):
    """
    Initialize the tool
    :param config: Dictionary containing the configuration
    :return: Instance of MultisiteCollector
    """
    try:
        IntersiteConfiguration(config)
    except ValueError as e:
        print 'Could not load improperly formatted configuration file'
        print e
        raise
        sys.exit(0)
    collector = MultisiteCollector()
    collector.config = IntersiteConfiguration(config)
    logging.debug('New configuration: %s', collector.config.get_config())

    for site_policy in collector.config.site_policies:
        collector.add_site_from_config(site_policy)

    collector.initialize_local_site()

    # For deleted export policies, try and clean up old dangling OutsideEPGs
    # It may not be possible if the Remote Site Policy was also deleted

    local_site = collector.get_local_site()
    if local_site is None:
        logging.error('No local site configured')
        print '%% No local site configured.'
        return collector
    for remote_site_policy in collector.config.site_policies:
        remote_site = collector.get_site(remote_site_policy.name)
        try:
            remote_site.remove_old_policies(local_site)
        except ConnectionError:
            logging.error('Could not remove old policies from remote site')
    return collector


class CommandLine(cmd.Cmd):
    """
    Command line parser
    """
    prompt = 'intersite> '
    intro = 'Cisco ACI Intersite tool (type help for commands)'

    SHOW_CMDS = ['configfile', 'debug', 'config', 'log', 'sites', 'stats']
    DEBUG_CMDS = ['verbose', 'warnings', 'critical']
    CLEAR_CMDS = ['stats']

    def __init__(self, collector):
        self.collector = collector
        cmd.Cmd.__init__(self)

    def do_quit(self, line):
        '''
        quit
        Quit the Intersite tool.
        '''
        sys.exit(0)

    def do_show(self, keyword):
        '''
        show
        Various commands that show the intersite tool details.

        Available subcommands:
        show debug - show the current debug level setting
        show configfile - show the config file name setting
        show config - show the current JSON configuration
        show log - show the contents of the intersite.log file
        show sites - show the status of the communication with the various APICs
        show stats - show some basic event statistics
        '''
        if keyword == 'debug':
            current_level = logging.getLevelName(logging.getLogger().getEffectiveLevel())
            if current_level == 'DEBUG':
                current_level = 'VERBOSE'
            elif current_level == 'WARNING':
                current_level = 'WARNINGS'
            print 'Debug level currently set to:', current_level
        elif keyword == 'configfile':
            print 'Configuration file is set to:', self.collector.config_filename
        elif keyword == 'config':
            print json.dumps(self.collector.config.get_config(), indent=4, separators=(',', ':'))
        elif keyword == 'log':
            p = subprocess.Popen(['less', 'intersite.%s.log' % str(os.getpid())], stdin=subprocess.PIPE)
            p.communicate()
        elif keyword == 'sites':
            sites = self.collector.get_sites()
            for site in sites:
                if site.session.logged_in():
                    state = 'Connected'
                else:
                    state = 'Not connected'
                print site.name, ':', state
        elif keyword == 'stats':
            handler = self.collector.get_local_site().monitor._endpoints
            print 'Endpoint addition events:', handler.endpoint_add_events
            print 'Endpoint deletion events:', handler.endpoint_del_events

    def emptyline(self):
        """
        Action for empty line input
        """
        pass

    def complete_show(self, text, line, begidx, endidx):
        """
        Complete the show command
        :param text:
        :param line:
        :param begidx:
        :param endidx:
        :return:
        """
        if not text:
            completions = self.SHOW_CMDS[:]
        else:
            completions = [f
                           for f in self.SHOW_CMDS
                           if f.startswith(text)
                           ]
        return completions

    def do_reloadconfig(self, line):
        '''
        reloadconfig
        Reload the configuration file and apply the configuration.
        '''
        if self.collector.reload_config():
            print 'Configuration reload complete'

    def do_configfile(self, filename):
        '''
        configfile <filename>
        Set the configuration file name.
        '''
        if len(filename):
            self.collector.config_filename = filename
            print 'Configuration file is set to:', self.collector.config_filename
        else:
            print 'No config filename given.'

    def do_clear(self, keyword):
        '''
        clear stats
        Set the statistics back to 0.
        '''
        if keyword == 'stats':
            handler = self.collector.get_local_site().monitor._endpoints
            handler.endpoint_add_events = 0
            handler.endpoint_del_events = 0

    def complete_clear(self, text, line, begidx, endidx):
        """
        Complete the clear command
        :param text:
        :param line:
        :param begidx:
        :param endidx:
        :return:
        """
        if not text:
            completions = self.CLEAR_CMDS[:]
        else:
            completions = [f
                           for f in self.CLEAR_CMDS
                           if f.startswith(text)
                           ]
        return completions

    def do_debug(self, keyword):
        '''
        debug [critical | warnings | verbose]
        Set the level for debug messages.
        '''
        if keyword == 'warnings':
            level = logging.WARNING
        elif keyword == 'verbose':
            level = logging.DEBUG
        elif keyword == 'critical':
            level = logging.CRITICAL
        else:
            print 'Unknown debug level. Valid values are:', self.DEBUG_CMDS[:]
            return
        logging.getLogger().setLevel(level)
        level_name = logging.getLevelName(logging.getLogger().getEffectiveLevel())
        if level_name == 'DEBUG':
            level_name = 'verbose'
        elif level_name == 'WARNING':
            level_name = 'warnings'
        elif level_name == 'CRITICAL':
            level_name = 'critical'
        print 'Debug level currently set to:', level_name

    def complete_debug(self, text, line, begidx, endidx):
        """
        complete the debug command
        :param text:
        :param line:
        :param begidx:
        :param endidx:
        :return:
        """
        if not text:
            completions = self.DEBUG_CMDS[:]
        else:
            completions = [f
                           for f in self.DEBUG_CMDS
                           if f.startswith(text)
                           ]
        return completions

    def do_reapply(self, keyword):
        '''
        reapply <tenant_name>/<app_profile_name>/<epg_name>
        Reapply the policy for EPG belonging to the specified tenant, app profile, epg
        '''
        logging.info('')
        if len(keyword.split('/')) != 3:
            print 'Usage: reapply <tenant_name>/<app_profile_name>/<epg_name>'
            return
        (tenant_name, app_name, epg_name) = keyword.split('/')
        local_site = self.collector.get_local_site()
        if local_site is None:
            print 'No local site configured.'
            return
        policy = local_site.get_policy_for_epg(tenant_name, app_name, epg_name)
        if policy is None:
            print 'Could not find policy for specified <tenant_name>/<app_profile_name>/<epg_name>'
            return
        local_site.monitor.handle_existing_endpoints(policy)

    def do_verify(self, keyword):
        '''
        verify <tenant_name>/<app_profile_name>/<epg_name>

        Verify that the policy for EPG belonging to the specified tenant, app profile, epg has been applied.
        Report on the number of local endpoints and endpoints pushed to the remote site as well as which specific
        endpoints are missing.
        '''
        logging.info('')
        if len(keyword.split('/')) != 3:
            print 'Usage: verify <tenant_name>/<app_profile_name>/<epg_name>'
            return
        (tenant_name, app_name, epg_name) = keyword.split('/')
        local_site = self.collector.get_local_site()
        if local_site is None:
            print 'No local site configured.'
            return
        policy = local_site.get_policy_for_epg(tenant_name, app_name, epg_name)
        if policy is None:
            print 'Could not find policy for specified <tenant_name>/<app_profile_name>/<epg_name>'
            return
        try:
            local_endpoints = IPEndpoint.get_all_by_epg(local_site.session, tenant_name, app_name, epg_name)
        except ConnectionError:
            print 'Could not collect endpoints from the APIC'
        print 'Local Endpoints:', len(local_endpoints)
        local_ips = []
        for ep in local_endpoints:
            local_ips.append(ep.name)
        for remote_site_policy in policy.get_site_policies():
            for interface_policy in remote_site_policy.get_interfaces():
                remote_site = self.collector.get_site(remote_site_policy.name)
                logging.info('getting remote endpoints')
                query_url = ('/api/mo/uni/tn-%s/out-%s/instP-%s.json?'
                             'query-target=subtree&'
                             'target-subtree-class=l3extSubnet' % (interface_policy.tenant,
                                                                   interface_policy.name,
                                                                   policy.remote_epg))
                resp = remote_site.session.get(query_url)
                if resp.ok:
                    print('Remote Endpoints for Site %s Interface %s : %s' %
                          (remote_site.name, interface_policy.name, str(len(resp.json()))))
                else:
                    print('Could not get remote endpoints for Site',
                          remote_site.name, 'Interface', interface_policy.name)
                    continue
                remote_ips = []
                if 'imdata' not in resp.json():
                    continue
                for ep in resp.json()['imdata']:
                    remote_ip = ep['l3extSubnet']['attributes']['ip']
                    if '/32' in remote_ip:
                        remote_ip = remote_ip.partition('/32')[0]
                    remote_ips.append(remote_ip)
                for ep in local_ips:
                    if ep not in remote_ips:
                        print ep, 'is missing from site', remote_site.name
                        logging.warning('%s is missing from site %s for tenant: %s app: %s epg: %s',
                                        ep, remote_site.name, tenant_name, app_name, epg_name)
        logging.info('complete')


def get_arg_parser():
    """
    Get the parser with the necessary arguments

    :return: Instance of argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description='ACI Multisite Tool')
    parser.add_argument('--config', default=None, help='Configuration file')
    parser.add_argument('--maxlogfiles', type=int, default=10, help='Maximum number of log files (default is 10)')
    parser.add_argument('--generateconfig', action='store_true', default=False,
                        help='Generate an empty example configuration file')
    parser.add_argument('--debug', nargs='?',
                        choices=['verbose', 'warnings', 'critical'],
                        const='critical',
                        help='Enable debug messages.')
    return parser


def main():
    """
    Main execution routine

    :return: None
    """
    execute_tool(get_arg_parser().parse_args())


def execute_tool(args, test_mode=False):
    """
    Main Intersite application execution

    :param args: command line arguments
    :param test_mode: True or False. True indicates that the command line parser should not be run.
                      This is used by test routines and when invoked by the REST API
    :return: None if test_mode is False. An instance of MultisiteCollector if test_mode is True.
    """
    # Set up the logging infrastructure
    if args.debug is not None:
        if args.debug == 'verbose':
            level = logging.DEBUG
        elif args.debug == 'warnings':
            level = logging.WARNING
        else:
            level = logging.CRITICAL
    else:
        level = logging.CRITICAL
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    log_file = 'intersite.%s.log' % str(os.getpid())
    my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024,
                                     backupCount=args.maxlogfiles, encoding=None, delay=0)
    my_handler.setLevel(level)
    my_handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(my_handler)
    logging.getLogger().setLevel(level)

    logging.info('Starting the tool....')
    # Handle generating sample configuration
    if args.generateconfig:
        config = {
            'config': [
                {
                    'site': {
                        'name': '',
                        'ip_address': '',
                        'username': '',
                        'password': '',
                        'use_https': '',
                        'local': ''
                    }
                },
                {
                    "export": {
                        "tenant": "",
                        "app": "",
                        "epg": "",
                        "remote_epg": "",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "",
                                                "tenant": "",
                                                "provides": [{"contract_name": ""}],
                                                "consumes": [{"contract_name": ""}],
                                                "protected_by": [{"taboo_name": ""}],
                                                "consumes_interface": [{"cif_name": ""}]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        }

        json_data = json.dumps(config, indent=4, separators=(',', ': '))
        config_file = open('sample_config.json', 'w')
        print 'Sample configuration file written to sample_config.json'
        print "Replicate the site JSON for each site."
        print "    Valid values for use_https and local are 'True' and 'False'"
        print "    One site must have local set to 'True'"
        print 'Replicate the export JSON for each exported contract.'
        config_file.write(json_data)
        config_file.close()
        return

    if args.config is None:
        print '%% No configuration file given.'
        return

    try:
        with open(args.config) as config_file:
            config = json.load(config_file)
    except IOError:
        print '%% Unable to open configuration file', args.config
        return
    except ValueError:
        print '%% File could not be decoded as JSON.'
        return
    if 'config' not in config:
        print '%% Invalid configuration file'
        return

    collector = initialize_tool(config)
    collector.config_filename = args.config

    # Just wait, add any CLI here
    if test_mode:
        return collector
    CommandLine(collector).cmdloop()
    while True:
        pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
