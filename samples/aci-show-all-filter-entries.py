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
description = 'An application that logs on to the APIC and displays Filter Entries.'
creds = ACI.Credentials('apic', description)
creds.add_argument('-t', '--tenant',
                   help='The name of a specific tenant to get filter entries. If none specified, all tenants is assumed.',
                   default=None)

args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')
    sys.exit(0)

data = []
tenant_names = []
if args.tenant:
    tenant_names.append(args.tenant)

# Get the tenant object hierarchy.  limit_to is just an optimization
tenants = ACI.Tenant.get_deep(session, names=tenant_names, limit_to=['fvTenant', 'vzFilter', 'vzEntry'])

longest_names = {'Tenant': len('Tenant'),
                 'Filter': len('Filter'),
                 'Entry': len('Entry')}
for tenant in tenants:
    for aci_filter in tenant.get_children(ACI.Filter):
        for filter_entry in aci_filter.get_children(ACI.FilterEntry):
            if len(tenant.name) > longest_names['Tenant']:
                longest_names['Tenant'] = len(tenant.name)
            if len(aci_filter.name) > longest_names['Filter']:
                longest_names['Filter'] = len(aci_filter.name)
            if len(filter_entry.name) > longest_names['Entry']:
                longest_names['Entry'] = len(filter_entry.name)
            data.append({'Tenant': tenant.name,
                         'Filter': aci_filter.name,
                         'Entry': filter_entry})

# Display the data downloaded
width = '20'
template = '{0:' + str(longest_names["Tenant"]) + '} {1:' + str(longest_names["Filter"]) + '} {2:' + str(longest_names["Entry"]) + '}'
print(template.format("Tenant", "Filter", "Entry"))
print(template.format('-' * longest_names["Tenant"], '-' * longest_names["Filter"], '-' * longest_names["Entry"]))
for rec in data:
    print(template.format(rec['Tenant'], rec['Filter'], rec['Entry']))
