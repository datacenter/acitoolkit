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
Demo of printing a Port Channel configuration
"""
from acitoolkit.acitoolkit import Interface, PortChannel, Tenant, AppProfile, L2Interface, EPG


def main():
    """
    Main execution routine

    :return: None
    """
    # Create the physical interface objects
    intf1 = Interface('eth', '1', '101', '1', '38')
    intf2 = Interface('eth', '1', '101', '1', '39')
    intf3 = Interface('eth', '1', '102', '1', '38')
    intf4 = Interface('eth', '1', '102', '1', '39')

    # Create a port channel and add physical interfaces
    pc = PortChannel('pc1')
    pc.attach(intf1)
    pc.attach(intf2)
    pc.attach(intf3)
    pc.attach(intf4)
    # pc.mark_as_deleted()

    # Create a VLAN interface on the port channel
    # This is the L2 interface representing a single VLAN encap
    # on this particular interface.
    vlan5_on_pc = L2Interface('vlan5_on_pc', 'vlan', '5')
    vlan5_on_pc.attach(pc)

    # Create a tenant, app profile, and epg
    tenant = Tenant('acitoolkitdemo')
    app = AppProfile('app', tenant)
    epg = EPG('epg', app)

    # Connect EPG to the VLAN interface
    # Remember, this VLAN interface is on the port channel we created
    # so the EPG will be attached to the port channel on VLAN 5
    epg.attach(vlan5_on_pc)

    # Print the resulting JSON
    print(pc.get_json())
    print(tenant.get_json())

if __name__ == '__main__':
    main()
