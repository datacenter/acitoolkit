# Copyright (c) 2014 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
"""ACI Toolkit Test module
"""
from acitoolkit.acitoolkit import *
from acitoolkit.aciphysobject import *
import unittest
import string
import random
from credentials import *
import sys
import time
import json

MAX_RANDOM_STRING_SIZE = 20


def random_string(size):
    """
    Generates a random string of a certain specified size.

    :param size: Integer indicating size of string
    :returns: String of random characters
    """
    return ''.join(random.choice(string.ascii_uppercase +
                                 string.digits) for _ in range(size))


def random_size_string():
    """
    Generates a random string between 1 and MAX_RANDOM_STRING_SIZE
    characters

    :returns: String of random characters between 1 and\
              MAX_RANDOM_STRING_SIZE characters.
    """
    return random_string(random.randint(1, MAX_RANDOM_STRING_SIZE))


class TestBaseRelation(unittest.TestCase):
    """Tests on the BaseRelation class.  These do not communicate with the APIC
    """
    def create_relation(self, status='attached'):
        """
        Creates a base relation
        """
        tenant = Tenant('test')
        relation = BaseRelation(tenant, status)
        return tenant, relation

    def create_attached_relation(self):
        """
        Creates an attached base relation
        """
        return self.create_relation('attached')

    def create_detached_relation(self):
        """
        Creates a detached base relation
        """
        return self.create_relation('detached')

    def test_create_with_valid_status_attached(self):
        """
        Creates an attached relation
        """
        tenant, relation = self.create_attached_relation()
        self.assertTrue(relation is not None)

    def test_create_with_valid_status_detached(self):
        """
        Creates a detached relation
        """
        tenant, relation = self.create_detached_relation()
        self.assertTrue(relation is not None)

    def test_create_invalid(self):
        """
        Creates an invalid relation status
        """
        tenant = Tenant('test')
        self.assertRaises(ValueError, BaseRelation, tenant, 'something else')

    def test_is_attached(self):
        """
        Test is_attached
        """
        tenant, relation = self.create_attached_relation()
        self.assertTrue(relation.is_attached())

    def test_is_detached(self):
        """
        Test is_detached
        """
        tenant, relation = self.create_detached_relation()
        self.assertTrue(relation.is_detached())

    def test_set_detached(self):
        """
        Test set_as_detached
        """
        tenant, relation = self.create_attached_relation()
        self.assertTrue(relation.is_attached())
        relation.set_as_detached()
        self.assertFalse(relation.is_attached())
        self.assertTrue(relation.is_detached())


class MockACIObject(BaseACIObject):
    def get_json(self):
        attr = self._generate_attributes()
        super(MockACIObject, self).get_json('mock', attributes=attr)

    def write(self, text):
        """Used to override sys.stdout calls to avoid printing
           coming from 3rd party libraries
        """
        pass


class TestBaseACIObject(unittest.TestCase):
    def test_create_valid(self):
        obj = MockACIObject('mock')
        self.assertTrue(isinstance(obj, MockACIObject))

    def test_create_invalid_name_is_none(self):
        self.assertRaises(TypeError, MockACIObject)

    def test_create_invalid_name_is_not_string(self):
        name = 53
        self.assertRaises(TypeError, MockACIObject, name)

    def test_create_invalid_parent_as_string(self):
        name = 'valid'
        invalid_parent = 'parent'
        self.assertRaises(TypeError, MockACIObject, name, invalid_parent)

    def test_string_transform(self):
        obj = MockACIObject('mock')
        object_as_string = str(obj)
        self.assertTrue(isinstance(object_as_string, str))

    def test_attach(self):
        obj1 = MockACIObject('mock')
        obj2 = MockACIObject('mock')
        obj1.attach(obj2)
        self.assertTrue(obj1.is_attached(obj2))
        return obj1, obj2

    def test_double_attach(self):
        obj1, obj2 = self.test_attach()
        obj1.attach(obj2)
        self.assertTrue(obj1.is_attached(obj2))

    def test_detach(self):
        obj1, obj2 = self.test_attach()
        obj1.detach(obj2)
        self.assertFalse(obj1.is_attached(obj2))

    def test_detach_unattached(self):
        obj1 = MockACIObject('mock')
        obj2 = MockACIObject('mock')
        self.assertFalse(obj1.is_attached(obj2))
        obj1.detach(obj2)
        self.assertFalse(obj1.is_attached(obj2))


class TestTenant(unittest.TestCase):
    """
    Tenant class tests.  These do not communicate with APIC
    """
    def test_create(self):
        """
        Tenant creation
        """
        tenant = Tenant('tenant')
        self.assertNotEqual(tenant, None)

    def test_json(self):
        """
        Tenant get_json
        """
        tenant = Tenant('tenant')
        self.assertTrue(type(tenant.get_json()) == dict)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(Tenant._get_parent_class(), None)

    def test_get_name_from_dn(self):
        """
        Ensure gives the correct name from a dn for a Tenant
        """
        dn = 'uni/tn-test'
        self.assertEquals(Tenant._get_name_from_dn(dn), 'test')


class TestAppProfile(unittest.TestCase):
    """
    AppProfile class tests.  These do not communicate with APIC
    """
    def test_create(self):
        """
        AppProfile creation
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        self.assertNotEqual(app, None)

    def test_invalid_create_no_parent(self):
        """
        Test invalid AppProfile creation by passing no parent class
        """
        self.assertRaises(TypeError, AppProfile, 'app', None)

    def test_invalid_create_parent_as_string(self):
        """
        Test invalid AppProfile creation by passing string as the
        parent class
        """
        self.assertRaises(TypeError, AppProfile, 'app', 'tenant')

    def test_invalid_create_no_name(self):
        """
        Test invalid AppProfile creation by passing no name
        """
        self.assertRaises(TypeError, AppProfile, None, Tenant('tenant'))

    def test_invalid_create_not_string_name(self):
        """
        Test invalid AppProfile creation by passing non-string as name
        """
        tenant = Tenant('tenant')
        self.assertRaises(TypeError, AppProfile, tenant, tenant)

    def test_get_parent_class(self):
        """
        Test AppProfile._get_parent_class returns Tenant class
        """
        self.assertEquals(AppProfile._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        """
        Test AppProfile._get_parent_dn returns correct dn of the
        parent
        """
        dn = 'uni/tn-tenant/ap-test'
        self.assertEquals(AppProfile._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        """
        Test that AppProfile._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'uni/tn-tenant/ap-test'
        self.assertEquals(AppProfile._get_name_from_dn(dn), 'test')

    def test_delete(self):
        """
        Test AppProfile deletion
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        self.assertFalse(app.is_deleted())
        app.mark_as_deleted()
        self.assertTrue(app.is_deleted())

    def test_eq(self):
        """
        Test AppProfile __eq__ function
        """
        tenant = Tenant('tenant')
        app1 = AppProfile('app', tenant)
        app2 = AppProfile('app', tenant)
        self.assertEqual(app1, app2)

    def test_not_eq_different_name(self):
        """
        Test AppProfile not equal due to different name
        """
        tenant = Tenant('tenant')
        app1 = AppProfile('app1', tenant)
        app2 = AppProfile('app2', tenant)
        self.assertNotEqual(app1, app2)

    def test_not_eq_different_parent(self):
        """
        Test AppProfile not equal due to different parent
        """
        tenant1 = Tenant('tenant1')
        tenant2 = Tenant('tenant2')
        app1 = AppProfile('app', tenant1)
        app2 = AppProfile('app', tenant2)
        self.assertNotEqual(app1, app2)

    def test_json(self):
        """
        Test AppProfile get_json returns something json-like
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        self.assertTrue(type(app.get_json()) == dict)


class TestBridgeDomain(unittest.TestCase):
    """
    Test the BridgeDomain class
    """
    def create_bd(self):
        """ Create a BridgeDomain """
        tenant = Tenant('tenant')
        bd = BridgeDomain('bd', tenant)
        return tenant, bd

    def create_bd_with_subnet(self):
        """ Create a BridgeDomain with a subnet """
        tenant, bd = self.create_bd()
        sub1 = Subnet('sub1', bd)
        sub1.set_addr('1.1.1.1/24')
        bd.add_subnet(sub1)
        return bd, sub1

    def test_valid_create(self):
        """
        Test basic BridgeDomain creation
        """
        tenant, bd = self.create_bd()
        self.assertNotEqual(bd, None)

    def test_invalid_create_no_parent(self):
        """
        Test invalid BridgeDomain creation due to no parent provided
        """
        self.assertRaises(TypeError, BridgeDomain, 'bd', None)

    def test_invalid_create_parent_as_string(self):
        """
        Test invalid BridgeDomain creation due to parent passed
        as a string
        """
        self.assertRaises(TypeError, BridgeDomain, 'bd', 'tenant')

    def test_invalid_create_no_name(self):
        """
        Test invalid BridgeDomain creation due to no name given
        """
        self.assertRaises(TypeError, BridgeDomain, None, Tenant('tenant'))

    def test_invalid_create_not_string_name(self):
        """
        Test invalid BridgeDomain creation due name not given as
        a string.
        """
        tenant = Tenant('tenant')
        self.assertRaises(TypeError, BridgeDomain, tenant, tenant)

    def test_get_parent_class(self):
        """
        Test that BridgeDomain._get_parent_class returns Tenant class
        """
        self.assertEquals(BridgeDomain._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        """
        Test BridgeDomain._get_parent_dn returns correct dn of the
        parent
        """
        dn = 'uni/tn-tenant/BD-test'
        self.assertEquals(BridgeDomain._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        """
        Test that BridgeDomain._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'uni/tn-tenant/BD-test'
        self.assertEquals(BridgeDomain._get_name_from_dn(dn), 'test')

    def test_valid_delete(self):
        """
        Test BridgeDomain instance deletion
        """
        tenant, bd = self.create_bd()
        self.assertFalse(bd.is_deleted())
        bd.mark_as_deleted()
        self.assertTrue(bd.is_deleted())

    def test_add_valid_subnet(self):
        """
        Test adding a subnet to the BD
        """
        # Add a single subnet to the BD
        bd, sub1 = self.create_bd_with_subnet()
        # Verify that the subnet is there
        subnets = bd.get_subnets()
        self.assertTrue(len(subnets) == 1)
        self.assertTrue(subnets[0] == sub1)
        self.assertTrue(bd.has_subnet(sub1))

    def test_add_2_valid_subnets(self):
        """
        Test adding 2 subnets to the BD
        """
        bd, sub1 = self.create_bd_with_subnet()

        # Add a second subnet to the BD
        sub2 = Subnet('sub2', bd)
        sub2.set_addr('10.1.1.1/24')
        bd.add_subnet(sub2)

        # Verify that there are now 2 subnets
        subnets = bd.get_subnets()
        self.assertTrue(len(subnets) == 2)
        self.assertTrue(bd.has_subnet(sub2))
        return bd, sub1, sub2

    def test_add_subnet_wrong_type(self):
        """
        Test that the subnet must be correct type
        """
        tenant, bd = self.create_bd()
        self.assertRaises(TypeError, bd.add_subnet, 'sub1')

    def test_add_subnet_no_addr(self):
        """
        Test that the subnet added must have an address
        """
        tenant, bd = self.create_bd()
        sub1 = Subnet('sub1', bd)
        self.assertRaises(ValueError, bd.add_subnet, sub1)
        self.assertRaises(ValueError, bd.get_json)

    def test_add_subnet_wrong_parent(self):
        """
        Test that creating a subnet with an invalid parent
        """
        tenant, bd = self.create_bd()
        self.assertRaises(TypeError, Subnet, 'sub1', tenant)

    def test_add_subnet_twice(self):
        bd, sub1 = self.create_bd_with_subnet()
        bd.add_subnet(sub1)
        self.assertTrue(len(bd.get_subnets()) == 1)

    def test_add_subnet_different_bd(self):
        tenant, bd = self.create_bd()
        subnet = Subnet('subnet', bd)
        subnet.set_addr('1.2.3.4/24')
        bd.add_subnet(subnet)
        bd2 = BridgeDomain('bd2', tenant)
        bd2.add_subnet(subnet)
        self.assertTrue(bd2.has_subnet(subnet))

    def test_set_subnet_addr_to_none(self):
        bd, sub1 = self.create_bd_with_subnet()
        self.assertRaises(TypeError, sub1.set_addr, None)

    def test_has_subnet_wrong_type(self):
        tenant, bd = self.create_bd()
        self.assertRaises(TypeError, bd.has_subnet, tenant)

    def test_has_subnet_no_addr(self):
        tenant, bd = self.create_bd()
        sub1 = Subnet('sub1', bd)
        self.assertRaises(ValueError, bd.has_subnet, sub1)

    def test_remove_subnet(self):
        bd, sub1 = self.create_bd_with_subnet()
        bd.remove_subnet(sub1)
        self.assertFalse(bd.has_subnet(sub1))
        self.assertTrue(len(bd.get_subnets()) == 0)

    def test_remove_2_subnets(self):
        bd, sub1, sub2 = self.test_add_2_valid_subnets()
        bd.remove_subnet(sub1)
        self.assertFalse(bd.has_subnet(sub1))
        self.assertTrue(bd.has_subnet(sub2))
        self.assertTrue(len(bd.get_subnets()) == 1)
        bd.remove_subnet(sub2)
        self.assertFalse(bd.has_subnet(sub1))
        self.assertFalse(bd.has_subnet(sub2))
        self.assertTrue(len(bd.get_subnets()) == 0)

    def test_remove_subnet_wrong_type(self):
        bd, sub1 = self.create_bd_with_subnet()
        self.assertRaises(TypeError, bd.remove_subnet, 'sub1')

    def test_add_context(self):
        tenant, bd = self.create_bd()
        context = Context('ctx', tenant)
        bd.add_context(context)
        self.assertTrue(bd.get_context() == context)

    def test_add_context_twice(self):
        tenant, bd = self.create_bd()
        context = Context('ctx', tenant)
        bd.add_context(context)
        bd.add_context(context)
        self.assertTrue(bd.get_context() == context)
        bd.remove_context()
        self.assertTrue(bd.get_context() is None)

    def test_remove_context(self):
        tenant, bd = self.create_bd()
        context = Context('ctx', tenant)
        bd.add_context(context)
        bd.remove_context()
        self.assertTrue(bd.get_context() is None)


class TestL2Interface(unittest.TestCase):
    def test_create_valid_vlan(self):
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vlan', '5')
        self.assertTrue(l2if is not None)
        self.assertTrue(l2if.get_encap_type() == 'vlan')
        self.assertTrue(l2if.get_encap_id() == '5')

    def test_create_valid_nvgre(self):
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'nvgre', '5')
        self.assertTrue(l2if is not None)

    def test_create_valid_vxlan(self):
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vxlan', '5')
        self.assertTrue(l2if is not None)

    def test_invalid_create_bad_encap_type(self):
        self.assertRaises(ValueError, L2Interface,
                          'vlan5_on_eth1/1/1/1', 'invalid_encap', '5')

    def test_invalid_create_bad_encap_id_non_number(self):
        self.assertRaises(ValueError, L2Interface,
                          'vlan5_on_eth1/1/1/1', 'invalid_encap', 'vlan')

    def test_invalid_create_bad_encap_id_none(self):
        self.assertRaises(ValueError, L2Interface,
                          'vlan5_on_eth1/1/1/1', 'invalid_encap', None)

    def test_invalid_create_bad_name_none(self):
        self.assertRaises(TypeError, L2Interface, None, 'vlan', '5')

    def test_invalid_create_bad_name_not_string(self):
        random_object = Tenant('foo')
        self.assertRaises(TypeError, L2Interface, random_object, 'vlan', '5')

    def test_is_interface(self):
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vlan', '5')
        self.assertTrue(l2if.is_interface())

    def test_path(self):
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vlan', '5')
        self.assertTrue(l2if._get_path() is None)

        physif = Interface('eth', '1', '1', '1', '1')
        l2if.attach(physif)
        self.assertTrue(l2if._get_path() is not None)


class TestL3Interface(unittest.TestCase):
    def test_create_valid(self):
        l3if = L3Interface('l3ifname')

    def test_create_invalid_no_name(self):
        self.assertRaises(TypeError, L3Interface)

    def test_is_interface(self):
        l3if = L3Interface('l3ifname')
        self.assertTrue(l3if.is_interface())

    def test_set_addr(self):
        l3if = L3Interface('l3ifname')
        self.assertEqual(l3if.get_addr(), None)
        l3if.set_addr('1.2.3.4/24')
        self.assertEqual(l3if.get_addr(), '1.2.3.4/24')

    def test_set_l3if_type(self):
        l3if = L3Interface('l3ifname')
        l3if.set_l3if_type('l3-port')
        self.assertEqual(l3if.get_l3if_type(), 'l3-port')

    def test_set_l3if_type_invalid(self):
        l3if = L3Interface('l3ifname')
        self.assertRaises(ValueError, l3if.set_l3if_type, 'invalid')

    def test_add_context(self):
        l3if = L3Interface('l3ifname')
        ctx = Context('ctx')
        l3if.add_context(ctx)
        self.assertEqual(l3if.get_context(), ctx)

    def test_add_context_twice(self):
        l3if = L3Interface('l3ifname')
        ctx = Context('ctx')
        l3if.add_context(ctx)
        l3if.add_context(ctx)
        self.assertEqual(l3if.get_context(), ctx)
        l3if.remove_context()
        self.assertIsNone(l3if.get_context())

    def test_add_context_different(self):
        l3if = L3Interface('l3ifname')
        ctx1 = Context('ctx1')
        ctx2 = Context('ctx2')
        l3if.add_context(ctx1)
        l3if.add_context(ctx2)
        self.assertEqual(l3if.get_context(), ctx2)
        self.assertTrue(l3if.has_context())

    def test_remove_context(self):
        l3if = L3Interface('l3ifname')
        ctx = Context('ctx')
        l3if.add_context(ctx)
        l3if.remove_context()
        self.assertIsNone(l3if.get_context())
        self.assertFalse(l3if.has_context())


class TestInterface(unittest.TestCase):
    def test_create_valid_phydomain(self):
        intf = Interface('eth', '1', '1', '1', '1')
        (phydomain_json, fabric_json, infra_json) = intf.get_json()
        expected_json = ("{'physDomP': {'attributes': {'name': 'allvlans'}, 'c"
                         "hildren': [{'infraRsVlanNs': {'attributes': {'tDn': "
                         "'uni/infra/vlanns-allvlans-static'}, 'children': []}"
                         "}]}}")
        self.assertEqual(str(phydomain_json), expected_json)

    def test_create_valid(self):
        intf = Interface('eth', '1', '1', '1', '1')
        (phydomain_json, fabric_json, infra_json) = intf.get_json()
        expected_json = ("{'infraInfra': {'children': [{'infraNodeP': {'attrib"
                         "utes': {'name': '1-1-1-1'}, 'children': [{'infraLeaf"
                         "S': {'attributes': {'type': 'range', 'name': '1-1-1-"
                         "1'}, 'children': [{'infraNodeBlk': {'attributes': {'"
                         "from_': '1', 'name': '1-1-1-1', 'to_': '1'}, 'childr"
                         "en': []}}]}}, {'infraRsAccPortP': {'attributes': {'t"
                         "Dn': 'uni/infra/accportprof-1-1-1-1'}, 'children': ["
                         "]}}]}}, {'infraAccPortP': {'attributes': {'name': '1"
                         "-1-1-1'}, 'children': [{'infraHPortS': {'attributes'"
                         ": {'type': 'range', 'name': '1-1-1-1'}, 'children': "
                         "[{'infraPortBlk': {'attributes': {'toPort': '1', 'fr"
                         "omPort': '1', 'fromCard': '1', 'name': '1-1-1-1', 't"
                         "oCard': '1'}, 'children': []}}, {'infraRsAccBaseGrp'"
                         ": {'attributes': {'tDn': 'uni/infra/funcprof/accport"
                         "grp-1-1-1-1'}, 'children': []}}]}}]}}, {'fabricHIfPo"
                         "l': {'attributes': {'dn': 'uni/infra/hintfpol-speed1"
                         "0G', 'autoNeg': 'on', 'speed': '10G', 'name': 'speed"
                         "10G'}, 'children': []}}, {'infraFuncP': {'attributes"
                         "': {}, 'children': [{'infraAccPortGrp': {'attributes"
                         "': {'dn': 'uni/infra/funcprof/accportgrp-1-1-1-1', '"
                         "name': '1-1-1-1'}, 'children': [{'infraRsHIfPol': {'"
                         "attributes': {'tnFabricHIfPolName': 'speed10G'}, 'ch"
                         "ildren': []}}, {'infraRsAttEntP': {'attributes': {'t"
                         "Dn': 'uni/infra/attentp-allvlans'}, 'children': []}}"
                         "]}}]}}, {'infraAttEntityP': {'attributes': {'name': "
                         "'allvlans'}, 'children': [{'infraRsDomP': {'attribut"
                         "es': {'tDn': 'uni/phys-allvlans'}}}]}}, {'fvnsVlanIn"
                         "stP': {'attributes': {'name': 'allvlans', 'allocMode"
                         "': 'static'}, 'children': [{'fvnsEncapBlk': {'attrib"
                         "utes': {'to': 'vlan-4092', 'from': 'vlan-1', 'name':"
                         " 'encap'}}}]}}]}}")
        self.assertTrue(intf is not None)
        self.assertEqual(str(infra_json), expected_json)

    def test_set_speed_10G(self):
        intf = Interface('eth', '1', '101', '1', '5')
        intf.speed = '10G'
        (phys_domain_json, fabric_json, infra_json) = intf.get_json()
        expected_json = ("{'infraInfra': {'children': [{'infraNodeP': {'attrib"
                         "utes': {'name': '1-101-1-5'}, 'children': [{'infraLe"
                         "afS': {'attributes': {'type': 'range', 'name': '1-10"
                         "1-1-5'}, 'children': [{'infraNodeBlk': {'attributes'"
                         ": {'from_': '101', 'name': '1-101-1-5', 'to_': '101'"
                         "}, 'children': []}}]}}, {'infraRsAccPortP': {'attrib"
                         "utes': {'tDn': 'uni/infra/accportprof-1-101-1-5'}, '"
                         "children': []}}]}}, {'infraAccPortP': {'attributes':"
                         " {'name': '1-101-1-5'}, 'children': [{'infraHPortS':"
                         " {'attributes': {'type': 'range', 'name': '1-101-1-5"
                         "'}, 'children': [{'infraPortBlk': {'attributes': {'t"
                         "oPort': '5', 'fromPort': '5', 'fromCard': '1', 'name"
                         "': '1-101-1-5', 'toCard': '1'}, 'children': []}}, {'"
                         "infraRsAccBaseGrp': {'attributes': {'tDn': 'uni/infr"
                         "a/funcprof/accportgrp-1-101-1-5'}, 'children': []}}]"
                         "}}]}}, {'fabricHIfPol': {'attributes': {'dn': 'uni/i"
                         "nfra/hintfpol-speed10G', 'autoNeg': 'on', 'speed': '"
                         "10G', 'name': 'speed10G'}, 'children': []}}, {'infra"
                         "FuncP': {'attributes': {}, 'children': [{'infraAccPo"
                         "rtGrp': {'attributes': {'dn': 'uni/infra/funcprof/ac"
                         "cportgrp-1-101-1-5', 'name': '1-101-1-5'}, 'children"
                         "': [{'infraRsHIfPol': {'attributes': {'tnFabricHIfPo"
                         "lName': 'speed10G'}, 'children': []}}, {'infraRsAttE"
                         "ntP': {'attributes': {'tDn': 'uni/infra/attentp-allv"
                         "lans'}, 'children': []}}]}}]}}, {'infraAttEntityP': "
                         "{'attributes': {'name': 'allvlans'}, 'children': [{'"
                         "infraRsDomP': {'attributes': {'tDn': 'uni/phys-allvl"
                         "ans'}}}]}}, {'fvnsVlanInstP': {'attributes': {'name'"
                         ": 'allvlans', 'allocMode': 'static'}, 'children': [{"
                         "'fvnsEncapBlk': {'attributes': {'to': 'vlan-4092', '"
                         "from': 'vlan-1', 'name': 'encap'}}}]}}]}}")
        self.assertEqual(str(infra_json), expected_json)

    def test_set_speed_1G(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.speed = '1G'
        (phys_domain_json, fabric_json, infra_json) = intf.get_json()
        expected_json = ("{'infraInfra': {'children': [{'infraNodeP': {'attrib"
                         "utes': {'name': '1-1-1-1'}, 'children': [{'infraLeaf"
                         "S': {'attributes': {'type': 'range', 'name': '1-1-1-"
                         "1'}, 'children': [{'infraNodeBlk': {'attributes': {'"
                         "from_': '1', 'name': '1-1-1-1', 'to_': '1'}, 'childr"
                         "en': []}}]}}, {'infraRsAccPortP': {'attributes': {'t"
                         "Dn': 'uni/infra/accportprof-1-1-1-1'}, 'children': ["
                         "]}}]}}, {'infraAccPortP': {'attributes': {'name': '1"
                         "-1-1-1'}, 'children': [{'infraHPortS': {'attributes'"
                         ": {'type': 'range', 'name': '1-1-1-1'}, 'children': "
                         "[{'infraPortBlk': {'attributes': {'toPort': '1', 'fr"
                         "omPort': '1', 'fromCard': '1', 'name': '1-1-1-1', 't"
                         "oCard': '1'}, 'children': []}}, {'infraRsAccBaseGrp'"
                         ": {'attributes': {'tDn': 'uni/infra/funcprof/accport"
                         "grp-1-1-1-1'}, 'children': []}}]}}]}}, {'fabricHIfPo"
                         "l': {'attributes': {'dn': 'uni/infra/hintfpol-speed1"
                         "G', 'autoNeg': 'on', 'speed': '1G', 'name': 'speed1G"
                         "'}, 'children': []}}, {'infraFuncP': {'attributes': "
                         "{}, 'children': [{'infraAccPortGrp': {'attributes': "
                         "{'dn': 'uni/infra/funcprof/accportgrp-1-1-1-1', 'nam"
                         "e': '1-1-1-1'}, 'children': [{'infraRsHIfPol': {'att"
                         "ributes': {'tnFabricHIfPolName': 'speed1G'}, 'childr"
                         "en': []}}, {'infraRsAttEntP': {'attributes': {'tDn':"
                         " 'uni/infra/attentp-allvlans'}, 'children': []}}]}}]"
                         "}}, {'infraAttEntityP': {'attributes': {'name': 'all"
                         "vlans'}, 'children': [{'infraRsDomP': {'attributes':"
                         " {'tDn': 'uni/phys-allvlans'}}}]}}, {'fvnsVlanInstP'"
                         ": {'attributes': {'name': 'allvlans', 'allocMode': '"
                         "static'}, 'children': [{'fvnsEncapBlk': {'attributes"
                         "': {'to': 'vlan-4092', 'from': 'vlan-1', 'name': 'en"
                         "cap'}}}]}}]}}")

        self.assertEqual(str(infra_json), expected_json)

    def test_adminstate_not_set(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.adminstate = ''
        phys_domain_url, fabric_url, infra_url = intf.get_url()
        phys_domain_json, fabric_json, infra_json = intf.get_json()
        self.assertIsNone(fabric_json)

    def test_adminstate_up(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.adminstatus = 'up'
        phys_domain_json, fabric_json, infra_json = intf.get_json()
        expected_json = ("{'fabricOOServicePol': {'children': [{'fabricRsOosPa"
                         "th': {'attributes': {'dn': 'uni/fabric/outofsvc/rsoo"
                         "sPath-[topology/pod-1/paths-1/pathep-[eth1/1]]', 'st"
                         "atus': 'deleted', 'tDn': 'topology/pod-1/paths-1/pat"
                         "hep-[eth1/1]'}, 'children': []}}]}}")
        self.assertEqual(str(fabric_json), expected_json)

    def test_adminstate_down(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.adminstatus = 'down'
        phys_domain_json, fabric_json, infra_json = intf.get_json()
        expected_json = ("{'fabricOOServicePol': {'children': [{'fabricRsOosPa"
                         "th': {'attributes': {'tDn': 'topology/pod-1/paths-1/"
                         "pathep-[eth1/1]', 'lc': 'blacklist'}, 'children': []"
                         "}}]}}")
        self.assertEqual(str(fabric_json), expected_json)

    def test_cdp_not_enabled(self):
        intf = Interface('eth', '1', '1', '1', '1')
        self.assertFalse(intf.is_cdp_enabled())

    def test_cdp_is_enabled(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.enable_cdp()
        self.assertTrue(intf.is_cdp_enabled())

    def test_cdp_is_disabled(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.disable_cdp()
        self.assertFalse(intf.is_cdp_enabled())

    def test_lldp_not_enabled(self):
        intf = Interface('eth', '1', '1', '1', '1')
        self.assertFalse(intf.is_lldp_enabled())

    def test_lldp_is_enabled(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.enable_lldp()
        self.assertTrue(intf.is_lldp_enabled())

    def test_lldp_is_disabled(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.disable_lldp()
        self.assertFalse(intf.is_lldp_enabled())

    def parse_name(self, text):
        (intf_type, pod, node, module, port) = Interface.parse_name(text)
        self.assertTrue(intf_type == 'eth')
        self.assertTrue(pod == '1')
        self.assertTrue(node == '2')
        self.assertTrue(module == '3')
        self.assertTrue(port == '4')

    def test_parse_name_space(self):
        self.parse_name('eth 1/2/3/4')

    def test_set_attributes(self):
        intf1 = Interface('eth', '1', '2', '3', '4')
        intf2 = Interface('eth', '6', '7', '8', '9')

        self.assertTrue(intf1.attributes['interface_type'] == 'eth')
        self.assertTrue(intf1.attributes['pod'] == '1')
        self.assertTrue(intf1.attributes['node'] == '2')
        self.assertTrue(intf1.attributes['module'] == '3')
        self.assertTrue(intf1.attributes['port'] == '4')

        self.assertTrue(intf2.attributes['interface_type'] == 'eth')
        self.assertTrue(intf2.attributes['pod'] == '6')
        self.assertTrue(intf2.attributes['node'] == '7')
        self.assertTrue(intf2.attributes['module'] == '8')
        self.assertTrue(intf2.attributes['port'] == '9')

    # def test_parse_name_no_space(self):
    #    self.parse_name('eth1/2/3/4')
    def test_get_serial(self) :
        intf1 = Interface('eth', '1', '2', '3', '4')
        self.assertEqual(intf1.get_serial(), None)

    def test_get_type(self) :
        intf1 = Interface('eth', '1', '2', '3', '4')
        self.assertEqual(intf1.get_type(), 'interface')

    def test_cdp_disabled(self) :
        intf1 = Interface('eth', '1', '2', '3', '4')
        self.assertFalse(intf1.is_cdp_disabled())

    def test_lldp_disabled(self) :
        intf1 = Interface('eth', '1', '2', '3', '4')
        self.assertFalse(intf1.is_lldp_disabled())

class TestBaseContract(unittest.TestCase):
    def test_get_contract_code(self):
        contract = BaseContract('contract')
        self.assertRaises(NotImplementedError,
                          contract._get_contract_code)

    def test_get_subject_code(self):
        contract = BaseContract('contract')
        self.assertRaises(NotImplementedError,
                          contract._get_subject_code)

    def test_get_subject_relation_code(self):
        contract = BaseContract('contract')
        self.assertRaises(NotImplementedError,
                          contract._get_subject_relation_code)

    def test_set_scope(self):
        contract = BaseContract('contract')
        valid_scopes = ['context', 'global', 'tenant', 'application-profile']
        for scope in valid_scopes:
            contract.set_scope(scope)
        bad_scope = 'bad-scope'
        self.assertRaises(ValueError, contract.set_scope, bad_scope)


class TestContract(unittest.TestCase):
    def test_create(self):
        contract = Contract('contract')

    def test_internal_get_contract_code(self):
        self.assertEqual(Contract._get_contract_code(), 'vzBrCP')

    def test_internal_get_subject_code(self):
        self.assertEqual(Contract._get_subject_code(), 'vzSubj')

    def test_internal_get_subject_relation_code(self):
        self.assertEqual(Contract._get_subject_relation_code(),
                         'vzRsSubjFiltAtt')

    def test_get_parent_class(self):
        self.assertEquals(Contract._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        dn = 'uni/tn-tenant/brc-test'
        self.assertEquals(Contract._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        dn = 'uni/tn-tenant/brc-test'
        self.assertEquals(Contract._get_name_from_dn(dn), 'test')

    def test_internal_generate_attributes(self):
        contract = Contract('contract')
        contract.set_scope('tenant')
        attributes = contract._generate_attributes()
        self.assertTrue('scope' in attributes)
        self.assertEqual(attributes['scope'], 'tenant')


class TestTaboo(unittest.TestCase):
    def test_create(self):
        taboo = Taboo('taboo')

    def test_internal_get_contract_code(self):
        self.assertEqual(Taboo._get_contract_code(), 'vzTaboo')

    def test_internal_get_subject_code(self):
        self.assertEqual(Taboo._get_subject_code(), 'vzTSubj')

    def test_internal_get_subject_relation_code(self):
        self.assertEqual(Taboo._get_subject_relation_code(),
                         'vzRsDenyRule')

    def test_get_parent_class(self):
        self.assertEquals(Taboo._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        dn = 'uni/tn-tenant/taboo-test'
        self.assertEquals(Taboo._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        dn = 'uni/tn-tenant/taboo-test'
        self.assertEquals(Taboo._get_name_from_dn(dn), 'test')


class TestEPG(unittest.TestCase):
    def create_epg(self):
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        return tenant, app, epg

    def create_epg_with_bd(self):
        tenant, app, epg = self.create_epg()
        self.assertFalse(epg.has_bd())
        bd = BridgeDomain('bd', tenant)
        epg.add_bd(bd)
        return tenant, app, epg, bd

    def test_valid_create(self):
        tenant, app, epg = self.create_epg()
        self.assertTrue(isinstance(epg, EPG))

    def test_invalid_create_parent_none(self):
        self.assertRaises(TypeError, EPG, 'epg', None)

    def test_invalid_create_parent_wrong_class(self):
        tenant = Tenant('tenant')
        self.assertRaises(TypeError, EPG, 'epg', tenant)

    def test_get_parent_class(self):
        self.assertEquals(EPG._get_parent_class(), AppProfile)

    def test_get_parent_dn(self):
        dn = 'uni/tn-tenant/ap-app/epg-test'
        self.assertEquals(EPG._get_parent_dn(dn), 'uni/tn-tenant/ap-app')

    def test_get_name_from_dn(self):
        dn = 'uni/tn-tenant/ap-app/epg-test'
        self.assertEquals(EPG._get_name_from_dn(dn), 'test')

    def test_valid_add_bd(self):
        tenant, app, epg, bd = self.create_epg_with_bd()
        self.assertTrue(epg.has_bd())
        self.assertTrue(epg.get_bd() == bd)

    def test_valid_add_bd_json(self):
        tenant, app, epg, bd = self.create_epg_with_bd()
        self.assertTrue('fvRsBd' in str(tenant.get_json()))

    def test_invalid_add_bd_as_none(self):
        tenant, app, epg = self.create_epg()
        self.assertRaises(TypeError, epg.add_bd, None)

    def test_invalid_add_bd_wrong_class(self):
        tenant, app, epg = self.create_epg()
        self.assertRaises(TypeError, epg.add_bd, tenant)

    def test_add_bd_twice(self):
        tenant, app, epg, bd = self.create_epg_with_bd()
        # Add the BD again
        epg.add_bd(bd)
        # Now, remove the BD
        epg.remove_bd()
        # Verify that a dangling BD was not left behind
        self.assertFalse(epg.has_bd())
        self.assertTrue(epg.get_bd() is None)

    def test_add_bd_two_different(self):
        tenant, app, epg, bd = self.create_epg_with_bd()
        # Add a different BD
        bd2 = BridgeDomain('bd2', tenant)
        epg.add_bd(bd2)
        self.assertTrue(epg.get_bd() == bd2)
        # Now, remove the BD
        epg.remove_bd()
        # Verify that a dangling BD was not left behind
        self.assertFalse(epg.has_bd())

    def test_valid_remove_bd(self):
        tenant, app, epg, bd = self.create_epg_with_bd()
        epg.remove_bd()
        self.assertFalse(epg.has_bd())
        self.assertFalse(epg.get_bd() == bd)

    def test_tag_add(self):
        tenant, app, epg = self.create_epg()
        self.assertFalse(epg.has_tags())
        epg.add_tag('secure')
        epg.add_tag('normal')
        self.assertTrue(epg.has_tags())
        self.assertTrue(epg.get_tags() == ['secure', 'normal'])
        self.assertTrue(epg.has_tag('secure'))

    def test_tag_remove(self):
        tenant, app, epg = self.create_epg()
        self.assertFalse(epg.has_tags())
        epg.add_tag('secure')
        epg.add_tag('normal')
        self.assertTrue(epg.has_tags())
        epg.remove_tag('secure')
        self.assertFalse(epg.has_tag('secure'))
        epg.remove_tag('normal')
        self.assertFalse(epg.has_tags())

    def test_epg_provide(self):
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
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

        epg.provide(contract1)
        output = tenant.get_json()
        self.assertTrue('fvRsProv' in str(output))

    def test_epg_consume(self):
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
        epg.consume(contract1)
        output = tenant.get_json()
        self.assertTrue('fvRsCons' in str(output))

    def test_epg_provide_consume(self):
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
        contract2 = Contract('contract-2', tenant)
        contract3 = Contract('contract-3', tenant)

        # Test the provide
        epg.provide(contract1)
        epg.provide(contract2)
        epg.provide(contract1)  # should be a no-op since already provided
        self.assertTrue(epg.does_provide(contract1))
        self.assertTrue(epg.does_provide(contract2))
        self.assertFalse(epg.does_provide(contract3))
        epg.dont_provide(contract1)
        self.assertFalse(epg.does_provide(contract1))
        self.assertTrue(epg.does_provide(contract2))
        epg.provide(contract3)
        contracts = epg.get_all_provided()
        self.assertTrue(len(contracts) == 2)
        for contract in contracts:
            self.assertTrue(contract in (contract2, contract3))
        epg.dont_provide(contract1)
        epg.dont_provide(contract2)
        epg.dont_provide(contract3)
        self.assertTrue(epg.get_all_provided() == [])

        # Test the consume
        epg.provide(contract1)
        epg.provide(contract2)
        epg.consume(contract1)
        epg.consume(contract2)
        epg.consume(contract1)  # should be a no-op since already consumed
        self.assertTrue(epg.does_consume(contract1))
        self.assertTrue(epg.does_consume(contract2))
        self.assertFalse(epg.does_consume(contract3))
        epg.dont_consume(contract1)
        self.assertFalse(epg.does_consume(contract1))
        self.assertTrue(epg.does_consume(contract2))
        epg.consume(contract3)
        contracts = epg.get_all_consumed()
        self.assertTrue(len(contracts) == 2)
        for contract in contracts:
            self.assertTrue(contract in (contract2, contract3))
        epg.dont_consume(contract1)
        epg.dont_consume(contract2)
        epg.dont_consume(contract3)
        self.assertTrue(epg.get_all_consumed() == [])

    def test_attach_epg(self):
        tenant, app, epg = self.create_epg()
        interface = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(interface)
        epg.attach(vlan_intf)
        self.assertTrue('fvRsPathAtt' in str(tenant.get_json()))

    def test_detach_epg(self):
        tenant, app, epg = self.create_epg()
        interface = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(interface)
        epg.attach(vlan_intf)
        epg.detach(vlan_intf)
        output = str(tenant.get_json())
        self.assertTrue(all(x in output for x in ('fvRsPathAtt', 'deleted')))


class TestOutsideEPG(unittest.TestCase):
    def test_create(self):
        tenant = Tenant('cisco')
        outside_epg = OutsideEPG('internet', tenant)
        self.assertTrue(isinstance(outside_epg, OutsideEPG))

    def test_invalid_create(self):
        self.assertRaises(TypeError, OutsideEPG, 'internet', 'cisco')

    def test_basic_json(self):
        tenant = Tenant('cisco')
        outside_epg = OutsideEPG('internet', tenant)
        self.assertTrue('l3extOut' in str(outside_epg.get_json()))


class TestEndpoint(unittest.TestCase):
    """
    Test Static Endpoints.
    These tests do not communicate with the APIC
    """
    def create_tenant_with_ep(self, tenant_name, app_name,
                              epg_name, ep_name, interface=None):
        """
        Create a tenant with an EP.  Optionally attach to the given
        interface
        """
        tenant = Tenant(tenant_name)
        app = AppProfile(app_name, tenant)
        epg = EPG(epg_name, app)
        ep = Endpoint(ep_name, epg)
        if interface is not None:
            epg.attach(interface)
            ep.attach(interface)
        return tenant
    
    def verify_json(self, data, deleted=False):
        """
        Check that the JSON is correct for an Endpoint.
        Setting deleted will check the status is set to deleted
        """
        app = data['fvTenant']['children'][0]['fvAp']
        epg = app['children'][0]['fvAEPg']
        interface = 'topology/pod-1/paths-1/pathep-[eth1/1]'
        mac = '00-11-22-33-44-55'
        children_checked = 0
        for child in epg['children']:
            if 'fvRsPathAtt' in child:
                dn_attr = child['fvRsPathAtt']['attributes']['tDn']
                self.assertTrue(dn_attr == interface)
                children_checked = children_checked + 1
            if 'fvStCEp' in child:
                ep_child = child['fvStCEp']['children'][0]
                ep_attributes = child['fvStCEp']['attributes']
                ep_name = ep_attributes['name']
                if deleted:
                    status = ep_attributes['status']
                    self.assertTrue(status == 'deleted')
                self.assertTrue(ep_name == mac)
                children_checked = children_checked + 1
                self.assertTrue('fvRsStCEpToPathEp' in ep_child)
                if_attr = ep_child['fvRsStCEpToPathEp']['attributes']
                child_interface = if_attr['tDn']
                self.assertTrue(child_interface == interface)
        self.assertTrue(children_checked >= 2)

    def test_create(self):
        """
        Create a basic static endpoint without attaching
        to an interface
        """
        tenant = self.create_tenant_with_ep('tenant', 'app', 'epg',
                                            '00-11-22-33-44-55')
        tenant.get_json()
    def test_create_bad_parent(self) :
        """
        checks to see that creating an endpoint in something
        other an EPG causes an error.
        """
        self.assertRaises(TypeError,Endpoint,'00-11-22-33-44-55','not an epg')
        
    def test_create_on_interface(self):
        """
        Create a basic static endpoint and attach
        to an interface.  Verify the JSON afterwards
        """
        interface = Interface('eth', '1', '1', '1', '1')
        vlan_interface = L2Interface('vlan5', 'vlan', '5')
        vlan_interface.attach(interface)
        tenant = self.create_tenant_with_ep('tenant', 'app', 'epg',
                                            '00-11-22-33-44-55',
                                            vlan_interface)
        data = tenant.get_json()

        # Verify the JSON is correct
        self.verify_json(data)

    def test_delete_from_interface(self):
        """
        Create a basic static endpoint and attach
        to an interface and then delete it.
        Verify the JSON afterwards
        """
        interface = Interface('eth', '1', '1', '1', '1')
        vlan_interface = L2Interface('vlan5', 'vlan', '5')
        vlan_interface.attach(interface)
        tenant = self.create_tenant_with_ep('tenant', 'app', 'epg',
                                            '00-11-22-33-44-55',
                                            vlan_interface)
        app = tenant.get_children(AppProfile)[0]
        epg = app.get_children(EPG)[0]
        ep = epg.get_children(Endpoint)[0]
        ep.mark_as_deleted()

        data = tenant.get_json()
        self.verify_json(data, True)


class TestJson(unittest.TestCase):
    def test_simple_3tier_app(self):
        tenant = Tenant('cisco')
        app = AppProfile('ordersystem', tenant)
        web_epg = EPG('web', app)
        app_epg = EPG('app', app)
        db_epg = EPG('db', app)

        json_output = tenant.get_json()
        json_string = json.dumps(json_output)

        for check in ('db', 'web', 'app', 'cisco', 'ordersystem'):
            self.assertTrue(check in json_string,
                            'Did not find %s in returned json' % check)

    def test_epg_attach_to_VLAN_interface(self):
        expected_json = ("{'fvTenant': {'attributes': {'name': 'cisco'}, 'chil"
                         "dren': [{'fvAp': {'attributes': {'name': 'ordersyste"
                         "m'}, 'children': [{'fvAEPg': {'attributes': {'name':"
                         " 'web'}, 'children': [{'fvRsPathAtt': {'attributes':"
                         " {'tDn': 'topology/pod-1/paths-1/pathep-[eth1/1]', '"
                         "encap': 'vlan-5'}}}, {'fvRsDomAtt': {'attributes': {"
                         "'tDn': 'uni/phys-allvlans'}}}]}}]}}]}}")
        tenant = Tenant('cisco')
        app = AppProfile('ordersystem', tenant)
        web_epg = EPG('web', app)
        intf = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(intf)
        web_epg.attach(vlan_intf)
        output = str(tenant.get_json())

        self.assertTrue(output == expected_json,
                        'Did not see expected JSON returned')


class TestPortChannel(unittest.TestCase):
    def create_pc(self):
        if1 = Interface('eth', '1', '101', '1', '8')
        if2 = Interface('eth', '1', '101', '1', '9')
        pc = PortChannel('pc1')
        pc.attach(if1)
        pc.attach(if2)
        return pc

    def test_create_pc(self):
        pc = self.create_pc()
        self.assertTrue(pc.is_interface())
        self.assertFalse(pc.is_vpc())
        fabric, infra = pc.get_json()

        expected_resp = ("{'infraInfra': {'children': [{'infraNodeP': {'attrib"
                         "utes': {'name': '1-101-1-8'}, 'children': [{'infraLe"
                         "afS': {'attributes': {'type': 'range', 'name': '1-10"
                         "1-1-8'}, 'children': [{'infraNodeBlk': {'attributes'"
                         ": {'from_': '101', 'name': '1-101-1-8', 'to_': '101'"
                         "}, 'children': []}}]}}, {'infraRsAccPortP': {'attrib"
                         "utes': {'tDn': 'uni/infra/accportprof-1-101-1-8'}, '"
                         "children': []}}]}}, {'infraAccPortP': {'attributes':"
                         " {'name': '1-101-1-8'}, 'children': [{'infraHPortS':"
                         " {'attributes': {'type': 'range', 'name': '1-101-1-8"
                         "'}, 'children': [{'infraPortBlk': {'attributes': {'t"
                         "oPort': '8', 'fromPort': '8', 'fromCard': '1', 'name"
                         "': '1-101-1-8', 'toCard': '1'}, 'children': []}}, {'"
                         "infraRsAccBaseGrp': {'attributes': {'tDn': 'uni/infr"
                         "a/funcprof/accbundle-pc1'}, 'children': []}}]}}]}}, "
                         "{'infraNodeP': {'attributes': {'name': '1-101-1-9'},"
                         " 'children': [{'infraLeafS': {'attributes': {'type':"
                         " 'range', 'name': '1-101-1-9'}, 'children': [{'infra"
                         "NodeBlk': {'attributes': {'from_': '101', 'name': '1"
                         "-101-1-9', 'to_': '101'}, 'children': []}}]}}, {'inf"
                         "raRsAccPortP': {'attributes': {'tDn': 'uni/infra/acc"
                         "portprof-1-101-1-9'}, 'children': []}}]}}, {'infraAc"
                         "cPortP': {'attributes': {'name': '1-101-1-9'}, 'chil"
                         "dren': [{'infraHPortS': {'attributes': {'type': 'ran"
                         "ge', 'name': '1-101-1-9'}, 'children': [{'infraPortB"
                         "lk': {'attributes': {'toPort': '9', 'fromPort': '9',"
                         " 'fromCard': '1', 'name': '1-101-1-9', 'toCard': '1'"
                         "}, 'children': []}}, {'infraRsAccBaseGrp': {'attribu"
                         "tes': {'tDn': 'uni/infra/funcprof/accbundle-pc1'}, '"
                         "children': []}}]}}]}}, {'infraFuncP': {'attributes':"
                         " {}, 'children': [{'infraAccBndlGrp': {'attributes':"
                         " {'lagT': 'link', 'name': 'pc1'}, 'children': []}}]}"
                         "}]}}")

        self.assertEqual(str(infra), expected_resp)

        # Not a VPC, so fabric should be None
        self.assertIsNone(fabric)

    def test_create_3rd_interface_as_vpc(self):
        pc = self.create_pc()
        path = pc._get_path()
        self.assertTrue(isinstance(path, str))

        # Add a 3rd interface to make it a VPC
        if3 = Interface('eth', '1', '102', '1', '9')
        pc.attach(if3)
        self.assertTrue(pc.is_vpc())
        path = pc._get_path()
        self.assertTrue(isinstance(path, str))
        fabric, infra = pc.get_json()
        # VPC, so fabric should have some configuration
        self.assertIsNotNone(fabric)

        # Remove the 3rd interface
        pc.detach(if3)
        self.assertFalse(pc.is_vpc())
        path = pc._get_path()
        self.assertTrue(isinstance(path, str))
        fabric, infra = pc.get_json()
        self.assertTrue(fabric is None)

    def test_internal_get_nodes(self):
        pc = self.create_pc()
        nodes = pc._get_nodes()

    def test_delete_vpc(self):
        pc = self.create_pc()
        pc.mark_as_deleted()
        fabric, infra = pc.get_json()
        fabric_url, infra_url = pc.get_url()


class TestContext(unittest.TestCase):
    def test_get_json(self):
        tenant = Tenant('cisco')
        context = Context('ctx-cisco', tenant)
        context_json = context.get_json()
        self.assertTrue('fvCtx' in context_json)

    def test_get_parent_class(self):
        self.assertEquals(Context._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        dn = 'uni/tn-tenant/ctx-test'
        self.assertEquals(Context._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        dn = 'uni/tn-tenant/ctx-test'
        self.assertEquals(Context._get_name_from_dn(dn), 'test')

    def test_set_allow_all(self):
        tenant = Tenant('cisco')
        context = Context('ctx-cisco', tenant)
        context_json = context.get_json()
        self.assertEqual(context_json['fvCtx']['attributes']['pcEnfPref'],
                         'enforced')
        context.set_allow_all()
        context_json = context.get_json()
        self.assertEqual(context_json['fvCtx']['attributes']['pcEnfPref'],
                         'unenforced')


class TestBGP(unittest.TestCase):
    def test_bgp_router(self):
        tenant = Tenant('bgp-tenant')
        context = Context('bgp-test', tenant)
        outside = OutsideEPG('out-1', tenant)
        phyif = Interface('eth', '1', '101', '1', '46')
        phyif.speed = '1G'
        l2if = L2Interface('eth 1/101/1/46', 'vlan', '1')
        l2if.attach(phyif)
        l3if = L3Interface('l3if')
        l3if.set_l3if_type('l3-port')
        l3if.set_addr('1.1.1.2/30')
        l3if.add_context(context)
        l3if.attach(l2if)
        bgpif = BGPSession('test', peer_ip='1.1.1.1', node_id='101')
        bgpif.router_id = '172.1.1.1'
        bgpif.attach(l3if)
        bgpif.options = 'send-ext-com'
        bgpif.networks.append('0.0.0.0/0')
        contract1 = Contract('icmp')
        outside.provide(contract1)
        outside.add_context(context)
        outside.consume(contract1)
        outside.attach(bgpif)
        bgp_json = outside.get_json()


class TestOspf(unittest.TestCase):
    def test_ospf_router_port(self):
        tenant = Tenant('aci-toolkit-test')
        context = Context('ctx-cisco', tenant)
        outside = OutsideEPG('out-1', tenant)
        phyif = Interface('eth', '1', '101', '1', '8')
        l2if = L2Interface('eth 1/101/1/8.5', 'vlan', '5')
        l2if.attach(phyif)
        l3if = L3Interface('l3if')
        l3if.set_l3if_type('l3-port')
        l3if.set_addr('10.1.1.1/24')
        l3if.add_context(context)
        l3if.attach(l2if)
        rtr = OSPFRouter('rtr-1')
        ifpol = OSPFInterfacePolicy('myospf-pol', tenant)
        ifpol.set_nw_type('bcast')
        ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='2')
        ospfif.auth_key = 'd667d47acc18e6b'
        ospfif.auth_keyid = '1'
        ospfif.auth_type = 'simple'
        ospfif.networks.append('55.5.5.0/24')
        ospfif.int_policy_name = ifpol.name
        ospfif.attach(l3if)
        contract1 = Contract('contract-1')
        outside.provide(contract1)
        contract2 = Contract('contract-2')
        outside.consume(contract2)
        outside.attach(ospfif)
        ospf_json = outside.get_json()

class TestMonitorPolicy(unittest.TestCase):
    """
    Tests the monitoriing policy
    """
    def test_create(self):
        m_policy = MonitorPolicy('fabric','policy-name')
        self.assertEqual(m_policy.name,'policy-name')
        self.assertEqual(m_policy.policyType,'fabric')
        m_policy.set_name('policy-name-2')
        self.assertEqual(m_policy.name,'policy-name-2')
        m_policy.set_description('Policy description string')
        self.assertEqual(m_policy.description,'Policy description string')
    
    
class TestLiveAPIC(unittest.TestCase):
    def login_to_apic(self):
        """Login to the APIC
           RETURNS:  Instance of class Session
        """
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)
        return session


class TestLiveTenant(TestLiveAPIC):
    def get_all_tenants(self):
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)
        return tenants

    def get_all_tenant_names(self):
        tenants = self.get_all_tenants()
        names = []
        for tenant in tenants:
            names.append(tenant.name)
        return names

    def test_get_tenants(self):
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))
            self.assertTrue(isinstance(tenant.name, str))

    def test_get_deep_tenants(self):
        session = self.login_to_apic()
        tenants = Tenant.get_deep(session)
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))
            self.assertTrue(isinstance(tenant.name, str))

    def test_exists_tenant(self):
        session = self.login_to_apic()
        tenants = self.get_all_tenants()
        for tenant in tenants:
            self.assertTrue(Tenant.exists(session, tenant))

    def test_no_exists_tenant(self):
        session = self.login_to_apic()
        tenants = self.get_all_tenants()
        # Pick a non-existing tenant.
        # Do this by choosing the first tenant and loop
        # until a unique tenant is generated.
        non_existing_tenant = tenants[0]
        while non_existing_tenant in tenants:
            non_existing_tenant = Tenant(random_size_string())

        self.assertFalse(Tenant.exists(session, non_existing_tenant))

    def test_create_tenant(self):
        session = self.login_to_apic()

        # Get all of the existing tenants
        tenants = self.get_all_tenants()
        tenant_names = self.get_all_tenant_names()

        # Pick a unique tenant name not currently in APIC
        tenant_name = tenant_names[0]
        while tenant_name in tenant_names:
            tenant_name = random_size_string()

        # Create the tenant and push to APIC
        new_tenant = Tenant(tenant_name)
        resp = session.push_to_apic(new_tenant.get_url(),
                                    data=new_tenant.get_json())
        self.assertTrue(resp.ok)

        # Get all of the tenants and verify that the new tenant is present
        names = self.get_all_tenant_names()
        self.assertTrue(new_tenant.name in names)

        # Now delete the tenant
        new_tenant.mark_as_deleted()
        resp = session.push_to_apic(new_tenant.get_url(),
                                    data=new_tenant.get_json())
        self.assertTrue(resp.ok)

        # Get all of the tenants and verify that the new tenant is deleted
        names = self.get_all_tenant_names()
        self.assertTrue(new_tenant.name not in names)


class TestLiveSubscription(TestLiveAPIC):
    def test_create_class_subscription(self):
        session = self.login_to_apic()
        Tenant.subscribe(session)
        self.assertFalse(Tenant.has_events(session))
        Tenant.unsubscribe(session)

    def test_delete_unsubscribed_class_subscription(self):
        session = self.login_to_apic()
        Tenant.unsubscribe(session)
        self.assertFalse(Tenant.has_events(session))

    def test_double_class_subscription(self):
        session = self.login_to_apic()
        Tenant.subscribe(session)
        Tenant.subscribe(session)
        self.assertFalse(Tenant.has_events(session))
        Tenant.unsubscribe(session)

    def test_get_event_no_subcribe(self):
        session = self.login_to_apic()
        self.assertFalse(Tenant.has_events(session))
        self.assertRaises(ValueError, Tenant.get_event(session))

    def test_get_actual_event(self):
        session = self.login_to_apic()
        Tenant.subscribe(session)

        # Get all of the existing tenants
        tenants = Tenant.get(session)
        tenant_names = []
        for tenant in tenants:
            tenant_names.append(tenant.name)

        # Pick a unique tenant name not currently in APIC
        tenant_name = tenant_names[0]
        while tenant_name in tenant_names:
            tenant_name = random_size_string()

        # Create the tenant and push to APIC
        new_tenant = Tenant(tenant_name)
        resp = session.push_to_apic(new_tenant.get_url(),
                                    data=new_tenant.get_json())
        self.assertTrue(resp.ok)

        # Wait for the event to come through the subscription
        # If it takes more than 2 seconds, fail the test.
        # Pass the test as quickly as possible
        start_time = time.time()
        while True:
            current_time = time.time()
            time_elapsed = current_time - start_time
            self.assertTrue(time_elapsed < 2)
            if Tenant.has_events(session):
                break

        event_tenant = Tenant.get_event(session)
        is_tenant = isinstance(event_tenant, Tenant)
        self.assertTrue(is_tenant)

        new_tenant.mark_as_deleted()
        resp = session.push_to_apic(new_tenant.get_url(),
                                    data=new_tenant.get_json())
        self.assertTrue(resp.ok)

    def test_resubscribe(self):
        session = self.login_to_apic()
        Tenant.subscribe(session)

        # Test the refresh used for subscription timeout
        session.subscription_thread.refresh_subscriptions()

        # Test the resubscribe used after re-login on login timeout
        session.subscription_thread._resubscribe()


class TestLiveInterface(TestLiveAPIC):
    def get_valid_interface(self, session) :
        interfaces = Interface.get(session)
        return interfaces[0]
    
    def get_spine(self):
        session = self.login_to_apic()
        nodes = Node.get(session)
        for node in nodes:
            if node.get_role() == 'spine' and node.fabricSt == 'active':
                return node
        return None
    
    def test_get_all_interfaces(self):
        session = self.login_to_apic()
        self.assertRaises(TypeError, Interface.get, None)
        intfs = Interface.get(session)
        for interface in intfs:
            self.assertTrue(isinstance(interface, Interface))
            interface_as_a_string = str(interface)
            self.assertTrue(isinstance(interface_as_a_string, str))
            path = interface._get_path()
            self.assertTrue(isinstance(path, str))
            
    def test_get(self) :
        session = self.login_to_apic()
        interface = self.get_valid_interface(session)
        pod = interface.pod
        node = interface.node
        slot = interface.module
        port = interface.port
        self.assertRaises(TypeError, Interface.get, session,pod, node, slot, 33)
        self.assertRaises(TypeError, Interface.get, session,pod, node, 1, port)
        self.assertRaises(TypeError, Interface.get, session,pod, 101, slot, port)
        self.assertRaises(TypeError, Interface.get, session,1, node, slot, port)
        interface_again = Interface.get(session, pod, node, slot, port)[0]
        self.assertTrue(interface==interface_again)

        self.assertRaises(TypeError, Interface.get, session, pod)
        pod = Linecard(pod,node,slot)
        interfaces = Interface.get(session, pod)
        self.assertTrue(len(interfaces)>0)

    def test_get_adjacent(self) :
        session = self.login_to_apic()
        interfaces = Interface.get(session)
        for interface in interfaces :
            if interface.porttype=='fab' and interface.attributes['operSt']=='up':
                adj = interface.get_adjacent_port()
                fields = adj.split('/')
                self.assertEqual(len(fields),4)
                for field in fields :
                    self.assertIsInstance(int(field), int)

class TestLivePortChannel(TestLiveAPIC):
    def test_get_all_portchannels(self):
        session = self.login_to_apic()
        self.assertRaises(TypeError, PortChannel.get, None)
        portchannels = PortChannel.get(session)
        for pc in portchannels:
            self.assertTrue(isinstance(pc, PortChannel))
            pc_as_a_string = str(pc)
            self.assertTrue(isinstance(pc_as_a_string, str))


class TestLiveAppProfile(TestLiveAPIC):
    def test_invalid_app(self):
        session = self.login_to_apic()
        self.assertRaises(TypeError, AppProfile.get, session, None)

    def test_valid_preexisting_app(self):
        session = self.login_to_apic()


class TestLiveEPG(TestLiveAPIC):
    def test_get_epgs(self):
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        for tenant in tenants:
            apps = AppProfile.get(session, tenant)
            for app in apps:
                epgs = EPG.get(session, app, tenant)
                for epg in epgs:
                    self.assertTrue(isinstance(epg, EPG))


class TestLiveEndpoint(unittest.TestCase):
    def test_get_bad_session(self):
        bad_session = 'BAD SESSION'
        self.assertRaises(TypeError, Endpoint.get, bad_session)

    def test_get(self):
        # Login to APIC
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)

        endpoints = Endpoint.get(session)


class TestApic(unittest.TestCase):
    def base_test_setup(self):
        # Login to APIC
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)

        # Create the Tenant
        tenant = Tenant('aci-toolkit-test')
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Create the Application Profile
        app = AppProfile('app1', tenant)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Create the EPG
        epg = EPG('epg1', app)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        return(session, tenant, app, epg)

    def base_test_teardown(self, session, tenant):
        # Delete the tenant
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_assign_epg_to_interface(self):
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Count the EPG attachments
        url = ('/api/mo/uni/tn-%s.json?query-target=subtree&'
               'target-subtree-class=fvRsPathAtt' % tenant.name)
        attachments = session.get(url)
        num_attachments_before = int(attachments.json()['totalCount'])

        # Attach the EPG to an Interface
        intf = Interface('eth', '1', '101', '1', '69')
        l2_intf = L2Interface('l2if', 'vlan', '5')
        l2_intf.attach(intf)
        epg.attach(l2_intf)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Verify that the number of attachments increased
        attachments = session.get(url)
        num_attachments_after = int(attachments.json()['totalCount'])
        self.assertTrue(num_attachments_after > num_attachments_before,
                        'EPG was not added to the interface')

        # Remove the EPG from the Interface
        epg.detach(l2_intf)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Verify that the number of attachments decreased
        attachments = session.get(url)
        num_attachments_after = int(attachments.json()['totalCount'])
        self.assertTrue(num_attachments_after == num_attachments_before,
                        'EPG was not removed from the interface')

        self.base_test_teardown(session, tenant)

    def test_assign_bridgedomain_to_epg(self):
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Create the bridgedomain
        bd = BridgeDomain('bd1', tenant)

        # Assign the bridgedomain to the EPG
        epg.add_bd(bd)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        BridgeDomain.get(session, tenant)

        # Check the JSON that was sent
        expected = ('{"fvTenant": {"attributes": {"name": "aci-toolkit-test"},'
                    ' "children": [{"fvAp": {"attributes": {"name": "app1"}, '
                    '"children": [{"fvAEPg": {"attributes": {"name": "epg1"}, '
                    '"children": [{"fvRsBd": {"attributes": {"tnFvBDName": '
                    '"bd1"}}}]}}]}}, {"fvBD": {"attributes": {"name": "bd1"},'
                    ' "children": []}}]}}')
        actual = json.dumps(tenant.get_json())
        self.assertTrue(actual == expected)

        # Remove the bridgedomain from the EPG
        epg.remove_bd()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Clean up
        self.base_test_teardown(session, tenant)

    def test_get_contexts(self):
        (session, tenant, app, epg) = self.base_test_setup()
        Context.get(session, tenant)

    def test_get_contexts_invalid_tenant_as_string(self):
        (session, tenant, app, epg) = self.base_test_setup()
        self.assertRaises(TypeError, Context.get, session, 'tenant')

    def test_assign_epg_to_port_channel(self):
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Create the port channel
        intf1 = Interface('eth', '1', '105', '1', '38')
        intf2 = Interface('eth', '1', '105', '1', '39')
        intf3 = Interface('eth', '1', '106', '1', '38')
        intf4 = Interface('eth', '1', '106', '1', '39')
        pc = PortChannel('pc1')
        pc.attach(intf1)
        pc.attach(intf2)
        pc.attach(intf3)
        pc.attach(intf4)
        (fabric, infra) = pc.get_json()
        expected = ('{"fabricProtPol": {"attributes": {"name": "vpc105"}, '
                    '"children": [{"fabricExplicitGEp": {"attributes": '
                    '{"name": "vpc105", "id": "105"}, "children": [{'
                    '"fabricNodePEp": {"attributes": {"id": "105"}}}, '
                    '{"fabricNodePEp": {"attributes": {"id": "106"}}}]}}]}}')
        self.assertTrue(json.dumps(fabric) == expected)
        if fabric is not None:
            resp = session.push_to_apic('/api/mo/uni/fabric.json', data=fabric)
            self.assertTrue(resp.ok)

        resp = session.push_to_apic('/api/mo/uni.json', data=infra)
        self.assertTrue(resp.ok)

        # Assign the EPG to the port channel
        l2_intf = L2Interface('l2if', 'vlan', '5')
        l2_intf.attach(pc)
        epg.attach(l2_intf)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        self.base_test_teardown(session, tenant)

    def test_context_allow_all(self):
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Create a Context and assign to the tenant
        context = Context('ctx1', tenant)

        # Allow all communication (No contract enforcement)
        context.set_allow_all()

        # Push to APIC and verify a successful request
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        self.base_test_teardown(session, tenant)

    def test_bd_attach_context(self):
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Create a Context and assign to the tenant
        context = Context('ctx1', tenant)

        # Create a BridgeDomain and attach the Context to it
        bd = BridgeDomain('bd1', tenant)
        bd.attach(context)

        # Push to APIC and verify a successful request
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        self.base_test_teardown(session, tenant)

    def test_subnet_basic(self):
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Create a Context and assign to the tenant
        context = Context('ctx1', tenant)

        # Create a BridgeDomain and attach the Context to it
        bd = BridgeDomain('bd1', tenant)
        bd.attach(context)

        # Create a subnet on a bridgedomain
        subnet = Subnet('subnet1', bd)
        subnet.set_addr('10.10.10.10/24')

        # Push to APIC and verify a successful request
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        subnets = Subnet.get(session, bd, tenant)
        self.assertNotEqual(len(subnets), 0)

        # Cleanup
        self.base_test_teardown(session, tenant)

    def test_ospf_basic(self):
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Create a Context and assign to the tenant
        context = Context('ctx1', tenant)

        # Create a BridgeDomain and attach the Context to it
        bd = BridgeDomain('bd1', tenant)
        bd.attach(context)

        # Create a subnet on a bridgedomain
        subnet = Subnet('subnet1', bd)
        subnet.set_addr('10.10.10.10/24')

        # Create the Interface for the Outside
        intf = Interface('eth', '1', '101', '1', '37')

        # Assign an L2 Interface to the Physical Interface
        l2_intf = L2Interface('l2if', 'vlan', '5')
        l2_intf.attach(intf)

        # Create an L3 Interface on the L2 Interface
        l3_intf = L3Interface('l3if')
        l3_intf.set_l3if_type('l3-port')
        l3_intf.set_addr('10.3.1.1/24')
        l3_intf.add_context(context)
        l3_intf.attach(l2_intf)

        # Create an OSPF Router
        rtr = OSPFRouter('rtr-1')
        rtr.set_router_id('23.23.23.23')
        rtr.set_node_id('101')
        # Create an OSPF Interface and connect to the L3 Interface
        ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='2')
        ospfif.auth_key = 'password'
        ospfif.auth_keyid = '1'
        ospfif.auth_type = 'simple'
        ospfif.networks.append('55.5.5.0/24')
        ospfif.attach(l3_intf)

        # Create the Outside EPG
        self.assertRaises(TypeError, OutsideEPG, 'out-1', 'tenant')
        outside = OutsideEPG('out-1', tenant)
        outside.add_context(context)
        outside.attach(ospfif)

        # Create a contract and provide from the Outside EPG
        contract1 = Contract('contract-1', tenant)
        outside.provide(contract1)

        # Create another contract and consume from the Outside EPG
        contract2 = Contract('contract-2', tenant)
        outside.consume(contract2)

        # Push to APIC and verify a successful request
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        self.base_test_teardown(session, tenant)


class TestLiveContracts(TestLiveAPIC):
    def get_2_entries(self, contract):
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
                             parent=contract)
        entry2 = FilterEntry('entry2',
                             applyToFrag='no',
                             arpOpc='unspecified',
                             dFromPort='443',
                             dToPort='443',
                             etherT='ip',
                             prot='tcp',
                             sFromPort='1',
                             sToPort='65535',
                             tcpRules='unspecified',
                             parent=contract)
        return(entry1, entry2)

    def test_get(self):
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        contracts = Contract.get(session, tenant)

    def test_create_basic_contract(self):
        tenant = Tenant('aci-toolkit-test')
        contract = Contract('contract1', tenant)

        (entry1, entry2) = self.get_2_entries(contract)

        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_create_basic_taboo(self):
        tenant = Tenant('aci-toolkit-test')
        taboo = Taboo('taboo1', tenant)

        (entry1, entry2) = self.get_2_entries(taboo)

        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_contract_scope(self):
        tenant = Tenant('aci-toolkit-test')
        contract = Contract('contract1', tenant)
        (entry1, entry2) = self.get_2_entries(contract)

        session = self.login_to_apic()

        # Test scopes
        # Verify the default
        self.assertTrue(contract.get_scope() == 'context')

        # Set the scope to tenant and push to apic
        contract.set_scope('tenant')
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)
        self.assertTrue(contract.get_scope() == 'tenant')

        # Set the scope to global and push to apic
        contract.set_scope('global')
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)
        self.assertTrue(contract.get_scope() == 'global')

        # Set the scope to application-profile and push to apic
        contract.set_scope('application-profile')
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)
        self.assertTrue(contract.get_scope() == 'application-profile')

        # Set the scope to context and push to apic
        contract.set_scope('context')
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)
        self.assertTrue(contract.get_scope() == 'context')

        # Set the scope to an invalid value and
        # verify that it raises the correct error
        self.assertRaises(ValueError, contract.set_scope, 'invalidstring')

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)


class TestLiveOSPF(TestLiveAPIC):

        def test_no_auth(self):
            tenant = Tenant('cisco')
            context = Context('cisco-ctx1', tenant)
            outside = OutsideEPG('out-1', tenant)
            outside.add_context(context)
            phyif = Interface('eth', '1', '101', '1', '46')
            phyif.speed = '1G'
            l2if = L2Interface('eth 1/101/1/46', 'vlan', '1')
            l2if.attach(phyif)
            l3if = L3Interface('l3if')
            l3if.set_l3if_type('l3-port')
            l3if.set_mtu('1500')
            l3if.set_addr('1.1.1.2/30')
            l3if.add_context(context)
            l3if.attach(l2if)
            rtr = OSPFRouter('rtr-1')
            rtr.set_router_id('23.23.23.23')
            rtr.set_node_id('101')
            ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='1')
            ifpol = OSPFInterfacePolicy('myospf-pol', tenant)
            ifpol.set_nw_type('p2p')
            ospfif.int_policy_name = ifpol.name
            tenant.attach(ospfif)
            ospfif.networks.append('55.5.5.0/24')
            ospfif.attach(l3if)
            contract1 = Contract('contract-1')
            outside.provide(contract1)
            contract2 = Contract('contract-2')
            outside.consume(contract2)
            outside.attach(ospfif)
            session = self.login_to_apic()
            resp = session.push_to_apic(tenant.get_url(),
                                        data=tenant.get_json())
            self.assertTrue(resp.ok)

            # Cleanup
            tenant.mark_as_deleted()
            resp = session.push_to_apic(tenant.get_url(),
                                        data=tenant.get_json())
            self.assertTrue(resp.ok)

        def test_authenticated(self):
            tenant = Tenant('cisco')
            context = Context('cisco-ctx1', tenant)
            outside = OutsideEPG('out-1', tenant)
            outside.add_context(context)
            phyif = Interface('eth', '1', '101', '1', '46')
            phyif.speed = '1G'
            l2if = L2Interface('eth 1/101/1/46', 'vlan', '1')
            l2if.attach(phyif)
            l3if = L3Interface('l3if')
            l3if.set_l3if_type('l3-port')
            l3if.set_mtu('1500')
            l3if.set_addr('1.1.1.2/30')
            l3if.add_context(context)
            l3if.attach(l2if)
            rtr = OSPFRouter('rtr-1')
            rtr.set_router_id('23.23.23.23')
            rtr.set_node_id('101')
            ospfif = OSPFInterface('ospfif-1', rtr, '1')
            ospfif.auth_key = 'password'
            ospfif.auth_keyid = '1'
            ospfif.auth_type = 'simple'
            ifpol = OSPFInterfacePolicy('myospf-pol', tenant)
            ifpol.set_nw_type('p2p')
            ospfif.int_policy_name = ifpol.name
            tenant.attach(ospfif)
            ospfif.networks.append('55.5.5.0/24')
            ospfif.attach(l3if)
            contract1 = Contract('contract-1')
            outside.provide(contract1)
            contract2 = Contract('contract-2')
            outside.consume(contract2)
            outside.attach(ospfif)

            session = self.login_to_apic()
            resp = session.push_to_apic(tenant.get_url(),
                                        data=tenant.get_json())
            self.assertTrue(resp.ok)

            # Cleanup
            tenant.mark_as_deleted()
            resp = session.push_to_apic(tenant.get_url(),
                                        data=tenant.get_json())
            self.assertTrue(resp.ok)

class TestLiveMonitorPolicy(TestLiveAPIC):
    """
    Live tests of the monitoriing policy
    """
    def check_collection_policy(self, parent) :
        for index in parent.collection_policy :
            policy = parent.collection_policy[index]
            self.assertEqual(index, policy.granularity)
            self.assertIn(policy.granularity, ['5min', '15min', '1h', '1d',
                       '1w', '1mo', '1qtr', '1year'])
            self.assertIn(policy.retention, ['none', 'inherited', '5min', '15min', '1h', '1d',
                     '1w', '10d', '1mo', '1qtr', '1year', '2year', '3year'])
            self.assertIn(policy.adminState, ['enabled', 'disabled', 'inherited'])
            self.assertEqual(policy._parent, parent)
        
    def test_get(self):
        session = self.login_to_apic()
        policies = MonitorPolicy.get(session)
        self.assertTrue(len(policies)>0)
        for policy in policies :
            self.assertIn(policy.policyType,['fabric','access'])
            self.assertIsInstance(policy.name, str)
            self.check_collection_policy(policy)

    def test_monitor_target(self) :
        session = self.login_to_apic()
        policies = MonitorPolicy.get(session)
        for policy in policies :
            monitor_targets = policy.monitor_target
            
            for index in monitor_targets :
                monitor_target = monitor_targets[index]
                self.assertIn(monitor_target.scope,['l1PhysIf'])
                self.assertEqual(monitor_target._parent, policy)
                self.assertIsInstance(monitor_target.descr, str)
                self.assertIsInstance(monitor_target.name, str)
                self.check_collection_policy(monitor_target)
                
    def test_monitor_stats(self) :
        session = self.login_to_apic()
        policies = MonitorPolicy.get(session)
        for policy in policies :
            monitor_targets = policy.monitor_target
            for index in monitor_targets :
                monitor_stats = monitor_targets[index].monitor_stats
                for index2 in monitor_stats :
                    monitor_stat = monitor_stats[index2]
                    self.assertIn(monitor_stat.scope,['egrBytes', 'egrPkts', 'egrTotal', 'egrDropPkts',
                        'ingrBytes', 'ingrPkts', 'ingrTotal', 'ingrDropPkts',
                        'ingrUnkBytes', 'ingrUnkPkts', 'ingrStorm'])
                    self.assertEqual(monitor_stat._parent, monitor_targets[index])
                    self.assertIsInstance(monitor_stat.descr, str)
                    self.assertIsInstance(monitor_stat.name, str)
                    self.check_collection_policy(monitor_stat)

                
        
            
if __name__ == '__main__':

    live = unittest.TestSuite()
    live.addTest(unittest.makeSuite(TestLiveTenant))
    live.addTest(unittest.makeSuite(TestLiveAPIC))
    live.addTest(unittest.makeSuite(TestLiveInterface))
    live.addTest(unittest.makeSuite(TestLivePortChannel))
    live.addTest(unittest.makeSuite(TestLiveAppProfile))
    live.addTest(unittest.makeSuite(TestLiveEPG))
    live.addTest(unittest.makeSuite(TestLiveContracts))
    live.addTest(unittest.makeSuite(TestLiveEndpoint))
    live.addTest(unittest.makeSuite(TestApic))
    live.addTest(unittest.makeSuite(TestLiveSubscription))
    live.addTest(unittest.makeSuite(TestLiveOSPF))
    live.addTest(unittest.makeSuite(TestLiveMonitorPolicy))

    offline = unittest.TestSuite()
    offline.addTest(unittest.makeSuite(TestBaseRelation))
    offline.addTest(unittest.makeSuite(TestBaseACIObject))
    offline.addTest(unittest.makeSuite(TestTenant))
    offline.addTest(unittest.makeSuite(TestAppProfile))
    offline.addTest(unittest.makeSuite(TestBridgeDomain))
    offline.addTest(unittest.makeSuite(TestL2Interface))
    offline.addTest(unittest.makeSuite(TestL3Interface))
    offline.addTest(unittest.makeSuite(TestInterface))
    offline.addTest(unittest.makeSuite(TestBaseContract))
    offline.addTest(unittest.makeSuite(TestContract))
    offline.addTest(unittest.makeSuite(TestTaboo))
    offline.addTest(unittest.makeSuite(TestEPG))
    offline.addTest(unittest.makeSuite(TestOutsideEPG))
    offline.addTest(unittest.makeSuite(TestJson))
    offline.addTest(unittest.makeSuite(TestPortChannel))
    offline.addTest(unittest.makeSuite(TestContext))
    offline.addTest(unittest.makeSuite(TestOspf))
    offline.addTest(unittest.makeSuite(TestBGP))
    offline.addTest(unittest.makeSuite(TestEndpoint))
    offline.addTest(unittest.makeSuite(TestMonitorPolicy))
    

    full = unittest.TestSuite([live, offline])

    # Add tests to this suite while developing the tests
    # This allows only these tests to be run
    develop = unittest.TestSuite()

    unittest.main(defaultTest='offline')
