#!/usr/bin/env python
# Copyright (c) 2014 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
"""
Simple application that logs on to the APIC and displays all
of the Filters.
"""
import sys
# import acitoolkit.acitoolkit as ACI
import aaacitoolkit as ACI
from acisampleslib import get_login_info

# Take login credentials from the command line if provided
# Otherwise, take them from credentials.py file
parser = get_login_info()
args = parser.parse_args()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

# Download all of the filter entries
# and store the data as tuples in a list
data = []
filter_entries = ACI.FilterEntry.get(session)
for fe in filter_entries:
    dn = fe['vzEntry']['attributes']['dn']
    tenant_name = dn.split('/')[1][3:]
    filter_name = dn.split('/')[2][4:]
    filter_entry_name = dn.split('/')[3][2:]
    data.append((tenant_name, filter_name, filter_entry_name))

# tenants = ACI.Tenant.get(session)
# for tenant in tenants:
#     filter_entries = ACI.FilterEntry.get(session, tenant=tenant)
#     for fe in filter_entries:
#         dn = fe['vzEntry']['attributes']['dn']
#         tenant_name = dn.split('/')[1][3:]
#         filter_name = dn.split('/')[2][4:]
#         filter_entry_name = dn.split('/')[3][2:]
#         data.append((tenant_name, filter_name, filter_entry_name))

# tenants = ACI.Tenant.get(session)
# for tenant in tenants:
#     contracts = ACI.Contract.get(session, tenant)
#     for contract in contracts:
#         filter_entries = ACI.FilterEntry.get(session, parent=contract)
#         for fe in filter_entries:
#             dn = fe['vzEntry']['attributes']['dn']
#             tenant_name = dn.split('/')[1][3:]
#             filter_name = dn.split('/')[2][4:]
#             filter_entry_name = dn.split('/')[3][2:]
#             data.append((tenant_name, filter_name, filter_entry_name))

# Display the data downloaded
template = '{0:19} {1:30} {2:20}'
print template.format("Tenant", "Filter", "FilterEntries")
print template.format("------", "------", "-------------")
for rec in data:
    print template.format(*rec)
