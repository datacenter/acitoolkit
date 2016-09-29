#!/usr/bin/env python
################################################################################
#                 _    ____ ___   _____           _ _    _ _                   #
#                / \  / ___|_ _| |_   _|__   ___ | | | _(_) |_                 #
#               / _ \| |    | |    | |/ _ \ / _ \| | |/ / | __|                #
#              / ___ \ |___ | |    | | (_) | (_) | |   <| | |_                 #
#        ____ /_/   \_\____|___|___|_|\___/ \___/|_|_|\_\_|\__|                #
#       / ___|___   __| | ___  / ___|  __ _ _ __ ___  _ __ | | ___  ___        #
#      | |   / _ \ / _` |/ _ \ \___ \ / _` | '_ ` _ \| '_ \| |/ _ \/ __|       #
#      | |__| (_) | (_| |  __/  ___) | (_| | | | | | | |_) | |  __/\__ \       #
#       \____\___/ \__,_|\___| |____/ \__,_|_| |_| |_| .__/|_|\___||___/       #
#                                                    |_|                       #
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
Simple application to define 2 EPGs with a contract between them and statically
connecting the EPGs to specific interfaces using a specific VLANs.

It logs in to the APIC and will create the tenant, application profile,
EPGs, and Contract if they do not exist already.  It then connects it to the
specified interface using the VLAN encapsulation specified.

Before running, examine the code and change the interface information if desired
as well as the VLAN.

"""
from acitoolkit import (Credentials, Session, Tenant, AppProfile, EPG, BridgeDomain, Context,
                        Interface, L2Interface, Contract, FilterEntry)

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = ('Simple application to define 2 EPGs with a contract between them and statically '
               'connecting the EPGs to specific interfaces using a specific VLANs.')
creds = Credentials('apic', description)
args = creds.get()

# Login to the APIC
session = Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')

# Create the Tenant, App Profile, and EPGs
tenant = Tenant('acitoolkit-attach-with-contract')
app = AppProfile('myapp', tenant)
first_epg = EPG('firstepg', app)
second_epg = EPG('secondepg', app)

# Create the Contract to permit only ARP and ICMP
contract = Contract('mycontract', tenant)
icmp_entry = FilterEntry('icmpentry',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='unspecified',
                         dToPort='unspecified',
                         etherT='ip',
                         prot='icmp',
                         sFromPort='unspecified',
                         sToPort='unspecified',
                         tcpRules='unspecified',
                         parent=contract)
arp_entry = FilterEntry('arpentry',
                        applyToFrag='no',
                        arpOpc='unspecified',
                        dFromPort='unspecified',
                        dToPort='unspecified',
                        etherT='arp',
                        prot='unspecified',
                        sFromPort='unspecified',
                        sToPort='unspecified',
                        tcpRules='unspecified',
                        parent=contract)
tcp_entry = FilterEntry('tcpentry',
                        applyToFrag='no',
                        arpOpc='unspecified',
                        dFromPort='5000',
                        dToPort='5010',
                        etherT='ip',
                        prot='tcp',
                        sFromPort='5000',
                        sToPort='5010',
                        tcpRules='unspecified',
                        parent=contract)
udp_entry = FilterEntry('udpentry',
                        applyToFrag='no',
                        arpOpc='unspecified',
                        dFromPort='5000',
                        dToPort='5010',
                        etherT='ip',
                        prot='udp',
                        sFromPort='5000',
                        sToPort='5010',
                        tcpRules='unspecified',
                        parent=contract)
# Provide and consume the Contract
first_epg.provide(contract)
second_epg.consume(contract)

# Create the networking stuff and put both EPGs in the same BridgeDomain
vrf = Context('vrf-1', tenant)
bd = BridgeDomain('bd-1', tenant)
bd.add_context(vrf)
first_epg.add_bd(bd)
second_epg.add_bd(bd)

# Create the physical interface objects representing the physical ethernet ports
first_intf = Interface('eth', '1', '101', '1', '17')
second_intf = Interface('eth', '1', '102', '1', '17')

# Create a VLAN interface and attach to each physical interface
first_vlan_intf = L2Interface('vlan5-on-eth1-101-1-17', 'vlan', '5')
first_vlan_intf.attach(first_intf)
second_vlan_intf = L2Interface('vlan5-on-eth1-102-1-17', 'vlan', '5')
second_vlan_intf.attach(second_intf)

# Attach the EPGs to the VLAN interfaces
first_epg.attach(first_vlan_intf)
second_epg.attach(second_vlan_intf)


# Push the tenant configuration to the APIC
resp = session.push_to_apic(tenant.get_url(),
                            tenant.get_json())
if not resp.ok:
    print('%% Error: Could not push the tenant configuration to APIC')

# Push the interface attachments to the APIC
resp = first_intf.push_to_apic(session)
if not resp.ok:
    print('%% Error: Could not push interface configuration to APIC')
resp = second_intf.push_to_apic(session)
if not resp.ok:
    print('%% Error: Could not push interface configuration to APIC')
