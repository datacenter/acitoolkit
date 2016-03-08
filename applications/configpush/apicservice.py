#!/usr/bin/env python
"""
Application to push contract configuration to the APIC
"""
from acitoolkit.acitoolkit import (Tenant, AppProfile, EPG,
                                   Session, Contract, FilterEntry,
                                   BridgeDomain, AttributeCriterion)
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

    def setup_logging(self, logging_level, max_log_files):
        """
        Set the logger level

        :param logging_level: String containing the logger level.
                              Expected values are 'verbose', 'warnings',
                              'critical'
        :param max_log_files: Integer containing the maximum number of log
                              files to keep
        :return: None
        """
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
        log_file = 'apicintegration.%s.log' % str(os.getpid())
        my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024,
                                         backupCount=max_log_files, encoding=None, delay=0)
        my_handler.setLevel(level)
        my_handler.setFormatter(log_formatter)
        logger = logging.getLogger()
        logger.addHandler(my_handler)
        logger.setLevel(level)

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

    def set_displayonly(self):
        """
        Set the display only flag.  This will cause the JSON to be displayed but not pushed to APIC.
        :return: None
        """
        self._displayonly = True


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

    @property
    def src_name(self):
        return self._policy['src_name']

    def get_node_policies(self):
        """
        Get the Node policies
        :return: List of NodePolicy instances
        """
        return self._node_policies


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

    @property
    def dst_name(self):
        """
        Get the destination name
        :return: String containing the destination name
        """
        return self._policy['dst_name']

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
        self._contract_policies = []
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
        Get the APIC policies
        :return: List of APICPolicy instances
        """
        return self._apic_policy

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
                self.remove_epg_policy(epg_policy)
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
                self.remove_contract_policy(contract_policy)
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
        if self.store_apic_config(config_json):
            logging.debug('APIC config has changed.')
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
        self._tenant_name = 'acitoolkit'
        self._app_name = 'acitoolkitapp'

    def set_tenant_name(self, name):
        """
        Set the Tenant name
        :param name: String containing the Tenant name
        :return: None
        """
        self._tenant_name = name

    def set_app_name(self, name):
        """
        Set the Application Profile name
        :param name: String containing the Application Profile name
        :return: None
        """
        self._app_name = name

    def push_config_to_apic(self):
        """
        Push the configuration to the APIC

        :return: Requests Response instance indicating success or not
        """
        # Find all the unique contract providers
        unique_providers = {}
        for provided_policy in self.cdb.get_contract_policies():
            if provided_policy.dst_id not in unique_providers:
                unique_providers[provided_policy.dst_id] = 0
            else:
                unique_providers[provided_policy.dst_id] += 1

        # Find any duplicate contracts that this provider is providing (remove)
        duplicate_policies = []
        for provider in unique_providers:
            for provided_policy in self.cdb.get_contract_policies():
                if provided_policy in duplicate_policies:
                    continue
                if provider in provided_policy.dst_ids:
                    for other_policy in self.cdb.get_contract_policies():
                        if other_policy == provided_policy or other_policy in duplicate_policies:
                            continue
                        if other_policy.dst_ids == provided_policy.dst_ids and other_policy.has_same_permissions(provided_policy):
                            provided_policy.src_ids = provided_policy.src_ids + other_policy.src_ids
                            duplicate_policies.append(other_policy)

        for duplicate_policy in duplicate_policies:
            self.cdb.remove_contract_policy(duplicate_policy)

        # Log on to the APIC
        apic_cfg = self.cdb.get_apic_config()
        apic = Session(apic_cfg.url, apic_cfg.user_name, apic_cfg.password)
        resp = apic.login()
        if not resp.ok:
            return resp

        # Push all of the Contracts
        tenant = Tenant(self._tenant_name)
        for contract_policy in self.cdb.get_contract_policies():
            name = contract_policy.src_id + '::' + contract_policy.dst_id
            descr = contract_policy.src_name + '::' + contract_policy.dst_name
            contract = Contract(name, tenant)
            contract.descr = descr
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
                                        sFromPort='1',
                                        sToPort='65535',
                                        tcpRules='unspecified',
                                        parent=contract)
                else:
                    entry = FilterEntry(entry_name,
                                        applyToFrag='no',
                                        arpOpc='unspecified',
                                        etherT='ip',
                                        prot=whitelist_policy.proto,
                                        parent=contract)
        if self._displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
        else:
            resp = tenant.push_to_apic(apic)
            if not resp.ok:
                return resp

        # Push all of the EPGs
        if not self._displayonly:
            tenant = Tenant(self._tenant_name)
        app = AppProfile(self._app_name, tenant)
        # Create a Base EPG
        base_epg = EPG('base', app)
        bd = BridgeDomain('bd', tenant)
        base_epg.add_bd(bd)
        # TODO: Send to all of the current nodes
        base_epg.add_static_leaf_binding('101', 'vlan', '1', encap_mode='untagged')

        # Create the Attribute based EPGs
        for epg_policy in self.cdb.get_epg_policies():
            epg = EPG(epg_policy.id, app)

            # Add all of the IP addresses
            epg.is_attributed_based = True
            epg.set_base_epg(base_epg)
            criterion = AttributeCriterion('criterion', epg)
            for node_policy in epg_policy.get_node_policies():
                ipaddr = ipaddress.ip_address(unicode(node_policy.ip))
                if ipaddr.is_multicast:
                    # Skip multicast addresses. They cannot be IP based EPGs
                    continue
                criterion.add_ip_address(node_policy.ip)

            epg.descr = epg_policy.name
            # Consume and provide all of the necessary contracts
            for contract_policy in self.cdb.get_contract_policies():
                contract = None
                if epg_policy.id in contract_policy.src_ids:
                    name = contract_policy.src_id + '::' + contract_policy.dst_id
                    contract = Contract(name, tenant)
                    epg.consume(contract)
                if epg_policy.id in contract_policy.dst_ids:
                    name = contract_policy.src_id + '::' + contract_policy.dst_id
                    if contract is None:
                        contract = Contract(name, tenant)
                    epg.provide(contract)

        if self._displayonly:
            print json.dumps(tenant.get_json(), indent=4, sort_keys=True)
        else:
            resp = tenant.push_to_apic(apic)
            return resp

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
            return 'NOTOK'
        if self.cdb.store_config(config_json) and self.cdb.has_apic_config():
            self.push_config_to_apic()
        return 'OK'


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

    logging.info('Starting the tool....')
    # Handle generating sample configuration
    if args.generateconfig:
        raise NotImplementedError

    tool = ApicService()
    if args.displayonly:
        tool.set_displayonly()
    tool.setup_logging(args.debug, args.maxlogfiles)
    if args.tenant:
        tool.set_tenant_name(args.tenant)
    if args.app:
        tool.set_app_name(args.app)
    return tool

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
