from acitoolkit.acitoolkit import *
import json
import re
import threading
import logging
import cmd

# Imports from standalone mode
import argparse

# TODO documentation
# TODO docstrings

# Maximum number of endpoints to handle in a single burst
MAX_ENDPOINTS = 1000


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
    def __init__(self):
        self.db = {}  # Indexed by remote site

    def _remove_queued_endpoint(self, remote_site, l3out_policy, endpoint):
        if remote_site not in self.db:
            return
        # Find the remote site's list of tenant JSONs
        db_entry = self.db[remote_site]
        # Find the l3outs we should be looking at based on the policy
        l3out_tenant = l3out_policy['l3out']['tenant']
        l3out_name = l3out_policy['l3out']
        for tenant_json in db_entry:
            if tenant_json['fvTenant']['attributes']['name'] != l3out_tenant:
                continue
            for l3out in tenant_json['fvTenant']['children']:
                if 'l3extOut' not in l3out:
                    continue
                if l3out['l3extOut']['attributes']['name'] != l3out_name:
                    continue
                for l3instp in l3out:
                    if 'l3extInstP' not in l3instp:
                        continue
                    mac = l3instp['l3extInstP']['attributes']['name']
                    if mac == endpoint.mac:
                        l3out.remove(l3instp)

    def _create_tenant_with_l3instp(self, l3out_policy, endpoint, tag):
        l3out_name = l3out_policy['l3out']['name']
        l3out_tenant = l3out_policy['l3out']['tenant']
        remote_tenant = Tenant(l3out_tenant)
        network = OutsideNetwork(endpoint.mac)
        if endpoint.is_deleted():
            network.mark_as_deleted()
        else:
            network.network = endpoint.ip + '/32'
        if 'provides' in l3out_policy['l3out']:
            for provided_contract in l3out_policy['l3out']['provides']:
                contract = Contract(provided_contract['contract_name'])
                network.provide(contract)
        if 'consumes' in l3out_policy['l3out']:
            for consumed_contract in l3out_policy['l3out']['consumes']:
                contract = Contract(consumed_contract['contract_name'])
                network.consume(contract)
        if 'protected_by' in l3out_policy['l3out']:
            for protecting_taboo in l3out_policy['l3out']['protected_by']:
                taboo = Taboo(protecting_taboo['taboo_name'])
                network.protect(taboo)
        if 'consumes_interface' in l3out_policy['l3out']:
            for consumes_interface in l3out_policy['l3out']['consumes_interface']:
                cif = ContractInterface(consumes_interface['cif_name'])
                network.consume_cif(cif)
        outside = OutsideEPG(l3out_name, remote_tenant)
        network.add_tag(str(tag))
        outside.networks.append(network)
        return remote_tenant.get_json()

    def _merge_tenant_json(self, remote_site, new_json):
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

        # Add the l3instP configuration with the existing JSON
        new_l3instp = new_l3out['l3extOut']['children'][0]
        assert 'l3extInstP' in new_l3instp
        l3out['l3extOut']['children'].append(new_l3instp)

    def add_endpoint(self, endpoint, local_site):
        logging.info('EndpointHandler:add_endpoint endpoint: %s', endpoint.mac)
        epg = endpoint.get_parent()
        app = epg.get_parent()
        tenant = app.get_parent()

        # Ignore events without IP addresses
        if endpoint.ip == '0.0.0.0' or (endpoint.ip is None and not endpoint.is_deleted()):
            return

        # Get the policy for the EPG
        policy = local_site.get_policy_for_epg(tenant.name, app.name, epg.name)
        if policy is None:
            logging.info('Ignoring endpoint as there is no policy defined for its EPG')
            return

        # Process the endpoint policy
        for remote_site in policy['export']['remote_sites']:
            remote_site_name = remote_site['site']['name']
            for l3out_policy in remote_site['site']['interfaces']:
                # Remove existing JSON for the endpoint if any already queued since this
                # update will override that
                self._remove_queued_endpoint(remote_site_name, l3out_policy, endpoint)

                # Create the JSON
                tag = IntersiteTag(tenant.name, app.name, epg.name, local_site.name)
                tenant_json = self._create_tenant_with_l3instp(l3out_policy, endpoint, tag)

                # Add to the database
                self._merge_tenant_json(remote_site_name, tenant_json)

    def push_to_remote_sites(self, collector):
        """
        Push the endpoints to the remote sites
        """
        logging.debug('EndpointHandler:push_to_remote_sites')
        for remote_site in self.db:
            remote_site_obj = collector.get_site(remote_site)
            assert remote_site_obj is not None
            remote_session = remote_site_obj.session
            for tenant_json in self.db[remote_site]:
                resp = remote_session.push_to_apic(Tenant.get_url(), tenant_json)
                if not resp.ok:
                    logging.warning('Could not push to remote site: %s %s', resp, resp.text)
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
        self._endpoints = EndpointHandler()

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def verify_endpoints(self, policy):
        raise NotImplementedError

    def handle_existing_endpoints(self, policy):
        tenant_name = policy['export']['tenant']
        app_name = policy['export']['app']
        epg_name = policy['export']['epg']
        logging.info('handle_existing_endpoints for tenant: %s app_name: %s epg_name: %s',
                     tenant_name, app_name, epg_name)
        endpoints = Endpoint.get_all_by_epg(self._session,
                                            tenant_name, app_name, epg_name,
                                            with_interface_attachments=False)
        for endpoint in endpoints:
            self._endpoints.add_endpoint(endpoint, self._local_site)
        self._endpoints.push_to_remote_sites(self._my_collector)
        self.verify_endpoints(policy)

    def handle_endpoint_event(self):
        num_eps = MAX_ENDPOINTS
        while Endpoint.has_events(self._session) and num_eps:
            ep = Endpoint.get_event(self._session, with_relations=False)
            logging.info('handle_endpoint_event for Endpoint: %s', ep.mac)
            self._endpoints.add_endpoint(ep, self._local_site)
            num_eps -= 1
        self._endpoints.push_to_remote_sites(self._my_collector)

    def run(self):
        # Subscribe to endpoints
        Endpoint.subscribe(self._session)

        while not self._exit:
            if Endpoint.has_events(self._session):
                self.handle_endpoint_event()


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
            logging.warning('Could not login to site: %s due to: %s %s', self.name, resp, resp.text)
            print('%% Could not login to APIC on Site', self.name)
        else:
            logging.info('%% Logged into Site %s', self.name)
            self.logged_in = True
        return resp


class ExportPolicy(object):
    def __init__(self, policy):
        self._policy = policy

    def get_tenant_name(self):
        return self._policy['export']['tenant']

    def get_app_name(self):
        return self._policy['export']['app']

    def get_epg_name(self):
        return self._policy['export']['epg']

    def has_same_epg(self, policy):
        if isinstance(policy, dict):
            policy = ExportPolicy(policy)
        if self.get_tenant_name() != policy.get_tenant_name():
            return False
        if self.get_app_name() != policy.get_app_name():
            return False
        if self.get_epg_name() != policy.get_epg_name():
            return False
        return True

    def get_sites(self):
        return self._policy['export']['remote_sites']


class LocalSite(Site):
    def __init__(self, name, credentials, parent):
        super(LocalSite, self).__init__(name, credentials, local=True)
        self.my_collector = parent
        self.monitor = None
        self.policy_db = []

    def start(self):
        resp = super(LocalSite, self).start()
        if resp.ok:
            self.monitor = MultisiteMonitor(self.session, self, self.my_collector)
            self.monitor.daemon = True
            self.monitor.start()
        return resp

    def add_policy(self, policy):
        old_policy = self.get_policy_for_epg(policy['export']['tenant'],
                                             policy['export']['app'],
                                             policy['export']['epg'])
        if old_policy is not None:
            self.policy_db.remove(old_policy)
        if policy not in self.policy_db:
            self.policy_db.append(policy)
        self.monitor.handle_existing_endpoints(policy)

    def validate_policy(self, policy):
        pass

    def remove_policy(self, policy):
        self.policy_db.remove(policy)

    def get_policy_for_epg(self, tenant_name, app_name, epg_name):
        for policy in self.policy_db:
            attributes = policy['export']
            if attributes['tenant'] == tenant_name and attributes['app'] == app_name and attributes['epg'] == epg_name:
                return policy


class RemoteSite(Site):
    def __init__(self, name, credentials):
        super(RemoteSite, self).__init__(name, credentials, local=False)

    def remove_all_entries(self, itag, l3out_name, l3out_tenant_name):
        query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=children&'
                     'target-subtree-class=l3extInstP&'
                     'rsp-subtree=children&'
                     'rsp-subtree-filter=eq(tagInst.name,"%s")&'
                     'rsp-subtree-include=required' % (l3out_tenant_name, l3out_name, itag))
        resp = self.session.get(query_url)
        if not resp.ok:
            logging.warning('Could not get remote site entries %s %s', resp, resp.text)
            return
        for entry in resp.json()['imdata']:
            url = '/api/mo/' + entry['l3extInstP']['attributes']['dn'] + '.json'
            data = {'l3extInstP': {'attributes': {'status': 'deleted'}}}
            resp = self.session.push_to_apic(url, data)
            if not resp.ok:
                logging.warning('Could not remove remote site entry %s %s', resp, resp.text)


class MultisiteCollector(object):
    """

    """
    def __init__(self):
        self.sites = []
        self.config = {}
        self.config_filename = None

    def initialize_local_site(self):
        # Initialize the local site
        local_site = self.get_local_site()
        if local_site is None:
            print '%% No local site configured'
            return

        # Export all of the configured exported contracts
        for export_policy in self.config['config']:
            if 'export' in export_policy:
                local_site.add_policy(export_policy)

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
        logging.info('add_site name:%s local:%s', name, local)
        self.delete_site(name)
        if local:
            site = LocalSite(name, credentials, self)
        else:
            site = RemoteSite(name, credentials)
        self.sites.append(site)
        return site.start()

    def add_site_from_config(self, site):
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
        self.add_site(site['site']['name'], creds, is_local)

    def delete_site(self, name):
        logging.info('add_site name:%s', name)
        for site in self.sites:
            if name == site.name:
                site.shutdown()
                self.sites.remove(site)

    def print_sites(self):
        print 'Number of sites:', len(self.sites)
        for site in self.sites:
            print site.name, site.credentials.ip_address

    def _reload_sites(self, old_config, new_config):
        added_local_site = False
        # Check the old sites for deleted sites or changed configs
        logging.info('Loading site configurations...')
        for old_site in old_config['config']:
            if 'site' not in old_site:
                continue
            found_site = False
            for new_site in new_config['config']:
                if 'site' not in new_site:
                    continue
                site_name = new_site['site']['name']
                if site_name == old_site['site']['name']:
                    if new_site != old_site:
                        logging.info('Site config for site %s has changed.', site_name)
                        # Something changed, remove the old site and add the new site
                        self.delete_site(site_name)
                        self.add_site_from_config(new_site)
                        if new_site['site']['local'] == 'True':
                            added_local_site = True
                    else:
                        logging.info('Site config for site %s is the same so no change.', site_name)
                        found_site = True
                        break
            if not found_site:
                # Old site is not in new sites
                logging.info('Could not find site config for site %s.  Deleting site...', old_site['site']['name'])
                self.delete_site(old_site)

        # Loop back through and check for new sites that didn't exist previously
        for new_site in new_config['config']:
            if 'site' not in new_site:
                continue
            site_found = False
            for old_site in old_config['config']:
                if 'site' not in old_site:
                    continue
                if new_site['site']['name'] == old_site['site']['name']:
                    site_found = True
                    break
            if not site_found:
                logging.info('Could not find site config for site %s.  Adding site...', new_site['site']['name'])
                self.add_site_from_config(new_site)
                if new_site['site']['local'] == 'True':
                    added_local_site = True
        return added_local_site

    def reload_config(self):
        with open(self.config_filename) as config_file:
            new_config = json.load(config_file)
        if 'config' not in new_config:
            print '%% Invalid configuration file'
            return
        old_config = self.config

        # Handle any changes in site configuration
        added_local_site = self._reload_sites(old_config, new_config)
        if added_local_site:
            self.config = new_config
            self.initialize_local_site()
            return

        # Handle any export policies for new EPGs
        for new_policy in new_config:
            if 'export' not in new_policy:
                continue
            new_export_policy = ExportPolicy(new_policy)
            policy_found = False
            for old_policy in old_config:
                if new_export_policy.has_same_epg(old_policy):
                    policy_found = True
                    break
            local_site = self.get_local_site()
            if local_site is None:
                print '%% No local site configured'
                return
            if policy_found:
                local_site.remove_policy(old_policy)
            local_site.add_policy(new_policy)
            local_site.monitor.handle_existing_endpoints(new_policy)

        # Handle any policies that have been deleted
        for old_policy in old_config:
            if 'export' not in old_policy:
                continue
            old_export_policy = ExportPolicy(old_policy)
            policy_found = False
            for new_policy in new_config:
                if old_export_policy.has_same_epg(new_policy):
                    policy_found = True
                    break
            if not policy_found:
                local_site = self.get_local_site()
                if local_site is None:
                    print '%% No local site configured'
                    return
                local_site.remove_policy(old_policy)
                self.remove_all_entries_for_policy(old_policy)

    def remove_all_entries_for_policy(self, policy):
        export_policy = ExportPolicy(policy)
        for site in export_policy.get_sites():
            site_name = site['site']['name']
            site_obj = self.get_site(site_name)
            for l3out in site['site']['interfaces']:
                l3out_name = l3out['l3out']['name']
                l3out_tenant = l3out['l3out']['tenant']
                itag = IntersiteTag(export_policy.get_tenant_name(),
                                    export_policy.get_app_name(),
                                    export_policy.get_epg_name(),
                                    site_name)
                site_obj.remove_all_entries(str(itag), l3out_name, l3out_tenant)


def initialize_tool(config):
    collector = MultisiteCollector()

    # Configure all of the sites
    for site in config['config']:
        if 'site' in site:
            collector.add_site_from_config(site)

    collector.config = config
    collector.initialize_local_site()
    return collector


class CommandLine(cmd.Cmd):
    prompt = 'intersite> '
    intro = 'Cisco ACI Intersite tool (type help for commands)'

    SHOW_CMDS = ['configfile', 'debug', 'config']
    DEBUG_CMDS = ['verbose', 'warnings', 'critical']

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
        '''
        if keyword == 'debug':
            print 'Debug level currently set to:', logging.getLevelName(logging.getLogger().getEffectiveLevel())
        elif keyword == 'configfile':
            print 'Configuration file is set to:', self.collector.config_filename
        elif keyword == 'config':
            print json.dumps(self.collector.config, indent=4, separators=(',', ':'))
        pass

    def emptyline(self):
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
        self.collector.reload_config()
        print 'Configuration reload complete'

    def do_configfile(self, filename):
        '''
        configfile <filename>
        Set the configuration file name.
        '''
        self.collector.config_filename = filename
        print 'Configuration file is set to:', self.collector.config_filename

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


def main():
    """
    Main execution routine

    :return: None
    """
    parser = argparse.ArgumentParser(description='ACI Multisite Tool')
    parser.add_argument('--config', default=None, help='Configuration file')
    parser.add_argument('--generateconfig', action='store_true', default=False,
                        help='Generate an empty example configuration file')
    parser.add_argument('--debug', nargs='?',
                        choices=['verbose', 'warnings', 'critical'],
                        const='critical',
                        help='Enable debug messages.')
    args = parser.parse_args()
    if args.debug is not None:
        if args.debug == 'verbose':
            level = logging.DEBUG
        elif args.debug == 'warnings':
            level = logging.WARNING
        else:
            level = logging.CRITICAL
    else:
        level = logging.CRITICAL
    logging.basicConfig(level=level, format='%(filename)s:%(message)s')

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

    collector = initialize_tool(config)
    collector.config_filename = args.config

    # Just wait, add any CLI here
    CommandLine(collector).cmdloop()
    while True:
        pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
