from acitoolkit.acisession import Session
from acitoolkit.acitoolkit import Tenant, AppProfile
import json


class EPGCollector(object):
    """
    Class to collect the EPG from the APIC
    """
    classes_to_rename = {'fvAEPg': 'name',
                         'fvRsProv': 'tnVzBrCPName',
                         'fvRsProtBy': 'tnVzTabooName',
                         'vzBrCP': 'name',
                         'vzTaboo': 'name',
                         'vzFilter': 'name',
                         'vzRsSubjFiltAtt': 'tnVzFilterName',
                         'vzRsDenyRule': 'tnVzFilterName'}

    classes_to_tag = ['fvAEPg']

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
                    print 'deleting dn:', data[key]['attributes']['dn']
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

    def get_epg_config(self, tenant, app, epg):
        # Create the tenant configuration and the EPG
        tenant = Tenant(tenant)
        app = AppProfile(app, tenant)
        tenant_json = tenant.get_json()

        # Grab the EPG
        epg_children_to_migrate = ['fvRsProv', 'tagInst', 'fvRsProtBy' ]
        query_url = '/api/mo/uni/tn-%s/ap-%s/epg-%s.json?query-target=self&rsp-subtree=full' % (tenant, app, epg)
        for child_class in epg_children_to_migrate:
            query_url += '&rsp-subtree-class=%s' % child_class
        query_url += '&rsp-prop-include=config-only'

        ret = self._session.get(query_url)
        epg_json = ret.json()['imdata'][0]
        tenant_json['fvTenant']['children'][0]['fvAp']['children'].append(epg_json)

        # Get the provided contracts and taboos
        provided = []
        provided_items = [('fvRsProv', 'tnVzBrCPName', 'brc'),
                          ('fvRsProtBy', 'tnVzTabooName', 'taboo')]
        # First, determine what is being provided
        for item in provided_items:
            (relation_term, relation_name, relation_url) = item
            if 'children' in epg_json['fvAEPg']:
                for child in epg_json['fvAEPg']['children']:
                    if relation_term in child:
                        name = child[relation_term]['attributes'][relation_name]
                        provided.append(name)
            # Next, get it from the APIC
            for name in provided:
                query_url = ('/api/mo/uni/tn-%s/%s-%s.json?query-target=self&rsp-subtree=full'
                             '&rsp-prop-include=config-only' % (tenant.name, relation_url, name))
                ret = self._session.get(query_url)
                provided_json = ret.json()['imdata']
                if len(provided_json):
                    tenant_json['fvTenant']['children'].append(provided_json[0])

        # Get the Filters that are being referenced
        class_names = ['vzRsSubjFiltAtt', 'vzRsDenyRule']
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

    def get_imported_epgs(self):
        pass

    def get_exported_epgs(self):
        pass

    def _rename_classes(self, data):
        if isinstance(data, list):
            for item in data:
                self._rename_classes(item)
        else:
            for key in data:
                if key in EPGCollector.classes_to_rename:
                    local_name = data[key]['attributes'][EPGCollector.classes_to_rename[key]]
                    data[key]['attributes'][EPGCollector.classes_to_rename[key]] = self.local_site_name + ':' + local_name
                if 'children' in data[key]:
                    self._rename_classes(data[key]['children'])

    def _tag_local_config(self, data):
        tag = {'tagInst': {'attributes': {'name': 'exported' + ':' + self.local_site_name}}}
        data['fvTenant']['fvAEPg']['children'].append(tag)


    def _tag_remote_config(self, data):
        if isinstance(data, list):
            for item in data:
                self._tag_remote_config(item)
        else:
            for key in data:
                if key in EPGCollector.classes_to_tag:
                    assert 'children' in data[key]
                    tag = {'tagInst': {'attributes': {'name': 'imported' + ':' + self.local_site_name}}}
                    data[key]['children'].append(tag)
                if 'children' in data[key]:
                    self._tag_remote_config(data[key]['children'])

    def export_epg_config(self, tenant_json, remote_session):
        self._rename_classes(tenant_json)
        self._tag_remote_config(tenant_json)

        self._pprint_json(tenant_json)
        resp = remote_session.push_to_apic(Tenant.get_url(), tenant_json)
        if not resp.ok:
            print resp, resp.text
            print '%% Could not export to remote APIC'

URL = 'https://172.31.216.100'
LOGIN = 'admin'
PASSWORD = 'ins3965!'
local_session  = Session(URL, LOGIN, PASSWORD)
resp = local_session.login()
if not resp.ok:
    print '%% Could not login to APIC'

collector = EPGCollector(local_session, 'siteA')
tenant_json = collector.get_epg_config('aci-toolkit-demo', 'my-demo-app', 'database-backend')

remote_session = Session(URL, LOGIN, PASSWORD)
resp = remote_session.login()
if not resp.ok:
    print '%% Could not login to APIC'

collector.export_epg_config(tenant_json, remote_session)

