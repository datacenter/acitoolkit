from acisession import Session
from credentials import *
from acitoolkit import *
from aciphysobject import *
import sys
import unittest

class TestPod(unittest.TestCase) :
    def test_pod_id(self) :
        pod = Pod('1')
        self.assertEqual(pod.pod, '1')
    def test_pod_name(self) :
        pod_id = '1'
        pod = Pod(pod_id)
        self.assertEqual(pod.name, 'pod-'+pod_id)
    def test_pod_type(self) :
        pod = Pod('1')
        self.assertEqual(pod.type,'pod')
    def test_create_invalid(self) :
        self.assertRaises(TypeError, Pod, '1', '2')
    def test_pod_invalid_session(self) :
        session = 'bogus'
        self.assertRaises(TypeError, Pod.get, session)
    def test_pod_equal(self):
        pod_id = '1'
        pod1 = Pod(pod_id)

        #check different IDs
        pod_id = '2'
        pod2 = Pod(pod_id)
        self.assertNotEqual(pod1, pod2)

        #check same 
        pod_id = '1'
        pod2 = Pod(pod_id)
        self.assertEqual(pod1, pod2)

        #check differnt types
        pod2 = Node(pod_id, '2', 'Leaf1')
        self.assertNotEqual(pod1, pod2)
    def test_pod_name(self) :
        pod_id = '2'
        pod = Pod(pod_id)
        self.assertEqual(str(pod),'pod-'+pod_id)

    def test_pod_get_url(self) :
        pod_id = '3'
        pod = Pod(pod_id)
        self.assertEqual(pod.get_url(),None)
        
    def test_pod_get_json(self) :
        pod_id = '3'
        pod = Pod(pod_id)
        self.assertEqual(pod.get_json(),None)
        
class TestNode(unittest.TestCase) :
    def test_node_id(self) :
        node = Node('1','2', 'Leaf1')
        self.assertEqual(node.pod, '1')
        self.assertEqual(node.node, '2')
        self.assertEqual(node.name, 'Leaf1')
    def test_node_bad_name(self) :
        node_name = 1
        self.assertRaises(TypeError, Node, '1', '2', node_name)

    def test_node_role(self) :
        node_name = 'Leaf1'
        node_pod = '1'
        node_node = '3'
        node_role = 'switch'
        node = Node(node_pod, node_node, node_name, node_role)
        self.assertEqual(node.role, node_role)
        node_role = 'controller'
        node = Node(node_pod, node_node, node_name, node_role)
        self.assertEqual(node.role, node_role)
        node_role = 'bogus'
        self.assertRaises(ValueError, Node, node_pod, node_node, node_name, node_role)
        
    def test_node_type(self) :
        node = Node('1','2', 'Leaf1')
        self.assertEqual(node.type,'node')
        
    def test_node_parent(self) :
        pod_id = '1'
        pod1 = Pod(pod_id)
        node = Node('1','2','Spine1','switch',pod1)
        self.assertEqual(pod1, node.get_parent())
        
    def test_create_invalid(self) :
        self.assertRaises(TypeError, Node, '1', '2','Leaf1','switch','1')
        
    def test_invalid_session_populate_children(self) :
        pod1 = Pod('1')
        node = Node('1','2','Spine1','switch',pod1)
        self.assertRaises(TypeError, node.populate_children)

    def test_get(self) :
        pod1 = Pod('1')
        session = 'bogus'
        self.assertRaises(TypeError, Node.get, session)
        

    def test_node_equal(self) :
        node_name = 'Leaf1'
        node_pod = '1'
        node_node = '3'
        node_role = 'switch'
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
        node_role = 'switch'
        node2 = Node(node_pod, node_node, node_name, node_role)
        self.assertEqual(node1, node2)

        node2 = Pod(node_pod)
        self.assertNotEqual(node1, node2)

class TestModule() :
    @staticmethod
    def test_module(self, mod_class, modNamePrefix, modType) :
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        node = Node(mod_pod, mod_node, 'Spine2', 'switch')
        mod = mod_class(mod_pod, mod_node, mod_slot)
        name = modNamePrefix+'-'+'/'.join([mod_pod, mod_node, mod_slot])

        self.assertNotEqual(mod, node)
        self.assertEqual(mod.pod, mod_pod)
        self.assertEqual(mod.node, mod_node)
        self.assertEqual(mod.slot, mod_slot)
        self.assertEqual(mod.get_parent(), None)
        self.assertEqual(mod.type, modType)
        self.assertEqual(mod.name, name)
        self.assertEqual(str(mod), name)
        self.assertEqual(mod.session, None)

    @staticmethod
    def test_mod_parent(self,mod_class) :
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        node = Node(mod_pod, mod_node, 'Spine2', 'switch')
        mod1 = mod_class(mod_pod, mod_node, mod_slot, node)        
        self.assertEqual(mod1.get_parent(), node)
        self.assertEqual(node.get_children(),[mod1])
        mod2 = mod_class(mod_pod, mod_node, mod_slot, node)        
        self.assertEqual(node.get_children(),[mod2])
        mod_slot = '3'
        mod3 = mod_class(mod_pod, mod_node, mod_slot, node)        
        self.assertEqual(node.get_children(),[mod2, mod3])
        self.assertEqual(node.get_children(mod_class),[mod2, mod3])
        
        # test illegal parent type
        self.assertRaises(TypeError, mod_class,mod_pod, mod_node, mod_slot, mod1)
        
    @staticmethod
    def test_mod_instance(self, mod_class) :
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        mod = mod_class(mod_pod, mod_node, mod_slot)
        self.assertIsInstance(mod, mod_class)

    @staticmethod
    def test_mod_get_json(self, mod_class) :
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        mod = mod_class(mod_pod, mod_node, mod_slot)
        self.assertEqual(mod.get_json(), None)
        
    @staticmethod
    def test_mod_get_url(self, mod_class) :
        mod_pod = '1'
        mod_node = '5'
        mod_slot = '2'
        mod = mod_class(mod_pod, mod_node, mod_slot)
        self.assertEqual(mod.get_url(), None)
        
class TestFan(unittest.TestCase) :
    def test_fan(self) :
        mod_class = Fantray
        TestModule.test_module(self,mod_class, 'Fan', 'fantray')
        TestModule.test_mod_parent(self, mod_class)
        TestModule.test_mod_instance(self, mod_class)
        TestModule.test_mod_get_url(self, mod_class)
        TestModule.test_mod_get_json(self, mod_class)
        
class TestPowerSupply(unittest.TestCase) :
    def test_fan(self) :
        mod_class = Powersupply
        TestModule.test_module(self,mod_class, 'PS', 'powersupply')
        TestModule.test_mod_parent(self, mod_class)
        TestModule.test_mod_instance(self, mod_class)
        TestModule.test_mod_get_url(self, mod_class)
        TestModule.test_mod_get_json(self, mod_class)

class TestLinecard(unittest.TestCase) :
    def test_fan(self) :
        mod_class = Linecard
        TestModule.test_module(self,mod_class, 'Lc', 'linecard')
        TestModule.test_mod_parent(self, mod_class)
        TestModule.test_mod_instance(self, mod_class)
        TestModule.test_mod_get_url(self, mod_class)
        TestModule.test_mod_get_json(self, mod_class)

class TestSupervisor(unittest.TestCase) :
    def test_fan(self) :
        mod_class = Supervisorcard
        TestModule.test_module(self,mod_class, 'SupC', 'supervisor')
        TestModule.test_mod_parent(self, mod_class)
        TestModule.test_mod_instance(self, mod_class)
        TestModule.test_mod_get_url(self, mod_class)
        TestModule.test_mod_get_json(self, mod_class)

class TestSystemcontroller(unittest.TestCase) :
    def test_fan(self) :
        mod_class = Systemcontroller
        TestModule.test_module(self,mod_class, 'SysC', 'systemctrlcard')
        TestModule.test_mod_parent(self, mod_class)
        TestModule.test_mod_instance(self, mod_class)
        TestModule.test_mod_get_url(self, mod_class)
        TestModule.test_mod_get_json(self, mod_class)

        
    
#class TestFan(unittest.TestCase) :
#    def test_fan(self) :
#        fan_pod = '1'
#        fan_node = '5'
#        fan_slot = '2'
#        node = Node(fan_pod, fan_node, 'Spine2', 'switch')
#        fan = mod_class(fan_pod, fan_node, fan_slot)
#        name = 'Fan-'+'/'.join([fan_pod, fan_node, fan_slot])
#
#        
#        self.assertEqual(fan.pod, fan_pod)
#        self.assertEqual(fan.node, fan_node)
#        self.assertEqual(fan.slot, fan_slot)
#        self.assertEqual(fan.get_parent(), None)
#        self.assertEqual(fan.type, 'fantray')
#        self.assertEqual(fan.name, name)
#        self.assertEqual(fan.session, None)
#
#    def test_fan_parent(self) :
#        fan_pod = '1'
#        fan_node = '5'
#        fan_slot = '2'
#        node = Node(fan_pod, fan_node, 'Spine2', 'switch')
#        fan1 = mod_class(fan_pod, fan_node, fan_slot, node)        
#        self.assertEqual(fan1.get_parent(), node)
#        self.assertEqual(node.get_children(),[fan1])
#        fan2 = mod_class(fan_pod, fan_node, fan_slot, node)        
#        self.assertEqual(node.get_children(),[fan2])
#        fan_slot = '3'
#        fan3 = mod_class(fan_pod, fan_node, fan_slot, node)        
#        self.assertEqual(node.get_children(),[fan2, fan3])
#        self.assertEqual(node.get_children(mod_class),[fan2, fan3])
#        
#        # test illegal parent type
#        self.assertRaises(TypeError, mod_class,fan_pod, fan_node, fan_slot, fan1)        
    

#check_json()
#show_inventory()
#check_exists()
if __name__ == '__main__':
    unittest.main()
