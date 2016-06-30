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
Simple application that logs on to the APIC and produces a report that can be used
for security compliance auditing.
"""
# TODO Show Service Graphs
# TODO Add statistics hit/miss counts

#from operator import attrgetter
import sys
# noinspection PyPep8Naming
from acitoolkit import *
import csv


# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = ('Simple application that logs on to the APIC and produces a report'
               ' that can be used for security compliance auditing.')
creds = Credentials('apic, nosnapshotfiles', description)
creds.add_argument('--csv',
                   type=str,
                   help='Output to a CSV file.')

args = creds.get()

# Login to APIC
session = Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

# Pull in the data from the APIC
tenants = Tenant.get_deep(session)

# Parse the APIC data
data = []
data.append(("Tenant",
             "Context",
             "BridgeDomain",
             "AppProfile",
             "ConsumerEPG",
             "NumberEndpointsInConsumerEPG"
             "ProviderEPG",
             "NumberEndpointsInProviderEPG"
             "ConsumedContract",
             "Protocol",
             "SourcePortRange",
             "DestPortRange",
             ))

for tenant in tenants:
    apps = tenant.get_children(only_class=AppProfile)
    for app in apps:
        epgs = app.get_children(only_class=EPG)
        for epg in epgs:
            num_consumer_epg_endpoints = len(epg.get_children(only_class=Endpoint))
            bd = epg.get_bd()
            if bd is not None:
                vrf = bd.get_context()
            else:
                vrf = None
            for consumed_contract in epg.get_all_consumed():
                # Get the providing contracts
                providing_epgs = consumed_contract.get_all_providing_epgs()
                if not len(providing_epgs):
                    continue
                subjects = consumed_contract.get_children(only_class=ContractSubject)
                for subject in subjects:
                    filters = subject.get_filters()
                    for filter in filters:
                        entries = filter.get_children(only_class=FilterEntry)
                        for entry in entries:
                            for providing_epg in providing_epgs:
                                num_provider_epg_endpoints = len(providing_epg.get_children(only_class=Endpoint))
                                data.append((tenant.name,
                                             getattr(vrf, 'name', None),
                                             getattr(bd, 'name', None),
                                             app.name,
                                             epg.name,
                                             num_consumer_epg_endpoints,
                                             providing_epg.name,
                                             num_provider_epg_endpoints,
                                             consumed_contract.name,
                                             entry.prot,
                                             entry.sFromPort + '-' + entry.sToPort,
                                             entry.dFromPort + '-' + entry.dToPort,
                                             ))

# Write to the CSV file if specified on command line
if args.csv is not None:
    with open(args.csv, 'wb') as csvfile:
        my_csv_writer = csv.writer(csvfile)
        for entry in data:
            my_csv_writer.writerow(entry)
else:
    # Dump the output to the screen
    for entry in data:
        print entry
