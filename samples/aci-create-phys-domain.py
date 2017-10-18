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
It logs in to the APIC and will create a physical Domain.

"""
import acitoolkit.acitoolkit as aci

# Define static values to pass (edit these for your environment)

POOL_NAME = 'dvs-vlans'
ENCAP_TYPE = 'vlan'
VLAN_START = '3150'
VLAN_END = '3200'
POOL_MODE = 'dynamic'


def main():
    """
    Main create VMM routine
    :return: None
    """
    # Get all the arguments
    description = 'Create Physical Domain'
    creds = aci.Credentials('apic', description)
    creds.add_argument('--phys', help='name of the physical domain')
    args = creds.get()

    # Login to the APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Define dynamic vlan range
    vlans = aci.NetworkPool(POOL_NAME, ENCAP_TYPE, VLAN_START, VLAN_END, POOL_MODE)

    # Commit VLAN Range
    vlanresp = session.push_to_apic(vlans.get_url(), vlans.get_json())

    if not vlanresp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(vlanresp.text)


    # Create Physical Domain object
    if args.phys:
        phys_d = aci.PhysDomain(args.phys)
    else:
        phys_d = aci.PhysDomain("test-phys-domain")

    phys_d.add_network(vlans)

    # Commit Changes
    resp = session.push_to_apic(phys_d.get_url(), phys_d.get_json())

    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
