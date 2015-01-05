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
from acitoolkit.acisession import Session
from credentials import *
from acitoolkit.acitoolkit import *
from acitoolkit.aciphysobject import *
import sys
import unittest
import cableplan
import os
LIVE_TEST = True

class Test_ParseXML(unittest.TestCase) :
    def get_temporary_filename(self) :
        fname_base = 'temp_cable_plan'
        fname_uniquifier = ''
        fname_suffix = '.xml'
        uniquifier = 0
        while(os.path.isfile(fname_base+fname_uniquifier+fname_suffix)) :
            fname_uniquifier = str(uniquifier)
            uniquifier += 1
        return fname_base+fname_uniquifier+fname_suffix
    
    def remove_file(self, fname) :
        os.remove(fname)
    def get_expected_xml(self) :
        expected_xml = ['<?xml version="1.0" encoding="UTF-8"?>\n',
                        '<?created by cableplan.py?>\n',
                        '<CISCO_NETWORK_TYPES version="1.0" xmlns="http://www.cisco.com/cableplan/Schema2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.cisco.com/cableplan/Schema2 nxos-cable-plan-schema.xsd">\n',
                        '   <DATA_CENTER networkLocation="san-jose" idFormat="hostname">\n',
                        '      <CHASSIS_INFO sourceChassis="Spine1" type="n9k">\n',
                        '         <LINK_INFO sourcePort="Eth1/1" destChassis="Leaf1" destPort="Eth1/1"/>\n',
                        '         <LINK_INFO sourcePort="Eth1/2, Eth1/3" destChassis="Leaf1" destPort="Eth1/2"/>\n',
                        '         <LINK_INFO sourcePort="Eth2/3 - Eth2/5" destChassis="Leaf2" destPort="Eth1/1"/>\n',
                        '         <LINK_INFO sourcePort="Eth2/3 - Eth2/5" destChassis="Leaf3"/>\n',
                        '      </CHASSIS_INFO>\n',
                        '      <CHASSIS_INFO sourceChassis="Spine2" type="n9k">\n',
                        '         <LINK_INFO destChassis="Leaf1" destPort="Eth1/2 - Eth1/9" minPorts="3"/>\n',
                        '         <LINK_INFO sourcePort="Eth1/2" destChassis="Leaf2" destPort="Eth1/2 - Eth1/4" maxPorts="2"/>\n',
                        '         <LINK_INFO sourcePort="Eth2/3, Eth2/4, Eth4/4" destChassis="Leaf3" destPort="Eth1/2" minPorts="1" maxPorts="5"/>\n',
                        '      </CHASSIS_INFO>\n',
                        '   </DATA_CENTER>\n',
                        '</CISCO_NETWORK_TYPES>\n']
        return expected_xml
    
    def initXML(self) :
        expected_xml = self.get_expected_xml()
        fname = self.get_temporary_filename()
        f = open(fname, 'w')
        for index in range(len(expected_xml)) :
            f.write(expected_xml[index])
        f.close()
        return fname

    def test_cisconetworktypes(self) :
        fName = self.initXML()
        cp = cableplan.CABLEPLAN.get(fName)
        self.assertEqual(cp.version, '1.0')
        self.assertEqual(cp.schemaLocation, 'http://www.cisco.com/cableplan/Schema2 nxos-cable-plan-schema.xsd')
        self.remove_file(fName)
        
    def test_datacenter(self) :
        fName = self.initXML()
        cp = cableplan.CABLEPLAN.get(fName)
        self.assertEqual(cp.networkLocation, 'san-jose')
        self.assertEqual(cp.idFormat,'hostname')
        self.remove_file(fName)

    def test_chassisinfo(self) :
        fName = self.initXML()
        cp = cableplan.CABLEPLAN.get(fName)
        switch = cp.get_switch('Spine1')
        self.assertEqual(switch.name, 'Spine1')
        self.assertEqual(switch.chassis_type,'n9k')
        self.assertEqual(switch.spine, True)

        switch = cp.get_switch('Spine2')
        self.assertEqual(switch.name, 'Spine2')
        self.assertEqual(switch.chassis_type,'n9k')
        self.assertEqual(switch.spine, True)

        self.remove_file(fName)

    def test_linkinfo(self) :
        fName = self.initXML()
        cp = cableplan.CABLEPLAN.get(fName)
        switch = cp.get_switch('Leaf1')
        self.assertEqual(switch.name, 'Leaf1')
        self.assertEqual(switch.chassis_type,None)
        self.assertEqual(switch.spine, False)

        switch = cp.get_switch('Leaf2')
        self.assertEqual(switch.name, 'Leaf2')
        self.assertEqual(switch.chassis_type,None)
        self.assertEqual(switch.spine, False)

        switch = cp.get_switch('Leaf3')
        self.assertEqual(switch.name, 'Leaf3')
        self.assertEqual(switch.chassis_type,None)
        self.assertEqual(switch.spine, False)

        switches = cp.get_switch()
        self.assertEqual(len(switches),5)

        processed = set()
        for switch in switches :
            self.assertIn(switch.name,['Leaf1','Leaf2','Leaf3','Spine1','Spine2'])
            self.assertNotIn(switch.name, processed)
            processed.add(switch.name)

        links = cp.get_links()
        self.assertEqual(len(links), 7)
            
        valid_links = ['(Leaf1-Eth1/1,Spine1-Eth1/1)', '(Leaf1-Eth1/2,Spine1-Eth1/2, Eth1/3)', '(Leaf2-Eth1/1,Spine1-Eth2/3 - Eth2/5)', '(Leaf3,Spine1-Eth2/3 - Eth2/5)', '(Leaf1-Eth1/2 - Eth1/9,Spine2)', '(Leaf2-Eth1/2 - Eth1/4,Spine2-Eth1/2)', '(Leaf3-Eth1/2,Spine2-Eth2/3, Eth2/4, Eth4/4)']

        processed = set()
        for link in links :
            self.assertIn(link.get_name(),valid_links)
            self.assertNotIn(link.get_name(), processed)
            processed.add(link.get_name())
        self.remove_file(fName)
        
    def test_link_create(self) :
        switch1 = cableplan.CP_SWITCH('Leaf1')
        switch2 = cableplan.CP_SWITCH('Leaf2')
        link1 = cableplan.CP_LINK(sourceChassis=switch1, sourcePort='Eth1/1',destChassis=switch2,destPort='Eth2/2')
        link2 = cableplan.CP_LINK(sourceChassis=switch2, sourcePort='Eth1/1',destChassis=switch1,destPort='Eth2/2')
        link3 = cableplan.CP_LINK(sourceChassis=switch2, sourcePort='Eth2/2',destChassis=switch1,destPort='Eth1/1')
        self.assertNotEqual(link1, link2)
        self.assertEqual(link2, link2)
        self.assertEqual(link1, link3)
        
        cp = cableplan.CABLEPLAN()
        cp.add_link(link1)
        links = cp.get_links()
        self.assertEqual(link1,links[0])
        self.assertEqual(len(links), 1)
        cp.add_link(link2)
        cp.add_link(link2)
        cp.add_link(link3)

        links = cp.get_links()
        self.assertIn(link1, links)
        self.assertIn(link2, links)
        self.assertEqual(len(links),2)

        cp.delete_link(link3)
        links = cp.get_links()
        self.assertIn(link2, links)
        self.assertNotIn(link1, links)
        self.assertEqual(len(links),1)

        self.assertFalse(cp.exists_link(link1))
        self.assertTrue(cp.exists_link(link2))
        self.assertFalse(cp.exists_link(link3))
    def test_link_create_error(self) :
        switch1 = cableplan.CP_SWITCH('Leaf1')
        switch2 = cableplan.CP_SWITCH('Leaf2')
        self.assertRaises(TypeError, cableplan.CP_LINK, sourceChassis='bogus', sourcePort='Eth1/1',destChassis=switch2,destPort='Eth2/2')
        self.assertRaises(TypeError, cableplan.CP_LINK, sourceChassis=switch1, sourcePort='Eth1/1',destChassis='bogus',destPort='Eth2/2')

    def test_link_create_port_list(self) :
        switch1 = cableplan.CP_SWITCH('Leaf1')
        switch2 = cableplan.CP_SWITCH('Leaf2')
        sPortList = ['Eth1/3', 'Eth1/2', 'Eth2/1']
        dPortList = ['Eth1/1', 'Eth1/2', 'Eth1/3']
        link1 = cableplan.CP_LINK(sourceChassis=switch1, sourcePort=sPortList,destChassis=switch2,destPort=dPortList)
        self.assertEqual(link1.get_name(), '(Leaf1-Eth1/2, Eth1/3, Eth2/1,Leaf2-Eth1/1 - Eth1/3)')

    def test_link_port_in_common(self) :
        switch1 = cableplan.CP_SWITCH('ALeaf1')
        switch2 = cableplan.CP_SWITCH('BLeaf2')
        switch3 = cableplan.CP_SWITCH('CLeaf2')
        link1 = cableplan.CP_LINK(sourceChassis=switch1, sourcePort='Eth1/1',destChassis=switch2,destPort='Eth2/2')
        link2 = cableplan.CP_LINK(sourceChassis=switch2, sourcePort='Eth2/2',destChassis=switch3,destPort='Eth3/3')
        link3 = cableplan.CP_LINK(sourceChassis=switch1, sourcePort='Eth2/2',destChassis=switch3,destPort='Eth3/3')
        self.assertTrue(link1.hasPortInCommon(link2))
        self.assertTrue(link2.hasPortInCommon(link1))
        self.assertFalse(link1.hasPortInCommon(link3))
        self.assertFalse(link3.hasPortInCommon(link1))
    def test_link_name(self) :
        switch1 = cableplan.CP_SWITCH('ALeaf1')
        switch2 = cableplan.CP_SWITCH('BLeaf2')
        link1 = cableplan.CP_LINK(sourceChassis=switch1, sourcePort='Eth1/1',destChassis=switch2,destPort='Eth2/2')
        self.assertEqual(link1.get_name(), '(ALeaf1-Eth1/1,BLeaf2-Eth2/2)')
        strng = str(link1)
        self.assertEqual(strng, link1.get_name())
        
    def test_switch_create(self) :
        switch1 = cableplan.CP_SWITCH('Leaf1')
        switch2 = cableplan.CP_SWITCH('Leaf2')
        switch3 = cableplan.CP_SWITCH('Leaf1')
        self.assertEqual(switch1.get_name(), 'Leaf1')
        self.assertFalse(switch1.spine)
        self.assertIsNone(switch1.chassis_type)

        cp = cableplan.CABLEPLAN()
        self.assertIsNone(cp.version)
        cp.add_switch(switch1)
        switches = cp.get_switch()
        self.assertEqual(switch1,switches[0])
        cp.add_switch(switch1)
        switches2 = cp.get_switch()
        self.assertEqual(len(switches2), 1)

        cp.add_switch(switch2)
        switches = cp.get_switch()
        self.assertIn(switch1, switches)
        self.assertIn(switch2, switches)
        self.assertEqual(len(switches),2)

        cp.delete_switch(switch3)
        switches = cp.get_switch()
        self.assertNotIn(switch1, switches)
        self.assertIn(switch2, switches)
        self.assertEqual(len(switches),1)

        self.assertTrue(cp.exists_switch(switch2))
        self.assertFalse(cp.exists_switch(switch1))
        self.assertFalse(cp.exists_switch(switch3))
    
    def test_switch_add(self) :
        fName = self.initXML()
        cp = cableplan.CABLEPLAN.get(fName)
        switches = cp.get_switch()
        test_switch1 = cableplan.CP_SWITCH('Spine1')
        test_switch2 = cableplan.CP_SWITCH('Spine3')
        self.assertIn(test_switch1, switches)
        self.assertNotIn(test_switch2, switches)
        self.assertEqual(len(switches),5)

        self.assertEqual(test_switch1.name, 'Spine1')
        self.assertEqual(test_switch2.name, 'Spine3')
        self.assertEqual(test_switch1.chassis_type, None)
        self.assertFalse(test_switch1.spine)
        self.assertEqual(test_switch2.chassis_type, None)
        self.assertFalse(test_switch2.spine)
        
        test_switch1 = cp.add_switch(test_switch1)
        switches = cp.get_switch()
        self.assertIn(test_switch1, switches)
        self.assertEqual(len(switches),5)
        self.assertEqual(test_switch1.chassis_type, 'n9k')
        self.assertTrue(test_switch1.spine)
        
        test_switch2 = cp.add_switch(test_switch2)
        switches = cp.get_switch()
        self.assertIn(test_switch2, switches)
        self.assertEqual(len(switches),6)
        self.assertEqual(test_switch2.chassis_type, None)
        self.assertFalse(test_switch2.spine)

        switches = cp.get_switch('Nonsense')
        self.assertEqual(switches, None)
        self.remove_file(fName)

        self.assertRaises(TypeError, cp.add_switch, 'test_string')

    def test_add_switch_error(self) :
        cp1 = cableplan.CABLEPLAN()
        cp2 = cableplan.CABLEPLAN()
        switch1 = cableplan.CP_SWITCH('Leaf1', parent=cp1)
        self.assertEqual(switch1.parent, cp1)
        self.assertRaises(TypeError, switch1.set_parent, 'Not_a_cableplan')
        self.assertRaises(ValueError, switch1.set_parent, cp2)
        
    def test_link_add(self) :
        fName = self.initXML()
        cp = cableplan.CABLEPLAN.get(fName)

        spine1= cp.get_switch('Spine1')
        leaf1 = cp.get_switch('Leaf1')
        leaf2 = cp.get_switch('Leaf2')

        base_links = cp.get_links()
        self.assertEqual(len(base_links),7)      

        test_link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3', destChassis=leaf1, destPort='Eth1/3')
        test_link2 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1', destChassis=leaf1, destPort='Eth1/1')
        test_link3 = cableplan.CP_LINK(sourceChassis=leaf1, sourcePort='Eth1/1', destChassis=spine1, destPort='Eth1/1')
        self.assertFalse(test_link1==test_link2)
        self.assertTrue(test_link2==test_link3)
        
        self.assertNotIn(test_link1, base_links)
        cp.add_link(test_link1)        
        cp.add_link(test_link1)        
        self.assertNotIn(test_link1, base_links)
        base_links = cp.get_links()
        self.assertIn(test_link1, base_links)
        self.assertEqual(len(base_links),8)      

        self.assertIn(test_link2, base_links)
        cp.add_link(test_link2)
        self.assertEqual(len(base_links),8)

        self.remove_file(fName)
        
            
class Test_portset(unittest.TestCase) :
    def test_port_equal_case_insensitive(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3', destChassis=leaf1, destPort='Eth1/1')
        link2 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='eTh1/3', destChassis=leaf1, destPort='eth1/1')
        self.assertEqual(link1, link2)
        
    def test_non_set(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3', destChassis=leaf1, destPort='Eth1/1')
        self.assertEqual(len(set(['Eth1/1']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/3']) ^ set(link1.destPort.ports)), 0)

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/2/3', destChassis=leaf1, destPort='Eth1/1')
        self.assertEqual(len(set(['Eth1/1']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/2/3']) ^ set(link1.destPort.ports)), 0)
                
    def test_set_list(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3, Eth1/5', destChassis=leaf1, destPort='Eth1/1, Eth2/6')
        self.assertEqual(len(set(['Eth1/1', 'Eth2/6']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/3', 'Eth1/5']) ^ set(link1.destPort.ports)), 0)

    def test_set_range(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3 - Eth1/5', destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertEqual(len(set(['Eth2/1', 'Eth2/2', 'Eth2/3', 'Eth2/4', 'Eth2/5', 'Eth2/6']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/3', 'Eth1/4', 'Eth1/5']) ^ set(link1.destPort.ports)), 0)
        
        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3 - Eth1/4', destChassis=leaf1, destPort='Eth2/1')
        self.assertEqual(len(set(['Eth2/1']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/3', 'Eth1/4']) ^ set(link1.destPort.ports)), 0)

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/2/3 - Eth1/2/5', destChassis=leaf1, destPort='Eth2/1')
        self.assertEqual(len(set(['Eth2/1']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/2/3', 'Eth1/2/4', 'Eth1/2/5']) ^ set(link1.destPort.ports)), 0)

    def test_mixed(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3 - Eth1/5, Eth1/7', destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertEqual(len(set(['Eth2/1', 'Eth2/2', 'Eth2/3', 'Eth2/4', 'Eth2/5', 'Eth2/6']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/1','Eth1/3', 'Eth1/4', 'Eth1/5', 'Eth1/7']) ^ set(link1.destPort.ports)), 0)
        self.assertEqual(link1.destPort.name(),'Eth1/1, Eth1/3 - Eth1/5, Eth1/7')
        self.assertEqual(link1.sourcePort.name(),'Eth2/1 - Eth2/6')
        
        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3 - Eth1/5, Eth1/7, Eth1/1', destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertEqual(len(set(['Eth2/1', 'Eth2/2', 'Eth2/3', 'Eth2/4', 'Eth2/5', 'Eth2/6']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/1','Eth1/3', 'Eth1/4', 'Eth1/5', 'Eth1/7']) ^ set(link1.destPort.ports)), 0)
        self.assertEqual(link1.destPort.name(),'Eth1/1, Eth1/3 - Eth1/5, Eth1/7')
        self.assertEqual(link1.sourcePort.name(),'Eth2/1 - Eth2/6')
        
        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3 - Eth1/5, Eth1/7', destChassis=leaf1, destPort='Eth2/1 - Eth2/2')
        self.assertEqual(len(set(['Eth2/1', 'Eth2/2']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/3', 'Eth1/4', 'Eth1/5', 'Eth1/7']) ^ set(link1.destPort.ports)), 0)
        self.assertEqual(link1.destPort.name(),'Eth1/3 - Eth1/5, Eth1/7')
        self.assertEqual(link1.sourcePort.name(),'Eth2/1, Eth2/2')
        
        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3 - Eth1/5', destChassis=leaf1, destPort='Eth2/1 - Eth2/1')
        self.assertEqual(len(set(['Eth2/1']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/1','Eth1/3', 'Eth1/4', 'Eth1/5']) ^ set(link1.destPort.ports)), 0)
        self.assertEqual(link1.destPort.name(),'Eth1/1, Eth1/3 - Eth1/5')
        self.assertEqual(link1.sourcePort.name(),'Eth2/1')
        
        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3 - Eth1/5, Eth1/4',
                           destChassis=leaf1, destPort='Eth2/1, Eth2/1 - Eth2/6, Eth2/6')
        self.assertEqual(len(set(['Eth2/1', 'Eth2/2', 'Eth2/3', 'Eth2/4', 'Eth2/5', 'Eth2/6']) ^ set(link1.sourcePort.ports)), 0)
        self.assertEqual(len(set(['Eth1/1','Eth1/3', 'Eth1/4', 'Eth1/5']) ^ set(link1.destPort.ports)), 0)
        self.assertEqual(link1.destPort.name(),'Eth1/1, Eth1/3 - Eth1/5')
        self.assertEqual(link1.sourcePort.name(),'Eth2/1 - Eth2/6')
        
    def test_bad_range(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')
        self.assertRaises(ValueError, cableplan.CP_LINK, sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3 - Eth2/5, Eth1/7',
                          destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertRaises(ValueError, cableplan.CP_LINK, sourceChassis=spine1, sourcePort='Eth1/1, Eth13 - Eth1/5, Eth1/7',
                          destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertRaises(ValueError, cableplan.CP_LINK, sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3 - Eth15, Eth1/7',
                          destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertRaises(ValueError, cableplan.CP_LINK, sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3 - Eth15, Eth17',
                          destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertRaises(ValueError, cableplan.CP_LINK, sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3 - Eth15, Eth17',
                          destChassis=leaf1, destPort='Eth2/1 - Eth2/6')
        self.assertRaises(ValueError, cableplan.CP_LINK, sourceChassis=spine1, sourcePort='Eth1/1, Eth1/5 - Eth1/3, Eth17',
                          destChassis=leaf1, destPort='Eth2/1 - Eth2/6')

    def test_hasPortInCommon(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')
        leaf2 = cableplan.CP_SWITCH('Leaf2')
        leafZ = cableplan.CP_SWITCH('ZLeaf1')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3-Eth1/5', destChassis=leaf1, destPort='Eth1/1, Eth2/6')
        link2 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1, Eth1/3', destChassis=leaf2, destPort='Eth1/1, Eth2/6')
        link3 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1-Eth1/3', destChassis=leaf2, destPort='Eth1/1, Eth2/6')
        link4 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1-Eth1/2', destChassis=leaf2, destPort='Eth1/1, Eth2/6')
        link5 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/5-Eth1/7', destChassis=leafZ, destPort='Eth1/1, Eth2/6')
        link6 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1-Eth1/2', destChassis=leafZ, destPort='Eth1/1, Eth2/6')
        link7 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1, Eth1/2', destChassis=leaf1, destPort='Eth1/1')
        link8 = cableplan.CP_LINK(sourceChassis=leafZ, sourcePort='Eth1/1, Eth1/2', destChassis=leaf1, destPort='Eth2/6')

        self.assertTrue(link1.hasPortInCommon(link2))
        self.assertTrue(link1.hasPortInCommon(link3))
        self.assertFalse(link1.hasPortInCommon(link4))
        self.assertTrue(link1.hasPortInCommon(link5))
        self.assertFalse(link1.hasPortInCommon(link6))
        self.assertTrue(link1.hasPortInCommon(link7))
        self.assertTrue(link1.hasPortInCommon(link8))
        
    def test_overlapping(self) :
        spine1 = cableplan.CP_SWITCH('Spine1', spine=True)
        leaf1 = cableplan.CP_SWITCH('Leaf1')
        leaf2 = cableplan.CP_SWITCH('Leaf2')
        leaf3 = cableplan.CP_SWITCH('Leaf3')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1-Eth1/3', destChassis=leaf1, destPort='Eth1/1, Eth2/6')
        link2 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1 - Eth1/3', destChassis=leaf2, destPort='Eth1/1, Eth2/6')
        link3 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1- Eth1/3', destChassis=leaf3, destPort='Eth1/1, Eth2/6')
        link4 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1- Eth1/3', destChassis=leaf3, destPort='Eth1/1, Eth2/6')

        cp = cableplan.CABLEPLAN()
        cp.add_switch(spine1)
        cp.add_switch(leaf1)
        cp.add_switch(leaf2)
        cp.add_switch(leaf3)
        cp.add_link(link1)
        cp.add_link(link2)
        cp.add_link(link3)
        cp.add_link(link4)

        links = cp.get_links(spine1)
        self.assertEqual(len(links),3)
        self.assertIn(link1, links)
        self.assertIn(link2, links)
        self.assertIn(link3, links)
        self.assertIn(link4, links)
        
        links = cp.get_links(leaf1)
        self.assertEqual(len(links),1)
        self.assertIn(link1, links)
        self.assertNotIn(link2, links)
        
        links = cp.get_links(leaf2)
        self.assertEqual(len(links),1)
        self.assertIn(link2, links)
        self.assertNotIn(link1, links)
        
class Test_switch(unittest.TestCase) :
    def test_name_change(self) :
        spine1 = cableplan.CP_SWITCH('Spine1')
        leaf1 = cableplan.CP_SWITCH('Leaf1')
        new_name = 'New_Name_2'
        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3', destChassis=leaf1, destPort='Eth1/1')
        link2 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='eTh1/3', destChassis=leaf1, destPort='eth1/1')
        self.assertEqual('(Leaf1-Eth1/1,Spine1-Eth1/3)', link1.get_name())
        self.assertEqual('Spine1',spine1.get_name())

        spine1.set_name(new_name)
        self.assertEqual('(Leaf1-Eth1/1,'+new_name+'-Eth1/3)', link1.get_name())
        self.assertEqual(new_name,spine1.get_name())
        
class Test_port(unittest.TestCase) :
    def test_string(self) :
        port = cableplan.CP_PORT('Eth1/3')
        portStr = str(port)
        self.assertEqual(portStr, 'Eth1/3')
    
class Test_cableplan(unittest.TestCase) :
    def test_get_links(self) :
        cp = cableplan.CABLEPLAN()
        spine1 = cableplan.CP_SWITCH('Spine1', spine=True)
        spine2 = cableplan.CP_SWITCH('Spine2', spine=True)
        leaf1 = cableplan.CP_SWITCH('Leaf1')
        leaf2 = cableplan.CP_SWITCH('Leaf2')
        leaf3 = cableplan.CP_SWITCH('Leaf3')

        link1 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/1', destChassis=leaf1, destPort='Eth1/1')
        link2 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/2', destChassis=leaf1, destPort='Eth2/1')
        link3 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/3', destChassis=leaf2, destPort='Eth1/1')
        link4 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/4', destChassis=leaf2, destPort='Eth2/1')
        link5 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/5', destChassis=leaf3, destPort='Eth1/1')
        link6 = cableplan.CP_LINK(sourceChassis=spine1, sourcePort='Eth1/6', destChassis=leaf3, destPort='Eth2/1')

        link7 = cableplan.CP_LINK(sourceChassis=spine2, sourcePort='Eth1/1', destChassis=leaf1, destPort='Eth1/2')
        link8 = cableplan.CP_LINK(sourceChassis=spine2, sourcePort='Eth1/2', destChassis=leaf1, destPort='Eth2/2')
        link9 = cableplan.CP_LINK(sourceChassis=spine2, sourcePort='Eth1/3', destChassis=leaf2, destPort='Eth1/2')
        link10 = cableplan.CP_LINK(sourceChassis=spine2, sourcePort='Eth1/4', destChassis=leaf2, destPort='Eth2/2')
        link11 = cableplan.CP_LINK(sourceChassis=spine2, sourcePort='Eth1/5', destChassis=leaf3, destPort='Eth1/2')
        link12 = cableplan.CP_LINK(sourceChassis=spine2, sourcePort='Eth1/6', destChassis=leaf3, destPort='Eth2/2')



        cp.add_switch(spine1)
        cp.add_switch(spine2)
        cp.add_switch(leaf1)
        cp.add_switch(leaf2)
        cp.add_switch(leaf3)
        cp.add_link(link1)
        cp.add_link(link2)
        cp.add_link(link3)
        cp.add_link(link4)
        cp.add_link(link5)
        cp.add_link(link6)
        cp.add_link(link7)
        cp.add_link(link8)
        cp.add_link(link9)
        cp.add_link(link10)
        cp.add_link(link11)
        cp.add_link(link12)

        links = cp.get_links()
        self.assertEqual(len(links), 12)
        linkSet = [link1, link2, link3, link4, link5,link6, link7,link8, link9, link10,link11,link12]
        for link in linkSet :
            self.assertIn(link, links)
        
        links = cp.get_links(spine1)
        self.assertEqual(len(links), 6)
        linkSet = [link1, link2, link3, link4, link5,link6]
        for link in linkSet :
            self.assertIn(link, links)
        
        links = cp.get_links(leaf3)
        self.assertEqual(len(links), 4)
        linkSet = [link5,link6, link11, link12]
        for link in linkSet :
            self.assertIn(link, links)
        
        links = cp.get_links(spine1, leaf1)
        self.assertEqual(len(links), 2)
        linkSet = [link1, link2]
        for link in linkSet :
            self.assertIn(link, links)
        
        links = cp.get_links(spine1, spine2)
        self.assertEqual(len(links), 0)

class Test_difference_switch(unittest.TestCase) :
    def test_difference(self) :
        cp1 = cableplan.CABLEPLAN()
        cp2 = cableplan.CABLEPLAN()

        spine1a = cableplan.CP_SWITCH('Spine1', spine=True)
        spine1b = cableplan.CP_SWITCH('Spine1', spine=True)
        spine2 = cableplan.CP_SWITCH('Spine2', spine=True)
        leaf1 = cableplan.CP_SWITCH('Leaf1')
        leaf2 = cableplan.CP_SWITCH('Leaf2')
        leaf3 = cableplan.CP_SWITCH('Leaf3')

        cp1.add_switch(spine1a)
        cp1.add_switch(leaf1)
        cp1.add_switch(leaf2)
        
        cp2.add_switch(spine1b)
        cp2.add_switch(leaf3)

        dswitches = cp1.difference_switch(cp2)
        self.assertIn(leaf1, dswitches)
        self.assertIn(leaf2, dswitches)
        self.assertEqual(len(dswitches), 2)
        
        dswitches = cp2.difference_switch(cp1)
        self.assertIn(leaf3, dswitches)
        self.assertEqual(len(dswitches), 1)

        
class Test_export(unittest.TestCase) : 
    def get_temporary_filename(self) :
        fname_base = 'temp_cable_plan'
        fname_uniquifier = ''
        fname_suffix = '.xml'
        uniquifier = 0
        while(os.path.isfile(fname_base+fname_uniquifier+fname_suffix)) :
            fname_uniquifier = str(uniquifier)
            uniquifier += 1
        return fname_base+fname_uniquifier+fname_suffix
    
    def remove_file(self, fname) :
        os.remove(fname)
    def get_expected_xml(self) :
        expected_xml = ['<?xml version="1.0" encoding="UTF-8"?>\n',
                        '<?created by cableplan.py?>\n',
                        '<CISCO_NETWORK_TYPES version="1.0" xmlns="http://www.cisco.com/cableplan/Schema2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.cisco.com/cableplan/Schema2 nxos-cable-plan-schema.xsd">\n',
                        '   <DATA_CENTER networkLocation="None" idFormat="hostname">\n',
                        '      <CHASSIS_INFO sourceChassis="ASpine1" type="n9k">\n',
                        '         <LINK_INFO sourcePort="Eth1/1" destChassis="Leaf1" destPort="Eth1/1"/>\n',
                        '         <LINK_INFO sourcePort="Eth1/2, Eth1/3" destChassis="Leaf1" destPort="Eth1/2"/>\n',
                        '         <LINK_INFO sourcePort="Eth2/3 - Eth2/5" destChassis="Leaf2" destPort="Eth1/1"/>\n',
                        '         <LINK_INFO sourcePort="Eth2/3 - Eth2/5" destChassis="Leaf3"/>\n',
                        '      </CHASSIS_INFO>\n',
                        '      <CHASSIS_INFO sourceChassis="ASpine2" type="n9k">\n',
                        '         <LINK_INFO destChassis="Leaf1" destPort="Eth1/2 - Eth1/9" minPorts="3"/>\n',
                        '         <LINK_INFO sourcePort="Eth1/2" destChassis="Leaf2" destPort="Eth1/2 - Eth1/4" maxPorts="2"/>\n',
                        '         <LINK_INFO sourcePort="Eth2/3, Eth2/4, Eth4/4" destChassis="Leaf3" destPort="Eth1/2" minPorts="1" maxPorts="5"/>\n',
                        '      </CHASSIS_INFO>\n',
                        '   </DATA_CENTER>\n',
                        '</CISCO_NETWORK_TYPES>\n']
        return expected_xml
    
    def test_export(self) :
        expected_xml = self.get_expected_xml()
        fname = self.get_temporary_filename()
        f = open(fname, 'w')
        cp = cableplan.CABLEPLAN(version='1.0')
        Leaf1 = cableplan.CP_SWITCH('Leaf1')
        Leaf2 = cableplan.CP_SWITCH('Leaf2')
        Leaf3 = cableplan.CP_SWITCH('Leaf3')
        Spine1 = cableplan.CP_SWITCH('ASpine1', chassis_type = 'n9k', spine = True)
        Spine2 = cableplan.CP_SWITCH('ASpine2', chassis_type = 'n9k', spine = True)
        cp.add_switch(Leaf1)
        cp.add_switch(Leaf2)
        cp.add_switch(Leaf3)
        cp.add_switch(Spine1)
        cp.add_switch(Spine2)

        cp.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth1/1',destChassis=Leaf1,destPort='Eth1/1'))
        cp.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth1/3,Eth1/2',destChassis=Leaf1,destPort='Eth1/2'))
        cp.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth2/3-Eth2/5',destChassis=Leaf2,destPort='Eth1/1'))
        cp.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth2/3-Eth2/5',destChassis=Leaf3))

        cp.add_link(cableplan.CP_LINK(sourceChassis=Spine2,destChassis=Leaf1,destPort='Eth1/2-Eth1/9,Eth1/2, Eth1/3', minPorts = 3))
        cp.add_link(cableplan.CP_LINK(sourceChassis=Spine2, sourcePort='Eth1/2',destChassis=Leaf2,destPort='Eth1/2, Eth1/3,Eth1/4', maxPorts = 2))
        cp.add_link(cableplan.CP_LINK(sourceChassis=Spine2, sourcePort='Eth2/3, Eth4/4, Eth2/4',destChassis=Leaf3,destPort='Eth1/2', minPorts = 1, maxPorts = 5))
                
        cp.export(f)
        f.close()
        f = open(fname, 'r')
        index = 0;
        for line in f :
            self.assertEqual(line,expected_xml[index])
            index +=1
        # cleanup
        self.remove_file(fname)

        self.assertRaises(TypeError, cp.export, 'BogusFile')
        
    def test_import(self) :
        expected_xml = self.get_expected_xml()
        fname = self.get_temporary_filename()
        f = open(fname, 'w')
        for index in range(len(expected_xml)) :
            f.write(expected_xml[index])
        f.close()

        cp1 = cableplan.CABLEPLAN(version='1.0')
        Leaf1 = cableplan.CP_SWITCH('Leaf1')
        Leaf2 = cableplan.CP_SWITCH('Leaf2')
        Leaf3 = cableplan.CP_SWITCH('Leaf3')
        Spine1 = cableplan.CP_SWITCH('ASpine1', chassis_type = 'n9k', spine = True)
        Spine2 = cableplan.CP_SWITCH('ASpine2', chassis_type = 'n9k', spine = True)
        cp1.add_switch(Leaf1)
        cp1.add_switch(Leaf2)
        cp1.add_switch(Leaf3)
        cp1.add_switch(Spine1)
        cp1.add_switch(Spine2)

        cp1.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth1/1',destChassis=Leaf1,destPort='Eth1/1'))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth1/3,Eth1/2',destChassis=Leaf1,destPort='Eth1/2'))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth2/3-Eth2/5',destChassis=Leaf2,destPort='Eth1/1'))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=Spine1, sourcePort='Eth2/3-Eth2/5',destChassis=Leaf3))

        cp1.add_link(cableplan.CP_LINK(sourceChassis=Spine2,destChassis=Leaf1,destPort='Eth1/2-Eth1/9,Eth1/2, Eth1/3', minPorts = 3))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=Spine2, sourcePort='Eth1/2',destChassis=Leaf2,destPort='Eth1/2, Eth1/3,Eth1/4', maxPorts = 2))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=Spine2, sourcePort='Eth2/3, Eth4/4, Eth2/4',destChassis=Leaf3,destPort='Eth1/2', minPorts = 1, maxPorts = 5))
        
        cp2 = cableplan.CABLEPLAN.get(fname)

        diff_switches = cp1.difference_switch(cp2)
        self.assertEqual(len(diff_switches),0)
        diff_switches = cp2.difference_switch(cp1)
        self.assertEqual(len(diff_switches),0)
        
        diff_links = cp1.difference_link(cp2)
            
        self.assertEqual(len(diff_links),0)
        diff_links = cp2.difference_link(cp1)
        self.assertEqual(len(diff_links),0)

        switches = cp2.get_switch()
        self.assertNotEqual(len(switches), 0)
        # cleanup
        self.remove_file(fname)

        
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


    def get_temporary_filename(self) :
        fname_base = 'temp_cable_plan'
        fname_uniquifier = ''
        fname_suffix = '.xml'
        uniquifier = 0
        while(os.path.isfile(fname_base+fname_uniquifier+fname_suffix)) :
            fname_uniquifier = str(uniquifier)
            uniquifier += 1
        return fname_base+fname_uniquifier+fname_suffix
    
    def remove_file(self, fname) :
        os.remove(fname)

    def test_import_export(self) :
        fname = self.get_temporary_filename()
        session = self.login_to_apic()
        cp1 = cableplan.CABLEPLAN.get(session)
        f = open(fname, 'w')
        cp1.export(f)
        f.close()
        f = open(fname, 'r')
        cp2 = cableplan.CABLEPLAN.get(fname)
        f.close()
        diff_switches = cp1.difference_switch(cp2)
        self.assertEqual(len(diff_switches),0)
        diff_switches = cp2.difference_switch(cp1)
        self.assertEqual(len(diff_switches),0)
        
        diff_links = cp1.difference_link(cp2)
        self.assertEqual(len(diff_links),0)
        diff_links = cp2.difference_link(cp1)
        self.assertEqual(len(diff_links),0)

        switches = cp2.get_switch()
        self.assertNotEqual(len(switches), 0)
        # cleanup
        self.remove_file(fname)
        
        
class Test_compare_cp(unittest.TestCase) :
    def test_basic(self) :
        cp1 = cableplan.CABLEPLAN()
        cp2 = cableplan.CABLEPLAN()
        
        spine1a = cableplan.CP_SWITCH('Spine1', spine=True)
        spine1b = cableplan.CP_SWITCH('Spine1', spine=True)
        spine2a = cableplan.CP_SWITCH('Spine2', spine=True)
        spine2b = cableplan.CP_SWITCH('Spine2', spine=True)
        leaf1a = cableplan.CP_SWITCH('Leaf1')
        leaf2a = cableplan.CP_SWITCH('Leaf2')
        leaf3a = cableplan.CP_SWITCH('Leaf3')
        leaf1b = cableplan.CP_SWITCH('Leaf1')
        leaf2b = cableplan.CP_SWITCH('Leaf2')
        leaf3b = cableplan.CP_SWITCH('Leaf3')
        
        cp1.add_switch(spine1a)
        cp1.add_switch(spine2a)
        self.assertEqual(len(cp1.difference_switch(cp2)), 2)
        self.assertEqual(len(cp2.difference_switch(cp1)), 0)
        cp2.add_switch(spine1b)
        cp2.add_switch(spine2b)
        cp2.add_switch(leaf1b)
        self.assertEqual(len(cp1.difference_switch(cp2)), 0)
        self.assertEqual(len(cp2.difference_switch(cp1)), 1)
        
        cp1.add_switch(leaf1a)
        cp1.add_switch(leaf2a)
        cp1.add_switch(leaf3a)
        cp2.add_switch(leaf2b)
        cp2.add_switch(leaf3b)
        
        cp1.add_link(cableplan.CP_LINK(sourceChassis=spine1a, sourcePort='Eth1/1-Eth1/4',destChassis=leaf1a,destPort='Eth1/1-Eth1/2', maxPorts=1))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=spine1a, sourcePort='Eth1/1-Eth1/4',destChassis=leaf2a,destPort='Eth1/1-Eth1/2', maxPorts=1))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=spine1a, sourcePort='Eth1/1-Eth1/4',destChassis=leaf3a,destPort='Eth1/1-Eth1/2', maxPorts=1))
        
        cp1.add_link(cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1-Eth1/5',destChassis=leaf1a,destPort='Eth1/1-Eth1/2', maxPorts=1))
        cp1.add_link(cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1-Eth1/5',destChassis=leaf2a,destPort='Eth1/1-Eth1/2', maxPorts=1))
        link6a = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1-Eth1/5',destChassis=leaf3a,destPort='Eth1/1-Eth1/2', maxPorts=1)
        cp1.add_link(link6a)
        
        link6b = cableplan.CP_LINK(sourceChassis=spine2b, sourcePort='Eth1/3',destChassis=leaf3b,destPort='Eth1/2')
        cp2.add_link(cableplan.CP_LINK(sourceChassis=spine1b, sourcePort='Eth1/1',destChassis=leaf1b,destPort='Eth1/2'))
        cp2.add_link(cableplan.CP_LINK(sourceChassis=spine1b, sourcePort='Eth1/2',destChassis=leaf2b,destPort='Eth1/1'))
        cp2.add_link(cableplan.CP_LINK(sourceChassis=spine1b, sourcePort='Eth1/3',destChassis=leaf3b,destPort='Eth1/1'))
        cp2.add_link(cableplan.CP_LINK(sourceChassis=spine2b, sourcePort='Eth1/1',destChassis=leaf1b,destPort='Eth1/1'))
        cp2.add_link(cableplan.CP_LINK(sourceChassis=spine2b, sourcePort='Eth1/2',destChassis=leaf2b,destPort='Eth1/2'))
        cp2.add_link(link6b)

        self.assertEqual(len(cp1.difference_switch(cp2)), 0)
        self.assertEqual(len(cp2.difference_switch(cp1)), 0)
        self.assertEqual(len(cp1.difference_link(cp2)),0)
        self.assertEqual(len(cp2.difference_link(cp1)),0)

        # delete a link
        cp2.delete_link(link6b)

        #make sure switches are still the same
        self.assertEqual(len(cp1.difference_switch(cp2)), 0)
        self.assertEqual(len(cp2.difference_switch(cp1)), 0)
        
        extra_links = cp1.difference_link(cp2)
        self.assertEqual(extra_links[0],link6a)
        self.assertEqual(len(extra_links),1)
        self.assertEqual(len(cp2.difference_link(cp1)),0)
        
        cp2.add_link(link6b)
        cp1.delete_link(link6a)
        
        extra_links = cp2.difference_link(cp1)
        self.assertEqual(extra_links[0],link6b)
        self.assertEqual(len(extra_links),1)
        self.assertEqual(len(cp1.difference_link(cp2)),0)
        
    def test_remaining(self) :
        cp1 = cableplan.CABLEPLAN()
        cp2 = cableplan.CABLEPLAN()
        
        spine1a = cableplan.CP_SWITCH('Spine1', spine=True)
        spine1b = cableplan.CP_SWITCH('Spine1', spine=True)
        leaf1a = cableplan.CP_SWITCH('Leaf1')
        leaf1b = cableplan.CP_SWITCH('Leaf1')
        
        cp1.add_switch(spine1a)
        cp1.add_switch(leaf1a)
        cp2.add_switch(spine1b)
        cp2.add_switch(leaf1b)

        link1a = cableplan.CP_LINK(sourceChassis=spine1a, sourcePort='Eth1/1-Eth1/14',destChassis=leaf1a,destPort='Eth1/1-Eth1/20', minPorts=3, maxPorts=5)
        cp1.add_link(link1a)
        cp2.add_link(cableplan.CP_LINK(sourceChassis=spine1b, sourcePort='Eth1/1',destChassis=leaf1b,destPort='Eth1/1'))

        missing_links = cp1.difference_link(cp2)
        self.assertEqual(link1a, missing_links[0])
        self.assertEqual(len(missing_links),1)

        self.assertEqual(missing_links[0].remainingAvail(), 4)
        self.assertEqual(missing_links[0].remainingNeed(), 2)

        cp1.delete_link(link1a)
        link1a = cableplan.CP_LINK(sourceChassis=spine1a,destChassis=leaf1a,destPort='Eth1/1-Eth1/20', minPorts=4)
        cp1.add_link(link1a)
        
        missing_links = cp1.difference_link(cp2)
        self.assertEqual(missing_links[0].remainingAvail(), 19)
        self.assertEqual(missing_links[0].remainingNeed(), 3)
        cp2.add_link(cableplan.CP_LINK(sourceChassis=spine1b,destChassis=leaf1b))
        missing_links = cp1.difference_link(cp2)
        self.assertEqual(len(missing_links),0)
        
        
    def test_any(self) :
        cp1 = cableplan.CABLEPLAN()
        cp2 = cableplan.CABLEPLAN()
        
        spine2a = cableplan.CP_SWITCH('Spine2', spine=True)
        spine2b = cableplan.CP_SWITCH('Spine2', spine=True)
        leaf1a = cableplan.CP_SWITCH('Leaf1')
        leaf1b = cableplan.CP_SWITCH('Leaf1')
        
        cp1.add_switch(spine2a)
        cp1.add_switch(leaf1a)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,destChassis=leaf1a,destPort='Eth1/1-Eth1/2', maxPorts=1)
        cp1.add_link(linka)

        cp2.add_switch(spine2b)
        cp2.add_switch(leaf1b)
        linkb=cableplan.CP_LINK(sourceChassis=spine2b, sourcePort='Eth1/1',destChassis=leaf1b,destPort='Eth1/1')
        cp2.add_link(linkb)
        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)

        cp1.delete_link(linka)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1',destChassis=leaf1a,maxPorts=2)
        cp1.add_link(linka)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
        
        cp1.delete_link(linka)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,destChassis=leaf1a,maxPorts=1)
        cp1.add_link(linka)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
        
        cp1.delete_link(linka)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,destChassis=leaf1a)
        cp1.add_link(linka)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
        
        cp2.delete_link(linkb)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a, destPort='Eth1/1, Eth1/2', minPorts=2)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
        
        cp1.delete_link(linka)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1, Eth1/2',destChassis=leaf1a)
        cp1.add_link(linka)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
        
        cp1.delete_link(linka)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a)
        cp1.add_link(linka)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
        
        cp1.delete_link(linka)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a, minPorts=3)
        cp1.add_link(linka)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0], linka)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
        
        cp1.delete_link(linka)
        cp2.delete_link(linkb)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a)
        cp1.add_link(linka)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
                
        cp1.delete_link(linka)
        cp2.delete_link(linkb)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/3 - Eth1/5',destChassis=leaf1a)
        cp1.add_link(linka)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
                
        cp1.delete_link(linka)
        cp2.delete_link(linkb)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/4 - Eth1/6',destChassis=leaf1a)
        cp1.add_link(linka)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(links[0], linka)
        self.assertEqual(len(links), 1)
        links = cp2.difference_link(cp1)
        self.assertEqual(links[0], linkb)
        self.assertEqual(len(links), 1)
                
        cp1.delete_link(linka)
        cp2.delete_link(linkb)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a, minPorts = 2)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a, minPorts = 2)
        cp1.add_link(linka)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
                
        cp1.delete_link(linka)
        cp2.delete_link(linkb)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/3',destChassis=leaf1a, minPorts = 2)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/3 - Eth1/5',destChassis=leaf1a, minPorts = 2)
        cp1.add_link(linka)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 1)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 1)
                
        cp1.delete_link(linka)
        cp2.delete_link(linkb)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1',destChassis=leaf1a)
        linkc = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/3',destChassis=leaf1a)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1 - Eth1/5',destChassis=leaf1a, minPorts = 2)
        cp1.add_link(linka)
        cp1.add_link(linkc)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
                
        cp1.delete_link(linka)
        cp1.delete_link(linkc)
        cp2.delete_link(linkb)
        linka = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/1-Eth1/3',destChassis=leaf1a, minPorts=2)
        linkc = cableplan.CP_LINK(sourceChassis=spine2a,sourcePort='Eth1/4-Eth1/6',destChassis=leaf1a, minPorts=2)
        linkb = cableplan.CP_LINK(sourceChassis=spine2a,destChassis=leaf1a, destPort='Eth1/2-Eth1/5', minPorts = 2)
        cp1.add_link(linka)
        cp1.add_link(linkc)
        cp2.add_link(linkb)

        links = cp1.difference_link(cp2)
        self.assertEqual(len(links), 0)
        links = cp2.difference_link(cp1)
        self.assertEqual(len(links), 0)
                
if __name__ == '__main__':
    unittest.main()
