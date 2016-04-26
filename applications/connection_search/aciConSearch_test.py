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
from acitoolkit import BridgeDomain, Filter, ContractInterface
from aciConSearch import *
import radix
import copy

LIVE_TEST = False


def get_tree():
    """
        Will build an object tree with attributes in each object
        :return:
        """
    tenant = Tenant('tenant')
    tenant.dn = '/tn-tenant'
    app1 = AppProfile('app1', tenant)
    app1.dn = app1.get_parent().dn + '/app-app1'
    app2 = AppProfile('app2', tenant)
    app2.dn = app2.get_parent().dn + '/app-app2'
    epg11 = EPG('epg11', app1)
    epg11.dn = epg11.get_parent().dn + '/epg-epg11'
    for index in range(1, 5):
        ep = Endpoint('endpoint_' + str(index), epg11)
        ep.ip = '192.168.11.' + str(index)
    epg12 = EPG('epg12', app1)
    epg12.dn = epg12.get_parent().dn + '/epg-epg12'
    for index in range(1, 5):
        ep = Endpoint('endpoint_' + str(index), epg12)
        ep.ip = '192.168.12.' + str(index)
    epg21 = EPG('epg21', app2)
    epg21.dn = epg21.get_parent().dn + '/epg-epg21'
    for index in range(1, 5):
        ep = Endpoint('endpoint_' + str(index), epg21)
        ep.ip = '192.168.21.' + str(index)
    epg22 = EPG('epg22', app2)
    epg22.dn = epg22.get_parent().dn + '/epg-epg22'
    for index in range(1, 5):
        ep = Endpoint('endpoint_' + str(index), epg22)
        ep.ip = '192.168.22.' + str(index)
    bd1 = BridgeDomain('bd1', tenant)
    bd1.dn = bd1.get_parent().dn + '/bd-bd1'
    bd2 = BridgeDomain('bd2', tenant)
    bd2.dn = bd2.get_parent().dn + '/bd-bd2'
    epg11.add_bd(bd1)
    epg12.add_bd(bd2)
    epg21.add_bd(bd1)
    epg22.add_bd(bd2)
    context = Context('ctx', tenant)
    context.dn = context.get_parent().dn + '/ctx-ctx'
    bd1.add_context(context)
    bd2.add_context(context)

    outside_l3 = OutsideL3('out_l3_1', tenant)
    outside_l3.add_context(context)

    outside_epg_1 = OutsideEPG('out_epg_1', outside_l3)
    outside_epg_2 = OutsideEPG('out_epg_2', outside_l3)
    outside_epg_3 = OutsideEPG('out_epg_3', outside_l3)

    subnet_11 = OutsideNetwork('subnet_11', outside_epg_1)
    subnet_11.set_addr('10.10.1.0/24')
    subnet_12 = OutsideNetwork('subnet_12', outside_epg_1)
    subnet_12.set_addr('10.10.2.0/24')
    subnet_13 = OutsideNetwork('subnet_13', outside_epg_1)
    subnet_13.set_addr('10.10.1.0/16')

    subnet_21 = OutsideNetwork('subnet_21', outside_epg_2)
    subnet_21.set_addr('10.21.2.1/32')
    subnet_22 = OutsideNetwork('subnet_22', outside_epg_2)
    subnet_22.set_addr('10.22.2.1/32')
    subnet_23 = OutsideNetwork('subnet_23', outside_epg_2)
    subnet_23.set_addr('10.23.2.1/32')

    subnet_31 = OutsideNetwork('subnet_31', outside_epg_3)
    subnet_31.set_addr('10.30.2.1/32')
    subnet_32 = OutsideNetwork('subnet_32', outside_epg_3)
    subnet_32.set_addr('10.30.3.1/24')
    subnet_33 = OutsideNetwork('subnet_33', outside_epg_3)
    subnet_33.set_addr('10.30.2.1/25')

    contract1 = Contract('contract-1', tenant)
    contract1.dn = contract1.get_parent().dn + '/con-contract1'
    entry1 = FilterEntry('entry1',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='80',
                         dToPort='80',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract1)
    subjects = contract1.get_children(ContractSubject)
    for subject in subjects:
        subject.dn = subject.get_parent().dn + '/subj-' + subject.name
    filters = tenant.get_children(Filter)
    for atk_filter in filters:
        atk_filter.dn = atk_filter.get_parent().dn + '/flt-' + atk_filter.name

    entry1.dn = entry1.get_parent().dn + '/flte-entry1'

    contract2 = Contract('contract-2', tenant)
    contract3 = Contract('contract-3', tenant)
    contract4 = Contract('contract-4', tenant)
    entry2 = FilterEntry('entry2',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='443',
                         dToPort='443',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract2)

    entry3 = FilterEntry('entry3',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='20',
                         dToPort='25',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract3)

    entry4 = FilterEntry('entry4',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='unspecified',
                         dToPort='unspecified',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract4)

    epg11.provide(contract1)
    epg11.consume(contract1)
    epg11.provide(contract4)

    epg12.consume(contract1)
    epg12.provide(contract2)
    epg12.consume(contract3)
    epg12.provide(contract4)
    epg12.consume(contract4)

    outside_epg_1.consume(contract2)
    outside_epg_2.provide(contract3)
    outside_epg_3.consume(contract4)
    outside_epg_3.provide(contract4)

    epg21.consume(contract2)
    epg22.provide(contract4)

    return [tenant]


def get_tree2():
    """
        Will build an object tree with attributes in each object
        :return:
        """
    tenant = Tenant('tenant2')
    tenant.dn = '/tn-tenant2'
    app1 = AppProfile('t2_app1', tenant)
    app1.dn = app1.get_parent().dn + '/app-app1'
    app2 = AppProfile('t2_app2', tenant)
    app2.dn = app2.get_parent().dn + '/app-app2'
    epg11 = EPG('t2_epg11', app1)
    epg11.dn = epg11.get_parent().dn + '/epg-epg11'
    for index in range(1, 5):
        ep = Endpoint('t2_endpoint_' + str(index), epg11)
        ep.ip = '192.168.11.' + str(index)
    epg12 = EPG('t2_epg12', app1)
    epg12.dn = epg12.get_parent().dn + '/epg-epg12'
    for index in range(1, 5):
        ep = Endpoint('t2_endpoint_' + str(index), epg12)
        ep.ip = '192.169.12.' + str(index)
    epg21 = EPG('t2_epg21', app1)
    epg21.dn = epg11.get_parent().dn + '/epg-epg21'
    for index in range(1, 5):
        ep = Endpoint('t2_endpoint_' + str(index), epg21)
        ep.ip = '192.170.11.' + str(index)
    epg22 = EPG('t2_epg22', app1)
    epg22.dn = epg22.get_parent().dn + '/epg-epg22'
    for index in range(1, 5):
        ep = Endpoint('t2_endpoint_' + str(index), epg22)
        ep.ip = '192.170.12.' + str(index)
    bd1 = BridgeDomain('bd1', tenant)
    bd1.dn = bd1.get_parent().dn + '/bd-bd1'
    bd2 = BridgeDomain('bd2', tenant)
    bd2.dn = bd2.get_parent().dn + '/bd-bd2'
    bd3 = BridgeDomain('bd3', tenant)
    bd3.dn = bd3.get_parent().dn + '/bd-bd3'

    epg11.add_bd(bd1)
    epg12.add_bd(bd2)
    epg21.add_bd(bd3)
    epg22.add_bd(bd3)
    context = Context('ctx', tenant)
    context.dn = context.get_parent().dn + '/ctx-ctx'
    context2 = Context('ctx2', tenant)
    context2.dn = context.get_parent().dn + '/ctx-ctx2'
    bd1.add_context(context)
    bd2.add_context(context)
    bd3.add_context(context2)

    outside_l3 = OutsideL3('out_l3_1', tenant)
    outside_l3.add_context(context)

    outside_epg_3 = OutsideEPG('out_epg_3', outside_l3)

    subnet_31 = OutsideNetwork('subnet_31', outside_epg_3)
    subnet_31.set_addr('10.30.2.1/32')
    subnet_32 = OutsideNetwork('subnet_32', outside_epg_3)
    subnet_32.set_addr('10.30.3.1/24')
    subnet_33 = OutsideNetwork('subnet_33', outside_epg_3)
    subnet_33.set_addr('10.30.2.1/25')

    contract1 = Contract('contract-1', tenant)
    contract1.dn = contract1.get_parent().dn + '/con-contract1'
    contract2 = Contract('contract-2', tenant)
    contract2.dn = contract2.get_parent().dn + '/con-contract2'
    entry1 = FilterEntry('entry1',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='80',
                         dToPort='80',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract1)
    subjects = contract1.get_children(ContractSubject)
    for subject in subjects:
        subject.dn = subject.get_parent().dn + '/subj-' + subject.name
    filters = tenant.get_children(Filter)
    for atk_filter in filters:
        atk_filter.dn = atk_filter.get_parent().dn + '/flt-' + atk_filter.name

    entry1.dn = entry1.get_parent().dn + '/flte-entry1'

    contract4 = Contract('contract-4', tenant)
    entry3 = FilterEntry('entry3',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='443',
                         dToPort='443',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract4)

    entry4 = FilterEntry('entry4',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='80',
                         dToPort='80',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract4)

    entry4 = FilterEntry('entry4',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='unspecified',
                         dToPort='unspecified',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract2)

    epg11.provide(contract1)
    epg11.consume(contract1)

    epg12.consume(contract1)
    epg12.provide(contract1)
    epg12.provide(contract4)
    epg12.consume(contract4)

    outside_epg_3.consume(contract4)
    outside_epg_3.provide(contract4)

    epg21.consume(contract2)
    epg22.provide(contract2)

    return [tenant]


def get_tree3():
    """
        Will build an object tree with attributes in each object
        :return:
        """
    tenant = Tenant('tenant3')
    tenant.dn = '/tn-tenant3'
    app1 = AppProfile('t3_app1', tenant)
    app1.dn = app1.get_parent().dn + '/app-app1'
    app2 = AppProfile('t3_app2', tenant)
    app2.dn = app2.get_parent().dn + '/app-app2'
    epg11 = EPG('t3_epg11', app1)
    epg11.dn = epg11.get_parent().dn + '/epg-epg11'
    for index in range(1, 5):
        ep = Endpoint('t3_endpoint_' + str(index), epg11)
        ep.ip = 'abcd:168:11::' + str(index)
    epg12 = EPG('t3_epg12', app1)
    epg12.dn = epg12.get_parent().dn + '/epg-epg12'
    for index in range(1, 5):
        ep = Endpoint('t3_endpoint_' + str(index), epg12)
        ep.ip = 'abcd:169:12::' + str(index)
    epg21 = EPG('t3_epg21', app1)
    epg21.dn = epg11.get_parent().dn + '/epg-epg21'
    for index in range(1, 5):
        ep = Endpoint('t3_endpoint_' + str(index), epg21)
        ep.ip = 'abcd:170:11::' + str(index)
    epg22 = EPG('t3_epg22', app1)
    epg22.dn = epg22.get_parent().dn + '/epg-epg22'
    for index in range(1, 5):
        ep = Endpoint('t3_endpoint_' + str(index), epg22)
        ep.ip = 'abcd:170:12::' + str(index)
    bd1 = BridgeDomain('bd1', tenant)
    bd1.dn = bd1.get_parent().dn + '/bd-bd1'
    bd2 = BridgeDomain('bd2', tenant)
    bd2.dn = bd2.get_parent().dn + '/bd-bd2'
    bd3 = BridgeDomain('bd3', tenant)
    bd3.dn = bd3.get_parent().dn + '/bd-bd3'

    epg11.add_bd(bd1)
    epg12.add_bd(bd2)
    epg21.add_bd(bd3)
    epg22.add_bd(bd3)
    context = Context('ctx', tenant)
    context.dn = context.get_parent().dn + '/ctx-ctx'
    context2 = Context('ctx2', tenant)
    context2.dn = context.get_parent().dn + '/ctx-ctx2'
    bd1.add_context(context)
    bd2.add_context(context)
    bd3.add_context(context2)

    outside_l3 = OutsideL3('out_l3_1', tenant)
    outside_l3.add_context(context)

    outside_epg_3 = OutsideEPG('out_epg_3', outside_l3)

    subnet_31 = OutsideNetwork('subnet_31', outside_epg_3)
    subnet_31.set_addr('10.30.2.1/32')
    subnet_32 = OutsideNetwork('subnet_32', outside_epg_3)
    subnet_32.set_addr('10.30.3.1/24')
    subnet_33 = OutsideNetwork('subnet_33', outside_epg_3)
    subnet_33.set_addr('10.30.2.1/25')

    contract1 = Contract('contract-1', tenant)
    contract1.dn = contract1.get_parent().dn + '/con-contract1'
    contract2 = Contract('contract-2', tenant)
    contract2.dn = contract2.get_parent().dn + '/con-contract2'
    entry1 = FilterEntry('entry1',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='80',
                         dToPort='80',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract1)
    subjects = contract1.get_children(ContractSubject)
    for subject in subjects:
        subject.dn = subject.get_parent().dn + '/subj-' + subject.name
    filters = tenant.get_children(Filter)
    for atk_filter in filters:
        atk_filter.dn = atk_filter.get_parent().dn + '/flt-' + atk_filter.name

    entry1.dn = entry1.get_parent().dn + '/flte-entry1'

    contract4 = Contract('contract-4', tenant)
    entry3 = FilterEntry('entry3',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='443',
                         dToPort='443',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract4)

    entry4 = FilterEntry('entry4',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='80',
                         dToPort='80',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract4)

    entry4 = FilterEntry('entry4',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='unspecified',
                         dToPort='unspecified',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract2)

    epg11.provide(contract1)
    epg11.consume(contract1)

    epg12.consume(contract1)
    epg12.provide(contract1)
    epg12.provide(contract4)
    epg12.consume(contract4)

    outside_epg_3.consume(contract4)
    outside_epg_3.provide(contract4)

    epg21.consume(contract2)
    epg22.provide(contract2)

    return [tenant]


class TestImportData(unittest.TestCase):
    """
    Checks that the object model is correctly setup
    """

    def setUp(self):
        self.sdb = SearchDb()
        self.tenants = get_tree()
        self.sdb.build(self.tenants)

    def get_all_epgs(self):
        """
        will return list of all EPGs as a tuple (context, app_profile, epg)
        :return:
        """
        result = []
        for tenant in self.tenants:
            app_profiles = tenant.get_children(AppProfile)
            for app_profile in app_profiles:
                epgs = app_profile.get_children(EPG)
                for epg in epgs:
                    result.append(epg)
        return result

    def get_all_outside_epgs(self):
        result = []
        for tenant in self.tenants:
            outside_l3s = tenant.get_children(OutsideL3)
            for outside_l3 in outside_l3s:
                outside_epg = outside_l3.get_children(OutsideEPG)
                for epg in outside_epg:
                    result.append(epg)
        return result

    def get_all_contracts(self):
        """
        Will get a list of all contracts returned as tuple (tenant, contract)
        :return:
        """
        result = []
        for tenant in self.tenants:
            contracts = tenant.get_children(Contract)
            for contract in contracts:
                result.append((tenant, contract))
        return result

    def get_all_filter_entries(self):

        result = []
        contracts = self.get_all_contracts()
        for (tenant, contract) in contracts:
            result.extend(contract.get_children(FilterEntry))
            subjects = contract.get_children(ContractSubject)
            for subject in subjects:
                filters = subject.get_filters()
                for aci_filter in filters:
                    result.extend(aci_filter.get_children(FilterEntry))
        return result

    def test_check_context_radix(self):

        real_contexts = []
        for tenant in self.tenants:
            for context in tenant.get_children(Context):
                real_contexts.append(context)

        radix_contexts = self.sdb.context_radix.keys()

        self.assertTrue(len(radix_contexts) == len(real_contexts))
        for context in real_contexts:
            self.assertTrue(context in radix_contexts)

    def test_check_ep_in_radix(self):

        ips = set()
        for tenant in self.tenants:
            app_profiles = tenant.get_children(AppProfile)
            for app_profile in app_profiles:
                epgs = app_profile.get_children(EPG)
                for epg in epgs:
                    eps = epg.get_children(Endpoint)
                    for ep in eps:
                        ips.add(ep.ip)

        addresses = set()
        for context in self.sdb.context_radix:
            for node in self.sdb.context_radix[context]:
                if node.data['location'] == 'internal':
                    addresses.add(node.network)

        difference = addresses ^ ips
        self.assertTrue(len(difference) == 0)

    def test_check_subnet_in_radix(self):
        ips = set()
        for tenant in self.tenants:
            outside_l3s = tenant.get_children(OutsideL3)
            for outside_l3 in outside_l3s:
                outside_epg = outside_l3.get_children(OutsideEPG)
                for epg in outside_epg:
                    subnets = epg.get_children(OutsideNetwork)
                    for subnet in subnets:
                        ip = IpAddress(subnet.get_addr())
                        ips.add(ip.prefix)

        addresses = set()
        for context in self.sdb.context_radix:
            for node in self.sdb.context_radix[context]:
                if node.data['location'] == 'external':
                    addresses.add(node.prefix)

        difference = addresses ^ ips
        self.assertTrue(len(difference) == 0)

    def test_check_epg_in_radix(self):

        epgs = set(self.get_all_epgs())
        radix_epgs = set()
        for context in self.sdb.context_radix:
            for node in self.sdb.context_radix[context]:
                if node.data['location'] == 'internal':
                    radix_epgs.add(node.data['epg'])

        difference = epgs ^ radix_epgs
        self.assertTrue(len(difference) == 0)

    def test_check_outside_epg_in_radix(self):

        epgs = set(self.get_all_outside_epgs())
        radix_epgs = set()
        for context in self.sdb.context_radix:
            for node in self.sdb.context_radix[context]:
                if node.data['location'] == 'external':
                    radix_epgs.add(node.data['epg'])

        difference = epgs ^ radix_epgs
        self.assertTrue(len(difference) == 0)

    def test_check_epg_in_epg_contract(self):
        """
        will check that all epgs are indicies to epg_contract
        :return:
        """
        epgs = set(self.get_all_epgs())
        test_epgs = set()
        for epg in self.sdb.epg_contract:
            for contract_record in self.sdb.epg_contract[epg]:
                if contract_record['location'] == 'internal':
                    test_epgs.add(epg)

        difference = epgs ^ test_epgs
        self.assertTrue(len(difference) == 0)

    def test_check_outside_epg_in_epg_contract(self):
        """
        will check that all epgs are indicies to epg_contract
        :return:
        """
        epgs = set(self.get_all_outside_epgs())
        test_epgs = set()
        for epg in self.sdb.epg_contract:
            for contract_record in self.sdb.epg_contract[epg]:
                if contract_record['location'] == 'external':
                    test_epgs.add(epg)

        difference = epgs ^ test_epgs
        self.assertTrue(len(difference) == 0)

    def test_check_all_contracts_in_epg_contract(self):
        contracts = set(self.get_all_contracts())
        test_contracts = set()
        for epg in self.sdb.epg_contract:
            for contract_record in self.sdb.epg_contract[epg]:
                test_contracts.add(contract_record['contract'])
        difference = contracts ^ test_contracts
        self.assertTrue(len(difference) == 0)

    def test_epg_consume_provide(self):
        """
        will test that epg_contract has all the consume relations correct
        :return:
        """
        epgs = self.get_all_epgs()
        num_internal_epgs = len(epgs)
        epgs.extend(self.get_all_outside_epgs())
        epg_consume = set()
        for epg in epgs:
            contracts = epg.get_all_consumed()
            for contract in contracts:
                tenant = contract.get_parent()
                epg_consume.add((tenant, contract))
        epg_provide = set()
        for epg in epgs:
            contracts = epg.get_all_provided()
            for contract in contracts:
                tenant = contract.get_parent()
                epg_provide.add((tenant, contract))

        test_consume = set()
        for epg in self.sdb.epg_contract:
            for contract_record in self.sdb.epg_contract[epg]:
                if contract_record['pro_con'] == 'consume':
                    test_consume.add((contract_record['contract']))

        test_provide = set()
        for epg in self.sdb.epg_contract:
            for contract_record in self.sdb.epg_contract[epg]:
                if contract_record['pro_con'] == 'provide':
                    test_provide.add((contract_record['contract']))

        difference = epg_consume ^ test_consume

        # the difference should only be implied contracts - one per epg internal
        self.assertEqual(len(difference), num_internal_epgs)

        difference = epg_provide ^ test_provide
        self.assertEqual(len(difference), num_internal_epgs)

    def test_contract_filters(self):
        filter_entries = self.get_all_filter_entries()
        test_filters = []
        for entry in self.sdb.contract_filter:
            test_filters.extend(self.sdb.contract_filter[entry])

        self.assertTrue(len(filter_entries) == len(test_filters))
        for filter_entry in filter_entries:
            self.assertTrue(filter_entry in test_filters)


class TestImportAnyEPG(unittest.TestCase):
    """
    Checks that the object model is correctly setup
    Is different from TestImportData in that
    it adds AnyEPG to the setup
    """

    def setUp(self):
        self.sdb = SearchDb()
        self.tenants = get_tree()
        contracts = self.tenants[0].get_children(Contract)
        context = self.tenants[0].get_children(Context)[0]
        any_epg = AnyEPG('any-epg', context)
        any_epg.consume(contracts[0])
        any_epg.provide(contracts[1])

        self.sdb.build(self.tenants)

    def get_all_anyepgs(self):
        """
        will return list of all AnyEPGs as a list
        :return:
        """
        any_epgs = []
        for tenant in self.tenants:
            for context in tenant.get_children(Context):
                for any_epg in context.get_children(AnyEPG):
                    any_epgs.append(any_epg)
        return any_epgs

    def get_all_outside_epgs(self):
        result = []
        for tenant in self.tenants:
            outside_l3s = tenant.get_children(OutsideL3)
            for outside_l3 in outside_l3s:
                outside_epg = outside_l3.get_children(OutsideEPG)
                for epg in outside_epg:
                    result.append(epg)
        return result

    def get_all_contracts(self):
        """
        Will get a list of all contracts returned as tuple (tenant, contract)
        :return:
        """
        result = []
        for tenant in self.tenants:
            contracts = tenant.get_children(Contract)
            for contract in contracts:
                result.append((tenant, contract))
        return result

    def get_all_filter_entries(self):

        result = []
        contracts = self.get_all_contracts()
        for (tenant, contract) in contracts:
            result.extend(contract.get_children(FilterEntry))
            subjects = contract.get_children(ContractSubject)
            for subject in subjects:
                filters = subject.get_filters()
                for aci_filter in filters:
                    result.extend(aci_filter.get_children(FilterEntry))
        return result

    def test_anyepg_in_context(self):

        any_epgs = self.get_all_anyepgs()
        self.assertEqual(len(any_epgs), 1)
        self.assertTrue(any_epgs[0].name == 'any-epg')
        self.assertTrue(isinstance(any_epgs[0], AnyEPG))

    def test_check_anyepg_in_radix(self):

        any_epgs = set(self.get_all_anyepgs())
        radix_epgs = set()
        for context in self.sdb.context_radix:
            for node in self.sdb.context_radix[context]:
                if node.data['location'] == 'internal':
                    radix_epgs.add(node.data['any_epg'])

        difference = any_epgs ^ radix_epgs
        self.assertTrue(len(difference) == 0)

    def test_check_epg_in_epg_contract(self):
        """
        will check that all AnyEPGs are indicies to epg_contract
        :return:
        """
        epgs = set(self.get_all_anyepgs())
        test_epgs = set()
        for epg in self.sdb.epg_contract:
            if isinstance(epg, AnyEPG):
                for contract_record in self.sdb.epg_contract[epg]:
                    if contract_record['location'] == 'internal':
                        test_epgs.add(epg)

        difference = epgs ^ test_epgs
        self.assertTrue(len(difference) == 0)

    def test_check_all_contracts_in_epg_contract(self):
        contracts = set(self.get_all_contracts())
        test_contracts = set()
        for epg in self.sdb.epg_contract:
            for contract_record in self.sdb.epg_contract[epg]:
                test_contracts.add(contract_record['contract'])
        difference = contracts ^ test_contracts
        self.assertTrue(len(difference) == 0)

    def test_epg_consume_provide(self):
        """
        will test that epg_contract has all the consume relations correct
        :return:
        """
        epgs = self.get_all_anyepgs()
        epg_consume = set()
        for epg in epgs:
            contracts = epg.get_all_consumed()
            for contract in contracts:
                tenant = contract.get_parent()
                epg_consume.add((tenant, contract))
        epg_provide = set()
        for epg in epgs:
            contracts = epg.get_all_provided()
            for contract in contracts:
                tenant = contract.get_parent()
                epg_provide.add((tenant, contract))

        test_consume = set()
        test_provide = set()
        for epg in self.sdb.epg_contract:

            if isinstance(epg, AnyEPG):
                for contract_record in self.sdb.epg_contract[epg]:
                    if contract_record['pro_con'] == 'consume':
                        test_consume.add((contract_record['contract']))

                    if contract_record['pro_con'] == 'provide':
                        test_provide.add((contract_record['contract']))

        difference = epg_consume ^ test_consume

        # the difference should only be implied contracts - one per epg internal
        self.assertEqual(len(difference), 0)

        difference = epg_provide ^ test_provide
        self.assertEqual(len(difference), 0)


class TestSearch(unittest.TestCase):
    """
    Checks that the object model is correctly setup
    """

    def setUp(self):
        self.sdb = SearchDb()
        self.tenants = get_tree()
        self.sdb.build(self.tenants)

    def get_all_epgs(self):
        """
        will return list of all EPGs as a tuple (context, app_profile, epg)
        :return:
        """
        result = []
        for tenant in self.tenants:
            app_profiles = tenant.get_children(AppProfile)
            for app_profile in app_profiles:
                epgs = app_profile.get_children(EPG)
                for epg in epgs:
                    result.append((tenant, app_profile, epg))
        return result

    def get_all_outside_epgs(self):
        result = []
        for tenant in self.tenants:
            outside_l3s = tenant.get_children(OutsideL3)
            for outside_l3 in outside_l3s:
                outside_epg = outside_l3.get_children(OutsideEPG)
                for epg in outside_epg:
                    result.append((tenant, outside_l3, epg))
        return result

    def get_all_contracts(self):
        """
        Will get a list of all contracts returned as tuple (tenant, contract)
        :return:
        """
        result = []
        for tenant in self.tenants:
            contracts = tenant.get_children(Contract)
            for contract in contracts:
                result.append((tenant, contract))
        return result

    def test_exact_search(self):
        flow_spec = FlowSpec()
        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '192.168.11.1.1'
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.etherT = 'ip'
        filt1.prot = 'tcp'
        filt1.dFromPort = 80
        filt1.dToPort = 80
        flow_spec.protocol_filter.append(filt1)

        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0] == flow_spec)
        filt1.dPort = 'any'
        self.assertTrue(result[1] == flow_spec)

    def test_exact_search2(self):
        flow_spec = FlowSpec()
        flow_spec.dip = '192.168.12.1.1'
        flow_spec.sip = '192.168.11.1.2'
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.etherT = 'ip'
        filt1.prot = 'tcp'
        filt1.dFromPort = 80
        filt1.dToPort = 80
        flow_spec.protocol_filter.append(filt1)

        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.sip = '192.168.12.1.1'
        flow_spec.dip = '192.168.22.1.2'

        result = self.sdb.search(flow_spec)
        filt1.dPort = 'any'
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.1'
        flow_spec.sip = '192.168.22.1.2'

        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.sip = '192.168.21.1.1'
        flow_spec.dip = '192.168.12.1.2'
        filt1.dFromPort = 443
        filt1.dToPort = 443

        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.21.1.1'
        flow_spec.sip = '192.168.12.1.2'

        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

    def test_exact_tosubnet_search(self):
        flow_spec = FlowSpec()
        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.1.1'
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.etherT = 'ip'
        filt1.prot = 'tcp'
        filt1.dFromPort = 443
        filt1.dToPort = 443
        flow_spec.protocol_filter.append(filt1)

        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.10.1.0/24'
        self.assertTrue(result[0] == flow_spec)

    def test_exact_outside_epg_1(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        filt1.etherT = 'ip'
        filt1.dFromPort = 443
        filt1.dToPort = 443
        flow_spec.protocol_filter.append(filt1)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.2.1'
        result = self.sdb.search(flow_spec)
        flow_spec.sip = '10.10.2.0/24'
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.3.1'
        result = self.sdb.search(flow_spec)
        flow_spec.sip = '10.10.0.0/16'
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.10.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.10.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.10.3.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.21.1.2'
        flow_spec.sip = '10.10.3.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.sip = '192.168.21.1.2'
        flow_spec.dip = '10.10.3.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

    def test_exact_outside_epg_2(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.etherT = 'ip'
        filt1.prot = 'tcp'
        filt1.dFromPort = 20
        filt1.dToPort = 20
        flow_spec.protocol_filter.append(filt1)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.21.2.1'
        result = self.sdb.search(flow_spec)
        filt1.dToPort = 25
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.22.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.23.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.24.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.21.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.22.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.23.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.24.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

    def test_exact_outside_epg_3(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.etherT = 'ip'
        filt1.prot = 'tcp'
        flow_spec.protocol_filter.append(filt1)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.30.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.30.3.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.dip = '10.30.3.0/24'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.30.3.255'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.dip = '10.30.3.0/24'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.30.2.10'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.dip = '10.30.2.0/25'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.30.2.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.30.3.1'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.30.3.0/24'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.30.3.255'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.30.3.0/24'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.30.2.10'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.30.2.0/25'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.11.1.2'
        flow_spec.sip = '10.30.2.127'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.30.2.0/25'
        # self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.22.1.2'
        flow_spec.sip = '10.30.2.127'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.30.2.0/25'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.sip = '192.168.11.1.2'
        flow_spec.dip = '10.30.2.127'
        result = self.sdb.search(flow_spec)
        flow_spec.sip = '10.30.2.0/25'
        self.assertTrue(len(result) == 0)

        flow_spec.sip = '192.168.22.1.2'
        flow_spec.dip = '10.30.2.127'
        result = self.sdb.search(flow_spec)
        flow_spec.sip = '10.30.2.0/25'
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.22.1.2'
        flow_spec.sip = '10.30.2.128'
        result = self.sdb.search(flow_spec)
        flow_spec.sip = '10.30.2.0/25'
        self.assertTrue(len(result) == 0)

    def test_nonexact_outside_epg1(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.etherT = 'ip'
        filt1.prot = 'tcp'
        filt1.dFromPort = 443
        filt1.dToPort = 443
        flow_spec.protocol_filter.append(filt1)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.1.0/24'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.2.1/24'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.255.255/16'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.1.255/25'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.10.1.0/24'
        self.assertTrue(result[0] == flow_spec)

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.2.0/23'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        flow_spec.sip = '10.10.0.0/16'
        self.assertTrue(result[0] == flow_spec)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_filt1.etherT = 'ip'
        exp_filt1.prot = 'tcp'
        exp_filt1.dFromPort = 443
        exp_filt1.dToPort = 443
        exp_flow_spec.protocol_filter.append(exp_filt1)
        exp_flow_spec.dip = '192.168.12.1.2'
        exp_flow_spec.sip = '10.10.0.0/16'

        flow_spec.dip = '192.168.12.1.2'
        flow_spec.sip = '10.10.5.4/15'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.10.5.4/15'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.12.1.2/24'
        flow_spec.sip = '10.10.5.4/15'
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.dip = '192.168.12.1.2/8'
        flow_spec.sip = '10.10.5.4/15'
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

    def test_nonexact_outside_epg2(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        filt1.dFromPort = 20
        filt1.dToPort = 20
        flow_spec.protocol_filter.append(filt1)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_filt1.etherT = 'ip'
        exp_filt1.prot = 'tcp'
        exp_filt1.dFromPort = 20
        exp_filt1.dToPort = 25
        exp_filt = exp_filt1
        exp_flow_spec.protocol_filter.append(exp_filt)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.21.2.0/24'
        exp_flow_spec.sip = '192.168.12.1.2'
        exp_flow_spec.dip = '10.21.2.1/32'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.22.2.18/24'
        exp_flow_spec.sip = '192.168.12.1.2'
        exp_flow_spec.dip = '10.22.2.1/32'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.23.2.1/25'
        exp_flow_spec.sip = '192.168.12.1.2'
        exp_flow_spec.dip = '10.23.2.1/32'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.22.1.255/15'
        result = self.sdb.search(flow_spec)
        exp_flow_spec.sip = '192.168.12.1.2'
        exp_flow_spec.dip = [IpAddress('10.22.2.1/32'), IpAddress('10.23.2.1/32')]
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.sip = '192.168.12.1.2'
        flow_spec.dip = '10.21.2.0/14'
        exp_flow_spec.sip = '192.168.12.1.2'
        exp_flow_spec.dip = [IpAddress('10.21.2.1/32'), IpAddress('10.22.2.1/32'), IpAddress('10.23.2.1/32')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.sip = '192.168.12.1.2/8'
        flow_spec.dip = '10.21.5.4/13'
        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('10.21.2.1/32'), IpAddress('10.22.2.1/32'), IpAddress('10.23.2.1/32')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.dip = '192.168.12.1.2/8'
        flow_spec.sip = '10.21.5.4/13'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

    def test_nonexact_outside_epg3(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        flow_spec.protocol_filter.append(filt1)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_filt1.etherT = 'ip'
        exp_filt1.prot = 'tcp'
        exp_flow_spec.protocol_filter.append(exp_filt1)

        flow_spec.sip = '192.168.12.1.2/24'
        flow_spec.dip = '10.30.2.0/16'
        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(exp_flow_spec in result)

        flow_spec.dip = '192.168.12.1.2/24'
        flow_spec.sip = '10.30.2.0/16'
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.sip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(exp_flow_spec in result)

        flow_spec.dip = '192.168.11.1.2/24'
        flow_spec.sip = '10.30.2.0/16'
        exp_flow_spec.dip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        exp_flow_spec.sip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(exp_flow_spec in result)

        flow_spec.sip = '192.168.11.1.2/24'
        flow_spec.dip = '10.30.2.0/16'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

        flow_spec.dip = '192.168.22.1.2/24'
        flow_spec.sip = '10.30.2.0/16'
        exp_flow_spec.dip = [IpAddress('192.168.22.1/32'), IpAddress('192.168.22.4/32'), IpAddress('192.168.22.2/31')]
        exp_flow_spec.sip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(exp_flow_spec in result)

        flow_spec.sip = '192.168.22.1.2/24'
        flow_spec.dip = '10.30.2.0/16'
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 0)

    def test_multi_epg(self):

        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        flow_spec.protocol_filter.append(filt1)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_filt1.etherT = 'ip'
        exp_filt1.prot = 'tcp'
        exp_flow_spec.protocol_filter.append(exp_filt1)

        flow_spec.sip = '192.168.12.1.2/8'
        flow_spec.dip = '10.30.2.0/16'
        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        result = self.sdb.search(flow_spec)
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

        flow_spec.dip = '192.168.12.1.2/8'
        flow_spec.sip = '10.30.2.0/16'
        exp_flow_spec.sip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 3)
        exp_flow_spec.dip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        self.assertTrue(result[0] == exp_flow_spec)
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        self.assertTrue(result[1] == exp_flow_spec)
        exp_flow_spec.dip = [IpAddress('192.168.22.1/32'), IpAddress('192.168.22.4/32'), IpAddress('192.168.22.2/31')]
        self.assertTrue(result[2] == exp_flow_spec)

    def test_full(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        flow_spec.protocol_filter.append(filt1)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_filt1.etherT = 'any'
        exp_filt1.prot = 'any'
        exp_flow_spec.protocol_filter.append(exp_filt1)

        flow_spec.sip = '0/0'
        flow_spec.dip = '0/0'
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 14)

        exp_flow_spec.sip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        exp_filt1.prot = 'any'
        exp_filt1.dPort = 'any'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('10.21.2.1/32'), IpAddress('10.22.2.1/32'), IpAddress('10.23.2.1/32')]
        exp_filt1.dFromPort = 20
        exp_filt1.dToPort = 25
        exp_filt1.prot = 'tcp'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        exp_filt1.dPort = 80
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        exp_filt1.dPort = 'any'
        exp_filt1.prot = 'tcp'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_filt1.dFromPort = 'any'
        exp_filt1.dToPort = 'any'
        exp_filt1.prot = 'any'
        exp_filt1.etherT = 'any'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.22.1/32'), IpAddress('192.168.22.4/32'), IpAddress('192.168.22.2/31')]
        exp_filt1.prot = 'tcp'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_flow_spec.dip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.21.1/32'), IpAddress('192.168.21.4/32'), IpAddress('192.168.21.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_filt1.dFromPort = 443
        exp_filt1.dToPort = 443
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.21.1/32'), IpAddress('192.168.21.4/32'), IpAddress('192.168.21.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.21.1/32'), IpAddress('192.168.21.4/32'), IpAddress('192.168.21.2/31')]
        exp_filt1.dPort = 'any'
        exp_filt1.prot = 'any'
        exp_filt1.etherT = 'any'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('192.168.22.1/32'), IpAddress('192.168.22.4/32'), IpAddress('192.168.22.2/31')]
        exp_flow_spec.dip = [IpAddress('192.168.22.1/32'), IpAddress('192.168.22.4/32'), IpAddress('192.168.22.2/31')]
        exp_filt1.dFromPort = 'any'
        exp_filt1.dToPort = 'any'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        exp_flow_spec.dip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        exp_filt1.dFromPort = 'any'
        exp_filt1.dToPort = 'any'
        exp_filt1.prot = 'tcp'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]

        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('10.30.2.0/25'), IpAddress('10.30.3.0/24')]
        exp_flow_spec.dip = [IpAddress('192.168.22.1/32'), IpAddress('192.168.22.4/32'), IpAddress('192.168.22.2/31')]
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = '10.10.0.0/16'
        exp_flow_spec.dip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        exp_filt1.dFromPort = 443
        exp_filt1.dToPort = 443
        self.assertTrue(exp_flow_spec in result)

    def test_by_contract(self):
        """
        Will test that we can search by contract name
        :return:
        """
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = 'ctx'
        flow_spec.contract = 'contract-1'
        filt1 = ProtocolFilter()
        flow_spec.protocol_filter.append(filt1)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_flow_spec.protocol_filter.append(exp_filt1)
        exp_filt1.dFromPort = 80
        exp_filt1.dToPort = 80
        exp_filt1.etherT = 'ip'
        exp_filt1.prot = 'tcp'

        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 1)
        exp_flow_spec.dip = [IpAddress('192.168.11.1/32'), IpAddress('192.168.11.4/32'), IpAddress('192.168.11.2/31')]
        exp_flow_spec.sip = [IpAddress('192.168.12.1/32'), IpAddress('192.168.12.4/32'), IpAddress('192.168.12.2/31')]
        self.assertTrue(result[0] == exp_flow_spec)


class TestSearchAnyEPG(unittest.TestCase):
    """
    Checks that search works properly with AnyEPG
    """

    def setUp(self):
        self.sdb = SearchDb()
        self.tenants = get_tree2()
        tenant = self.tenants[0]
        context = tenant.get_child(Context, 'ctx')
        any_epg = AnyEPG('any-epg', context)
        contract1 = Contract('contract-any1', tenant)
        entry1 = FilterEntry('entry_any_1',
                             applyToFrag='no',
                             arpOpc='unspecified',
                             dFromPort='5000',
                             dToPort='5005',
                             etherT='ip',
                             prot='udp',
                             sFromPort='unspecified',
                             sToPort='unspecified',
                             tcpRules='unspecified',
                             parent=contract1)

        contract2 = Contract('contract-any2', tenant)
        entry2 = FilterEntry('entry_any_2',
                             applyToFrag='no',
                             arpOpc='unspecified',
                             dFromPort='6000',
                             dToPort='6005',
                             etherT='ip',
                             prot='tcp',
                             sFromPort='unspecified',
                             sToPort='unspecified',
                             tcpRules='unspecified',
                             parent=contract2)

        any_epg.consume(contract1)
        any_epg.provide(contract2)

        ap1 = AppProfile('t2_app3', tenant)
        epg31 = EPG('t2_epg31', ap1)
        epg41 = EPG('t2_epg41', ap1)
        for index in range(1, 3):
            ep = Endpoint('t2_endpoint_31_' + str(index), epg31)
            ep.ip = '192.170.31.' + str(index)

        for index in range(1, 3):
            ep = Endpoint('t2_endpoint_31_' + str(index), epg41)
            ep.ip = '192.170.41.' + str(index)

        bd1 = BridgeDomain('bdany-1', tenant)
        bd1.add_context(context)

        epg31.add_bd(bd1)
        epg41.add_bd(bd1)

        epg31.provide(contract1)
        epg41.consume(contract2)

        self.sdb.build(self.tenants)

    def test_search_all(self):
        flow_spec = FlowSpec()
        filt1 = ProtocolFilter()
        flow_spec.protocol_filter.append(filt1)

        result = self.sdb.search(flow_spec)
        self.assertEqual(len(result), 13)
        epg_result = []
        for flow in result:
            epg_result.append((flow.source_epg, flow.contract, flow.dest_epg))

        self.assertTrue(('t2_epg31', 'implied_contract_4', 't2_epg31') in epg_result)
        self.assertTrue(('t2_epg41', 'implied_contract_5', 't2_epg41') in epg_result)
        self.assertTrue(('t2_epg12', 'contract-1', 't2_epg11') in epg_result)
        self.assertTrue(('t2_epg12', 'contract-4', 'out_epg_3') in epg_result)
        self.assertTrue(('t2_epg12', 'implied_contract_1', 't2_epg12') in epg_result)
        self.assertTrue(('t2_epg22', 'implied_contract_3', 't2_epg22') in epg_result)
        self.assertTrue(('out_epg_3', 'contract-4', 't2_epg12') in epg_result)
        self.assertTrue(('t2_epg21', 'contract-2', 't2_epg22') in epg_result)
        self.assertTrue(('t2_epg21', 'implied_contract_2', 't2_epg21') in epg_result)
        self.assertTrue(('t2_epg11', 'contract-1', 't2_epg12') in epg_result)
        self.assertTrue(('t2_epg11', 'implied_contract_0', 't2_epg11') in epg_result)

        self.assertTrue(('any-epg', 'contract-any1', 't2_epg31') in epg_result)
        self.assertTrue(('t2_epg41', 'contract-any2', 'any-epg') in epg_result)

    def test_AnyEPG_ip_membership(self):
        flow_spec = FlowSpec()
        filt1 = ProtocolFilter()
        flow_spec.protocol_filter.append(filt1)

        result = self.sdb.search(flow_spec)
        self.assertEqual(len(result), 13)
        sips = []
        for flow in result:
            if flow.source_epg == 'any-epg':
                sips = flow.sip
                break

        text_sips = [str(sip) for sip in sips]

        self.assertTrue('192.169.12.4/32' in text_sips)
        self.assertTrue('192.170.41.2/32' in text_sips)
        self.assertTrue('192.170.41.1/32' in text_sips)
        self.assertTrue('192.170.31.1/32' in text_sips)
        self.assertTrue('192.170.31.2/32' in text_sips)
        self.assertTrue('192.168.11.1/32' in text_sips)
        self.assertTrue('192.168.11.4/32' in text_sips)
        self.assertTrue('192.169.12.1/32' in text_sips)
        self.assertTrue('192.169.12.3/31' in text_sips)
        self.assertTrue('192.168.11.3/31' in text_sips)


class TestSearchv6(unittest.TestCase):
    """
    Checks that the object model is correctly setup
    """

    def setUp(self):
        self.sdb = SearchDb()
        self.tenants = get_tree3()
        self.sdb.build(self.tenants)

    def test_full(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant3'
        flow_spec.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        flow_spec.protocol_filter.append(filt1)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant3'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_flow_spec.protocol_filter.append(exp_filt1)

        flow_spec.sip = '::/0'
        flow_spec.dip = '::/0'
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 4)

        exp_flow_spec.sip = [IpAddress('abcd:168:11::1/128'), IpAddress('abcd:168:11::4/128'),
                             IpAddress('abcd:168:11::2/127')]
        exp_flow_spec.dip = [IpAddress('abcd:168:11::1/128'), IpAddress('abcd:168:11::4/128'),
                             IpAddress('abcd:168:11::2/127')]
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.dip = [IpAddress('abcd:169:12::1/128'), IpAddress('abcd:169:12::4/128'),
                             IpAddress('abcd:169:12::2/127')]
        exp_flow_spec.sip = [IpAddress('abcd:168:11::1/128'), IpAddress('abcd:168:11::4/128'),
                             IpAddress('abcd:168:11::2/127')]
        exp_filt1.dFromPort = 80
        exp_filt1.dToPort = 80
        exp_filt1.prot = 'tcp'
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.sip = [IpAddress('abcd:169:12::1/128'), IpAddress('abcd:169:12::4/128'),
                             IpAddress('abcd:169:12::2/127')]
        exp_flow_spec.dip = [IpAddress('abcd:168:11::1/128'), IpAddress('abcd:168:11::4/128'),
                             IpAddress('abcd:168:11::2/127')]
        exp_filt1.dFromPort = 80
        exp_filt1.dToPort = 80
        self.assertTrue(exp_flow_spec in result)

        exp_flow_spec.dip = [IpAddress('abcd:169:12::1/128'), IpAddress('abcd:169:12::4/128'),
                             IpAddress('abcd:169:12::2/127')]
        exp_flow_spec.sip = [IpAddress('abcd:169:12::1/128'), IpAddress('abcd:169:12::4/128'),
                             IpAddress('abcd:169:12::2/127')]
        exp_filt1.dFromPort = 'any'
        exp_filt1.dToPort = 'any'
        exp_filt1.prot = 'any'
        exp_filt1.etherT = 'any'
        self.assertTrue(exp_flow_spec in result)


class TestWildcardFields(unittest.TestCase):
    def setUp(self):
        self.sdb = SearchDb()
        self.tenants = get_tree()
        self.tenants.extend(get_tree2())
        self.sdb.build(self.tenants)

    def test_multiple_filters(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant2'
        flow_spec.context_name = 'ctx'
        filt = ProtocolFilter()
        flow_spec.protocol_filter.append(filt)
        filt.prot = 'tcp'

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant2'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_filt1.etherT = 'ip'
        exp_filt1.prot = 'tcp'
        exp_filt1.dFromPort = 443
        exp_filt1.dToPort = 443
        exp_filt2 = ProtocolFilter()
        exp_filt2.etherT = 'ip'
        exp_filt2.prot = 'tcp'
        exp_filt2.dFromPort = 80
        exp_filt2.dToPort = 80
        exp_flow_spec.protocol_filter.append(exp_filt1)
        exp_flow_spec.protocol_filter.append(exp_filt2)

        flow_spec.sip = '192.169.12.1'
        flow_spec.dip = '10.30.2.1'
        exp_flow_spec.sip = '192.169.12.1'
        exp_flow_spec.dip = '10.30.2.1'
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0] == exp_flow_spec)

    def test_any_tenant(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant2'
        flow_spec.context_name = 'ctx'
        filt = ProtocolFilter()
        flow_spec.protocol_filter.append(filt)
        filt.prot = 'tcp'

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant2'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_filt1.prot = 'tcp'
        exp_flow_spec.protocol_filter.append(exp_filt1)

        flow_spec.sip = '0/0'
        flow_spec.dip = '0/0'
        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 6)

        flow_spec.tenant_name = '*'
        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 20)
        self.assertEqual(result[0].tenant_name, 'tenant')
        self.assertEqual(result[19].tenant_name, 'tenant2')

        flow_spec.tenant_name = 'tenant*'
        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 20)
        self.assertEqual(result[0].tenant_name, 'tenant')
        self.assertEqual(result[19].tenant_name, 'tenant2')

    def test_any_context(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant2'
        flow_spec.context_name = 'ctx*'
        filt = ProtocolFilter()
        flow_spec.protocol_filter.append(filt)

        flow_spec.sip = '0/0'
        flow_spec.dip = '0/0'
        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 9)
        self.assertEqual(result[0].context_name, 'ctx')
        self.assertEqual(result[8].context_name, 'ctx2')

        flow_spec.context_name = 'ctx2'
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 3)
        self.assertEqual(result[0].context_name, 'ctx2')

        flow_spec.context_name = 'ctx'
        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0].context_name, 'ctx')

        flow_spec.context_name = '*'
        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 9)
        self.assertEqual(result[0].context_name, 'ctx')
        self.assertEqual(result[8].context_name, 'ctx2')

    def test_all_wild(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = '*'
        flow_spec.context_name = '*'
        filt = ProtocolFilter()
        flow_spec.protocol_filter.append(filt)

        flow_spec.sip = '0/0'
        flow_spec.dip = '0/0'
        result = sorted(self.sdb.search(flow_spec))
        self.assertEqual(len(result), 23)

    def test_empty_epg_result(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = '*'
        filt = ProtocolFilter()
        flow_spec.protocol_filter.append(filt)

        flow_spec.sip = '192.168.21/24'
        flow_spec.dip = '192.168.21/24'
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 1)

    def test_implied_contract(self):
        flow_spec = FlowSpec()
        flow_spec.tenant_name = 'tenant'
        flow_spec.context_name = '*'
        filt = ProtocolFilter()
        flow_spec.protocol_filter.append(filt)

        flow_spec.sip = '192.168.21/24'
        flow_spec.dip = '192.168.21/24'
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 1)

        exp_flow_spec = FlowSpec()
        exp_flow_spec.tenant_name = 'tenant'
        exp_flow_spec.context_name = 'ctx'
        exp_filt1 = ProtocolFilter()
        exp_flow_spec.protocol_filter.append(exp_filt1)
        exp_flow_spec.dip = [IpAddress('192.168.21.1/32'), IpAddress('192.168.21.4/32'), IpAddress('192.168.21.2/31')]
        exp_flow_spec.sip = [IpAddress('192.168.21.1/32'), IpAddress('192.168.21.4/32'), IpAddress('192.168.21.2/31')]
        self.assertTrue(result[0] == exp_flow_spec)


class TestIpv4Address(unittest.TestCase):
    """
    Will check that IpAddress class works properly
    """

    def test_init(self):
        ip = IpAddress('1.2.3.4')
        self.assertEqual(ip.addr, '1.2.3.4')
        self.assertEqual(ip.prefixlen, 32)
        self.assertEqual(ip.prefix, '1.2.3.4/32')
        self.assertEqual(ip.min_address(), IpAddress('1.2.3.4'))
        self.assertEqual(ip.max_address(), IpAddress('1.2.3.4'))
        self.assertEqual(ip.mask, '255.255.255.255')

        ip = IpAddress('1.2.3.4/32')
        self.assertEqual(ip.addr, '1.2.3.4')
        self.assertEqual(ip.prefixlen, 32)
        self.assertEqual(ip.prefix, '1.2.3.4/32')
        self.assertEqual(ip.min_address(), IpAddress('1.2.3.4'))
        self.assertEqual(ip.max_address(), IpAddress('1.2.3.4'))

        ip = IpAddress('1.2.3.4/24')
        self.assertEqual(ip.addr, '1.2.3.4')
        self.assertEqual(ip.prefixlen, 24)
        self.assertEqual(ip.prefix, '1.2.3.0/24')
        self.assertEqual(ip.min_address(), IpAddress('1.2.3.0'))
        self.assertEqual(ip.max_address(), IpAddress('1.2.3.255'))
        self.assertEqual(ip.mask, '255.255.255.0')

    def test_compare(self):
        ip1 = IpAddress('1.2.3.4')
        ip2 = IpAddress('1.2.3.5')
        self.assertTrue(ip1 < ip2)
        self.assertTrue(ip2 > ip1)

    def test_overlap(self):
        ip1 = IpAddress('1.2.3.0/10')
        ip2 = IpAddress('1.2.3.0/9')
        self.assertEqual(ip1.overlap(ip2), IpAddress('1.2.3.0/10'))
        self.assertEqual(ip2.overlap(ip1), IpAddress('1.2.3.0/10'))

        ip3 = IpAddress('1.2.3.4/32')
        self.assertEqual(ip1.overlap(ip3), IpAddress('1.2.3.4/32'))
        self.assertEqual(ip3.overlap(ip1), IpAddress('1.2.3.4/32'))

        ip4 = IpAddress('2.2.3.4/32')
        self.assertEqual(ip1.overlap(ip4), None)

    def test_combine(self):
        ip1 = IpAddress('1.2.3.4/24')
        ip2 = IpAddress('1.2.3.4/16')
        result = Ipv4Address.combine([ip1, ip2])
        self.assertTrue(len(result) == 1)
        self.assertEqual(result[0], ip2)

        ip3 = Ipv4Address('1.3.3.4')
        ip4 = Ipv4Address('1.3.3.4/24')

        result = Ipv4Address.combine([ip1, ip2, ip3, ip4])
        self.assertTrue(len(result) == 2)
        self.assertEqual([ip4, ip2], sorted(result))

        result = Ipv4Address.combine([ip4, ip3, ip2, ip1])
        self.assertTrue(len(result) == 2)
        self.assertEqual([ip4, ip2], sorted(result))

    def test_supernet(self):
        """
        will check that supernetting work properly
        :return:
        """
        ip1 = IpAddress('4.3.2.0/24')
        ip2 = IpAddress('4.3.3.1/24')
        ip3 = IpAddress('4.3.0.0/24')
        ip4 = IpAddress('4.3.1.1/24')
        result = ip1.supernet([ip1, ip2])
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/23')))

        result = ip1.supernet([ip1, ip2, ip3, ip4])
        self.assertTrue(len(result) == 1)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/22')))

        result = sorted(ip1.supernet([ip1, ip3, ip4]))
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[1].equiv(IpAddress('4.3.1.1/23')))

        result = sorted(ip1.supernet([ip3, ip1, ip4]))
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[1].equiv(IpAddress('4.3.1.1/23')))

        result = sorted(ip1.supernet([ip1, ip4, ip3]))
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[1].equiv(IpAddress('4.3.1.1/23')))

        result = sorted(ip1.supernet([ip3, ip4, ip1]))
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[1].equiv(IpAddress('4.3.1.1/23')))

        result = sorted(ip1.supernet([ip4, ip1, ip3]))
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[1].equiv(IpAddress('4.3.1.1/23')))

        result = sorted(ip1.supernet([ip4, ip3, ip1]))
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[1].equiv(IpAddress('4.3.1.1/23')))

        ip1 = IpAddress('4.3.2.0/24')
        ip2 = IpAddress('4.3.2.1/27')
        ip3 = IpAddress('4.3.0.0/24')
        ip4 = IpAddress('4.3.1.1/24')

        result = sorted(ip1.supernet([ip1, ip2, ip3, ip4]))
        self.assertTrue(len(result) == 3)
        self.assertTrue(result[1].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[2].equiv(IpAddress('4.3.1.1/23')))
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/27')))

    def test_simplify(self):
        ip1 = IpAddress('4.3.2.0/24')
        ip2 = IpAddress('4.3.2.1/27')
        ip3 = IpAddress('4.3.0.0/24')
        ip4 = IpAddress('4.3.1.1/24')

        result = sorted(ip1.simplify([ip1, ip2, ip3, ip4]))
        self.assertTrue(len(result) == 2)
        self.assertTrue(result[0].equiv(IpAddress('4.3.2.1/24')))
        self.assertTrue(result[1].equiv(IpAddress('4.3.1.1/23')))

    def test_null_init(self):
        ip1 = IpAddress('')
        self.assertEqual(str(ip1), '0.0.0.0/0')


class TestIpv6Address(unittest.TestCase):
    """
    Will check that IpAddress class works properly
    """

    def test_input_ipv6(self):
        ip1 = IpAddress('2004:1:2:1::1:0:8')
        self.assertEqual(str(ip1), '2004:1:2:1:0:1:0:8/128')
        self.assertEqual(ip1.prefixlen, 128)

        ip1 = IpAddress('2004:1:2::1:0:8')
        self.assertEqual(str(ip1), '2004:1:2::1:0:8/128')

        ip1 = IpAddress('2004::8')
        self.assertEqual(str(ip1), '2004::8/128')
        self.assertEqual(ip1.prefixlen, 128)

        ip1 = IpAddress('2004::')
        self.assertEqual(str(ip1), '2004::/128')

        ip1 = IpAddress('::1:2:3')
        self.assertEqual(str(ip1), '::1:2:3/128')

        ip1 = IpAddress('::')
        self.assertEqual(str(ip1), '::/128')
        self.assertEqual(ip1.prefixlen, 128)

        ip1 = IpAddress('0:4:3:2:1:2:3:4')
        self.assertEqual(str(ip1), '0:4:3:2:1:2:3:4/128')

        ip1 = IpAddress('0:0:3:2:1:2:3:4')
        self.assertEqual(str(ip1), '::3:2:1:2:3:4/128')

        ip1 = IpAddress('0:0:0:2:1:2:3:4')
        self.assertEqual(str(ip1), '::2:1:2:3:4/128')

        ip1 = IpAddress('0:0:0:0:1:2:3:4')
        self.assertEqual(str(ip1), '::1:2:3:4/128')

        ip1 = IpAddress('0:0:0:0:0:2:3:4')
        self.assertEqual(str(ip1), '::2:3:4/128')

        ip1 = IpAddress('0:0:0:0:0:0:3:4')
        self.assertEqual(str(ip1), '::3:4/128')

        ip1 = IpAddress('0:0:0:0:0:0:0:4')
        self.assertEqual(str(ip1), '::4/128')

        ip1 = IpAddress('0:0:0:0:0:0:0:0')
        self.assertEqual(str(ip1), '::/128')

        ip1 = IpAddress('1:0:0:0:0:0:0:0')
        self.assertEqual(str(ip1), '1::/128')

        ip1 = IpAddress('1:2:0:0:0:0:0:0')
        self.assertEqual(str(ip1), '1:2::/128')

        ip1 = IpAddress('1:2:3:0:0:0:0:0')
        self.assertEqual(str(ip1), '1:2:3::/128')

        ip1 = IpAddress('1:2:3:4:0:0:0:0')
        self.assertEqual(str(ip1), '1:2:3:4::/128')

        ip1 = IpAddress('1:2:3:4:5:0:0:0')
        self.assertEqual(str(ip1), '1:2:3:4:5::/128')

        ip1 = IpAddress('1:2:3:4:5:6:0:0')
        self.assertEqual(str(ip1), '1:2:3:4:5:6::/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:0')
        self.assertEqual(str(ip1), '1:2:3:4:5:6:7:0/128')

        ip1 = IpAddress('1:0:0:4:5:6:7:0')
        self.assertEqual(str(ip1), '1::4:5:6:7:0/128')

        ip1 = IpAddress('1:0:0:0:5:6:7:0')
        self.assertEqual(str(ip1), '1::5:6:7:0/128')

        ip1 = IpAddress('1:0:0:0:0:6:7:0')
        self.assertEqual(str(ip1), '1::6:7:0/128')

        ip1 = IpAddress('1:0:0:0:0:0:7:8')
        self.assertEqual(str(ip1), '1::7:8/128')

        ip1 = IpAddress('1:0:0:0:0:0:0:8')
        self.assertEqual(str(ip1), '1::8/128')

        ip1 = IpAddress('1:0:0:2:0:0:0:8')
        self.assertEqual(str(ip1), '1:0:0:2::8/128')

        ip1 = IpAddress('1:0:0:0:2:0:0:8')
        self.assertEqual(str(ip1), '1::2:0:0:8/128')

        ip1 = IpAddress('1:0:0:0:2:0:0:0')
        self.assertEqual(str(ip1), '1::2:0:0:0/128')

        ip1 = IpAddress('abcd:ef01:2345:6789::')
        self.assertEqual(str(ip1), 'abcd:ef01:2345:6789::/128')

        ip1 = IpAddress('ABCD:ef01:2345:6789::')
        self.assertEqual(str(ip1), 'abcd:ef01:2345:6789::/128')

    def test_prefixlen(self):
        ip1 = IpAddress('1234::/3')
        self.assertEqual(ip1.prefixlen, 3)

        ip1 = IpAddress('1234::/24')
        self.assertEqual(ip1.prefixlen, 24)

    def test_max_address(self):
        ip1 = IpAddress('1:2:3:4:5:6:7:8/64')
        self.assertEqual(str(ip1.max_address()), '1:2:3:4:ffff:ffff:ffff:ffff/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/65')
        self.assertEqual(str(ip1.max_address()), '1:2:3:4:7fff:ffff:ffff:ffff/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/72')
        self.assertEqual(str(ip1.max_address()), '1:2:3:4:ff:ffff:ffff:ffff/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/76')
        self.assertEqual(str(ip1.max_address()), '1:2:3:4:f:ffff:ffff:ffff/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/78')
        self.assertEqual(str(ip1.max_address()), '1:2:3:4:7:ffff:ffff:ffff/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/79')
        self.assertEqual(str(ip1.max_address()), '1:2:3:4:5:ffff:ffff:ffff/128')

    def test_min_address(self):
        ip1 = IpAddress('1:2:3:4:5:6:7:8/64')
        self.assertEqual(str(ip1.min_address()), '1:2:3:4::/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/65')
        self.assertEqual(str(ip1.min_address()), '1:2:3:4::/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/72')
        self.assertEqual(str(ip1.min_address()), '1:2:3:4::/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/76')
        self.assertEqual(str(ip1.min_address()), '1:2:3:4::/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/78')
        self.assertEqual(str(ip1.min_address()), '1:2:3:4:4::/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/79')
        self.assertEqual(str(ip1.min_address()), '1:2:3:4:4::/128')

        ip1 = IpAddress('1:2:3:4:5:6:7:8/80')
        self.assertEqual(str(ip1.min_address()), '1:2:3:4:5::/128')

    def test_compare(self):
        ip1 = IpAddress('1:2:3:4:5:6:7:8')
        ip2 = IpAddress('1:2:3:4:5:6:7:8')
        self.assertEqual(ip1, ip2)

        ip3 = IpAddress('1:2:3:4:5:6:7:9')
        self.assertTrue(ip1 < ip3)
        self.assertFalse(ip1 > ip3)
        self.assertTrue(ip3 > ip1)
        self.assertFalse(ip3 < ip1)

        ip4 = IpAddress('1:2:3:6:5:6:7:8')
        self.assertTrue(ip1 <= ip4)
        self.assertFalse(ip1 >= ip4)
        self.assertTrue(ip4 >= ip1)
        self.assertFalse(ip4 <= ip1)

        self.assertTrue(ip1 <= ip2)
        self.assertTrue(ip2 >= ip1)

        self.assertTrue(ip1 != ip3)
        self.assertFalse(ip1 != ip2)
        self.assertFalse(ip1 == ip3)

    def test_encompass(self):
        ip1 = IpAddress('1:2:3:4:5:6:7:8/64')
        ip2 = IpAddress('1:2:3:4:5:6:71:8/70')
        ip3 = IpAddress('1:2:4:4:5:6:72:8/64')
        self.assertTrue(Ipv6Address.encompass(ip1, ip2))
        self.assertFalse(Ipv6Address.encompass(ip2, ip1))
        self.assertFalse(Ipv6Address.encompass(ip3, ip2))

        ip1 = IpAddress('1:2:3:4::/64')
        ip2 = IpAddress('1:2:3:4:5::/80')
        ip3 = IpAddress('1:2:3:4:5:6:72:8/128')
        self.assertTrue(Ipv6Address.encompass(ip1, ip2))
        self.assertTrue(Ipv6Address.encompass(ip1, ip3))
        self.assertTrue(Ipv6Address.encompass(ip2, ip3))

        self.assertFalse(Ipv6Address.encompass(ip2, ip1))
        self.assertFalse(Ipv6Address.encompass(ip3, ip1))
        self.assertFalse(Ipv6Address.encompass(ip3, ip2))

    def test_combine(self):
        ip1 = IpAddress('1:2:3:4::/64')
        ip2 = IpAddress('1:2:3:4:5::/80')
        ip3 = IpAddress('1:2:3:4:5:6:72:8/128')
        ip4 = IpAddress('1:2:3:5::/64')
        result = Ipv6Address.combine([ip1, ip2, ip3, ip4])
        self.assertEqual(len(result), 2)
        self.assertTrue(ip1 in result)
        self.assertTrue(ip4 in result)

    def test_overlap(self):
        ip1 = IpAddress('1:2:3:4::/64')
        ip2 = IpAddress('1:2:3:4:5::/80')
        self.assertEqual(ip1.overlap(ip2), ip2)
        self.assertEqual(ip2.overlap(ip1), ip2)

    def test_supernet(self):
        ip1 = IpAddress('1:2:3:4:4:/80')
        ip2 = IpAddress('1:2:3:4:5::/80')
        ip3 = IpAddress('1:2:3:5:4:/80')
        ip4 = IpAddress('1:2:3:5:5::/80')
        result = Ipv6Address.supernet([ip1, ip2, ip3, ip4])
        self.assertEqual(len(result), 2)
        self.assertTrue(IpAddress('1:2:3:4:4:/79') in result)
        self.assertTrue(IpAddress('1:2:3:5:4:/79') in result)

        ip1 = IpAddress('1:2:0:4:4:/48')
        ip2 = IpAddress('1:2:1:4:5::/48')
        ip3 = IpAddress('1:2:2:5:4:/48')
        ip4 = IpAddress('1:2:3:5:5::/48')
        result = Ipv6Address.supernet([ip1, ip2, ip3, ip4])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], IpAddress('1:2::/46'))

        ip1 = IpAddress('1:2:0:4:4:/48')
        ip2 = IpAddress('1:2:0:4:4:/48')
        ip3 = IpAddress('1:2:2:5:4:/48')
        ip4 = IpAddress('1:2:2:5:4:/48')
        result = Ipv6Address.supernet([ip1, ip2, ip3, ip4])
        self.assertEqual(len(result), 2)
        self.assertTrue(IpAddress('1:2:0:4:4:/48') in result)
        self.assertTrue(IpAddress('1:2:2:5:4:/48') in result)

        ip1 = IpAddress('1:2:0:4:4:/48')
        ip2 = IpAddress('1:2:1:4:4:/48')
        ip3 = IpAddress('1:2:2:5:4:/48')
        ip4 = IpAddress('1:2:2:5:4:/48')
        ip5 = IpAddress('1:2:3:5:4:/48')
        result = Ipv6Address.supernet([ip1, ip2, ip3, ip4, ip5])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], IpAddress('1:2:0::/46'))


class TestProtocolFilter(unittest.TestCase):
    def test_load_aci_filter(self):
        entry3 = FilterEntry('entry3',
                             applyToFrag='no',
                             arpOpc='unspecified',
                             dFromPort='443',
                             dToPort='443',
                             etherT='ip',
                             prot='tcp',
                             sFromPort='unspecified',
                             sToPort='unspecified',
                             tcpRules='unspecified',
                             parent=None)
        filt = ProtocolFilter(entry3)
        self.assertEqual(filt.applyToFrag, False)
        self.assertEqual(filt.arpOpc, 'any')
        self.assertEqual(filt.dFromPort, 443)
        self.assertEqual(filt.dToPort, 443)
        self.assertEqual(filt.etherT, 'ip')
        self.assertEqual(filt.prot, 'tcp')
        self.assertEqual(filt.sFromPort, 'any')
        self.assertEqual(filt.sToPort, 'any')
        self.assertEqual(filt.tcpRules, 'any')

        entry3 = FilterEntry('entry3',
                             applyToFrag='yes',
                             arpOpc='resp',
                             dFromPort='80',
                             dToPort='85',
                             etherT='icmp',
                             prot='udp',
                             sFromPort='10',
                             sToPort='20',
                             tcpRules='syn',
                             parent=None)
        filt = ProtocolFilter(entry3)
        self.assertEqual(filt.applyToFrag, True)
        self.assertEqual(filt.arpOpc, 'resp')
        self.assertEqual(filt.dFromPort, 80)
        self.assertEqual(filt.dToPort, 85)
        self.assertEqual(filt.etherT, 'icmp')
        self.assertEqual(filt.prot, 'udp')
        self.assertEqual(filt.sFromPort, 10)
        self.assertEqual(filt.sToPort, 20)
        self.assertEqual(filt.tcpRules, 'syn')

    def test_overlap(self):
        filt1 = ProtocolFilter()
        filt2 = ProtocolFilter()
        filt1.applyToFrag = 'no'
        filt1.arpOpc = 'unspecified'
        filt1.dFromPort = '20'
        filt1.dToPort = '40'
        filt1.etherT = 'any'
        filt1.prot = 'tcp'
        filt1.sFromPort = '100'
        filt1.sToPort = '500'
        filt1.tcpRules = 'rst'

        filt2.applyToFrag = '*'
        filt2.arpOpc = 'req'
        filt2.dFromPort = '10'
        filt2.dToPort = '30'
        filt2.etherT = 'ip'
        filt2.prot = 'any'
        filt2.sFromPort = '200'
        filt2.sToPort = '300'
        filt2.tcpRules = 'unspecified'

        filt3 = filt1.overlap(filt2)
        filt4 = ProtocolFilter()
        filt4.applyToFrag = False
        filt4.arpOpc = 'req'
        filt4.dFromPort = '20'
        filt4.dToPort = '30'
        filt4.etherT = 'ip'
        filt4.prot = 'tcp'
        filt4.sFromPort = '200'
        filt4.sToPort = '300'
        filt4.tcpRules = 'rst'

        self.assertEqual(filt3, filt4)
        filt3 = filt2.overlap(filt1)
        self.assertEqual(filt3, filt4)

        filt2.applyToFrag = 'yes'
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt2.applyToFrag = 'any'
        filt1.arpOpc = 'ack'
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt1.arpOpc = 'any'
        filt1.etherT = 'icmp'
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt2.etherT = 'icmp'
        filt2.prot = 'udp'
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt1.prot = 'udp'
        filt2.tcpRules = 'syn'
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt2.prot = 'udp'
        filt1.tcpRules = 'syn'
        filt4.prot = 'udp'
        filt4.tcpRules = 'syn'
        filt4.etherT = 'icmp'
        filt4.arpOpc = 'ack'
        filt3 = filt1.overlap(filt2)
        self.assertNotEqual(filt3, filt4)
        filt3 = filt2.overlap(filt1)
        self.assertNotEqual(filt3, filt4)
        filt4.arpOpc = 'req'
        filt3 = filt1.overlap(filt2)
        self.assertEqual(filt3, filt4)
        filt3 = filt2.overlap(filt1)
        self.assertEqual(filt3, filt4)

        filt1.dFromPort = '2'
        filt1.dToPort = '9'
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt1.dFromPort = '2000'
        filt1.dToPort = '9000'
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt2.dFromPort = '2000'
        filt2.dToPort = '9000'
        filt1.sFromPort = 3
        filt1.sToPort = 6
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt1.sFromPort = 10000
        filt1.sToPort = 20000
        filt3 = filt1.overlap(filt2)
        self.assertTrue(filt3 is None)
        filt3 = filt2.overlap(filt1)
        self.assertTrue(filt3 is None)

        filt1.sFromPort = 250
        filt4.sFromPort = 250
        filt4.sToPort = 300
        filt4.dToPort = 9000
        filt4.dFromPort = 2000
        filt3 = filt1.overlap(filt2)
        self.assertEqual(filt3, filt4)
        filt3 = filt2.overlap(filt1)
        self.assertEqual(filt3, filt4)

    def test_default(self):
        filt1 = ProtocolFilter()
        self.assertEqual(filt1.applyToFrag, 'any')
        self.assertEqual(filt1.arpOpc, 'any')
        self.assertEqual(filt1.dFromPort, 'any')
        self.assertEqual(filt1.dToPort, 'any')
        self.assertEqual(filt1.etherT, 'any')
        self.assertEqual(filt1.prot, 'any')
        self.assertEqual(filt1.sFromPort, 'any')
        self.assertEqual(filt1.sToPort, 'any')
        self.assertEqual(filt1.tcpRules, 'any')

    def check_all_combos_a_lt_b(self, a, b):
        self.assertFalse(a == b)
        self.assertTrue(a != b)
        self.assertFalse(a >= b)
        self.assertFalse(a > b)
        self.assertTrue(a <= b)
        self.assertTrue(a < b)
        self.assertFalse(b == a)
        self.assertTrue(b != a)
        self.assertFalse(b <= a)
        self.assertFalse(b < a)
        self.assertTrue(b >= a)
        self.assertTrue(b > a)

    def test_compare(self):
        filt1 = ProtocolFilter()
        filt2 = ProtocolFilter()
        filt1.applyToFrag = 'no'
        filt1.arpOpc = 'unspecified'
        filt1.dFromPort = '20'
        filt1.dToPort = '40'
        filt1.etherT = 'any'
        filt1.prot = 'tcp'
        filt1.sFromPort = '100'
        filt1.sToPort = '500'
        filt1.tcpRules = 'rst'

        filt2.applyToFrag = 'no'
        filt2.arpOpc = 'unspecified'
        filt2.dFromPort = '20'
        filt2.dToPort = '40'
        filt2.etherT = 'any'
        filt2.prot = 'tcp'
        filt2.sFromPort = '100'
        filt2.sToPort = '500'
        filt2.tcpRules = 'rst'

        self.assertTrue(filt1 == filt2)
        self.assertFalse(filt1 != filt2)
        self.assertTrue(filt1 >= filt2)
        self.assertFalse(filt1 > filt2)
        self.assertTrue(filt1 <= filt2)
        self.assertFalse(filt1 < filt2)

        filt2.applyToFrag = 'any'

        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.applyToFrag = 'no'
        filt2.arpOpc = 'req'
        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.arpOpc = 'any'
        filt2.dFromPort = 21
        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.dFromPort = 20
        filt2.dToPort = 41

        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.dToPort = 40
        filt2.etherT = 'ip'
        filt1.etherT = 'any'

        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.etherT = 'any'
        filt2.prot = 'udp'
        filt2.etherT = 'any'

        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.prot = 'tcp'
        filt2.sFromPort = '101'
        filt2.etherT = 'any'
        filt2.etherT = 'any'

        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.sFromPort = '100'
        filt2.sToPort = '501'
        filt2.etherT = 'any'

        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.sToPort = '500'
        filt2.tcpRules = 'syn'
        filt2.etherT = 'any'

        self.check_all_combos_a_lt_b(filt1, filt2)

        filt2.tcpRules = 'rst'

        self.assertEqual(filt1, filt2)


class TestArgs(unittest.TestCase):
    """
    Will test that the command line arguments are parsed correctly to build a flow spec
    """

    def test_parse_port_range(self):
        text = 'any'
        (r1, r2) = parse_port_range(text)
        self.assertEqual(r1, 'any')
        self.assertEqual(r2, 'any')

        text = '80-83'
        (r1, r2) = parse_port_range(text)
        self.assertEqual(r1, '80')
        self.assertEqual(r2, '83')

        text = '81 -82'
        (r1, r2) = parse_port_range(text)
        self.assertEqual(r1, '81')
        self.assertEqual(r2, '82')

        text = '81 - 82'
        (r1, r2) = parse_port_range(text)
        self.assertEqual(r1, '81')
        self.assertEqual(r2, '82')

        text = '81 82'
        self.assertRaises(ValueError, parse_port_range, text)

        text = '81, 82'
        self.assertRaises(ValueError, parse_port_range, text)

    def test_input_args(self):
        class ARGS:
            def __init__(self):
                pass

        args = ARGS()
        args.tenant = 'tenant'
        args.context = 'context'
        args.etherT = 'ip'
        args.sip = '1.2.3.4/20'
        args.dip = '10.20.30.40/32'
        args.applyToFrag = 'yes'
        args.arpOpc = 'req'
        args.etherT = 'ip'
        args.prot = 'tcp'
        args.tcpRules = 'syn'
        args.dport = 'any'
        args.sport = 'any'

        flow_spec = build_flow_spec_from_args(args)

        self.assertEqual(flow_spec.tenant_name, 'tenant')
        self.assertEqual(flow_spec.context_name, 'context')
        self.assertTrue(len(flow_spec.protocol_filter) == 1)
        pf = flow_spec.protocol_filter[0]
        self.assertEqual(pf.applyToFrag, True)
        self.assertEqual(pf.arpOpc, 'req')
        self.assertEqual(pf.etherT, 'ip')
        self.assertEqual(pf.prot, 'tcp')
        self.assertEqual(pf.tcpRules, 'syn')
        self.assertEqual(pf.dFromPort, 'any')
        self.assertEqual(pf.dToPort, 'any')
        self.assertEqual(pf.sFromPort, 'any')
        self.assertEqual(pf.sToPort, 'any')

        args.dport = '80'
        args.sport = '443'
        flow_spec = build_flow_spec_from_args(args)
        self.assertEqual(flow_spec.protocol_filter[0].dFromPort, 80)
        self.assertEqual(flow_spec.protocol_filter[0].dToPort, 80)
        self.assertEqual(flow_spec.protocol_filter[0].sFromPort, 443)
        self.assertEqual(flow_spec.protocol_filter[0].sToPort, 443)

        args.dport = '80-85'
        args.sport = '443 - 1000'
        flow_spec = build_flow_spec_from_args(args)
        self.assertEqual(flow_spec.protocol_filter[0].dFromPort, 80)
        self.assertEqual(flow_spec.protocol_filter[0].dToPort, 85)
        self.assertEqual(flow_spec.protocol_filter[0].sFromPort, 443)
        self.assertEqual(flow_spec.protocol_filter[0].sToPort, 1000)


class TestRadix(unittest.TestCase):
    """
    Will test the radix library
    """

    def test_find_best(self):
        r = radix.Radix()
        r.add('1.2.3.4')
        r.add('1.2.3.5')
        r.add('1.2.3.6')
        r.add('1.2.4.4')
        r.add('1.2.4.5')
        r.add('1.2.4.6')
        r.add('1.2.3.0/24')
        r.add('1.2.4.0/24')
        r.add('1.2.0.0/16')
        r.add('1.3.0.0/16')
        r.add('1.0.0.0/8')
        r.add('2.0.0.0/8')
        r.add('0.0.0.0/0')

        self.assertEqual('1.2.3.4/32', r.search_best('1.2.3.4').prefix)
        self.assertEqual('1.2.3.5/32', r.search_best('1.2.3.5').prefix)
        self.assertEqual('1.2.3.6/32', r.search_best('1.2.3.6').prefix)
        self.assertEqual('1.2.3.0/24', r.search_best('1.2.3.7').prefix)
        self.assertEqual('1.2.4.4/32', r.search_best('1.2.4.4').prefix)
        self.assertEqual('1.2.4.5/32', r.search_best('1.2.4.5').prefix)
        self.assertEqual('1.2.4.6/32', r.search_best('1.2.4.6').prefix)
        self.assertEqual('1.2.4.0/24', r.search_best('1.2.4.7').prefix)

        self.assertEqual('1.2.3.0/24', r.search_best('1.2.3.0/24').prefix)
        self.assertEqual('1.2.0.0/16', r.search_best('1.2.5.4/32').prefix)
        self.assertEqual('1.2.0.0/16', r.search_best('1.2.6.0/24').prefix)

        self.assertEqual('1.3.0.0/16', r.search_best('1.3.6.0/24').prefix)

        self.assertEqual('1.0.0.0/8', r.search_best('1.4.6.0/24').prefix)
        self.assertEqual('2.0.0.0/8', r.search_best('2.4.6.4').prefix)

        self.assertEqual('0.0.0.0/0', r.search_best('3.4.6.4').prefix)

    def test_find_covered(self):
        r = radix.Radix()
        r.add('1.2.3.4')
        r.add('1.2.3.5')
        r.add('1.2.3.6')
        r.add('1.2.4.4')
        r.add('1.2.4.5')
        r.add('1.2.4.6')
        r.add('1.2.3.0/24')
        r.add('1.2.4.0/24')
        r.add('1.2.0.0/16')
        r.add('1.3.0.0/16')
        r.add('1.0.0.0/8')
        r.add('2.0.0.0/8')
        r.add('0.0.0.0/0')

        result = r.search_covered('1.2.3.4/32')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].prefix, '1.2.3.4/32')

        result = r.search_covered('1.2.3.5/32')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].prefix, '1.2.3.5/32')

        result = r.search_covered('1.2.3.6/24')
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].prefix, '1.2.3.4/32')
        self.assertEqual(result[1].prefix, '1.2.3.5/32')
        self.assertEqual(result[2].prefix, '1.2.3.6/32')
        self.assertEqual(result[3].prefix, '1.2.3.0/24')

        result = r.search_covered('1.2.3.7/24')
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].prefix, '1.2.3.4/32')
        self.assertEqual(result[1].prefix, '1.2.3.5/32')
        self.assertEqual(result[2].prefix, '1.2.3.6/32')
        self.assertEqual(result[3].prefix, '1.2.3.0/24')

        result = r.search_covered('1.2.4.4/24')
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].prefix, '1.2.4.4/32')
        self.assertEqual(result[1].prefix, '1.2.4.5/32')
        self.assertEqual(result[2].prefix, '1.2.4.6/32')
        self.assertEqual(result[3].prefix, '1.2.4.0/24')

        result = r.search_covered('1.2.4.5/24')
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].prefix, '1.2.4.4/32')
        self.assertEqual(result[1].prefix, '1.2.4.5/32')
        self.assertEqual(result[2].prefix, '1.2.4.6/32')
        self.assertEqual(result[3].prefix, '1.2.4.0/24')

        result = r.search_covered('1.2.4.6/24')
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].prefix, '1.2.4.4/32')
        self.assertEqual(result[1].prefix, '1.2.4.5/32')
        self.assertEqual(result[2].prefix, '1.2.4.6/32')
        self.assertEqual(result[3].prefix, '1.2.4.0/24')

        result = r.search_covered('1.2.4.7/24')
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].prefix, '1.2.4.4/32')
        self.assertEqual(result[1].prefix, '1.2.4.5/32')
        self.assertEqual(result[2].prefix, '1.2.4.6/32')
        self.assertEqual(result[3].prefix, '1.2.4.0/24')

        result = r.search_covered('1.2.3.0/24')
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].prefix, '1.2.3.4/32')
        self.assertEqual(result[1].prefix, '1.2.3.5/32')
        self.assertEqual(result[2].prefix, '1.2.3.6/32')
        self.assertEqual(result[3].prefix, '1.2.3.0/24')

        result = r.search_covered('1.2.3.5/31')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].prefix, '1.2.3.4/32')
        self.assertEqual(result[1].prefix, '1.2.3.5/32')

        result = r.search_covered('1.2.6.0/16')
        self.assertEqual(len(result), 9)
        self.assertEqual(result[0].prefix, '1.2.3.4/32')
        self.assertEqual(result[1].prefix, '1.2.3.5/32')
        self.assertEqual(result[2].prefix, '1.2.3.6/32')
        self.assertEqual(result[3].prefix, '1.2.3.0/24')
        self.assertEqual(result[4].prefix, '1.2.4.4/32')
        self.assertEqual(result[5].prefix, '1.2.4.5/32')
        self.assertEqual(result[6].prefix, '1.2.4.6/32')
        self.assertEqual(result[7].prefix, '1.2.4.0/24')
        self.assertEqual(result[8].prefix, '1.2.0.0/16')

        result = r.search_covered('1.3.6.0/16')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].prefix, '1.3.0.0/16')

        result = r.search_covered('1.4.6.0/16')
        self.assertEqual(len(result), 0)

        result = r.search_covered('2.4.6.4/8')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].prefix, '2.0.0.0/8')
        result = r.search_covered('3.4.6.4/8')
        self.assertEqual(len(result), 0)

        result = r.search_covered('0.0.0.0/0')
        self.assertEqual(len(result), 13)
        self.assertEqual(result[0].prefix, '1.2.3.4/32')
        self.assertEqual(result[1].prefix, '1.2.3.5/32')
        self.assertEqual(result[2].prefix, '1.2.3.6/32')
        self.assertEqual(result[3].prefix, '1.2.3.0/24')
        self.assertEqual(result[4].prefix, '1.2.4.4/32')
        self.assertEqual(result[5].prefix, '1.2.4.5/32')
        self.assertEqual(result[6].prefix, '1.2.4.6/32')
        self.assertEqual(result[7].prefix, '1.2.4.0/24')
        self.assertEqual(result[8].prefix, '1.2.0.0/16')
        self.assertEqual(result[9].prefix, '1.3.0.0/16')
        self.assertEqual(result[10].prefix, '1.0.0.0/8')
        self.assertEqual(result[11].prefix, '2.0.0.0/8')
        self.assertEqual(result[12].prefix, '0.0.0.0/0')

    def test_default_bug(self):
        r = radix.Radix()
        r.add("0.0.0.0/0")
        r.add("192.168.1.133/32")
        result = r.search_covered('192.168.0.0/16')
        self.assertEqual(result[0].prefix, '192.168.1.133/32')

    def test_default_bug2(self):
        r = radix.Radix()
        r.add('10.0.0.0/24')
        r.add('0.0.0.0/0')

        result = r.search_covered('10.0.0.1')
        self.assertEqual(len(result), 0)

    def test_find_covered2(self):
        r = radix.Radix()
        r.add('10.30.2.1/32')
        r.add('10.30.2.1/25')

        result = r.search_covered('10.30.2.64/32')
        self.assertEqual(len(result), 0)


class TestFlowSpec(unittest.TestCase):
    def test_compare_tenant_context(self):
        f1 = FlowSpec()
        f1.tenant_name = 'tenant'
        f1.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        f1.protocol_filter.append(filt1)

        f2 = FlowSpec()
        f2.tenant_name = 'tenant1'
        f2.context_name = 'ctx'
        f2.protocol_filter.append(filt1)

        self.assertTrue(f1 < f2)
        self.assertTrue(f2 > f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertTrue(f1 != f2)
        self.assertTrue(f2 != f1)
        self.assertFalse(f1 == f2)

        f2.tenant_name = 'tenant'
        f2.context_name = 'dtx'

        self.assertTrue(f1 < f2)
        self.assertTrue(f2 > f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertTrue(f1 != f2)
        self.assertTrue(f2 != f1)
        self.assertFalse(f1 == f2)

        f2.tenant_name = 'tenant'
        f2.context_name = 'ctx'
        self.assertTrue(f1 == f2)
        self.assertFalse(f2 != f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertFalse(f1 < f2)
        self.assertFalse(f1 > f2)
        self.assertFalse(f2 < f1)
        self.assertFalse(f2 > f1)

    def test_compare_ip(self):
        f1 = FlowSpec()
        f1.tenant_name = 'tenant'
        f1.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        f1.protocol_filter.append(filt1)

        f2 = FlowSpec()
        f2.tenant_name = 'tenant'
        f2.context_name = 'ctx'
        f2.protocol_filter.append(filt1)

        f1.dip = [Ipv4Address('1.2.3.4/32')]
        f2.dip = [Ipv4Address('1.2.4.4/32')]
        self.assertTrue(f1 < f2)
        self.assertTrue(f2 > f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertTrue(f1 != f2)
        self.assertTrue(f2 != f1)
        self.assertFalse(f1 == f2)
        self.assertFalse(f2 == f1)
        self.assertFalse(f1 > f2)
        self.assertFalse(f2 < f1)
        self.assertFalse(f1 >= f2)
        self.assertFalse(f2 <= f1)

        f2.dip = [Ipv4Address('1.2.3.4/32')]
        self.assertTrue(f1 == f2)

        f1.sip = [Ipv4Address('1.2.3.4/32')]
        f2.sip = [Ipv4Address('1.2.4.4/32')]
        self.assertTrue(f1 < f2)
        self.assertTrue(f2 > f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertTrue(f1 != f2)
        self.assertTrue(f2 != f1)
        self.assertFalse(f1 == f2)
        self.assertFalse(f2 == f1)
        self.assertFalse(f1 > f2)
        self.assertFalse(f2 < f1)
        self.assertFalse(f1 >= f2)
        self.assertFalse(f2 <= f1)

        f1.sip = [Ipv4Address('1.2.3.4/32')]
        f2.sip = [Ipv4Address('1.2.3.4/16')]
        self.assertTrue(f1 < f2)
        self.assertTrue(f2 > f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertTrue(f1 != f2)
        self.assertTrue(f2 != f1)
        self.assertFalse(f1 == f2)
        self.assertFalse(f2 == f1)
        self.assertFalse(f1 > f2)
        self.assertFalse(f2 < f1)
        self.assertFalse(f1 >= f2)
        self.assertFalse(f2 <= f1)

        f2.sip = [Ipv4Address('1.2.3.4/32')]

        f1.sip = [Ipv4Address('1.2.3.4/16')]
        f2.sip = [Ipv4Address('1.2.3.4/16'), Ipv4Address('1.2.3.7/8')]
        self.assertTrue(f1 < f2)
        self.assertTrue(f2 > f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertTrue(f1 != f2)
        self.assertTrue(f2 != f1)
        self.assertFalse(f1 == f2)
        self.assertFalse(f2 == f1)
        self.assertFalse(f1 > f2)
        self.assertFalse(f2 < f1)
        self.assertFalse(f1 >= f2)
        self.assertFalse(f2 <= f1)

    def test_compare_protocol_filter(self):
        f1 = FlowSpec()
        f1.tenant_name = 'tenant'
        f1.context_name = 'ctx'
        filt1 = ProtocolFilter()
        filt1.prot = 'tcp'
        f1.protocol_filter.append(filt1)

        f2 = FlowSpec()
        f2.tenant_name = 'tenant'
        f2.context_name = 'ctx'
        filt2 = ProtocolFilter()
        filt2.prot = 'tcp'
        f2.protocol_filter.append(filt2)

        filt1.dFromPort = 80
        self.assertTrue(f1 < f2)
        self.assertTrue(f2 > f1)
        self.assertTrue(f1 <= f2)
        self.assertTrue(f2 >= f1)
        self.assertTrue(f1 != f2)
        self.assertTrue(f2 != f1)
        self.assertFalse(f1 == f2)
        self.assertFalse(f2 == f1)
        self.assertFalse(f1 > f2)
        self.assertFalse(f2 < f1)
        self.assertFalse(f1 >= f2)
        self.assertFalse(f2 <= f1)


class TestImportContract(unittest.TestCase):
    """
    Check that can handle imported contacts
    """

    def setUp(self):
        """
        creates two EPGs in different tenants
        One is made available to the other
        :return:
        """
        tenant1 = Tenant('tenant1')
        tenant2 = Tenant('tenant2')

        app1 = AppProfile('app1', tenant1)
        app2 = AppProfile('app2', tenant2)

        epg1 = EPG('epg1', app1)
        epg2 = EPG('epg2', app1)
        for index in range(1, 5):
            ep = Endpoint('endpoint_' + str(index), epg1)
            ep.ip = '10.0.0.' + str(index)
        for index in range(1, 5):
            ep = Endpoint('endpoint_' + str(index), epg2)
            ep.ip = '11.0.0.' + str(index)

        bd1 = BridgeDomain('bd1', tenant1)
        bd2 = BridgeDomain('bd2', tenant1)
        epg1.add_bd(bd1)
        epg2.add_bd(bd2)

        context = Context('ctx', tenant1)
        bd1.add_context(context)
        bd2.add_context(context)

        self.contract1 = Contract('contract-1', tenant1)
        entry1 = FilterEntry('entry1',
                             applyToFrag='no',
                             arpOpc='unspecified',
                             dFromPort='80',
                             dToPort='80',
                             etherT='ip',
                             prot='tcp',
                             sFromPort='unspecified',
                             sToPort='unspecified',
                             tcpRules='unspecified',
                             parent=self.contract1)

        self.contract_interface = ContractInterface('contract_if', tenant1)
        epg1.consume_cif(self.contract_interface)
        epg2.provide(self.contract1)
        self.tenants = [tenant1, tenant2]

    def test_cif(self):
        self.contract_interface.import_contract(self.contract1)
        self.sdb = SearchDb()
        self.sdb.build(self.tenants)
        flow_spec = FlowSpec()
        filt1 = ProtocolFilter()
        filt = filt1
        flow_spec.protocol_filter.append(filt)
        filt2 = ProtocolFilter()
        filt2.dPort = 80
        filt2.prot = 'tcp'
        result = sorted(self.sdb.search(flow_spec))
        exp_flow = copy.deepcopy(flow_spec)
        exp_flow.tenant_name = 'tenant1'
        exp_flow.context_name = 'ctx'
        exp_flow.dip = []
        exp_flow.sip = [IpAddress('11.0.0.1/32'), IpAddress('11.0.0.4/32'), IpAddress('11.0.0.2/31')]
        exp_flow.dip = [IpAddress('11.0.0.1/32'), IpAddress('11.0.0.4/32'), IpAddress('11.0.0.2/31')]
        exp_flow.protocol_filter = [filt1]
        self.assertTrue(len(result) == 3)
        self.assertTrue(result[2] == exp_flow)
        exp_flow.dip = [IpAddress('11.0.0.1/32'), IpAddress('11.0.0.4/32'), IpAddress('11.0.0.2/31')]
        exp_flow.sip = [IpAddress('10.0.0.1/32'), IpAddress('10.0.0.4/32'), IpAddress('10.0.0.2/31')]
        exp_flow.protocol_filter = [filt2]
        self.assertTrue(result[1] == exp_flow)
        exp_flow.protocol_filter = [filt1]
        exp_flow.sip = [IpAddress('10.0.0.1/32'), IpAddress('10.0.0.4/32'), IpAddress('10.0.0.2/31')]
        exp_flow.dip = [IpAddress('10.0.0.1/32'), IpAddress('10.0.0.4/32'), IpAddress('10.0.0.2/31')]
        self.assertTrue(result[0] == exp_flow)

    def test_empty_cif(self):
        # self.contract_interface.import_contract(self.contract1)
        self.sdb = SearchDb()
        self.sdb.build(self.tenants)
        flow_spec = FlowSpec()
        filt1 = ProtocolFilter()
        filt = filt1
        flow_spec.protocol_filter.append(filt)
        filt2 = ProtocolFilter()
        filt2.dPort = 80
        filt2.prot = 'tcp'
        result = sorted(self.sdb.search(flow_spec))
        self.assertTrue(len(result) == 2)
        exp_flow = copy.deepcopy(flow_spec)
        exp_flow.tenant_name = 'tenant1'
        exp_flow.context_name = 'ctx'
        exp_flow.dip = []
        exp_flow.sip = [IpAddress('11.0.0.1/32'), IpAddress('11.0.0.4/32'), IpAddress('11.0.0.2/31')]
        exp_flow.dip = [IpAddress('11.0.0.1/32'), IpAddress('11.0.0.4/32'), IpAddress('11.0.0.2/31')]
        exp_flow.protocol_filter = [filt1]
        self.assertTrue(result[1] == exp_flow)
        exp_flow.sip = [IpAddress('10.0.0.1/32'), IpAddress('10.0.0.4/32'), IpAddress('10.0.0.2/31')]
        exp_flow.dip = [IpAddress('10.0.0.1/32'), IpAddress('10.0.0.4/32'), IpAddress('10.0.0.2/31')]
        self.assertTrue(result[0] == exp_flow)


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
class TestLiveAPIC(unittest.TestCase):
    def login_to_apic(self):
        """Login to the APIC
           RETURNS:  Instance of class Session
        """
        pass


if __name__ == '__main__':
    unittest.main()
