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
Sample of creating a BGP peer
"""

from acitoolkit.acitoolkit import Credentials, Session, Tenant, Context, OutsideL3, OutsideEPG, Contract
from acitoolkit.acitoolkit import Interface, L2Interface, L3Interface, BGPSession


def main():
    """
    Main execution routine

    :return: None
    """
    creds = Credentials('apic')
    args = creds.get()
    session = Session(args.url, args.login, args.password)
    session.login()

    tenant = Tenant('cisco')
    context = Context('ctx1', tenant)
    outside_l3 = OutsideL3('out-1', tenant)
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
    outside_epg = OutsideEPG('outepg', outside_l3)
    outside_epg.provide(contract1)
    outside_l3.add_context(context)
    outside_epg.consume(contract1)
    outside_l3.attach(bgpif)
    bgp_json = bgpif.get_json()

    resp = session.push_to_apic(tenant.get_url(),
                                tenant.get_json())

    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)

if __name__ == '__main__':
    main()
