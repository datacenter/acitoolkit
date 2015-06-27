from acitoolkit.acitoolkit import *
import json
import re
import threading

# Imports from standalone mode
import argparse

# TODO documentation
# TODO docstrings

# Maximum number of endpoints to handle in a single burst
MAX_ENDPOINTS = 1000


def strip_illegal_characters(name):
    """
    Strip characters that the APIC deems are illegal

    :param name: String to remove the illegal characters
    :return: String with the illegal characters removed
    """
    chars_all_good = True
    for character in name:
        if character.isalnum() or character in ('_', '.', ':', '-'):
            continue
        chars_all_good = False
        name = name.replace(character, '')
    if chars_all_good:
        return name
    return strip_illegal_characters(name)


class MultisiteTag(object):
    """
    This class deals with the tagInst instances stored in the APIC
    Used to re-derive the application state after booting
    """
    def __init__(self, contract_name, export_state, remote_site):
        """
        Class instance  initialization

        :param contract_name: String containing the contract name.
                              If the name contains a ':', it is assumed that
                              the first portion of the string is the site name.
        :param export_state: String containing the export state.  Valid values are:
                             'imported', 'exported', or 'local'.
        :param remote_site:  String containing the remote site name
        """
        # Remove the local site from the contract if present
        if ':' in contract_name:
            names = contract_name.split(':')
            assert len(names) == 2
            contract_name = names[1]
        self._contract_name = contract_name
        #assert export_state in ['imported', 'exported', 'local']
        self._export_state = export_state
        self._remote_site = remote_site

    @staticmethod
    def is_multisite_tag(tag):
        """
        Indicates whether the tag is a multisite tag

        :param tag: String containing the tag from the APIC
        :returns: True or False.  True if the tag is considered a
                  multisite tag. False otherwise.
        """
        return re.match(r'multisite:.*:contract:.*:site:.*', tag)

    @classmethod
    def fromstring(cls, tag):
        """
        Extract the multisite tag from a string

        :param tag: String containing the multisite tag
        :returns: New instance of MultisiteTag
        """
        if not cls.is_multisite_tag(tag):
            assert cls.is_multisite_tag(tag)
            return None
        tag_data = tag.split(':')
        export_state = tag_data[1]
        contract_name = tag_data[3]
        remote_site_name = tag_data[5]
        new_tag = cls(contract_name, export_state, remote_site_name)
        return new_tag

    def __str__(self):
        """
        Convert the multisite tag into a string

        :returns: String containing the multisite tag
        """
        return 'multisite:' + self._export_state + ':contract:' + self._contract_name + ':site:' + self._remote_site

    def is_imported(self):
        """
        Checks if the multisite tag is imported.

        :returns: True if the export state is 'imported'.  False, otherwise.
        """
        if self._export_state == 'imported':
            return True
        return False

    def is_exported(self):
        """
        Checks if the multisite tag is exported.

        :returns: True if the export state is 'exported'.  False, otherwise.
        """
        if self._export_state == 'exported':
            return True
        return False

    def get_local_contract_name(self):
        """
        Get the contract name as used in the local site.  If imported, then the contract name is prepended
        with the site name.

        :returns: string containing the contract name
        """
        if self.is_imported():
            local_contract_name = strip_illegal_characters(self._remote_site) + ':' + self._contract_name
            return local_contract_name
        return self._contract_name

    def get_contract_name(self):
        """
        Get the contract name

        :returns: string containing the contract name
        """
        return self._contract_name

    def get_remote_site_name(self):
        """
        Get the remote site name

        :returns: string containing the remote site name
        """
        return self._remote_site

    def get_export_state(self):
        """
        Get the contract export state
        Valid values are: 'imported' and 'exported'

        :returns: string containing the contract export state
        """
        return self._export_state


class EndpointJsonDB(object):
    """
    Class responsible for tracking the Endpoints during processing.
    Used to queue bursts of Endpoint events before sending to the APIC
    """
    def __init__(self, local_site):
        self.db = {}
        self._local_site = local_site

    def get_remote_sites_using_epg(self, epg):
        """
        Get the remote sites that can use a particular EPG.  This equates to the
        remote sites that export/import a contract that the EPG provides/consumes

        :param epg: Instance of EPG class
        :returns: list of strings containing remote site names
        """
        remote_sites = []
        app = epg.get_parent()
        tenant = app.get_parent()
        epg_db = self._local_site.epg_db
        contract_db = self._local_site.contract_db
        epgdb_entries = epg_db.find_entries(tenant.name, app.name, epg.name)
        for epgdb_entry in epgdb_entries:
            contract_db_entry = contract_db.find_entry(tenant.name, epgdb_entry.contract_name)
            for remote_site in contract_db_entry.remote_sites:
                remote_sites.append(remote_site)
        return remote_sites

    def _convert_contract_name_to_other_site(self, contract_name):
        if ':' not in contract_name:
            contract_name = self._local_site.name + ':' + str(contract_name)
        else:
            contract_name = str(contract_name).partition(':')[2]
        return contract_name

    def _add_endpoint_subnet(self, tenant, endpoint, remote_site,
                             remote_contracts={}):
        network = OutsideNetwork(endpoint.name)
        if endpoint.is_deleted():
            network.mark_as_deleted()
        else:
            network.network = endpoint.ip + '/32'

            # Tag the l3extInstP with the EPG and site name
            epg = endpoint.get_parent()
            app = epg.get_parent()
            ntag = MultisiteTag(epg.name, app.name, self._local_site.name)
            network.add_tag(str(ntag))

            if remote_site in remote_contracts:
                for contract in remote_contracts[remote_site]['provides']:
                    contract_name = self._convert_contract_name_to_other_site(contract)
                    network.provide(Contract(contract_name, tenant))
                for contract in remote_contracts[remote_site]['consumes']:
                    contract_name = self._convert_contract_name_to_other_site(contract)
                    network.consume(Contract(contract_name, tenant))
        outside_epg_entries = self._local_site.outside_db.get_outside_epg_entries(tenant.name,
                                                                                  remote_site)
        if len(outside_epg_entries) == 0:
            # Likely, a site that is not up yet or old config
            return
        for outside_epg_entry in outside_epg_entries:
            # TODO need to loop through outside epg names and properly handle tenant common
            has_outside_epg = False
            if outside_epg_entry.uses_tenant_common:
                current_tenant = Tenant('common')
                current_tenant = self.get_tenant_from_db(remote_site, current_tenant)
            else:
                current_tenant = tenant
            outside_epgs = current_tenant.get_children(only_class=OutsideEPG)
            for outside_epg in outside_epgs:
                if outside_epg.name == outside_epg_entry.outside_epg_name:
                    outside = outside_epg
                    has_outside_epg = True
            if not has_outside_epg:
                outside = OutsideEPG(outside_epg_entry.outside_epg_name,
                                     current_tenant)
            outside.networks.append(network)

    def get_tenant_from_db(self, remote_site, tenant):
        if remote_site in self.db:
            if tenant.name not in self.db[remote_site]:
                self.db[remote_site][tenant.name] = Tenant(tenant.name)
            return self.db[remote_site][tenant.name]
        else:
            self.db[remote_site] = {}
            self.db[remote_site][tenant.name] = Tenant(tenant.name)
            return self.db[remote_site][tenant.name]

    def _remove_contracts_from_json(self, tenant_json):
        # Remove the contracts
        for child in tenant_json['fvTenant']['children']:
            if 'vzBrCP' in child:
                tenant_json['fvTenant']['children'].remove(child)

    def _get_contracts_using_epg(self, tenant_name, app_name, epg_name):
        remote_contracts = {}
        epgdb_entries = self._local_site.epg_db.find_entries(tenant_name, app_name, epg_name)
        for epgdb_entry in epgdb_entries:
            contract_db_entry = self._local_site.contract_db.find_entry(tenant_name, epgdb_entry.contract_name)
            for remote_site in contract_db_entry.remote_sites:
                if remote_site not in remote_contracts:
                    remote_contracts[remote_site] = {}
                    remote_contracts[remote_site]['provides'] = []
                    remote_contracts[remote_site]['consumes'] = []
                    remote_contracts[remote_site][epgdb_entry.state].append(contract_db_entry.contract_name)
        return remote_contracts

    def add_endpoint(self, endpoint):
        epg = endpoint.get_parent()
        if not self._local_site.uses_multisite_contract(epg):
            # Ignore this event.  Endpoint uses only local contracts
            return
        app = epg.get_parent()
        tenant = app.get_parent()
        if endpoint.is_deleted():
            remote_sites = self.get_remote_sites_using_epg(epg)
            for remote_site in remote_sites:
                tenant = self.get_tenant_from_db(remote_site, tenant)
                self._add_endpoint_subnet(tenant, endpoint, remote_site)
            return  # Done handling deleted Endpoint
        elif endpoint.ip == '0.0.0.0':
            # Ignore this event
            return
        # Need to push this to the remote sites
        # remote_contracts is a dictionary indexed by remote_site
        # Each dictionary entry contains 2 lists; provided contracts and consumed contracts
        remote_contracts = self._get_contracts_using_epg(tenant.name, app.name, epg.name)
        for remote_site in remote_contracts:
            tenant = self.get_tenant_from_db(remote_site, tenant)
            self._add_endpoint_subnet(tenant, endpoint, remote_site, remote_contracts)

    def _push_to_remote_site(self, remote_site_name, url, data_json):
        """
        Push the endpoints to the remote site

        :param remote_site_name: string containing the remote site name
        :param url: string containing the URL to be sent to the remote site APIC
        :param data_json: JSON dictionary containing all of the JSON to be pushed to the APIC
        :returns resp: Response object from the Requests library or None if remote site is unknown
        """
        remote_site_obj = self._local_site.my_collector.get_site(remote_site_name)
        if remote_site_obj is not None:
            remote_session = remote_site_obj.session
            resp = remote_session.push_to_apic(url, data_json)
            return resp

    def push_to_remote_sites(self):
        """
        Push the endpoints to the remote sites
        """
        for remote_site in self.db:
            for tenant_name in self.db[remote_site]:
                tenant = self.db[remote_site][tenant_name]
                tenant_json = tenant.get_json()
                self._remove_contracts_from_json(tenant_json)
                #self._local_site.contract_collector._rename_classes(tenant_json)
                resp = self._push_to_remote_site(remote_site, tenant.get_url(), tenant_json)
        self.db = {}


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
        self._endpointdb = EndpointJsonDB(local_site)
        # self.remote_sites = []

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def handle_contract(self, tenant_name, contract):
        tenants = Tenant.get_deep(self._local_site.session, names=[tenant_name], limit_to=['fvTenant', 'tagInst'],
                                  subtree='full', config_only=True)
        for tenant in tenants:  # a bit overkill, since only 1 tenant should be returned
            for tag in tenant.get_tags():
                if MultisiteTag.is_multisite_tag(tag.name):
                    mtag = MultisiteTag.fromstring(tag.name)
                    if mtag.is_imported():
                        # Update the list of remote l3extOuts
                        remote_site_name = mtag.get_remote_site_name()
                        remote_site_obj = self._local_site.my_collector.get_site(remote_site_name)
                        self._local_site.outside_db.update_from_apic(tenant.name, remote_site_obj)
                    if contract.name == mtag.get_local_contract_name():
                        if contract.is_deleted():
                            if mtag.is_exported():
                                self._local_site.unexport_contract(contract.name, tenant_name, mtag.get_remote_site_name())
                            cdb_entry = ContractDBEntry.from_multisite_tag(tenant.name, mtag)
                            self._local_site.contract_db.remove_entry(cdb_entry)
                            return None
                        else:
                            cdb_entry = ContractDBEntry.from_multisite_tag(tenant.name, mtag)
                            self._local_site.contract_db.add_entry(cdb_entry)
                            return cdb_entry
        # If it's not tagged then it must be a non-exported (local) contract
        cdb_entry = ContractDBEntry()
        cdb_entry.tenant_name = tenant_name
        cdb_entry.contract_name = contract.name
        cdb_entry.export_state = 'local'
        self._local_site.contract_db.add_entry(cdb_entry)
        return cdb_entry

    def _get_local_contractdb_entry(self, tenant_name, contract_name):
        cdb_entry = self._local_site.contract_db.find_entry(tenant_name, contract_name)
        if cdb_entry is None:
            # Check tenant common for the contract
            cdb_entry = self._local_site.contract_db.find_entry('common', contract_name)
        return cdb_entry

    def handle_contract_relation_event(self, event, apic_class, apic_dn_class):
        # Process any pending contract events to make sure we handle those first
        self.process_contract_events()

        # Extract status, tenant_name, contract_name
        event_attributes = event['imdata'][0][apic_class]['attributes']
        if 'status' in event_attributes:
            status = event_attributes['status']
        else:
            status = 'created'
        dn = event_attributes['dn']
        tenant_name = str(dn.split('uni/tn-')[1].split('/')[0])
        contract_name = str(dn.split('/%s-' % apic_dn_class)[1])

        # Get the ContractDB entry
        cdb_entry = self._get_local_contractdb_entry(tenant_name, contract_name)
        if cdb_entry is None:
            # Contract must have been deleted
            return
        # If this is local only contract, ignore it
        if cdb_entry.is_local():
            return

        # Extract app_name, epg_name
        assert '/ap-' in dn and '/out-' not in dn
        app_name = str(dn.split('/ap-')[1].split('/')[0])
        epg_name = str(dn.split('/epg-')[1].split('/')[0])

        # Record this EPG in the EpgDB
        epg_entry = EpgDBEntry()
        epg_entry.tenant_name = tenant_name
        epg_entry.app_name = app_name
        epg_entry.epg_name = epg_name
        epg_entry.contract_name = contract_name
        if apic_class == 'fvRsProv':
            epg_entry.state = 'provides'
        else:
            assert apic_class == 'fvRsCons'
            epg_entry.state = 'consumes'

        if status == 'deleted':
            self._local_site.epg_db.remove_entry(epg_entry)
            for remote_site_name in cdb_entry.remote_sites:
                # First get all of the Endpoint entries providing this contract
                outside_epg_entries = self._local_site.outside_db.get_outside_epg_entries(tenant_name, remote_site_name)
                if len(outside_epg_entries) == 0:
                    continue
                for outside_epg_entry in outside_epg_entries:
                    if outside_epg_entry.uses_tenant_common:
                        query_url = '/api/mo/uni/tn-common'
                    else:
                        query_url = '/api/mo/uni/tn-%s' % tenant_name
                    query_url += '/out-%s' % outside_epg_entry.outside_epg_name
                    query_url += '.json?query-target=subtree&target-subtree-class=%s' % apic_class
                    query_url += '&query-target-filter=eq(%s.tnVzBrCPName,"' % apic_class
                    if epg_entry.state == 'provides':
                        remote_contract_name = strip_illegal_characters(self._local_site.name) + ':' + contract_name
                    elif ':' in contract_name:
                        remote_contract_name = contract_name.split(':')[1]
                    else:
                        remote_contract_name = contract_name
                    query_url += remote_contract_name + '")&rsp-prop-include=config-only'
                    remote_site = self._my_collector.get_site(remote_site_name)
                    resp = remote_site.session.get(query_url)
                    data = resp.json()['imdata']

                    # Next, mark as deleted
                    if len(data):
                        for item in data:
                            if apic_class not in item:
                                continue
                            # Delete the fvRsProv/fvRsCons on the remote l3extInstPs
                            dn = '/api/mo/' + item[apic_class]['attributes']['dn'] + '.json'
                            data_json = {apic_class: {'attributes': {'status': 'deleted'}}}
                            # Push to APIC
                            resp = remote_site.session.push_to_apic(dn, data_json)
                            # Read back and see if any remaining contracts provided or consumed
                            # If none, delete the l3extInstP
                            query_url = dn + '?query-target=subtree&target-subtree-class=fvRsProv,fvRsCons&'
                            site_name = strip_illegal_characters(self._local_site.name) + ':'
                            query_url += 'query-target-filter=or(wcard(fvRsProv.tnVzBrCPName,"%s"),' % site_name
                            query_url += 'wcard(fvRsProv.tnVzBrCPName,"%s"))&rsp-prop-include=config-only' % site_name
                            resp = remote_site.session.get(query_url)
                            if int(resp.json()['totalCount']) == 0:
                                dn = dn.split('/%s-' % apic_dn_class)[0]
                                instp_name = dn.split('/instP-')[1].split('/')[0]
                                data_json = {'l3extInstP': {'attributes': {'name': instp_name, 'status': 'deleted'}}}
                                resp = remote_site.session.push_to_apic(dn + '.json', data_json)
        else:
            self._local_site.epg_db.add_entry(epg_entry)
            self.handle_existing_endpoints(tenant_name, app_name, epg_name)

    def handle_provided_contract_event(self, event):
        return self.handle_contract_relation_event(event, 'fvRsProv', 'rsprov')

    def handle_consumed_contract_event(self, event):
        return self.handle_contract_relation_event(event, 'fvRsCons', 'rscons')

    def handle_existing_endpoints(self, tenant_name, app_name, epg_name):
        endpoints = Endpoint.get_all_by_epg(self._session,
                                            tenant_name, app_name, epg_name,
                                            with_interface_attachments=False)
        for endpoint in endpoints:
            self._endpointdb.add_endpoint(endpoint)
        self._endpointdb.push_to_remote_sites()

    def handle_endpoint_event(self):
        # TODO: loop to batch the events and collect JSON before pushing it to APIC
        tenants_json = {}
        num_eps = MAX_ENDPOINTS
        while Endpoint.has_events(self._session) and num_eps:
            ep = Endpoint.get_event(self._session, with_relations=False)
            self._endpointdb.add_endpoint(ep)
            num_eps -= 1
        self._endpointdb.push_to_remote_sites()

    def process_contract_events(self):
        while Contract.has_events(self._session):
            contract = Contract.get_event(self._session)
            tenant = contract.get_parent()
            self.handle_contract(tenant.name, contract)

    def run(self):
        # Subscribe to endpoints
        Endpoint.subscribe(self._session)

        # Subscribe to Contract events
        resp = Contract.subscribe(self._session)

        # Subscribe to fvRsProv (EPGs providing Contracts)
        provides_url = '/api/class/fvRsProv.json?query-target-filter=wcard(fvRsProv.dn,"/ap-")&subscription=yes'
        resp = self._session.subscribe(provides_url)

        # Subscribe to fvRsCons (EPGs consuming Contracts)
        consumes_url = '/api/class/fvRsCons.json?query-target-filter=wcard(fvRsCons.dn,"/ap-")&subscription=yes'
        resp = self._session.subscribe(consumes_url)

        while not self._exit:
            self.process_contract_events()

            if self._session.has_events(provides_url):
                self.handle_provided_contract_event(self._session.get_event(provides_url))

            if self._session.has_events(consumes_url):
                self.handle_consumed_contract_event(self._session.get_event(consumes_url))

            if Endpoint.has_events(self._session):
                self.handle_endpoint_event()


class ContractCollector(object):
    """
    Class to collect the Contract from the APIC, along with all of the providing EPGs
    """
    classes_to_rename = {'fvRsProv': 'tnVzBrCPName',
                         'fvRsCons': 'tnVzBrCPName',
                         'fvRsProtBy': 'tnVzTabooName',
                         'vzBrCP': 'name',
                         'vzTaboo': 'name',
                         'vzFilter': 'name',
                         'vzRsSubjFiltAtt': 'tnVzFilterName',
                         'vzRsDenyRule': 'tnVzFilterName'}

    classes_to_tag = ['fvTenant']

    def __init__(self, session, local_site_name):
        self._session = session
        self.local_site_name = local_site_name

    def _strip_dn(self, data):
        """
        Recursively remove dn attributes from the JSON data

        :param data: JSON dictionary
        :return: None
        """
        if isinstance(data, list):
            for item in data:
                self._strip_dn(item)
        else:
            for key in data:
                if 'dn' in data[key]['attributes']:
                    del data[key]['attributes']['dn']
                if 'children' in data[key]:
                    self._strip_dn(data[key]['children'])

    def _find_all_of_attribute(self, data, attribute, class_names):
        """
        Find all of the object instance names belonging to a set of APIC classes

        :param data: JSON dictionary
        :param class_names: list of strings containing APIC class names
        :return: list of tuples in the form of (classname, objectname)
        """
        resp = []
        if isinstance(data, list):
            for item in data:
                resp = resp + self._find_all_of_attribute(item, attribute, class_names)
            return resp
        for key in data:
            if key in class_names:
                resp.append((key, data[key]['attributes'][attribute]))
            if 'children' in data[key]:
                resp = resp + self._find_all_of_attribute(data[key]['children'], attribute, class_names)
        return resp

    def get_contract_config(self, tenant, contract):
        # Create the tenant configuration
        tenant = Tenant(tenant)
        tenant_json = tenant.get_json()

        # Grab the Contract
        contract_children_to_migrate = ['vzSubj', 'vzRsSubjFiltAtt']
        query_url = '/api/mo/uni/tn-%s/brc-%s.json?query-target=self&rsp-subtree=full' % (tenant, contract)
        for child_class in contract_children_to_migrate:
            query_url += '&rsp-subtree-class=%s' % child_class
        query_url += '&rsp-prop-include=config-only'

        ret = self._session.get(query_url)
        if not len(ret.json()['imdata']):
            return
        contract_json = ret.json()['imdata'][0]
        tenant_json['fvTenant']['children'].append(contract_json)

        # Get the Filters referenced by the Contract
        class_names = ['vzRsSubjFiltAtt']
        filters = self._find_all_of_attribute(tenant_json, 'tnVzFilterName', class_names)
        for (class_name, filter_name) in filters:
            query_url = ('/api/mo/uni/tn-%s/flt-%s.json?query-target=self&rsp-subtree=full'
                         '&rsp-prop-include=config-only' % (tenant.name, filter_name))
            ret = self._session.get(query_url)
            filter_json = ret.json()['imdata']
            if len(filter_json):
                tenant_json['fvTenant']['children'].append(filter_json[0])
        self._strip_dn(tenant_json)
        return tenant_json

    @staticmethod
    def _pprint_json(data):
        print json.dumps(data, indent=4, separators=(',', ':'))

    def _rename_classes(self, data):
        if isinstance(data, list):
            for item in data:
                self._rename_classes(item)
        else:
            for key in data:
                if key in ContractCollector.classes_to_rename:
                    local_name = data[key]['attributes'][ContractCollector.classes_to_rename[key]]
                    data[key]['attributes'][ContractCollector.classes_to_rename[key]] = strip_illegal_characters(self.local_site_name) + ':' + local_name
                if 'children' in data[key]:
                    self._rename_classes(data[key]['children'])

    def _get_tag(self, contract_name, site_name, exported=True):
        if exported:
            export_state = 'exported'
        else:
            export_state = 'imported'
        tag = 'multisite:%s:contract:' % export_state + contract_name + ':site:' + site_name
        return tag

    def get_local_tag(self, contract_name, site_name):
        return self._get_tag(contract_name, site_name, exported=True)

    def get_remote_tag(self, contract_name, site_name):
        return self._get_tag(contract_name, site_name, exported=False)

    def _tag_local_config(self, data, contract_name):
        tag = {'tagInst': {'attributes': {'name': self.get_local_tag(contract_name, self.local_site_name)}}}
        data['fvTenant']['fvAEPg']['children'].append(tag)

    def _tag_remote_config(self, data, contract_name):
        if isinstance(data, list):
            for item in data:
                self._tag_remote_config(item, contract_name)
        else:
            for key in data:
                if key in ContractCollector.classes_to_tag:
                    assert 'children' in data[key]
                    tag = {'tagInst': {'attributes': {'name': self.get_remote_tag(contract_name, self.local_site_name)}}}
                    data[key]['children'].append(tag)
                if 'children' in data[key]:
                    self._tag_remote_config(data[key]['children'],
                                            contract_name)

    def export_epg(self, tenant_json, contract_name, remote_site):
        self.export_contract_config(tenant_json, contract_name, remote_site)

    def export_contract_config(self, tenant_json, contract_name, remote_site):
        assert remote_site is not None
        self._rename_classes(tenant_json)
        self._tag_remote_config(tenant_json, contract_name)
        resp = remote_site.session.push_to_apic(Tenant.get_url(), tenant_json)
        if not resp.ok:
            print '%% Could not export to remote APIC'
        return resp


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
        self.logged_in = False

    def get_credentials(self):
        return self.credentials

    def login(self):
        url = self.credentials.ip_address
        if self.credentials.use_https:
            url = 'https://' + url
        else:
            url = 'http://' + url
        self.session = Session(url, self.credentials.user_name, self.credentials.password)
        resp = self.session.login()
        return resp

    def __eq__(self, other):
        if self.name == other.name:
            return True
        else:
            return False

    def shutdown(self):
        pass

    def start(self):
        resp = self.login()
        if not resp.ok:
            print('%% Could not login to APIC on Site', self.name)
        else:
            print('%% Logged into Site', self.name)
            self.logged_in = True
        return resp


class MultisiteDB(object):
    def __init__(self):
        self._db = []
        self.callbacks = []

    def find_all(self):
        return self._db

    def register_callback(self, callback_function):
        if callback_function not in self.callbacks:
            self.callbacks.append(callback_function)

    def deregister_callback(self, callback_function):
        if callback_function in self.callbacks:
            self.callbacks.remove(callback_function)

    def trigger_callback(self):
        for callback in self.callbacks:
            callback()

    def has_entry(self, entry):
        return entry in self._db

    def add_entry(self, entry):
        if entry not in self._db:
            self._db.append(entry)
            self.trigger_callback()

    def remove_entry(self, entry):
        if entry not in self._db:
            return
        self._db.remove(entry)
        self.trigger_callback()


class ContractDBEntry(object):
    def __init__(self):
        self.tenant_name = None
        self.contract_name = None
        self.export_state = None
        self.remote_sites = []

    @classmethod
    def from_multisite_tag(cls, tenant_name, mtag):
        db_entry = cls()
        db_entry.tenant_name = tenant_name
        db_entry.contract_name = mtag.get_local_contract_name()
        db_entry.export_state = mtag.get_export_state()
        db_entry.remote_sites.append(mtag.get_remote_site_name())
        return db_entry

    def is_local(self):
        return self.export_state == 'local'

    def is_exported(self):
        return self.export_state == 'exported'

    def is_imported(self):
        return self.export_state == 'imported'

    def is_multisite(self):
        return self.is_exported() or self.is_imported()

    def __eq__(self, other):
        if self.tenant_name == other.tenant_name and self.contract_name == other.contract_name:
            return True
        else:
            return False

    def add_remote_site(self, mtag):
        self.export_state = mtag.get_export_state()
        remote_site = mtag.get_remote_site_name()
        if remote_site not in self.remote_sites:
            self.remote_sites.append(remote_site)

    def remove_remote_site(self, remote_site_name):
        self.remote_sites.remove(remote_site_name)

    def get_remote_sites_as_string(self):
        resp = ''
        for remote_site in self.remote_sites:
            resp += remote_site + ', '
        return resp[:-2]


class ContractDB(MultisiteDB):
    def __init__(self):
        super(ContractDB, self).__init__()

    def find_entry(self, tenant_name, contract_name):
        search_entry = ContractDBEntry()
        search_entry.tenant_name = tenant_name
        search_entry.contract_name = contract_name
        for entry in self._db:
            if entry == search_entry:
                return entry
        return None

    def has_entry(self, tenant_name, contract_name):
        if self.find_entry(tenant_name, contract_name) is not None:
            return True
        return False

    def add_remote_site(self, tenant_name, mtag):
        entry = self.find_entry(tenant_name, mtag.get_local_contract_name())
        if entry is None:
            assert False
        entry.add_remote_site(mtag)

    def print_entries(self):
        print 'Contract DB Entries:'
        for entry in self._db:
            print entry.tenant_name, ':', entry.contract_name, ':', entry.export_state


class EpgDBEntry(object):
    def __init__(self):
        self.tenant_name = None
        self.app_name = None
        self.epg_name = None
        self.contract_name = None
        self.state = None  # provides or consumes

    def __eq__(self, other):
        if (self.tenant_name == other.tenant_name) and (self.app_name == other.app_name) and \
           (self.epg_name == other.epg_name) and (self.contract_name == other.contract_name) and \
           (self.state == other.state):
            return True
        else:
            return False


class EpgDB(MultisiteDB):
    def __init__(self):
        super(EpgDB, self).__init__()

    def find_entries(self, tenant_name, app_name, epg_name):
        resp = []
        for entry in self._db:
            if entry.tenant_name == tenant_name and entry.app_name == app_name and entry.epg_name == epg_name:
                resp.append(entry)
        return resp

    def find_epgs_using_contract(self, tenant_name, contract_name):
        resp = []
        for db_entry in self._db:
            if db_entry.contract_name == contract_name and db_entry.tenant_name == tenant_name:
                resp.append(db_entry)
        return resp

    def print_db(self):
        print 'EPG Database'
        for entry in self._db:
            print 'tenant:', entry.tenant_name, 'app:', entry.app_name, 'epg:', entry.epg_name, 'contract:', entry.contract_name


class OutsideDBEntry(object):
    def __init__(self):
        self.tenant_name = None
        self.remote_site_name = None
        self.outside_epg_name = None
        self.uses_tenant_common = False

    def __eq__(self, other):
        if self.tenant_name == other.tenant_name and self.remote_site_name == other.remote_site_name:
            return True
        else:
            return False


class OutsideDB(MultisiteDB):
    def __init__(self, local_site):
        super(OutsideDB, self).__init__()
        self.local_site = local_site

    def add_entry(self, tenant_name, remote_site_name, outside_epg_name, uses_tenant_common=False):
        db_entry = OutsideDBEntry()
        db_entry.tenant_name = tenant_name
        db_entry.remote_site_name = remote_site_name
        db_entry.outside_epg_name = outside_epg_name
        db_entry.uses_tenant_common = uses_tenant_common
        if db_entry in self._db:
            self._db.remove(db_entry)
        self._db.append(db_entry)
        self.trigger_callback()

    def _get_entries(self, search_entry):
        resp = []
        for db_entry in self._db:
            if db_entry == search_entry:
                resp.append(db_entry)
        return resp

    def get_outside_epg_entries(self, tenant_name, remote_site_name):
        search_entry = OutsideDBEntry()
        search_entry.tenant_name = tenant_name
        search_entry.remote_site_name = remote_site_name
        db_entries = self._get_entries(search_entry)
        if len(db_entries):
            return db_entries
        # Don't have it.  Go get it from APIC
        remote_site_obj = self.local_site.my_collector.get_site(remote_site_name)
        if remote_site_obj is not None:
            self.update_from_apic(tenant_name, remote_site_obj)
            return self._get_entries(search_entry)
        else:
            return []

    # def has_entry(self, tenant_name, remote_site_name):
    #     return tenant_name in self._db

    def remove_entry(self, tenant_name, remote_site_name):
        search_entry = OutsideDBEntry()
        search_entry.tenant_name = tenant_name
        search_entry.remote_site_name = remote_site_name
        if search_entry in self._db:
            self._db.remove(search_entry)
            self.trigger_callback()

    def update_from_apic(self, tenant_name, remote_site):
        """
        Update the OutsideDB

        :param tenant_name: String containing the tenant name
        :param remote_site: Instance of RemoteSite
        :return: None
        """
        if isinstance(remote_site, str):
            remote_site = self.local_site.my_collector.get_site(remote_site)
        if remote_site is None:
            return
        tenant = Tenant(tenant_name)
        outside_epgs = OutsideEPG.get(remote_site.session, parent=tenant, tenant=tenant)
        if len(outside_epgs):  # TODO add multiple l3extOuts here
            # Remote tenant has l3extOuts.  Use those.
            for outside_epg in outside_epgs:
                self.add_entry(tenant_name, remote_site.name, outside_epg.name)
        else:
            # No l3extOuts in remote tenant.  Get from tenant common instead
            tenant = Tenant('common')
            outside_epgs = OutsideEPG.get(remote_site.session, parent=tenant, tenant=tenant)
            if len(outside_epgs):  # TODO add multiple l3extOuts here
                for outside_epg in outside_epgs:
                    self.add_entry(tenant_name, remote_site.name, outside_epg.name, uses_tenant_common=True)
            else:
                print '%% No Outside EPG found in remote site', remote_site.name

# TODO need to update get_outside_epg_name to return multiple entries.
# TODO also, need to handle be careful to handle the tenant common case properly since tenant common can't be
# TODO pushed in the same request as the tenant


class LocalSite(Site):
    def __init__(self, name, credentials, parent):
        super(LocalSite, self).__init__(name, credentials, local=True)
        self.contract_collector = None
        self.my_collector = parent
        self.monitor = None
        self.contract_db = ContractDB()
        self.epg_db = EpgDB()
        self.outside_db = OutsideDB(self)

    def register_for_callbacks(self, key, callback_function):
        """
        Register to get a callback when certain events occur.  Mainly when
        the various DBs are updated.

        :param key: String containing type of callback. Valid values are 'epgs' and 'contracts'
        :param callback_function: The function to be called upon changes
        :return: None
        """
        if key == 'contracts':
            self.contract_db.register_callback(callback_function)
        elif key == 'epgs':
            self.epg_db.register_callback(callback_function)

    def deregister_from_callbacks(self, key, callback_function):
        """
        Deregister the callback.

        :param key: String containing type of callback. Valid values are 'epgs' and 'contracts'
        :param callback_function: The function to be called upon changes
        :return: None
        """
        if key == 'contracts':
            self.contract_db.deregister_callback(callback_function)
        elif key == 'epgs':
            self.epg_db.deregister_callback(callback_function)

    def start(self):
        resp = super(LocalSite, self).start()
        if resp.ok:
            self.contract_collector = ContractCollector(self.session, self.name)
            self.monitor = MultisiteMonitor(self.session, self, self.my_collector)
            self.monitor.daemon = True
            self.monitor.start()
        return resp

    def _populate_contracts_from_apic(self):
        resp = []
        tenants = Tenant.get_deep(self.session, limit_to=['vzBrCP', 'fvTenant', 'tagInst'])

        # First handle imported and exported contracts through the tags
        for tenant in tenants:
            if tenant.has_tags():
                tags = tenant.get_tags()
                for tag in tags:
                    if MultisiteTag.is_multisite_tag(tag.name):
                        mtag = MultisiteTag.fromstring(tag.name)
                        db_entry = self.contract_db.find_entry(tenant.name, mtag.get_local_contract_name())
                        if db_entry is None:
                            db_entry = ContractDBEntry.from_multisite_tag(tenant.name, mtag)
                            self.contract_db.add_entry(db_entry)
                        else:
                            self.contract_db.add_remote_site(tenant.name, mtag)

        # Next, handle the non-exported local contracts
        for tenant in tenants:
            contracts = tenant.get_children(Contract)
            for contract in contracts:
                db_entry = self.contract_db.find_entry(tenant.name, contract.name)
                if db_entry is None:
                    db_entry = ContractDBEntry()
                    db_entry.tenant_name = tenant.name
                    db_entry.contract_name = contract.name
                    db_entry.export_state = 'local'
                    self.contract_db.add_entry(db_entry)

        # Sanity check : This can be removed later
        entries = []
        contract_count = 0
        print 'FROM CONTRACTS'
        for tenant in tenants:
            contracts = tenant.get_children(Contract)
            for contract in contracts:
                print 'tenant:', tenant.name, 'contract:', contract.name
                contract_count += 1
                entries.append((tenant.name, contract.name))
        print 'FROM DB'
        for db_entry in self.contract_db.find_all():
            print 'tenant:', db_entry.tenant_name, 'contract:', db_entry.contract_name
            if (db_entry.tenant_name, db_entry.contract_name) not in entries:
                print 'MISSING: ', db_entry.tenant_name, db_entry.contract_name
        print 'contract_count', contract_count, len(self.contract_db.find_all())

        # assert contract_count == len(self.contract_db.find_all())

    def get_contracts(self):
        return self.contract_db.find_all()

    def get_contract(self, tenant_name, contract_name):
        return self.contract_db.find_entry(tenant_name, contract_name)

    def uses_multisite_contract(self, epg):
        """
        Checks if a site is importing or exporting a given EPG

        :param epg: Instance of EPG class to check if being imported or exported
        :returns:  True or False.  True if the site is importing or exporting the
                   EPG, False otherwise.
        """
        app = epg.get_parent()
        tenant = app.get_parent()
        epg_db_entries = self.epg_db.find_entries(tenant.name, app.name, epg.name)
        if len(epg_db_entries) == 0:
            return False
        for epg_db_entry in epg_db_entries:
            contract_db_entry = self.contract_db.find_entry(tenant.name, epg_db_entry.contract_name)
            if contract_db_entry is None:
                continue
            if contract_db_entry.is_exported() or contract_db_entry.is_imported():
                return True
        return False

    def _populate_epgs_from_apic(self):
        resp = []
        contracts = self.get_contracts()
        tenants = Tenant.get_deep(self.session,
                                  limit_to=['vzBrCP', 'fvTenant', 'fvAp',
                                            'fvAEPg', 'fvRsProv', 'fvRsCons'])
        for contract in contracts:
            if contract.is_exported() or contract.is_imported():
                for tenant in tenants:
                    if tenant.name == contract.tenant_name:
                        contract_objs = tenant.get_children(Contract)
                        assert len(contract_objs)
                        for contract_obj in contract_objs:
                            if contract_obj.name == contract.contract_name:
                                break
                        apps = tenant.get_children(AppProfile)
                        for app in apps:
                            epgs = app.get_children(EPG)
                            for epg in epgs:
                                if epg.does_provide(contract_obj) or epg.does_consume(contract_obj):
                                    entry = EpgDBEntry()
                                    entry.tenant_name = tenant.name
                                    entry.app_name = app.name
                                    entry.epg_name = epg.name
                                    entry.contract_name = contract_obj.name
                                    if epg.does_provide(contract_obj):
                                        entry.state = 'provides'
                                    else:
                                        entry.state = 'consumes'
                                    if entry not in self.epg_db.find_all():
                                        self.epg_db.add_entry(entry)

    def get_epgs(self):
        return self.epg_db.find_all()

    def _populate_endpoints_from_apic(self):
        pass

    def initialize_from_apic(self):
        assert self.logged_in

        # Clear existing DB data
        self.contract_db = ContractDB()
        self.epg_db = EpgDB()

        # Get the latest data from the APIC
        self._populate_contracts_from_apic()
        self._populate_epgs_from_apic()
        self._populate_endpoints_from_apic()

        # Push the EPGs for imported contracts
        # (in case they were imported during a downtime)
        self.export_epgs_consuming_imported_contract()

    def unexport_contract(self, contract_name, tenant_name, remote_site):
        unexport_tenant = Tenant(str(tenant_name))
        local_contract_name = strip_illegal_characters(str(self.name)) + ':' + str(contract_name)

        # TODO this looks like it might unlink local contracts from an exported contract
        # TODO don't need to necessarily delete the realtion, just leave it.  User added, user can delete it
        remote_site_obj = self.my_collector.get_site(remote_site)
        remote_session = remote_site_obj.session
        query_url = ('/api/mo/uni/tn-%s.json?query-target=subtree&'
                     'target-subtree-class=fvRsCons,fvRsProv&'
                     'query-target-filter=or(eq(fvRsCons.tnVzBrCPName,"%s"),'
                     'eq(fvRsProv.tnVzBrCPName,"%s"))' % (tenant_name,
                                                          local_contract_name,
                                                          local_contract_name))
        resp = remote_session.get(query_url)
        if resp.ok and 'imdata' in resp.json():
            data = resp.json()['imdata']
            for item in data:
                if 'fvRsCons' in item:
                    apic_class = 'fvRsCons'
                else:
                    apic_class = 'fvRsProv'
                ret_data = {apic_class: {'attributes': {'tnVzBrCPName': local_contract_name,
                                                        'status': 'deleted'},
                                         'children': []}}
                query_url = '/api/mo/' + item[apic_class]['attributes']['dn'] + '.json'
                resp = remote_session.push_to_apic(query_url,
                                                   ret_data)
                # TODO need to read back and delete if no more fvRsCons/fvRsProv
                if '/instP-' in query_url:
                    main_query_url = query_url.rpartition('/')[0] + '.json'
                    query_url = main_query_url + '?query-target=subtree&target-subtree-class=fvRsCons,fvRsProv'
                    resp = remote_session.get(query_url)
                    if resp.ok and 'imdata' in resp.json():
                        data = resp.json()['imdata']
                        if len(data) == 0:
                            ret_data = {'l3extInstP': {'attributes': {'status': 'deleted'},
                                                       'children': []}}
                            resp = remote_session.push_to_apic(main_query_url,
                                                               ret_data)

        # Remove contract from remote site
        unexport_contract = Contract(local_contract_name, unexport_tenant)
        unexport_contract.mark_as_deleted()

        # TODO: Filters need to be removed

        # Remove tag from tenant in remote site
        mtag = MultisiteTag(str(contract_name), 'imported', str(self.name))
        unexport_tenant.add_tag(str(mtag))
        unexport_tenant.delete_tag(str(mtag))

        # Push config to the remote APIC
        resp = unexport_tenant.push_to_apic(remote_site_obj.session)

        # Remove tag locally from tenant
        local_tenant = Tenant(unexport_tenant.name)
        mtag = MultisiteTag(str(contract_name), 'exported', str(remote_site))
        local_tenant.add_tag(str(mtag))
        local_tenant.delete_tag(str(mtag))

        # Push config to the local APIC
        local_tenant.push_to_apic(self.session)

    def export_epg_providing_contract(self):
        # need tenant/app/epg, contract provided, remote_site
        pass

    def export_epgs_consuming_imported_contract(self):
        tenants = Tenant.get_deep(self.session, limit_to=['fvTenant', 'tagInst', 'vzBrCP',
                                                          'fvAp', 'fvAEPg', 'fvRsCons'],
                                  config_only=True)
        for tenant in tenants:
            tags = tenant.get_tags()
            for tag in tags:
                if not MultisiteTag.is_multisite_tag(tag.name):
                    continue
                mtag = MultisiteTag.fromstring(tag.name)
                if mtag.is_imported():
                    for contract in tenant.get_children(Contract):
                        if contract.name == mtag.get_local_contract_name():
                            break
                    for app in tenant.get_children(AppProfile):
                        for epg in app.get_children(EPG):
                            if epg.does_consume(contract):
                                export_tenant = Tenant(tenant.name)
                                export_app = AppProfile(app.name, export_tenant)
                                export_epg = EPG(str(epg.name), export_app)
                                export_tag = MultisiteTag(contract.name, 'imported', self.name)
                                export_epg.add_tag(str(export_tag))
                                export_contract = Contract(export_tag.get_contract_name(), export_tenant)
                                export_epg.consume(export_contract)
                                export_site = self.my_collector.get_site(mtag.get_remote_site_name())
                                if export_site is not None:
                                    resp = export_tenant.push_to_apic(export_site.session)
        self.epg_db.print_db()

    def export_contract(self, contract_name, tenant_name, remote_sites):
        problem_sites = []

        # get the old contract data
        old_entry = self.contract_db.find_entry(tenant_name, contract_name)
        contract_json = None

        # compare new remote sites list to old list for new sites to export
        for remote_site in remote_sites:
            if remote_site in old_entry.remote_sites:
                continue
            if remote_site not in old_entry.remote_sites:
                # New site that needs to be exported
                if contract_json is None:
                    # only grab the contract configuration once
                    contract_json = self.contract_collector.get_contract_config(str(tenant_name),
                                                                                str(contract_name))
                    if contract_json is None:
                        return remote_sites
                # Export to the remote site
                remote_site_obj = self.my_collector.get_site(remote_site)
                resp = self.contract_collector.export_contract_config(contract_json,
                                                                      contract_name,
                                                                      remote_site_obj)
                if not resp.ok:
                    problem_sites.append(remote_site)
                else:
                    # Now tag the local tenant
                    tenant = Tenant(str(tenant_name))
                    tenant.add_tag(self.contract_collector.get_local_tag(contract_name, remote_site))
                    tenant.push_to_apic(self.session)
                    # Update the OutsideDB if necessary
                    self.outside_db.update_from_apic(str(tenant_name), remote_site_obj)

        # compare old site list with new for sites no longer being exported to
        removed_site_names = []
        for old_site in old_entry.remote_sites:
            if old_site not in remote_sites:
                self.unexport_contract(contract_name, tenant_name, old_site)
                removed_site_names.append(old_site)

        # Remove the unexported sites from the ContractDBEntry
        for removed_site in removed_site_names:
            old_entry.remove_remote_site(removed_site)

        # update the ContractDB
        for problem_site in problem_sites:
            remote_sites.remove(problem_site)
        for remote_site in remote_sites:
            mtag = MultisiteTag(contract_name, 'exported', remote_site)
            old_entry.add_remote_site(mtag)
        if len(remote_sites) == 0:
            # Contract has been unexported from all sites
            old_entry.export_state = 'local'

        # Update the EPG DB
        self._populate_epgs_from_apic()

        return problem_sites


class RemoteSite(Site):
    def __init__(self, name, credentials):
        super(RemoteSite, self).__init__(name, credentials, local=False)


class MultisiteCollector(object):
    """

    """
    def __init__(self):
        self.sites = []

    @staticmethod
    def _extract_value(item):
        item = str(item).split('value="')[1]
        item = item.split('"')[0]
        return item

    def verify_legal_characters(self, site_name):
        site_name = self._extract_value(site_name)
        num_chars = len(site_name)
        return num_chars == len(strip_illegal_characters(site_name))

    def verify_unique_sitename(self, site_name):
        site_name = self._extract_value(site_name)
        sites = self.get_sites()
        for site in sites:
            if site.name == site_name:
                return False
        return True

    def verify_unique_ipaddress(self, ipaddress):
        ipaddress = self._extract_value(ipaddress)
        sites = self.get_sites()
        for site in sites:
            if site.credentials.ip_address == ipaddress:
                return False
        return True

    def get_sites(self, local_only=False, remote_only=False):
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
        local_sites = self.get_sites(local_only=True)
        if len(local_sites):
            return local_sites[0]
        else:
            return None

    def get_site(self, name):
        for site in self.sites:
            if site.name == name:
                return site

    def get_num_sites(self):
        return len(self.sites)

    def add_site(self, name, credentials, local):
        self.delete_site(name)
        if local:
            site = LocalSite(name, credentials, self)
        else:
            site = RemoteSite(name, credentials)
        self.sites.append(site)
        site.start()

    def delete_site(self, name):
        for site in self.sites:
            if name == site.name:
                site.shutdown()
                self.sites.remove(site)

    def print_sites(self):
        print 'Number of sites:', len(self.sites)
        for site in self.sites:
            print site.name, site.credentials.ip_address


def main():
    """
    Main execution routine when run standalone (i.e. not GUI)

    :return: None
    """
    parser = argparse.ArgumentParser(description='ACI Multisite Tool')
    parser.add_argument('--config', default=None, help='Configuration file')
    parser.add_argument('--generateconfig', action='store_true', default=False,
                        help='Generate an empty example configuration file')
    args = parser.parse_args()

    if args.generateconfig:
        config = {'config': [{'site': {'name': '',
                                       'ip_address': '',
                                       'username': '',
                                       'password': '',
                                       'use_https': '',
                                       'local': ''}},
                             {'export': {'contract': '',
                                         'tenant': '',
                                         'sites': [{'site': {'name': ''}}]}}]}

        json_data = json.dumps(config, indent=4, separators=(',', ':'))
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
        parser.print_help()
        return

    with open(args.config) as config_file:
        config = json.load(config_file)
    if 'config' not in config:
        print '%% Invalid configuration file'
        return

    collector = MultisiteCollector()

    # Configure all of the sites
    for site in config['config']:
        if 'site' in site:
            if site['site']['use_https'] == 'True':
                use_https = True
            else:
                use_https = False
            creds = SiteLoginCredentials(site['site']['ip_address'],
                                         site['site']['username'],
                                         site['site']['password'],
                                         use_https)
            if site['site']['local'] == 'True':
                is_local = True
            else:
                is_local = False
            collector.add_site(site['site']['name'],
                               creds,
                               is_local)

    # Initialize the local site
    local_site = collector.get_local_site()
    if local_site is None:
        print '%% No local site configured'
        return
    local_site.initialize_from_apic()

    # Export all of the configured exported contracts
    for contract in config['config']:
        if 'export' in contract:
            remote_sites = []
            for remote_site in contract['export']['sites']:
                remote_sites.append(remote_site['site']['name'])
            local_site.export_contract(contract['export']['contract'],
                                       contract['export']['tenant'],
                                       remote_sites)

    # Just wait, add any CLI here
    while True:
        pass

    #print json.dumps(config, indent=4, separators=(',', ':'))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
