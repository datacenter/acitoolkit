#!/usr/bin/env python
"""
Application to push contract configuration to the APIC
"""
from acitoolkit import (Tenant, AppProfile, EPG,
                        Session, Contract, ContractSubject, Filter, FilterEntry,
                        BridgeDomain, AttributeCriterion, OutsideL3, OutsideEPG, OutsideNetwork,
                        Node, Context)
import json
import re
from jsonschema import validate, ValidationError, FormatChecker
import logging
from logging.handlers import RotatingFileHandler
import os
import ipaddress

# Imports from standalone mode
import argparse
from pprint import pprint


class GenericService(object):
    """
    Base class for services
    """

    def __init__(self):
        self._json_schema = None
        self.logger = None
        self._displayonly = False
        self.prompt = False

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
    def prompt(self):
        """
        Get the display only flag.  This will cause the JSON to be displayed but not pushed to APIC.
        """
        return self._prompt

    @prompt.setter
    def prompt(self, x):
        """
        Set the display only flag.  This will cause the JSON to be displayed but not pushed to APIC.
        """
        self._prompt = x

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
        valid_char_set = set('_.-')
        valid_name = self._replace_invalid_chars(name, valid_char_set)
        return valid_name[:63]  # valid name validators. Range: min: "1" max: "63"

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
    def cert_name(self):
        """
        Cert_Name to use to login to the APIC
        :return: String containing the cert_name
        """
        return self._policy['cert_name']

    @property
    def key(self):
        """
        Key to use to login to the APIC
        :return: String containing the key
        """
        return self._policy['key']

    @property
    def appcenter_user(self):
        """
        Appcenter_User to use to login to the APIC
        :return: String containing the appcenter_user
        """
        return self._policy['appcenter_user']

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
    
    @name.setter
    def name(self, value):
        self._policy['name'] = value

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


class RouteTagPolicy(PolicyObject):
    """
    RouteTag Policy
    """

    def __init__(self, policy):
        super(RouteTagPolicy, self).__init__(policy)

    @property
    def name(self):
        """
        route_tag name
        :return: String containing the route_tag  name
        """
        return self._policy['name']

    @property
    def subnet_mask(self):
        """
        route_tag subnet_mask address
        :return: String containing the route_tag subnet_mask
        """
        return self._policy['subnet_mask']


class EPGPolicy(PolicyObject):
    """
    EPG Policy
    """

    def __init__(self, policy):
        super(EPGPolicy, self).__init__(policy)
        self._node_policies = []
        self._populate_node_policies()
        self._populate_routeTag_policy()

    def _populate_routeTag_policy(self):
        """
        Fill in the RouteTag policy
        :return: None
        """
        self._routeTag_policy = RouteTagPolicy(self._policy['route_tag'])

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
    def external(self):
        """
        EPG external
        :return: String containing EPG external
        """
        if 'external' not in self._policy:
            return False
        return self._policy['external']

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

    def get_route_tag_policy(self):
        """
        Get the RouteTag policy
        :return: List of RouteTagPolicy instances
        """
        return self._routeTag_policy


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

    @name.setter
    def name(self, value):
        self._policy['name'] = value


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

    @name.setter
    def name(self, value):
        self._policy['name'] = value


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
        self._l3out_policies = []

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

    def add_l3out_policies(self, policy):
        """
        Add the L3out policies
        :param policy: Instance of L3out policy to be added
        :return: None
        """
        self._l3out_policies.append(policy)

    def remove_l3out_policies(self, policy):
        """
        Remove the L3out policy
        :param policy: Instance of L3out Policy to be removed
        :return: None
        """
        self._l3out_policies.remove(policy)

    def get_l3out_policies(self):
        """
        Get the L3out policies
        :return: List of L3out Policy instances
        """
        return self._l3out_policies

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
        path = os.path.dirname(os.path.realpath(__file__))
        schema_file = os.path.join(path, 'json_schema.json')
        logging.info(schema_file)
        self.set_json_schema(schema_file)
        self._tenant_name = ''
        self._app_name = 'acitoolkitapp'
        self._l3ext_name = 'L3OUT'
        self._use_ip_epgs = False
        self._use_certificate_authentication = False

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

    def set_l3ext_name(self, name):
        """
        Set the External Routed Network name
        :param name: String containing the External Routed Network name
        :return: None
        """
        self._l3ext_name = name

    def use_ip_epgs(self):
        self._use_ip_epgs = True

    def use_certificate_authentication(self):
        self._use_certificate_authentication = True

    def prompt_and_mark_as_deleted(self, apic, object_delete=None):
        '''
        if self.prompt is True, prompts for the decision and if yes the object is deleted.
        if self.prompt is False, directly object is deleted
        '''
        if self.prompt:
            logging.debug(object_delete.get_json())
            print "----------------------------------"
            pprint(object_delete.get_json())
            msg = 'do u want to delete %s : %s' % (object_delete.__class__.__name__, object_delete.name)
            shall = raw_input("%s (y/n/all) " % msg).lower()
            if shall == "all":
                self.prompt = False
                shall = 'y'
            if shall == 'y':
                print("deleting object %s : %s" % (object_delete.__class__.__name__, object_delete.name))
                logging.debug("deleting object %s : %s" % (object_delete.__class__.__name__, object_delete.name))
                object_delete.mark_as_deleted()
            else:
                print("not deleting object %s : %s" % (object_delete.__class__.__name__, object_delete.name))
        else:
            print("deleting object %s : %s" % (object_delete.__class__.__name__, object_delete.name))
            logging.debug("deleting object %s : %s" % (object_delete.__class__.__name__, object_delete.name))
            object_delete.mark_as_deleted()

    def prompt_and_remove_relation(self, apic, parentObject=None, childObject=None, relation_type=None):
        '''
        if self.prompt is True,prompts for the decision and if given yes removes the relation of child from the parent object.
        if self.prompt is False, directly removes the relation of child from parent object
        '''
        if self.prompt:
            logging.debug(parentObject.get_json())
            print "----------------------------------"
            pprint(parentObject.get_json())
            msg = 'do u want to remove relation of %s in  %s : %s' % (
                childObject.name, parentObject.__class__.__name__, parentObject.name)
            shall = raw_input("%s (y/n/all) " % msg).lower()
            if shall == "all":
                self.prompt = False
                shall = 'y'
            if shall == 'y':
                print("removing relation of %s with %s : %s" %
                      (childObject.name, parentObject.__class__.__name__, parentObject.name))
                logging.debug("removing relation of %s with %s : %s" %
                              (childObject.name, parentObject.__class__.__name__, parentObject.name))
                if relation_type == 'provided':
                    parentObject.dont_provide(childObject)
                elif relation_type == 'consumed':
                    parentObject.dont_consume(childObject)
                else:
                    parentObject._remove_relation(childObject)
            else:
                print("not removing relation of %s with %s : %s" %
                      (childObject.name, parentObject.__class__.__name__, parentObject.name))
        else:
            logging.debug("removing relation of %s with %s : %s" %
                          (childObject.name, parentObject.__class__.__name__, parentObject.name))
            print("removing relation of %s with %s : %s" %
                  (childObject.name, parentObject.__class__.__name__, parentObject.name))
            if relation_type == 'provided':
                parentObject.dont_provide(childObject)
            elif relation_type == 'consumed':
                parentObject.dont_consume(childObject)
            else:
                parentObject._remove_relation(childObject)

    def remove_duplicate_contracts(self):
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

    def seperate_epgs_with_external(self):
        '''
        moves all the EpgPolicies with external True to l3out_policies
        '''
        for epg_policy in self.cdb.get_epg_policies():
            if epg_policy.external is True:
                self.cdb.add_l3out_policies(epg_policy)

        for epg_policy in self.cdb.get_l3out_policies():
            self.cdb.remove_epg_policy(epg_policy)
            
    def removing_unwanted_app_profiles(self,apic):
        '''
        deletes the unwanted appProfiles
        '''
        tenant_names = [self._tenant_name]
        tenant = Tenant(self._tenant_name)
        if Tenant.exists(apic, tenant):
            tenants = Tenant.get_deep(
                apic,
                names=tenant_names,
                limit_to=[
                    'fvTenant',
                    'fvAp'
                    ])
            tenant = tenants[0]
            existing_appProfiles = tenant.get_children(AppProfile)
            for existing_appProfile in existing_appProfiles:
                if existing_appProfile.name != self._app_name:
                    existing_appProfile.mark_as_deleted()
                    
            if self.displayonly:
                print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
                return 'OK'
            else:
                logging.debug('Pushing contracts by deleting unwanted app profiles')
                resp = tenant.push_to_apic(apic)
                if resp.ok:
                    return 'OK'
                else:
                    return resp.text
        else:
            return 'OK'
        
    def delete_unwanted_contracts(self, apic):
        '''
        deletes the Contracts which are not in the present config['policies']
        '''
        tenant_names = [self._tenant_name]
        tenant = Tenant(self._tenant_name)
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
                    'vzRsSubjFiltAtt',
                    'l3extInstP',
                    'l3extOut',
                    'l3extSubnet'])
            tenant = tenants[0]
            existing_contracts = tenant.get_children(Contract)
            for existing_contract in existing_contracts:
                matched = False
                for contract_policy in self.cdb.get_contract_policies():
                    contract_policy.descr = contract_policy.descr[0:127 -
                                                                  (contract_policy.descr.count('"') +
                                                                   contract_policy.descr.count("'") +
                                                                   contract_policy.descr.count('/'))]
                    if "::" in existing_contract.descr and "::" in contract_policy.descr :
                        if existing_contract.descr.split("::")[1] == contract_policy.descr.split(
                                "::")[1] and existing_contract.descr.split("::")[0] == contract_policy.descr.split("::")[0]:
                            matched = True
                if not matched:
                    self.prompt_and_mark_as_deleted(apic, existing_contract)
                    exist_contract_providing_epgs = existing_contract.get_all_providing_epgs()
                    for exist_contract_providing_epg in exist_contract_providing_epgs:
                        self.prompt_and_remove_relation(
                            apic, exist_contract_providing_epg, existing_contract, 'provided')
                    exist_contract_consuming_epgs = existing_contract.get_all_consuming_epgs()
                    for exist_contract_consuming_epg in exist_contract_consuming_epgs:
                        self.prompt_and_remove_relation(
                            apic, exist_contract_consuming_epg, existing_contract, 'consumed')
            if self.displayonly:
                print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
                return 'OK'
            else:
                logging.debug('Pushing contracts by deleting unwanted contracts')
                resp = tenant.push_to_apic(apic)
                if resp.ok:
                    return 'OK'
                else:
                    return resp.text
        else:
            return 'OK'

    def removing_unwanted_filter_relations(self, apic):
        '''
        deletes the filter relations in contracts which are not in the present config['policies']
        '''
        # if num of contract_subjects is 0 then remove it finally
        tenant_names = [self._tenant_name]
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
            existing_contracts = []
        # removing the unwanted contractsubject filters for each contract subject
        for contract_policy in self.cdb.get_contract_policies():
            for existing_contract in existing_contracts:
                if existing_contract.descr != "" and "::" in existing_contract.descr and "::" in contract_policy.descr :
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
                                    self.prompt_and_remove_relation(apic, child_contractSubject, child_filter)
        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
            return 'OK'
        else:
            logging.debug('Pushing contracts by deleting unwanted filters')
            resp = tenant.push_to_apic(apic)
            if resp.ok:
                return 'OK'
            else:
                return resp.text

    def push_remaining_contracts_along_with_filters(self, apic, THROTTLE_SIZE):
        '''
        pushing the contracts in config['policies']
        if the tenant doesnot exist, then all the policies(contracts) are pushed to apic.
        if the tenant exists, then only the policies(contracts) which are not existing are pushed to apic
        '''
        self.filterEntry_list = []
        tenant_names = [self._tenant_name]
        tenant = Tenant(self._tenant_name)
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
            existing_contracts = tenant.get_children(Contract)
        else:
            existing_contracts = []
        for contract_policy in self.cdb.get_contract_policies():
            matched = False
            for existing_contract in existing_contracts:
                if "::" in existing_contract.descr and "::" in contract_policy.descr:
                    if existing_contract.descr != "" and existing_contract.descr.split("::")[1] == contract_policy.descr.split(
                            "::")[1] and existing_contract.descr.split("::")[0] == contract_policy.descr.split("::")[0]:
                        matched = True
                        break
            child_filters = []
            if matched:
                contract = existing_contract
                for child_contractSubject in contract.get_children(ContractSubject):
                    child_filters = child_contractSubject.get_filters()
            else:
                name = contract_policy.src_name + '::' + contract_policy.dst_name
                contract = Contract(name, tenant)
                contract.descr = contract_policy.descr[0:127 -
                                                       (contract_policy.descr.count('"') +
                                                        contract_policy.descr.count("'") +
                                                        contract_policy.descr.count('/'))]
                if self.prompt:
                    pprint(contract.get_json())
                    msg = "do u want to add a new contract %s" % name
                    shall = raw_input("%s (y/n/all) " % msg).lower()
                    if shall == "all":
                        self.prompt = False
                        shall = 'y'
                    if shall == 'y':
                        print("adding a new contract " + name)
                        logging.debug("adding a new contract " + name)
                    else:
                        contract.mark_as_deleted()
                        print("not adding a new contract " + name)
            for whitelist_policy in contract_policy.get_whitelist_policies():
                entry_name = whitelist_policy.proto + '.' + whitelist_policy.port_min + '.' + whitelist_policy.port_max
                self.filterEntry_list.append(entry_name)
                filter_not_exists = True
                for child_filter in child_filters:
                    if child_filter.name == entry_name + '_Filter':
                        filter_not_exists = False
                if filter_not_exists:
                    if self.prompt:
                        print "----------------------------------"
                        pprint(contract.get_json())
                        msg = "do u want to add a new filter relation %s in contract %s " % (entry_name, contract.name)
                        shall = raw_input("%s (y/n/all) " % msg).lower()
                        if shall == "all":
                            self.prompt = False
                            shall = 'y'
                        if shall != 'y':
                            print("not adding a new filter relation %s for contract %s" % (entry_name, contract.name))
                            logging.debug(
                                "not adding a new filter relation %s for contract %s" %
                                (entry_name, contract.name))
                            break
                        else:
                            print("adding a new filter for contract " + entry_name)
                    logging.debug("adding a new filter for contract " + entry_name)
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
            if not self.displayonly:
                if len(str(tenant.get_json())) > THROTTLE_SIZE:
                    logging.debug('Throttling contracts. Pushing config...')
                    resp = tenant.push_to_apic(apic)
                    if not resp.ok:
                        return resp.content
                    tenant = Tenant(self._tenant_name)
        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
            return 'OK'
        else:
            logging.debug('Pushing remaining contracts')
            resp = tenant.push_to_apic(apic)
            if resp.ok:
                return 'OK'
            else:
                return resp.text

    def removing_unwanted_filters(self, apic):
        '''
        deleting the filters which are not in any of the whitelist_policies of the present config['policies']
        '''
        tenants = Tenant.get_deep(apic, names=[self._tenant_name], limit_to=['fvTenant', 'vzFilter', 'vzEntry'])
        if len(tenants) > 0:
            tenant = tenants[0]
            existing_Filters = []
            existing_Filters = tenant.get_children(Filter)
            for existing_filter in existing_Filters:
                matched = False
                for filterEntry in self.filterEntry_list:
                    if filterEntry + '_Filter' == existing_filter.name:
                        matched = True
                        break
                if not matched:
                    self.prompt_and_mark_as_deleted(apic, existing_filter)
            if self.displayonly:
                print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
                return 'OK'
            else:
                resp = tenant.push_to_apic(apic)
                if resp.ok:
                    return 'OK'
                else:
                    return resp.text

    def consume_and_provide_contracts_for_epgs(self, epg_policy, epg, tenant):
        '''
        for epgs creates all the providing and consuming contracts
        '''
        consumed_contracts = epg.get_all_consumed()
        provided_contracts = epg.get_all_provided()
        for contract_policy in self.cdb.get_contract_policies():
            contract = None
            if epg_policy.id in contract_policy.src_ids:
                name = contract_policy.src_name + '::' + contract_policy.dst_name
                pattern = re.escape(re.match(r"(.*)-(.*)", contract_policy.src_name).group(1))
                pattern += r"-\d+::"
                pattern += re.escape(re.match(r"(.*)-(.*)", contract_policy.dst_name).group(1))
                pattern += r"-\d+"
                existing = False
                for existing_consumed_contract in consumed_contracts:
                    if re.search(pattern, existing_consumed_contract.name, re.IGNORECASE):
                        existing = True
                        contract = existing_consumed_contract
                if not existing:
                    if self.prompt:
                        msg = "do u want to add a new consuming contract %s for EPG %s" % (name, epg)
                        shall = raw_input("%s (y/n/all) " % msg).lower()
                        if shall == "all":
                            self.prompt = False
                            shall = 'y'
                        if shall == 'y':
                            contract = Contract(name, tenant)
                            epg.consume(contract)
                            logging.debug("adding a consuming contract %s for EPG %s " % (name, epg_policy.name))
                            print("adding a consuming contract %s for EPG %s " % (name, epg_policy.name))
                        else:
                            print("not adding a consuming contract %s for EPG %s " % (name, epg_policy.name))
                    else:
                        print("adding a consuming contract %s for EPG %s " % (name, epg_policy.name))
                        logging.debug("adding a consuming contract %s for EPG %s " % (name, epg_policy.name))
                        contract = Contract(name, tenant)
                        epg.consume(contract)
            if epg_policy.id in contract_policy.dst_ids:
                name = contract_policy.src_name + '::' + contract_policy.dst_name
                pattern = re.escape(re.match(r"(.*)-(.*)", contract_policy.src_name).group(1))
                pattern += r"-\d+::"
                pattern += re.escape(re.match(r"(.*)-(.*)", contract_policy.dst_name).group(1))
                pattern += r"-\d+"
                if contract is None:
                    existing = False
                    for existing_provided_contract in provided_contracts:
                        if re.search(pattern, existing_provided_contract.name, re.IGNORECASE):
                            existing = True
                            contract = existing_provided_contract
                    if not existing:
                        if self.prompt:
                            msg = "do u want to add a new consuming contract %s for EPG %s" % (name, epg)
                            shall = raw_input("%s (y/n/all) " % msg).lower()
                            if shall == "all":
                                self.prompt = False
                                shall = 'y'
                            if shall == 'y':
                                contract = Contract(name, tenant)
                                logging.debug(
                                    "adding a providing contract %s for EPG %s " %
                                    (name, epg_policy.name))
                                print(
                                    "adding a providing contract %s for EPG %s " %
                                    (name, epg_policy.name))
                            else:
                                logging.debug(
                                    "not adding a providing contract %s for EPG %s " %
                                    (name, epg_policy.name))
                        else:
                            print("adding a providing contract %s for EPG %s " % (name, epg_policy.name))
                            logging.debug("adding a providing contract %s for EPG %s " % (name, epg_policy.name))
                            contract = Contract(name, tenant)
                epg.provide(contract)

    def pushing_l3outs(self, tenant, outside_l3):
        '''
        pushing the epgs to L3OUT in config['clusters'] which have external flag set to true
        if the tenant doesnot exist, then all the policies(l3out_epgs) are pushed to apic.
        if the tenant exists, then only the policies(egs) with exteranl true which are not existing are pushed to apic
        '''
        for l3out_epg_policy in self.cdb.get_l3out_policies():
            outsideEPG = OutsideEPG(l3out_epg_policy.name, outside_l3)
            outsideEPG.descr = l3out_epg_policy.descr[0:127]

            ipaddrs = []
            for node_policy in l3out_epg_policy.get_node_policies():
                ipaddrs = []
                ipaddr = ipaddress.ip_address(unicode(node_policy.ip))
                # if not ipaddr.is_multicast:
                ipaddrs.append(ipaddr)
                nets = ipaddress.collapse_addresses(ipaddrs)
                for net in nets:
                    logging.debug(
                        "adding outsideNetwork with ip address  %s to EPG %s " %
                        (str(net), l3out_epg_policy.name))
                    outsideNetwork = OutsideNetwork(node_policy.name, outsideEPG)
                    if node_policy.ip == '0.0.0.0':
                        outsideNetwork.set_addr(str(node_policy.ip))
                    else:
                        outsideNetwork.set_addr(str(net))

            for contract_policy in self.cdb.get_contract_policies():
                contract = None
                if l3out_epg_policy.id in contract_policy.src_ids:
                    name = contract_policy.src_name + '::' + contract_policy.dst_name
                    contract = Contract(name, tenant)
                    outsideEPG.consume(contract)
                    logging.debug("adding a consuming contract %s for OutsideEPG %s " % (name, l3out_epg_policy.name))
                if l3out_epg_policy.id in contract_policy.dst_ids:
                    name = contract_policy.src_name + '::' + contract_policy.dst_name
                    if contract is None:
                        contract = Contract(name, tenant)
                    outsideEPG.provide(contract)
                    logging.debug("adding a providing contract %s for OutsideEPG %s " % (name, l3out_epg_policy.name))

    def pushing_epgs(self, apic, tenant, app, THROTTLE_SIZE):
        '''
        pushing the contracts in config['epgs']
        if the tenant doesnot exist, then all the policies(epgs) are pushed to apic.
        if the tenant exists, then only the policies(epgs) which are not existing are pushed to apic
        '''
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
            for epg_policy in self.cdb.get_epg_policies():
                if not self.displayonly:
                    # Check if we need to throttle very large configs
                    if len(str(tenant.get_json())) > THROTTLE_SIZE:
                        resp = tenant.push_to_apic(apic)
                        if not resp.ok:
                            return resp.content
                        tenant = Tenant(self._tenant_name)
                        app = AppProfile(self._app_name, tenant)
                        context = Context(context_name, tenant)
                        bd = BridgeDomain('bd', tenant)
                        bd.add_context(context)
                        if self._use_ip_epgs:
                            base_epg = EPG('base', app)
                            base_epg.add_bd(bd)
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

                    route_tag_policy = epg_policy.get_route_tag_policy()
                    ipnetwork = ipaddress.ip_network(unicode(route_tag_policy.subnet_mask))

                    for node_policy in epg_policy.get_node_policies():
                        ipaddr = ipaddress.ip_address(unicode(node_policy.ip))
                        # Skip multicast addresses and broadcast address. They cannot be IP based EPGs
                        if ipnetwork.broadcast_address != ipaddr and not ipaddr.is_multicast:
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
                        contract = Contract(name, tenant)
                        epg.consume(contract)
                        logging.debug("adding a consuming contract %s for EPG %s " % (name, epg_policy.name))
                    if epg_policy.id in contract_policy.dst_ids:
                        name = contract_policy.src_name + '::' + contract_policy.dst_name
                        if contract is None:
                            contract = Contract(name, tenant)
                        epg.provide(contract)
                        logging.debug("adding a providing contract %s for EPG %s " % (name, epg_policy.name))
        else:
            logging.debug('Creating EPGs')
            for epg_policy in self.cdb.get_epg_policies():
                epg = EPG(epg_policy.name, app)
                epg.descr = epg_policy.descr[0:127]
                # Consume and provide all of the necessary contracts
                for contract_policy in self.cdb.get_contract_policies():
                    contract = None
                    if epg_policy.id in contract_policy.src_ids:
                        name = contract_policy.src_name + '::' + contract_policy.dst_name
                        contract = Contract(name, tenant)
                        epg.consume(contract)
                        logging.debug("adding a consuming contract %s for EPG %s " % (name, epg_policy.name))
                    if epg_policy.id in contract_policy.dst_ids:
                        name = contract_policy.src_name + '::' + contract_policy.dst_name
                        if contract is None:
                            contract = Contract(name, tenant)
                        epg.provide(contract)
                        logging.debug("adding a providing contract %s for EPG %s " % (name, epg_policy.name))

    def pushing_remaining_epgs(self, tenant, app, bd=None, base_epg=None):
        '''
        pushing the contracts in config['epgs']
        if the tenant doesnot exist, then all the policies(epgs) are pushed to apic.
        if the tenant exists, then only the policies(epgs) which are not existing are pushed to apic
        '''
        existing_epgs = app.get_children(EPG)
        for epg_policy in self.cdb.get_epg_policies():
            matched = False
            for existing_epg in existing_epgs:
                if existing_epg.name != "base":
                    if ":" in existing_epg.descr and ":" in epg_policy.descr:
                        if existing_epg.descr.split(":")[1] == epg_policy.descr.split(
                                ":")[1] and existing_epg.descr.split(":")[0] == epg_policy.descr.split(":")[0]:
                            matched = True
                            break

            if matched is True:
                epg = existing_epg
            else:
                epg = EPG(epg_policy.name, app)
                epg.descr = epg_policy.descr[0:127]
                if self.prompt:
                    print "----------------------------------"
                    pprint(epg.get_json())
                    msg = "do u want to add a new EPG %s" % epg_policy.name
                    shall = raw_input("%s (y/n/all) " % msg).lower()
                    if shall == "all":
                        self.prompt = False
                        shall = 'y'
                    if shall != 'y':
                        epg.mark_as_deleted()
                        print("not adding a new epg " + epg_policy.name)
                        continue
                    else:
                        print("adding a new epg " + epg_policy.name)
                        logging.debug("adding a new epg " + epg_policy.name)
            if self._use_ip_epgs:
                no_default_endpoint = True
                for node_policy in epg_policy.get_node_policies():
                    if node_policy.ip == '0.0.0.0' and node_policy.prefix_len == 0:
                        no_default_endpoint = False
                        epg.add_bd(bd)
                # Add all of the IP addresses
                if no_default_endpoint:
                    if not epg.is_attributed_based:
                        epg.is_attributed_based = True
                        epg.set_base_epg(base_epg)
                        criterion = AttributeCriterion('criterion', epg)
                    else:
                        existing_criterions = epg.get_children(AttributeCriterion)
                        if len(existing_criterions) > 0:
                            criterion = existing_criterions[0]
                        else:
                            criterion = AttributeCriterion('criterion', epg)
                    ipaddrs = []
                    for node_policy in epg_policy.get_node_policies():
                        ipaddr = ipaddress.ip_address(unicode(node_policy.ip))
                        if not ipaddr.is_multicast:  # Skip multicast addresses. They cannot be IP based EPGs
                            ipaddrs.append(ipaddr)
                    nets = ipaddress.collapse_addresses(ipaddrs)
                    for net in nets:
                        existing_ip_address = criterion.get_ip_addresses()
                        if not str(net) in existing_ip_address:
                            if self.prompt:
                                print "----------------------------------"
                                pprint(epg.get_json())
                                msg = "do u want to add attribute Criterion with ip address %s to EPG %s " % (
                                    str(net), epg.name)
                                shall = raw_input("%s (y/n/all) " % msg).lower()
                                if shall == "all":
                                    self.prompt = False
                                    shall = 'y'
                                if shall == 'y':
                                    logging.debug(
                                        "adding attribute Criterion with ip address  %s to EPG %s " %
                                        (str(net), epg_policy.name))
                                    print(
                                        "adding attribute Criterion with ip address  %s to EPG %s " %
                                        (str(net), epg_policy.name))
                                    criterion.add_ip_address(str(net))
                                else:
                                    print(
                                        "not adding attribute Criterion with ip address  %s to EPG %s " %
                                        (str(net), epg_policy.name))
                            else:
                                logging.debug(
                                    "adding attribute Criterion with ip address  %s to EPG %s " %
                                    (str(net), epg_policy.name))
                                print(
                                    "adding attribute Criterion with ip address  %s to EPG %s " %
                                    (str(net), epg_policy.name))
                                criterion.add_ip_address(str(net))
                epg.descr = epg_policy.descr[0:127]
            self.consume_and_provide_contracts_for_epgs(epg_policy, epg, tenant)

    def _replace_invalid_chars(self, name, valid_char_set):
        stripped_name = ''
        name_len = 0
        for char in name:
            if name_len < 63:  # valid name validators. Range: min: "1" max: "63"
                if char not in valid_char_set and not char.isalnum():
                    stripped_name += '_'
                else:
                    stripped_name += char
                name_len = name_len + 1
        return stripped_name

    def replace_invalid_name_chars(self):
        valid_char_set = set('_.-')
        self._tenant_name = self._replace_invalid_chars(self._tenant_name, valid_char_set)
        self._app_name = self._replace_invalid_chars(self._app_name, valid_char_set)
        self._l3ext_name = self._replace_invalid_chars(self._l3ext_name, valid_char_set)

    def push_config_to_apic(self):
        """
        Push the configuration to the APIC
        :return: Requests Response instance indicating success or not
        """
        THROTTLE_SIZE = 500000 / 8
        tenant_created = False
        app_created = False
        # Set the tenant name correctly
        if self._tenant_name == '' and self.cdb.has_context_config():
            self.set_tenant_name(self.cdb.get_context_config().tenant_name)
        elif self._tenant_name == '':
            self.set_tenant_name('acitoolkit')
        logging.debug('Removing invalid characters in tenant_name, app_name, l3ext_name')
        self.replace_invalid_name_chars()

        logging.debug('Removing duplicate contracts')
        self.remove_duplicate_contracts()

        logging.debug("moving epgs with external true")
        self.seperate_epgs_with_external()

        # Log on to the APIC
        apic_cfg = self.cdb.get_apic_config()
        if self._use_certificate_authentication:
            apic = Session(apic_cfg.url, apic_cfg.user_name, cert_name=apic_cfg.cert_name,
                        key=apic_cfg.key, appcenter_user=apic_cfg.appcenter_user,
                        subscription_enabled=False)
        else:
            apic = Session(apic_cfg.url, apic_cfg.user_name, apic_cfg.password)
            resp = apic.login()
            if not resp.ok:
                return resp.text

        tenant = Tenant(self._tenant_name)
        if not Tenant.exists(apic, tenant):
            # when adding tenant for the first time, all the config is added so prompt is made false
            print ("tenant doesnot exist. so adding all the config without showing the prompt ")
            self.prompt = False
            tenant_created = True

        # delete all the unused or not existing contracts in the present config
        logging.debug('Deleting unused or not existing contracts in the present config')
        resp = self.delete_unwanted_contracts(apic)
        if not resp == 'OK':
            return resp

        logging.debug('Deleting unused or not existing filter relations from contractSubjects in the present config')
        resp = self.removing_unwanted_filter_relations(apic)
        if not resp == 'OK':
            return resp

        # pushing remaining contracts
        logging.debug('Pushing remaining contracts along with filters relations')
        resp = self.push_remaining_contracts_along_with_filters(apic, THROTTLE_SIZE)
        if not resp == 'OK':
            return resp
        
        '''
        # delete unwanted appProfiles
        logging.debug('delete unwanted appProfiles')
        resp = self.removing_unwanted_app_profiles(apic)
        if not resp == 'OK':
            return resp
        '''

        # Push remaining EPGs
        tenant_names = [self._tenant_name]
        logging.debug('Pushing EPGs')
        tenants = Tenant.get_deep(apic, names=tenant_names)
        tenant = tenants[0]
        appProfiles = tenant.get_children(AppProfile)
        existing_epgs = []
        app = None
        if len(appProfiles) > 0:
            for appProfile in appProfiles:
                if appProfile.name == self._app_name:
                    app = appProfile
                    existing_epgs = appProfile.get_children(EPG)
                    
        if app is None:
            app = AppProfile(self._app_name, tenant)
            app_created = True

        if len(self.cdb.get_epg_policies()) > 0:
            if tenant_created or app_created:
                self.pushing_epgs(apic, tenant, app, THROTTLE_SIZE)
            else:
                for epg_policy in self.cdb.get_epg_policies():
                    matched = False
                    for existing_epg in existing_epgs:
                        if existing_epg.name != "base":
                            if ":" in existing_epg.descr and ":" in epg_policy.descr :
                                if existing_epg.descr.split(":")[1] == epg_policy.descr.split(
                                        ":")[1] and existing_epg.descr.split(":")[0] == epg_policy.descr.split(":")[0]:
                                    matched = True
                                    break

                    if matched is True:
                        epg = existing_epg
                        self.consume_and_provide_contracts_for_epgs(epg_policy, epg, tenant)
                        if not self.displayonly:
                            # Check if we need to throttle very large configs
                            if len(str(tenant.get_json())) > THROTTLE_SIZE:
                                resp = tenant.push_to_apic(apic)
                                if not resp.ok:
                                    return resp.content
                                tenants = Tenant.get_deep(apic, names=tenant_names)
                                tenant = tenants[0]
                                appProfiles = tenant.get_children(AppProfile)
                                for appProfile in appProfiles:
                                    if appProfile.name == self._app_name:
                                        app = appProfile
                                        existing_epgs = app.get_children(EPG)

        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
            return 'OK'
        else:
            resp = tenant.push_to_apic(apic)
            if not resp.ok:
                return resp.text

        # pushing remaining l3outs
        tenants = Tenant.get_deep(apic, names=tenant_names)
        tenant = tenants[0]
        outsideL3s = tenant.get_children(OutsideL3)
        if tenant_created:
            outside_l3 = OutsideL3(self._l3ext_name, tenant)
            self.pushing_l3outs(tenant, outside_l3)
        else:
            for outsideL3 in outsideL3s:
                if outsideL3.name == self._l3ext_name:
                    existing_outside_epgs = outsideL3.get_children(OutsideEPG)
                    for l3out_epg_policy in self.cdb.get_l3out_policies():
                        matched = False
                        for existing_outside_epg in existing_outside_epgs:
                            if ":" in existing_outside_epg.descr and ":" in l3out_epg_policy.descr :
                                if existing_outside_epg.descr.split(":")[1] == l3out_epg_policy.descr.split(
                                        ":")[1] and existing_outside_epg.descr.split(":")[0] == l3out_epg_policy.descr.split(":")[0]:
                                    matched = True
                                    break
                        if matched is True:
                            epg = existing_outside_epg
                            self.consume_and_provide_contracts_for_epgs(l3out_epg_policy, epg, tenant)
                            if not self.displayonly:
                                # Check if we need to throttle very large configs
                                if len(str(tenant.get_json())) > THROTTLE_SIZE:
                                    resp = tenant.push_to_apic(apic)
                                    if not resp.ok:
                                        return resp.content
                                    tenants = Tenant.get_deep(apic, names=tenant_names)
                                    tenant = tenants[0]
                                    outsideL3s = tenant.get_children(OutsideL3)
                                    for outsideL3 in outsideL3s:
                                        if outsideL3.name == self._l3ext_name:
                                            existing_outside_epgs = outsideL3.get_children(OutsideEPG)
                        else:
                            logging.debug('EPG doesnot exist %s ' % (l3out_epg_policy.name))
                            print("EPG doesnot exist " + l3out_epg_policy.name)

        if self.displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
            return 'OK'
        else:
            resp = tenant.push_to_apic(apic)
            if not resp.ok:
                return resp.text

        # remove the unwanted filters
        logging.debug('Deleting the unused or not existing Filters in the present config')
        return self.removing_unwanted_filters(apic)

    def mangle_names(self):
        unique_id = 0
        name_db_by_id = {}
        if not self.cdb._context_policy is None:
            context_policy = self.cdb._context_policy
            context_policy.name = context_policy.replace_invalid_name_chars(context_policy.name)
        for application_policy in self.cdb.get_application_policies():
            application_policy.name = application_policy.replace_invalid_name_chars(application_policy.name)
        for epg_policy in self.cdb.get_epg_policies():
            epg_policy.descr = epg_policy.name + ':' + epg_policy.id
            epg_policy.descr = epg_policy.replace_invalid_descr_chars(epg_policy.descr)
            if epg_policy.id in name_db_by_id:
                epg_policy.name = name_db_by_id[epg_policy.id]
            else:
                epg_policy.name = epg_policy.replace_invalid_name_chars(epg_policy.name)
                end_string = '-' + str(unique_id)
                epg_policy.name = epg_policy.name[0:27 - len(end_string)] + end_string
                unique_id += 1
                name_db_by_id[epg_policy.id] = epg_policy.name
                
            for node_policy in epg_policy.get_node_policies():
                node_policy.name = node_policy.replace_invalid_name_chars(node_policy.name)
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
        if self.displayonly or resp == 'OK':
            return 'OK'
        else:
            return 'ERROR:' + resp


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
    tool.prompt = args.prompt
    if args.tenant:
        tool.set_tenant_name(args.tenant)
    if args.app:
        tool.set_app_name(args.app)
    if args.l3ext:
        tool.set_l3ext_name(args.l3ext)
    if args.useipepgs:
        tool.use_ip_epgs()
    try:
        if args.appcenter:
            tool.use_certificate_authentication()
    except AttributeError:
        # Silently handle no appcenter argument
        pass
    return tool
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
