#!/usr/bin/env python
"""
Inheritance application enables EPGs to inherit contracts from other EPGs
For documentation, refer to http://acitoolkit.readthedocs.org/en/latest/inheritance.html
"""
from acitoolkit.acitoolkit import (Tenant, AppProfile, EPG, OutsideL3, OutsideEPG, OutsideNetwork,
                                   IPEndpoint, Session, Contract, ContractInterface,
                                   Taboo)
import json
from jsonschema import validate, ValidationError, FormatChecker
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
import radix
# TODO update the setup.py dependencies to install py-radix

# Imports from standalone mode
import argparse


class GenericService(object):
    def __init__(self):
        self._json_schema = None
        self.logger = None

    def setup_logging(self, logging_level, max_log_files):
        # Set up the logging infrastructure
        if logging_level is not None:
            if logging_level == 'verbose':
                level = logging.DEBUG
            elif logging_level == 'warnings':
                level = logging.WARNING
            else:
                level = logging.CRITICAL
        else:
            level = logging.CRITICAL
        log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
        log_file = 'inheritance.%s.log' % str(os.getpid())
        my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024,
                                         backupCount=max_log_files, encoding=None, delay=0)
        my_handler.setLevel(level)
        my_handler.setFormatter(log_formatter)
        logger = logging.getLogger()
        logger.addHandler(my_handler)
        logger.setLevel(level)

    def set_json_schema(self, filename):
        try:
            with open(filename) as json_data:
                self._json_schema = json.load(json_data)
        except IOError:
            logging.error('Could not find JSON schema file.')
        except ValueError:
            logging.error('Schema file does not contain properly formatted JSON')

    def get_json_schema(self):
        return self._json_schema


class Event(object):
    def __init__(self, event):
        self.event = event

    @property
    def dn(self):
        return self.event[self.event_type]['attributes']['dn']

    @property
    def tenant(self):
        dn = self.dn
        tenant_name = dn.partition('/tn-')[-1].partition('/')[0]
        return tenant_name

    @property
    def epg(self):
        dn = self.dn
        tenant_name = self.tenant
        if '/out-' in dn:
            # Must be L3Out
            container_type = "l3out"
            container_name = dn.partition('/out-')[-1].partition('/')[0]
            epg_name = dn.partition('/instP-')[-1].partition('/')[0]
        elif '/ap-' in dn:
            # Must be a regular EPG
            container_type = "app"
            container_name = dn.partition('/ap-')[-1].partition('/')[0]
            epg_name = dn.partition('/epg-')[-1].partition('/')[0]
        elif 'l2out-' in dn:
            # TODO how do we deal with this ?
            container_type = "l2out"
            container_name = dn.partition('/l2out-')[-1].partition('/')[0]
            epg_name = dn.partition('/instP-')[-1].partition('/')[0]
        else:
            raise ValueError('Unexpected container type: %s' % dn)
        epg = {"tenant": tenant_name,
               "epg_container": {"name": container_name,
                                 "container_type": container_type},
               "name": epg_name}
        return EPGPolicy(epg)

    @property
    def event_type(self):
        for event_type in self.event:
            return event_type

    def is_deleted(self):
        status = self.event[self.event_type]['attributes']['status']
        return status == 'deleted'

    def __str__(self):
        return str(self.event)


class RelationEvent(Event):
    @property
    def relation_name(self):
        dn = self.event[self.event_type]['attributes']['dn']
        relation_name = ''
        if self.event_type == 'fvRsProv':
            relation_name = dn.partition('/rsprov-')[2]
        elif self.event_type == 'fvRsCons':
            relation_name = dn.partition('/rscons-')[2]
        elif self.event_type == 'fvRsProtBy':
            relation_name = dn.partition('/rsprotBy-')[2]
        elif self.event_type == 'fvRsConsIf':
            relation_name = dn.partition('/rsconsIf-')[2]
        return relation_name

# TODO need to subscribe to tag events in case someone deletes them

class TagEvent(RelationEvent):
    @property
    def event_type(self):
        return 'tagInst'

    def _process_names(self):
        tag_name = self.event['tagInst']['attributes']['dn'].partition('/tag-inherited:')[-1]
        return tag_name.split(':')

    @property
    def policy_relation_type(self):
        relation_type, relation_name = self._process_names()
        return relation_type

    @property
    def policy_relation_name(self):
        relation_type, relation_name = self._process_names()
        return relation_name


class SubnetEvent(Event):
    @property
    def event_type(self):
        return 'l3extSubnet'

    @property
    def l3out(self):
        return self.dn.partition('/out-')[-1].partition('/')[0]

    @property
    def l3instp(self):
        return self.dn.partition('/instP-')[-1].partition('/')[0]

    @property
    def subnet(self):
        return self.dn.partition('/extsubnet-[')[-1].partition(']')[0]


class EPGEvent(Event):
    pass

class BaseDB(object):
    def __init__(self):
        self.db = {}

    def _convert_policy_epg_to_db_epg(self, epg):
        if isinstance(epg, str):
            return epg
        elif isinstance(epg, dict):
            return (epg['tenant'],
                    epg['epg_container']['container_type'],
                    epg['epg_container']['name'],
                    epg['name'])
        elif isinstance(epg, EPGPolicy):
            return (epg.tenant,
                    epg.epg_container_type,
                    epg.epg_container_name,
                    epg.name)

    def _convert_db_epg_to_policy_epg(self, epg):
        if isinstance(epg, str):
            return json.loads(epg)
        if isinstance(epg, EPGPolicy):
            return epg
        (tenant_name, container_type, container_name, epg_name) = epg
        epg = {"tenant": tenant_name,
               "epg_container": {"name": container_name,
                                 "container_type": container_type},
               "name": epg_name}
        return EPGPolicy(epg)


class SubnetDB(BaseDB):
    """
    This database tracks the subnets.
    The database consists of a nested dictionary indexed by tenant and then by l3out name. The dictionary entries are
    radix trees containing the subnet addresses.  In addition to the subnet address, each radix tree node has the
    InstP that the subnet resides.
    """
    def is_l3out_known(self, epg):
        return epg.tenant in self.db and epg.l3out_name in self.db[epg.tenant]

    def get_all_subnets_for_epg(self, epg):
        logging.debug('get_all_subnets_for_epg for epg: %s', epg)
        subnets = []
        if epg.epg_container_type != 'l3out' or epg.tenant not in self.db or epg.epg_container_name not in self.db[epg.tenant]:
            logging.debug('no epg in subnet db: %s', self.db)
            return subnets
        logging.debug('looking at nodes for epg: %s', epg.epg_container_name)
        for node in self.db[epg.tenant][epg.epg_container_name].nodes():
            logging.debug('looking at node prefix: %s on epg: %s', node.prefix, node.data['l3instp'])
            if node.data['l3instp'] == epg.name:
                subnets.append(node.prefix)
        return subnets

    def get_all_covering_epgs_for_subnet(self, epg, subnet):
        """
        Get all of the EPGs with subnets covering the specified subnet.

        :param epg: EPGPolicy instance that is used to provide the tenant and l3out to scope the EPG search
        :param subnet: String containing the subnet that the search is for
        :return: list of EPGPolicy instances of EPGs with subnets that cover the specified subnet
        """
        logging.debug('get_all_covering_epgs_for_subnet for epg: %s subnet: %s', epg, subnet)
        covering_epgs = []
        if not self.is_l3out_known(epg):
            return covering_epgs

        covering_subnets = self.db[epg.tenant][epg.l3out_name].search_covering(subnet)
        for covering_subnet in covering_subnets:
            covering_epg = covering_subnet.data['l3instp']
            if covering_epg not in covering_epgs and covering_epg != epg.name:
                covering_epgs.append(covering_epg)

        covering_epg_policies = []
        for covering_epg in covering_epgs:
            covering_epg_policy = {"tenant": epg.tenant,
                                   "epg_container": {"name": epg.epg_container_name,
                                                     "container_type": epg.epg_container_type},
                                   "name": covering_epg}
            covering_epg_policy = EPGPolicy(covering_epg_policy)
            covering_epg_policies.append(covering_epg_policy)
        logging.debug('Found covering EPGs: %s', covering_epg_policies)
        return covering_epg_policies

    def get_all_covering_epgs(self, epg):
        logging.debug('get_all_covering_epgs for epg: %s', epg)

        covering_epgs = []

        # Find all the subnets for this epg
        my_subnets = self.get_all_subnets_for_epg(epg)

        # Get all the EPGs covering the subnets of this EPG
        for subnet in my_subnets:
            parent_epgs = self.get_all_covering_epgs_for_subnet(epg, subnet)
            for parent_epg in parent_epgs:
                if parent_epg not in covering_epgs:
                    covering_epgs.append(parent_epg)
        return covering_epgs


    def store_subnet_event(self, event):
        logging.debug('store_subnet_event for event: %s', event)
        assert isinstance(event, SubnetEvent)

        # Check if the l3out has been seen before and if not, set up the DB
        if not self.is_l3out_known(event.epg):
            if event.tenant not in self.db:
                self.db[event.tenant] = {}
            if event.l3out not in self.db[event.tenant]:
                self.db[event.tenant][event.l3out] = radix.Radix()

        # Store the subnet event
        if event.is_deleted():
            self.db[event.tenant][event.l3out].delete(event.subnet)
        else:
            # TODO new : should check to see if node is already in the radix and has the same l3instp
            # Add the subnet to the database
            logging.debug('Adding subnet %s to tenant %s epg %s', event.subnet, event.tenant, event.epg)
            subnet_node = self.db[event.tenant][event.l3out].add(event.subnet)
            subnet_node.data['l3instp'] = event.l3instp


class RelationDB(BaseDB):
    """
    This class is used to track the contract, taboo, and contractinterface relations from EPGs and OutsideEPGs
    """
    def __init__(self):
        super(RelationDB, self).__init__()
        self.db = {}

    def store_relation(self, event):
        assert isinstance(event, RelationEvent)
        logging.debug('add_relation: %s', event)
        epg = self._convert_policy_epg_to_db_epg(event.epg)
        if epg not in self.db:
            self.db[epg] = {}
        if event.event_type not in self.db[epg]:
            self.db[epg][event.event_type] = []
        if event.is_deleted():
            self.db[epg][event.event_type].remove(event.relation_name)
        elif event.relation_name not in self.db[epg][event.event_type]:
            self.db[epg][event.event_type].append(event.relation_name)
        logging.debug('Created relation db entry: EPG: %s TYPE: %s NAME: %s',
                      epg, event.event_type, event.relation_name)

    def get_relations_for_epg(self, epg):
        """
        Get the relations required for a given EPG

        :param epg: EPG to get the relations for
        :return: List of tuples containing relation_type, relation_name
        """
        logging.debug('get_relations_for_epg for epg: %s', epg)
        relations = []

        epg = self._convert_policy_epg_to_db_epg(epg)
        if epg not in self.db:
            return relations
        for relation_type in self.db[epg]:
            for relation_name in self.db[epg][relation_type]:
                relation = (relation_type, relation_name)
                if relation not in relations:
                    relations.append(relation)
        return relations

    def has_relation_for_epg(self, epg, relation):
        """
        Check if the relation exists for a given EPG

        :param epg: EPGPolicy instance to check for the relation
        :param relation: Tuple containing relation_type, relation_name
        :return: True if the relation exists for the specified EPG. False otherwise.
        """
        logging.debug('has_relation_for_epg for epg: %s relation: %s', epg, relation)
        epg = self._convert_policy_epg_to_db_epg(epg)
        if epg not in self.db:
            return False
        return relation in self.db[epg]


class TagDB(BaseDB):
    """
    This class is used to store all of the inheritance tags present on the APIC
    """
    def __init__(self):
        super(TagDB, self).__init__()
        self.db = {}

    def store_tag(self, tag_event):
        assert isinstance(tag_event, TagEvent)
        epg = self._convert_policy_epg_to_db_epg(tag_event.epg)
        if epg not in self.db:
            self.db[epg] = []
        db_entry = (tag_event.policy_relation_type, tag_event.policy_relation_name)
        if tag_event.is_deleted():
            self.db[epg].remove(db_entry)
        else:
            self.db[epg].append(db_entry)

    def is_inherited(self, epg, relation):
        """
        Check if the relation is inherited or not

        :param epg: EPGPolicy instance that the relation belongs
        :param relation: Tuple containing 2 strings; relation_type and relation_name
        :return: True if the relation is inherited. False, otherwise
        """
        epg = self._convert_policy_epg_to_db_epg(epg)
        if epg not in self.db:
            return False
        return relation in self.db[epg]


class Monitor(threading.Thread):
    """
    Thread responsible for monitoring EPG-to-Contract relations.
    """
    def __init__(self, cdb):
        threading.Thread.__init__(self)
        self.cdb = cdb
        self._monitor_frequency = 1
        self._exit = False
        self._relation_subscriptions = []
        self._inheritance_tag_subscriptions = []
        self._subnet_subscriptions = []
        self._relations = RelationDB()
        self._inheritance_tags = TagDB()
        self._subnets = SubnetDB()
        self.apic = None

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def subscribe(self, policy):
        query_url = ''
        epg = policy.epg
        epg_data = (epg.tenant, epg.epg_container_name, epg.name)
        if epg.epg_container_type == 'app':
            query_url = '/api/mo/uni/tn-%s/ap-%s/epg-%s.json' % epg_data
        elif epg.epg_container_type == 'l3out':
            subnet_query_url = '/api/mo/uni/tn-%s/out-%s/instP-%s.json' % epg_data
            subnet_query_url += '?query-target=subtree&target-subtree-class=l3extSubnet'
            subnet_query_url += '&subscription=yes'
            if subnet_query_url not in self._subnet_subscriptions:
                self.apic.subscribe(subnet_query_url)
                self._subnet_subscriptions.append(subnet_query_url)
            query_url = '/api/mo/uni/tn-%s/out-%s/instP-%s.json' % epg_data
        elif epg.epg_container_type == 'l2out':
            query_url = '/api/mo/uni/tn-%s/l2out-%s/instP-%s.json' % epg_data
        query_url += '?query-target=subtree&target-subtree-class=fvRsProv,fvRsCons,fvRsProtBy,fvRsConsIf'
        query_url += '&subscription=yes'
        if query_url not in self._relation_subscriptions:
            self.apic.subscribe(query_url)
            self._relation_subscriptions.append(query_url)

    def connect_to_apic(self):
        logging.debug('Connecting to APIC...')
        # Connect to APIC
        apic_config = self.cdb.get_apic_config()
        url = apic_config.ip_address
        if apic_config.use_https:
            url = 'https://' + url
        else:
            url = 'http://' + url
        if self.apic is not None:
            logging.debug('APIC is previously connected')
        self.apic = Session(url, apic_config.user_name, apic_config.password)
        resp = self.apic.login()

        # TODO: need to clear out the databases first

        # Get all of the subnets
        query_url = '/api/mo/uni.json?query-target=subtree&target-subtree-class=l3extSubnet'
        subnets = self.apic.get(query_url)
        for subnet in subnets.json()['imdata']:
            subnet_event = SubnetEvent(subnet)
            self._subnets.store_subnet_event(subnet_event)

        # Get all of the inherited relations
        tag_query_url = '/api/class/tagInst.json?query-target-filter=wcard(tagInst.name,"inherited:")'
        tags = self.apic.get(tag_query_url)
        for tag in tags.json()['imdata']:
            tag_event = TagEvent(tag)
            # Create a database entry for the inherited relations
            self._inheritance_tags.store_tag(tag_event)

        # Get all of the relations. We need this to track relations that are already present
        # i.e. configured but not through inheritance so that we can tell the difference
        query_url = '/api/mo/uni.json?query-target=subtree&target-subtree-class=fvRsProv,fvRsCons,fvRsProtBy,fvRsConsIf'
        relations = self.apic.get(query_url)
        for relation in relations.json()['imdata']:
            self._relations.store_relation(RelationEvent(relation))

        # Get all of the policies that are inherited from but not inheriting
        parent_only_policies = []
        for policy in self.cdb.get_inheritance_policies():
            inherited_from = False
            if policy.allowed and not policy.enabled:
                for child_policy in self.cdb.get_inheritance_policies():
                    if child_policy.has_inherit_from() and child_policy.inherit_from == policy.epg:
                        inherited_from = True
            if inherited_from:
                parent_only_policies.append(policy)

        # Issue all of the subscriptions
        for policy in self.cdb.get_inheritance_policies():
            self.subscribe(policy)
        for parent_only_policy in parent_only_policies:
            self.subscribe(parent_only_policy)
        tag_query_url += '&subscription=yes'
        self.apic.subscribe(tag_query_url)
        self._inheritance_tag_subscriptions.append(tag_query_url)

    def _add_inherited_relation(self, tenants, epg, relation, deleted=False):
        tenant_found = False

        # Find the tenant. Add if necessary
        for tenant in tenants:
            if tenant.name == epg.tenant:
                tenant_found = True
                break
        if not tenant_found:
            tenant = Tenant(epg.tenant)
            tenants.append(tenant)

        # Find the EPG Container. Add if necessary
        if epg.is_l3out:
            epg_container_class = OutsideL3
        else:
            epg_container_class = AppProfile
        epg_containers = tenant.get_children(only_class=epg_container_class)
        epg_container_found = False
        for epg_container in epg_containers:
            if epg_container.name == epg.epg_container_name:
                epg_container_found = True
                break
        if not epg_container_found:
            epg_container = epg_container_class(epg.epg_container_name, tenant)

        # Find the EPG. Add if necessary
        if epg.is_l3out:
            epg_class = OutsideEPG
        else:
            epg_class = EPG
        epgs = tenant.get_children(only_class=epg_class)
        epg_found = False
        for tenant_epg in epgs:
            if tenant_epg.name == epg.name:
                epg_found = True
                break
        if not epg_found:
            tenant_epg = epg_class(epg.name, epg_container)

        # Add the relation
        (relation_type, relation_name) = relation
        if relation_type == 'fvRsProv':
            contract = Contract(relation_name, tenant)
            tenant_epg.provide(contract)
            if deleted:
                tenant_epg.provide(contract)
                tenant_epg.dont_provide(contract)
        elif relation_type == 'fvRsCons':
            contract = Contract(relation_name, tenant)
            tenant_epg.consume(contract)
            if deleted:
                tenant_epg.consume(contract)
                tenant_epg.dont_consume(contract)
        elif relation_type == 'fvRsConsIf':
            contract_interface = ContractInterface(relation_name, tenant)
            tenant_epg.consume_cif(contract_interface)
            if deleted:
                tenant_epg.consume_cif(contract_interface)
                tenant_epg.dont_consume_cif(contract_interface)
        elif relation_type == 'fvRsProtBy':
            taboo = Taboo(relation_name, tenant)
            tenant_epg.protect(taboo)
            if deleted:
                tenant_epg.protect(taboo)
                tenant_epg.dont_protect(taboo)
        tenant_epg.add_tag('inherited:%s:%s' % (relation_type, relation_name))
        if deleted:
            tenant_epg.delete_tag('inherited:%s:%s' % (relation_type, relation_name))
        return tenants

    def add_inherited_relation(self, tenants, epg, relation):
        return self._add_inherited_relation(tenants, epg, relation)

    def remove_inherited_relation(self, tenants, epg, relation):
        return self._add_inherited_relation(tenants, epg, relation, deleted=True)

    def _calculate_relations_for_l3out_policy(self, inheritance_policy):
        logging.debug('_calculate_relations_for_l3out_policy: %s', inheritance_policy)
        # Get all of the EPGs covering this policy's EPG's subnets
        covering_epgs = self._subnets.get_all_covering_epgs(inheritance_policy.epg)

        # Remove any EPGs that are not allowed to be inherited
        for covering_epg in covering_epgs:
            if not self.cdb.is_inheritance_allowed(covering_epg):
                covering_epgs.remove(covering_epg)

        # Get all of the relations for the remaining covering EPGs
        relations = []
        for covering_epg in covering_epgs:
            epg_relations = self._relations.get_relations_for_epg(covering_epg)
            for epg_relation in epg_relations:
                if epg_relation not in relations:
                    relations.append(epg_relation)

        logging.debug('Relations to be inherited: %s', relations)

        # Need to add any configured relations
        configured_relations = self._relations.get_relations_for_epg(inheritance_policy.epg)
        for configured_relation in configured_relations:
            if configured_relation not in relations:
                logging.debug('Adding configured relation: %s', configured_relation)
                if not self._inheritance_tags.is_inherited(inheritance_policy.epg, configured_relation):
                    relations.append(configured_relation)
        return relations

    def _calculate_relations_for_app_policy(self, inheritance_policy):
        pass

    def calculate_relations(self):
        relations = {}
        for inheritance_policy in self.cdb.get_inheritance_policies():
            if not inheritance_policy.enabled:
                continue
            if inheritance_policy.epg.is_l3out():
                epg_relations = self._calculate_relations_for_l3out_policy(inheritance_policy)
            else:
                # TODO: may eventually need to process l2out
                self._calculate_relations_for_app_policy(inheritance_policy)
            relations[inheritance_policy.epg.get_json()] = epg_relations
        return relations

    def process_relation_event(self, event):
        logging.debug('process_event EVENT: %s', event.event)
        self._relations.store_relation(event)

    def process_subnet_event(self, event):
        logging.debug('Received subnet event: %s', event)
        # Store the subnet in the SubnetDB
        self._subnets.store_subnet_event(event)

    def process_inheritance_tag_event(self, event):
        logging.debug('Received subnet event: %s', event)
        # Store the tag in the TagDB
        self._inheritance_tags.store_tag(event)

    def _process_events(self, old_relations):
        while self.apic is None:
            pass

        # Check for any tag events
        for subscription in self._inheritance_tag_subscriptions:
            while self.apic.has_events(subscription):
                event = TagEvent(self.apic.get_event(subscription)['imdata'][0])
                self.process_inheritance_tag_event(event)

        # Check for relation events
        for subscription in self._relation_subscriptions:
            while self.apic.has_events(subscription):
                event = RelationEvent(self.apic.get_event(subscription)['imdata'][0])
                self.process_relation_event(event)

        # Check for subnet events
        for subscription in self._subnet_subscriptions:
            while self.apic.has_events(subscription):
                event = SubnetEvent(self.apic.get_event(subscription)['imdata'][0])
                self.process_subnet_event(event)

        # Calculate the new set of relations
        new_relations = self.calculate_relations()

        logging.debug('OLD_RELATIONS: %s %s', len(old_relations), old_relations)
        for old_epg in old_relations:
            logging.debug(old_epg)
        logging.debug('NEW_RELATIONS: %s %s', len(new_relations), new_relations)
        for new_epg in new_relations:
            logging.debug(new_epg)

        # Compare the old and the new relations for changes
        tenants = []
        for new_epg in new_relations:
            if new_epg not in old_relations:
                # New EPG, so we need to add all of the relations
                for new_relation in new_relations[new_epg]:
                    if self._inheritance_tags.is_inherited(EPGPolicy(json.loads(new_epg)), new_relation):
                        # If it's inherited, but we don't have the relation. We are likely coming up and not populated
                        # the old_relations yet
                        #continue
                        pass
                    # If just configured, we will have a relationDB entry. Otherwise, we need to inherit it
                    if self._relations.has_relation_for_epg(EPGPolicy(json.loads(new_epg)), new_relation):
                        continue
                    tenants = self.add_inherited_relation(tenants, EPGPolicy(json.loads(new_epg)), new_relation)
            else:
                # Handle any new added relations
                for new_relation in new_relations[new_epg]:
                    if new_relation not in old_relations[new_epg]:
                        if self._relations.has_relation_for_epg(EPGPolicy(json.loads(new_epg)), new_relation):
                            continue
                        tenants = self.add_inherited_relation(tenants, EPGPolicy(json.loads(new_epg)), new_relation)
                # Handle any deleted relations
                for old_relation in old_relations[new_epg]:
                    if old_relation not in new_relations[new_epg]:
                        if self._inheritance_tags.is_inherited(EPGPolicy(json.loads(new_epg)), old_relation):
                            tenants = self.remove_inherited_relation(tenants, EPGPolicy(json.loads(new_epg)), old_relation)
                        else:
                            # Must have been configured and manually deleted
                            pass
        for old_epg in old_relations:
            if old_epg not in new_relations:
                for old_relation in old_relations[old_epg]:
                    if self._inheritance_tags.is_inherited(EPGPolicy(json.loads(old_epg)), old_relation):
                        tenants = self.remove_inherited_relation(tenants, EPGPolicy(json.loads(old_epg)), old_relation)

        # Push the necessary config to the APIC
        for tenant in tenants:
            resp = tenant.push_to_apic(self.apic)
            if resp.ok:
                logging.debug('Pushed to APIC successfully')
            else:
                logging.error('Error pushing to APIC', resp.text)
        return new_relations

    def run(self):
        loop_count = 0
        accelerated_cleanup_done = False
        old_relations = {}
        while not self._exit:
            time.sleep(self._monitor_frequency)
            old_relations = self._process_events(old_relations)
            # if not accelerated_cleanup_done:
            #     if loop_count < 3:
            #         loop_count += 1
            #     elif loop_count == 3:
            #         logging.debug('Running accelerated cleanup...')
            #         self.remove_crufty_inherited_relations()
            #         accelerated_cleanup_done = True
            #         logging.debug('Completed accelerated cleanup')


class PolicyObject(object):
    def __init__(self, policy):
        self._policy = policy

    def __eq__(self, other):
        return self._policy == other._policy

    def __str__(self):
        return str(self._policy)


class EPGPolicy(PolicyObject):
    @property
    def tenant(self):
        return self._policy['tenant']

    @property
    def epg_container_type(self):
        return self._policy['epg_container']['container_type']

    @property
    def epg_container_name(self):
        return self._policy['epg_container']['name']

    @property
    def l3out_name(self):
        if self.epg_container_type != 'l3out':
            return ''
        return self.epg_container_name

    @property
    def name(self):
        return self._policy['name']

    def is_l3out(self):
        return self.epg_container_type == 'l3out'

    def get_json(self):
        return json.dumps(self._policy)


class ApicPolicy(PolicyObject):
    @property
    def ip_address(self):
        return self._policy['ip_address']

    @property
    def use_https(self):
        return self._policy['use_https']

    @property
    def user_name(self):
        return self._policy['user_name']

    @property
    def password(self):
        return self._policy['password']


class InheritancePolicy(PolicyObject):
    @property
    def epg(self):
        return EPGPolicy(self._policy['epg'])

    @property
    def allowed(self):
        try:
            return self._policy['allowed']
        except KeyError:
            return False

    @property
    def enabled(self):
        try:
            return self._policy['enabled']
        except KeyError:
            return False

    @property
    def inherit_from(self):
        assert 'inherit_from' in self._policy
        return EPGPolicy(self._policy['inherit_from'])

    def has_inherit_from(self):
        return 'inherit_from' in self._policy


class ConfigDB(object):
    def __init__(self):
        self._apic_policy = None
        self._inheritance_policies = []

    def store_apic_config(self, new_config):
        """
        Store the APIC configuration in the current configuration.

        :param new_config: Config JSON
        :return: True if config has changed from previous config. False if no change.
        """
        # If no apic in new config, we just want to keep the current
        if 'apic' not in new_config:
            return False
        # If no current APIC config, then take the new config
        if not self.has_apic_config():
            self._apic_policy = ApicPolicy(new_config['apic'])
            return True
        if self._apic_policy == ApicPolicy(new_config['apic']):
            return False
        self._apic_policy = ApicPolicy(new_config['apic'])
        return True

    def has_apic_config(self):
        #return 'apic' in self._config
        return self._apic_policy is not None

    def get_apic_config(self):
        #return self._config['apic']
        return self._apic_policy

    def store_inheritance_policy(self, inheritance_policy):
        """
        Store the inheritance policy in the current configuration.

        :param inheritance_policy:
        :return: True if config has changed from previous config. False if no change.
        """
        inheritance_policy = InheritancePolicy(inheritance_policy)
        for configured_policy in self.get_inheritance_policies():
            # If we already have this policy, we're done
            if configured_policy == inheritance_policy:
                return False
            # Check if the EPG is the same
            if configured_policy.epg == inheritance_policy.epg:
                # Something must have changed. Replace the old policy with the new one.
                self.remove_inheritance_policy(configured_policy)
                self.add_inheritance_policy(inheritance_policy)
                return True
        # If we get this far, we must not have the policy
        self.add_inheritance_policy(inheritance_policy)
        return True

    def get_inheritance_policy(self, epg):
        for configured_policy in self.get_inheritance_policies():
            # If we already have this policy, we're done
            if configured_policy.epg == epg:
                return configured_policy
        return None

    def remove_inheritance_policy(self, policy):
        self._inheritance_policies.remove(policy)

    def add_inheritance_policy(self, policy):
        self._inheritance_policies.append(policy)

    def get_inheritance_policies(self):
        return self._inheritance_policies

    def store_config(self, config_json):
        config_change = False
        if 'inheritance_policies' in config_json:
            # No inheritance policies
            for inheritance_policy in config_json['inheritance_policies']:
                if self.store_inheritance_policy(inheritance_policy):
                    logging.debug('Inheritance policy config has changed.')
                    config_change = True
        if self.store_apic_config(config_json):
            logging.debug('APIC config has changed.')
            config_change = True
        return config_change

    def is_inheritance_allowed(self, epg):
        policy = self.get_inheritance_policy(epg)
        if policy is None:
            return False
        return policy.allowed


class InheritanceService(GenericService):
    def __init__(self):
        self.cdb = ConfigDB()
        self.monitor = None
        super(InheritanceService, self).__init__()
        self.set_json_schema('schema.json')

    def add_config(self, config_json):
        logging.debug('Received new config: %s', config_json)
        try:
            validate(config_json, self._json_schema, format_checker=FormatChecker())
        except ValidationError as e:
            logging.error('JSON configuration validation failed: %s', e.message)
        if self.cdb.store_config(config_json) and self.cdb.has_apic_config():
            if self.monitor is not None:
                self.monitor.exit()
            self.monitor = Monitor(self.cdb)
            self.monitor.daemon = True
            self.monitor.start()
            self.monitor.connect_to_apic()
        return 'OK'

    def exit(self):
        self.monitor.exit()


class CommandLine(cmd.Cmd):
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


def execute_tool(args, cli_mode=False):
    """
    Main Inheritance application execution

    :param args: command line arguments
    :param cli_mode: True or False. True indicates that the command line parser should be run.
                     False is used by test routines and when invoked by the REST API
    :return: None
    """

    logging.info('Starting the tool....')
    # Handle generating sample configuration
    if args.generateconfig:
        raise NotImplementedError

    # if args.config is None:
    #     print '%% No configuration file given.'
    #     return

    tool = InheritanceService()
    tool.setup_logging(args.debug, args.maxlogfiles)
    tool.set_json_schema('schema.json')

    if not cli_mode:
        return tool

    # Start the Command line parser
    CommandLine(tool).cmdloop()
    while True:
        pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
