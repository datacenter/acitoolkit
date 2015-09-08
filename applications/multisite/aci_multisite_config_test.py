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
Configure the fabric to run the multisite test suite
"""
import argparse
import json

from acitoolkit.acisession import Session
from acitoolkit.acitoolkit import (
    AppProfile, BridgeDomain, Context, Contract, EPG, FilterEntry, L2Interface,
    L3Interface, OSPFInterface, OSPFRouter, OutsideEPG, Tenant
)
from acitoolkit.aciphysobject import Interface
from multisite_credentials import *


def setup_multisite_test(printonly=False, delete=False):
    # Create the Tenant
    tenant1 = Tenant('multisite')

    # Create the Application Profile
    app = AppProfile('my-demo-app', tenant1)

    # Create the EPGs
    web_epg = EPG('web-frontend', app)
    db_epg = EPG('database-backend', app)

    # Create a Context and BridgeDomain
    # Place both EPGs in the Context and in the same BD
    context = Context('VRF-1', tenant1)
    bd = BridgeDomain('BD-1', tenant1)
    bd.add_context(context)
    web_epg.add_bd(bd)
    db_epg.add_bd(bd)

    # Define a contract with a single entry
    contract = Contract('multisite_mysqlcontract', tenant1)
    entry1 = FilterEntry('entry1',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='3306',
                         dToPort='3306',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='1',
                         sToPort='65535',
                         tcpRules='unspecified',
                         parent=contract)

    # Provide the contract from 1 EPG and consume from the other
    db_epg.provide(contract)
    web_epg.consume(contract)

    context = Context('ctx0', tenant1)
    #contract = Contract('contract', tenant)
    phyif = Interface('eth', '1', '102', '1', '25')
    l2if = L2Interface('eth 1/102/1/25', 'vlan', '500')
    l2if.attach(phyif)
    l3if = L3Interface('l3if')
    l3if.set_l3if_type('ext-svi')
    l3if.set_addr('20.0.0.1/16')
    l3if.add_context(context)
    l3if.attach(l2if)

    #l3if.networks.append('1.1.1.1/32')
    #outside.provide(contract)
    l3if.attach(l2if)
    rtr = OSPFRouter('rtr-1')
    rtr.set_router_id('101.101.101.101')
    rtr.set_node_id('102')
    # net1 = OutsideNetwork('1.1.1.1/32')
    # net1.network = '1.1.1.1/32'
    # net1.provide(contract)
    ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='0.0.0.1')
    ospfif.attach(l3if)
    # ospfif.networks.append(net1)
    outside = OutsideEPG('multisite-l3out', tenant1)
    outside.attach(ospfif)
    #outside.add_context(context)

    # Create the Tenant
    tenant2 = Tenant('multisite')

    # Create the Application Profile
    app = AppProfile('my-demo-app', tenant2)

    # Create the EPGs
    web_epg = EPG('web-frontend', app)

    # Create a Context and BridgeDomain
    # Place both EPGs in the Context and in the same BD
    context = Context('VRF-1', tenant2)
    bd = BridgeDomain('BD-1', tenant2)
    bd.add_context(context)
    web_epg.add_bd(bd)

    context = Context('ctx0', tenant2)
    #contract = Contract('contract', tenant)
    phyif = Interface('eth', '1', '102', '1', '25')
    l2if = L2Interface('eth 1/102/1/25', 'vlan', '500')
    l2if.attach(phyif)
    l3if = L3Interface('l3if')
    l3if.set_l3if_type('ext-svi')
    l3if.set_addr('20.0.0.2/16')
    l3if.add_context(context)
    l3if.attach(l2if)
    #outside.provide(contract)
    l3if.attach(l2if)
    rtr = OSPFRouter('rtr-1')
    rtr.set_router_id('102.102.102.102')
    rtr.set_node_id('102')
    ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='0.0.0.1')
    ospfif.attach(l3if)
    #ospfif.networks.append('1.1.1.1/32')
    #ospfif.networks.append('1.1.1.2/32')
    outside = OutsideEPG('multisite-l3out', tenant2)
    outside.attach(ospfif)

    if not printonly:
        # Login to APIC and push the config
        session = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        session.login()
        # Cleanup (uncomment the next line to delete the config)
        if delete:
            print 'Deleting...'
            tenant1.mark_as_deleted()
        resp = tenant1.push_to_apic(session)
        if resp.ok:
            # Print what was sent
            print('Pushed the following JSON to the APIC', resp.text)
        else:
            print resp, resp.text
    print('URL: '  + str(tenant1.get_url()))
    print('JSON:')
    print json.dumps(tenant1.get_json(), indent=4, separators=(',',':'))


    if not printonly:
        # Login to APIC and push the config
        session = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        session.login()
        # Cleanup (uncomment the next line to delete the config)
        if delete:
            tenant2.mark_as_deleted()
        resp = tenant2.push_to_apic(session)
        if resp.ok:
            # Print what was sent
            print('Pushed the following JSON to the APIC', resp.text)
        else:
            print resp, resp.text
    print('URL: '  + str(tenant2.get_url()))
    print('JSON:')
    print json.dumps(tenant2.get_json(), indent=4, separators=(',',':'))

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='')
        parser.add_argument('--delete', action='store_true')
        parser.add_argument('--printonly', action='store_true')
        args = parser.parse_args()
        setup_multisite_test(printonly=args.printonly, delete=args.delete)
    except KeyboardInterrupt:
        pass
