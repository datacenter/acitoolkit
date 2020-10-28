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
# Copyright (c) 2020 Cisco Systems                                             #
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
Simple application that logs on to the APIC and displays all of the virtual
machine names and the associated MAC address of the virtual machine's virtual
NIC.
This also shows how direct APIC REST API calls can be used in conjunction with
acitoolkit.
"""
from acitoolkit import Session, Credentials
from tabulate import tabulate


def main():
    """
    Main Show VM Names Routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the virtual machine names.')
    creds = Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Make a direct call to the APIC REST API
    # Get all of the VMs (all objects of compVM class) and include the compVNic children
    # which contain the MAC address of the NIC.
    # The advantage of using acitoolkit Session.get() instead of direct Requests.get() calls
    # is that acitoolkit will automatically handle retries and pagination for queries with
    # large response data
    class_url = '/api/node/class/compVm.json?rsp-subtree=children&rsp-subtree-class=compVNic'
    ret = session.get(class_url)
    vm_list = ret.json()['imdata']

    # Process the response. We're looking for the VM name and the associated vNIC MAC addresses.
    data = []
    for vm in vm_list:
        vm_name = vm['compVm']['attributes']['name']
        for vnic in vm['compVm']['children']:
            vm_mac = vnic['compVNic']['attributes']['mac']
            # Store the VM name and MAC address. Note that VM names may be associated with
            # multiple MAC addresses if they have multiple vNICs.
            data.append((vm_name, vm_mac))

    # Display the data downloaded
    print(tabulate(data, headers=["VMNAME", "MACADDRESS"]))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
