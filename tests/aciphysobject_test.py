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
from acitoolkit.acisession import Session
try:
    from credentials import *
except ImportError:
    URL = ''
    LOGIN = ''
    PASSWORD = ''
from acitoolkit.acitoolkit import *
from acitoolkit.aciphysobject import *
import sys
import unittest


class TestPod(unittest.TestCase):
    def test_pod_id(self):
        pod = Pod('1')
        self.assertEqual(pod.pod, '1')

    def test_pod_name(self):
        pod_id = '1'
        pod = Pod(pod_id)
        self.assertEqual(pod.get_name(), 'pod-' + pod_id)
        self.assertEqual(pod.get_pod(), '1')

    def test_pod_type(self):
        pod = Pod('1')
        self.assertEqual(pod.get_type(), 'pod')

    def test_create_invalid(self):
        self.assertRaises(TypeError, Pod, '1', '2')

    def test_pod_invalid_session(self):
        session = 'bogus'
        self.assertRaises(TypeError, Pod.get, session)

    def test_pod_equal(self):
        pod_id = '1'
        pod1 = Pod(pod_id)

        # check different IDs
        pod_id = '2'
        pod2 = Pod(pod_id)
        self.assertNotEqual(pod1, pod2)

        # check same
        pod_id = '1'
        pod2 = Pod(pod_id)
        self.assertEqual(pod1, pod2)

        # check different types
        pod2 = Node(pod_id, '2', 'Leaf1', role='leaf')
        self.assertNotEqual(pod1, pod2)

    def test_pod_str_name(self):
        pod_id = '2'
        pod = Pod(pod_id)
        self.assertEqual(str(pod), 'pod-' + pod_id)

    def test_pod_get_url(self):
        pod_id = '3'
        pod = Pod(pod_id)
        self.assertEqual(pod.get_url(), None)

    def test_pod_get_json(self):
        pod_id = '3'
        pod = Pod(pod_id)
        self.assertEqual(pod.get_json(), None)

    def test_pod_parent(self) :
        pod_id = '4'
        attributes = {'type':'pod'}
        self.assertRaises(TypeError, Pod, pod_id, attributes, 'pod-1')
        

class TestNode(unittest.TestCase):
    def test_node_id(self):
        node = Node('1', '2', 'Leaf1', role='leaf')
        self.assertEqual(node.get_pod(), '1')
        self.assertEqual(node.get_node(), '2')
        self.assertEqual(node.get_name(), 'Leaf1')

    def test_node_bad_name(self):
        node_name = 1
        self.assertRaises(TypeError, Node, '1', '2', node_name, 'leaf')

    def test_node_role(self):
        node_name = 'Leaf1'
        node_pod = '1'
        node_node = '3'
        node_role = 'leaf'
        node = Node(node_pod, node_node, node_name, role=node_role)
        self.assertEqual(node.role, node_role)
        node_role = 'controller'
        node = Node(node_pod, node_node, node_name, role=node_role)
        self.assertEqual(node.role, node_role)
        node_role = 'bogus'
        self.assertRaises(ValueError, Node, node_pod, node_node,
                          node_name, node_role)

    def test_node_type(self):
        node = Node('1', '2', 'Leaf1', role='leaf')
        self.assertEqual(node.get_type(), 'node')

    def test_node_model(self) :
        node = Node('1', '2', 'Leaf1', role='leaf')
        self.assertEqual(node.get_chassis_type(), None)
        node.model = 'N9K-C9396PX'
        self.assertEqual(node.get_model(), 'N9K-C9396PX')
        self.assertEqual(node.get_chassis_type(), 'n9k')
        
    def test_node_parent(self):
        pod_id = '1'
        pod1 = Pod(pod_id)
        node = Node('1', '2', 'Spine1', role='leaf', parent=pod1)
        self.assertEqual(pod1, node.get_parent())

    def test_node_bad_parent(self):
        pod_id = '1'
        session = Session(URL, LOGIN, PASSWORD)
        self.assertRaises(TypeError, Node,'1', '2', 'Spine1', role='leaf', parent=pod_id)

    def test_create_invalid(self):
        self.assertRaises(TypeError, Node, '1', '2', 'Leaf1', 'leaf', '1')

    def test_invalid_session_populate_children(self):
        pod1 = Pod('1')
        node = Node('1', '2', 'Spine1', 'spine', pod1)
        self.assertRaises(TypeError, node.populate_children)

    def test_get(self):
        pod1 = Pod('1')
        session = 'bogus'
        self.assertRaises(TypeError, Node.get, session)

    def test_node_get_fabric_state(self) :
        node_name = 'Leaf1'
        node_pod = '1'
        node_node = '3'
        node_role = 'leaf'
        node1 = Node(node_pod, node_node, node_name, node_role)
        

    def test_node_equal(self):
        node_name = 'Leaf1'
        node_pod = '1'
        node_node = '3'
        node_role = 'leaf'
        node1 = Node(node_pod, node_node, node_name, node_role)

        node_name = 'Leaf2'
        node2 = Node(node_pod, node_node, node_name, node_role)
        self.assertNotEqual(node1, node2)
        node_name = 'Leaf1'
        node_pod = '2'
        node2 = Node(node_pod, node_node, node_name, node_role)
        self.assertNotEqual(node1, node2)
        node_pod = '1'
        node_node = '4'
        node2 = Node(node_pod, node_node, node_name, node_role)
        self.assertNotEqual(node1, node2)
        node_node = '3'
        node_role = 'controller'
        node2 = Node(node_pod, node_node, node_name, node_role)
        self.assertNotEqual(node1, node2)
        node_role = 'leaf'
        node2 = Node(node_pod, node_node, node_name, node_role)
        self.assertEqual(node1, node2)

        node2 = Pod(node_pod)
        self.assertNotEqual(node1, node2)


class TestLink(unittest.TestCase):
    def test_parameters(self):
        pod = Pod('1')
        node1 = '2'
        node2 = '3'
        slot1 = '4'
        slot2 = '5'
        port1 = '6'
        port2 = '7'
        link = '101'

        link1 = Link(pod.pod, link, node1, slot1, port1,
                     node2, slot2, port2, pod)
        self.assertEqual(link1.pod, pod.pod)
        self.assertEqual(link1.link, link)
        self.assertEqual(link1.node1, node1)
        self.assertEqual(link1.slot1, slot1)
        self.assertEqual(link1.port1, port1)
        self.assertEqual(link1.node2, node2)
        self.assertEqual(link1.slot2, slot2)
        self.assertEqual(link1.port2, port2)
        self.assertEqual(link1.get_parent(), pod)

        self.assertEqual(link1.get_port_id1(), '1/2/4/6')
        self.assertEqual(link1.get_port_id2(), '1/3/5/7')
        
    def test_link_bad_parent(self) :
        pod = '1'
        node1 = '2'
        node2 = '3'
        slot1 = '4'
        slot2 = '5'
        port1 = '6'
        port2 = '7'
        link = '101'

        self.assertRaises(TypeError,Link,pod, link, node1, slot1, port1,
                     node2, slot2, port2, pod)

    def test_link_get_bad_parent(self) :
        pod = Link
        session = Session(URL, LOGIN, PASSWORD)

        self.assertRaises(TypeError,Link.get,session,pod)
        pod = Pod('1')
        self.assertRaises(TypeError,Link.get,'bad_session',pod)
        
    def test_get_endpoint_objects(self):
        pod_id = '1'
        node1_id = '2'
        node2_id = '3'
        slot1_id = '4'
        slot2_id = '5'
        port1_id = '6'
        port2_id = '7'
        link_id = '101'

        pod = Pod(pod_id)
        node1 = Node(pod_id, node1_id, 'Spine', 'spine', pod)
        node2 = Node(pod_id, node2_id, 'Leaf', 'leaf', pod)
        linecard1 = Linecard(slot1_id, node1)
        linecard2 = Linecard(slot2_id, node2)
        interface1 = Interface(interface_type='eth', pod=pod_id,
                               node=node1_id, module=slot1_id,
                               port=port1_id, parent=linecard1)
        inf = linecard1.get_children()
        interface2 = Interface(interface_type='eth', pod=pod_id,
                               node=node2_id, module=slot2_id,
                               port=port2_id, parent=linecard2)
        link1 = Link(pod_id, link_id, node1_id, slot1_id, port1_id,
                     node2_id, slot2_id, port2_id, pod)
        self.assertEqual(node1, link1.get_node1())
        self.assertEqual(node2, link1.get_node2())
        self.assertEqual(linecard1, link1.get_slot1())
        self.assertEqual(linecard2, link1.get_slot2())
        self.assertEqual(interface1, link1.get_port1())
        self.assertEqual(interface2, link1.get_port2())


class CheckModule():
    @staticmethod
    def check_module(self, mod_class, modNamePrefix, modType):
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        node = Node(mod_pod, mod_node, 'Spine2', 'leaf')
        mod = mod_class(mod_pod, mod_node, mod_slot)
        name = modNamePrefix + '-' + '/'.join([mod_pod, mod_node, mod_slot])

        self.assertNotEqual(mod, node)
        self.assertEqual(mod.get_pod(), mod_pod)
        self.assertEqual(mod.get_node(), mod_node)
        self.assertEqual(mod.get_slot(), mod_slot)
        self.assertEqual(mod.get_parent(), None)
        self.assertEqual(mod.get_type(), modType)
        self.assertEqual(mod.get_name(), name)
        self.assertEqual(str(mod), name)
        self.assertEqual(mod._session, None)

    @staticmethod
    def check_mod_parent(self, mod_class):
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        node = Node(mod_pod, mod_node, 'Spine2', 'spine')
        mod1 = mod_class(mod_pod, mod_node, mod_slot, node)
        self.assertEqual(mod1.get_parent(), node)
        self.assertEqual(node.get_children(), [mod1])
        mod2 = mod_class(mod_pod, mod_node, mod_slot, node)
        self.assertEqual(node.get_children(), [mod2])
        mod_slot = '3'
        mod3 = mod_class(mod_pod, mod_node, mod_slot, node)
        self.assertEqual(node.get_children(), [mod2, mod3])
        self.assertEqual(node.get_children(mod_class), [mod2, mod3])

        # test illegal parent type
        self.assertRaises(TypeError, mod_class, mod_pod, mod_node,
                          mod_slot, mod1)

    @staticmethod
    def check_mod_instance(self, mod_class):
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        mod = mod_class(mod_pod, mod_node, mod_slot)
        self.assertIsInstance(mod, mod_class)

    @staticmethod
    def check_mod_get_json(self, mod_class):
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        mod = mod_class(mod_pod, mod_node, mod_slot)
        self.assertEqual(mod.get_json(), None)

    @staticmethod
    def check_mod_get_url(self, mod_class):
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        mod = mod_class(mod_pod, mod_node, mod_slot)
        self.assertEqual(mod.get_url(), None)


class TestFan(unittest.TestCase):
    def test_fan(self):
        mod_class = Fantray
        CheckModule.check_module(self, mod_class, 'FT', 'fantray')
        CheckModule.check_mod_parent(self, mod_class)
        CheckModule.check_mod_instance(self, mod_class)
        CheckModule.check_mod_get_url(self, mod_class)
        CheckModule.check_mod_get_json(self, mod_class)


class TestPowerSupply(unittest.TestCase):
    def test_powerSupply(self):
        mod_class = Powersupply
        CheckModule.check_module(self, mod_class, 'PS', 'powersupply')
        CheckModule.check_mod_parent(self, mod_class)
        CheckModule.check_mod_instance(self, mod_class)
        CheckModule.check_mod_get_url(self, mod_class)
        CheckModule.check_mod_get_json(self, mod_class)


class TestLinecard(unittest.TestCase):
    def test_lineCard(self):
        mod_class = Linecard
        CheckModule.check_module(self, mod_class, 'Lc', 'linecard')
        CheckModule.check_mod_parent(self, mod_class)
        CheckModule.check_mod_instance(self, mod_class)
        CheckModule.check_mod_get_url(self, mod_class)
        CheckModule.check_mod_get_json(self, mod_class)


class TestSupervisor(unittest.TestCase):
    def test_supervisor(self):
        mod_class = Supervisorcard
        CheckModule.check_module(self, mod_class, 'SupC', 'supervisor')
        CheckModule.check_mod_parent(self, mod_class)
        CheckModule.check_mod_instance(self, mod_class)
        CheckModule.check_mod_get_url(self, mod_class)
        CheckModule.check_mod_get_json(self, mod_class)


class TestSystemcontroller(unittest.TestCase):
    def test_systemController(self):
        mod_class = Systemcontroller
        CheckModule.check_module(self, mod_class, 'SysC', 'systemctrlcard')
        CheckModule.check_mod_parent(self, mod_class)
        CheckModule.check_mod_instance(self, mod_class)
        CheckModule.check_mod_get_url(self, mod_class)
        CheckModule.check_mod_get_json(self, mod_class)
    

class TestExternalNode(unittest.TestCase):
    def test_eNode(self):
        attrib = {'name': 'testEnode', 'role': 'physicalSwitch'}
        node = ENode(attributes=attrib, session=None, parent=None)
        self.assertEqual(node.getName(), 'testEnode')

    def test_eNode_role(self):
        attrib = {'name': 'testEnode', 'role': 'physicalSwitch'}
        node = ENode(attributes=attrib, session=None, parent=None)
        self.assertEqual(node.getRole(), 'physicalSwitch')

        attrib = {'name': 'testEnode', 'role': 'virtualSwitch'}
        node = ENode(attributes=attrib, session=None, parent=None)
        self.assertEqual(node.getRole(), 'virtualSwitch')

        attrib = {'name': 'testEnode'}
        node = ENode(attributes=attrib, session=None, parent=None)
        self.assertEqual(node.getRole(), None)

        attrib = {'name': 'testEnode', 'role': 'leaf'}
        self.assertRaises(ValueError, ENode, attrib)

        self.assertEqual(node.info(),'           name: testEnode\n')

    def test_eNode_parent(self):
        pod = Pod('1')
        attrib = {'name': 'testEnode'}
        node = ENode(attributes=attrib, session=None, parent=pod)
        self.assertEqual(node.getRole(), None)
        self.assertEqual(node._parent, pod)
        children = pod.get_children()
        self.assertEqual(len(children), 1)
        for child in children:
            self.assertEqual(child, node)

        self.assertRaises(TypeError, ENode, attrib, None, 'text')

    def test_eNode_session(self):
        attrib = {'name': 'testEnode'}
        self.assertRaises(TypeError, ENode, attrib, 'text')
        self.assertRaises(TypeError, ENode.get, 'non-session')
        session = Session(URL, LOGIN, PASSWORD)
        node = ENode(attrib, session)
        self.assertEqual(node._session, session)


class TestLiveAPIC(unittest.TestCase):
    def login_to_apic(self):
        """Login to the APIC
           RETURNS:  Instance of class Session
        """
        session = Session(URL, LOGIN, PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)
        return session


class TestLivePod(TestLiveAPIC):
    def get_all_pods(self):
        session = self.login_to_apic()
        pods = Pod.get(session)
        self.assertTrue(len(pods) > 0)
        return pods, session

    def get_spine(self):
        session = self.login_to_apic()
        nodes = Node.get(session)
        for node in nodes:
            if node.get_role() == 'spine' and node.fabricSt == 'active':
                return node, session

    def get_controller(self):
        session = self.login_to_apic()
        nodes = Node.get(session)
        for node in nodes:
            if node.get_role() == 'controller' and node.fabricSt != 'inactive':
                return node, session

    def test_exists_node(self) :
        session = self.login_to_apic()
        nodes = Node.get(session)
        self.assertTrue(Node.exists(session,nodes[0]))
        nodes[0].node = '999'
        self.assertFalse(Node.exists(session,nodes[0]))
        
    def test_get_all_nodes(self):
        pods, session = self.get_all_pods()
        for pod in pods:
            nodes = Node.get(session)
            self.assertTrue(len(nodes) > 0)
            self.assertTrue(pod.get_serial()==None)

    def test_node(self):
        session = self.login_to_apic()
        nodes = Node.get(session)

        for node in nodes:
            self.assertIsInstance(node.get_name(), str)
            self.assertTrue(len(node.get_name()) > 0)

            self.assertEqual(node.get_type(), 'node')

            self.assertIsInstance(node.get_pod(), str)
            self.assertTrue(len(node.get_pod()) > 0)

            self.assertIsInstance(node.get_node(), str)
            self.assertTrue(len(node.get_node()) > 0)

            self.assertIn(node.get_role(), ['controller', 'leaf', 'spine'])
            self.assertIn(node.getFabricSt(), ['active','inactive','unknown'])
            
        pods = Pod.get(session)
        pod = pods[0]
        nodes = Node.get(session, parent=pod)
        self.assertEqual(len(nodes), len(pod.get_children()))
        self.assertEqual(nodes[0].get_parent(), pod)

        
    def test_switch_children(self):
        spine, session = self.get_spine()
        spine.populate_children()
        children = spine.get_children()
        children_types = set()
        for child in children:
            children_types.add(child.get_type())

        self.assertEqual(len(children_types), 4)
        self.assertIn('linecard', children_types)
        self.assertIn('supervisor', children_types)
        self.assertIn('powersupply', children_types)
        self.assertIn('fantray', children_types)

    def test_link_get_for_node(self) :
        session = self.login_to_apic()
        pod = Pod.get(session)[0]
        links = Link.get(session)
        total_links = len(links)
        self.assertTrue(total_links>0)
        self.assertRaises(TypeError, links[0].get_node1)
        self.assertRaises(TypeError, links[0].get_node2)
        self.assertRaises(TypeError, links[0].get_slot1)
        self.assertRaises(TypeError, links[0].get_slot2)
        self.assertRaises(TypeError, links[0].get_port1)
        self.assertRaises(TypeError, links[0].get_port2)
        links = Link.get(session, pod)
        self.assertEqual(len(links), total_links)
        switches = []
        for link in links :
            self.assertEqual(link.get_node1(), None)
            self.assertEqual(link.get_slot1(), None)
            self.assertEqual(link.get_port1(), None)
            self.assertEqual(link.get_node2(), None)
            self.assertEqual(link.get_slot2(), None)
            self.assertEqual(link.get_port2(), None)
            if link.node1 not in switches :
                switches.append(link.node1)
        self.assertTrue(len(switches)>1)
        nodes = Node.get(session)
        spine = None
        for node in nodes:
            if node.get_role() == 'spine' and node.fabricSt == 'active':
                spine = node
                break
        if spine :
            links = Link.get(session,pod,spine.node)
            spine_links = len(links)
            self.assertTrue(spine_links > 0)
            self.assertTrue(spine_links < total_links)
            for link in links :
                self.assertEqual(link.node1, spine.node)
                self.assertIsInstance(str(link), str)
            links = Link.get(session,'1',spine.node)
            self.assertEqual(len(links), spine_links)

            self.assertNotEqual(links[0], links[1])

            
    def test_controller_children(self):
        controller, session = self.get_controller()
        controller.populate_children()
        children = controller.get_children()
        children_types = set()
        for child in children:
            children_types.add(child.get_type())

        self.assertEqual(len(children_types), 3)
        self.assertIn('systemctrlcard', children_types)
        self.assertIn('fantray', children_types)
        self.assertIn('powersupply', children_types)

    def test_linecard(self):
        session = self.login_to_apic()
        linecards = Linecard.get(session)
        for lc in linecards:
            self.assertIsInstance(lc.get_name(), str)
            self.assertTrue(len(lc.get_name()) > 0)

            self.assertEqual(lc.get_type(), 'linecard')

            self.assertIsInstance(lc.get_pod(), str)
            self.assertTrue(len(lc.get_pod()) > 0)

            self.assertIsInstance(lc.get_node(), str)
            self.assertTrue(len(lc.get_node()) > 0)

            self.assertIsInstance(lc.get_slot(), str)
            self.assertTrue(len(lc.get_slot()) > 0)

            self.assertIsInstance(lc.serial, str)
            self.assertIsInstance(lc.model, str)
            self.assertIsInstance(lc.dn, str)
            self.assertIsInstance(lc.descr, str)

    def test_powersupply(self):
        session = self.login_to_apic()
        powersupplies = Powersupply.get(session)
        for ps in powersupplies:
            self.assertIsInstance(ps.get_name(), str)
            self.assertTrue(len(ps.get_name()) > 0)

            self.assertEqual(ps.get_type(), 'powersupply')

            self.assertIsInstance(ps.get_pod(), str)
            self.assertTrue(len(ps.get_pod()) > 0)

            self.assertIsInstance(ps.get_node(), str)
            self.assertTrue(len(ps.get_node()) > 0)

            self.assertIsInstance(ps.get_slot(), str)
            self.assertTrue(len(ps.get_slot()) > 0)

            self.assertIsInstance(ps.serial, str)
            self.assertIsInstance(ps.model, str)
            self.assertIsInstance(ps.dn, str)
            self.assertIsInstance(ps.descr, str)

            self.assertIsInstance(ps.status, str)
            self.assertIsInstance(ps.fan_status, str)
            self.assertIsInstance(ps.voltage_source, str)
            info_string = ps.info()
            self.assertIn('node', info_string)
            self.assertIn('pod', info_string)
            self.assertIn('slot', info_string)
            self.assertIn('serial', info_string)

            self.assertIsInstance(ps.get_serial(), str)
            
    def test_fantray(self):
        session = self.login_to_apic()
        fantrays = Fantray.get(session)
        for ft in fantrays:
            self.assertIsInstance(ft.get_name(), str)

            self.assertEqual(ft.get_type(), 'fantray')

            self.assertIsInstance(ft.get_pod(), str)
            self.assertTrue(len(ft.get_pod()) > 0)

            self.assertIsInstance(ft.get_node(), str)
            self.assertTrue(len(ft.get_node()) > 0)

            self.assertIsInstance(ft.get_slot(), str)
            self.assertTrue(len(ft.get_slot()) > 0)

            self.assertIsInstance(ft.serial, str)
            self.assertIsInstance(ft.model, str)
            self.assertIsInstance(ft.dn, str)
            self.assertIsInstance(ft.descr, str)

            self.assertIsInstance(ft.status, str)

    def test_populate_deep(self):
        session = self.login_to_apic()
        pods = Pod.get(session)
        pod = pods[0]
        pod.populate_children(deep=True)
        nodes = pod.get_children(Node)
        original_num_nodes = len(nodes)
        node_roles = set()
        for node in nodes:
            node_roles.add(node.get_role())
            if node.get_role() == 'spine' and node.fabricSt == 'active':
                spine = node
            if node.get_role() == 'controller' and node.fabricSt != 'inactive':
                controller = node

        self.assertEqual(len(node_roles ^ set(['controller',
                                               'spine', 'leaf'])), 0)
        

        modules = spine.get_children()
        module_types = set()
        for module in modules:
            module_types.add(module.get_type())
            if module.get_type() == 'linecard':
                linecard = module

        self.assertEqual(len(module_types ^ set(['linecard',
                                                 'supervisor',
                                                 'powersupply',
                                                 'fantray'])), 0)

        interfaces = linecard.get_children()
        for interface in interfaces:
            self.assertIsInstance(interface, Interface)
        if linecard.model == 'N9K-X9736PQ':
            self.assertEqual(len(interfaces), 36)

        modules = controller.get_children()
        module_types = set()
        for module in modules:
            module_types.add(module.get_type())
        self.assertEqual(len(module_types ^ set(['systemctrlcard',
                                                 'powersupply',
                                                 'fantray'])), 0)

        links = pod.get_children(Link)
        for link in links:
            self.assertIsInstance(link, Link)
            self.assertIsInstance(link.node1, str)
            self.assertIsInstance(link.node2, str)
            self.assertIsInstance(link.slot1, str)
            self.assertIsInstance(link.slot2, str)
            self.assertIsInstance(link.port1, str)
            self.assertIsInstance(link.port2, str)
            self.assertIsInstance(link.link, str)

        #check that duplicate children are not populated
        pod.populate_children(deep=True)
        nodes = pod.get_children(Node)
        self.assertTrue(len(nodes)==original_num_nodes)
        
    def test_get_external_nodes(self):
        session = self.login_to_apic()
        enodes = ENode.get(session)
        for enode in enodes:

            if enode.getRole() == 'virtualSwitch':
                self.assertIsInstance(enode.attributes.get('dn'), str)
                self.assertIsInstance(enode.attributes.get('status'), str)
                self.assertIsInstance(enode.attributes.get('name'), str)
                self.assertIsInstance(enode.attributes.get('descr'), str)
                self.assertIsInstance(enode.attributes.get('oid'), str)
                self.assertIsInstance(enode.attributes.get('state'), str)
                self.assertIsInstance(enode.attributes.get('fabricSt'), str)
                self.assertIsInstance(enode.attributes.get('role'), str)
                self.assertIsInstance(enode.attributes.get('guid'), str)
                self.assertEqual(enode.attributes.get('type'), 'hv')
            if enode.getRole() == 'physicalSwitch':
                self.assertIsInstance(enode.attributes.get('dn'), str)
                self.assertIsInstance(enode.attributes.get('status'), str)
                self.assertIsInstance(enode.attributes.get('name'), str)
                self.assertIsInstance(enode.attributes.get('descr'), str)
                if enode.attributes.get('macAddress') :
                    self.assertIsInstance(enode.attributes.get('macAddress'), str)
                self.assertIsInstance(enode.attributes.get('state'), str)
                self.assertIsInstance(enode.attributes.get('fabricSt'), str)
                self.assertIsInstance(enode.attributes.get('role'), str)
                self.assertIsInstance(enode.attributes.get('operIssues'), str)
                if enode.attributes.get('ipAddress') :
                    self.assertIsInstance(enode.attributes.get('ipAddress'), str)
                self.assertIsInstance(enode.attributes.get('id'), str)
                self.assertEqual(enode.attributes.get('pod'), None)
            self.assertIn(enode.attributes.get('role'), ['physicalSwitch',
                                                         'virtualSwitch'])


class TestFind(unittest.TestCase):
    def test_find(self):
        pod_id = '1'
        node1_id = '2'
        node2_id = '3'
        slot1_id = '4'
        slot2_id = '5'
        port1_id = '6'
        port2_id = '7'
        link_id = '101'

        pod = Pod(pod_id)
        node1 = Node(pod_id, node1_id, 'Spine', 'spine', pod)
        node2 = Node(pod_id, node2_id, 'Leaf', 'leaf', pod)
        linecard1 = Linecard(slot1_id, node1)
        linecard2 = Linecard(slot2_id, node2)
        linecard1.serial = 'SerialNumber1'
        linecard2.serial = 'SerialNumber2'
        interface1 = Interface(interface_type='eth', pod=pod_id,
                               node=node1_id, module=slot1_id,
                               port=port1_id, parent=linecard1)
        inf = linecard1.get_children()
        interface2 = Interface(interface_type='eth', pod=pod_id,
                               node=node2_id, module=slot2_id,
                               port=port2_id, parent=linecard2)
        link1 = Link(pod_id, link_id, node1_id, slot1_id, port1_id,
                     node2_id, slot2_id, port2_id, pod)

        so = Search()
        so.node = node2_id
        results = pod.find(so)
        self.assertIn(node2, results)
        self.assertIn(linecard2, results)
        self.assertIn(interface2, results)
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.node, node2_id)

        so = Search()
        so.serial = 'SerialNumber1'
        results = pod.find(so)
        self.assertIn(linecard1, results)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].serial, 'SerialNumber1')


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

if __name__ == '__main__':
    offline = unittest.TestSuite()

    offline.addTest(unittest.makeSuite(TestPod))
    offline.addTest(unittest.makeSuite(TestNode))
    offline.addTest(unittest.makeSuite(TestLink))
    offline.addTest(unittest.makeSuite(TestFan))
    offline.addTest(unittest.makeSuite(TestPowerSupply))
    offline.addTest(unittest.makeSuite(TestLinecard))
    offline.addTest(unittest.makeSuite(TestSupervisor))
    offline.addTest(unittest.makeSuite(TestSystemcontroller))
    offline.addTest(unittest.makeSuite(TestExternalNode))
    offline.addTest(unittest.makeSuite(TestFind))
    offline.addTest(unittest.makeSuite(TestInterface))

    live = unittest.TestSuite()
    live.addTest(unittest.makeSuite(TestLiveAPIC))
    live.addTest(unittest.makeSuite(TestLivePod))

    full = unittest.TestSuite([live, offline])

    unittest.main(defaultTest='offline')
