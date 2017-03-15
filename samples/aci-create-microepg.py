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
This example logs into the APIC and creates a tenant with an application profile
that contains a microEPG.  A single base EPG is used to provide the networking and
many microepgs can use the same base EPG. Note that the base EPG is statically bound
to a leaf switch in this example (hardcoded as leaf 101 and using untagged vlan 1).
"""
from acitoolkit import (Credentials, Session, Tenant, AppProfile, EPG, Context,
                        BridgeDomain, AttributeCriterion)


def main():
    """
    Main routine
    """
    # Get all the arguments
    description = 'Creates a tenant with a micro-EPG.'
    creds = Credentials('apic', description)
    args = creds.get()

    # Login to the APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Create the Tenant and AppProfile
    tenant = Tenant('acitoolkit-microepg-example')
    app_profile = AppProfile('myapp', tenant)

    # Create a Base EPG that will provide networking for the microEPGs
    base_epg = EPG('base', app_profile)
    base_epg.add_static_leaf_binding('101', 'vlan', '1', encap_mode='untagged')
    vrf = Context('myvrf', tenant)
    bd = BridgeDomain('mybd', tenant)
    bd.add_context(vrf)
    base_epg.add_bd(bd)

    # Create a microEPG
    microepg = EPG('microepg', app_profile)
    microepg.is_attributed_based = True
    microepg.set_base_epg(base_epg)
    # Add an IP address to this microepg
    criterion = AttributeCriterion('criterion', microepg)
    criterion.add_ip_address('1.2.3.4')

    # Contracts can be provided/consumed from the microepg as desired (not shown)

    # Push the tenant to the APIC
    resp = tenant.push_to_apic(session)
    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
