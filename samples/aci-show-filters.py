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
An application that logs on to the APIC and displays all
of the Filters.
"""
import sys
import acitoolkit.acitoolkit as ACI
from acisampleslib import get_login_info

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'An application that logs on to the APIC and displays all of the Filters.'
parser = get_login_info(description)
parser.add_argument('-t', '--tenant', help='The name of tenant where the entry forms', default=None)
parser.add_argument('-f', '--filter', help='The name of filter where the entry forms', default=None)
parser.add_argument('-T', '--applied_tenant', help='The name of tenant where the entry applied to', default=None)
parser.add_argument('-c', '--applied_contract', help='The name of contract where the entry applied to', default=None)

args = parser.parse_args()


# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)


def get_all_registered_filters():
    """
    :return: all the registered filters and the associated contracts and tenants.
    """
    rs_filters = {}
    ret = session.get('/api/node/class/vzRsSubjFiltAtt.json')
    for rs_f in ret.json()['imdata']:
        dn = rs_f['vzRsSubjFiltAtt']['attributes']['dn']
        tenant_name = dn.split('/')[1][3:]
        contract_name = dn.split('/')[2][4:]
        rs_filter_name = dn.split('/')[4][14:]
        tDn = rs_f['vzRsSubjFiltAtt']['attributes']['tDn']
        from_tenant = tDn.split('/')[1][3:]
        if rs_filter_name not in rs_filters.keys():
            rs_filters[rs_filter_name] = []
        rs_filters[rs_filter_name].append({'tenant': tenant_name, 'contract': contract_name, 'from_tenant': from_tenant})
    return rs_filters


def get_all_filter_entries():
    filter_entry_query_url = '/api/node/class/vzEntry.json'
    ret = session.get(filter_entry_query_url)
    return ret.json()['imdata']


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
        if f_entry[key] == args.__getattribute__(key):
            results.append(f_entry)
    return results


rs_filters = get_all_registered_filters()
filter_entries = get_all_filter_entries()

result = []
for filter_entry in filter_entries:
    dn = filter_entry['vzEntry']['attributes']['dn']
    tenant_name = dn.split('/')[1][3:]
    filter_name = dn.split('/')[2][4:]
    filter_entry_name = dn.split('/')[3][2:]
    fe = {'filter_entry': filter_entry_name, 'tenant': tenant_name}
    if filter_name in rs_filters.keys():
        for item in rs_filters[filter_name]:
            if tenant_name == item['from_tenant']:
                result.append({'filter_entry': filter_entry_name,
                               'filter': filter_name,
                               'tenant': tenant_name,
                               'applied_tenant': item['tenant'],
                               'applied_contract': item['contract']})


result = set_filter(result, 'tenant')
result = set_filter(result, 'filter')
result = set_filter(result, 'applied_tenant')
result = set_filter(result, 'applied_contract')

# Display the data downloaded
width = '20'
template = '{0:' + width + '} {1:' + width + '} {2:' + width + '} {3:' + width + '} {4:' + width + '}'
print template.format("FilterEntries", "Filter", "Tenant", "AppliedTenant", "AppliedContract")
print template.format("-------------", "------", "------", "-------------", "---------------")
for rec in result:
    print template.format(rec['filter_entry'], rec['filter'], rec['tenant'], rec['applied_tenant'], rec['applied_contract'])
