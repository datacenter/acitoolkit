#!/usr/bin/env python
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
"""
Sample of creating OSPF interface
"""

from acitoolkit.acitoolkit import *

creds = Credentials('apic')
args = creds.get()
session = Session(args.url, args.login, args.password)
session.login()

tenant = Tenant('Cisco-Demo')
context = Context('ctx1', tenant)
outside = OutsideEPG('out-1', tenant)
outside.add_context(context)
phyif = Interface('eth', '1', '101', '1', '46')
phyif.speed='1G'
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
ospfif.auth_key = 'password'
ospfif.auth_keyid = '1'
ospfif.auth_type = 'simple'
ospfif.set_nw_type('p2p')
tenant.attach(ospfif)
ospfif.networks.append('55.5.5.0/24')
ospfif.attach(l3if)
contract1 = Contract('contract-1')
outside.provide(contract1)
contract2 = Contract('contract-2')
outside.consume(contract2)
outside.attach(ospfif)



resp = session.push_to_apic(tenant.get_url(),
                            tenant.get_json())

if not resp.ok:
   print '%% Error: Could not push configuration to APIC'
   print resp.text

