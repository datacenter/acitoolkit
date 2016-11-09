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
Delete tenants named with the specified string.
"""
from acitoolkit import Session, Tenant, Credentials


def main():
    """
    Main create tenant routine
    :return: None
    """
    # Get all the arguments
    description = 'It logs in to the APIC and will delete tenants named with the specified string.'
    creds = Credentials(['apic', 'nosnapshotfiles'], description)
    group = creds.add_mutually_exclusive_group()
    group.add_argument('--startswith', default=None,
                       help='String to match that starts the tenant name')
    group.add_argument('--endswith', default=None,
                       help='String to match that ends the tenant name')
    group.add_argument('--exactmatch', default=None,
                       help='String that exactly matches the tenant name')
    group.add_argument('--contains', default=None,
                       help='String that is contained in the tenant name')
    creds.add_argument('--force', action='store_true',
                       help='Attempt to remove the tenants without prompting for confirmation')
    args = creds.get()

    # Login to the APIC
    apic = Session(args.url, args.login, args.password)
    resp = apic.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Get all of the Tenants
    tenants = Tenant.get(apic)

    # Find the list of Tenants to delete according to command line options
    tenants_to_delete = []
    for tenant in tenants:
        if args.startswith is not None:
            if tenant.name.startswith(args.startswith):
                tenants_to_delete.append(tenant)
        elif args.endswith is not None:
            if tenant.name.endswith(args.endswith):
                tenants_to_delete.append(tenant)
        elif args.exactmatch is not None:
            if args.exactmatch == tenant.name:
                tenants_to_delete.append(tenant)
        elif args.contains is not None:
            if args.contains in tenant.name:
                tenants_to_delete.append(tenant)

    # Query the user to be sure of deletion
    if not args.force:
        for tenant in tenants_to_delete:
            prompt = 'Delete tenant %s ? [y/N]' % tenant.name
            try:
                resp = raw_input(prompt)
            except NameError:
                resp = input(prompt)
            if not resp.lower().startswith('y'):
                tenants_to_delete.remove(tenant)
                print 'Skipping tenant', tenant.name

    # Delete the tenants
    for tenant in tenants_to_delete:
        tenant.mark_as_deleted()
        resp = tenant.push_to_apic(apic)
        if resp.ok:
            print 'Deleted tenant', tenant.name
        else:
            print 'Could not delete tenant', tenant.name
            print resp.text


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
