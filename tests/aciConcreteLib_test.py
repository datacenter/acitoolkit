"""
Concrete object tests
"""
from acitoolkit import (
    Node, Table
)
from acitoolkit.aciConcreteLib import (
    ConcreteArp, ConcreteArpDomain, ConcreteArpEntry,
    ConcreteVpc, ConcreteVpcIf,
    ConcreteContext, ConcreteBD, ConcreteSVI,
    ConcreteLoopback, ConcreteAccCtrlRule,
    ConcreteFilter, ConcreteFilterEntry, ConcreteEp,
    ConcretePortChannel, ConcreteTunnel, ConcreteOverlay,
    ConcreteCdp, ConcreteCdpIf, ConcreteCdpAdjEp)
import unittest


class TestConcreteArp(unittest.TestCase):
    """
    Test the ConcreteArp class
    """

    def test_create(self):
        """
        ConcreteArp creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteArp = ConcreteArp(node)
        self.assertNotEqual(concreteArp, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteArp._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteArp._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/arp/inst'
        self.assertEquals(ConcreteArp._get_name_from_dn(dn), '')

    def test_children_concrete_classes(self):
        """
        Test ConcreteArp _get_children_concrete_classes returns something list-like
        """
        node_id = '103'
        node = Node(node_id)
        concreteArp = ConcreteArp(node)
        self.assertTrue(
            isinstance(
                concreteArp._get_children_concrete_classes(),
                list))
        for child in concreteArp._get_children_concrete_classes():
            self.assertFalse(isinstance(child, ConcreteArpDomain))

    def test_eq(self):
        """
        Test ConcreteArp __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteArp = ConcreteArp(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteArp2 = ConcreteArp(node2)
        self.assertEqual(concreteArp, concreteArp2)

    def test_get_table(self):
        """
        Test ConcreteArp create table function
        """
        node1 = Node('103')
        node2 = Node('102')
        concreteArp1 = ConcreteArp(node1)
        concreteArp2 = ConcreteArp(node2)
        concreteArps = [concreteArp1, concreteArp2]
        self.assertTrue(
            isinstance(
                ConcreteArp.get_table(concreteArps)[0],
                Table))


class TestConcreteArpDomain(unittest.TestCase):
    """
    Test the ConcreteArpDomain class
    """

    def test_create(self):
        """
        ConcreteArpDomain creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteArp = ConcreteArp(node)
        concreteArpDomain = ConcreteArpDomain(concreteArp)
        self.assertNotEqual(concreteArpDomain, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteArpDomain._get_parent_class(), ConcreteArp)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteArpDomain._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/arp/inst/dom-Tenant1:T1-CTX2'
        self.assertEquals(
            ConcreteArpDomain._get_name_from_dn(dn),
            'Tenant1:T1-CTX2')

    def test_children_concrete_classes(self):
        """
        Test ConcreteArpDomain _get_children_concrete_classes returns something list-like
        """
        node_id = '103'
        node = Node(node_id)
        concreteArp = ConcreteArp(node)
        concreteArpDomain = ConcreteArpDomain(concreteArp)
        self.assertTrue(
            isinstance(
                concreteArpDomain._get_children_concrete_classes(),
                list))
        for child in concreteArpDomain._get_children_concrete_classes():
            self.assertFalse(isinstance(child, ConcreteArpEntry))


class TestConcreteArpEntry(unittest.TestCase):
    """
    Test the ConcreteArpEntry class
    """

    def test_create(self):
        """
        ConcreteArpEntry creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteArp = ConcreteArp(node)
        concreteArpDomain = ConcreteArpDomain(concreteArp)
        concreteArpEntry = ConcreteArpEntry(concreteArpDomain)
        self.assertNotEqual(concreteArpEntry, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(
            ConcreteArpEntry._get_parent_class(),
            ConcreteArpDomain)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteArpEntry._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/arp/inst/dom-Tenant-SharedService:Shared_Service/db-ip/adj-[eth1/40.69]-[40.40.41.2]'
        self.assertEquals(ConcreteArpEntry._get_name_from_dn(dn), '[eth1')


class TestConcreteVpc(unittest.TestCase):
    """
    Test the ConcreteVpc class
    """

    def test_create(self):
        """
        ConcreteVpc creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteVpc = ConcreteVpc(node)
        self.assertNotEqual(concreteVpc, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteVpc._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteVpc._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/vpc'
        self.assertEquals(ConcreteVpc._get_name_from_dn(dn), '')

    def test_eq(self):
        """
        Test ConcreteVpc __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteVpc = ConcreteVpc(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteVpc2 = ConcreteVpc(node2)
        self.assertEqual(concreteVpc, concreteVpc2)

    def test_get_table(self):
        """
        Test ConcreteVpc create table function
        """
        node1 = Node('103')
        node2 = Node('102')
        concreteVpc1 = ConcreteVpc(node1)
        concreteVpc2 = ConcreteVpc(node2)
        concreteVpc1.attr['admin_state'] = 'enabled'
        concreteVpc2.attr['admin_state'] = 'enabled'
        concreteVpc1.attr['dom_present'] = True
        concreteVpc2.attr['dom_present'] = True
        concreteVpcs = [concreteVpc1, concreteVpc2]
        self.assertTrue(
            isinstance(
                ConcreteVpc.get_table(concreteVpcs)[0],
                Table))


class TestConcreteVpcIf(unittest.TestCase):
    """
    Test the ConcreteVpcIf class
    """

    def test_create(self):
        """
        ConcreteVpcIf creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteVpc = ConcreteVpc(node)
        concreteVpcIf = ConcreteVpcIf(concreteVpc)
        self.assertNotEqual(concreteVpcIf, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteVpcIf._get_parent_class(), ConcreteVpc)

    def test_get_table(self):
        """
        Test ConcreteVpcIf create table function
        """
        node1 = Node('103')
        node2 = Node('102')
        concreteVpc1 = ConcreteVpc(node1)
        concreteVpc2 = ConcreteVpc(node2)
        concreteVpcIf1 = ConcreteVpcIf(concreteVpc1)
        concreteVpcIf2 = ConcreteVpcIf(concreteVpc2)

        concreteVpcIfs = [concreteVpcIf1, concreteVpcIf2]
        self.assertTrue(
            isinstance(
                ConcreteVpcIf.get_table(concreteVpcIfs)[0],
                Table))


class TestConcreteContext(unittest.TestCase):
    """
    Test the ConcreteContext class
    """

    def test_create(self):
        """
        ConcreteContext creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteContext = ConcreteContext(node)
        self.assertNotEqual(concreteContext, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteContext._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteContext._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-202/sys/ctx-[vxlan-2129920]'
        self.assertEquals(
            ConcreteContext._get_name_from_dn(dn),
            '[vxlan-2129920]')

    def test_eq(self):
        """
        Test ConcreteContext __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteContext = ConcreteContext(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteContext2 = ConcreteContext(node2)
        self.assertEqual(concreteContext, concreteContext2)

    def test_get_table(self):
        """
        Test ConcreteContext create table function
        """
        node1 = Node('103')
        node2 = Node('102')
        concreteContext1 = ConcreteContext(node1)
        concreteContext2 = ConcreteContext(node2)
        concreteContext1.attr['tenant'] = 'tenant1'
        concreteContext1.attr['context'] = 'context1'
        concreteContext2.attr['tenant'] = 'tenant2'
        concreteContext2.attr['context'] = 'context2'
        concreteContexts = [concreteContext1, concreteContext2]
        self.assertTrue(
            isinstance(
                ConcreteContext.get_table(concreteContexts)[0],
                Table))


class TestConcreteSVI(unittest.TestCase):
    """
    Test the ConcreteSVI class
    """

    def test_create(self):
        """
        ConcreteSVI creation
        """
        node_id = '102'
        node = Node(node_id)
        concreteBd = ConcreteBD(node)
        concreteSVI = ConcreteSVI(concreteBd)
        self.assertNotEqual(concreteSVI, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteSVI._get_parent_class(), ConcreteBD)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteSVI._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-102/sys/ctx-[vxlan-2293760]/bd-[vxlan-14811120]/svi-[vlan14]'
        self.assertEquals(ConcreteSVI._get_name_from_dn(dn), '[vlan14]')

    def test_eq(self):
        """
        Test ConcreteSVI __eq__ function
        """
        node_id = '102'
        node = Node(node_id)
        concreteBd = ConcreteBD(node)
        concreteSVI = ConcreteSVI(concreteBd)
        node_id = '102'
        node = Node(node_id)
        concreteBd1 = ConcreteBD(node)
        concreteSVI1 = ConcreteSVI(concreteBd1)
        self.assertEqual(concreteSVI, concreteSVI1)

    def test_get_table(self):
        """
        Test ConcreteSVI create table function
        """
        node_id = '102'
        node = Node(node_id)
        concreteBd = ConcreteBD(node)
        concreteSVI = ConcreteSVI(concreteBd)
        node_id = '102'
        node = Node(node_id)
        concreteBd1 = ConcreteBD(node)
        concreteSVI1 = ConcreteSVI(concreteBd1)
        concreteSVIs = [concreteSVI, concreteSVI1]
        self.assertTrue(
            isinstance(
                ConcreteSVI.get_table(concreteSVIs)[0],
                Table))


class TestConcreteLoopback(unittest.TestCase):
    """
    Test the ConcreteLoopback class
    """

    def test_create(self):
        """
        ConcreteLoopback creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteLoopback = ConcreteLoopback(node)
        self.assertNotEqual(concreteLoopback, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteLoopback._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteLoopback._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/ctx-[vxlan-2916352]/lb-[lo5]'
        self.assertEquals(ConcreteLoopback._get_name_from_dn(dn), '[lo5]')

    def test_eq(self):
        """
        Test ConcreteLoopback __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteLoopback = ConcreteLoopback(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteLoopback2 = ConcreteLoopback(node2)
        self.assertEqual(concreteLoopback, concreteLoopback2)


class TestConcreteBD(unittest.TestCase):
    """
    Test the ConcreteBD class
    """

    def test_create(self):
        """
        ConcreteBD creation
        """
        node_id = '101'
        node = Node(node_id)
        concreteBD = ConcreteBD(node)
        self.assertNotEqual(concreteBD, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteBD._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteBD._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-101/sys/ctx-[vxlan-2686976]/bd-[vxlan-15794151]'
        self.assertEquals(
            ConcreteBD._get_name_from_dn(dn),
            'ctx-[vxlan-2686976]')

    def test_children_concrete_classes(self):
        """
        Test ConcreteBD _get_children_concrete_classes returns something list-like
        """
        node_id = '101'
        node = Node(node_id)
        concreteBD = ConcreteBD(node)
        self.assertTrue(
            isinstance(
                concreteBD._get_children_concrete_classes(),
                list))
        for child in concreteBD._get_children_concrete_classes():
            self.assertFalse(isinstance(child, ConcreteSVI))

    def test_eq(self):
        """
        Test ConcreteBD __eq__ function
        """
        node_id = '101'
        node = Node(node_id)
        concreteBD = ConcreteBD(node)
        node_id2 = '101'
        node2 = Node(node_id2)
        concreteBD2 = ConcreteBD(node2)
        self.assertEqual(concreteBD, concreteBD2)

    def test_get_table(self):
        """
        Test ConcreteBD create table function
        """
        node_id = '102'
        node = Node(node_id)
        concreteBd = ConcreteBD(node)
        node_id = '102'
        node = Node(node_id)
        concreteBd1 = ConcreteBD(node)
        concreteBds = [concreteBd, concreteBd1]
        self.assertTrue(
            isinstance(
                ConcreteBD.get_table(concreteBds)[0],
                Table))


class TestConcreteAccCtrlRule(unittest.TestCase):
    """
    Test the ConcreteAccCtrlRule class
    """

    def test_create(self):
        """
        ConcreteAccCtrlRule creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteAccCtrlRule = ConcreteAccCtrlRule(node)
        self.assertNotEqual(concreteAccCtrlRule, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteAccCtrlRule._get_parent_class(), Node)

    def test_get_table(self):
        """
        Test ConcreteAccCtrlRule create table function
        """
        node_id1 = '102'
        node1 = Node(node_id1)
        concreteAccCtrlRule1 = ConcreteAccCtrlRule(node1)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteAccCtrlRule2 = ConcreteAccCtrlRule(node2)
        concreteAccCtrlRules = [concreteAccCtrlRule1, concreteAccCtrlRule2]
        self.assertTrue(
            isinstance(
                ConcreteAccCtrlRule.get_table(concreteAccCtrlRules)[0],
                Table))


class TestConcreteFilter(unittest.TestCase):
    """
    Test the ConcreteFilter class
    """

    def test_create(self):
        """
        ConcreteFilter creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteFilter = ConcreteFilter(node)
        self.assertNotEqual(concreteFilter, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteFilter._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteFilter._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-102/sys/actrl/filt-implicit'
        self.assertEquals(ConcreteFilter._get_name_from_dn(dn), 'implicit')

    def test_eq(self):
        """
        Test ConcreteFilter __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteFilter = ConcreteFilter(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteFilter2 = ConcreteFilter(node2)
        self.assertEqual(concreteFilter, concreteFilter2)


class TestConcreteFilterEntry(unittest.TestCase):
    """
    Test the ConcreteFilterEntry class
    """

    def test_create(self):
        """
        ConcreteFilterEntry creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteFilter = ConcreteFilter(node)
        concreteFilterEntry = ConcreteFilterEntry(concreteFilter)
        self.assertNotEqual(concreteFilterEntry, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(
            ConcreteFilterEntry._get_parent_class(),
            ConcreteFilter)

    def test_eq(self):
        """
        Test ConcreteFilterEntry __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteFilter = ConcreteFilter(node)
        concreteFilterEntry = ConcreteFilterEntry(concreteFilter)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteFilter2 = ConcreteFilter(node2)
        concreteFilterEntry2 = ConcreteFilterEntry(concreteFilter2)
        self.assertEqual(concreteFilterEntry, concreteFilterEntry2)


class TestConcreteEp(unittest.TestCase):
    """
    Test the ConcreteEp class
    """

    def test_create(self):
        """
        ConcreteEp creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteEp = ConcreteEp(node)
        self.assertNotEqual(concreteEp, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteEp._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteEp._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/ctx-[vxlan-2293760]/bd-[vxlan-15597456]/db-ep/ip-[100.100.101.1]'
        self.assertEquals(ConcreteEp._get_name_from_dn(dn), '[vxlan-2293760]')

    def test_eq(self):
        """
        Test ConcreteEp __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteEp = ConcreteEp(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteEp2 = ConcreteEp(node2)
        self.assertEqual(concreteEp, concreteEp2)

    def test_get_table(self):
        """
        Test ConcreteEp create table function
        """
        node1 = Node('103')
        node2 = Node('102')
        concreteEp1 = ConcreteEp(node1)
        concreteEp2 = ConcreteEp(node2)
        concreteEp1.attr['tenant'] = 'tenant1'
        concreteEp1.attr['context'] = 'context1'
        concreteEp1.attr['bridge_domain'] = 'bridge_domain1'
        concreteEp2.attr['tenant'] = 'tenant2'
        concreteEp2.attr['context'] = 'context2'
        concreteEp2.attr['bridge_domain'] = 'bridge_domain2'
        concreteEps = [concreteEp1, concreteEp2]
        self.assertTrue(
            isinstance(
                ConcreteEp.get_table(concreteEps)[0],
                Table))


class TestConcretePortChannel(unittest.TestCase):
    """
    Test the ConcretePortChannel class
    """

    def test_create(self):
        """
        ConcretePortChannel creation
        """
        node_id = '103'
        node = Node(node_id)
        concretePortChannel = ConcretePortChannel(node)
        self.assertNotEqual(concretePortChannel, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcretePortChannel._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcretePortChannel._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-101/sys/aggr-[po3]'
        self.assertEquals(ConcretePortChannel._get_name_from_dn(dn), '[po3]')

    def test_eq(self):
        """
        Test ConcretePortChannel __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concretePortChannel = ConcretePortChannel(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concretePortChannel2 = ConcretePortChannel(node2)
        self.assertEqual(concretePortChannel, concretePortChannel2)

    def test_get_table(self):
        """
        Test ConcretePortChannel create table function
        """
        node1 = Node('103')
        node2 = Node('102')
        concretePortChannel1 = ConcretePortChannel(node1)
        concretePortChannel2 = ConcretePortChannel(node2)
        concretePortChannel1.attr['id'] = '1'
        concretePortChannel2.attr['id'] = '2'
        concretePortChannels = [concretePortChannel1, concretePortChannel2]
        self.assertTrue(
            isinstance(
                ConcretePortChannel.get_table(concretePortChannels)[0],
                Table))


class TestConcreteTunnel(unittest.TestCase):
    """
    Test the ConcreteTunnel class
    """

    def test_create(self):
        """
        ConcreteTunnel creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteOverlay = ConcreteOverlay(node)
        concreteTunnel = ConcreteTunnel(concreteOverlay)
        self.assertNotEqual(concreteTunnel, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteTunnel._get_parent_class(), ConcreteOverlay)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteTunnel._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-201/sys/tunnel-[tunnel1]'
        self.assertEquals(ConcreteTunnel._get_name_from_dn(dn), '[tunnel1]')

    def test_children_concrete_classes(self):
        """
        Test ConcreteTunnel _get_children_concrete_classes returns something list-like
        """
        node_id = '103'
        node = Node(node_id)
        concreteOverlay = ConcreteOverlay(node)
        concreteTunnel = ConcreteTunnel(concreteOverlay)
        self.assertTrue(
            isinstance(
                concreteTunnel._get_children_concrete_classes(),
                list))
        self.assertTrue(
            len(concreteTunnel._get_children_concrete_classes()) == 0)

    def test_get_table(self):
        """
        Test ConcreteTunnel create table function
        """
        node_id = '103'
        node = Node(node_id)
        concreteOverlay = ConcreteOverlay(node)
        concreteTunnel1 = ConcreteTunnel(concreteOverlay)
        node_id = '103'
        node = Node(node_id)
        concreteOverlay = ConcreteOverlay(node)
        concreteTunnel2 = ConcreteTunnel(concreteOverlay)
        concreteTunnels = [concreteTunnel1, concreteTunnel2]
        self.assertTrue(
            isinstance(
                ConcreteTunnel.get_table(concreteTunnels)[0],
                Table))


class TestConcreteOverlay(unittest.TestCase):
    """
    Test the ConcreteOverlay class
    """

    def test_create(self):
        """
        ConcreteOverlay creation
        """
        node_id = '201'
        node = Node(node_id)
        concreteOverlay = ConcreteOverlay(node)
        self.assertNotEqual(concreteOverlay, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteOverlay._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteOverlay._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-201/overlay'
        self.assertEquals(ConcreteOverlay._get_name_from_dn(dn), '')

    def test_children_concrete_classes(self):
        """
        Test ConcreteOverlay _get_children_concrete_classes returns something list-like
        """
        node_id = '103'
        node = Node(node_id)
        concreteOverlay = ConcreteOverlay(node)
        self.assertTrue(
            isinstance(
                concreteOverlay._get_children_concrete_classes(),
                list))
        for child in concreteOverlay._get_children_concrete_classes():
            self.assertFalse(isinstance(child, ConcreteTunnel))

    def test_get_table(self):
        """
        Test ConcreteOverlay create table function
        """
        node_id = '103'
        node = Node(node_id)
        concreteOverlay1 = ConcreteOverlay(node)
        node_id = '103'
        node = Node(node_id)
        concreteOverlay2 = ConcreteOverlay(node)
        concreteOverlays = [concreteOverlay1, concreteOverlay2]
        self.assertTrue(
            isinstance(
                ConcreteOverlay.get_table(concreteOverlays)[0],
                Table))


class TestConcreteCdp(unittest.TestCase):
    """
    Test the ConcreteCdp class
    """

    def test_create(self):
        """
        ConcreteCdp creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteCdp = ConcreteCdp(node)
        self.assertNotEqual(concreteCdp, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteCdp._get_parent_class(), Node)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteCdp._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/cdp/inst'
        self.assertEquals(ConcreteCdp._get_name_from_dn(dn), '')

    def test_children_concrete_classes(self):
        """
        Test ConcreteCdp _get_children_concrete_classes returns something list-like
        """
        node_id = '103'
        node = Node(node_id)
        concreteCdp = ConcreteCdp(node)
        self.assertTrue(
            isinstance(
                concreteCdp._get_children_concrete_classes(),
                list))
        for child in concreteCdp._get_children_concrete_classes():
            self.assertFalse(isinstance(child, ConcreteCdpIf))

    def test_eq(self):
        """
        Test ConcreteCdp __eq__ function
        """
        node_id = '103'
        node = Node(node_id)
        concreteCdp = ConcreteCdp(node)
        node_id2 = '102'
        node2 = Node(node_id2)
        concreteCdp2 = ConcreteCdp(node2)
        self.assertEqual(concreteCdp, concreteCdp2)

    def test_get_table(self):
        """
        Test ConcreteCdp create table function
        """
        node_id1 = '103'
        node1 = Node(node_id1)
        concreteCdp1 = ConcreteCdp(node1)
        concreteCdpIf1 = ConcreteCdpIf(concreteCdp1)
        concreteCdp1.add_child(concreteCdpIf1)
        node_id2 = '103'
        node2 = Node(node_id2)
        concreteCdp2 = ConcreteCdp(node2)
        concreteCdpIf2 = ConcreteCdpIf(concreteCdp2)
        concreteCdp2.add_child(concreteCdpIf2)
        concreteCdps = [concreteCdp1, concreteCdp2]
        self.assertTrue(
            isinstance(
                ConcreteCdp.get_table(concreteCdps)[0],
                Table))


class TestConcreteCdpIf(unittest.TestCase):
    """
    Test the ConcreteCdpIf class
    """

    def test_create(self):
        """
        ConcreteCdpIf creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteCdp = ConcreteCdp(node)
        concreteCdpIf = ConcreteCdpIf(concreteCdp)
        self.assertNotEqual(concreteCdpIf, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteCdpIf._get_parent_class(), ConcreteCdp)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteCdpIf._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/cdp/inst/if-[eth1/17]'
        self.assertEquals(ConcreteCdpIf._get_name_from_dn(dn), '[eth1')

    def test_children_concrete_classes(self):
        """
        Test ConcreteCdpIf _get_children_concrete_classes returns something list-like
        """
        node_id = '103'
        node = Node(node_id)
        concreteCdp = ConcreteCdp(node)
        concreteCdpIf = ConcreteCdpIf(concreteCdp)
        self.assertTrue(
            isinstance(
                concreteCdpIf._get_children_concrete_classes(),
                list))
        for child in concreteCdpIf._get_children_concrete_classes():
            self.assertFalse(isinstance(child, ConcreteCdpAdjEp))


class TestConcreteCdpAdjEp(unittest.TestCase):
    """
    Test the ConcreteCdpAdjEp class
    """

    def test_create(self):
        """
        ConcreteCdpAdjEp creation
        """
        node_id = '103'
        node = Node(node_id)
        concreteCdp = ConcreteCdp(node)
        concreteCdpIf = ConcreteCdpIf(concreteCdp)
        concreteCdpAdjEp = ConcreteCdpAdjEp(concreteCdpIf)
        self.assertNotEqual(concreteCdpAdjEp, None)

    def test_get_parent_class(self):
        """
        Ensure class has the correct parent class
        """
        self.assertEquals(ConcreteCdpAdjEp._get_parent_class(), ConcreteCdpIf)

    def test_get_name_from_dn(self):
        """
        Test that ConcreteCdpAdjEp._get_name_from_dn returns the name
        derived from the dn provided
        """
        dn = 'topology/pod-1/node-103/sys/cdp/inst/if-[eth1/17]/adj-1'
        self.assertEquals(ConcreteCdpAdjEp._get_name_from_dn(dn), '1')

    def test_children_concrete_classes(self):
        """
        Test ConcreteCdpAdjEp _get_children_concrete_classes returns something list-like
        """
        node_id = '103'
        node = Node(node_id)
        concreteCdp = ConcreteCdp(node)
        concreteCdpIf = ConcreteCdpIf(concreteCdp)
        concreteCdpAdjEp = ConcreteCdpAdjEp(concreteCdpIf)
        self.assertTrue(
            isinstance(
                concreteCdpAdjEp._get_children_concrete_classes(),
                list))
        self.assertTrue(
            len(concreteCdpAdjEp._get_children_concrete_classes()) == 0)

if __name__ == '__main__':
    offline = unittest.TestSuite()
    offline.addTest(unittest.makeSuite(TestConcreteArp))
    offline.addTest(unittest.makeSuite(TestConcreteArpDomain))
    unittest.main()
