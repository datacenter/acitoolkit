#!/usr/bin/env python
"""
Application to push contract configuration to the APIC
"""
from acitoolkit import (Tenant, AppProfile, EPG,
                        Session, Contract, ContractSubject, Filter, FilterEntry,
                        BridgeDomain, AttributeCriterion,
                        Node, Context)
import json
from jsonschema import validate, ValidationError, FormatChecker
import logging
from logging.handlers import RotatingFileHandler
import os
import ipaddress

# Imports from standalone mode
import argparse


class GenericService(object):
    """
    Base class for services
    """

    def __init__(self):
        self._json_schema = None
        self.logger = None
        self._displayonly = False

    def set_json_schema(self, filename):
        """
        Set the JSON schema filename

        :param filename: String containing the filename of the JSON schema
        :return: None
        """
        try:
            with open(filename) as json_data:
                self._json_schema = json.load(json_data)
        except IOError:
            logging.error('Could not find JSON schema file.')
        except ValueError:
            logging.error('Schema file does not contain properly formatted JSON')

    def get_json_schema(self):
        """
        Get the JSON Schema
        :return: Dictionary containing the JSON schema
        """
        return self._json_schema

    @property
    def displayonly(self):
        """
        Get the display only flag.  This will cause the JSON to be displayed but not pushed to APIC.
        """
        return self._displayonly

    @displayonly.setter
    def displayonly(self, x):
        """
        Set the display only flag.  This will cause the JSON to be displayed but not pushed to APIC.
        """
        self._displayonly = x


class PolicyObject(object):
    """
    Base Policy Object
    """

    def __init__(self, policy):
        self._policy = policy

    def __eq__(self, other):
        return self._policy == other._policy

    def __str__(self):
        return str(self._policy)

    @staticmethod
    def _replace_invalid_chars(name, valid_char_set):
        stripped_name = ''
        for char in name:
            if char not in valid_char_set and not char.isalnum():
                stripped_name += '_'
            else:
                stripped_name += char
        return stripped_name

    def replace_invalid_name_chars(self, name):
        valid_char_set = set('_.:-')
        return self._replace_invalid_chars(name, valid_char_set)

    def replace_invalid_descr_chars(self, name):
        valid_char_set = set('\\!#$%()*,-./:;@ _{|}~?&+')
        return self._replace_invalid_chars(name, valid_char_set)


class ApicPolicy(PolicyObject):
    """
    APIC policy - defines APIC credentials
    """
    @property
    def ip_address(self):
        """
        IP address of the APIC
        :return: String containing the IP address of the APIC
        """
        return self._policy['ip_address']

    @property
    def use_https(self):
        """
        Use HTTPS flag
        :return: True if HTTPS is to be used. False is HTTP to be used.
        """
        return self._policy['use_https']

    @property
    def user_name(self):
        """
        Username to use to login to the APIC
        :return: String containing the username
        """
        return self._policy['user_name']

    @property
    def password(self):
        """
        Password to use to login to the APIC
        :return: String containing the password
        """
        return self._policy['password']

    @property
    def url(self):
        """
        URL to use to login to the APIC
        :return: String containing the URL
        """
        if self.use_https:
            return 'https://' + self.ip_address
        else:
            return 'http://' + self.ip_address


class WhitelistPolicy(PolicyObject):
    """
    Whitelist Policy
    """

    def __init__(self, policy):
        super(WhitelistPolicy, self).__init__(policy)
        assert 'proto' in self._policy
        assert 'port' in self._policy and len(self._policy['port']) == 2

    @property
    def proto(self):
        """
        Protocol number
        :return: String containing the protocol number
        """
        return str(self._policy['proto'])

    @property
    def port_min(self):
        """
        Minimum port number
        :return: String containing the minimum port number
        """
        return str(self._policy['port'][0])

    @property
    def port_max(self):
        """
        Maximum port number
        :return: String containing the maximum port number
        """
        return str(self._policy['port'][1])


class NodePolicy(PolicyObject):
    """
    Node Policy
    """

    def __init__(self, policy):
        super(NodePolicy, self).__init__(policy)

    @property
    def name(self):
        """
        Node name
        :return: String containing the Node  name
        """
        return self._policy['name']

    @property
    def ip(self):
        """
        Node IP address
        :return: String containing the Node IP address
        """
        return self._policy['ip']

    @property
    def prefix_len(self):
        """
        Node IP prefix length
        :return: Integer containing the prefix length
        """
        return self._policy['prefix_len']


class EPGPolicy(PolicyObject):
    """
    EPG Policy
    """

    def __init__(self, policy):
        super(EPGPolicy, self).__init__(policy)
        self._node_policies = []
        self._populate_node_policies()

    def _populate_node_policies(self):
        """
        Fill in the Node policies
        :return: None
        """
        for node_policy in self._policy['nodes']:
            self._node_policies.append(NodePolicy(node_policy))

    @property
    def id(self):
        """
        EPG Unique Identifier
        :return: String containing EPG Unique Identifier
        """
        return self._policy['id']

    @property
    def name(self):
        """
        EPG Name
        :return: String containing EPG Name
        """
        return self._policy['name']

    @name.setter
    def name(self, value):
        self._policy['name'] = value

    @property
    def descr(self):
        """
        EPG Description
        :return: String containing EPG Description
        """
        if 'descr' not in self._policy:
            return ''
        return self._policy['descr']

    @descr.setter
    def descr(self, value):
        self._policy['descr'] = value

    def get_node_policies(self):
        """
        Get the Node policies
        :return: List of NodePolicy instances
        """
        return self._node_policies


class ApplicationPolicy(PolicyObject):
    """
    Application Profile Policy
    """
    @property
    def id(self):
        return self._policy['id']

    @property
    def name(self):
        return self._policy['name']

    @property
    def clusters(self):
        return self._policy['clusters']


class ContextPolicy(PolicyObject):
    """
    Context Policy
    """
    @property
    def id(self):
        return self._policy['id']

    @property
    def name(self):
        return self._policy['name']

    @property
    def tenant_id(self):
        return self._policy['tenant_id']

    @property
    def tenant_name(self):
        return self._policy['tenant_name']


class ContractPolicy(PolicyObject):
    """
    Contract Policy
    """

    def __init__(self, policy):
        super(ContractPolicy, self).__init__(policy)
        self._whitelist_policies = []
        self._populate_whitelist_policies()
        self.src_ids = [self.src_id]
        self.dst_ids = [self.dst_id]

    def _populate_whitelist_policies(self):
        """
        Fill in the Whitelist policies
        :return: None
        """
        for whitelist_policy in self._policy['whitelist']:
            self._whitelist_policies.append(WhitelistPolicy(whitelist_policy))

    @property
    def src_id(self):
        """
        Get the source identifier
        :return: String containing the source identifier
        """
        return self._policy['src']

    @property
    def dst_id(self):
        """
        Get the destination identifier
        :return: String containing the destination identifier
        """
        return self._policy['dst']

    @property
    def src_name(self):
        """
        Get the source name
        :return: String containing the source name
        """
        return self._policy['src_name']

    @src_name.setter
    def src_name(self, value):
        self._policy['src_name'] = value

    @property
    def dst_name(self):
        """
        Get the destination name
        :return: String containing the destination name
        """
        return self._policy['dst_name']

    @dst_name.setter
    def dst_name(self, value):
        self._policy['dst_name'] = value

    @property
    def descr(self):
        """
        EPG Description
        :return: String containing EPG Description
        """
        if 'descr' not in self._policy:
            return ''
        return self._policy['descr']

    @descr.setter
    def descr(self, value):
        self._policy['descr'] = value

    def get_whitelist_policies(self):
        """
        Get the Whitelist policies
        :return: List of WhitelistPolicy instances
        """
        return self._whitelist_policies

    def has_same_permissions(self, other):
        """
        Check if the Contract Policies have the exact same permissions
        :param other: Instance of ContractPolicy to compare against
        :return: True if the Contract Policies have the exact same permissions. False otherwise
        """
        if len(self.get_whitelist_policies()) != len(other.get_whitelist_policies()):
            return False
        all_found = True
        for my_whitelist in self.get_whitelist_policies():
            if my_whitelist not in other.get_whitelist_policies():
                all_found = False
        return all_found

    @staticmethod
    def _has_same_ids(first_ids, second_ids):
        """
        Check if the 2 sets of identifiers are the same

        :param first_ids:  First set of identifier strings to compare
        :param second_ids: Second set of identifier strings to compare
        :return: True if they are the same. False otherwise.
        """
        if len(first_ids) != len(second_ids):
            return False
        for first_id in first_ids:
            if first_id not in second_ids:
                return False
        return True

    def has_same_src_ids(self, other):
        """
        Check if the Contract Policies have the exact same source identifiers
        :param other: Instance of ContractPolicy to compare against
        :return: True if the Contract Policies have the exact same source identifiers. False otherwise
        """
        return self._has_same_ids(self.src_ids, other.src_ids)

    def has_same_dst_ids(self, other):
        """
        Check if the Contract Policies have the exact same destination identifiers
        :param other: Instance of ContractPolicy to compare against
        :return: True if the Contract Policies have the exact same destination identifiers. False otherwise
        """
        return self._has_same_ids(self.dst_ids, other.dst_ids)

    def has_same_ids(self, other):
        """
        Check if the Contract Policies have the exact same source and destination identifiers
        :param other: Instance of ContractPolicy to compare against
        :return: True if the Contract Policies have the exact same source and destination identifiers. False otherwise
        """
        return self.has_same_src_ids(other) and self.has_same_dst_ids(other)


class ConfigDB(object):
    """
    Configuration Database
    """

    def __init__(self):
        self._apic_policy = None
        self._context_policy = None
        self._contract_policies = []
        self._application_policies = []
        self._epg_policies = []
        self._old_policies = []

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
        """
        Check if the configuration has an APIC policy
        :return: True if APIC policy is present. False otherwise.
        """
        return self._apic_policy is not None

    def get_apic_config(self):
        """
        Get the APIC policy
        :return: ApicPolicy instance or None if not present
        """
        return self._apic_policy

    def store_context_config(self, new_config):
        """
        Store the Context configuration in the current configuration.

        :param new_config: Config JSON
        :return: True if config has changed from previous config. False if no change.
        """
        # If no apic in new config, we just want to keep the current
        if 'vrf' not in new_config:
            return False
        # If no current Context config, then take the new config
        if not self.has_context_config():
            self._context_policy = ContextPolicy(new_config['vrf'])
            return True
        if self._context_policy == ContextPolicy(new_config['vrf']):
            return False
        self._context_policy = ContextPolicy(new_config['vrf'])
        return True

    def has_context_config(self):
        """
        Check if the configuration has a Context policy
        :return: True if Context policy is present. False otherwise.
        """
        return self._context_policy is not None

    def get_context_config(self):
        """
        Get the Context policy
        :return: ContextPolicy instance or None if not present
        """
        return self._context_policy

    def store_epg_policy(self, epg_policy):
        """
        Store the epg policy in the current configuration.

        :param epg_policy:
        :return: True if config has changed from previous config. False if no change.
        """
        epg_policy = EPGPolicy(epg_policy)
        for configured_policy in self.get_epg_policies():
            # If we already have this policy, we're done
            if configured_policy == epg_policy:
                return False
            # Check if the EPG is the same
            if configured_policy.id == epg_policy.id:
                # Something must have changed. Replace the old policy with the new one.
                self.remove_epg_policy(configured_policy)
                self.add_epg_policy(epg_policy)
                return True
        # If we get this far, we must not have the policy
        self.add_epg_policy(epg_policy)
        return True

    def remove_epg_policy(self, policy):
        """
        Remove the EPG policy
        :param policy: Instance of EPGPolicy to be removed
        :return: None
        """
        self._epg_policies.remove(policy)

    def add_epg_policy(self, policy):
        """
        Add the EPG policy
        :param policy: Instance of EPGPolicy to be added
        :return: None
        """
        self._epg_policies.append(policy)

    def get_epg_policies(self):
        """
        Get the EPG policies
        :return: List of EPGPolicy instances
        """
        return self._epg_policies

    def store_app_policy(self, app_policy):
        """
        Store the application policy in the current configuration.

        :param app_policy: dictionary containing JSON of the Application Policy
        :return: True if config has changed from previous config. False if no change.
        """
        app_policy = ApplicationPolicy(app_policy)
        for configured_policy in self.get_application_policies():
            # If we already have this policy, we're done
            if configured_policy == app_policy:
                return False
            # Check if the EPG is the same
            if configured_policy.name == app_policy.name:
                # Something must have changed. Replace the old policy with the new one.
                self.remove_application_policy(configured_policy)
                self.add_application_policy(app_policy)
                return True
        # If we get this far, we must not have the policy
        self.add_application_policy(app_policy)
        return True

    def remove_application_policy(self, policy):
        """
        Remove the application policy
        :param policy: Instance of applicationPolicy
        :return: None
        """
        self._application_policies.remove(policy)

    def add_application_policy(self, policy):
        """
        Add the application policy
        """
        self._application_policies.append(policy)

    def get_application_policies(self):
        """
        Get the application policies
        :return: List of applicationPolicy instances
        """
        return self._application_policies

    def store_contract_policy(self, contract_policy):
        """
        Store the contract policy in the current configuration.

        :param contract_policy:
        :return: True if config has changed from previous config. False if no change.
        """
        contract_policy = ContractPolicy(contract_policy)
        for configured_policy in self.get_contract_policies():
            # If we already have this policy, we're done
            if configured_policy == contract_policy:
                return False
            # Check if the EPG is the same
            if configured_policy.src_id == contract_policy.src_id and configured_policy.dst_id == contract_policy.dst_id:
                # Something must have changed. Replace the old policy with the new one.
                self.remove_contract_policy(configured_policy)
                self.add_contract_policy(contract_policy)
                return True
        # If we get this far, we must not have the policy
        self.add_contract_policy(contract_policy)
        return True

    def remove_contract_policy(self, policy):
        """
        Remove the contract policy
        :param policy: Instance of ContractPolicy
        :return: None
        """
        self._contract_policies.remove(policy)

    def add_contract_policy(self, policy):
        """
        Add the contract policy
        """
        self._contract_policies.append(policy)

    def get_contract_policies(self):
        """
        Get the contract policies
        :return: List of ContractPolicy instances
        """
        return self._contract_policies

    def store_config(self, config_json):
        """
        Store the configuration
        :param config_json: dictionary containing the configuration JSON
        :return: Boolean indicating whether the configuration has changed. True if changed. False otherwise.
        """
        config_change = False
        if 'policies' in config_json:
            for contract_policy in config_json['policies']:
                if self.store_contract_policy(contract_policy):
                    logging.debug('Contract policy config has changed.')
                    config_change = True
        if 'clusters' in config_json:
            for epg_policy in config_json['clusters']:
                if self.store_epg_policy(epg_policy):
                    logging.debug('EPG policy config has changed.')
                    config_change = True
        if 'applications' in config_json:
            for app_policy in config_json['applications']:
                if self.store_app_policy(app_policy):
                    logging.debug('Application Profile policy config has changed.')
                    config_change = True
        if self.store_apic_config(config_json):
            logging.debug('APIC config has changed.')
            config_change = True
        if self.store_context_config(config_json):
            logging.debug('Context config has changed.')
            config_change = True
        # Look for old contracts that are no longer needed
        for configured_policy in self.get_contract_policies():
            found_contract = False
            for new_policy in config_json['policies']:
                if configured_policy == ContractPolicy(new_policy):
                    found_contract = True
            if not found_contract:
                # Put the unused policy on the old policy list
                self._old_policies.append(configured_policy)
                self._contract_policies.remove(configured_policy)
                config_change = True
        return config_change


class ApicService(GenericService):
    """
    Service to communicate with the APIC
    """

    def __init__(self):
        self.cdb = ConfigDB()
        self.monitor = None
        super(ApicService, self).__init__()
        self.set_json_schema('json_schema.json')
        self._tenant_name = ''
        self._app_name = 'acitoolkitapp'
        self._use_ip_epgs = False

    def set_tenant_name(self, name):
        """
        Set the Tenant name
        :param name: String containing the Tenant name
        :return: None
        """
        self._tenant_name = name

    @property
    def tenant_name(self):
        """
        tenant name
        :return: String containing the tenant name
        """
        return self._tenant_name

    def set_app_name(self, name):
        """
        Set the Application Profile name
        :param name: String containing the Application Profile name
        :return: None
        """
        self._app_name = name

    def use_ip_epgs(self):
        self._use_ip_epgs = True

    def push_config_to_apic(self):
        """
        Push the configuration to the APIC

        :return: Requests Response instance indicating success or not
        """
        THROTTLE_SIZE = 500000 / 8
        # Set the tenant name correctly
        if self._tenant_name == '' and self.cdb.has_context_config():
            self.set_tenant_name(self.cdb.get_context_config().tenant_name)
        elif self._tenant_name == '':
            self.set_tenant_name('acitoolkit')

        # Find all the unique contract providers
        logging.debug('Finding the unique contract providers')
        unique_providers = {}
        for provided_policy in self.cdb.get_contract_policies():
            if provided_policy.dst_id not in unique_providers:
                unique_providers[provided_policy.dst_id] = 0
            else:
                unique_providers[provided_policy.dst_id] += 1
        logging.debug('Found %s unique contract providers', len(unique_providers))

        # Find any duplicate contracts that this provider is providing (remove)
        logging.debug('Finding any duplicate contracts')
        duplicate_policies = []
        for provider in unique_providers:
            for provided_policy in self.cdb.get_contract_policies():
                if provided_policy in duplicate_policies:
                    continue
                if provider in provided_policy.dst_ids:
                    for other_policy in self.cdb.get_contract_policies():
                        if other_policy == provided_policy or other_policy in duplicate_policies:
                            continue
                        if other_policy.dst_ids == provided_policy.dst_ids and other_policy.has_same_permissions(
                                provided_policy):
                            provided_policy.src_ids = provided_policy.src_ids + other_policy.src_ids
                            duplicate_policies.append(other_policy)
                            logging.debug('duplicate_policies now has %s entries', len(duplicate_policies))

        logging.debug('Removing duplicate contracts')
        for duplicate_policy in duplicate_policies:
            self.cdb.remove_contract_policy(duplicate_policy)

        if not self.displayonly:
            # Log on to the APIC
            apic_cfg = self.cdb.get_apic_config()
            apic = Session(apic_cfg.url, apic_cfg.user_name, apic_cfg.password)
            resp = apic.login()
            if not resp.ok:
                return resp

        tenant_names = []
        tenant_names.append(self._tenant_name)

        # delete all the unwanted epgs
        tenant = Tenant(self._tenant_name)
        existing_epgs = []
        if Tenant.exists(apic, tenant):
            tenants = Tenant.get_deep(
                apic,
                names=tenant_names,
                limit_to=[
                    'fvTenant',
                    'fvAp',
                    'vzFilter',
                    'vzEntry',
                    'vzBrCP',
                    'vzSubj',
                    'vzRsSubjFiltAtt'])
            tenant = tenants[0]
            appProfiles = tenant.get_children(AppProfile)
            app = appProfiles[0]
            existing_epgs = app.get_children(EPG)
        else:

            app = AppProfile(self._app_name, tenant)

        for existing_epg in existing_epgs:
            matched = False
            if existing_epg.name != "base":
                for epg_policy in self.cdb.get_epg_policies():
                    if existing_epg.descr.split(":")[1] == epg_policy.descr.split(
                            ":")[1] and existing_epg.descr.split(":")[0] == epg_policy.descr.split(":")[0]:
                        if self._use_ip_epgs:
                            if existing_epg._is_attribute_based:
                                matched = True
                                existing_criterions = existing_epg.get_children(AttributeCriterion)
                                for existing_criterion in existing_criterions:
                                    existing_criterion.mark_as_deleted()
                        elif existing_epg._is_attribute_based:
                            matched = True
                            existing_criterions = existing_epg.get_children(AttributeCriterion)
                            for existing_criterion in existing_criterions:
                                existing_criterion.mark_as_deleted()

                if not matched:
                    existing_epg.mark_as_deleted()
            else:
                if not self._use_ip_epgs:
                    base_epg = EPG('base', app)
                    if self.cdb.has_context_config():
                        context_name = self.cdb.get_context_config().name
                    else:
                        context_name = 'vrf1'
                    context = Context(context_name, tenant)
                    existing_contexts = tenant.get_children(Context)
                    for existing_context in existing_contexts:
                        if existing_context.name == context_name:
                            existing_context.mark_as_deleted()
                    existing_bds = tenant.get_children(BridgeDomain)
                    for existing_bd in existing_bds:
                        if existing_bd.name == 'bd':
                            existing_bd.mark_as_deleted()
                    base_epg.mark_as_deleted()

        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
        else:
            logging.debug('Pushing EPGS by deleting unwanted epgs ')
            if len(tenant.get_children()) > 0:
                resp = tenant.push_to_apic(apic)
                if not resp.ok:
                    return resp

        # delete all the unwanted contracts
        tenants = Tenant.get_deep(
            apic,
            names=tenant_names,
            limit_to=[
                'fvTenant',
                'fvAp',
                'vzFilter',
                'vzEntry',
                'vzBrCP',
                'vzSubj',
                'vzRsSubjFiltAtt'])
        tenant = tenants[0]
        existing_contracts = tenant.get_children(Contract)
        for existing_contract in existing_contracts:
            matched = False
            for contract_policy in self.cdb.get_contract_policies():
                if existing_contract.descr.split("::")[1] == contract_policy.descr.split(
                        "::")[1] and existing_contract.descr.split("::")[0] == contract_policy.descr.split("::")[0]:
                    matched = True
            if not matched:
                existing_contract.mark_as_deleted()
                exist_contract_providing_epgs = existing_contract.get_all_providing_epgs()
                for exist_contract_providing_epg in exist_contract_providing_epgs:
                    exist_contract_providing_epg.mark_as_deleted()
                exist_contract_consuming_epgs = existing_contract.get_all_consuming_epgs()
                for exist_contract_consuming_epg in exist_contract_consuming_epgs:
                    exist_contract_consuming_epg.mark_as_deleted()

        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
        else:
            logging.debug('Pushing contracts by deleting unwanted contracts')
            if len(tenant.get_children()) > 0:
                resp = tenant.push_to_apic(apic)
                if not resp.ok:
                    return resp

        filterEntry_list = []

        logging.debug('Generating JSON....')
        # Push all of the Contracts
        logging.debug('Pushing contracts. # of Contract policies: %s', len(self.cdb.get_contract_policies()))
        tenant = Tenant(self._tenant_name)
        if Tenant.exists(apic, tenant):
            tenants = Tenant.get_deep(
                apic,
                names=tenant_names,
                limit_to=[
                    'fvTenant',
                    'vzFilter',
                    'vzEntry',
                    'vzBrCP',
                    'vzSubj',
                    'vzRsSubjFiltAtt'])
            tenant = tenants[0]
            existing_contracts = tenant.get_children(Contract)
        else:
            existing_contracts = tenant.get_children(Contract)
        # removing the unwanted contractsubject filters for each contract subject
        for contract_policy in self.cdb.get_contract_policies():
            name = contract_policy.src_name + '::' + contract_policy.dst_name
            for existing_contract in existing_contracts:
                if existing_contract.descr.split("::")[1] == contract_policy.descr.split(
                        "::")[1] and existing_contract.descr.split("::")[0] == contract_policy.descr.split("::")[0]:
                    for child_contractSubject in existing_contract.get_children(ContractSubject):
                        for child_filter in child_contractSubject.get_filters():
                            matched = False
                            for whitelist_policy in contract_policy.get_whitelist_policies():
                                entry_name = whitelist_policy.proto + '.' + whitelist_policy.port_min + '.' + whitelist_policy.port_max
                                if child_filter.name == entry_name + '_Filter':
                                    matched = True
                                    continue
                            if not matched:
                                # TBD need to check this. this is not working
                                child_contractSubject._remove_relation(child_filter)
                                child_filter._remove_attachment(child_contractSubject)
                                logging.debug('removing filter ' + child_filter.name)

        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
        else:
            logging.debug('Pushing contracts by deleting unwanted filters')
            if len(tenant.get_children()) > 0:
                resp = tenant.push_to_apic(apic)
                if not resp.ok:
                    return resp

        # if num of contract_subjects is 0 then remove it finally
        for contract_policy in self.cdb.get_contract_policies():
            name = contract_policy.src_name + '::' + contract_policy.dst_name
            contract = Contract(name, tenant)
            contract.descr = contract_policy.descr[0:127 -
                                                   (contract_policy.descr.count('"') +
                                                    contract_policy.descr.count("'") +
                                                       contract_policy.descr.count('/'))]
            for whitelist_policy in contract_policy.get_whitelist_policies():
                entry_name = whitelist_policy.proto + '.' + whitelist_policy.port_min + '.' + whitelist_policy.port_max
                if whitelist_policy.proto == '6' or whitelist_policy.proto == '17':
                    entry = FilterEntry(entry_name,
                                        applyToFrag='no',
                                        arpOpc='unspecified',
                                        dFromPort=whitelist_policy.port_min,
                                        dToPort=whitelist_policy.port_max,
                                        etherT='ip',
                                        prot=whitelist_policy.proto,
                                        sFromPort='unspecified',
                                        sToPort='unspecified',
                                        tcpRules='unspecified',
                                        parent=contract)
                else:
                    entry = FilterEntry(entry_name,
                                        applyToFrag='no',
                                        arpOpc='unspecified',
                                        etherT='ip',
                                        prot=whitelist_policy.proto,
                                        parent=contract)
                filterEntry_list.append(entry_name)
            if not self.displayonly:
                if len(str(tenant.get_json())) > THROTTLE_SIZE:
                    logging.debug('Throttling contracts. Pushing config...')
                    resp = tenant.push_to_apic(apic)
                    if not resp.ok:
                        return resp
                    tenant = Tenant(self._tenant_name)

            if self.displayonly:
                print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
            else:
                logging.debug('Pushing remaining contracts')
                resp = tenant.push_to_apic(apic)
                if not resp.ok:
                    return resp

        # Push all of the EPGs
        logging.debug('Pushing EPGs')
        if not self.displayonly:
            tenants = Tenant.get_deep(apic, names=tenant_names)
            tenant = tenants[0]
            appProfiles = tenant.get_children(AppProfile)
            app = appProfiles[0]

        if self._use_ip_epgs:
            # Create a Base EPG
            base_epg = EPG('base', app)
            if self.cdb.has_context_config():
                context_name = self.cdb.get_context_config().name
            else:
                context_name = 'vrf1'
            context = Context(context_name, tenant)
            bd = BridgeDomain('bd', tenant)
            bd.add_context(context)
            base_epg.add_bd(bd)
            if self.displayonly:
                # If display only, just deploy the EPG to leaf 101
                base_epg.add_static_leaf_binding('101', 'vlan', '1', encap_mode='untagged')
            else:
                # Deploy the EPG to all of the leaf switches
                nodes = Node.get(apic)
                for node in nodes:
                    if node.role == 'leaf':
                        base_epg.add_static_leaf_binding(node.node, 'vlan', '1', encap_mode='untagged')

            # Create the Attribute based EPGs
            logging.debug('Creating Attribute Based EPGs')
            existing_epgs = app.get_children(EPG)
            for epg_policy in self.cdb.get_epg_policies():
                if not self.displayonly:
                    # Check if we need to throttle very large configs
                    if len(str(tenant.get_json())) > THROTTLE_SIZE:
                        resp = tenant.push_to_apic(apic)
                        if not resp.ok:
                            return resp
                        tenant = Tenant(self._tenant_name)
                        app = AppProfile(self._app_name, tenant)
                        context = Context(context_name, tenant)
                        bd = BridgeDomain('bd', tenant)
                        bd.add_context(context)
                        if self._use_ip_epgs:
                            base_epg = EPG('base', app)
                            base_epg.add_bd(bd)

                matched = False
                for existing_epg in existing_epgs:
                    if existing_epg.name != "base":
                        if existing_epg.descr.split(":")[1] == epg_policy.descr.split(
                                ":")[1] and existing_epg.descr.split(":")[0] == epg_policy.descr.split(":")[0]:
                            matched = True
                            break

                consumed_contracts = []
                provided_contracts = []
                if matched is True:
                    consumed_contracts = existing_epg.get_all_consumed()
                    provided_contracts = existing_epg.get_all_provided()
                    epg = existing_epg
                else:
                    epg = EPG(epg_policy.name, app)

                # Check if the policy has the default 0.0.0.0 IP address
                no_default_endpoint = True
                for node_policy in epg_policy.get_node_policies():
                    if node_policy.ip == '0.0.0.0' and node_policy.prefix_len == 0:
                        no_default_endpoint = False
                        epg.add_bd(bd)

                # Add all of the IP addresses
                if no_default_endpoint:
                    epg.is_attributed_based = True
                    epg.set_base_epg(base_epg)
                    criterion = AttributeCriterion('criterion', epg)
                    ipaddrs = []
                    # TBD check if the existing nodes are there in the present config,if not delete them
                    for node_policy in epg_policy.get_node_policies():
                        ipaddr = ipaddress.ip_address(unicode(node_policy.ip))
                        if not ipaddr.is_multicast:  # Skip multicast addresses. They cannot be IP based EPGs
                            ipaddrs.append(ipaddr)
                    nets = ipaddress.collapse_addresses(ipaddrs)
                    for net in nets:
                        criterion.add_ip_address(str(net))
                epg.descr = epg_policy.descr[0:127]
                # Consume and provide all of the necessary contracts
                for contract_policy in self.cdb.get_contract_policies():
                    contract = None
                    if epg_policy.id in contract_policy.src_ids:
                        name = contract_policy.src_name + '::' + contract_policy.dst_name
                        existing = False
                        for existing_consumed_contract in consumed_contracts:
                            if name == existing_consumed_contract.name:
                                existing = True
                                contract = existing_consumed_contract
                        if not existing:
                            contract = Contract(name, tenant)
                            epg.consume(contract)
                    if epg_policy.id in contract_policy.dst_ids:
                        name = contract_policy.src_name + '::' + contract_policy.dst_name
                        if contract is None:
                            existing = False
                            for existing_provided_contract in provided_contracts:
                                if name == existing_provided_contract.name:
                                    existing = True
                                    contract = existing_provided_contract
                            if not existing:
                                contract = Contract(name, tenant)
                        epg.provide(contract)
        else:
            logging.debug('Creating EPGs')
            tenants = Tenant.get_deep(apic, names=tenant_names)
            tenant = tenants[0]
            appProfiles = tenant.get_children(AppProfile)
            if len(appProfiles) > 0:
                app = appProfiles[0]
            else:
                app = AppProfile(self._app_name, tenant)

            existing_epgs = app.get_children(EPG)

            for epg_policy in self.cdb.get_epg_policies():

                matched = False
                for existing_epg in existing_epgs:
                    if existing_epg.name != "base":
                        if existing_epg.descr.split(":")[1] == epg_policy.descr.split(
                                ":")[1] and existing_epg.descr.split(":")[0] == epg_policy.descr.split(":")[0]:
                            matched = True
                            break

                consumed_contracts = []
                provided_contracts = []
                if matched is True:
                    consumed_contracts = existing_epg.get_all_consumed()
                    provided_contracts = existing_epg.get_all_provided()
                epg = EPG(epg_policy.name, app)
                epg.descr = epg_policy.descr[0:127]

                # Consume and provide all of the necessary contracts
                for contract_policy in self.cdb.get_contract_policies():
                    contract = None
                    if epg_policy.id in contract_policy.src_ids:
                        name = contract_policy.src_name + '::' + contract_policy.dst_name
                        existing = False
                        for existing_consumed_contract in consumed_contracts:
                            if name == existing_consumed_contract.name:
                                existing = True
                                contract = existing_consumed_contract
                        if not existing:
                            contract = Contract(name, tenant)
                            epg.consume(contract)
                    if epg_policy.id in contract_policy.dst_ids:
                        name = contract_policy.src_name + '::' + contract_policy.dst_name
                        if contract is None:
                            existing = False
                            for existing_provided_contract in provided_contracts:
                                if name == existing_provided_contract.name:
                                    existing = True
                                    contract = existing_provided_contract
                            if not existing:
                                contract = Contract(name, tenant)
                        epg.provide(contract)

        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
        else:
            resp = tenant.push_to_apic(apic)
            if not resp.ok:
                return resp

        # remove the unwanted filters
        existing_filters = tenant.get_children(Filter)
        for existing_filetrEntry in existing_filters:
            matched = False
            for filterEntry in filterEntry_list:
                if filterEntry + '_Filter' == existing_filetrEntry.name:
                    matched = True
            if not matched:
                existing_filetrEntry.mark_as_deleted()
        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
        else:
            resp = tenant.push_to_apic(apic)
            return resp

    def mangle_names(self):
        unique_id = 0
        name_db_by_id = {}
        for epg_policy in self.cdb.get_epg_policies():
            epg_policy.descr = epg_policy.name + ':' + epg_policy.id
            epg_policy.descr = epg_policy.replace_invalid_descr_chars(epg_policy.descr)
            if epg_policy.id in name_db_by_id:
                epg_policy.name = name_db_by_id[epg_policy.id]
            else:
                epg_policy.name = epg_policy.replace_invalid_name_chars(epg_policy.name)
                end_string = '-' + str(unique_id)
                epg_policy.name = epg_policy.name[0:30 - len(end_string)] + end_string
                unique_id += 1
                name_db_by_id[epg_policy.id] = epg_policy.name

        for contract_policy in self.cdb.get_contract_policies():
            contract_policy.descr = contract_policy.src_name + ':' + contract_policy.dst_name + '::'
            contract_policy.descr += contract_policy.src_id + ':' + contract_policy.dst_id
            contract_policy.descr = contract_policy.replace_invalid_descr_chars(contract_policy.descr)
            contract_policy.src_name = name_db_by_id[contract_policy.src_id]
            contract_policy.dst_name = name_db_by_id[contract_policy.dst_id]

    def add_config(self, config_json):
        """
        Set the configuration
        :param config_json: dictionary containing the JSN configuration
        :return: String indicating success
        """
        logging.debug('Received new config: %s', config_json)
        try:
            validate(config_json, self._json_schema, format_checker=FormatChecker())
        except ValidationError as e:
            logging.error('JSON configuration validation failed: %s', e.message)
            return 'ERROR: JSON configuration validation failed: %s' % e.message
        else:
            logging.info('JSON Validation passed')
        if self.cdb.store_config(config_json) and (self.cdb.has_apic_config() or self.displayonly):
            self.mangle_names()
            resp = self.push_config_to_apic()
        if self.displayonly or resp.ok:
            return 'OK'
        else:
            return 'ERROR:' + resp.text


def get_arg_parser():
    """
    Get the parser with the necessary arguments

    :return: Instance of argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description='ACI Configuration Deployment Tool')
    parser.add_argument('--maxlogfiles', type=int, default=10, help='Maximum number of log files (default is 10)')
    parser.add_argument('--generateconfig', action='store_true', default=False,
                        help='Generate an empty example configuration')
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


def execute_tool(args):
    """
    Main application execution

    :param args: command line arguments
    :return: None
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
    level = logging.DEBUG
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    log_file = 'apicservice.%s.log' % str(os.getpid())
    my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5 * 1024 * 1024,
                                     backupCount=args.maxlogfiles, encoding=None, delay=0)
    my_handler.setLevel(level)
    my_handler.setFormatter(log_formatter)
    logger = logging.getLogger()
    logger.addHandler(my_handler)
    logger.setLevel(level)

    logging.info('Starting the tool....')
    # Handle generating sample configuration
    try:
        if args.generateconfig:
            raise NotImplementedError
    except AttributeError:
        pass

    tool = ApicService()
    tool.displayonly = args.displayonly
    if args.tenant:
        tool.set_tenant_name(args.tenant)
    if args.app:
        tool.set_app_name(args.app)
    if args.useipepgs:
        tool.use_ip_epgs()
    return tool

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
