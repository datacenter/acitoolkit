################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""
Search test
"""
import unittest

import aciSearchDb
from acitoolkit.acitoolkit import (
    AppProfile, BaseContract, BGPSession, BridgeDomain, Context, Contract,
    ContractSubject, Endpoint, EPG, EPGDomain, Filter, FilterEntry, L2ExtDomain,
    L2Interface, L3ExtDomain, L3Interface, MonitorPolicy, OSPFInterface,
    OSPFInterfacePolicy, OSPFRouter, OutsideEPG, OutsideL3, PhysDomain,
    PortChannel, Subnet, Taboo, Tenant, VmmDomain
)

LIVE_TEST = False


def get_tree():
    """
    Will build an object tree with attributes in each object
    :return:
    """
    tenant = Tenant('tenant')
    tenant.dn = '/tn-tenant'
    app1 = AppProfile('app1', tenant)
    app1.dn = app1._parent.dn + '/app-app1'
    app2 = AppProfile('app2', tenant)
    app2.dn = app2._parent.dn + '/app-app2'
    epg11 = EPG('epg11', app1)
    epg11.dn = epg11._parent.dn + '/epg-epg11'
    epg12 = EPG('epg12', app1)
    epg12.dn = epg12._parent.dn + '/epg-epg12'
    epg21 = EPG('epg21', app2)
    epg21.dn = epg21._parent.dn + '/epg-epg21'
    epg22 = EPG('epg22', app2)
    epg22.dn = epg22._parent.dn + '/epg-epg22'
    bd1 = BridgeDomain('bd1', tenant)
    bd1.dn = bd1._parent.dn + '/bd-bd1'
    bd2 = BridgeDomain('bd2', tenant)
    bd2.dn = bd2._parent.dn + '/bd-bd2'
    epg11.add_bd(bd1)
    epg12.add_bd(bd2)
    epg21.add_bd(bd1)
    epg22.add_bd(bd2)
    context = Context('ctx', tenant)
    context.dn = context._parent.dn + '/ctx-ctx'
    bd1.add_context(context)
    bd2.add_context(context)
    contract1 = Contract('contract-1', tenant)
    contract1.dn = contract1._parent.dn + '/con-contract1'
    entry1 = FilterEntry('entry1',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='80',
                         dToPort='80',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='1',
                         sToPort='65535',
                         tcpRules='unspecified',
                         parent=contract1)
    subjects = contract1.get_children(ContractSubject)
    for subject in subjects:
        subject.dn = subject._parent.dn + '/subj-' + subject.name
    filters = tenant.get_children(Filter)
    for atk_filter in filters:
        atk_filter.dn = atk_filter._parent.dn + '/flt-' + atk_filter.name

    entry1.dn = entry1._parent.dn + '/flte-entry1'

    epg11.provide(contract1)
    epg11.consume(contract1)
    epg12.consume(contract1)

    epg11.value1 = 'value2'
    bd1.value2 = 'value1'
    return tenant


class Test_SearchIndexLookup(unittest.TestCase):
    """
    Checks parsing of the XML
    """
    def setUp(self):
        tree = get_tree()
        self.index = aciSearchDb.SearchIndexLookup()
        self.index.add_atk_objects(tree)

    def check_single(self, search_string, score, uids, terms):
        results = self.index.search(search_string)
        result_sorted = sorted(results[0])
        expect_sorted = sorted(uids)

        for index in range(len(uids)):
            self.assertEqual(result_sorted[index]['uid'], expect_sorted[index])
            self.assertEqual(result_sorted[index]['pscore'], score)
            self.assertEqual(result_sorted[index]['terms'][0], terms)

        self.assertEqual(results[1], len(uids))

    def check_multi(self, search_string, expected_result):
        results = self.index.search(search_string)

        for index in range(len(expected_result)):
            res = results[0][index]
            exp = expected_result[index]
            self.assertEqual(res['uid'], exp['uid'])
            self.assertEqual(res['pscore'], exp['pscore'])

        self.assertEqual(results[1], len(expected_result))

    def test_one_term(self):
        """
        Will test that the atk object tree is properly indexed
        :return:
        """
        self.check_single('#Tenant', 2, ['/tn-tenant'], "Tenant")
        self.check_single('#EPG', 2, ['/tn-tenant/app-app1/epg-epg11',
                                      '/tn-tenant/app-app1/epg-epg12',
                                      '/tn-tenant/app-app2/epg-epg21',
                                      '/tn-tenant/app-app2/epg-epg22'], "EPG")

        self.check_single('#AppProfile', 2, ['/tn-tenant/app-app1',
                                             '/tn-tenant/app-app2'], 'AppProfile')

        self.check_single('#Context', 2, ['/tn-tenant/ctx-ctx'], 'Context')
        self.check_single('#Contract', 2, ['/tn-tenant/con-contract1'], 'Contract')
        self.check_single('#ContractSubject', 2, ['/tn-tenant/con-contract1/subj-contract-1_Subject'], 'ContractSubject')
        self.check_single('@name', 2, ['/tn-tenant/app-app1/epg-epg11',
                                       '/tn-tenant/flt-entry1_Filter/flte-entry1',
                                       '/tn-tenant/app-app1/epg-epg12',
                                       '/tn-tenant/flt-entry1_Filter',
                                       '/tn-tenant/ctx-ctx',
                                       '/tn-tenant/con-contract1/subj-contract-1_Subject',
                                       '/tn-tenant/bd-bd2', '/tn-tenant/bd-bd1',
                                       '/tn-tenant/app-app2/epg-epg22',
                                       '/tn-tenant',
                                       '/tn-tenant/app-app2',
                                       '/tn-tenant/app-app1',
                                       '/tn-tenant/app-app2/epg-epg21',
                                       '/tn-tenant/con-contract1'], 'name')
        self.check_single('@unicast_route', 2, ['/tn-tenant/bd-bd2', '/tn-tenant/bd-bd1'], 'unicast_route')
        self.check_single('@bogus', 0, [], '')
        self.check_single('=no', 2, ['/tn-tenant/flt-entry1_Filter/flte-entry1',
                                     '/tn-tenant/bd-bd2',
                                     '/tn-tenant/bd-bd1'], 'no')
        self.check_single('=value1', 2, ['/tn-tenant/bd-bd1'], 'value1')
        self.check_single('=value2', 2, ['/tn-tenant/app-app1/epg-epg11'], 'value2')
        self.check_single('@value1', 2, ['/tn-tenant/app-app1/epg-epg11'], 'value1')
        self.check_single('@value2', 2, ['/tn-tenant/bd-bd1'], 'value2')
        self.check_single('*value1', 1, ['/tn-tenant/bd-bd1', '/tn-tenant/app-app1/epg-epg11'], 'value1')
        self.check_single('*Context', 1, ['/tn-tenant/ctx-ctx'], 'Context')

    def test_two_terms(self):
        """
        Will test that the atk object tree is properly indexed
        :return:
        """
        self.check_single('#BridgeDomain=no', 4, ['/tn-tenant/bd-bd2', '/tn-tenant/bd-bd1'], "('BridgeDomain', 'no')")
        self.check_single('=no#BridgeDomain', 4, ['/tn-tenant/bd-bd2', '/tn-tenant/bd-bd1'], "('BridgeDomain', 'no')")
        self.check_single('@value2=value1', 4, ['/tn-tenant/bd-bd1'], "('value2', 'value1')")
        self.check_single('@value2*value1', 3, ['/tn-tenant/bd-bd1'], "('value2', 'value1')")
        self.check_single('=value1@value2', 4, ['/tn-tenant/bd-bd1'], "('value2', 'value1')")
        self.check_single('*value2=value1', 3, ['/tn-tenant/bd-bd1'], "('value2', 'value1')")
        self.check_single('value2=value1', 3, ['/tn-tenant/bd-bd1'], "('value2', 'value1')")

    def test_three_terms(self):
        """
        Will test that the atk object tree is properly indexed
        :return:
        """
        self.check_single('#AppProfile@name=app1', 8, ['/tn-tenant/app-app1'], "('AppProfile', 'name', 'app1')")
        self.check_single('#AppProfile@name=app2', 8, ['/tn-tenant/app-app2'], "('AppProfile', 'name', 'app2')")
        self.check_single('@name#AppProfile=app2', 8, ['/tn-tenant/app-app2'], "('AppProfile', 'name', 'app2')")
        self.check_single('@name=app2#AppProfile', 8, ['/tn-tenant/app-app2'], "('AppProfile', 'name', 'app2')")
        self.check_single('#AppProfile=app2@name', 8, ['/tn-tenant/app-app2'], "('AppProfile', 'name', 'app2')")
        self.check_single('=app2#AppProfile@name', 8, ['/tn-tenant/app-app2'], "('AppProfile', 'name', 'app2')")
        self.check_single('=app2@name#AppProfile', 8, ['/tn-tenant/app-app2'], "('AppProfile', 'name', 'app2')")

        self.check_single('#BridgeDomain@arp_flood=no', 8, ['/tn-tenant/bd-bd1', '/tn-tenant/bd-bd2'],
                          "('BridgeDomain', 'arp_flood', 'no')")
        self.check_single('BridgeDomain@arp_flood=no', 6, ['/tn-tenant/bd-bd1', '/tn-tenant/bd-bd2'],
                          "('BridgeDomain', 'arp_flood', 'no')")
        self.check_single('*BridgeDomain@arp_flood=no', 6, ['/tn-tenant/bd-bd1', '/tn-tenant/bd-bd2'],
                          "('BridgeDomain', 'arp_flood', 'no')")
        self.check_single('#BridgeDomain*arp_flood=no', 6, ['/tn-tenant/bd-bd1', '/tn-tenant/bd-bd2'],
                          "('BridgeDomain', 'arp_flood', 'no')")
        self.check_single('#BridgeDomain@arp_flood*no', 6, ['/tn-tenant/bd-bd1', '/tn-tenant/bd-bd2'],
                          "('BridgeDomain', 'arp_flood', 'no')")

        # todo: score of 5 for any, any, exact match not yet implemented
        # self.check_single('BridgeDomain@arp_flood*no', 5, ['/tn-tenant/bd-bd1', '/tn-tenant/bd-bd2'])

    def test_two_ind_terms(self):
        """
        Will test that the atk object tree is properly indexed
        :return:
        """
        self.check_multi('#BridgeDomain =no', [{'uid': '/tn-tenant/bd-bd1', 'pscore': 4},
                                               {'uid': '/tn-tenant/bd-bd2', 'pscore': 4},
                                               {'uid': '/tn-tenant/flt-entry1_Filter/flte-entry1', 'pscore': 2}])

        self.check_multi('=no #BridgeDomain', [{'uid': '/tn-tenant/bd-bd1', 'pscore': 4},
                                               {'uid': '/tn-tenant/bd-bd2', 'pscore': 4},
                                               {'uid': '/tn-tenant/flt-entry1_Filter/flte-entry1', 'pscore': 2}])

        self.check_multi('#AppProfile @unicast_route', [{'uid': '/tn-tenant/app-app1', 'pscore': 2},
                                                        {'uid': '/tn-tenant/app-app2', 'pscore': 2},
                                                        {'uid': '/tn-tenant/bd-bd1', 'pscore': 2},
                                                        {'uid': '/tn-tenant/bd-bd2', 'pscore': 2}])

        self.check_multi('@unicast_route #AppProfile ', [
            {'uid': '/tn-tenant/app-app1', 'pscore': 2},
            {'uid': '/tn-tenant/app-app2', 'pscore': 2},
            {'uid': '/tn-tenant/bd-bd1', 'pscore': 2},
            {'uid': '/tn-tenant/bd-bd2', 'pscore': 2}
        ])


class Test_SearchObjectStore(unittest.TestCase):
    """
    Checks that objects are placed into the object store correctly, are cross-referenced, and
    can be retrieved correctly.
    """

    def setUp(self):
        self.tree = get_tree()
        self.store = aciSearchDb.SearchObjectStore()
        self.store.add_atk_objects(self.tree)

    def test_get_object(self):
        atk_dn = "/tn-tenant/bd-bd2"
        results = self.store.get_object_info(atk_dn)

        self.assertEqual(results['attributes']['dn'], '/tn-tenant/bd-bd2')
        self.assertEqual(results['parent']['dn'], '/tn-tenant')
        self.assertEqual(results['parent']['class'], 'Tenant')
        self.assertEqual(results['parent']['name'], 'tenant')
        self.assertEqual(results['properties']['dn'], '/tn-tenant/bd-bd2')
        self.assertEqual(results['properties']['class'], 'BridgeDomain')
        self.assertEqual(results['properties']['name'], 'bd2')
        self.assertEqual(results['relations']['context'][0]['dn'], '/tn-tenant/ctx-ctx')
        self.assertEqual(results['relations']['epgs'][0]['dn'], '/tn-tenant/app-app1/epg-epg12')

        results = self.store.get_object_info('/tn-tenant/app-app1/epg-epg12')
        self.assertEqual(results['parent']['dn'], '/tn-tenant/app-app1')
        self.assertEqual(results['parent']['class'], 'AppProfile')
        self.assertEqual(results['parent']['name'], 'app1')
        self.assertEqual(results['properties']['dn'], '/tn-tenant/app-app1/epg-epg12')
        self.assertEqual(results['properties']['class'], 'EPG')
        self.assertEqual(results['properties']['name'], 'epg12')
        self.assertEqual(results['relations']['bridge domain'][0]['dn'], '/tn-tenant/bd-bd2')
        self.assertEqual(results['relations']['consumes'][0]['dn'], '/tn-tenant/con-contract1')

        results = self.store.get_object_info('/tn-tenant/app-app1/epg-epg11')
        self.assertEqual(results['properties']['dn'], '/tn-tenant/app-app1/epg-epg11')
        self.assertEqual(results['properties']['class'], 'EPG')
        self.assertEqual(results['properties']['name'], 'epg11')
        self.assertEqual(results['relations']['consumes'][0]['dn'], '/tn-tenant/con-contract1')
        self.assertEqual(results['relations']['provides'][0]['dn'], '/tn-tenant/con-contract1')

        results = self.store.get_object_info('/tn-tenant/con-contract1')
        self.assertEqual(results['properties']['dn'], '/tn-tenant/con-contract1')
        self.assertEqual(results['properties']['class'], 'Contract')
        self.assertEqual(results['properties']['name'], 'contract-1')
        self.assertEqual(results['relations']['consumed by'][0]['dn'], '/tn-tenant/app-app1/epg-epg11')
        self.assertEqual(results['relations']['consumed by'][1]['dn'], '/tn-tenant/app-app1/epg-epg12')
        self.assertEqual(results['relations']['provided by'][0]['dn'], '/tn-tenant/app-app1/epg-epg11')

    def test_get_by_uid_short(self):
        atk_dn = ["/tn-tenant/bd-bd2", '/tn-tenant/app-app1/epg-epg11']
        results = self.store.get_by_uids_short(atk_dn)
        self.assertEqual(results['/tn-tenant/bd-bd2']['dn'], '/tn-tenant/bd-bd2')
        self.assertEqual(results['/tn-tenant/bd-bd2']['class'], 'BridgeDomain')
        self.assertEqual(results['/tn-tenant/bd-bd2']['name'], 'bd2')
        self.assertEqual(results['/tn-tenant/app-app1/epg-epg11']['dn'], '/tn-tenant/app-app1/epg-epg11')
        self.assertEqual(results['/tn-tenant/app-app1/epg-epg11']['class'], 'EPG')
        self.assertEqual(results['/tn-tenant/app-app1/epg-epg11']['name'], 'epg11')


class TestTerm(unittest.TestCase):
    """
    Test the Search class
    """

    def test_parse_class(self):
        """
        Test that it can parse a class

        :return: None
        """
        terms = aciSearchDb.Term.parse_input('#class')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'class')
        self.assertTrue(terms[0].type == 'c')
        self.assertTrue(terms[0].points == 2)

        terms = aciSearchDb.Term.parse_input('other#class')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('class', 'other'))
        self.assertTrue(terms[0].type == 'ca')
        self.assertTrue(terms[0].points == 3)
        self.assertTrue(terms[1].key == ('class', 'other'))
        self.assertTrue(terms[1].type == 'cv')
        self.assertTrue(terms[1].points == 3)

        terms = aciSearchDb.Term.parse_input('#class1@other')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class1', 'other'))
        self.assertTrue(terms[0].type == 'ca')
        self.assertTrue(terms[0].points == 4)

        terms = aciSearchDb.Term.parse_input('#class=other')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'other'))
        self.assertTrue(terms[0].type == 'cv')
        self.assertTrue(terms[0].points == 4)

        terms = aciSearchDb.Term.parse_input('#1class*other')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('1class', 'other'))
        self.assertTrue(terms[0].type == 'ca')
        self.assertTrue(terms[0].points == 3)
        self.assertTrue(terms[1].key == ('1class', 'other'))
        self.assertTrue(terms[1].type == 'cv')
        self.assertTrue(terms[1].points == 3)

        terms = aciSearchDb.Term.parse_input('#cl_ass@')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('cl_ass', ''))
        self.assertTrue(terms[0].type == 'ca')
        self.assertTrue(terms[0].points == 4)

        terms = aciSearchDb.Term.parse_input('#cl-ass=')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('cl-ass', ''))
        self.assertTrue(terms[0].type == 'cv')
        self.assertTrue(terms[0].points == 4)

        terms = aciSearchDb.Term.parse_input('#cl[ass*')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('cl[ass', ''))
        self.assertTrue(terms[0].type == 'ca')
        self.assertTrue(terms[0].points == 3)

        terms = aciSearchDb.Term.parse_input('#class#another_class')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'class')
        self.assertTrue(terms[0].type == 'c')
        self.assertTrue(terms[0].points == 2)

        terms = aciSearchDb.Term.parse_input('#class#')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'class')
        self.assertTrue(terms[0].type == 'c')
        self.assertTrue(terms[0].points == 2)

        terms = aciSearchDb.Term.parse_input('#class#')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'class')
        self.assertTrue(terms[0].type == 'c')
        self.assertTrue(terms[0].points == 2)

    def test_parse_attr(self):
        """
        Test that it can parse a class
        :return: None
        """
        terms = aciSearchDb.Term.parse_input('@attr')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'attr')
        self.assertTrue(terms[0].type == 'a')

        terms = aciSearchDb.Term.parse_input('other@attr')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('other', 'attr'))
        self.assertTrue(terms[0].type == 'ca')
        self.assertTrue(terms[1].key == ('attr', 'other'))
        self.assertTrue(terms[1].type == 'av')

        terms = aciSearchDb.Term.parse_input('@attr1#other')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('other', 'attr1'))
        self.assertTrue(terms[0].type == 'ca')

        terms = aciSearchDb.Term.parse_input('@attr=other')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('attr', 'other'))
        self.assertTrue(terms[0].type == 'av')

        terms = aciSearchDb.Term.parse_input('@1attr*other')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('other', '1attr'))
        self.assertTrue(terms[0].type == 'ca')
        self.assertTrue(terms[1].key == ('1attr', 'other'))
        self.assertTrue(terms[1].type == 'av')

        terms = aciSearchDb.Term.parse_input('@at_tr@')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'at_tr')
        self.assertTrue(terms[0].type == 'a')

        terms = aciSearchDb.Term.parse_input('@at-tr=')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('at-tr', ''))
        self.assertTrue(terms[0].type == 'av')

        terms = aciSearchDb.Term.parse_input('@at[tr*')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('', 'at[tr'))
        self.assertTrue(terms[0].type == 'ca')

        terms = aciSearchDb.Term.parse_input('@attr@another_attr')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'attr')
        self.assertTrue(terms[0].type == 'a')

        terms = aciSearchDb.Term.parse_input('@attr@')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'attr')
        self.assertTrue(terms[0].type == 'a')

    def test_parse_value(self):
        """
        Test that it can parse a value

        :return: None
        """
        terms = aciSearchDb.Term.parse_input('=value')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'value')
        self.assertTrue(terms[0].type == 'v')

        terms = aciSearchDb.Term.parse_input('other=value')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('other', 'value'))
        self.assertTrue(terms[0].type == 'cv')
        self.assertTrue(terms[1].key == ('other', 'value'))
        self.assertTrue(terms[1].type == 'av')

        terms = aciSearchDb.Term.parse_input('=value1#other')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('other', 'value1'))
        self.assertTrue(terms[0].type == 'cv')

        terms = aciSearchDb.Term.parse_input('=value@other')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('other', 'value'))
        self.assertTrue(terms[0].type == 'av')

        terms = aciSearchDb.Term.parse_input('=1value*other')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('other', '1value'))
        self.assertTrue(terms[0].type == 'cv')
        self.assertTrue(terms[1].key == ('other', '1value'))
        self.assertTrue(terms[1].type == 'av')

        terms = aciSearchDb.Term.parse_input('=va_lue#')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('', 'va_lue'))
        self.assertTrue(terms[0].type == 'cv')

        terms = aciSearchDb.Term.parse_input('=va-lue@')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('', 'va-lue'))
        self.assertTrue(terms[0].type == 'av')

        terms = aciSearchDb.Term.parse_input('=va[lue*')
        self.assertTrue(len(terms) == 2)
        self.assertTrue(terms[0].key == ('', 'va[lue'))
        self.assertTrue(terms[0].type == 'cv')

        terms = aciSearchDb.Term.parse_input('=value=another_value')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'value')
        self.assertTrue(terms[0].type == 'v')

        terms = aciSearchDb.Term.parse_input('=value=')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == 'value')
        self.assertTrue(terms[0].type == 'v')

    def test_parse_all(self):
        """
        Test that it can parse a class, attr, and value

        :return: None
        """
        terms = aciSearchDb.Term.parse_input('#class@attr=value')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 8)
        self.assertTrue(terms[0].sql ==
                        "SELECT value FROM avc WHERE class = 'class' AND attribute = 'attr' AND  value LIKE 'value%'")

        terms = aciSearchDb.Term.parse_input('@attr#class=value')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 8)
        self.assertTrue(terms[0].sql ==
                        "SELECT value FROM avc WHERE class = 'class' AND attribute = 'attr' AND  value LIKE 'value%'")

        terms = aciSearchDb.Term.parse_input('@attr=value#class')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 8)
        self.assertTrue(terms[0].sql ==
                        "SELECT class FROM avc WHERE attribute = 'attr' AND value = 'value' AND  class LIKE 'class%'")

        terms = aciSearchDb.Term.parse_input('=value@attr#class')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 8)

        terms = aciSearchDb.Term.parse_input('=value#class@attr')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 8)

        terms = aciSearchDb.Term.parse_input('@attr=value#class')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 8)

    def test_parse_all_with_any(self):
        """
        Test that it can parse a class, attr, and value

        :return: None
        """
        terms = aciSearchDb.Term.parse_input('*class@attr=value')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 6)

        terms = aciSearchDb.Term.parse_input('#class*attr=value')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 6)

        terms = aciSearchDb.Term.parse_input('#class@attr*value')
        self.assertTrue(len(terms) == 1)
        self.assertTrue(terms[0].key == ('class', 'attr', 'value'))
        self.assertTrue(terms[0].type == 'cav')
        self.assertTrue(terms[0].points == 6)

    def test_parse_single_generic(self):
        """
        Tests that a single, unqualified term will result in c, a, and v.
        :return:
        """
        terms = aciSearchDb.Term.parse_input('search_term')
        self.assertTrue(len(terms) == 3)
        self.assertTrue(terms[0].key == 'search_term')
        self.assertTrue(terms[0].type == 'c')
        self.assertTrue(terms[0].points == 1)
        self.assertTrue(terms[1].key == 'search_term')
        self.assertTrue(terms[1].type == 'a')
        self.assertTrue(terms[1].points == 1)
        self.assertTrue(terms[2].key == 'search_term')
        self.assertTrue(terms[2].type == 'v')
        self.assertTrue(terms[2].points == 1)


class TestCustomSplit(unittest.TestCase):
    def test_simple_split(self):
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split("aaa bbb"),
                         ['aaa', 'bbb'])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split("aaa bbb ccc ddd eee"),
                         ['aaa', 'bbb', "ccc", "ddd", "eee"])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split("aaa bbb "),
                         ['aaa', 'bbb'])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split(" aaa bbb"),
                         ['aaa', 'bbb'])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split(" aaa bbb "),
                         ['aaa', 'bbb'])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split('"aaa bbb" "ccc ddd" eee'),
                         ['aaa bbb', "ccc ddd", "eee"])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split('"aaa bbb" ccc "ddd efg"'),
                         ['aaa bbb', "ccc", "ddd efg"])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split('"aaa bbb" "ccc ddd" "eee'),
                         ['aaa bbb', "ccc ddd", "eee"])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split('"aaa bbb" ccc "ddd efg'),
                         ['aaa bbb', "ccc", "ddd efg"])
        self.assertEqual(aciSearchDb.SearchIndexLookup._custom_split('"aaa bbb" ccc "ddd efg '),
                         ['aaa bbb', "ccc", "ddd efg "])


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
class TestLiveAPIC(unittest.TestCase):
    def login_to_apic(self):
        """Login to the APIC
           RETURNS:  Instance of class Session
        """
        pass


if __name__ == '__main__':
    unittest.main()
