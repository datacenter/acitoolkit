#!/usr/bin/env python
"""
IntraEPG application enables policies to be enforced within a single EPG
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
from ansible import playbook, callbacks
import pprint
import jinja2
from tempfile import NamedTemporaryFile
from intraepg_templates import HOSTS_TEMPLATE, MY_PLAYBOOK
import time

# Imports from standalone mode
import argparse


# Maximum number of endpoints to handle in a single burst
MAX_ENDPOINTS = 500

# Server credentials
SERVER_USERNAME = 'admin'
SERVER_PASSWORD = 'password'


class LoggingCallbacks(callbacks.PlaybookCallbacks):
    def log(self, level, msg, *args, **kwargs):
        logging.log(level, msg, *args, **kwargs)

    def on_task_start(self, name, is_conditional):
        self.log(logging.INFO, 'task: {0}'.format(name))
        super(LoggingCallbacks, self).on_task_start(name, is_conditional)

    # def on_play_start(self, name):
    #     self.log(logging.INFO, 'play: {0}'.format(name))


class LoggingRunnerCallbacks(callbacks.PlaybookRunnerCallbacks):
    def log(self, level, msg, *args, **kwargs):
        logging.log(level, msg, *args, **kwargs)

    def _on_any(self, level, label, host, orig_result):
        result = orig_result.copy()
        result.pop('invocation', None)
        result.pop('verbose_always', True)
        item = result.pop('item', None)
        if not result:
            msg = ''
        elif len(result) == 1:
            msg = ' | {0}'.format(result.values().pop())
        else:
            msg = '\n' + pprint.pformat(result)
        if item:
            self.log(level, '{0} (item={1}): {2}{3}'.format(host, item, label, msg))
        else:
            self.log(level, '{0}: {1}{2}'.format(host, label, msg))

    def on_failed(self, host, res, ignore_errors=False):
        if ignore_errors:
            level = logging.INFO
            label = 'FAILED (ignored)'
        else:
            level = logging.ERROR
            label = 'FAILED'
        self._on_any(level, label, host, res)
        super(LoggingRunnerCallbacks, self).on_failed(host, res, ignore_errors)

    def on_ok(self, host, res):
        self._on_any(logging.INFO, 'SUCCESS', host, res)
        super(LoggingRunnerCallbacks, self).on_ok(host, res)

    def on_error(self, host, msg):
        self.log(logging.ERROR, '{0}: ERROR | {1}'.format(host, msg))
        super(LoggingRunnerCallbacks, self).on_error(host, msg)

    def on_skipped(self, host, item=None):
        if item:
            self.log(logging.INFO, '{0} (item={1}): SKIPPED'.format(host, item))
        else:
            self.log(logging.INFO, '{0}: SKIPPED'.format(host))
        super(LoggingRunnerCallbacks, self).on_skipped(host, item)

    def on_unreachable(self, host, res):
        self._on_any(logging.ERROR, 'UNREACHABLE', host, dict(unreachable=res))
        super(LoggingRunnerCallbacks, self).on_unreachable(host, res)

    def on_no_hosts(self):
        self.log(logging.ERROR, 'No hosts matched')
        super(LoggingRunnerCallbacks, self).on_no_hosts()


class IntraEPGConfiguration(object):
    def __init__(self, config):
        self.apic_policy = None
        self.contract_policies = []
        self.epg_policies = []

        if 'config' not in config:
            raise ValueError('Expected "config" in configuration')

        for item in config['config']:
            if 'apic' in item:
                self.apic_policy = ApicPolicy(item)
            elif 'contract' in item:
                contract_policy = ContractPolicy(item)
                if contract_policy is not None:
                    self.contract_policies.append(contract_policy)
            elif 'epg' in item:
                epg_policy = EPGPolicy(item)
                if epg_policy is not None:
                    self.epg_policies.append(epg_policy)
        self._validate_unique_contracts()
        self._validate_unique_epgs()

    def _validate_unique(self, policies):
        for policy in policies:
            count = 0
            for other_policy in policies:
                if other_policy.name == policy.name:
                    count += 1
            if count > 1:
                raise ValueError('Duplicate policy found for policy: %s' % policy.get_policy_name())

    def _validate_unique_contracts(self):
        self._validate_unique(self.contract_policies)

    def _validate_unique_epgs(self):
        self._validate_unique(self.epg_policies)

    def has_epg_policy(self, tenant_name, app_name, epg_name):
        if len(self.epg_policies) == 0:
            return False
        for policy in self.epg_policies:
            if policy.tenant == tenant_name and policy.app == app_name and policy.name == epg_name:
                return True
        return False

    def get_epg_policy(self, tenant_name, app_name, epg_name):
        for policy in self.epg_policies:
            if policy.tenant == tenant_name and policy.app == app_name and policy.name == epg_name:
                return policy

    def get_contract_policy(self, contract_name):
        for policy in self.contract_policies:
            if policy.name == contract_name:
                return policy

    def get_config(self):
        policies = []
        if self.apic_policy is not None:
            policies.append(self.apic_policy._policy)
        for policy in self.contract_policies:
            policies.append(policy._policy)
        for policy in self.epg_policies:
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

    def _validate_status(self, item):
        if str(item).lower() not in ['enabled', 'disabled']:
            raise ValueError(self.__class__.__name__ + ': Expected "enabled" or "disabled"')

    def validate(self):
        raise NotImplementedError


class ApicPolicy(ConfigObject):
    @property
    def user_name(self):
        return self._policy['apic']['user_name']

    @user_name.setter
    def user_name(self, user_name):
        self._policy['apic']['user_name'] = user_name

    @property
    def ip_address(self):
        return self._policy['apic']['ip_address']

    @ip_address.setter
    def ip_address(self, ip_address):
        self._policy['apic']['ip_address'] = ip_address

    @property
    def password(self):
        return self._policy['apic']['password']

    @password.setter
    def password(self, password):
        self._policy['apic']['password'] = password

    @property
    def use_https(self):
        return self._policy['apic']['use_https']

    @use_https.setter
    def use_https(self, use_https):
        self._policy['apic']['use_https'] = use_https

    def __eq__(self, other):
        if self.user_name != other.user_name or self.ip_address != other.ip_address:
            return False
        if self.password != other.password or self.use_https != other.use_https:
            return False
        else:
            return True

    def __ne__(self, other):
        return not self == other

    def validate(self):
        if 'apic' not in self._policy:
            raise ValueError(self.__class__.__name__, 'Expecting "apic" in configuration')
        policy = self._policy['apic']
        for item in policy:
            keyword_validators = {'user_name': '_validate_non_empty_string',
                                  'ip_address': '_validate_ip_address',
                                  'password': '_validate_string',
                                  'use_https': '_validate_boolean_string'}
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])


class EntryPolicy(ConfigObject):
    @property
    def applyToFrag(self):
        return self._policy['entry']['applyToFrag']

    @property
    def arpOpc(self):
        return self._policy['entry']['arpOpc']

    @property
    def dFromPort(self):
        return self._policy['entry']['dFromPort']

    @property
    def dToPort(self):
        return self._policy['entry']['dToPort']

    @property
    def etherT(self):
        return self._policy['entry']['etherT']

    @property
    def icmpv4T(self):
        return self._policy['entry']['icmpv4T']

    @property
    def icmpv6T(self):
        return self._policy['entry']['icmpv6T']

    @property
    def prot(self):
        return self._policy['entry']['prot']

    @property
    def sFromPort(self):
        return self._policy['entry']['sFromPort']

    @property
    def sToPort(self):
        return self._policy['entry']['sToPort']

    @property
    def stateful(self):
        return self._policy['entry']['stateful']

    @property
    def tcpRules(self):
        return self._policy['entry']['tcpRules']

    def validate(self):
        if 'entry' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "entry" in entry policy')
        policy = self._policy['entry']
        for item in policy:
            keyword_validators = {'applyToFrag': '_validate_string',
                                  'arpOpc': '_validate_string',
                                  'dFromPort': '_validate_string',
                                  'dToPort': '_validate_string',
                                  'etherT': '_validate_string',
                                  'icmpv4T': '_validate_string',
                                  'icmpv6T': '_validate_string',
                                  'prot': '_validate_string',
                                  'sFromPort': '_validate_string',
                                  'sToPort': '_validate_string',
                                  'stateful': '_validate_string',
                                  'tcpRules': '_validate_string'}
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])


class ContractPolicy(ConfigObject):
    @property
    def name(self):
        return self._policy['contract']['name']

    @property
    def status(self):
        return self._policy['contract']['status']

    def validate(self):
        if 'contract' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "contract" in configuration')
        policy = self._policy['contract']
        for item in policy:
            keyword_validators = {'name': '_validate_string',
                                  'status': '_validate_status',
                                  'entries': '_validate_list'}
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])
            self.get_entry_policies()

    def get_entry_policies(self):
        entries = []
        for entry in self._policy['contract']['entries']:
            entries.append(EntryPolicy(entry))
        return entries

    def _convert(self, converter, value):
        if value in converter:
            value = converter[value]
        value = str(value)

        # Normalize to decimal
        try:
            if '0x' in value:
                value = str(int(value, 16))
            else:
                value = str(int(value))
        except ValueError:
            return converter['unspecified']
        return value

    def _convert_l4port(self, port_number):
        converter = {
            'unspecified': '0',
            'ftpData': '20',
            'smtp': '25',
            'dns': '53',
            'http': '80',
            'pop3': '110',
            'https': '443',
            'rtsp': '554'
        }
        return self._convert(converter, port_number)

    def _convert_ethertype(self, ethertype):
        converter = {
            'unspecified': '0',
            'trill': '0x22F3',
            'arp': '0x806',
            'mpls_ucast': '0x8847',
            'mac_security': '0x88E5',
            'fcoe': '0x8906',
            'ip': '0xABCD'
        }
        return self._convert(converter, ethertype)

    def generate_configuration(self, endpoints):
        arp_entries = []
        eb_entries = []
        ip_entries = []

        # Convert the entries
        for entry in self.get_entry_policies():
            # Create the single entry
            if entry.arpOpc:
                arp_entries.append('    opcode %s ACCEPT;\n' % entry.arpOpc)
                continue
            if entry.etherT:
                eb_entries.append('    proto %s ACCEPT;\n') % self._convert_ethertype(entry.etherT)
                continue
            new_entry = '    proto ' + entry.prot
            if entry.dFromPort:
                from_port = self._convert_l4port(entry.dFromPort)
                to_port = self._convert_l4port(entry.dToPort)
                if from_port == to_port:
                    new_entry += ' dport %s' % from_port
                else:
                    new_entry += ' dport %s:%s' % (from_port, to_port)
            if entry.sFromPort:
                from_port = self._convert_l4port(entry.sFromPort)
                to_port = self._convert_l4port(entry.sToPort)
                if from_port == to_port:
                    new_entry += ' sport %s' % from_port
                else:
                    new_entry += ' sport %s:%s' % (from_port, to_port)
            new_entry += ' ACCEPT;\n'
            ip_entries.append(new_entry)

        arp_table = ''
        eb_table = ''
        ip_table = ''
        # Postprocess the entries
        if arp_entries:
            arp_table = 'domain arp chain INPUT {\n'
            for arp_entry in arp_entries:
                arp_table += arp_entry
            arp_table += '    DROP;\n}\n'
        if eb_entries:
            eb_table = 'domain eb chain INPUT {\n'
            for eb_entry in eb_entries:
                eb_table += eb_entry
            eb_table += '    DROP;\n}\n'
        if ip_entries:
            ip_table = '@def $ENDPOINTS = ('
            for ep in endpoints:
                ip_table += ep.name + ' '
            ip_table += ');\ndomain (ip)\ntable filter {\n    chain INPUT {\n'
            # Connection Tracking
            ip_table += '        mod state state INVALID DROP;\n'
            ip_table += '        mod state state (ESTABLISHED RELATED) ACCEPT;\n'
            # Allow local connections
            ip_table += '        interface lo ACCEPT;\n'
            # Allow ssh connections. Must keep this for Ansible to access host.
            ip_table += '        proto tcp dport ssh ACCEPT;\n'

            addnl = """
    # Because the default policy is to ACCEPT we DROP
    # everything that comes through to this stage.
    }

    # Outgoing connections are not limited.
    chain OUTPUT policy ACCEPT;

    # This is not a router.
    chain FORWARD policy DROP;
}
                    """
            ip_table += '        saddr $ENDPOINTS @subchain {\n'
            for ip_entry in ip_entries:
                ip_table += '            ' + ip_entry
            ip_table += '                ' + 'DROP;\n        }\n'
            ip_table += addnl
        config = jinja2.Template(arp_table + eb_table + ip_table).render({'endpoints': endpoints})
        logging.info('generating config\n%s', config)
        return config


class EPGPolicy(ConfigObject):
    @property
    def tenant(self):
        return self._policy['epg']['tenant']

    @property
    def app(self):
        return self._policy['epg']['app']

    @property
    def name(self):
        return self._policy['epg']['name']

    @property
    def contract(self):
        return self._policy['epg']['contract']

    @property
    def status(self):
        return self._policy['epg']['status']

    def validate(self):
        if 'epg' not in self._policy:
            raise ValueError(self.__class__.__name__ + 'Expecting "epg" in configuration')
        policy = self._policy['epg']
        for item in policy:
            keyword_validators = {'tenant': '_validate_string',
                                  'app': '_validate_string',
                                  'name': '_validate_string',
                                  'contract': '_validate_string',
                                  'status': '_validate_status'}
            if item not in keyword_validators:
                raise ValueError(self.__class__.__name__ + 'Unknown keyword: %s' % item)
            self.__getattribute__(keyword_validators[item])(policy[item])


class EndpointMonitor(threading.Thread):
    """
    Monitor thread responsible for subscribing for Endpoints.
    """
    def __init__(self, tool):
        threading.Thread.__init__(self)
        self._exit = False
        self._tool = tool
        self._ansible_stats = callbacks.AggregateStats()
        self._ansible_playbook_cb = LoggingCallbacks(verbose=3)
        self._ansible_runner_cb = LoggingRunnerCallbacks(self._ansible_stats, verbose=3)
        self._endpoint_db = {}
        for policy in self._tool.config.epg_policies:
            self._endpoint_db[(policy.tenant, policy.app, policy.name)] = []

    @property
    def session(self):
        return self._tool.apic.get_session()

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def process_policy(self, contract_policy, epg, host_ips, new_host_ips):
        host_template = jinja2.Template(HOSTS_TEMPLATE)
        rendered_host_template = host_template.render({'all_host_ip': host_ips,
                                                       'new_host_ip': new_host_ips})
        print 'hosts_file:'
        print rendered_host_template
        hosts_file = NamedTemporaryFile(delete=False)
        hosts_file.write(rendered_host_template)
        hosts_file.close()

        # Create the temporary ferm.conf file
        ferm_config = contract_policy.generate_configuration(self._endpoint_db[epg])
        ferm_config_template = jinja2.Template(ferm_config)
        rendered_ferm_config_template = ferm_config_template.render({'ferm_conf': 'ferm.conf'})
        print 'ferm.conf:'
        print rendered_ferm_config_template
        ferm_config_file = NamedTemporaryFile(delete=False)
        ferm_config_file.write(rendered_ferm_config_template)
        ferm_config_file.close()

        # Create the temporary yml playbook
        my_playbook_template = jinja2.Template(MY_PLAYBOOK)
        my_rendered_playbook_template = my_playbook_template.render({'ferm_conf': ferm_config_file.name,
                                                                     'user_name': SERVER_USERNAME})
        my_playbook_file = NamedTemporaryFile(delete=False)
        print 'Playbook:'
        print my_rendered_playbook_template
        my_playbook_file.write(my_rendered_playbook_template)
        my_playbook_file.close()

        # Call the playbook
        pb = playbook.PlayBook(playbook=my_playbook_file.name,
                               host_list=hosts_file.name,
                               stats=self._ansible_stats,
                               callbacks=self._ansible_playbook_cb,
                               runner_callbacks=self._ansible_runner_cb,
                               remote_user=SERVER_USERNAME,
                               remote_pass=SERVER_PASSWORD,
                               become_pass=SERVER_PASSWORD)
        result = pb.run()
        print 'result:', result
        if self._ansible_stats.failures or self._ansible_stats.dark:
            raise RuntimeError('Playbook failed')

    def handle_endpoint_event(self):
        num_eps = MAX_ENDPOINTS
        dirty_epgs = {}
        while IPEndpoint.has_events(self.session) and num_eps:
            ep = IPEndpoint.get_event(self.session)
            logging.info('for Endpoint: %s', ep.name)
            epg = ep.get_parent()
            app = epg.get_parent()
            tenant = app.get_parent()

            print 'Endpoint found', ep.name
            print 'Has EPG policy', (tenant.name, app.name, epg.name), (tenant.name, app.name, epg.name) in self._endpoint_db
            if (tenant.name, app.name, epg.name) in self._endpoint_db:
                # Store the Endpoint in our Endpoint DB
                if ep.is_deleted():
                    try:
                        self._endpoint_db[(tenant.name, app.name, epg.name)].remove(ep)
                    except ValueError:
                        logging.error('Tried to delete endpoint that was not in database.')
                else:
                    self._endpoint_db[(tenant.name, app.name, epg.name)].append(ep)
                # Mark the EPG as dirty (we need to push to the hosts)
                if (tenant.name, app.name, epg.name) not in dirty_epgs:
                    dirty_epgs[(tenant.name, app.name, epg.name)] = []
                if not ep.is_deleted():
                    dirty_epgs[(tenant.name, app.name, epg.name)].append(ep)
            num_eps -= 1
        start_time = time.time()
        for epg in dirty_epgs:
            (tenant_name, app_name, epg_name) = epg
            epg_policy = self._tool.config.get_epg_policy(tenant_name, app_name, epg_name)
            contract_policy = self._tool.config.get_contract_policy(epg_policy.contract)

            # Create the temporary equivalent of a /etc/ansible/hosts file for all hosts
            host_ips = ''
            new_host_ips = ''
            for ep in self._endpoint_db[epg]:
                host_ips += ep.name + '\n'
            for ep in dirty_epgs[epg]:
                assert not ep.is_deleted()
                new_host_ips += ep.name + '\n'

            self.process_policy(contract_policy, epg, host_ips, new_host_ips)
        end_time = time.time()
        print 'Time taken:', end_time - start_time

    def run(self):
        # Subscribe to endpoints
        IPEndpoint.subscribe(self.session)

        while not self._exit:
            if IPEndpoint.has_events(self.session):
                try:
                    self.handle_endpoint_event()
                except ConnectionError:
                    logging.error('Could not handle endpoint event due to ConnectionError')


class Apic(object):
    def __init__(self, apic_policy):
        self._policy = apic_policy
        self._session = None

    def login(self):
        url = self._policy.ip_address
        if str(self._policy.use_https).lower() == 'true':
            url = 'https://' + url
        else:
            url = 'http://' + url
        self._session = Session(url, self._policy.user_name, self._policy.password)
        resp = self._session.login()
        return resp

    def logged_in(self):
        return self._session.logged_in()

    def get_name(self):
        return self._policy.ip_address

    def get_session(self):
        return self._session


class IntraEPGTool(object):
    def __init__(self, config, config_filename):
        self.apic = None
        self.config_filename = config_filename
        self.contracts = {}
        # TODO remove prints and replace with logging and proper error messages that can be handled by the REST API
        try:
            self.config = IntraEPGConfiguration(config)
        except ValueError as e:
            print 'Could not load improperly formatted configuration file'
            print e
            sys.exit(0)
        logging.debug('New configuration: %s', self.config.get_config())

        # Login to APIC
        resp = self._initialize_apic()

        for contract_policy in self.config.contract_policies:
            config = contract_policy.generate_configuration(endpoints=[])
            print config

        # Start the Endpoint Monitor
        self.monitor = EndpointMonitor(self)
        self.monitor.daemon = True
        self.monitor.start()

    def _initialize_apic(self):
        if self.config.apic_policy is None:
            print 'no apic policy'
            return
        self.apic = Apic(self.config.apic_policy)
        return self.apic.login()

    def reload_config(self, config):
        try:
            self.config = IntraEPGConfiguration(config)
        except ValueError as e:
            print 'Could not load improperly formatted configuration file'
            print e
            sys.exit(0)

        start_time = time.time()
        for epg_policy in self.config.epg_policies:
            epg = (epg_policy.tenant, epg_policy.app, epg_policy.name)
            host_ips = ''
            new_host_ips = ''
            for ep in self.monitor._endpoint_db[epg]:
                host_ips += ep.name + '\n'

            contract_policy = self.config.get_contract_policy(epg_policy.contract)
            self.monitor.process_policy(contract_policy, epg,
                                        host_ips, new_host_ips)
        end_time = time.time()
        print 'Time taken:', end_time - start_time


class CommandLine(cmd.Cmd):
    prompt = 'intraepg> '
    intro = 'Cisco ACI IntraEPG tool (type help for commands)'

    SHOW_CMDS = ['configfile', 'debug', 'config', 'contracts', 'endpoints', 'epgs', 'log', 'apic', 'stats']
    DEBUG_CMDS = ['verbose', 'warnings', 'critical']
    CLEAR_CMDS = ['stats']

    def __init__(self, tool):
        self.tool = tool
        cmd.Cmd.__init__(self)

    def do_quit(self, line):
        '''
        quit
        Quit the IntraEPG tool.
        '''
        sys.exit(0)

    def do_show(self, keyword):
        '''
        show
        Various commands that show the intraepg tool details.

        Available subcommands:
        show debug - show the current debug level setting
        show configfile - show the config file name setting
        show config - show the current JSON configuration
        show log - show the contents of the intraepg.log file
        show apic - show the status of the communication with the APIC
        show stats - show some basic event statistics
        '''
        if keyword == 'debug':
            print 'Debug level currently set to:', logging.getLevelName(logging.getLogger().getEffectiveLevel())
        elif keyword == 'configfile':
            print 'Configuration file is set to:', self.tool.config_filename
        elif keyword == 'config':
            print json.dumps(self.tool.config.get_config(), indent=4, separators=(',', ':'))
        elif keyword == 'log':
            p = subprocess.Popen(['less', 'intraepg.%s.log' % str(os.getpid())], stdin=subprocess.PIPE)
            p.communicate()
        elif keyword == 'apic':
            if self.tool.apic is None:
                print 'No APIC configured'
                return
            if self.tool.apic.logged_in():
                state = 'Connected'
            else:
                state = 'Not connected'
            print self.tool.apic.get_name(), ':', state
        elif keyword == 'stats':
            raise NotImplementedError

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
        try:
            with open(self.tool.config_filename) as config_file:
                config = json.load(config_file)
        except IOError:
            print '%% Unable to open configuration file', self.tool.config_filename
            return
        except ValueError:
            print '%% File could not be decoded as JSON.'
            return
        if 'config' not in config:
            print '%% Invalid configuration file'
            return

        if self.tool.reload_config(config):
            print 'Configuration reload complete'

    def do_configfile(self, filename):
        '''
        configfile <filename>
        Set the configuration file name.
        '''
        if len(filename):
            self.tool.config_filename = filename
            print 'Configuration file is set to:', self.tool.config_filename
        else:
            print 'No config filename given.'

    def do_clear(self, keyword):
        '''
        clear stats
        Set the statistics back to 0.
        '''
        if keyword == 'stats':
            handler = self.collector.get_local_apic().monitor._endpoints
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
        local_apic = self.collector.get_local_apic()
        if local_apic is None:
            print 'No local apic configured.'
            return
        policy = local_apic.get_policy_for_epg(tenant_name, app_name, epg_name)
        if policy is None:
            print 'Could not find policy for specified <tenant_name>/<app_profile_name>/<epg_name>'
            return
        local_apic.monitor.handle_existing_endpoints(policy)


def get_arg_parser():
    """
    Get the parser with the necessary arguments

    :return: Instance of argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description='ACI IntraEPG Tool')
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
    Main IntraEPG application execution

    :param args: command line arguments
    :param test_mode: True or False. True indicates that the command line parser should not be run.
                      This is used by test routines and when invoked by the REST API
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
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    log_file = 'intraepg.%s.log' % str(os.getpid())
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
            "config": [
                {
                    "apic": {
                        "user_name": "",
                        "ip_address": "",
                        "password": "",
                        "use_https": ""
                    }
                },
                {
                    "contract": {
                        "name": "",
                        "status": "",
                        "entries": [
                            {
                                "entry": {
                                    "applyToFrag": "",
                                    "arpOpc": "",
                                    "dFromPort": "",
                                    "dToPort": "",
                                    "etherT": "",
                                    "icmpv4T": "",
                                    "icmpv6T": "",
                                    "prot": "",
                                    "sFromPort": "",
                                    "sToPort": "",
                                    "stateful": "",
                                    "tcpRules": ""
                                }
                            }
                        ]
                    }
                },
                {
                    "epg": {
                        "tenant": "",
                        "app": "",
                        "name": "",
                        "contract": "",
                        "status": ""
                    }
                }
            ]
        }

        json_data = json.dumps(config, indent=4, separators=(',', ': '))
        config_file = open('sample_config.json', 'w')
        print 'Sample configuration file written to sample_config.json'
        print "    Valid values for use_https and local are 'True' and 'False'"
        print 'Replicate the contract JSON for each IntraEPG contract.'
        print 'Replicate the epg JSON for each EPG using the IntraEPG contract.'
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

    tool = IntraEPGTool(config, args.config)

    # Just wait, add any CLI here
    if test_mode:
        return tool
    CommandLine(tool).cmdloop()
    while True:
        pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
