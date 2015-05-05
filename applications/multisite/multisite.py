from acitoolkit.acitoolkit import *
import json
import re


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

    def _tag_local_config(self, data, contract_name):
        tag = {'tagInst': {'attributes': {'name': 'multisite:exported:contract:' + contract_name + ':sites:' + self.local_site_name}}}
        data['fvTenant']['fvAEPg']['children'].append(tag)


    def _tag_remote_config(self, data, contract_name):
        if isinstance(data, list):
            for item in data:
                self._tag_remote_config(item, contract_name)
        else:
            for key in data:
                if key in ContractCollector.classes_to_tag:
                    assert 'children' in data[key]
                    tag = {'tagInst': {'attributes': {'name': 'multisite:imported:contract:' + contract_name + ':sites:' + self.local_site_name}}}
                    data[key]['children'].append(tag)
                if 'children' in data[key]:
                    self._tag_remote_config(data[key]['children'],
                                            contract_name)

    def export_contract_config(self, tenant_json, contract_name, remote_site):
        self._rename_classes(tenant_json)
        self._tag_remote_config(tenant_json, contract_name)
        self._pprint_json(tenant_json)
        resp = remote_site.session.push_to_apic(Tenant.get_url(), tenant_json)
        if not resp.ok:
            print resp, resp.text
            print '%% Could not export to remote APIC'

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
        print 'MICHSMIT STARTING SITE', self.name
        return resp

class LocalSite(Site):
    def __init__(self, name, credentials, parent):
        super(LocalSite, self).__init__(name, credentials, local=True)
        self.contract_collector = None
        self.parent = parent

    def start(self):
        resp = super(LocalSite, self).start()
        if resp.ok:
            self.contract_collector = ContractCollector(self.session, self.name)
        return resp

    def get_contracts(self):
        resp = []
        tenants = Tenant.get_deep(self.session)
        for tenant in tenants:
            contracts = tenant.get_children(Contract)
            for contract in contracts:
                export_state = 'local'
                remote_site_names = ''
                if tenant.has_tags():
                    tags = tenant.get_tags()
                    for tag in tags:
                        match = re.match(r'multisite:.*:contract:.*:sites:.*', tag)
                        if match:
                            split_tag = tag.split(':')
                            assert len(split_tag) == 6
                            if split_tag[3] != contract.name:
                                continue
                            export_state = split_tag[1]
                            remote_site_names = split_tag[5]
                resp.append((tenant.name, contract.name, export_state, remote_site_names))
        return resp

    def extract_contract(self, contract_name, tenant_name):
        pass

    def export_contracts(self, contract_data, exported_sites):
        """
        Export the contracts

        :param contract_data: list of tuples containing contract_name and tenant_name
        :param exported_sites: list of remote_site_names
        """
        # # Reorganize the contract_data for easier access
        # contracts = {}
        # for data in contract_data:
        #     (contract_name, tenant_name) = data
        #     if tenant_name not in contracts:
        #         contracts[tenant_name] = []
        #     contracts[tenant_name].append(contract_name)
        #
        # # Get the RemoteSite instances
        # remote_sites = []
        # for remote_site in self.get_sites(remote_only=True):
        #     if remote_site.name in exported_sites:
        #         remote_sites.append(remote_site)

        old_contracts = self.get_contracts()
        prev_contracts = {}
        for old_contract in old_contracts:
            (prev_tenant_name,
             prev_contract_name,
             prev_export_state, prev_remote_site_names) = old_contract
            prev_contracts[(prev_contract_name, prev_tenant_name)] = prev_remote_site_names

        for contract in contract_data:
            if contract in prev_contracts:
                for old_exported_site in prev_contracts[contract].split('.'):
                    if old_exported_site not in exported_sites:
                        print '****DELETE*** Delete this site', old_exported_site
                        # TODO delete the contract from the old site
                first = True
                for exported_site in exported_sites:
                    if first:
                        remote_site_list = exported_site
                    else:
                        first = False
                        remote_site_list += '.' + exported_site
                for exported_site in exported_sites:
                    if exported_site not in prev_contracts[contract]:
                        print 'Export this site'
                        (contract_name, tenant_name) = contract
                        contract_json = self.contract_collector.get_contract_config(str(tenant_name),
                                                                                    str(contract_name))
                        self.contract_collector.export_contract_config(contract_json,
                                                                       contract_name,
                                                                       self.parent.get_site(exported_site))
                        #self.contract_collector._pprint_json(contract_json)

                        # Now tag the local tenant
                        tenant = Tenant(str(tenant_name))
                        print '****TAGGING**** with ', remote_site_list
                        tenant.add_tag('multisite:exported:contract:' + contract_name + ':sites:' + remote_site_list)
                        tenant.push_to_apic(self.session)


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
        print '****MICHSMIT**** Number of sites:', len(self.sites)
        for site in self.sites:
            print site.name, site.credentials.ip_address

    def export_contracts(self, contract_data, exported_sites):
        """
        Export the contracts to the remote sites

        :param contract_data: list of tuples containing contract_name and tenant_name
        :param exported_sites: list of remote_site_names
        """

        local_site = self.get_sites(local_only=True)[0]
        # TODO : there is an assumption here that there is only one local site
        assert(len(self.get_sites(local_only=True)) == 1)
        local_site.export_contracts(contract_data, exported_sites)


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