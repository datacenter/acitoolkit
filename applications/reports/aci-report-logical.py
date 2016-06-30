#!/usr/bin/env python
################################################################################
#               _    ____ ___   ____                       _                   #
#              / \  / ___|_ _| |  _ \ ___ _ __   ___  _ __| |_ ___             #
#             / _ \| |    | |  | |_) / _ \ '_ \ / _ \| '__| __/ __|            #
#            / ___ \ |___ | |  |  _ <  __/ |_) | (_) | |  | |_\__ \            #
#           /_/   \_\____|___| |_| \_\___| .__/ \___/|_|   \__|___/            #
#                                        |_|                                   #
#                                                                              #
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
Simple application that logs on to the APIC and displays all
of the Interfaces.
"""
from operator import attrgetter
import sys
# noinspection PyPep8Naming
import acitoolkit.acitoolkit as ACI

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application that logs on to the APIC and displays reports for the logical model.'
creds = ACI.Credentials('apic, nosnapshotfiles', description)
creds.add_argument('-t', '--tenant',
                   type=str,
                   default=None,
                   help='Specify a particular tenant name')
creds.add_argument('-all', action="store_true",
                   help='Show all detailed information')
creds.add_argument('-basic', action="store_true", help='Show basic tenant info')
creds.add_argument('-context', action="store_true", help='Show Context info')
creds.add_argument('-bridgedomain', action="store_true", help='Show Bridge Domain info')
creds.add_argument('-contract', action="store_true", help='Show Contract info')
creds.add_argument('-taboo', action="store_true", help='Show Taboo (Deny) info')
creds.add_argument('-filter', action="store_true", help='Show Filter info')
creds.add_argument('-app_profile', action="store_true", help='Show Application Profile info')
creds.add_argument('-epg', action="store_true", help='Show Endpoint Group info')
# creds.add_argument('-svi', action="store_true", help='Show SVI info')
# creds.add_argument('-accessrule', action="store_true", help='Show Access Rule and Filter info')
creds.add_argument('-endpoint', action="store_true", help='Show End Point info')
# creds.add_argument('-portchannel', action="store_true", help='Show Port Channel and Virtual Port Channel info')
# creds.add_argument('-overlay', action="store_true", help='Show Overlay info')

args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)


def show_tenant_short(tenant_id):
    """
    Setup template and display header information for summary version of tenant info

    :param tenant_id: Optional tenant name to select a specific tenant.  If ommitted, will be all tenants.
    """

    if tenant_id:
        tenants = ACI.Tenant.get(session, tenant_id)
    else:
        tenants = ACI.Tenant.get(session)

    tables = ACI.Tenant.get_table(tenants, title='All Tenants ')
    text_string = tables[0].get_text(tablefmt='fancy_grid') + '\n'
    print text_string


def render_text_tenant(tenant):
    """
    Render the tenant info into a text string that can be directly display on
    a text monitor.
    :param tenant:
    """
    title = 'Tenant:{0} - '.format(tenant.name)
    text_string = ''
    if args.all or args.basic:
        tables = ACI.Tenant.get_table([tenant], title)
        text_string += tables[0].get_text(tablefmt='fancy_grid') + '\n'

    if args.all or args.context:
        text_string += render_tables(tenant, ACI.Context, title)

    if args.all or args.bridgedomain:
        text_string += render_tables(tenant, ACI.BridgeDomain, title)

    if args.all or args.contract:
        text_string += render_tables(tenant, ACI.Contract, title)

    if args.all or args.taboo:
        text_string += render_tables(tenant, ACI.Taboo, title)

    if args.all or args.filter:
        filters = []
        contracts = tenant.get_children(ACI.Contract)
        for contract in contracts:
            filter_entry = contract.get_children(ACI.FilterEntry)
            for flter in filter_entry:
                if flter not in filters:
                    filters.append(flter)
            subjects = contract.get_children(only_class=ACI.ContractSubject)
            for subject in subjects:
                subj_filters = subject.get_filters()
                for subj_filter in subj_filters:
                    subj_filt_entries = subj_filter.get_children(only_class=ACI.FilterEntry)
                    for subj_filt_entry in subj_filt_entries:
                        if subj_filt_entry not in filters:
                            filters.append(subj_filt_entry)

        tables = ACI.FilterEntry.get_table(filters, title)
        for table in tables:
            text_string += table.get_text(tablefmt='fancy_grid') + '\n'

    if args.all or args.app_profile:
        text_string += render_tables(tenant, ACI.AppProfile, title)

    if args.all or args.epg:
        epgs = []
        app_profiles = tenant.get_children(ACI.AppProfile)
        for app_profile in app_profiles:
            epgs.extend(app_profile.get_children(ACI.EPG))
        tables = ACI.EPG.get_table(epgs, title)

        for table in tables:
            text_string += table.get_text(tablefmt='fancy_grid') + '\n'

    if args.all or args.endpoint:
        epgs = []
        app_profiles = tenant.get_children(ACI.AppProfile)
        for app_profile in app_profiles:
            epgs.extend(app_profile.get_children(ACI.EPG))

        endpoints = []
        for epg in epgs:
            endpoints.extend(epg.get_children(ACI.Endpoint))

        tables = ACI.Endpoint.get_table(endpoints, title)

        for table in tables:
            text_string += table.get_text(tablefmt='fancy_grid') + '\n'

    return text_string


def render_tables(tenant, toolkit_class, title):
    """
    Will create a table and return it as a string
    with the title

    :param tenant:
    :param title: Title string for table
    :param toolkit_class:  Concrete class to build the table for
    :return: String version of the table
    """
    text_string = ''
    objs = tenant.get_children(toolkit_class)
    tables = toolkit_class.get_table(objs, title)

    for table in tables:
        text_string += table.get_text(tablefmt='fancy_grid') + '\n'

    return text_string


def show_tenant_long():
    """
    This function will display the long version of the tenant information.
    What to display is controlled through args
    """
    tenants = ACI.Tenant.get(session)

    # filter to only one tenant if specified
    if args.tenant:
        tenants = [ten for ten in tenants if ten.name == args.tenant]

    for tenant in sorted(tenants, key=attrgetter('name')):
        tenant = ACI.Tenant.get_deep(session, names=[tenant.name])

        if tenant:
            print render_text_tenant(tenant[0])


if (args.all or
        args.tenant or
        args.basic or
        args.context or
        args.bridgedomain or
        args.contract or
        args.taboo or
        args.filter or
        args.app_profile or
        args.epg or
        args.endpoint):
    show_tenant_long()
else:
    show_tenant_short(args.tenant)
