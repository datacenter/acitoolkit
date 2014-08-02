"""ACI Toolkit Test module
"""
from acitoolkit import *
import unittest
import string
import random
from credentials import *
import xml.dom.minidom
import sys

LIVE_TEST = True
MAX_RANDOM_STRING_SIZE = 20


def random_string(size):
    """Generates a random string of a certain specified size
    RETURNS: String
    """
    return ''.join(random.choice(string.ascii_uppercase +
                                 string.digits) for _ in range(size))


def random_size_string():
    """Generates a random string between 1 and
       MAX_RANDOM_STRING_SIZE characters
    RETURNS: String
    """
    return random_string(random.randint(1, MAX_RANDOM_STRING_SIZE))


class TestBaseRelation(unittest.TestCase):
    """Tests on the BaseRelation class.  These do not communicate with the APIC
    """
    def create_relation(self, status='attached'):
        tenant = Tenant('test')
        relation = BaseRelation(tenant, status)
        return tenant, relation

    def create_attached_relation(self):
        return self.create_relation('attached')

    def create_detached_relation(self):
        return self.create_relation('detached')

    def test_create_with_valid_status_attached(self):
        tenant, relation = self.create_attached_relation()
        self.assertTrue(relation is not None)

    def test_create_with_valid_status_detached(self):
        tenant, relation = self.create_detached_relation()
        self.assertTrue(relation is not None)

    def test_create_invalid(self):
        tenant = Tenant('test')
        self.assertRaises(ValueError, BaseRelation, tenant, 'something else')

    def test_is_attached(self):
        tenant, relation = self.create_attached_relation()
        self.assertTrue(relation.is_attached())

    def test_is_detached(self):
        tenant, relation = self.create_detached_relation()
        self.assertTrue(relation.is_detached())

    def test_set_detached(self):
        tenant, relation = self.create_attached_relation()
        self.assertTrue(relation.is_attached())
        relation.set_as_detached()
        self.assertFalse(relation.is_attached())
        self.assertTrue(relation.is_detached())


class MockACIObject(BaseACIObject):
    def get_json(self):
        super(MockACIObject, self).get_json('mock')

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

    def test_get_xml(self):
        obj = MockACIObject('mock')
        # parseString will actually print to stdout
        # so we temporarily override it for this test
        temp = sys.stdout
        sys.stdout = obj
        xml.dom.minidom.parseString(obj.get_xml())
        xml.dom.minidom.parseString(obj.get_xml(True))
        sys.stdout = temp

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
    def test_create(self):
        tenant = Tenant('tenant')
        self.assertNotEqual(tenant, None)

    def test_json(self):
        tenant = Tenant('tenant')
        self.assertTrue(type(tenant.get_json()) == dict)


class TestAppProfile(unittest.TestCase):
    def test_create(self):
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        self.assertNotEqual(app, None)

    def test_invalid_create_no_parent(self):
        self.assertRaises(TypeError, AppProfile, 'app', None)

    def test_invalid_create_parent_as_string(self):
        self.assertRaises(TypeError, AppProfile, 'app', 'tenant')

    def test_invalid_create_no_name(self):
        self.assertRaises(TypeError, AppProfile, None, Tenant('tenant'))

    def test_invalid_create_not_string_name(self):
        tenant = Tenant('tenant')
        self.assertRaises(TypeError, AppProfile, tenant, tenant)

    def test_delete(self):
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        self.assertFalse(app.is_deleted())
        app.mark_as_deleted()
        self.assertTrue(app.is_deleted())

    def test_eq(self):
        tenant = Tenant('tenant')
        app1 = AppProfile('app', tenant)
        app2 = AppProfile('app', tenant)
        self.assertEqual(app1, app2)

    def test_not_eq_different_name(self):
        tenant = Tenant('tenant')
        app1 = AppProfile('app1', tenant)
        app2 = AppProfile('app2', tenant)
        self.assertNotEqual(app1, app2)

    def test_not_eq_different_parent(self):
        tenant1 = Tenant('tenant1')
        tenant2 = Tenant('tenant2')
        app1 = AppProfile('app', tenant1)
        app2 = AppProfile('app', tenant2)
        self.assertNotEqual(app1, app2)

    def test_json(self):
        tenant = Tenant('tenant')
        app = AppProfile('app', tenant)
        self.assertTrue(type(app.get_json()) == dict)


class TestBridgeDomain(unittest.TestCase):
    def create_bd(self):
        tenant = Tenant('tenant')
        bd = BridgeDomain('bd', tenant)
        return tenant, bd

    def create_bd_with_subnet(self):
        tenant, bd = self.create_bd()
        sub1 = Subnet('sub1', bd)
        sub1.set_addr('1.1.1.1/24')
        bd.add_subnet(sub1)
        return bd, sub1

    def test_valid_create(self):
        tenant, bd = self.create_bd()
        self.assertNotEqual(bd, None)

    def test_invalid_create_no_parent(self):
        self.assertRaises(TypeError, BridgeDomain, 'bd', None)

    def test_invalid_create_parent_as_string(self):
        self.assertRaises(TypeError, BridgeDomain, 'bd', 'tenant')

    def test_invalid_create_no_name(self):
        self.assertRaises(TypeError, BridgeDomain, None, Tenant('tenant'))

    def test_invalid_create_not_string_name(self):
        tenant = Tenant('tenant')
        self.assertRaises(TypeError, BridgeDomain, tenant, tenant)

    def test_valid_delete(self):
        tenant, bd = self.create_bd()
        self.assertFalse(bd.is_deleted())
        bd.mark_as_deleted()
        self.assertTrue(bd.is_deleted())

    def test_add_valid_subnet(self):
        # Add a single subnet to the BD
        bd, sub1 = self.create_bd_with_subnet()
        # Verify that the subnet is there
        subnets = bd.get_subnets()
        self.assertTrue(len(subnets) == 1)
        self.assertTrue(subnets[0] == sub1)
        self.assertTrue(bd.has_subnet(sub1))

    def test_add_2_valid_subnets(self):
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
        tenant, bd = self.create_bd()
        self.assertRaises(TypeError, bd.add_subnet, 'sub1')

    def test_add_subnet_no_addr(self):
        tenant, bd = self.create_bd()
        sub1 = Subnet('sub1', bd)
        self.assertRaises(ValueError, bd.add_subnet, sub1)
        self.assertRaises(ValueError, bd.get_json)

    def test_add_subnet_wrong_parent(self):
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
        self.assertTrue(l2if.get_path() is None)

        physif = Interface('eth', '1', '1', '1', '1')
        l2if.attach(physif)
        self.assertTrue(l2if.get_path() is not None)


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
    def test_create_valid(self):
        intf = Interface('eth', '1', '1', '1', '1')
        intf.get_json()
        self.assertTrue(intf is not None)

    def parse_name(self, text):
        (intf_type, pod, node, module, port) = Interface.parse_name(text)
        self.assertTrue(intf_type == 'eth')
        self.assertTrue(pod == '1')
        self.assertTrue(node == '2')
        self.assertTrue(module == '3')
        self.assertTrue(port == '4')

    def test_parse_name_space(self):
        self.parse_name('eth 1/2/3/4')

    # def test_parse_name_no_space(self):
    #    self.parse_name('eth1/2/3/4')


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

    def test_valid_add_bd(self):
        tenant, app, epg, bd = self.create_epg_with_bd()
        self.assertTrue(epg.has_bd())
        self.assertTrue(epg.get_bd() == bd)

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
        expected = ('{"fvTenant": {"attributes": {"name": "cisco"}, '
                    '"children": [{"fvAp": {"attributes": {"name": '
                    '"ordersystem"}, "children": [{"fvAEPg": {"attributes":'
                    ' {"name": "web"}, "children": [{"fvRsPathAtt": '
                    '{"attributes": {"tDn": "topology/pod-1/paths-1/pathep'
                    '-[eth1/1]", "encap": "vlan-5"}}}]}}]}}]}}')
        tenant = Tenant('cisco')
        app = AppProfile('ordersystem', tenant)
        web_epg = EPG('web', app)
        intf = Interface('eth', '1', '1', '1', '1')
        vlan_intf = L2Interface('v5', 'vlan', '5')
        vlan_intf.attach(intf)
        web_epg.attach(vlan_intf)
        output = json.dumps(tenant.get_json())

        self.assertTrue(output == expected,
                        'Did not see expected JSON returned')


class TestPortChannel(unittest.TestCase):
    def test_create(self):
        if1 = Interface('eth', '1', '101', '1', '8')
        if2 = Interface('eth', '1', '101', '1', '9')
        pc = PortChannel('pc1')
        pc.attach(if1)
        pc.attach(if2)
        self.assertTrue(pc.is_interface())
        self.assertFalse(pc.is_vpc())

        # Add a 3rd interface to make it a VPC
        if3 = Interface('eth', '1', '102', '1', '9')
        pc.attach(if3)
        self.assertTrue(pc.is_vpc())

        # Remove the 3rd interface
        pc.detach(if3)
        self.assertFalse(pc.is_vpc())
        path = pc.get_path()
        self.assertTrue(isinstance(path, str))
        fabric, infra = pc.get_json()
        self.assertTrue(fabric is None)

    def test_portchannel(self):
        if1 = Interface('eth', '1', '101', '1', '8')
        if2 = Interface('eth', '1', '101', '1', '9')
        pc = PortChannel('pc1')
        pc.attach(if1)
        pc.attach(if2)

        # print pc.get_json()


class TestOspf(unittest.TestCase):
    def test_ospf_router_port(self):
        tenant = Tenant('cisco')
        context = Context('ctx-cisco', tenant)
        outside = OutsideEPG('out-1', tenant)
        phyif = Interface('eth', '1', '101', '1', '8')
        l2if = L2Interface('eth 1/101/1/8.5', 'vlan', '5')
        l2if.attach(phyif)
        l3if = L3Interface('l3if')
        l3if.set_l3if_type('l3-port')
        l3if.addr = '10.1.1.1/24'
        l3if.add_context(context)
        l3if.attach(l2if)
        ospfif = OSPFInterface('ospfif-1', '2')
        ospfif.auth_key = 'd667d47acc18e6b'
        ospfif.auth_keyid = '1'
        ospfif.auth_type = '2'
        ospfif.networks.append('55.5.5.0/24')
        ospfif.attach(l3if)
        contract1 = Contract('contract-1')
        outside.provide(contract1)
        contract2 = Contract('contract-2')
        outside.consume(contract2)
        outside.attach(ospfif)
        # print outside.get_json()

    def test_ospf_router(self):
        rtr = OSPFRouter('rtr-1')


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
class TestLiveAPIC(unittest.TestCase):
    def login_to_apic(self):
        """Login to the APIC
           RETURNS:  Instance of class Session
        """
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)
        return session


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
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


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
class TestLiveInterface(TestLiveAPIC):
    def test_get_all_interfaces(self):
        session = self.login_to_apic()
        self.assertRaises(TypeError, Interface.get, None)
        intfs = Interface.get(session)
        for interface in intfs:
            self.assertTrue(isinstance(interface, Interface))
            interface_as_a_string = str(interface)
            self.assertTrue(isinstance(interface_as_a_string, str))
            path = interface.get_path()
            self.assertTrue(isinstance(path, str))


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
class TestLiveAppProfile(TestLiveAPIC):
    def test_invalid_app(self):
        session = self.login_to_apic()
        self.assertRaises(TypeError, AppProfile.get, session, None)

    def test_valid_preexisting_app(self):
        session = self.login_to_apic()


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
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


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
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
        intf1 = Interface('eth', '1', '101', '1', '38')
        intf2 = Interface('eth', '1', '101', '1', '39')
        intf3 = Interface('eth', '1', '102', '1', '38')
        intf4 = Interface('eth', '1', '102', '1', '39')
        pc = PortChannel('pc1')
        pc.attach(intf1)
        pc.attach(intf2)
        pc.attach(intf3)
        pc.attach(intf4)
        (fabric, infra) = pc.get_json()
        expected = ('{"fabricProtPol": {"attributes": {"name": "vpc101"}, '
                    '"children": [{"fabricExplicitGEp": {"attributes": '
                    '{"name": "vpc101", "id": "101"}, "children": [{'
                    '"fabricNodePEp": {"attributes": {"id": "101"}}}, '
                    '{"fabricNodePEp": {"attributes": {"id": "102"}}}]}}]}}')
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

        # Create an OSPF Interface and connect to the L3 Interface
        ospfif = OSPFInterface('ospfif-1', '2')
        ospfif.auth_key = 'd667d47acc18e6b'
        ospfif.auth_keyid = '1'
        ospfif.auth_type = '2'
        ospfif.networks.append('55.5.5.0/24')
        ospfif.attach(l3_intf)

        # Create the Outside EPG
        self.assertRaises(TypeError, OutsideEPG, 'out-1', 'tenant')
        outside = OutsideEPG('out-1', tenant)
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


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
class TestLiveContracts(unittest.TestCase):
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

    def test_create_basic_contract(self):
        tenant = Tenant('aci-toolkit-test')
        contract = Contract('contract1', tenant)

        (entry1, entry2) = self.get_2_entries(contract)

        # Login to APIC
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)

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

        # Login to APIC
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)

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

        # Login to APIC
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)

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

if __name__ == '__main__':
    unittest.main()
