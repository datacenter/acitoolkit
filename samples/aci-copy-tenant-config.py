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
# Copyright (c) 2016 Cisco Systems                                             #
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
Application dealing with tenant configurations
It can download a tenant configuration from the APIC and store it as raw JSON in a file.
It can also push a tenant configuration stored as raw JSON in a file to the APIC.
"""
import json
from acitoolkit import Credentials, Session, Tenant


def pull_config_from_apic(session, tenant_name, filename):
    """
    Pull the tenant configuration from the APIC

    :param session: Instance of Session class. Assumed to be logged in to the APIC.
    :param tenant_name: String containing the tenant name
    :param filename: String containing the file name
    :return: None
    """
    tenants = Tenant.get_deep(session, names=[tenant_name], config_only=True)
    output_file = open(filename, 'w')
    for tenant in tenants:
        output_file.write(json.dumps(tenant.get_json(), indent=4, sort_keys=True))
    output_file.close()


def push_config_to_apic(session, tenant_name, filename):
    """
    Push the tenant configuration to the APIC

    :param session: Instance of Session class. Assumed to be logged in to the APIC.
    :param filename: String containing the file name
    :return: None
    """
    tenant = Tenant(tenant_name)
    with open(filename) as input_file:
        tenant_json = json.load(input_file)
    tenant_json['fvTenant']['attributes']['name'] = tenant_name
    resp = session.push_to_apic(tenant.get_url(), tenant_json)
    if resp.ok:
        print 'Successfully pushed configuration to APIC.'
    else:
        print 'Could not push configuration to APIC.', resp.text


def main():
    """
    Main execution routine

    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Application dealing with tenant configuration. '
                   'It can download a tenant configuration from the APIC and store it as raw JSON in a file. '
                   'It can also push a tenant configuration stored as raw JSON in a file to the APIC.')
    creds = Credentials(('apic', 'nosnapshotfiles'), description)
    creds.add_argument('--config', default=None, help='Configuration file to push/pull tenant configuration')
    creds.add_argument('--tenant', default=None, help='Tenant name')
    group = creds.add_mutually_exclusive_group()
    group.add_argument('--push-to-apic', action='store_true',
                       help='Push the tenant configuration file to the APIC')
    group.add_argument('--pull-from-apic', action='store_true',
                       help=('Pull the tenant configuration from the APIC and'
                             'store in the specified configuration file'))

    # Get the command line arguments
    args = creds.get()

    # Sanity check the command line arguments
    if args.config is None:
        print '%% No configuration file given.'
        creds.print_help()
        return
    if args.tenant is None:
        print '%% No Tenant name given.'
        creds.print_help()
        return
    if not args.push_to_apic and not args.pull_from_apic:
        print '%% No direction (push-to-apic/pull-from-apic) given.'
        creds.print_help()
        return

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        return

    # Do the work
    if args.pull_from_apic:
        pull_config_from_apic(session, args.tenant, args.config)

    if args.push_to_apic:
        push_config_to_apic(session, args.tenant, args.config)

if __name__ == '__main__':
    main()
