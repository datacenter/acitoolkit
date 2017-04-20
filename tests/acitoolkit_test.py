################################################################################
#                                  _    ____ ___                               #
#                                 / \  / ___|_ _|                              #
#                                / _ \| |    | |                               #
#                               / ___ \ |___ | |                               #
#                         _____/_/   \_\____|___|_ _                           #
#                        |_   _|__   ___ | | | _(_) |_                         #
#                          | |/ _ \ / _ \| | |/ / | __|                        #
#                          | | (_) | (_) | |   <| | |_                         #
#                          |_|\___/ \___/|_|_|\_\_|\__|                        #
#                                                                              #
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
"""ACI Toolkit Test module
"""
from acitoolkit import (
    AppProfile, BaseContract, BaseACIObject, BaseRelation,
    BGPSession, BridgeDomain, Context, Contract, ContractInterface,
    ContractSubject, Endpoint, EPG, EPGDomain, Filter, FilterEntry, L2ExtDomain,
    L2Interface, L3ExtDomain, L3Interface, MonitorPolicy, OSPFInterface,
    OSPFInterfacePolicy, OSPFRouter, OutsideEPG, OutsideL3, PhysDomain,
    PortChannel, Subnet, Taboo, Tenant, VmmDomain, LogicalModel, OutsideNetwork,
    AttributeCriterion, OutsideL2, TunnelInterface, FexInterface, VMM,
    OutsideL2EPG, AnyEPG, InputTerminal, OutputTerminal, AcitoolkitGraphBuilder,
    Interface, Linecard, Node, Fabric, Table, Session, HealthScore)
import os.path
import unittest
import string
import random
import time
import json
import sys

try:
    from credentials import URL, LOGIN, PASSWORD, CERT_NAME, KEY
except ImportError:
    print
    print('To run live tests, please create a credentials.py file with the following variables filled in:')
    print("""
    URL = ''
    LOGIN = ''
    PASSWORD = ''
    CERT_NAME = ''
    KEY = ''
    """)
try:
    from credentials import APPCENTER_LOGIN, APPCENTER_CERT_NAME, APPCENTER_KEY
except ImportError:
    print('To run appcenter tests, please create a credentials.py file with the following variables filled in:')
    print("""
    APPCENTER_LOGIN=''
    APPCENTER_CERT_NAME=''
    APPCENTER_KEY=''
    """)


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

    def test_eq(self):
        """
        Test __eq__
        """
        tenant, relation = self.create_attached_relation()
        tenant2, relation2 = self.create_attached_relation()
        self.assertEqual(relation, relation2)

    def test_hashing_based_on_eq_same_object(self):
        """
        Test that the __hash__ works according to __eq__
        Details: https://github.com/datacenter/acitoolkit/issues/233
        """
        tenant, relation = self.create_attached_relation()
        tenant2, relation2 = self.create_attached_relation()
        test_dic = {}
        test_dic[relation] = 5
        test_dic[relation2] = 10
        """
        relation == relation2 in this case as per __eq__, this means that there should
        only be one entry in the dictonary, otherwise we have duplicated keys.
        """
        self.assertEqual(len(test_dic), 1)
        self.assertEqual(test_dic[relation], 10)
        self.assertEqual(test_dic[relation2], 10)

    def test_hashing_based_on_eq_multiple_objects(self):
        """
        Test that the __hash__ works according to __eq__
        Details: https://github.com/datacenter/acitoolkit/issues/233
        """
        tenant, relation = self.create_attached_relation()
        tenant2, relation2 = self.create_attached_relation()
        tenant3, relation3 = self.create_detached_relation()
        self.assertEqual(relation, relation2)
        self.assertNotEqual(relation, relation3)
        self.assertNotEqual(relation2, relation3)
        test_dic = {}
        test_dic[relation] = 5
        test_dic[relation2] = 10
        test_dic[relation3] = 5
        self.assertEqual(len(test_dic), 2)
        self.assertEqual(test_dic[relation], 10)
        self.assertEqual(test_dic[relation2], 10)


class MockACIObject(BaseACIObject):
    """
    Test object to test inheriting from BaseACIObject
    """
    def get_json(self):
        """
        Get the JSON
        :return: None
        """
        attr = self._generate_attributes()
        super(MockACIObject, self).get_json('mock', attributes=attr)

    def write(self, text):
        """Used to override sys.stdout calls to avoid printing
           coming from 3rd party libraries
        """
        pass


class TestBaseACIObject(unittest.TestCase):
    """
    Test the BaseACIObject class
    """
    def test_create_valid(self):
        """
        Create a valid object inheriting from BaseACIObject
        """
        obj = MockACIObject('mock')
        self.assertTrue(isinstance(obj, MockACIObject))

    def test_create_invalid_name_is_none(self):
        """
        Create an invalid BaseACIObject object that has no name
        """
        self.assertRaises(TypeError, MockACIObject)

    def test_create_invalid_name_is_not_string(self):
        """
        Create an invalid BaseACIObject object that has a non-string name
        """
        name = 53
        self.assertRaises(TypeError, MockACIObject, name)

    def test_create_invalid_parent_as_string(self):
        """
        Create an invalid BaseACIObject object that has a parent as a string
        """
        name = 'valid'
        invalid_parent = 'parent'
        self.assertRaises(TypeError, MockACIObject, name, invalid_parent)

    def test_string_transform(self):
        """
        Test the ability to convert the object to a string
        """
        obj = MockACIObject('mock')
        object_as_string = str(obj)
        self.assertTrue(isinstance(object_as_string, str))

    def test_attach(self):
        """
        Test attaching one object to another
        """
        obj1 = MockACIObject('mock')
        obj2 = MockACIObject('mock')
        obj1.attach(obj2)
        self.assertTrue(obj1.is_attached(obj2))
        return obj1, obj2

    def test_double_attach(self):
        """
        Test attaching one object to another twice is still attached
        """
        obj1, obj2 = self.test_attach()
        obj1.attach(obj2)
        self.assertTrue(obj1.is_attached(obj2))

    def test_detach(self):
        """
        Test detaching one object from another
        """
        obj1, obj2 = self.test_attach()
        obj1.detach(obj2)
        self.assertFalse(obj1.is_attached(obj2))

    def test_detach_unattached(self):
        """
        Test detaching one object from another twice
        """
        obj1 = MockACIObject('mock')
        obj2 = MockACIObject('mock')
        self.assertFalse(obj1.is_attached(obj2))
        obj1.detach(obj2)
        self.assertFalse(obj1.is_attached(obj2))

    def test_eq(self):
        """
        Test __eq__
        """
        obj1 = MockACIObject('mock')
        obj2 = MockACIObject('mock')
        self.assertEqual(obj1, obj2)

    def test_hashing_based_on_eq_same_object(self):
        """
        Test that the __hash__ works according to __eq__
        Details: https://github.com/datacenter/acitoolkit/issues/233
        """
        obj1 = MockACIObject('mock')
        obj2 = MockACIObject('mock')
        test_dic = {}
        test_dic[obj1] = 5
        test_dic[obj2] = 10
        """
        obj1 == obj2 in this case as per __eq__, this means that there should
        only be one entry in the dictonary, otherwise we have duplicated keys.
        """
        self.assertEqual(len(test_dic), 1)
        self.assertEqual(test_dic[obj1], 10)
        self.assertEqual(test_dic[obj2], 10)

    def test_hashing_based_on_eq_multiple_objects(self):
        """
        Test that the __hash__ works according to __eq__
        Details: https://github.com/datacenter/acitoolkit/issues/233
        """
        obj1 = MockACIObject('mock')
        obj2 = MockACIObject('mock')
        obj3 = MockACIObject('mock2')
        self.assertEqual(obj1, obj2)
        self.assertNotEqual(obj1, obj3)
        self.assertNotEqual(obj2, obj3)
        test_dic = {}
        test_dic[obj1] = 5
        test_dic[obj2] = 10
        test_dic[obj3] = 5
        self.assertEqual(len(test_dic), 2)
        self.assertEqual(test_dic[obj1], 10)
        self.assertEqual(test_dic[obj2], 10)


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
        self.assertEqual(Tenant._get_parent_class(), LogicalModel)

    def test_get_name_from_dn(self):
        """
        Ensure gives the correct name from a dn for a Tenant
        """
        dn = 'uni/tn-test'
        self.assertEqual(Tenant._get_name_from_dn(dn), 'test')

    def test_get_table(self):
        """
        Test tenant create table function
        """
        tenants = [Tenant('tenant1'), Tenant('tenant2'), Tenant('tenant3')]
        self.assertTrue(isinstance(Tenant.get_table(tenants)[0], Table))

    def test_bad_parent(self):
        fabric = Fabric()
        tenant = Tenant('mytenant', parent=fabric)
        self.assertRaises(TypeError, Tenant, 'badtenant', tenant)


class TestSession(unittest.TestCase):
    """
    Offline tests for the Session class
    """
    def test_session_with_https(self):
        session = Session('https://myapic.mydomain.com', 'admin', 'password')
        self.assertTrue(isinstance(session, Session))


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
        self.assertEqual(AppProfile._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        """
        Test AppProfile._get_parent_dn returns correct dn of the
        parent
        """
        dn = 'uni/tn-tenant/ap-test'
        self.assertEqual(AppProfile._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        """
        Test that AppProfile._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'uni/tn-tenant/ap-test'
        self.assertEqual(AppProfile._get_name_from_dn(dn), 'test')

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

    def test_get_table(self):
        """
        Test app profile create table function
        """
        tenant1 = Tenant('tenant1')
        tenant2 = Tenant('tenant2')
        app1 = AppProfile('app', tenant1)
        app2 = AppProfile('app', tenant2)
        app_profiles = [app1, app2]
        self.assertTrue(isinstance(AppProfile.get_table(app_profiles)[0], Table))


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
        self.assertEqual(BridgeDomain._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        """
        Test BridgeDomain._get_parent_dn returns correct dn of the
        parent
        """
        dn = 'uni/tn-tenant/BD-test'
        self.assertEqual(BridgeDomain._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        """
        Test that BridgeDomain._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'uni/tn-tenant/BD-test'
        self.assertEqual(BridgeDomain._get_name_from_dn(dn), 'test')

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
        """
        Test adding the same subnet twice to the same BridgeDomain
        """
        bd, sub1 = self.create_bd_with_subnet()
        bd.add_subnet(sub1)
        self.assertTrue(len(bd.get_subnets()) == 1)

    def test_add_subnet_different_bd(self):
        """
        Test adding the same subnet to 2 different BridgeDomains
        """
        tenant, bd = self.create_bd()
        subnet = Subnet('subnet', bd)
        subnet.set_addr('1.2.3.4/24')
        bd.add_subnet(subnet)
        bd2 = BridgeDomain('bd2', tenant)
        bd2.add_subnet(subnet)
        self.assertTrue(bd2.has_subnet(subnet))

    def test_set_subnet_addr_to_none(self):
        """
        Test adding subnet to None
        """
        bd, sub1 = self.create_bd_with_subnet()
        self.assertRaises(TypeError, sub1.set_addr, None)

    def test_has_subnet_wrong_type(self):
        """
        Test has_subnet with the wrong object class
        """
        tenant, bd = self.create_bd()
        self.assertRaises(TypeError, bd.has_subnet, tenant)

    def test_has_subnet_no_addr(self):
        """
        Test subnet without address set
        """
        tenant, bd = self.create_bd()
        sub1 = Subnet('sub1', bd)
        self.assertRaises(ValueError, bd.has_subnet, sub1)

    def test_remove_subnet(self):
        """
        Test remove subnet
        """
        bd, sub1 = self.create_bd_with_subnet()
        bd.remove_subnet(sub1)
        self.assertFalse(bd.has_subnet(sub1))
        self.assertTrue(len(bd.get_subnets()) == 0)

    def test_remove_2_subnets(self):
        """
        Test remove 2 subnets
        """
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
        """
        Test remove subnet of the wrong type
        """
        bd, sub1 = self.create_bd_with_subnet()
        self.assertRaises(TypeError, bd.remove_subnet, 'sub1')

    def test_add_context(self):
        """
        Test adding context to the bd
        """
        tenant, bd = self.create_bd()
        context = Context('ctx', tenant)
        bd.add_context(context)
        self.assertTrue(bd.get_context() == context)

    def test_add_context_twice(self):
        """
        Test adding the same context twice
        """
        tenant, bd = self.create_bd()
        context = Context('ctx', tenant)
        bd.add_context(context)
        bd.add_context(context)
        self.assertTrue(bd.get_context() == context)
        bd.remove_context()
        self.assertTrue(bd.get_context() is None)

    def test_remove_context(self):
        """
        Test removing the context
        """
        tenant, bd = self.create_bd()
        context = Context('ctx', tenant)
        bd.add_context(context)
        bd.remove_context()
        self.assertTrue(bd.get_context() is None)

    def test_get_table(self):
        """
        Test get table function
        """
        # Create a tenant
        tenant = Tenant('tenant')

        # Create a few bridge domains, generate and populate their attributes
        bd1 = BridgeDomain('bd1', tenant)
        attr1 = bd1._generate_attributes()
        bd1._populate_from_attributes(attr1)

        bd2 = BridgeDomain('bd2', tenant)
        attr2 = bd2._generate_attributes()
        bd2._populate_from_attributes(attr2)

        bd3 = BridgeDomain('bd3', tenant)
        attr3 = bd3._generate_attributes()
        bd3._populate_from_attributes(attr3)

        bridge_domains = [bd1, bd2, bd3]
        self.assertTrue(isinstance(BridgeDomain.get_table(bridge_domains)[0], Table))

    def test_unknown_mac_unicast_default(self):
        """
        Test default unknown mac unicast
        """
        tenant, bd = self.create_bd()
        self.assertTrue(bd.get_unknown_mac_unicast(), 'proxy')

    def test_unknown_mac_unicast_flood(self):
        """
        Test changing unknown mac unicast to flood
        """
        tenant, bd = self.create_bd()
        bd.set_unknown_mac_unicast('flood')
        self.assertTrue(bd.get_unknown_mac_unicast(), 'flood')

    def test_set_mac(self):
        """
        Test an invalid unknown mac unicast
        """
        tenant, bd = self.create_bd()
        bd.set_mac('00:11:22:33:44:55')
        self.assertTrue(bd.mac, '00:11:22:33:44:55')

    def test_unknown_mac_unicast_invalid(self):
        """
        Test an invalid unknown mac unicast
        """
        tenant, bd = self.create_bd()
        self.assertRaises(ValueError,
                          bd.set_unknown_mac_unicast, "invalid")

    def test_unknown_mac_unicast_change(self):
        """
        Test changing unknown mac unicast multiple times
        """
        tenant, bd = self.create_bd()
        bd.set_unknown_mac_unicast('proxy')
        bd.set_unknown_mac_unicast('flood')
        self.assertTrue(bd.get_unknown_mac_unicast(), 'flood')

    def test_unknown_multicast_default(self):
        """
        Test default unknown multicast
        """
        tenant, bd = self.create_bd()
        self.assertTrue(bd.get_unknown_multicast(), 'flood')

    def test_unknown_multicast_opt_flood(self):
        """
        Test changing unknown multicast to optimized flood
        """
        tenant, bd = self.create_bd()
        bd.set_unknown_multicast('opt-flood')
        self.assertTrue(bd.get_unknown_multicast(), 'opt-flood')

    def test_unknown_multicast_invalid(self):
        """
        Test an invalid unknown multicast
        """
        tenant, bd = self.create_bd()
        self.assertRaises(ValueError,
                          bd.set_unknown_multicast, "invalid")

    def test_unknown_multicast_change(self):
        """
        Test changing unknown multicast multiple times
        """
        tenant, bd = self.create_bd()
        bd.set_unknown_multicast('opt-flood')
        bd.set_unknown_multicast('flood')
        self.assertTrue(bd.get_unknown_mac_unicast(), 'flood')

    def test_arp_flood_default(self):
        """
        Test default arp flood
        """
        tenant, bd = self.create_bd()
        self.assertFalse(bd.is_arp_flood())

    def test_arp_flood_switch(self):
        """
        Test switching arp flood value
        """
        tenant, bd = self.create_bd()
        bd.set_arp_flood("yes")
        self.assertTrue(bd.is_arp_flood())

    def test_arp_flood_invalid(self):
        """
        Test an invalid arp flood
        """
        tenant, bd = self.create_bd()
        self.assertRaises(ValueError,
                          bd.set_arp_flood, 'invalid')

    def test_arp_flood_change(self):
        """
        Test changing arp flood multiple times
        """
        tenant, bd = self.create_bd()
        bd.set_arp_flood('yes')
        bd.set_arp_flood('no')
        self.assertFalse(bd.is_arp_flood())

    def test_multidestination(self):
        """
        Test changing multidestination
        """
        tenant, bd = self.create_bd()
        for multidestination_setting in ['drop', 'bd-flood', 'encap-flood']:
            bd.set_multidestination(multidestination_setting)
            self.assertEqual(bd.multidestination, multidestination_setting)

    def test_invalid_multidestination(self):
        """
        Test changing multidestination to an invalid value
        """
        tenant, bd = self.create_bd()
        with self.assertRaises(ValueError):
            bd.set_multidestination('bad-value')
        self.assertNotEqual(bd.multidestination, 'bad-value')

    def test_unicast_route_default(self):
        """
        Test default unicast route
        """
        tenant, bd = self.create_bd()
        self.assertTrue(bd.is_unicast_route())

    def test_unicast_route_switch(self):
        """
        Test switching unicast route value
        """
        tenant, bd = self.create_bd()
        bd.set_unicast_route('no')
        self.assertFalse(bd.is_unicast_route())

    def test_unicast_route_invalid(self):
        """
        Test an invalid unicast route
        """
        tenant, bd = self.create_bd()
        self.assertRaises(ValueError,
                          bd.set_unicast_route, 'invalid')

    def test_unicast_route_change(self):
        """
        Test changing unicast route multiple times
        """
        tenant, bd = self.create_bd()
        bd.set_unicast_route('no')
        bd.set_unicast_route('yes')
        self.assertTrue(bd.is_unicast_route())


class TestContractInterface(unittest.TestCase):
    """
    Test the ContractInterface class
    """
    def setUp(self):
        """
        Set up the basic scenario
        """
        self.tenant1 = Tenant('testtenant1')
        self.contract = Contract('testcontract', self.tenant1)
        self.tenant2 = Tenant('testtenant2')
        self.contract_if = ContractInterface('testcontractif', self.tenant2)
        self.contract_if.import_contract(self.contract)

    def test_has_import(self):
        """
        Test has_import_contract function
        """
        self.assertTrue(self.contract_if.has_import_contract())

    def test_does_import_contract(self):
        """
        Test does_import_contract function
        """
        self.assertTrue(self.contract_if.does_import_contract(self.contract))

    def test_does_not_import_contract(self):
        """
        Test does_import_contract function - negative scenario
        """
        tenant = Tenant('testtenant2')
        contract = Contract('testcontract', tenant)
        self.assertFalse(self.contract_if.does_import_contract(contract))

    def test_import_contract_twice(self):
        """
        Test calling does_import_contract function twice
        """
        self.contract_if.import_contract(self.contract)
        self.assertTrue(self.contract_if.does_import_contract(self.contract))

    def test_import_different_contract(self):
        """
        Test importing a different contract
        """
        tenant = Tenant('testtenant2')
        contract = Contract('testcontract', tenant)
        self.contract_if.import_contract(contract)
        self.assertTrue(self.contract_if.does_import_contract(contract))
        self.assertFalse(self.contract_if.does_import_contract(self.contract))
        self.assertEqual(len(self.contract_if._get_all_relation(Contract, 'imported')), 1)

    def test_get_json(self):
        """
        Test get_json
        """
        tenant_json = self.tenant2.get_json()
        expected_json = {
            'fvTenant': {
                'attributes':
                    {
                        'name': 'testtenant2'
                    },
                'children':
                    [
                        {
                            'vzCPIf':
                                {
                                    'attributes':
                                        {
                                            'name': 'testcontractif'
                                        },
                                    'children':
                                        [
                                            {
                                                'vzRsIf':
                                                    {
                                                        'attributes':
                                                            {
                                                                'tDn': 'uni/tn-testtenant1/brc-testcontract'
                                                            }
                                                    }
                                            }
                                        ]
                                }
                        }
                    ]
            }
        }
        self.assertEqual(tenant_json, expected_json)


class TestL2Interface(unittest.TestCase):
    """
    Test the L2Interface class
    """
    def test_create_valid_vlan(self):
        """
        Test a valid vlan encap on an L2Interface object
        """
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vlan', '5')
        self.assertTrue(l2if is not None)
        self.assertTrue(l2if.get_encap_type() == 'vlan')
        self.assertTrue(l2if.get_encap_id() == '5')

    def test_create_valid_nvgre(self):
        """
        Test a valid nvgre encap on an L2Interface object
        """
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'nvgre', '5')
        self.assertTrue(l2if is not None)

    def test_create_valid_vxlan(self):
        """
        Test a valid vxlan encap on an L2Interface object
        """
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vxlan', '5')
        self.assertTrue(l2if is not None)

    def test_invalid_create_bad_encap_type(self):
        """
        Test an invalid encap type on an L2Interface object
        """
        self.assertRaises(ValueError, L2Interface,
                          'vlan5_on_eth1/1/1/1', 'invalid_encap', '5')

    def test_invalid_create_bad_encap_id_non_number(self):
        """
        Test an invalid encap value on an L2Interface object
        """
        self.assertRaises(ValueError, L2Interface,
                          'vlan5_on_eth1/1/1/1', 'invalid_encap', 'vlan')

    def test_invalid_create_bad_encap_id_none(self):
        """
        Test an invalid encap on an L2Interface object
        """
        self.assertRaises(ValueError, L2Interface,
                          'vlan5_on_eth1/1/1/1', 'invalid_encap', None)

    def test_invalid_create_bad_name_none(self):
        """
        Test an invalid name on an L2Interface object
        """
        self.assertRaises(TypeError, L2Interface, None, 'vlan', '5')

    def test_invalid_create_bad_name_not_string(self):
        """
        Test an non-string name on an L2Interface object
        """
        random_object = Tenant('foo')
        self.assertRaises(TypeError, L2Interface, random_object, 'vlan', '5')

    def test_is_interface(self):
        """
        Test is_interface on an L2Interface object
        """
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vlan', '5')
        self.assertTrue(l2if.is_interface())

    def test_path(self):
        """
        Test path assignment on an L2Interface object
        """
        l2if = L2Interface('vlan5_on_eth1/1/1/1', 'vlan', '5')
        self.assertTrue(l2if._get_path() is None)

        physif = Interface('eth', '1', '1', '1', '1')
        l2if.attach(physif)
        self.assertTrue(l2if._get_path() is not None)


class TestL3Interface(unittest.TestCase):
    """
    Test L3Interface class
    """
    def test_create_valid(self):
        """
        Test basic create
        """
        l3if = L3Interface('l3ifname')
        self.assertTrue(isinstance(l3if, L3Interface))

    def test_create_invalid_no_name(self):
        """
        Test invalid create that doesn't pass a name
        """
        self.assertRaises(TypeError, L3Interface)

    def test_is_interface(self):
        """
        Test that a call to is_instance on L3Interface will return True
        """
        l3if = L3Interface('l3ifname')
        self.assertTrue(l3if.is_interface())

    def test_set_addr(self):
        """
        Test setting address on L3Interface
        """
        l3if = L3Interface('l3ifname')
        self.assertEqual(l3if.get_addr(), None)
        l3if.set_addr('1.2.3.4/24')
        self.assertEqual(l3if.get_addr(), '1.2.3.4/24')

    def test_set_l3if_type(self):
        """
        Test set_l3if_type method with correct parameters
        """
        l3if = L3Interface('l3ifname')
        l3if.set_l3if_type('l3-port')
        self.assertEqual(l3if.get_l3if_type(), 'l3-port')

    def test_set_l3if_type_invalid(self):
        """
        Test set_l3if_type method with incorrect parameters
        """
        l3if = L3Interface('l3ifname')
        self.assertRaises(ValueError, l3if.set_l3if_type, 'invalid')

    def test_add_context(self):
        """
        Test adding a context to a L3Interface
        """
        l3if = L3Interface('l3ifname')
        ctx = Context('ctx')
        l3if.add_context(ctx)
        self.assertEqual(l3if.get_context(), ctx)

    def test_add_context_twice(self):
        """
        Test adding a context twice to a L3Interface
        """
        l3if = L3Interface('l3ifname')
        ctx = Context('ctx')
        l3if.add_context(ctx)
        l3if.add_context(ctx)
        self.assertEqual(l3if.get_context(), ctx)
        l3if.remove_context()
        self.assertIsNone(l3if.get_context())

    def test_add_context_different(self):
        """
        Test adding a different context to a L3Interface
        """
        l3if = L3Interface('l3ifname')
        ctx1 = Context('ctx1')
        ctx2 = Context('ctx2')
        l3if.add_context(ctx1)
        l3if.add_context(ctx2)
        self.assertEqual(l3if.get_context(), ctx2)
        self.assertTrue(l3if.has_context())

    def test_remove_context(self):
        """
        Test removing a context from a L3Interface
        """
        l3if = L3Interface('l3ifname')
        ctx = Context('ctx')
        l3if.add_context(ctx)
        l3if.remove_context()
        self.assertIsNone(l3if.get_context())
        self.assertFalse(l3if.has_context())


class TestBaseContract(unittest.TestCase):
    """
    Test the BaseContract class
    """
    def test_get_contract_code(self):
        """
        Test the _get_contract_code method raises not implemented exception
        """
        contract = BaseContract('contract')
        self.assertRaises(NotImplementedError,
                          contract._get_contract_code)

    def test_get_subject_code(self):
        """
        Test the _get_subject_code method raises not implemented exception
        """
        contract = BaseContract('contract')
        self.assertRaises(NotImplementedError,
                          contract._get_subject_code)

    def test_get_subject_relation_code(self):
        """
        Test the _get_subject_relation_code method raises not implemented exception
        """
        contract = BaseContract('contract')
        self.assertRaises(NotImplementedError,
                          contract._get_subject_relation_code)

    def test_set_scope(self):
        """
        Test the set_scope method
        """
        contract = BaseContract('contract')
        valid_scopes = ['context', 'global', 'tenant', 'application-profile']
        for scope in valid_scopes:
            contract.set_scope(scope)
        bad_scope = 'bad-scope'
        self.assertRaises(ValueError, contract.set_scope, bad_scope)


class TestContract(unittest.TestCase):
    """
    Test the Contract class
    """
    def test_create(self):
        """
        Test basic Contract creation
        """
        contract = Contract('contract')
        self.assertTrue(isinstance(contract, Contract))

    def test_internal_get_contract_code(self):
        """
        Test _get_contract_code method
        """
        self.assertEqual(Contract._get_contract_code(), 'vzBrCP')

    def test_get_parent_class(self):
        """
        Test _get_parent_class method
        """
        self.assertEqual(Contract._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        """
        Test _get_parent_dn method
        """
        dn = 'uni/tn-tenant/brc-test'
        self.assertEqual(Contract._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        """
        Test getting the contract name from _get_parent_dn method
        """
        dn = 'uni/tn-tenant/brc-test'
        self.assertEqual(Contract._get_name_from_dn(dn), 'test')

    def test_internal_generate_attributes(self):
        """
        Test _generate_attributes method
        """
        contract = Contract('contract')
        contract.set_scope('tenant')
        attributes = contract._generate_attributes()
        self.assertTrue('scope' in attributes)
        self.assertEqual(attributes['scope'], 'tenant')


class TestContractSubject(unittest.TestCase):
    """
    Test ContractSubject Class
    """
    def test_create(self):
        """
        Test basic ContractSubject class creation
        """
        contract_subject = ContractSubject('ContractSubject')
        self.assertTrue(isinstance(contract_subject, ContractSubject))

    def test_get_parent_class(self):
        """
        Test _get_parent_class method
        """
        self.assertEqual(ContractSubject._get_parent_class(), [Contract, Taboo])

    def test_get_json(self):
        """
        Test get_json method
        """
        cs_name = 'ContractSubject'
        cs = ContractSubject(cs_name)
        cs_json = cs.get_json()
        self.assertTrue('vzSubj' in cs_json)
        self.assertEqual(cs_json['vzSubj']['attributes']['name'], cs_name)

    def test_get_json_with_children(self):
        """
        Test get_json method with Filter children
        """
        cs_name = 'ContractSubject'
        cs = ContractSubject(cs_name)

        filt_name = 'Filter'
        filt = Filter(filt_name)
        cs.add_filter(filt)

        input_terminal_name = 'InputTerminal'
        it = InputTerminal(input_terminal_name, cs)

        output_terminal_name = 'OutTerminal'
        ot = OutputTerminal(output_terminal_name, cs)

        cs_json = cs.get_json()
        self.assertTrue('vzRsSubjFiltAtt' in cs_json['vzSubj']['children'][0])
        self.assertEqual(cs_json['vzSubj']['children'][0]['vzRsSubjFiltAtt']['attributes']['tnVzFilterName'],
                         filt_name)

        self.assertTrue('vzInTerm' in cs_json['vzSubj']['children'][1])
        self.assertEqual(cs_json['vzSubj']['children'][1]['vzInTerm']['attributes']['name'], input_terminal_name)

        self.assertTrue('vzOutTerm' in cs_json['vzSubj']['children'][2])
        self.assertEqual(cs_json['vzSubj']['children'][2]['vzOutTerm']['attributes']['name'], output_terminal_name)


class TestInputTerminal(unittest.TestCase):
    """
    Test InputTerminal Class
    """
    def test_create(self):
        """
        Test basic ContractSubject class creation
        """
        input_terminal = InputTerminal('InputTerminal')
        self.assertTrue(isinstance(input_terminal, InputTerminal))

    def test_get_parent_class(self):
        """
        Test _get_parent_class method
        """
        self.assertEqual(InputTerminal._get_parent_class(), ContractSubject)

    def test_get_json(self):
        """
        Test get_json method
        """
        it_name = 'InputTerminal'
        it = InputTerminal(it_name)
        it_json = it.get_json()
        self.assertTrue('vzInTerm' in it_json)
        self.assertEqual(it_json['vzInTerm']['attributes']['name'], it_name)

    def test_get_json_with_children(self):
        """
        Test get_json method with Filter children
        """
        it_name = 'InputTerminal'
        it = InputTerminal(it_name)
        filt_name = 'Filter'
        filt = Filter(filt_name)
        it.add_filter(filt)
        it_json = it.get_json()
        self.assertTrue('vzRsFiltAtt' in it_json['vzInTerm']['children'][0])
        self.assertEqual(it_json['vzInTerm']['children'][0]['vzRsFiltAtt']['attributes']['tnVzFilterName'],
                         filt_name)


class TestOutputTerminal(unittest.TestCase):
    """
    Test OutputTerminal Class
    """
    def test_create(self):
        """
        Test basic ContractSubject class creation
        """
        Output_terminal = OutputTerminal('OutputTerminal')
        self.assertTrue(isinstance(Output_terminal, OutputTerminal))

    def test_get_parent_class(self):
        """
        Test _get_parent_class method
        """
        self.assertEqual(OutputTerminal._get_parent_class(), ContractSubject)

    def test_get_json(self):
        """
        Test get_json method
        """
        ot_name = 'OutputTerminal'
        ot = OutputTerminal(ot_name)
        ot_json = ot.get_json()
        self.assertTrue('vzOutTerm' in ot_json)
        self.assertEqual(ot_json['vzOutTerm']['attributes']['name'], ot_name)

    def test_get_json_with_children(self):
        """
        Test get_json method with Filter children
        """
        it_name = 'OutputTerminal'
        it = OutputTerminal(it_name)
        filt_name = 'Filter'
        filt = Filter(filt_name)
        it.add_filter(filt)
        it_json = it.get_json()
        self.assertTrue('vzRsFiltAtt' in it_json['vzOutTerm']['children'][0])
        self.assertEqual(it_json['vzOutTerm']['children'][0]['vzRsFiltAtt']['attributes']['tnVzFilterName'],
                         filt_name)


class TestFilter(unittest.TestCase):
    """
    Test TestFilter class
    """
    def test_create(self):
        """
        Test basic TestFilter class creation
        """
        filt = Filter('Filter')
        self.assertTrue(isinstance(filt, Filter))

    def test_get_json(self):
        """
        Test get_json method
        """
        filt_name = 'Filter'
        filt = Filter(filt_name)
        filt_json = filt.get_json()
        self.assertTrue('vzFilter' in filt_json)
        self.assertEqual(filt_json['vzFilter']['attributes']['name'], filt_name)

    def test_get_json_with_children(self):
        """
        Test get_json method with FilterEntry children
        """
        filt_name = 'Filter'
        filt = Filter(filt_name)
        filt_entry_name = 'FilterEntry'
        filt_entry = FilterEntry(filt_entry_name, filt)
        filt_json = filt.get_json()
        self.assertTrue('vzEntry' in filt_json['vzFilter']['children'][0])
        self.assertEqual(filt_json['vzFilter']['children'][0]['vzEntry']['attributes']['name'],
                         filt_entry_name)


class TestFilterEntry(unittest.TestCase):
    """
    Test TestFilterEntry class
    """
    def test_create(self):
        """
        Test basic TestFilterEntry class creation
        """
        filt_name = 'Filter'
        filt = Filter(filt_name)
        filt_entry_name = 'FilterEntry'
        filt_entry = FilterEntry(filt_entry_name, filt)
        self.assertTrue(isinstance(filt_entry, FilterEntry))

    def test_get_json(self):
        """
        Test get_json method
        """
        filt_name = 'Filter'
        filt = Filter(filt_name)
        filt_entry_name = 'FilterEntry'
        filt_entry = FilterEntry(filt_entry_name, filt)
        filt_entry_json = filt_entry.get_json()
        self.assertTrue('vzEntry' in filt_entry_json)
        self.assertEqual(filt_entry_json['vzEntry']['attributes']['name'],
                         filt_entry_name)
        self.assertNotIn('icmpv4T', filt_entry_json['vzEntry']['attributes'])
        self.assertNotIn('icmpv6T', filt_entry_json['vzEntry']['attributes'])

    def test_get_json_with_icmpv4T(self):
        """
        Test test_get_json_with_icmpv4T method
        """
        filt_name = 'Filter'
        filt = Filter(filt_name)
        filt_entry_name = 'FilterEntry'
        filt_entry = FilterEntry(filt_entry_name, filt, icmpv4T='unspecified')
        filt_entry_json = filt_entry.get_json()
        self.assertTrue('vzEntry' in filt_entry_json)
        self.assertEqual(filt_entry_json['vzEntry']['attributes']['name'],
                         filt_entry_name)
        self.assertIn('icmpv4T', filt_entry_json['vzEntry']['attributes'])
        self.assertNotIn('icmpv6T', filt_entry_json['vzEntry']['attributes'])

    def test_get_json_with_icmpv6T(self):
        """
        Test test_get_json_with_icmpv4T method
        """
        filt_name = 'Filter'
        filt = Filter(filt_name)
        filt_entry_name = 'FilterEntry'
        filt_entry = FilterEntry(filt_entry_name, filt, icmpv6T='unspecified')
        filt_entry_json = filt_entry.get_json()
        self.assertTrue('vzEntry' in filt_entry_json)
        self.assertEqual(filt_entry_json['vzEntry']['attributes']['name'],
                         filt_entry_name)
        self.assertIn('icmpv6T', filt_entry_json['vzEntry']['attributes'])
        self.assertNotIn('icmpv4T', filt_entry_json['vzEntry']['attributes'])

    def test_get_json_with_icmpv4T_and_icmpv6T(self):
        """
        Test test_get_json_with_icmpv4T method
        """
        filt_name = 'Filter'
        filt = Filter(filt_name)
        filt_entry_name = 'FilterEntry'
        filt_entry = FilterEntry(filt_entry_name, filt, icmpv4T='unspecified', icmpv6T='unspecified')
        filt_entry_json = filt_entry.get_json()
        self.assertTrue('vzEntry' in filt_entry_json)
        self.assertEqual(filt_entry_json['vzEntry']['attributes']['name'],
                         filt_entry_name)
        self.assertIn('icmpv6T', filt_entry_json['vzEntry']['attributes'])
        self.assertIn('icmpv4T', filt_entry_json['vzEntry']['attributes'])

    def test_eq(self):
        """
        Test eq method
        """
        filt_name = 'filt'
        filt = Filter(filt_name)

        filt_entry_name = 'FiltEntry'
        filt_entry = FilterEntry(filt_entry_name, filt)

        filt_entry2_name = 'FiltEntry2'
        filt_entry2 = FilterEntry(filt_entry2_name, filt)
        self.assertEqual(filt_entry, filt_entry2)

    def test_hashing_based_on_eq_same_object(self):
        """
        Test that the __hash__ works according to __eq__
        Details: https://github.com/datacenter/acitoolkit/issues/233
        """
        filt_name = 'filt'
        filt = Filter(filt_name)

        filt_entry_name = 'FiltEntry'
        filt_entry = FilterEntry(filt_entry_name, filt)

        filt_entry2_name = 'FiltEntry2'
        filt_entry2 = FilterEntry(filt_entry2_name, filt)
        test_dic = {}
        test_dic[filt_entry] = 5
        test_dic[filt_entry2] = 10
        """
        filt_entry == filt_entry2 in this case as per __eq__, this means that there should
        only be one entry in the dictonary, otherwise we have duplicated keys.
        """
        self.assertEqual(len(test_dic), 1)
        self.assertEqual(test_dic[filt_entry], 10)
        self.assertEqual(test_dic[filt_entry2], 10)

    def test_hashing_based_on_eq_multiple_objects(self):
        """
        Test that the __hash__ works according to __eq__
        Details: https://github.com/datacenter/acitoolkit/issues/233
        """
        filt_name = 'filt'
        filt = Filter(filt_name)

        filt_entry_name = 'FiltEntry'
        filt_entry = FilterEntry(filt_entry_name, filt)

        filt_entry2_name = 'FiltEntry2'
        filt_entry2 = FilterEntry(filt_entry2_name, filt)

        filt_entry3_name = 'FiltEntry3'
        filt_entry3 = FilterEntry(filt_entry3_name, filt)
        filt_entry3.sFromPort = 80

        self.assertEqual(filt_entry, filt_entry2)
        self.assertNotEqual(filt_entry, filt_entry3)
        self.assertNotEqual(filt_entry2, filt_entry3)
        test_dic = {}
        test_dic[filt_entry] = 5
        test_dic[filt_entry2] = 10
        test_dic[filt_entry3] = 5
        self.assertEqual(len(test_dic), 2)
        self.assertEqual(test_dic[filt_entry], 10)
        self.assertEqual(test_dic[filt_entry2], 10)


class TestTaboo(unittest.TestCase):
    """
    Test Taboo class
    """
    def test_create(self):
        """
        Test basic Taboo class creation
        """
        taboo = Taboo('taboo')
        self.assertTrue(isinstance(taboo, Taboo))

    def test_internal_get_contract_code(self):
        """
        Test _get_contract_code method
        """
        self.assertEqual(Taboo._get_contract_code(), 'vzTaboo')

    def test_internal_get_subject_code(self):
        """
        Test _get_subject_code method
        """
        self.assertEqual(Taboo._get_subject_code(), 'vzTSubj')

    def test_internal_get_subject_relation_code(self):
        """
        Test _get_subject_relation_code method
        """
        self.assertEqual(Taboo._get_subject_relation_code(),
                         'vzRsDenyRule')

    def test_get_parent_class(self):
        """
        Test _get_parent_class method
        """
        self.assertEqual(Taboo._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        """
        Test _get_parent_dn method
        """
        dn = 'uni/tn-tenant/taboo-test'
        self.assertEqual(Taboo._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        """
        Test _get_name_from_dn method
        """
        dn = 'uni/tn-tenant/taboo-test'
        self.assertEqual(Taboo._get_name_from_dn(dn), 'test')

    def test_get_table(self):
        """
        Test get_table method
        """
        tenant = Tenant('tenant')
        taboo1 = Taboo('taboo1', tenant)
        taboo2 = Taboo('taboo2', tenant)
        taboo3 = Taboo('taboo3', tenant)
        taboos = [taboo1, taboo2, taboo3]
        self.assertIsInstance(Taboo.get_table(taboos)[0], Table)


class TestEPG(unittest.TestCase):
    """
    Test EPG class
    """
    def create_epg(self):
        """
        Method to create basic EPG used by test cases
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        return tenant, app, epg

    def create_epg_with_bd(self):
        """
        Method to create basic EPG with a BridgeDomain used by test cases
        """
        tenant, app, epg = self.create_epg()
        self.assertFalse(epg.has_bd())
        bd = BridgeDomain('bd', tenant)
        epg.add_bd(bd)
        return tenant, app, epg, bd

    def test_valid_create(self):
        """
        Test basic EPG creation
        """
        tenant, app, epg = self.create_epg()
        self.assertTrue(isinstance(epg, EPG))

    # def test_invalid_create_parent_none(self):
    #    self.assertRaises(TypeError, EPG, 'epg', None)

    def test_invalid_create_parent_wrong_class(self):
        """
        Test EPG creation with wrong parent class
        """
        tenant = Tenant('tenant')
        self.assertRaises(TypeError, EPG, 'epg', tenant)

    def test_get_parent_class(self):
        """
        Test EPG parent class is AppProfile
        """
        self.assertEqual(EPG._get_parent_class(), AppProfile)

    def test_get_parent_dn(self):
        """
        Test _get_parent_dn method
        """
        dn = 'uni/tn-tenant/ap-app/epg-test'
        self.assertEqual(EPG._get_parent_dn(dn), 'uni/tn-tenant/ap-app')

    def test_get_name_from_dn(self):
        """
        Test _get_name_from_dn method
        """
        dn = 'uni/tn-tenant/ap-app/epg-test'
        self.assertEqual(EPG._get_name_from_dn(dn), 'test')

    def test_valid_add_bd(self):
        """
        Test add_bd method
        """
        tenant, app, epg, bd = self.create_epg_with_bd()
        self.assertTrue(epg.has_bd())
        self.assertTrue(epg.get_bd() == bd)

    def test_valid_add_bd_json(self):
        """
        Test add_bd method produces correct JSON
        """
        tenant, app, epg, bd = self.create_epg_with_bd()
        self.assertTrue('fvRsBd' in str(tenant.get_json()))

    def test_invalid_add_bd_as_none(self):
        """
        Test add_bd method raises exception for BD as None
        """
        tenant, app, epg = self.create_epg()
        self.assertRaises(TypeError, epg.add_bd, None)

    def test_invalid_add_bd_wrong_class(self):
        """
        Test add_bd method raises exception for BD as wrong class
        """
        tenant, app, epg = self.create_epg()
        self.assertRaises(TypeError, epg.add_bd, tenant)

    def test_add_bd_twice(self):
        """
        Test add_bd method when adding BD twice
        """
        tenant, app, epg, bd = self.create_epg_with_bd()
        # Add the BD again
        epg.add_bd(bd)
        # Now, remove the BD
        epg.remove_bd()
        # Verify that a dangling BD was not left behind
        self.assertFalse(epg.has_bd())
        self.assertTrue(epg.get_bd() is None)

    def test_add_bd_two_different(self):
        """
        Test add_bd method cleans up when changing BD
        """
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
        """
        Test remove_bd method
        """
        tenant, app, epg, bd = self.create_epg_with_bd()
        epg.remove_bd()
        self.assertFalse(epg.has_bd())
        self.assertFalse(epg.get_bd() == bd)

    def test_tag_add(self):
        """
        Test add_tag method
        """
        tenant, app, epg = self.create_epg()
        self.assertFalse(epg.has_tags())
        epg.add_tag('secure')
        epg.add_tag('normal')
        self.assertTrue(epg.has_tags())
        self.assertTrue(epg.get_tags() == ['secure', 'normal'])
        self.assertTrue(epg.has_tag('secure'))

    def test_tag_remove(self):
        """
        Test remove_tag method
        """
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
        """
        Test provide method
        """
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

    def test_epg_does_provide(self):
        """
        Test does_provide method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
        epg.provide(contract1)
        self.assertTrue(epg.does_provide(contract1))

    def test_epg_dont_provide(self):
        """
        Test dont_provide method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
        epg.provide(contract1)
        output = tenant.get_json()
        self.assertIn('fvRsProv', str(output))
        self.assertNotIn('deleted', str(output))
        epg.dont_provide(contract1)
        output = tenant.get_json()
        self.assertIn('fvRsProv', str(output))
        self.assertIn('deleted', str(output))

    def test_epg_consume(self):
        """
        Test consume method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
        epg.consume(contract1)
        output = tenant.get_json()
        self.assertTrue('fvRsCons' in str(output))

    def test_epg_does_consume(self):
        """
        Test does_consume method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
        epg.consume(contract1)
        self.assertTrue(epg.does_consume(contract1))

    def test_epg_dont_consume(self):
        """
        Test dont_consume method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        contract1 = Contract('contract-1', tenant)
        epg.consume(contract1)
        output = tenant.get_json()
        self.assertIn('fvRsCons', str(output))
        self.assertNotIn('deleted', str(output))
        epg.dont_consume(contract1)
        output = tenant.get_json()
        self.assertIn('fvRsCons', str(output))
        self.assertIn('deleted', str(output))

    def test_epg_consume_cif(self):
        """
        Test consume method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        cif = ContractInterface('cif-1', tenant)
        epg.consume(cif)
        output = tenant.get_json()
        self.assertTrue('fvRsConsIf' in str(output))

    def test_epg_does_consume_cif(self):
        """
        Test does_consume_cif method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        cif = ContractInterface('cif-1', tenant)
        epg.consume_cif(cif)
        self.assertTrue(epg.does_consume_cif(cif))

    def test_epg_does_already_consume_cif(self):
        """
        Test does_consume_cif method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        cif = ContractInterface('cif-1', tenant)
        epg.consume_cif(cif)
        self.assertTrue(epg.does_consume_cif(cif))
        epg.consume_cif(cif)
        self.assertTrue(epg.does_consume_cif(cif))
        epg.dont_consume_cif(cif)
        self.assertFalse(epg.does_consume_cif(cif))
        epg.consume_cif(cif)
        self.assertTrue(epg.does_consume_cif(cif))

    def test_epg_dont_consume_cif(self):
        """
        Test dont_consume_cif method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        cif = ContractInterface('cif-1', tenant)
        epg.consume_cif(cif)
        output = tenant.get_json()
        self.assertIn('fvRsConsIf', str(output))
        self.assertNotIn('deleted', str(output))
        epg.dont_consume_cif(cif)
        output = tenant.get_json()
        self.assertIn('fvRsConsIf', str(output))
        self.assertIn('deleted', str(output))

    def test_epg_provide_consume(self):
        """
        Test provide and consume method together
        """
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

    def test_get_all_contracts_bad_contract_type(self):
        """
        Test _get_all_contracts with a bad contract_type
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        with self.assertRaises(ValueError):
            epg._get_all_contracts(contract_type='bad')

    def test_get_all_provided_with_include_any_epg_set_but_not_used(self):
        """
        Test get_all_provided with include_any_epg set to True but not used
        """
        tenant = Tenant('mytenant')
        app = AppProfile('myapp', tenant)
        epg = EPG('myepg', app)
        self.assertEqual(len(epg.get_all_provided(include_any_epg=True)), 0)

    def test_get_all_provided_with_include_any_epg_only_in_common(self):
        """
        Test get_all_provided with include_any_epg set to True and the AnyEPG is only in tenant common
        """
        fabric = Fabric()
        tenant = Tenant('mytenant', parent=fabric)
        app = AppProfile('myapp', tenant)
        epg = EPG('myepg', app)
        self.assertEqual(len(epg.get_all_provided(include_any_epg=True)), 0)

        tenant_common = Tenant('common', parent=fabric)
        context = Context('default', tenant_common)
        any_epg = AnyEPG('myany', context)

        contract = Contract('mycontract', tenant_common)
        any_epg.provide(contract)

        self.assertEqual(len(epg.get_all_provided()), 0)
        self.assertEqual(len(epg.get_all_provided(include_any_epg=True)), 1)
        self.assertEqual(len(epg.get_all_consumed(include_any_epg=True)), 0)

        any_epg.consume(contract)
        self.assertEqual(len(epg.get_all_consumed(include_any_epg=True)), 1)

    def test_get_all_provided_with_include_any_epg_in_tenant(self):
        fabric = Fabric()
        tenant = Tenant('mytenant', parent=fabric)
        app = AppProfile('myapp', tenant)
        epg = EPG('myepg', app)
        context = Context('mycontext', tenant)
        bd = BridgeDomain('mybd', tenant)
        bd.add_context(context)
        epg.add_bd(bd)
        contract = Contract('mycontract', tenant)

        self.assertEqual(len(epg.get_all_provided(include_any_epg=True)), 0)

        any_epg = AnyEPG('myanyepg', context)
        any_epg.provide(contract)

        self.assertEqual(len(epg.get_all_provided(include_any_epg=True)), 1)

    def test_protect(self):
        """
        Test protect method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        taboo = Taboo('taboo1', tenant)
        epg.protect(taboo)
        output = tenant.get_json()
        self.assertIn('fvRsProtBy', str(output))

    def test_double_call_to_protect(self):
        """
        Test protect method called twice
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        taboo = Taboo('taboo1', tenant)
        epg.protect(taboo)
        epg.protect(taboo)
        output = tenant.get_json()
        self.assertIn('fvRsProtBy', str(output))
        self.assertEqual(str(output).count('fvRsProtBy'), 1)

    def test_does_protect(self):
        """
        Test protect method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        taboo = Taboo('taboo1', tenant)
        epg.protect(taboo)
        self.assertTrue(epg.does_protect(taboo))
        epg.dont_protect(taboo)
        self.assertFalse(epg.does_protect(taboo))

    def test_dont_protect(self):
        """
        Test dont_protect method
        """
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        taboo = Taboo('taboo1', tenant)
        epg.protect(taboo)
        output = tenant.get_json()
        self.assertIn('fvRsProtBy', str(output))
        self.assertNotIn('deleted', str(output))
        epg.dont_protect(taboo)
        output = tenant.get_json()
        self.assertIn('fvRsProtBy', str(output))
        self.assertIn('deleted', str(output))

    def test_attach_epg(self):
        """
        Test attaching an EPG to an L2Interface
        """
        tenant, app, epg = self.create_epg()
        interface = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(interface)
        epg.attach(vlan_intf)
        self.assertTrue('fvRsPathAtt' in str(tenant.get_json()))

    def test_detach_epg(self):
        """
        Test detaching an EPG from an L2Interface
        """
        tenant, app, epg = self.create_epg()
        interface = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(interface)
        epg.attach(vlan_intf)
        epg.detach(vlan_intf)
        output = str(tenant.get_json())
        self.assertTrue(all(x in output for x in ('fvRsPathAtt', 'deleted')))

    def test_set_deployment_immediacy(self):
        """
        Test setting deployment immediacy
        """
        tenant, app, epg = self.create_epg()
        interface = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(interface)
        epg.attach(vlan_intf)
        epg.set_deployment_immediacy('immediate')
        output = str(tenant.get_json())
        self.assertTrue("'instrImedcy': 'immediate'" in output)

    def test_set_dom_deployment_immediacy(self):
        """
        Test setting domain deployment immediacy
        """
        tenant, app, epg = self.create_epg()
        domain = EPGDomain('test_epg_domain', tenant)
        epg.add_infradomain(domain)
        epg.set_dom_deployment_immediacy('immediate')
        output = str(tenant.get_json())
        self.assertTrue("'instrImedcy': 'immediate'" in output)

    def test_set_bad_infradomain(self):
        """
        Test setting a bad infradomain
        """
        tenant, app, epg = self.create_epg()
        with self.assertRaises(TypeError):
            epg.add_infradomain(tenant)

    def test_duplicate_add_infradomain(self):
        tenant, app, epg = self.create_epg()
        domain = EPGDomain('test_epg_domain', tenant)
        epg.add_infradomain(domain)
        epg.set_dom_resolution_immediacy('immediate')
        epg.add_infradomain(domain)
        output = str(tenant.get_json())
        self.assertTrue("'resImedcy': 'immediate'" in output)

    def test_set_dom_resolution_immediacy(self):
        """
        Test detaching an EPG from an L2Interface
        """
        tenant, app, epg = self.create_epg()
        domain = EPGDomain('test_epg_domain', tenant)
        epg.add_infradomain(domain)
        epg.set_dom_resolution_immediacy('immediate')
        output = str(tenant.get_json())
        self.assertTrue("'resImedcy': 'immediate'" in output)

    def test_add_static_leaf_binding(self):
        tenant, app, epg = self.create_epg()
        epg.add_static_leaf_binding('101', 'vlan', '5', 'untagged', 'immediate', '1')

    def test_add_static_leaf_binding_bad_immediacy(self):
        tenant, app, epg = self.create_epg()
        with self.assertRaises(ValueError):
            epg.add_static_leaf_binding('101', 'vlan', '5', 'untagged', 'bad', '1')

    def test_add_static_leaf_binding_bad_encap_type(self):
        tenant, app, epg = self.create_epg()
        with self.assertRaises(ValueError):
            epg.add_static_leaf_binding('101', 'bad', '5', 'untagged', 'immediate', '1')

    def test_add_static_leaf_binding_bad_encap_mode(self):
        tenant, app, epg = self.create_epg()
        with self.assertRaises(ValueError):
            epg.add_static_leaf_binding('101', 'vlan', '5', 'bad', 'immediate', '1')

    def test_add_static_leaf_binding_get_json(self):
        tenant, app, epg = self.create_epg()
        epg.add_static_leaf_binding('101', 'vlan', '5', 'untagged', 'immediate', '1')
        self.assertIn('fvRsNodeAtt', str(tenant.get_json()))


class TestOutsideEPG(unittest.TestCase):
    """
    Test OutsideEPG class
    """
    def test_create(self):
        """
        Test basic OutsideEPG creation
        """
        tenant = Tenant('cisco')
        outside_epg = OutsideEPG('internet', tenant)
        self.assertTrue(isinstance(outside_epg, OutsideEPG))

    def test_invalid_create(self):
        """
        Test invalid OutsideEPG creation
        """
        self.assertRaises(TypeError, OutsideEPG, 'internet', 'cisco')

    def test_basic_json(self):
        """
        Test OutsideEPG JSON creation
        """
        tenant = Tenant('cisco')
        outside_l3 = OutsideL3('internet', tenant)
        self.assertTrue('l3extOut' in str(outside_l3.get_json()))


class TestAnyEPG(unittest.TestCase):
    """
    Test AnyEPG class
    """
    def test_create(self):
        """
        Test basic AnyEPG creation
        """
        context = Context('cisco-ctx')
        any_epg = AnyEPG('internet', context)
        self.assertTrue(isinstance(any_epg, AnyEPG))
        self.assertEqual(any_epg.get_parent(), context)

    def test_invalid_create(self):
        """
        Test invalid AnyEPG creation
        """
        self.assertRaises(TypeError, AnyEPG, 'internet', 'cisco')

    def test_basic_json(self):
        """
        Test AnyEPG JSON creation
        """
        context = Context('cisco-ctx')
        any_epg = AnyEPG('internet', context)
        self.assertTrue('vzAny' in str(any_epg.get_json()))

    def test_provide_contract(self):
        """
        Test that AnyEPG can provide a contract
        :return:
        """
        context = Context('cisco-ctx')
        any_epg = AnyEPG('any', context)
        contract = Contract('contract-1')
        any_epg.provide(contract)
        contracts = any_epg.get_all_provided()
        self.assertTrue(len(contracts), 1)
        self.assertEqual(contracts[0], contract)
        json = any_epg.get_json()
        self.assertEqual(json['vzAny']['attributes']['name'], 'any')
        for child in json['vzAny']['children']:
            self.assertTrue('vzRsAnyToProv' in child)
            self.assertTrue(child['vzRsAnyToProv']['attributes']['tnVzBrCPName'] == 'contract-1')

    def test_consume_contract(self):
        """
        Test that AnyEPG can provide a contract
        :return:
        """
        context = Context('cisco-ctx')
        any_epg = AnyEPG('any', context)
        contract = Contract('contract-1')
        any_epg.consume(contract)
        contracts = any_epg.get_all_consumed()
        self.assertTrue(len(contracts), 1)
        self.assertEqual(contracts[0], contract)
        json = any_epg.get_json()
        self.assertEqual(json['vzAny']['attributes']['name'], 'any')
        for child in json['vzAny']['children']:
            self.assertTrue('vzRsAnyToCons' in child)
            self.assertTrue(child['vzRsAnyToCons']['attributes']['tnVzBrCPName'] == 'contract-1')


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
                children_checked += 1
            if 'fvStCEp' in child:
                ep_child = child['fvStCEp']['children'][0]
                ep_attributes = child['fvStCEp']['attributes']
                ep_name = ep_attributes['name']
                if deleted:
                    status = ep_attributes['status']
                    self.assertTrue(status == 'deleted')
                self.assertTrue(ep_name == mac)
                children_checked += 1
                self.assertTrue('fvRsStCEpToPathEp' in ep_child or 'fvStIp' in ep_child)
                if 'fvRsStCEpToPathEp' in ep_child:
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

    def test_create_bad_parent(self):
        """
        checks to see that creating an endpoint in something
        other an EPG causes an error.
        """
        self.assertRaises(TypeError, Endpoint,
                          '00-11-22-33-44-55', 'not an epg')

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


class TestPhysDomain(unittest.TestCase):
    """
    Class for testing Phys Domain
    """
    def test_create(self):
        """
        Test create phys domain
        """
        phys_domain = PhysDomain('test_phys_domain', None)
        self.assertTrue(isinstance(phys_domain, PhysDomain))

    def test_json(self):
        """
        Test get json of phys domain
        """
        phys_domain = PhysDomain('test_phys_domain', None)
        self.assertTrue(type(phys_domain.get_json()) is dict)

    def test_generate_attributes_conditionals(self):
        """
        Test conditionals within generate attributes function
        """
        phys_domain = PhysDomain('test_phys_domain', None)
        phys_domain.dn = 'dn'
        phys_domain.lcOwn = 'lcOwn'
        phys_domain.childAction = 'childAction'
        self.assertEqual(phys_domain._generate_attributes()['dn'], phys_domain.dn)
        self.assertEqual(phys_domain._generate_attributes()['lcOwn'], phys_domain.lcOwn)
        self.assertEqual(phys_domain._generate_attributes()['childAction'], phys_domain.childAction)

    def test_get_parent(self):
        """
        Test get parent function
        """
        phys_domain = PhysDomain('test-phys-domain', None)
        self.assertEqual(phys_domain.get_parent(), phys_domain._parent)


class TestJson(unittest.TestCase):
    """
    Class for testing JSON creation
    """
    def test_simple_3tier_app(self):
        """
        Test a simple 3-tier app example
        """
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
        """
        Test attaching an EPG to a L2Interface
        """
        expected_json = ('{"fvTenant": {"attributes": {"name": "cisco"}, "child'
                         'ren": [{"fvAp": {"attributes": {"name": "ordersystem"'
                         '}, "children": [{"fvAEPg": {"attributes": {"name": "w'
                         'eb"}, "children": [{"fvRsPathAtt": {"attributes": {"e'
                         'ncap": "vlan-5", "tDn": "topology/pod-1/paths-1/pathe'
                         'p-[eth1/1]"}}}, {"fvRsDomAtt": {"attributes": {"tDn":'
                         ' "uni/phys-allvlans"}}}]}}]}}]}}')
        expected_json = str(expected_json)
        tenant = Tenant('cisco')
        app = AppProfile('ordersystem', tenant)
        web_epg = EPG('web', app)
        intf = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(intf)
        web_epg.attach(vlan_intf)
        output = json.dumps(tenant.get_json(), sort_keys=True)

        self.assertTrue(output == expected_json,
                        'Did not see expected JSON returned')


class TestEPGDomain(unittest.TestCase):
    """
    Test the EPG Domain class
    """
    def test_get_parent_class(self):
        """
        Test _get_parent_class
        """
        epg_domain = EPGDomain('test_epg_domain', None)
        self.assertIsNone(epg_domain._get_parent_class())

    def test_get_parent(self):
        """
        Test get_parent
        """
        epg_domain = EPGDomain('test_epg_domain', None)
        self.assertEqual(epg_domain.get_parent(), epg_domain._parent)

    def test_get_json(self):
        """
        Test get_json
        """
        epg_domain = EPGDomain('test_epg_domain', None)
        self.assertTrue(type(epg_domain.get_json()) is dict)


class TestAttributeCriterion(unittest.TestCase):
    """
    Test the AttributeCriterion class
    """
    @staticmethod
    def make_valid_criteria():
        tenant = Tenant('test')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        return AttributeCriterion('attr', epg)

    def test_create(self):
        criterion = self.make_valid_criteria()
        self.assertEqual(criterion.match, 'any')

    def test_create_with_bad_parent(self):
        tenant = Tenant('test')
        self.assertRaises(TypeError, AttributeCriterion, 'attr', tenant)

    def test_set_match(self):
        criterion = self.make_valid_criteria()
        self.assertEqual(criterion.match, 'any')
        criterion.match = 'all'
        self.assertEqual(criterion.match, 'all')

    def test_set_bad_match(self):
        criterion = self.make_valid_criteria()
        self.assertEqual(criterion.match, 'any')
        criterion.match = 'all'
        with self.assertRaises(AssertionError):
            criterion.match = 'bad'
        self.assertEqual(criterion.match, 'all')

    def test_get_json(self):
        tenant = Tenant('test')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        criterion = AttributeCriterion('attr', epg)

        expected_json = {
            'fvTenant': {
                'attributes': {
                    'name': 'test'
                }, 'children': [
                    {
                        'fvAp': {
                            'attributes': {
                                'name': 'app'
                            },
                            'children': [
                                {
                                    'fvAEPg': {
                                        'attributes': {'isAttrBasedEPg': 'yes', 'name': 'epg'},
                                        'children': [
                                            {
                                                'fvCrtrn':
                                                    {
                                                        'attributes': {'name': 'attr', 'match': 'any'},
                                                        'children': []
                                                    }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.assertEqual(tenant.get_json(), expected_json)

    def test_is_attribute_based(self):
        criterion = self.make_valid_criteria()
        epg = criterion.get_parent()
        self.assertEqual(epg.__class__, EPG)
        self.assertTrue(epg.is_attributed_based)

    def test_single_ip_based_attribute(self):
        tenant = Tenant('test')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        criterion = AttributeCriterion('attr', epg)
        criterion.add_ip_address('1.2.3.4')

        expected_json = {
            'fvTenant': {
                'attributes': {'name': 'test'},
                'children': [
                    {
                        'fvAp': {
                            'attributes': {'name': 'app'},
                            'children': [
                                {
                                    'fvAEPg': {
                                        'attributes': {'isAttrBasedEPg': 'yes', 'name': 'epg'},
                                        'children': [
                                            {
                                                'fvCrtrn': {
                                                    'attributes': {'name': 'attr', 'match': 'any'},
                                                    'children': [
                                                        {
                                                            'fvIpAttr': {
                                                                'attributes': {'ip': '1.2.3.4', 'name': '1.2.3.4'},
                                                                'children': []
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.assertEqual(tenant.get_json(), expected_json)

    def test_multiple_ip_based_attribute(self):
        tenant = Tenant('test')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        criterion = AttributeCriterion('attr', epg)
        criterion.add_ip_address('1.2.3.4')
        criterion.add_ip_address('1.2.3.5')

        expected_json = {
            'fvTenant': {
                'attributes': {'name': 'test'},
                'children': [
                    {
                        'fvAp': {
                            'attributes': {'name': 'app'},
                            'children': [
                                {
                                    'fvAEPg': {
                                        'attributes': {'isAttrBasedEPg': 'yes', 'name': 'epg'},
                                        'children': [
                                            {
                                                'fvCrtrn': {
                                                    'attributes': {'name': 'attr', 'match': 'any'},
                                                    'children': [
                                                        {
                                                            'fvIpAttr': {
                                                                'attributes': {'ip': '1.2.3.4', 'name': '1.2.3.4'},
                                                                'children': []
                                                            }
                                                        },
                                                        {
                                                            'fvIpAttr': {
                                                                'attributes': {'ip': '1.2.3.5', 'name': '1.2.3.5'},
                                                                'children': []
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.assertEqual(tenant.get_json(), expected_json)


class TestOutsideL2(unittest.TestCase):
    """
    Test the OutsideL2 class
    """
    def test_create(self):
        tenant = Tenant('test')
        outside_l2 = OutsideL2('l2out', tenant)
        self.assertEqual(outside_l2.bd_name, None)

    def test_create_bad_parent(self):
        tenant = Tenant('test')
        app = AppProfile('app', tenant)
        with self.assertRaises(TypeError):
            outside_l2 = OutsideL2('l2out', app)

    def test_has_bd(self):
        tenant = Tenant('test')
        bd = BridgeDomain('bd', tenant)
        outside_l2 = OutsideL2('l2out', tenant)
        self.assertFalse(outside_l2.has_bd())
        outside_l2.add_bd(bd)
        self.assertTrue(outside_l2.has_bd())

    def test_add_bad_bd(self):
        tenant = Tenant('test')
        bd = Context('bd', tenant)
        outside_l2 = OutsideL2('l2out', tenant)
        with self.assertRaises(AssertionError):
            outside_l2.add_bd(bd)
        self.assertFalse(outside_l2.has_bd())

    def test_remove_bd(self):
        tenant = Tenant('test')
        bd = BridgeDomain('bd', tenant)
        outside_l2 = OutsideL2('l2out', tenant)
        self.assertFalse(outside_l2.has_bd())
        outside_l2.add_bd(bd)
        self.assertTrue(outside_l2.has_bd())
        outside_l2.remove_bd()
        self.assertFalse(outside_l2.has_bd())

    def test_get_json(self):
        tenant = Tenant('test')
        bd = BridgeDomain('bd', tenant)
        outside_l2 = OutsideL2('l2out', tenant)
        outside_l2.add_bd(bd)

        expected_json = {
            'fvTenant': {
                'attributes': {'name': 'test'},
                'children': [
                    {
                        'fvBD': {
                            'attributes': {
                                'name': 'bd',
                                'unkMacUcastAct': 'proxy',
                                'arpFlood': 'no',
                                'multiDstPktAct': 'bd-flood',
                                'unicastRoute': 'yes',
                                'unkMcastAct': 'flood'
                            },
                            'children': []
                        }
                    },
                    {
                        'l2extOut': {
                            'attributes': {'name': 'l2out'},
                            'children': [
                                {
                                    'l2extRsEctx': {'attributes': {'tnFvBDName': 'bd'}}
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.assertEqual(expected_json, tenant.get_json())


class TestOutsideL2EPG(unittest.TestCase):
    """
    Test the OutsideL2EPG class
    """
    def test_create(self):
        tenant = Tenant('test')
        outside_l2 = OutsideL2('l2out', tenant)
        outside_l2_epg = OutsideL2EPG('l2outepg', outside_l2)
        self.assertEqual(outside_l2_epg.name, 'l2outepg')

    def test_get_json(self):
        tenant = Tenant('test')
        outside_l2 = OutsideL2('l2out', tenant)
        outside_l2_epg = OutsideL2EPG('l2outepg', outside_l2)
        tenant_json = tenant.get_json()
        expected_json = {
            'fvTenant': {
                'attributes': {
                    'name': 'test'
                },
                'children': [
                    {
                        'l2extOut': {
                            'attributes': {
                                'name': 'l2out'
                            },
                            'children': [
                                {
                                    'l2extInstP': {
                                        'attributes': {
                                            'name': 'l2outepg'
                                        },
                                        'children': []
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.assertEqual(tenant_json, expected_json)


class TestPortChannel(unittest.TestCase):
    """
    Test the PortChannel class
    """
    def create_pc(self):
        """
        Create a basic PortChannel used as setup for test cases
        """
        if1 = Interface('eth', '1', '101', '1', '8')
        if2 = Interface('eth', '1', '101', '1', '9')
        pc = PortChannel('pc1')
        pc.attach(if1)
        pc.attach(if2)
        return pc

    def test_create_pc(self):
        """
        Test creating a PortChannel
        """
        pc = self.create_pc()
        self.assertTrue(pc.is_interface())
        self.assertFalse(pc.is_vpc())
        fabric, infra = pc.get_json()

        expected_resp = json.loads('{"infraInfra": {"attributes": {}, "children": [{"infraNodeP": {"attrib'
                                   'utes": {"name": "1-101-1-8"}, "children": [{"infraLe'
                                   'afS": {"attributes": {"type": "range", "name": "1-10'
                                   '1-1-8"}, "children": [{"infraNodeBlk": {"attributes"'
                                   ': {"from_": "101", "name": "1-101-1-8", "to_": "101"'
                                   '}, "children": []}}]}}, {"infraRsAccPortP": {"attrib'
                                   'utes": {"tDn": "uni/infra/accportprof-1-101-1-8"}, "'
                                   'children": []}}]}}, {"infraAccPortP": {"attributes":'
                                   ' {"name": "1-101-1-8"}, "children": [{"infraHPortS":'
                                   ' {"attributes": {"type": "range", "name": "1-101-1-8'
                                   '"}, "children": [{"infraPortBlk": {"attributes": {"t'
                                   'oPort": "8", "fromPort": "8", "fromCard": "1", "name'
                                   '": "1-101-1-8", "toCard": "1"}, "children": []}}, {"'
                                   'infraRsAccBaseGrp": {"attributes": {"tDn": "uni/infr'
                                   'a/funcprof/accbundle-pc1"}, "children": []}}]}}]}}, '
                                   '{"infraNodeP": {"attributes": {"name": "1-101-1-9"},'
                                   ' "children": [{"infraLeafS": {"attributes": {"type":'
                                   ' "range", "name": "1-101-1-9"}, "children": [{"infra'
                                   'NodeBlk": {"attributes": {"from_": "101", "name": "1'
                                   '-101-1-9", "to_": "101"}, "children": []}}]}}, {"inf'
                                   'raRsAccPortP": {"attributes": {"tDn": "uni/infra/acc'
                                   'portprof-1-101-1-9"}, "children": []}}]}}, {"infraAc'
                                   'cPortP": {"attributes": {"name": "1-101-1-9"}, "chil'
                                   'dren": [{"infraHPortS": {"attributes": {"type": "ran'
                                   'ge", "name": "1-101-1-9"}, "children": [{"infraPortB'
                                   'lk": {"attributes": {"toPort": "9", "fromPort": "9",'
                                   ' "fromCard": "1", "name": "1-101-1-9", "toCard": "1"'
                                   '}, "children": []}}, {"infraRsAccBaseGrp": {"attribu'
                                   'tes": {"tDn": "uni/infra/funcprof/accbundle-pc1"}, "'
                                   'children": []}}]}}]}}, {"infraFuncP": {"attributes":'
                                   ' {}, "children": [{"infraAccBndlGrp": {"attributes":'
                                   ' {"lagT": "link", "name": "pc1"}, "children": []}}]}'
                                   '}]}}')

        # TODO: Temporarily disable check in Python3 environments
        if sys.version_info < (3, 0, 0):
            self.assertEqual(infra, expected_resp)

        # Not a VPC, so fabric should be None
        self.assertIsNone(fabric)

    def test_create_3rd_interface_as_vpc(self):
        """
        Test creating a VPC
        """
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
        """
        Test _get_nodes class
        """
        pc = self.create_pc()
        nodes = pc._get_nodes()

    def test_delete_vpc(self):
        """
        Test deleting VPC
        """
        pc = self.create_pc()
        pc.mark_as_deleted()
        fabric, infra = pc.get_json()
        fabric_url, infra_url = pc.get_url()


class TestTunnelInterface(unittest.TestCase):
    """
    Test TunnelInterface class
    """
    def test_create(self):
        """
        Basic create test
        """
        tunnel = TunnelInterface('eth', '1', '1', '1')
        self.assertTrue(isinstance(tunnel, TunnelInterface))


class TestFexInterface(unittest.TestCase):
    """
    Test FexInterface class
    """
    def test_create(self):
        """
        Basic create test
        """
        fex = FexInterface('eth', '1', '1', '1', '1', '1')
        self.assertTrue(isinstance(fex, FexInterface))


class TestAcitoolkitGraphBuilder(unittest.TestCase):
    """
    Test AcitoolkitGraphBuilder class
    """
    def test_create(self):
        graphs = AcitoolkitGraphBuilder()
        graphs.build_graphs()
        expected_files = ['acitoolkit-hierarchy.Fabric.gv',
                          'acitoolkit-hierarchy.Fabric.tmp.gv',
                          'acitoolkit-hierarchy.Fabric.tmp.gv.pdf',
                          'acitoolkit-hierarchy.LogicalModel.gv',
                          'acitoolkit-hierarchy.LogicalModel.tmp.gv',
                          'acitoolkit-hierarchy.LogicalModel.tmp.gv.pdf',
                          'acitoolkit-hierarchy.PhysicalModel.gv',
                          'acitoolkit-hierarchy.PhysicalModel.tmp.gv',
                          'acitoolkit-hierarchy.PhysicalModel.tmp.gv.pdf']
        for expected_file in expected_files:
            self.assertTrue(os.path.isfile(expected_file))
            os.remove(expected_file)


class TestOutsideNetwork(unittest.TestCase):
    """
    Test OutsideNetwork class
    """
    def test_get_json(self):
        """
        Test JSON creation for a OutsideNetwork
        """
        tenant = Tenant('cisco')
        out_net = OutsideNetwork('OutsideNetwork', tenant)
        out_net.set_addr('0.0.0.0/0')
        out_net_json = out_net.get_json()
        self.assertTrue('l3extSubnet' in out_net_json)

    def test_get_json_without_ip(self):
        """
        Test JSON creation for a OutsideNetwork without an IP
        This should raise an error
        """
        tenant = Tenant('cisco')
        out_net = OutsideNetwork('OutsideNetwork', tenant)
        with self.assertRaises(ValueError):
            out_net.get_json()

    def test_get_parent_class(self):
        """
        Test _get_parent_class method
        """
        self.assertEqual(OutsideNetwork._get_parent_class(), OutsideEPG)

    def test_get_name_dn_delimiters(self):
        """
        Test _get_name_dn_delimiters method
        """
        self.assertEqual(OutsideNetwork._get_name_dn_delimiters(),
                         ['/extsubnet-[', '/'])

    def test_set_scope(self):
        """
        Test the set_scope method
        """
        tenant = Tenant('cisco')
        out_net = OutsideNetwork('OutsideNetwork', tenant)
        out_net.set_addr('0.0.0.0/0')
        valid_scopes = ['import-rtctrl', 'export-rtctrl', 'import-security',
                        'shared-security', 'shared-rtctrl']
        for scope in valid_scopes:
            out_net.set_scope(scope)
        bad_scope = 'bad-scope'
        self.assertRaises(ValueError, out_net.set_scope, bad_scope)

    def test_set_scope_to_none(self):
        """
        Test the set_scope with None
        """
        tenant = Tenant('cisco')
        out_net = OutsideNetwork('OutsideNetwork', tenant)
        self.assertRaises(TypeError, out_net.set_scope, None)

    def test_get_json_detail(self):
        """
        Make sure that the json is correct
        """
        ip_add = '0.0.0.0/0'
        out_net_name = 'OutsideNetwork'
        tenant = Tenant('cisco')
        out_net = OutsideNetwork(out_net_name, tenant)
        out_net.set_addr(ip_add)
        out_net_json = out_net.get_json()
        self.assertEqual(ip_add,
                         out_net_json['l3extSubnet']['attributes']['ip'])
        self.assertEqual(out_net_name,
                         out_net_json['l3extSubnet']['attributes']['name'])

    def test_get_json_detail_set_scope(self):
        """
        Make sure that the json is correct when a scope is set
        """
        ip_add = '0.0.0.0/0'
        out_net_name = 'OutsideNetwork'
        tenant = Tenant('cisco')
        out_net = OutsideNetwork(out_net_name, tenant)
        out_net.set_addr(ip_add)
        valid_scopes = ['import-rtctrl', 'export-rtctrl', 'import-security',
                        'shared-security', 'shared-rtctrl']
        for scope in valid_scopes:
            out_net.set_scope(scope)
            out_net_json = out_net.get_json()
            self.assertEqual(scope,
                             out_net_json['l3extSubnet']['attributes']['scope'])


class TestContext(unittest.TestCase):
    """
    Test Context class
    """
    def test_get_json(self):
        """
        Test JSON creation for a Context
        """
        tenant = Tenant('cisco')
        context = Context('ctx-cisco', tenant)
        context_json = context.get_json()
        self.assertTrue('fvCtx' in context_json)

    def test_get_parent_class(self):
        """
        Test _get_parent_class method
        """
        self.assertEqual(Context._get_parent_class(), Tenant)

    def test_get_parent_dn(self):
        """
        Test _get_parent_dn method
        """
        dn = 'uni/tn-tenant/ctx-test'
        self.assertEqual(Context._get_parent_dn(dn), 'uni/tn-tenant')

    def test_get_name_from_dn(self):
        """
        Test _get_name_from_dn method
        """
        dn = 'uni/tn-tenant/ctx-test'
        self.assertEqual(Context._get_name_from_dn(dn), 'test')

    def test_set_allow_all(self):
        """
        Test set_allow_all method
        """
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
    """
    Test BGPSession class
    """
    def test_bgp_router(self):
        """
        Test basic BGPSession creation
        """
        tenant = Tenant('bgp-tenant')
        context = Context('bgp-test', tenant)
        l3out = OutsideL3('out-1', tenant)
        outside = OutsideEPG('out-epg-1', l3out)
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
        self.assertTrue(bgpif.is_interface())
        self.assertTrue(bgpif.is_bgp())
        contract1 = Contract('icmp')
        outside.provide(contract1)
        l3out.add_context(context)
        outside.consume(contract1)
        outside.attach(bgpif)
        bgp_json = outside.get_json()


class TestOspf(unittest.TestCase):
    """
    Test OSPFInterface class
    """
    def test_ospf_router_port(self):
        """
        Test basic OSPFInterface creation
        """
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
        rtr.set_router_id('1')
        rtr.set_node_id('1')
        self.assertEqual(rtr.get_router_id(), '1')
        self.assertEqual(rtr.get_node_id(), '1')
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
        self.assertTrue(ospfif.is_ospf())
        ospf_json = outside.get_json()

    def test_area_type(self):
        """
        Test changing area_type
        """
        rtr = OSPFRouter('rtr-1')
        ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='2')
        for area_type_setting in ['nssa', 'stub', 'regular']:
            ospfif.set_area_type(area_type_setting)
            self.assertEqual(ospfif.area_type, area_type_setting)

    def test_invalid_area_type(self):
        """
        Test changing area_type to an invalid value
        """
        rtr = OSPFRouter('rtr-1')
        ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='2')
        with self.assertRaises(ValueError):
            ospfif.set_area_type('bad-value')
        self.assertNotEqual(ospfif.area_type, 'bad-value')


class TestMonitorPolicy(unittest.TestCase):
    """
    Tests the monitoring policy
    """

    def test_create(self):
        """
        Test basic MonitorPolicy creation
        """
        m_policy = MonitorPolicy('fabric', 'policy-name')
        self.assertEqual(m_policy.name, 'policy-name')
        self.assertEqual(m_policy.policyType, 'fabric')
        m_policy.set_name('policy-name-2')
        self.assertEqual(m_policy.name, 'policy-name-2')
        m_policy.set_description('Policy description string')
        self.assertEqual(m_policy.description, 'Policy description string')


class TestLiveAPIC(unittest.TestCase):
    """
    Test with a live APIC
    """
    def login_to_apic(self):
        """Login to the APIC
           RETURNS:  Instance of class Session
        """
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)
        return session


class TestLiveCertAuth(TestLiveAPIC):
    """
    Certificate auth tests with a live APIC
    """
    def login_to_apic(self):
        """Login to the APIC using Certificate auth
           RETURNS:  Instance of class Session
        """
        session = Session(URL, LOGIN, cert_name=CERT_NAME, key=KEY, subscription_enabled=False)
        return session

    @unittest.skipUnless('KEY' in globals() and os.path.isfile(KEY), 'Key file does not exist.')
    def test_get_tenants(self):
        """
        Test that cert auth can get Tenants
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)

    @unittest.skipUnless('KEY' in globals() and os.path.isfile(KEY), 'Key file does not exist.')
    def test_get_with_params(self):
        """
        Test that URL encoded parameters do not break cert auth
        """
        session = self.login_to_apic()
        tenants = Tenant.get_deep(
            session,
            names=['mgmt', 'common'],
            limit_to=['fvTenant', 'fvAp']
        )
        self.assertTrue(len(tenants) > 0)


class TestLiveAppcenterSubscription(unittest.TestCase):
    """
    Certificate subscription tests with a live APIC
    Note, this test requires appcenter user credentials and valid appcenter user private key
    """

    def login_to_apic(self):
        """Login to the APIC using Certificate auth with appcenter_user enabled
           RETURNS:  Instance of class Session
        """
        session = Session(URL, APPCENTER_LOGIN, cert_name=APPCENTER_CERT_NAME,
                          key=APPCENTER_KEY, subscription_enabled=True, appcenter_user=True)
        resp = session.login()
        self.assertTrue(resp.ok)
        return session

    @unittest.skipIf('APPCENTER_LOGIN' not in vars(), 'APPCENTER credentials not given.')
    def test_get_actual_event(self):
        """
        Test get_event for certificate based subscription
        """
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
        Tenant.unsubscribe(session)


class TestLiveSession(unittest.TestCase):
    """
    Tests for the Session class
    """
    def test_bad_password(self):
        session = Session(URL, LOGIN, 'badpassword')
        resp = session.login()
        self.assertFalse(resp.ok)

    def test_refresh_login(self):
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)
        resp = session.refresh_login()
        self.assertTrue(resp.ok)

    def test_close(self):
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)
        self.assertTrue(session.logged_in())
        session.close()
        self.assertFalse(session.logged_in())


class TestLiveTenant(TestLiveAPIC):
    """
    Tenant tests on a live APIC
    """
    def create_unique_live_tenant(self):
        """
        Creates test tenant that does not interfere with tenants in APIC
        """
        session = self.login_to_apic()
        tenants = self.get_all_tenants()
        non_existing_tenant = tenants[0]
        while non_existing_tenant in tenants:
            non_existing_tenant = Tenant(random_size_string())
        return non_existing_tenant

    def get_all_tenants(self):
        """
        Test Tenant.get
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)
        return tenants

    def get_all_tenant_names(self):
        """
        Test getting Tenant names
        """
        tenants = self.get_all_tenants()
        names = []
        for tenant in tenants:
            names.append(tenant.name)
        return names

    def test_get_tenants(self):
        """
        Test getting tenants
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))
            self.assertTrue(isinstance(tenant.name, str))

    def test_get_tenants_with_parent(self):
        """
        Test getting tenants with a parent object
        """
        session = self.login_to_apic()
        logical_model = LogicalModel()
        tenants = Tenant.get(session, parent=logical_model)
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))
            self.assertTrue(isinstance(tenant.name, str))
            self.assertEqual(tenant.get_parent(), logical_model)

    def test_get_deep_tenants(self):
        """
        Test Tenant.get_deep
        """
        session = self.login_to_apic()
        tenants = Tenant.get_deep(session)
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))
            self.assertTrue(isinstance(tenant.name, str))

    def test_get_deep_tenants_invalid_names(self):
        """
        Test Tenant.get_deep
        """
        session = self.login_to_apic()
        self.assertRaises(TypeError, Tenant.get_deep, session, names=[4, 5])

    def test_get_deep_tenants_limit_to_as_string(self):
        """
        Test Tenant.get_deep
        """
        session = self.login_to_apic()
        self.assertRaises(TypeError, Tenant.get_deep, session, limit_to='fvTenant')

    def test_get_deep_tenants_config_only(self):
        """
        Test Tenant.get_deep
        """
        session = self.login_to_apic()
        tenants = Tenant.get_deep(session, limit_to=['fvTenant'], config_only=True)
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))

    def test_get_deep_tenants_limit_to_multiple(self):
        """
        Test Tenant.get_deep
        """
        session = self.login_to_apic()
        tenants = Tenant.get_deep(session, limit_to=['fvTenant', 'fvBD'])
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))

    def test_get_deep_tenants_limit_to_multiple_as_set(self):
        """
        Test Tenant.get_deep
        """
        session = self.login_to_apic()
        tenants = Tenant.get_deep(session, limit_to=('fvTenant', 'fvBD'))
        self.assertTrue(len(tenants) > 0)
        for tenant in tenants:
            self.assertTrue(isinstance(tenant, Tenant))

    def test_exists_tenant(self):
        """
        Test exists method with valid tenant
        """
        session = self.login_to_apic()
        tenants = self.get_all_tenants()
        for tenant in tenants:
            self.assertTrue(Tenant.exists(session, tenant))

    def test_no_exists_tenant(self):
        """
        Test exists method with invalid tenant
        """
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
        """
        Test basic tenant creation
        """
        session = self.login_to_apic()

        # Create the tenant and push to APIC
        new_tenant = self.create_unique_live_tenant()
        resp = session.push_to_apic(new_tenant.get_url(),
                                    data=new_tenant.get_json())
        self.assertTrue(resp.ok)

        # Get all of the tenants and verify that the new tenant is present
        names = self.get_all_tenant_names()
        self.assertTrue(new_tenant.name in names)

        # Now delete the tenant
        new_tenant.mark_as_deleted()
        new_tenant.push_to_apic(session)
        self.assertTrue(new_tenant.push_to_apic(session).ok)

        # Get all of the tenants and verify that the new tenant is deleted
        names = self.get_all_tenant_names()
        self.assertTrue(new_tenant.name not in names)


class TestLiveSubscription(TestLiveAPIC):
    """
    Test Subscriptions
    """
    def test_create_class_subscription(self):
        """
        Test class subscription creation
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        Tenant.subscribe(session)
        if len(tenants):
            self.assertTrue(Tenant.has_events(session))
        else:
            self.assertFalse(Tenant.has_events(session))
        Tenant.unsubscribe(session)

    def test_is_subscribed(self):
        """
        Test is_subscribed function
        """
        session = self.login_to_apic()
        url = Tenant._get_subscription_urls()[0]
        self.assertFalse(session.is_subscribed(url))
        session.subscribe(url)
        self.assertTrue(session.is_subscribed(url))
        session.unsubscribe(url)

    def test_get_event_count(self):
        """
        Test get_event_count function
        """
        session = self.login_to_apic()
        url = Tenant._get_subscription_urls()[0]
        self.assertFalse(session.get_event_count(url))
        session.subscribe(url)
        self.assertTrue(session.get_event_count(url))
        session.unsubscribe(url)

    def test_delete_unsubscribed_class_subscription(self):
        """
        Test deleting a class subscription that has not been subscribed
        """
        session = self.login_to_apic()
        Tenant.unsubscribe(session)
        self.assertFalse(Tenant.has_events(session))

    def test_double_class_subscription(self):
        """
        Test issuing a class subscription twice
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        Tenant.subscribe(session)
        Tenant.subscribe(session)
        if len(tenants):
            self.assertTrue(Tenant.has_events(session))
        else:
            self.assertFalse(Tenant.has_events(session))
        Tenant.unsubscribe(session)

    def test_get_event_no_subcribe(self):
        """
        Test get_event with no subscription
        """
        session = self.login_to_apic()
        self.assertFalse(Tenant.has_events(session))
        self.assertIsNone(Tenant.get_event(session))
        url = Tenant._get_subscription_urls()[0]
        self.assertFalse(session.is_subscribed(url))
        with self.assertRaises(ValueError):
            session.get_event(url)


    def test_get_actual_event(self):
        """
        Test get_event
        """
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
        """
        Test resubscription
        """
        session = self.login_to_apic()
        Tenant.subscribe(session)

        # Test the refresh used for subscription timeout
        session.subscription_thread.refresh_subscriptions()

        # Test the resubscribe used after re-login on login timeout
        session.resubscribe()


class TestLiveInterface(TestLiveAPIC):
    def get_valid_interface(self, session):
        interfaces = Interface.get(session)
        if len(interfaces):
            return interfaces[0]
        else:
            return None

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
            self.assertTrue(isinstance(interface, Interface) or isinstance(interface, FexInterface))
            interface_as_a_string = str(interface)
            self.assertTrue(isinstance(interface_as_a_string, str))
            path = interface._get_path()
            self.assertTrue(isinstance(path, str))

    def test_get(self):
        session = self.login_to_apic()
        interface = self.get_valid_interface(session)
        assert interface is not None
        pod = interface.pod
        node = interface.node
        slot = interface.module
        port = interface.port
        self.assertRaises(TypeError, Interface.get, session,
                          pod, node, slot, 33)
        self.assertRaises(TypeError, Interface.get, session,
                          pod, node, 1, port)
        self.assertRaises(TypeError, Interface.get, session,
                          pod, 101, slot, port)
        self.assertRaises(TypeError, Interface.get, session,
                          1, node, slot, port)
        interface_again = Interface.get(session, pod, node, slot, port)[0]
        self.assertTrue(interface == interface_again)

        self.assertRaises(TypeError, Interface.get, session, pod)
        pod = Linecard(pod, node, slot)
        interfaces = Interface.get(session, pod)
        self.assertTrue(len(interfaces) > 0)

    def test_get_adjacent(self):
        session = self.login_to_apic()
        interfaces = Interface.get(session)
        for interface in interfaces:
            if interface.porttype == 'fab' and interface.attributes['operSt'] == 'up':
                adj = interface.get_adjacent_port()
                if adj is not None:
                    fields = adj.split('/')
                    self.assertEqual(len(fields), 4)
                    for field in fields:
                        self.assertIsInstance(int(field), int)


class TestLivePortChannel(TestLiveAPIC):
    """
    Live tests for PortChannel class
    """
    def test_get_all_portchannels(self):
        """
        Test getting all of the portchannels
        """
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

    def test_get_table(self):
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        for tenant in tenants:
            apps = AppProfile.get(session, tenant)
            for app in apps:
                epgs = EPG.get(session, app, tenant)
                self.assertTrue(isinstance(EPG.get_table(epgs)[0], Table))


class TestLiveAnyEPG(TestLiveAPIC):
    def __init__(self, *args):
        self.session = None
        super(TestLiveAnyEPG, self).__init__(*args)

    def setUp(self):
        self.session = self.login_to_apic()
        tenant = Tenant('aci-toolkit-test')
        context = Context('ctx', tenant)
        any_epg = AnyEPG('anyepg', context)
        prov_contract = Contract('prov_contract', tenant)
        filt_entry = FilterEntry('provfilterentry', prov_contract)
        any_epg.provide(prov_contract)
        cons_contract = Contract('cons_contract', tenant)
        filt_entry = FilterEntry('consfilterentry', cons_contract)
        any_epg.consume(cons_contract)
        contract_intf = ContractInterface('contract_if', tenant)
        any_epg.consume_cif(contract_intf)

        resp = self.session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_get_any_epgs(self):
        tenants = Tenant.get(self.session)
        for tenant in tenants:
            contexts = Context.get(self.session, tenant)
            for context in contexts:
                any_epgs = AnyEPG.get(self.session, context, tenant)
                for any_epg in any_epgs:
                    self.assertTrue(isinstance(any_epg, AnyEPG))

    def check_get_deep(self):
        tenants = Tenant.get_deep(self.session, names=['aci-toolkit-test'])
        self.assertGreater(len(tenants), 0)
        contexts = tenants[0].get_children(only_class=Context)
        self.assertGreater(len(contexts), 0)
        any_epgs = contexts[0].get_children(only_class=AnyEPG)
        self.assertGreater(len(any_epgs), 0)

    def test_any_epg_get_deep(self):
        self.check_get_deep()

    def test_delete_contracts(self):
        tenant = Tenant('aci-toolkit-test')
        prov_contract = Contract('prov_contract', tenant)
        prov_contract.mark_as_deleted()
        cons_contract = Contract('cons_contract', tenant)
        cons_contract.mark_as_deleted()
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)
        self.check_get_deep()

    def test_delete_contract_relations(self):
        tenant = Tenant('aci-toolkit-test')
        context = Context('ctx', tenant)
        any_epg = AnyEPG('anyepg', context)
        prov_contract = Contract('prov_contract', tenant)
        any_epg.provide(prov_contract)
        any_epg.dont_provide(prov_contract)
        cons_contract = Contract('cons_contract', tenant)
        cons_contract.mark_as_deleted()
        any_epg.consume(cons_contract)
        any_epg.dont_consume(cons_contract)
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)
        self.check_get_deep()

    def test_delete_contract_interface_relation(self):
        tenant = Tenant('aci-toolkit-test')
        context = Context('ctx', tenant)
        any_epg = AnyEPG('anyepg', context)
        contract_intf = ContractInterface('contract_if', tenant)
        any_epg.consume_cif(contract_intf)
        any_epg.dont_consume_cif(contract_intf)
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)
        self.check_get_deep()

    def tearDown(self):
        if not self.session.logged_in():
            return
        tenant = Tenant('aci-toolkit-test')
        tenant.mark_as_deleted()
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)


class TestLiveAnyEPGWithTenantCommonContracts(TestLiveAPIC):
    def __init__(self, *args):
        self.session = None
        super(TestLiveAnyEPGWithTenantCommonContracts, self).__init__(*args)

    def setUp(self):
        self.session = self.login_to_apic()
        tenant = Tenant('common')
        prov_contract = Contract('aci-toolkit-test-prov_contract', tenant)
        filt_entry = FilterEntry('provfilterentry', prov_contract)
        cons_contract = Contract('aci-toolkit-test-cons_contract', tenant)
        filt_entry = FilterEntry('consfilterentry', cons_contract)
        contract_intf = ContractInterface('aci-toolkit-test-contract_if', tenant)
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)

        tenant = Tenant('aci-toolkit-test')
        context = Context('ctx', tenant)
        any_epg = AnyEPG('anyepg', context)
        any_epg.provide(prov_contract)
        any_epg.consume(cons_contract)
        any_epg.consume_cif(contract_intf)

        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)

    def test_get_any_epgs(self):
        tenants = Tenant.get(self.session)
        for tenant in tenants:
            contexts = Context.get(self.session, tenant)
            for context in contexts:
                any_epgs = AnyEPG.get(self.session, context, tenant)
                for any_epg in any_epgs:
                    self.assertTrue(isinstance(any_epg, AnyEPG))

    def check_get_deep(self):
        tenants = Tenant.get_deep(self.session, names=['aci-toolkit-test', 'common'])
        self.assertGreater(len(tenants), 0)
        contexts = tenants[0].get_children(only_class=Context)
        self.assertGreater(len(contexts), 0)
        any_epgs = contexts[0].get_children(only_class=AnyEPG)
        self.assertGreater(len(any_epgs), 0)

    def test_any_epg_get_deep(self):
        self.check_get_deep()

    def test_delete_contracts(self):
        tenant = Tenant('common')
        prov_contract = Contract('aci-toolkit-test-prov_contract', tenant)
        prov_contract.mark_as_deleted()
        cons_contract = Contract('aci-toolkit-test-cons_contract', tenant)
        cons_contract.mark_as_deleted()
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)
        self.check_get_deep()

    def tearDown(self):
        if not self.session.logged_in():
            return
        tenant = Tenant('aci-toolkit-test')
        tenant.mark_as_deleted()
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)

        tenant = Tenant('common')
        prov_contract = Contract('aci-toolkit-test-prov_contract', tenant)
        prov_contract.mark_as_deleted()
        cons_contract = Contract('aci-toolkit-test-cons_contract', tenant)
        cons_contract.mark_as_deleted()
        contract_intf = ContractInterface('aci-toolkit-test-contract_if', tenant)
        contract_intf.mark_as_deleted()
        resp = tenant.push_to_apic(self.session)
        self.assertTrue(resp.ok)


class TestLiveL2ExtDomain(TestLiveAPIC):
    """
    Test L2ExtDomain class
    """
    def test_get(self):
        session = self.login_to_apic()
        l2ext_domains = L2ExtDomain.get(session)
        for l2ext_domain in l2ext_domains:
            self.assertTrue(isinstance(l2ext_domain, L2ExtDomain))
        return l2ext_domains

    def test_get_by_name(self):
        session = self.login_to_apic()
        l2ext_domains = self.test_get()
        for l2ext_domain in l2ext_domains:
            self.assertEqual(L2ExtDomain.get_by_name(session, l2ext_domain.name), l2ext_domain)

    def test_generate_attributes(self):
        l2ext_domains = self.test_get()
        for l2ext_domain in l2ext_domains:
            if l2ext_domain.name:
                self.assertEqual(l2ext_domain._generate_attributes()['name'], l2ext_domain.name)
            if l2ext_domain.dn:
                self.assertEqual(l2ext_domain._generate_attributes()['dn'], l2ext_domain.dn)
            if l2ext_domain.lcOwn:
                self.assertEqual(l2ext_domain._generate_attributes()['lcOwn'], l2ext_domain.lcOwn)
            if l2ext_domain.childAction:
                self.assertEqual(l2ext_domain._generate_attributes()['childAction'], l2ext_domain.childAction)


class TestLiveL3ExtDomain(TestLiveAPIC):
    """
    Test L3ExtDomain class
    """
    def test_get(self):
        session = self.login_to_apic()
        l3ext_domains = L3ExtDomain.get(session)
        for l3ext_domain in l3ext_domains:
            self.assertTrue(isinstance(l3ext_domain, L3ExtDomain))

    def test_get_json(self):
        session = self.login_to_apic()
        l3ext_domains = L3ExtDomain.get(session)
        for l3ext_domain in l3ext_domains:
            l3ext_domain_json = l3ext_domain.get_json()
            self.assertTrue(type(l3ext_domain_json) is dict)


class TestLiveOutsideL3(TestLiveAPIC):
    """
    Test OutsideL3 class
    """
    def base_test_setup(self):
        session = self.login_to_apic()

        # Create the Tenant
        tenant = Tenant('aci-toolkit-test')
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Create the BridgeDomain
        bd = BridgeDomain('bd1', tenant)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Create the OutsideL3
        l3_out = OutsideL3('l3_out', tenant)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        return (session, tenant, bd, l3_out)

    def base_test_teardown(self, session, tenant):
        # Delete the tenant
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_attach_l3_out_to_bd(self):
        # Set up the tenant, bd, and l3_out
        (session, tenant, bd, l3_out) = self.base_test_setup()

        # Attach the OutsideL3 to the BridgeDomain
        bd.add_l3out(l3_out)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)
        self.assertTrue(bd.has_l3out)
        self.assertTrue(l3_out in bd.get_l3out())

        # Clean up
        self.base_test_teardown(session, tenant)

    def test_attach_l3_out_to_bd_and_retrive(self):
        # Set up the tenant, bd, and l3_out
        (session, tenant, bd, l3_out) = self.base_test_setup()

        # Attach the OutsideL3 to the BridgeDomain
        bd.add_l3out(l3_out)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)
        self.assertTrue(bd.has_l3out)
        self.assertTrue(l3_out in bd.get_l3out())

        # Retrive the configuration
        t = Tenant.get_deep(session, names=('aci-toolkit-test',))[0]
        bds_retrived = t.get_children(only_class=BridgeDomain)
        l3_outs = t.get_children(only_class=OutsideL3)

        # Make sure that the OutsideL3 are properly attached to the BDs
        for bd_retrived in bds_retrived:
            bd_retrived_attached_l3_outs = bd_retrived.get_l3out()
            for bd_retrived_attached_l3_out in bd_retrived_attached_l3_outs:
                self.assertTrue(bd_retrived_attached_l3_out in l3_outs)

        # Clean up
        self.base_test_teardown(session, tenant)


class TestLiveOutsideEPG(TestLiveAPIC):
    """
    Test OutsideEPG class
    """
    def base_test_setup(self):
        session = self.login_to_apic()

        # Create the Tenant
        tenant = Tenant('aci-toolkit-test')
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        # Create the OutsideL3
        l3_out = OutsideL3('l3_out', tenant)
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        # Create the OutsideEPG
        epg_out = OutsideEPG('epg_out')
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        return (session, tenant, epg_out, l3_out)

    def base_test_teardown(self, session, tenant):
        # Delete the tenant
        tenant.mark_as_deleted()
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

    def test_attach_outside_epg_to_outside_l3(self):
        # Set up the tenant, epg_out and l3_out
        (session, tenant, epg_out, l3_out) = self.base_test_setup()

        # Attach the OutsideEPG to the OutsideL3
        l3_out.add_child(epg_out)
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)
        self.assertTrue(epg_out in l3_out.get_children())

        # Retrive the configuration
        t = Tenant.get_deep(session, names=('aci-toolkit-test',))[0]
        l3_out_ret = t.get_children(only_class=OutsideL3)[0]

        # Make sure that the OutsideL3 has a OutsideEPG attached
        l3_out_childrens = l3_out_ret.get_children()
        self.assertTrue(l3_out_childrens)
        for l3_out_child in l3_out_childrens:
            self.assertTrue(isinstance(l3_out_child, OutsideEPG))

        # Clean up
        self.base_test_teardown(session, tenant)


class TestLiveEPGDomain(TestLiveAPIC):
    """
    Test live EPG Domain
    """
    def test_get(self):
        """
        Test get all EPG Domains from APIC
        """
        session = self.login_to_apic()
        epg_domains = EPGDomain.get(session)
        self.assertTrue(len(epg_domains) > 0)
        for epg_domain in epg_domains:
            self.assertTrue(isinstance(epg_domain, EPGDomain))
            self.assertTrue(isinstance(epg_domain.name, str))


class TestLiveEndpoint(TestLiveAPIC):
    """
    Live tests for Endpoint class
    """
    def setUp(self):
        session = self.login_to_apic()

        # Create a tenant with endpoints in 2 EPGs, 5 endpoints in each
        tenant = Tenant('acitoolkit-test')
        app = AppProfile('myapp', tenant)
        epg1 = EPG('epg1', app)
        epg2 = EPG('epg2', app)
        intf = Interface('eth', '1', '101', '1', '1')

        # Create a VLAN interface and attach to the physical interface
        vlan_intf5 = L2Interface('vlan5', 'vlan', '5')
        vlan_intf5.attach(intf)

        vlan_intf6 = L2Interface('vlan5', 'vlan', '6')
        vlan_intf6.attach(intf)

        # Attach the EPG to the VLAN interface
        epg1.attach(vlan_intf5)
        epg2.attach(vlan_intf6)

        for epg, epg_prefix, vlan_intf in [(epg1, '11', vlan_intf5), (epg2, '22', vlan_intf6)]:
            for i in range(0, 5):
                mac = '00:11:11:11:%s:1%s' % (epg_prefix, str(i))
                ip = '10.10.%s.%s' % (epg_prefix, str(i))
                ep = Endpoint(name=mac, parent=epg)
                ep.mac = mac
                ep.ip = ip
                ep.attach(vlan_intf)
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

    def tearDown(self):
        session = self.login_to_apic()

        # Create a tenant with endpoints in 2 EPGs, 5 endpoints in each
        tenant = Tenant('acitoolkit-test')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

    def test_get_bad_session(self):
        """
        Test Endpoint.get() supplied with a bad session
        """
        bad_session = 'BAD SESSION'
        self.assertRaises(TypeError, Endpoint.get, bad_session)

    def test_get(self):
        """
        Test Endpoint.get()
        """
        session = self.login_to_apic()
        endpoints = Endpoint.get(session)

    def test_get_all_by_epg(self):
        """
        Test Endpoint.get_all_by_epg()
        """
        session = self.login_to_apic()
        endpoints = Endpoint.get(session)

        epg, app, tenant = None, None, None

        for endpoint in endpoints:
            if not isinstance(endpoint.get_parent(), EPG):
                continue
            epg = endpoint.get_parent()
            app = epg.get_parent()
            tenant = app.get_parent()

        self.assertNotEqual(tenant, None)
        endpoints = Endpoint.get_all_by_epg(session, tenant.name, app.name, epg.name, with_interface_attachments=False)
        self.assertGreater(len(endpoints), 0)

    def test_get_table(self):
        """
        Test Endpoint.get_table()
        """
        session = self.login_to_apic()
        endpoints = Endpoint.get(session)
        self.assertTrue(isinstance(Endpoint.get_table(endpoints)[0], Table))


class TestApic(TestLiveAPIC):
    """
    APIC live tests
    """
    def base_test_setup(self):
        """
        Set up the tests
        """
        session = self.login_to_apic()

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

        return (session, tenant, app, epg)

    def base_test_teardown(self, session, tenant):
        """
        Tear down the tests
        """
        # Delete the tenant
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_assign_epg_to_interface(self):
        """
        Assign the EPG to an interface
        """
        # Set up the tenant, app, and epg
        (session, tenant, app, epg) = self.base_test_setup()

        # Count the EPG attachments
        url = ('/api/mo/uni/tn-%s.json?query-target=subtree&'
               'target-subtree-class=fvRsPathAtt' % tenant.name)
        attachments = session.get(url)
        attachment_data = attachments.json()
        if 'totalCount' in attachment_data:
            num_attachments_before = int(attachment_data['totalCount'])
        else:
            num_attachments_before = 0

        # Attach the EPG to an Interface
        intf = Interface('eth', '1', '101', '1', '69')
        l2_intf = L2Interface('l2if', 'vlan', '5')
        l2_intf.attach(intf)
        epg.attach(l2_intf)
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Verify that the number of attachments increased
        attachments = session.get(url)
        attachment_data = attachments.json()
        if 'totalCount' in attachment_data:
            num_attachments_after = int(attachments.json()['totalCount'])
        else:
            num_attachments_after = 0
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
        """
        Assign the bridgedomain to an EPG
        """
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
        expected = ('{"fvTenant": {"attributes": {"name": "aci-toolkit-test"}, '
                    '"children": [{"fvAp": {"attributes": {"name": "app1"}, "ch'
                    'ildren": [{"fvAEPg": {"attributes": {"name": "epg1"}, "chi'
                    'ldren": [{"fvRsBd": {"attributes": {"tnFvBDName": "bd1"}}}'
                    ']}}]}}, {"fvBD": {"attributes": {"arpFlood": "no", "mac": '
                    '"00:22:BD:F8:19:FF", "multiDstPktAct": "bd-flood", "name":'
                    ' "bd1", "unicastRoute": "yes", "unkMacUcastAct": "proxy", '
                    '"unkMcastAct": "flood"}, "children": []}}]}}')

        actual = json.dumps(tenant.get_json(), sort_keys=True)
        self.assertTrue(actual == expected)

        # Remove the bridgedomain from the EPG
        epg.remove_bd()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Clean up
        self.base_test_teardown(session, tenant)

    def test_get_contexts(self):
        """
        Test Context.get()
        """
        (session, tenant, app, epg) = self.base_test_setup()
        Context.get(session, tenant)

    def test_get_contexts_table(self):
        """
        Test Context.get_table()
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        total_contexts = []
        for tenant in tenants:
            contexts = Context.get(session, tenant)
            for context in contexts:
                total_contexts.append(context)
        contexts_table = Context.get_table(total_contexts)[0]
        self.assertIsInstance(contexts_table, Table)

    def test_get_contexts_invalid_tenant_as_string(self):
        """
        Test Context.get invalid parent
        """
        (session, tenant, app, epg) = self.base_test_setup()
        self.assertRaises(TypeError, Context.get, session, 'tenant')

    def test_assign_epg_to_port_channel(self):
        """
        Assign EPG to a port channel
        """
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
                    '{"id": "105", "name": "vpc105"}, "children": [{'
                    '"fabricNodePEp": {"attributes": {"id": "105"}}}, '
                    '{"fabricNodePEp": {"attributes": {"id": "106"}}}]}}]}}')
        self.assertTrue(json.dumps(fabric, sort_keys=True) == expected)
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
        """
        Test Context.set_allow_all()
        """
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
        """
        Test BridgeDomain.attach to a Context
        """
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
        """
        Basic test for Subnet class
        """
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

        tenant = Tenant(tenant.name)
        bd = BridgeDomain('bd1', tenant)
        subnets = Subnet.get(session, bd, tenant)
        self.assertNotEqual(len(subnets), 0)

        # Cleanup
        self.base_test_teardown(session, tenant)

    def test_ospf_basic(self):
        """
        Basic test for OSPF
        """
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
        outside_l3 = OutsideL3('out-1', tenant)
        outside_l3.add_context(context)
        outside_l3.attach(ospfif)

        # Create a contract and provide from the Outside EPG
        contract1 = Contract('contract-1', tenant)
        outside_epg = OutsideEPG('epg-1', outside_l3)
        outside_epg.provide(contract1)

        # Create another contract and consume from the Outside EPG
        contract2 = Contract('contract-2', tenant)
        outside_epg.consume(contract2)

        # Push to APIC and verify a successful request
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        self.base_test_teardown(session, tenant)


class TestLivePhysDomain(TestLiveAPIC):
    """
    Class to test live phys domain
    """
    def create_unique_live_phys_domain(self):
        """
        Create live phys domain that will not conflict with phys domains on APIC
        """
        session = self.login_to_apic()
        phys_domains = PhysDomain.get(session)
        non_existing_phys_domain = phys_domains[0]
        while non_existing_phys_domain in phys_domains:
            non_existing_phys_domain = PhysDomain(random_size_string(), None)
        return non_existing_phys_domain

    def get_all_phys_domains(self):
        """
        Get all phys domains from APIC and test phys domain get function
        """
        session = self.login_to_apic()
        phys_domains = PhysDomain.get(session)
        self.assertTrue(len(phys_domains) > 0)
        return phys_domains

    def get_all_phys_domain_names(self):
        """
        Test getting phys domain names
        """
        phys_domains = self.get_all_phys_domains()
        names = []
        for phys_domain in phys_domains:
            names.append(phys_domain.name)
        return names

    def test_get_by_name(self):
        """
        Test get by name function
        """
        # Log in to APIC
        session = self.login_to_apic()

        # Create new phys domain and push to APIC
        new_phys_domain = PhysDomain('phys_domain_toolkit_test', None)
        new_phys_domain.push_to_apic(session)
        self.assertTrue(new_phys_domain.push_to_apic(session).ok)

        # Test get by name function (passing conditional to successfully find name)
        phys_domain_by_name = PhysDomain.get_by_name(session, 'phys_domain_toolkit_test')
        self.assertEqual(phys_domain_by_name, new_phys_domain)

        # Delete new phys domain
        new_phys_domain.mark_as_deleted()
        new_phys_domain.push_to_apic(session)
        self.assertTrue(new_phys_domain.push_to_apic(session).ok)

        # Test get by name function (failing conditional to find name)
        phys_domain_by_name = PhysDomain.get_by_name(session, 'phys_domain_toolkit_test')
        self.assertIsNone(phys_domain_by_name)

        # Verify that new phys domain is deleted
        names = self.get_all_phys_domain_names()
        self.assertTrue(new_phys_domain.name not in names)


class TestLiveVmm(TestLiveAPIC):
    """
    Live tests for VMM class
    """
    def test_get(self):
        """
        Test VMM.get()
        """
        session = self.login_to_apic()
        vmms = VMM.get(session)
        for vmm in vmms:
            self.assertTrue(isinstance(vmm, VMM))


class TestLiveVmmDomain(TestLiveAPIC):
    """
    Live tests for VmmDomain class
    """
    def test_get(self):
        """
        Test VmmDomain.get()
        """
        session = self.login_to_apic()
        vmm_domains = VmmDomain.get(session)
        for vmm_domain in vmm_domains:
            self.assertTrue(isinstance(vmm_domain, VmmDomain))
        return vmm_domains

    def test_get_json(self):
        """
        Test VmmDomain.get_deep()
        """
        vmm_domains = self.test_get()
        for vmm_domain in vmm_domains:
            self.assertTrue(type(vmm_domain.get_json()) is dict)

    def test_get_by_name(self):
        """
        Test VmmDomain.get_by_name()
        """
        session = self.login_to_apic()
        vmm_domains = VmmDomain.get(session)
        for vmm_domain in vmm_domains:
            self.assertEqual(VmmDomain.get_by_name(session, vmm_domain.name), vmm_domain)


class TestLiveFilter(TestLiveAPIC):
    """
    Live tests for Filter class
    """
    def test_filter_no_children_no_parent(self):
        """
        Test Filter created with no parent nor child
        """
        tenant = Tenant('aci-toolkit-test')
        filt = Filter('Filter')

        # Push to APIC
        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_filter_no_children_parent(self):
        """
        Test Filter created with parent but no child
        """
        tenant = Tenant('aci-toolkit-test')
        contract = Contract('contract', tenant)
        contract_subject = ContractSubject('contract_subject', contract)
        filt = Filter('Filter', contract_subject)

        # Push to APIC
        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_filter_children_no_parent(self):
        """
        Test Filter created with child but no parent
        """
        tenant = Tenant('aci-toolkit-test')
        filt = Filter('Filter')
        filt_entry = FilterEntry('FilterEntry', filt)

        # Push to APIC
        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_filter_children_parent(self):
        """
        Test Filter created with child and parent
        """
        tenant = Tenant('aci-toolkit-test')
        contract = Contract('contract', tenant)
        contract_subject = ContractSubject('contract_subject', contract)
        filt = Filter('Filter', contract_subject)
        filt_entry = FilterEntry('FilterEntry', filt)

        # Push to APIC
        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)


class TestLiveFilterEntry(TestLiveAPIC):
    """
    Live tests for FilterEntry class
    """
    def test_get(self):
        """
        Test FilterEntry.get()
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        filter_entries = []
        # contracts = []
        for tenant in tenants:
            tenant_contracts = Contract.get(session, tenant)
            for tenant_contract in tenant_contracts:
                contract_filter_entries = FilterEntry.get(session, tenant_contract, tenant)
                for contract_filter_entry in contract_filter_entries:
                    filter_entries.append(contract_filter_entry)
        for filter_entry in filter_entries:
            self.assertTrue(isinstance(filter_entry, FilterEntry))
        return filter_entries

    def test_get_bad_parent(self):
        """
        Test FilterEntry.get() with a bad parent
        """
        session = self.login_to_apic()
        contract = Contract('contract', Tenant('tenant'))
        with self.assertRaises(TypeError):
            FilterEntry.get(session, contract, 'tenant')

    def test_get_table(self):
        """
        Test FilterEntry.get_table()
        """
        filter_entries = self.test_get()
        self.assertTrue(FilterEntry.get_table(filter_entries), Table)


class TestLiveContracts(TestLiveAPIC):
    """
    Live tests for Contract class
    """
    def get_2_entries(self, contract):
        """
        Get 2 FilterEntry instances
        :param contract: Contract instance that will serve as the parent for the FilterEntry instances
        :return: Tuple containing the 2 FilterEntry instances
        """
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
        return (entry1, entry2)

    def test_get(self):
        """
        Test Contract.get()
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        contracts = Contract.get(session, tenant)

    def test_create_basic_contract(self):
        """
        Test Contract creation
        """
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
        """
        Test Taboo creation
        """
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
        """
        Test Contract scope
        """
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

    def test_get_table(self):
        """
        Test Contract.get_table()
        """
        session = self.login_to_apic()
        tenants = Tenant.get(session)
        self.assertTrue(len(tenants) > 0)
        total_contracts = []
        for tenant in tenants:
            contracts = Contract.get(session, tenant)
            for contract in contracts:
                total_contracts.append(contract)

        self.assertIsInstance(Contract.get_table(total_contracts)[0], Table)

    def test_get_deep_contract_consumed_same_tenant(self):
        """
        Test get_deep() that contract consume relationship is set correctly
        """
        apic = self.login_to_apic()

        # Create the tenant
        tenant = Tenant('aci-toolkit-test')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('mycontract', tenant)
        epg.consume(contract)
        self.assertTrue(epg.does_consume(contract))

        # Push tenant to the APIC
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        # Get the tenant using get_deep
        tenants = Tenant.get_deep(apic, names=['aci-toolkit-test'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]

        # Check that the EPG consumes the contract
        contract = tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract)
        app = tenant.get_child(AppProfile, 'app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, 'epg')
        self.assertIsNotNone(epg)

        self.assertTrue(epg.does_consume(contract))

        # Delete the tenant
        tenant.mark_as_deleted()
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def test_get_deep_contract_consumed_different_tenant(self):
        """
        Test get_deep() that contract consume relationship is set correctly
        """
        apic = self.login_to_apic()

        # Create the contract in tenant common
        common_tenant = Tenant('common')
        common_contract = Contract('aci-toolkit-test', common_tenant)

        # Push contract to the APIC
        resp = common_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        # Create the tenant
        tenant = Tenant('aci-toolkit-test')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        epg.consume(common_contract)
        self.assertTrue(epg.does_consume(common_contract))

        # Push tenant to the APIC
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        # Get the tenant using get_deep
        fabric = Fabric()
        tenants = Tenant.get_deep(apic, names=['aci-toolkit-test', 'common'], parent=fabric)
        self.assertTrue(len(tenants) > 0)
        consumer_tenant = None
        common_tenant = None
        for tenant in tenants:
            if tenant.name == 'aci-toolkit-test':
                consumer_tenant = tenant
            elif tenant.name == 'common':
                common_tenant = tenant
        self.assertIsNotNone(consumer_tenant)
        self.assertIsNotNone(common_tenant)

        # Check that the EPG consumes the contract
        contract = common_tenant.get_child(Contract, 'aci-toolkit-test')
        self.assertIsNotNone(contract)
        app = consumer_tenant.get_child(AppProfile, 'app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, 'epg')
        self.assertIsNotNone(epg)

        self.assertTrue(epg.does_consume(contract))

        # Delete the tenant
        consumer_tenant.mark_as_deleted()
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        # Delete the tenant common contract
        common_tenant = Tenant('common')
        common_contract = Contract('aci-toolkit-test', common_tenant)
        common_contract.mark_as_deleted()
        resp = common_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)


class TestLiveContractInterface(TestLiveAPIC):
    """
    Live tests for ContractInterface
    """
    def setUp(self):
        apic = self.login_to_apic()

        provider_tenant = Tenant('aci-toolkit-test-provider')
        app = AppProfile('myapp', provider_tenant)
        epg = EPG('myepg', app)
        contract = Contract('mycontract', provider_tenant)
        (entry1, entry2) = self.get_2_entries(contract)
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        consumer_tenant = Tenant('aci-toolkit-test-consumer')
        consumer_app = AppProfile('consumer-app', consumer_tenant)
        consumer_epg = EPG('consumerappepg', consumer_app)
        context = Context('mycontext', consumer_tenant)
        l3out = OutsideL3('myl3out', consumer_tenant)
        consumer_outside_epg = OutsideEPG('consumerepg', l3out)
        consumer_network = OutsideNetwork('5.1.1.1', consumer_outside_epg)
        consumer_network.ip = '5.1.1.1/8'
        contract_if = ContractInterface('mycontract', consumer_tenant)
        contract_if.import_contract(contract)
        consumer_outside_epg.consume_cif(contract_if)
        consumer_epg.consume_cif(contract_if)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def tearDown(self):
        provider_tenant = Tenant('aci-toolkit-test-provider')
        provider_tenant.mark_as_deleted()
        consumer_tenant = Tenant('aci-toolkit-test-consumer')
        consumer_tenant.mark_as_deleted()
        apic = self.login_to_apic()
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def get_2_entries(self, contract):
        """
        Get 2 FilterEntry instances
        :param contract: Contract instance that will serve as the parent for the FilterEntry instances
        :return: Tuple containing the 2 FilterEntry instances
        """
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
        return (entry1, entry2)

    def test_get(self):
        """
        Test ContractInterface.get()
        """
        apic = self.login_to_apic()
        tenant = Tenant('aci-toolkit-test-consumer')
        contract_ifs = ContractInterface.get(apic, tenant)
        self.assertEqual(len(contract_ifs), 1)

    def test_get_deep_contract_if(self):
        """
        Test ContractInterface.get_deep()
        """
        apic = self.login_to_apic()

        # Get the tenants
        fabric = Fabric()
        tenants = Tenant.get_deep(apic, names=['aci-toolkit-test-provider', 'aci-toolkit-test-consumer'], parent=fabric)
        self.assertEqual(len(tenants), 2)
        self.assertEqual(tenants[0].get_parent(), tenants[1].get_parent())
        self.assertEqual(tenants[0].get_parent(), fabric)

        # Find the Tenant with the ContractInterface
        consumer_tenant = None
        for tenant in tenants:
            if tenant.name == 'aci-toolkit-test-consumer':
                consumer_tenant = tenant
        self.assertIsNotNone(consumer_tenant)

        # Find the ContractInterface
        children = consumer_tenant.get_children(only_class=ContractInterface)
        self.assertEqual(len(children), 1)
        contract_if = children[0]

        # Find the Tenant providing the Contract
        provider_tenant = None
        for tenant in tenants:
            if tenant.name == 'aci-toolkit-test-provider':
                provider_tenant = tenant
                break
        self.assertIsNotNone(provider_tenant)

        # Find the Contract
        provided_contract = provider_tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(provided_contract)

        # Verify that it imports the correct Contract
        self.assertTrue(contract_if.has_import_contract())
        self.assertTrue(contract_if.does_import_contract(provided_contract))

        # Find the EPG that it supposed to be consuming the ContractInterface
        outsidel3 = consumer_tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(outsidel3)
        consumer_epg = outsidel3.get_child(OutsideEPG, 'consumerepg')
        self.assertIsNotNone(consumer_epg)
        self.assertTrue(consumer_epg.does_consume_cif(contract_if))


class TestLiveContractSubject(TestLiveAPIC):
    """
    Live tests using an actual APIC for ContractSubject
    """
    def test_filter_no_children_no_parent(self):
        """
        Test pushing basic empty ContractSubject with no parent
        """
        tenant = Tenant('aci-toolkit-test')
        contract_subject = ContractSubject('contract_subject')
        # TODO shouldn't this create an exception of some sort ?

        # Push to APIC
        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_contract_subject_no_children_parent(self):
        """
        Test pushing basic empty ContractSubject with a Contract parent configured
        """
        tenant = Tenant('aci-toolkit-test')
        contract = Contract('contract', tenant)
        contract_subject = ContractSubject('contract_subject', contract)

        # Push to APIC
        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_contract_subject_children_parent(self):
        """
        Test pushing ContractSubject with a Contract parent configured and a Filter child
        """
        tenant = Tenant('aci-toolkit-test')
        contract = Contract('contract', tenant)
        contract_subject = ContractSubject('contract_subject', contract)
        filt = Filter('Filter', contract_subject)

        # Push to APIC
        session = self.login_to_apic()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

        # Cleanup
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)


class TestLiveOSPF(TestLiveAPIC):
    """
    Live tests using an actual APIC for OSPF
    """
    def test_no_auth(self):
        """
        Test basic no authentication
        """
        tenant = Tenant('cisco')
        context = Context('cisco-ctx1', tenant)
        outside_l3 = OutsideL3('out-1', tenant)
        outside_l3.add_context(context)
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
        outside_epg = OutsideEPG('epg-1', outside_l3)
        outside_epg.provide(contract1)
        contract2 = Contract('contract-2')
        outside_epg.consume(contract2)
        outside_l3.attach(ospfif)
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
        """
        Test basic authentication
        """
        tenant = Tenant('cisco')
        context = Context('cisco-ctx1', tenant)
        outside_l3 = OutsideL3('out-1', tenant)
        outside_l3.add_context(context)
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
        outside_epg = OutsideEPG('epg-1', outside_l3)
        outside_epg.provide(contract1)
        contract2 = Contract('contract-2')
        outside_epg.consume(contract2)
        outside_l3.attach(ospfif)

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
    def check_collection_policy(self, parent):
        """
        Check the collection policy
        """
        for index in parent.collection_policy:
            policy = parent.collection_policy[index]
            self.assertEqual(index, policy.granularity)
            self.assertIn(policy.granularity, ['5min', '15min', '1h', '1d',
                                               '1w', '1mo', '1qtr', '1year'])
            self.assertIn(policy.retention,
                          ['none', 'inherited', '5min', '15min', '1h', '1d',
                           '1w', '10d', '1mo', '1qtr', '1year', '2year',
                           '3year'])
            self.assertIn(policy.adminState,
                          ['enabled', 'disabled', 'inherited'])
            self.assertEqual(policy._parent, parent)

    def test_get(self):
        """
        Test MonitorPolicy.get()
        """
        session = self.login_to_apic()
        policies = MonitorPolicy.get(session)
        self.assertTrue(len(policies) > 0)
        for policy in policies:
            self.assertIn(policy.policyType, ['fabric', 'access'])
            self.assertIsInstance(policy.name, str)
            self.check_collection_policy(policy)
        return policies

    def test_monitor_target(self):
        """
        Test MonitorPolicy monitor_target
        """
        session = self.login_to_apic()
        policies = MonitorPolicy.get(session)
        for policy in policies:
            monitor_targets = policy.monitor_target
            for index in monitor_targets:
                monitor_target = monitor_targets[index]
                self.assertIn(monitor_target.scope, ['l1PhysIf'])
                self.assertEqual(monitor_target._parent, policy)
                self.assertIsInstance(monitor_target.descr, str)
                self.assertIsInstance(monitor_target.name, str)
                self.check_collection_policy(monitor_target)

    def test_monitor_stats(self):
        """
        Test MonitorPolicy monitor_stats
        """
        session = self.login_to_apic()
        policies = MonitorPolicy.get(session)
        for policy in policies:
            monitor_targets = policy.monitor_target
            for index in monitor_targets:
                monitor_stats = monitor_targets[index].monitor_stats
                for index2 in monitor_stats:
                    monitor_stat = monitor_stats[index2]
                    self.assertIn(monitor_stat.scope,
                                  ['egrBytes', 'egrPkts', 'egrTotal',
                                   'egrDropPkts', 'ingrBytes', 'ingrPkts',
                                   'ingrTotal', 'ingrDropPkts', 'ingrUnkBytes',
                                   'ingrUnkPkts', 'ingrStorm'])
                    self.assertEqual(monitor_stat._parent,
                                     monitor_targets[index])
                    self.assertIsInstance(monitor_stat.descr, str)
                    self.assertIsInstance(monitor_stat.name, str)
                    self.check_collection_policy(monitor_stat)


class TestLiveHealthScores(TestLiveAPIC):
    """
    Live tests for HealthScore class
    """
    def base_test_setup(self):
        """
        Set up the test
        """
        session = self.login_to_apic()

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

        return (session, tenant, app, epg)

    def base_test_teardown(self, session, tenant):
        """
        Tear down the test
        """
        # Delete the tenant
        tenant.mark_as_deleted()
        resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        self.assertTrue(resp.ok)

    def test_get_all_healthscores(self):
        """
        Test HealthScore.get_all
        """
        (session, tenant, app, epg) = self.base_test_setup()
        session = self.login_to_apic()
        scores = HealthScore.get_all(session)
        scores = HealthScore.get_all(session)
        test = len(scores) > 1
        self.assertTrue(test)
        self.base_test_teardown(session, tenant)

    # TODO: the following lines are commented out until .dn attribute is implemented more pervasively
    #
    # def test_get_object_healthscore(self):
    #     (session, tenant, app, epg) = self.base_test_setup()
    #     push = session.push_to_apic(tenant.get_url(), tenant.get_json())
    #     scores = []
    #     for o in [tenant,app,epg]:
    #         hs = HealthScore.get(session, o)
    #         scores.append(hs.cur)
    #     self.assertEqual(scores, ['100','100','100'])

    def test_get_healthscore_by_dn(self):
        """
        Test HealthScore.get_by_dn
        """
        (session, tenant, app, epg) = self.base_test_setup()
        ts = HealthScore.get_by_dn(session, 'uni/tn-aci-toolkit-test')
        try:
            self.assertIsInstance(ts.cur, unicode)
        # NameError is risen when code is run with Python3
        except NameError:
            self.assertIsInstance(ts.cur, str)
        self.assertGreaterEqual(int(ts.cur), 0)
        self.assertLessEqual(int(ts.cur), 100)
        self.base_test_teardown(session, tenant)

    def test_get_unhealthy(self):
        """
        Test get_unhealthy
        """
        (session, tenant, app, epg) = self.base_test_setup()
        unhealthy = HealthScore.get_unhealthy(session, 100)


if __name__ == '__main__':
    live = unittest.TestSuite()
    live.addTest(unittest.makeSuite(TestLiveHealthScores))
    live.addTest(unittest.makeSuite(TestLiveTenant))
    live.addTest(unittest.makeSuite(TestLiveAPIC))
    live.addTest(unittest.makeSuite(TestLiveCertAuth))
    live.addTest(unittest.makeSuite(TestLiveAppcenterSubscription))
    live.addTest(unittest.makeSuite(TestLiveInterface))
    live.addTest(unittest.makeSuite(TestLivePortChannel))
    live.addTest(unittest.makeSuite(TestLiveAppProfile))
    live.addTest(unittest.makeSuite(TestLiveEPG))
    live.addTest(unittest.makeSuite(TestLiveAnyEPG))
    live.addTest(unittest.makeSuite(TestLiveAnyEPGWithTenantCommonContracts))
    live.addTest(unittest.makeSuite(TestLiveL2ExtDomain))
    live.addTest(unittest.makeSuite(TestLiveL3ExtDomain))
    live.addTest(unittest.makeSuite(TestLiveEPGDomain))
    live.addTest(unittest.makeSuite(TestLiveFilter))
    live.addTest(unittest.makeSuite(TestLiveFilterEntry))
    live.addTest(unittest.makeSuite(TestLiveContracts))
    live.addTest(unittest.makeSuite(TestLiveContractSubject))
    live.addTest(unittest.makeSuite(TestLiveEndpoint))
    live.addTest(unittest.makeSuite(TestApic))
    live.addTest(unittest.makeSuite(TestLivePhysDomain))
    live.addTest(unittest.makeSuite(TestLiveVmmDomain))
    live.addTest(unittest.makeSuite(TestLiveVmm))
    live.addTest(unittest.makeSuite(TestLiveSubscription))
    live.addTest(unittest.makeSuite(TestLiveOSPF))
    live.addTest(unittest.makeSuite(TestLiveMonitorPolicy))
    live.addTest(unittest.makeSuite(TestLiveOutsideL3))
    live.addTest(unittest.makeSuite(TestLiveOutsideEPG))
    live.addTest(unittest.makeSuite(TestLiveContractInterface))
    live.addTest(unittest.makeSuite(TestLiveSession))

    offline = unittest.TestSuite()
    offline.addTest(unittest.makeSuite(TestBaseRelation))
    offline.addTest(unittest.makeSuite(TestBaseACIObject))
    offline.addTest(unittest.makeSuite(TestTenant))
    offline.addTest(unittest.makeSuite(TestSession))
    offline.addTest(unittest.makeSuite(TestAppProfile))
    offline.addTest(unittest.makeSuite(TestBridgeDomain))
    offline.addTest(unittest.makeSuite(TestL2Interface))
    offline.addTest(unittest.makeSuite(TestL3Interface))
    offline.addTest(unittest.makeSuite(TestBaseContract))
    offline.addTest(unittest.makeSuite(TestContract))
    offline.addTest(unittest.makeSuite(TestContractInterface))
    offline.addTest(unittest.makeSuite(TestContractSubject))
    offline.addTest(unittest.makeSuite(TestFilter))
    offline.addTest(unittest.makeSuite(TestFilterEntry))
    offline.addTest(unittest.makeSuite(TestTaboo))
    offline.addTest(unittest.makeSuite(TestEPG))
    offline.addTest(unittest.makeSuite(TestOutsideEPG))
    offline.addTest(unittest.makeSuite(TestPhysDomain))
    offline.addTest(unittest.makeSuite(TestJson))
    offline.addTest(unittest.makeSuite(TestEPGDomain))
    offline.addTest(unittest.makeSuite(TestPortChannel))
    offline.addTest(unittest.makeSuite(TestContext))
    offline.addTest(unittest.makeSuite(TestOspf))
    offline.addTest(unittest.makeSuite(TestBGP))
    offline.addTest(unittest.makeSuite(TestEndpoint))
    offline.addTest(unittest.makeSuite(TestMonitorPolicy))
    offline.addTest(unittest.makeSuite(TestAttributeCriterion))
    offline.addTest(unittest.makeSuite(TestOutsideL2))
    offline.addTest(unittest.makeSuite(TestOutsideNetwork))
    offline.addTest(unittest.makeSuite(TestTunnelInterface))
    offline.addTest(unittest.makeSuite(TestFexInterface))
    offline.addTest(unittest.makeSuite(TestInputTerminal))
    offline.addTest(unittest.makeSuite(TestOutputTerminal))
    offline.addTest(unittest.makeSuite(TestAnyEPG))
    offline.addTest(unittest.makeSuite(TestOutsideL2EPG))

    graphs = unittest.TestSuite()
    graphs.addTest(unittest.makeSuite(TestAcitoolkitGraphBuilder))

    full = unittest.TestSuite([live, offline, graphs])

    # Add tests to this suite while developing the tests
    # This allows only these tests to be run
    develop = unittest.TestSuite()

    unittest.main(defaultTest='offline')
