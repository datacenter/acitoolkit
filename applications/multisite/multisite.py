from acitoolkit.acitoolkit import *
import json
import re
import threading

class MultisiteMonitor(threading.Thread):
    """
    Monitor thread responsible for subscribing for local Endpoints and EPG notifications.
    """
    def __init__(self, session, local_site):
        threading.Thread.__init__(self)
        self._session = session
        self._local_site = local_site
        self._exit = False
        self.remote_sites = []

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def run(self):
        Endpoint.subscribe(self._session)
        while not self._exit:
            if Endpoint.has_events(self._session):
                print 'Endpoint Event received'
                ep = Endpoint.get_event(self._session)
                epg = ep.get_parent()
                app = epg.get_parent()
                tenant = app.get_parent()
                if self._local_site.exports_epg(epg):

                    # TODO clean up this section and also handle ep.is_deleted() == True


                    tenant = Tenant('site2')
                    outside = OutsideEPG('site2-l3out', tenant)
                    tenant = Tenant('site2')
                    outside = OutsideEPG('site2-l3out', tenant)
                    l3if1 = L3Interface('l3if1')
                    l3if1.networks.append(ep.ip)
                    l3if1.set_l3if_type('ext-svi')
                    outside.attach(l3if1)
                    for contract_db_entry in self._local_site.get_all_provided_contracts(epg):
                        contract = Contract(contract_db_entry.contract_name, tenant)
                        outside.provide(contract)
                    phyif = Interface('eth', '1', '102', '1', '25')
                    l2if = L2Interface('eth 1/102/1/25', 'vlan', '500')
                    l2if.attach(phyif)
                    l3if1.attach(l2if)
                    #for remote_site in self.remote_sites:
                        #resp = tenant.push_to_apic(remote_site.session)
                        #if not resp.ok:
                        #    print "couldn't export", resp, resp.text
                    print '*****CONFIG FOR ENDPOINT*****'
                    print json.dumps(tenant.get_json(), indent=4, separators=(',', ':'))
                    print 'Exported endpoint'



class ContractCollector(object):
    """
    Class to collect the Contract from the APIC, along with all of the providing EPGs
    """
    classes_to_rename = {'fvAEPg': 'name',
                         'fvRsProv': 'tnVzBrCPName',
                         'fvRsProtBy': 'tnVzTabooName',
                         'vzBrCP': 'name',
                         'vzTaboo': 'name',
                         'vzFilter': 'name',
                         'vzRsSubjFiltAtt': 'tnVzFilterName',
                         'vzRsDenyRule': 'tnVzFilterName'}

    classes_to_tag = ['fvAEPg', 'fvTenant']

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
        contract_children_to_migrate = ['vzSubj', 'vzRsSubjFiltAtt' ]
        query_url = '/api/mo/uni/tn-%s/brc-%s.json?query-target=self&rsp-subtree=full' % (tenant, contract)
        for child_class in contract_children_to_migrate:
            query_url += '&rsp-subtree-class=%s' % child_class
        query_url += '&rsp-prop-include=config-only'

        ret = self._session.get(query_url)
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

        # Get the EPGs providing the contract
        query_url = '/api/mo/uni/tn-%s/brc-%s.json?query-target=subtree&target-subtree-class=vzRtProv' % (tenant.name, contract)
        ret = self._session.get(query_url)
        epgs = ret.json()['imdata']
        epg_children_to_collect = ['fvRsProv', 'tagInst', 'fvRsProtBy' ]
        url_extension = '.json?query-target=self&rsp-subtree=full&rsp-prop-include=config-only'
        for child_class in epg_children_to_collect:
            url_extension += '&rsp-subtree-class=%s' % child_class
        for epg in epgs:
            query_url = '/api/mo/' + epg['vzRtProv']['attributes']['tDn'] + url_extension
            epg_json = self._session.get(query_url).json()['imdata']
            app_name = epg_json[0]['fvAEPg']['attributes']['dn'].split('tn-%s/ap-' % tenant.name)[1]
            app_name = str(app_name.split('/')[0])
            existing_apps = tenant.get_children(AppProfile)
            app_already_exists = False
            for existing_app in existing_apps:
                if existing_app.name == app_name:
                    app_already_exists = True
            if not app_already_exists:
                app = AppProfile(app_name, tenant)
                tenant_json['fvTenant']['children'].append(app.get_json())
            for child in tenant_json['fvTenant']['children']:
                if 'fvAp' in child:
                    if child['fvAp']['attributes']['name'] == app_name:
                        assert 'children' in child['fvAp']
                        child['fvAp']['children'].append(epg_json)
        self._strip_dn(tenant_json)
        return tenant_json

    @staticmethod
    def _pprint_json(data):
        print json.dumps(data, indent=4, separators=(',', ':'))

    def get_imported_contracts(self):
        pass

    def get_exported_contracts(self):
        pass

    def strip_illegal_characters(self, name):
        chars_all_good = True
        for character in name:
            if character.isalnum() or character in ('_', '.', ':', '-'):
                continue
            chars_all_good = False
            name = name.replace(character, '')
        if chars_all_good:
            return name
        return self.strip_illegal_characters(name)

    def _rename_classes(self, data):
        if isinstance(data, list):
            for item in data:
                self._rename_classes(item)
        else:
            for key in data:
                if key in ContractCollector.classes_to_rename:
                    local_name = data[key]['attributes'][ContractCollector.classes_to_rename[key]]
                    data[key]['attributes'][ContractCollector.classes_to_rename[key]] = self.strip_illegal_characters(self.local_site_name) + ':' + local_name
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

    def export_contract_config(self, tenant_json, contract_name, remote_site):
        print '*****export_contract_config*****', contract_name
        self._rename_classes(tenant_json)
        #tenant_json['fvTenant']['attributes']['name'] = 'site2' # TODO hard code the tenant name right now to make up for bad config
        self._tag_remote_config(tenant_json, contract_name)
        resp = remote_site.session.push_to_apic(Tenant.get_url(), tenant_json)
        if not resp.ok:
            print resp, resp.text
            print remote_site.name
            print Tenant.get_url()
            print tenant_json
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
        print 'MICHSMIT STARTING SITE', self.name
        return resp

class ContractDBEntry(object):
    def __init__(self):
        self.tenant_name = None
        self.contract_name = None
        self.export_state = None
        self.remote_sites = []

    def is_local(self):
        return self.export_state == 'local'

    def is_exported(self):
        return self.export_state == 'exported'

    def is_imported(self):
        return self.export_state == 'imported'

    def __eq__(self, other):
        if self.tenant_name == other.tenant_name and self.contract_name == other.contract_name:
            return True
        else:
            return False

    def add_remote_site(self, export_state, remote_site):
        self.export_state = export_state
        if remote_site not in self.remote_sites:
            self.remote_sites.append(remote_site)

    def get_remote_sites_as_string(self):
        resp = ''
        for remote_site in self.remote_sites:
            resp += remote_site + ', '
        return resp[:-2]

class ContractDB(object):
    def __init__(self):
        self._db = []

    def find_entry(self, tenant_name, contract_name):
        search_entry = ContractDBEntry()
        search_entry.tenant_name = tenant_name
        search_entry.contract_name = contract_name
        for entry in self._db:
            if entry == search_entry:
                return entry
        return None

    def add_entry(self, entry):
        self._db.append(entry)

    def add_remote_site(self, tenant_name, contract_name, export_state, remote_site_name):
        entry = self.find_entry(tenant_name, contract_name)
        entry.add_remote_site(export_state, remote_site_name)

class EpgDBEntry(object):
    def __init__(self):
        self.tenant_name = None
        self.app_name = None
        self.epg_name = None
        self.contract_name = None

class EpgDB(object):
    def __init__(self):
        self._db = []

    def add_entry(self, entry):
        self._db.append(entry)

    def find_entries(self, tenant_name, app_name, epg_name):
        resp = []
        for entry in self._db:
            if entry.tenant_name == tenant_name and entry.app_name == app_name and entry.epg_name == epg_name:
                resp.append(entry)
        return resp

class LocalSite(Site):
    def __init__(self, name, credentials, parent):
        super(LocalSite, self).__init__(name, credentials, local=True)
        self.contract_collector = None
        self.my_collector = parent
        self.monitor = None
        self.contract_db = ContractDB()
        self.epg_db = EpgDB()

    def start(self):
        resp = super(LocalSite, self).start()
        if resp.ok:
            self.contract_collector = ContractCollector(self.session, self.name)
            self.monitor = MultisiteMonitor(self.session, self)
            self.monitor.daemon = True
            self.monitor.start()
        return resp

    def _populate_contracts_from_apic(self):
        resp = []
        tenants = Tenant.get_deep(self.session, limit_to=['vzBrCP', 'fvTenant', 'tagInst'])
        for tenant in tenants:
            contracts = tenant.get_children(Contract)
            for contract in contracts:
                db_entry = ContractDBEntry()
                db_entry.tenant_name = tenant.name
                db_entry.contract_name = contract.name
                db_entry.export_state = 'local'
                self.contract_db.add_entry(db_entry)
            if tenant.has_tags():
                tags = tenant.get_tags()
                for tag in tags:
                    match = re.match(r'multisite:.*:contract:.*:site:.*', tag)
                    if match:
                        split_tag = tag.split(':')
                        assert len(split_tag) == 6
                        contract_name = split_tag[3]
                        export_state = split_tag[1]
                        remote_site_name = split_tag[5]
                        self.contract_db.add_remote_site(tenant.name, contract_name,
                                                         export_state, remote_site_name)

    def get_contracts(self):
        return self.contract_db._db

    def get_contract(self, tenant_name, contract_name):
        return self.contract_db.find_entry(tenant_name, contract_name)

    def exports_epg(self, epg):
        """
        Checks if a site is exporting a given EPG

        :param epg: Instance of EPG class to check if being exported
        :returns:  True or False.  True if the site is exporting the EPG, False otherwise.
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
            if contract_db_entry.is_exported():
                return True
        return False

    def get_all_provided_contracts(self, epg):
        resp = []
        app = epg.get_parent()
        tenant = app.get_parent()
        epg_db_entries = self.epg_db.find_entries(tenant.name, app.name, epg.name)
        for epg_db_entry in epg_db_entries:
            contract_db_entry = self.contract_db.find_entry(tenant.name, epg_db_entry.contract_name)
            resp.append(epg_db_entry)
        return resp

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
                        for contract_obj in contract_objs:
                            if contract_obj.name == contract.contract_name:
                                break
                        apps = tenant.get_children(AppProfile)
                        for app in apps:
                            epgs = app.get_children(EPG)
                            for epg in epgs:
                                if (contract.is_exported() and epg.does_provide(contract_obj)) or \
                                        (contract.is_imported() and epg.does_consume(contract_obj)):
                                    entry = EpgDBEntry()
                                    entry.tenant_name = tenant.name
                                    entry.app_name = app.name
                                    entry.epg_name = epg.name
                                    entry.contract_name = contract_obj.name
                                    self.epg_db.add_entry(entry)

    def get_epgs(self):
        return self.epg_db._db

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

    # def get_contract_names(self, tenant, app, epg):
    #     resp = []
    #     print 'get_contract_names', self.exported_epgs
    #     print 'looking for', tenant, app, epg
    #     for my_epg in self.exported_epgs:
    #         (tenant_name, app_name, epg_name, contract_name, remote_site_names) = my_epg
    #         # TODO ignoring tenant name for now due to hardcoded difference
    #         if app_name == app and epg_name == epg:
    #             resp.append(contract_name)
    #     return resp

    def extract_contract(self, contract_name, tenant_name):
        pass

    def unexport_contract(self, contract_name, tenant_name, remote_site):

        # Need to know the site, contract, and EPGs
        pass

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
                # Export to the remote site
                resp = self.contract_collector.export_contract_config(contract_json,
                                                                      contract_name,
                                                                      self.my_collector.get_site(remote_site))
                if not resp.ok:
                    problem_sites.append(remote_site)
                else:
                    # Now tag the local tenant
                    tenant = Tenant(str(tenant_name))
                    tenant.add_tag(self.contract_collector.get_local_tag(contract_name, remote_site))
                    tenant.push_to_apic(self.session)

        # compare old site list with new for sites no longer being exported to
        for old_site in old_entry.remote_sites:
            if old_site not in remote_sites:
                raise NotImplementedError  # TODO
                pass

        # update the ContractDB
        for problem_site in problem_sites:
            remote_sites.remove(problem_site)
        for remote_site in remote_sites:
            old_entry.add_remote_site('exported', remote_site)
        return problem_sites


class RemoteSite(Site):
    def __init__(self, name, credentials):
        super(RemoteSite, self).__init__(name, credentials, local=False)


class MultisiteCollector(object):
    """

    """
    def __init__(self):
        self.sites = []

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
            # TODO temporary hack to pass RemoteSite to Monitor
            for previous_site in self.sites:
                if isinstance(previous_site, LocalSite):
                    previous_site.monitor.remote_sites.append(site)
        self.sites.append(site)
        site.start()

    def delete_site(self, name):
        for site in self.sites:
            if name == site.name:
                site.shutdown()
                self.sites.remove(site)

    def print_sites(self):
        print '****MICHSMIT**** Number of sites:', len(self.sites)
        for site in self.sites:
            print site.name, site.credentials.ip_address

def main():
    """
    Main execution routine when run standalone (i.e. not GUI)

    :return: None
    """
    pass

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass