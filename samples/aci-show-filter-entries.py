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
An application that logs on to the APIC and displays all
of the Filters.
"""
import sys
import acitoolkit.acitoolkit as ACI

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'An application that logs on to the APIC and displays all of the Filter Entries.'
creds = ACI.Credentials('apic', description)
creds.add_argument('-e', '--filter_entry', help='The name of Filter Entry', default=None)
creds.add_argument('-c', '--contract', help='The name of contract', default=None)
creds.add_argument('-t', '--tenant', help='The name of tenant', default=None)
args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')
    sys.exit(0)

# Download all of the interfaces
# and store the data as tuples in a list
data = []
tenants = ACI.Tenant.get(session)
for tenant in tenants:
    contracts = ACI.Contract.get(session, tenant)
    for contract in contracts:
        filter_entries = ACI.FilterEntry.get(session, parent=contract, tenant=tenant)
        for fe in filter_entries:
            data.append({'filter_entry': fe.name,
                         'contract': fe.get_parent().name,
                         'tenant': fe.get_parent().get_parent().name})


def set_filter(data, key):
    """
    :param data: the data to be filtered
    :param key: the key value that needed to be compared
    :return: return an array which elements pass the filter test
    """
    if not args.__getattribute__(key):
        return data
    results = []
    for f_entry in data:
        if args.__getattribute__(key) in f_entry[key]:
            results.append(f_entry)
    return results


data = set_filter(data, 'filter_entry')
data = set_filter(data, 'tenant')
data = set_filter(data, 'contract')

# Display the data downloaded
width = '20'
template = '{0:' + width + '} {1:' + width + '} {2:' + width + '}'
print(template.format("Filter Entries", "Contract", "Tenant"))
print(template.format("--------------", "--------", "------"))
for rec in data:
    print(template.format(rec['filter_entry'], rec['contract'], rec['tenant']))
