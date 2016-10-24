#!/usr/bin/env python
import sys
import json
import logging
import argparse
import time
import tempfile

import acitoolkit as aci

from intersite import *


class ExportEPG():
    """
    ExportEPG : Class used to construct a json 'export' object defined in the
                intersite application.
    """
    def __init__(self, lepg, remotesite, rtenant, rint_name, repg):
        """
        :param lepg: Instance of EPG class from the local site that is to
                     be exported
        :param remotesite: Site object for the remote APIC
        :param rtenant: Name of Tenant that contains the L3out interface
        :param rint_name: Name of remote site's L3Out interface that will
                          contain the network object
        :param repg_pattern: Name of ExternalEPG that will be used in the L3out
                             network.  If it does not exist, it will be created.
        """
        self.epg = lepg
        self.app = self.epg.get_parent()
        self.tenant = self.app.get_parent()

        self.remotesite = remotesite

        # contracts
        self.consume_contracts = []
        self.provide_contracts = []
        self.consume_interfaces = []

        self.remote_epg = self._generate_object_name_from_pattern(repg)

        # remote network
        self.remote_l3out_tenant = rtenant
        self.remote_l3out_interface = rint_name

    def get_config(self):
        """
        Return an 'intersite' compatible export object
        """
        return {"export": {"epg": self.epg.name,
                           "app": self.app.name,
                           "tenant": self.tenant.name,
                           "remote_epg": self.remote_epg,
                           "remote_sites": [
                               {"site": {
                                   "name": self.remotesite.name,
                                   "interfaces": [
                                       {
                                           "l3out": {
                                               "name": self.remote_l3out_interface,
                                               "consumes_interface": self.consume_interfaces,
                                               "provides": self.provide_contracts,
                                               "consumes": self.consume_contracts,
                                               "tenant": self.remote_l3out_tenant,
                                               "noclean": "True",
                                           },
                                       },
                                   ]
                               },
                               },
                           ],
                           },
                }

    def _login(self):
        if not self.remotesite.session or not self.remotesite.session.logged_in():
            resp = self.remotesite.login()
            if not resp.ok:
                print('% Unable to authenticate to remote site:', self.remotesite.name)
                sys.exit(0)

    def _get_contract(self, contract_name, tenant):
        # check if contract exists in tenant
        self._login()

        tenant = Tenant.get_deep(self.remotesite.session, names=[str(tenant)])
        if len(tenant) > 1:
            print('% Found more than one tenant with name', ac.auto_config['remote_l3out']['tenant'], 'in site', self.remotesite.name)
            print('% Tenant names should be unique, so this should not be possible')
            sys.exit(0)

        # return contract, or None
        return tenant[0].get_child(aci.Contract, contract_name)

    def _create_contract(self, contract_name, default_filter=None):
        self._login()  # blind call to login

        tenant = Tenant.get_deep(self.remotesite.session, names=[str(self.remote_l3out_tenant)])
        if len(tenant) > 1:
            print('% Found more than one tenant with name', ac.auto_config['remote_l3out']['tenant'], 'in site', self.remotesite.name)
            print('% Tenant names should be unique, so this should not be possible')
            sys.exit(0)

        # let's see if it exists first
        if tenant[0].get_child(aci.Contract, contract_name) is None:
            # contract does not yet exist in remote site, create it with default filter (if it is defined)
            contract = aci.Contract(contract_name, tenant[0])

            # add the default filter to the newly created contract
            if default_filter:
                rfilter = tenant[0].get_child(aci.Filter, default_filter)
                if rfilter is None:
                    print('% could not find filter with name', default_filter, 'in site', self.remotesite.name)
                    print('% nothing more can be done until this filter is created.')
                    sys.exit(0)

                contract_subj = aci.ContractSubject(contract_name + "_subject", contract)
                contract_subj.add_filter(rfilter)

            resp = tenant[0].push_to_apic(self.remotesite.session)
            if not resp.ok:
                print('% could not create contract due to:', resp)
                sys.exit(0)

    def add_consume_contract(self, contract_name, default_filter=None):
        if '{' in contract_name:
            contract_name = self._generate_object_name_from_pattern(contract_name)

        self._create_contract(contract_name, default_filter)
        self.consume_contracts.append({"contract_name": contract_name})

    def add_provide_contract(self, contract_name, default_filter=None):
        if '{' in contract_name:
            contract_name = self._generate_object_name_from_pattern(contract_name)

        self._create_contract(contract_name, default_filter)
        self.provide_contracts.append({"contract_name": contract_name})

    def add_consume_interface(self, contract_name, default_filter=None):
        if '{' in contract_name:
            contract_name = self._generate_object_name_from_pattern(contract_name)

        self._create_contract(contract_name, default_filter)
        self.consume_interfaces.append({"cif_name": contract_name})

    def export_contract(self, contract, export_name):
        # exports a contract from tenant who owns the L3out object to the tenant that owns
        # the original EPG
        if '{' in export_name:
            export_name = self._generate_object_name_from_pattern(export_name)
        if '{' in contract:
            contract = self._generate_object_name_from_pattern(contract)

        logging.info("Exporting contract with name '%s' to '%s'" % (contract, export_name))

        ct = self._get_contract(contract, self.remote_l3out_tenant)
        if ct is None:
            raise ValueError('Cannot export contract that does not exist')

        exported_contract = self._get_contract(export_name, self.tenant.name)
        if exported_contract is not None:
            # contract with name already exists.. nothing more to do
            # TODO maybe a more thourough check should be done to determine
            # if this is the same contract
            return

        imported_contract = ContractInterface(export_name, self.tenant)
        imported_contract.import_contract(ct)

        resp = self.tenant.push_to_apic(self.remotesite.session)
        if not resp.ok:
            print('% could not export contract due to:', resp)

    def get_json(self):
        return json.dumps(self.get_config())

    def _generate_object_name_from_pattern(self, pattern):
        """
        Takes in a string containing one or more placeholders in the format of %{<object_name>}
        and replaces them with their equivilent variable values.
        Currently only supports epg, app and tenant names.
        """
        name = pattern.replace("%{epg}", self.epg.name)
        name = name.replace("%{app}", self.app.name)
        name = name.replace("%{tenant}", self.tenant.name)

        return name


class RemoteContract(ConfigObject):
    """
    Simple class to make extracting of contract attributes simple and painless.
    """
    def __init__(self, contract_config):
        if 'name' not in contract_config:
            raise ValueError('Contract name is a mandatory field')
        self.name = contract_config['name']

        if 'default_filter' in contract_config:
            self.default_filter = contract_config['default_filter']
        else:
            self.default_filter = None

        if 'export_to_epg_owner' in contract_config and contract_config['export_to_epg_owner'] == "True":
            self.export = True
        else:
            self.export = False

        if self.export and 'export_name' in contract_config:
            self.export_name = contract_config['export_name']
        else:
            self.export_name = None


class AutoIntersiteConfiguration(IntersiteConfiguration):
    """
    AutoIntersiteConfiguration : Extends IntersiteConfiguration defined in intersite application,
    adding validation for additional configuration options and handles the generation of
    intersite configuration.
    """
    def __init__(self, config):
        IntersiteConfiguration.__init__(self, config)

        if 'automator' not in config:
            raise ValueError('Invalid autosite configuration given')

        self.auto_config = config['automator']

        # simple state attribute help with performance
        self._collector = None
        self._changed = False
        self.sleep_time = 600  # default value

        self.consume_contracts = []
        self.provide_contracts = []
        self.consume_interfaces = []

        self._validate(config)

    # TODO there has to be a better way to validate this configuration.. perhaps
    #       utlising a JSON schema library isn't the worst idea?
    def _validate(self, config):
        if 'automator' not in config:
            raise ValueError('Invalid autosite configuration given, use flag -h for more information.')

        if 'check_interval' in config['automator'] and config['automator']['check_interval'].isdigit():
            self.sleep_time = float(config['automator']['check_interval'])

        if 'search_filter' not in config['automator']:
            raise ValueError('Invalid autosite configuration given.  search_filter is a required field.')
        else:
            self.epg_search_filter = config['automator']['search_filter']

        # remote_l3out validation, all mandatory fields.
        if 'remote_l3out' not in config['automator']:
            raise ValueError('Invalid autosite configuration given.  remote_l3out is a required field.')
        if 'tenant' not in config['automator']['remote_l3out']:
            raise ValueError('Invalid autosite configuration given.  remote_l3out is a required field.')
        if 'interface_name' not in config['automator']['remote_l3out']:
            raise ValueError('Invalid autosite configuration given.  remote_l3out is a required field.')
        if 'network_name' not in config['automator']['remote_l3out']:
            raise ValueError('Invalid autosite configuration given.  remote_l3out is a required field.')

        if 'remote_contracts' in config['automator']:
            for contract_type in config['automator']['remote_contracts']:
                for contract in config['automator']['remote_contracts'][contract_type]:
                    try:
                        cobject = RemoteContract(contract)
                        if contract_type == 'consume_contract':
                            self._add_consume_contract(cobject)
                        if contract_type == 'provide_contract':
                            self._add_provide_contract(cobject)
                        if contract_type == 'consume_int_contract':
                            self._add_consume_interface(cobject)
                    except ValueError, e:
                        print('Invalid AutoIntersite configuration given:', e)
                        sys.exit(1)

    def reload_collector(self):
        if not self._changed:  # simple way to avoid unneccessary reloading of the intersite configuration
            return

        logging.info('Reloading Intersite Collector configuration.. ')
        if self._collector is None:
            logging.info('Initializing collector.. this should only happen at first load')
            buffer = tempfile.NamedTemporaryFile(delete=False)
            buffer.write(json.dumps(self.get_config()))
            buffer.close()

            self._collector = initialize_tool(self.get_config())
            self._collector.config_filename = buffer.name
        else:
            logging.info('Loading new configuration into collector')
            resp = self._collector.save_config(self.get_config())
            if resp != 'OK':
                print('FATAL: Failed to load configuration into MultisiteCollector:', resp)
                sys.exit(1)

            if not self._collector.reload_config():
                print('FATAL: Could not reload configuration.')
                sys.exit(1)

            self._changed = False

    def get_local_site(self):
        """
        Returns a Site object of the first site in the configuration that has the local attribute set.
        Assumes there is always only 1 local site.
        """
        for site in self.site_policies:
            if site.local == 'True':
                return Site(site.name,
                            SiteLoginCredentials(site.ip_address,
                                                 site.username,
                                                 site.password,
                                                 site.use_https),
                            local=True)

        raise ValueError('No local site defined')

    def get_remote_sites(self):
        sites = []

        for site in self.site_policies:
            if site.local == 'False':
                sites.append(Site(site.name,
                             SiteLoginCredentials(site.ip_address,
                                                  site.username,
                                                  site.password,
                                                  site.use_https),
                             local=True))
        return sites

    def get_export_policies(self):
        return self.export_policies

    def add_export_policy(self, policy):
        assert isinstance(policy, ExportPolicy)
        self.export_policies.append(policy)

        try:
            self._validate_unique_epgs()
            self._changed = True
        except ValueError as e:
            print('epg unique constraint not met..')
            print(self.export_policies)
            self.export_policies.pop()

    def remove_export_policy(self, del_policy):
        assert isinstance(del_policy, ExportPolicy)

        for index, policy in enumerate(self.export_policies):
            if policy.has_same_epg_and_remote_epg(del_policy):
                del self.export_policies[index]
                self._changed = True

    def get_auto_config(self):
        return self.auto_config

    def get_sleep_time(self):
        return self.sleep_time

    def _add_consume_contract(self, c):
        self.consume_contracts.append(c)

    def _add_provide_contract(self, c):
        self.provide_contracts.append(c)

    def _add_consume_interface(self, c):
        self.consume_interfaces.append(c)

    def get_consume_contracts(self):
        return self.consume_contracts

    def get_provide_contracts(self):
        return self.provide_contracts

    def get_consume_interfaces(self):
        return self.consume_interfaces


def get_arg_parser():
    """
    Setup parser with the neccessary arguments

    :return: Instance of argparse.ArgumentParser
    """

    parser = argparse.ArgumentParser(description='ACI Multisite Automation Tool')
    parser.add_argument('--config', default='config.json',
                        help='Configuration file in JSON format')
    parser.add_argument('--generateconfig', action='store_true', default=False,
                        help='Generate an empty example configuration file')
    parser.add_argument('--debug', nargs='?', choices=['verbose', 'info', 'warnings', 'critical'],
                        const='critical',
                        help='Enable printing of debug messages')
    parser.add_argument('--stdout', action='store_true', default=False,
                        help='Output all log events to stdout')

    return parser


def configure_logging(args):
    """
    Configures the logging instance.

    This is done in the same manner as the intersite application to enable
    existing logging calls to be usable from the automator.
    """
    if args.debug is not None:
        if args.debug == 'verbose':
            level = logging.DEBUG
	elif args.debug == 'info':
	    level = logging.INFO
        elif args.debug == 'warnings':
            level = logging.WARNING
        else:
            level = logging.CRITICAL
    else:
        level = logging.CRITICAL

    if args.stdout:
        my_handler = logging.StreamHandler(sys.stdout)
    else:
        log_file = 'intersite_automator.%s.log' % str(os.getpid())
        my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024,
                                         encoding=None, delay=0)

    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    my_handler.setLevel(level)
    my_handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(my_handler)
    logging.getLogger().setLevel(level)

    logging.info('Starting Intersite Automator! ...')

    return


def parse_config(config_path):
    try:
        with open(config_path) as file:
            config = json.loads(file.read())
    except IOError as e:
        print('Unable to open configuration file:', e)
        sys.exit(1)
    except ValueError as e:
        print('Unable to parse config file:', e)
        sys.exit(1)

    if 'config' not in config:
        raise ValueError('Missing intersite configuration in config file')
    if 'automator' not in config:
        raise ValueError('Missing automator configuration in config file')

    try:
        AutoIntersiteConfiguration(config)
    except ValueError as e:
        print('Could not load improperly formatted configuration file', e)
        raise
        sys.exit(1)

    return config


def main():
    args = get_arg_parser().parse_args()

    configure_logging(args)

    try:
        config = parse_config(args.config)
    except ValueError as e:
        print('Error validating configuration file:', e)
        sys.exit(1)

    ac = AutoIntersiteConfiguration(config)
    ls = ac.get_local_site()

    resp = ls.login()
    if not resp.ok:
        print('% Could not authenticate to APIC')
        sys.exit(0)

    # initial state
    aci.Tag.subscribe(ls.session)
    while True:
        if aci.Tag.has_events(ls.session):
            tag = aci.Tag.get_event(ls.session)

            # limit results to EPG's only
            if isinstance(tag.get_parent(), aci.EPG):
                if ac.auto_config['search_filter'] and tag.name == ac.auto_config['search_filter']:
                    epg = tag.get_parent()
                    app = epg.get_parent()
                    tenant = app.get_parent()

                    logging.info("Found EPG to process %s->%s->%s" % (str(epg.name), str(app.name), str(tenant.name)))

                    for remotesite in ac.get_remote_sites():
                        repg = ExportEPG(epg, remotesite,
                                         ac.auto_config['remote_l3out']['tenant'],
                                         ac.auto_config['remote_l3out']['interface_name'],
                                         ac.auto_config['remote_l3out']['network_name'])

                        for cons_contract in ac.get_consume_contracts():
                            repg.add_consume_contract(cons_contract.name, default_filter=cons_contract.default_filter)

                            if cons_contract.export:
                                repg.export_contract(cons_contract.name, cons_contract.export_name)
                        for prov_contract in ac.get_provide_contracts():
                            repg.add_provide_contract(prov_contract.name, default_filter=prov_contract.default_filter)

                            if prov_contract.export:
                                repg.export_contract(prov_contract.name, prov_contract.export_name)
                        for cons_interface in ac.get_consume_interfaces():
                            repg.add_consume_interface(cons_interface.name, default_filter=cons_interface.default_filter)

                            if cons_interface.export:
                                repg.export_contract(cons_interface.name, cons_interface.export_name)

                        ep = ExportPolicy(repg.get_config())
                        if ep is None:
                            logging.error('Could not create ExportProfile with: tenant: %s app %s epg %s site %s remote_tenant %s remote_interface %s',
                                          tenant.name,
                                          app.name,
                                          epg.name,
                                          remotesite.name,
                                          ac.auto_config['remote_l3out']['tenant'],
                                          ac.auto_config['remote_l3out']['interface_name'])
                            continue

                        if tag.is_deleted():
                            # EPG is being deleted, should probably clean up contracts?
                            logging.info('Removing ExportPolicy to config: %s-%s|%s|%s', remotesite.name, tenant.name, app.name, epg.name)
                            ac.remove_export_policy(ep)

                        else:
                            # new EPG being exported, probably need to create a contract for it?
                            logging.info('Adding ExportPolicy to config: %s-%s|%s|%s', remotesite.name, tenant.name, app.name, epg.name)
                            ac.add_export_policy(ep)

        else:
            logging.info('No new events to process, sleeping for %d seconds', ac.get_sleep_time())
            ac.reload_collector()
            time.sleep(ac.get_sleep_time())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
