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
of the Endpoints.
"""
import sys
import acitoolkit.acitoolkit as ACI

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = ('Simple application that logs on to the APIC'
               ' and displays all of the Endpoints.')
creds = ACI.Credentials('apic', description)
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
endpoints = ACI.Endpoint.get(session)
for ep in endpoints:
    epg = ep.get_parent()
    app_profile = epg.get_parent()
    tenant = app_profile.get_parent()
    data.append((ep.mac, ep.ip, ep.if_name, ep.encap, tenant.name, app_profile.name, epg.name))

# Display the data downloaded
template = "{0:19} {1:17} {2:15} {3:10} {4:10} {5:15} {6:15}"
print(template.format("MACADDRESS",        "IPADDRESS",        "INTERFACE",     "ENCAP",      "TENANT", "APP PROFILE", "EPG"))
print(template.format("-----------------", "---------------", "--------------", "----------", "------", "-----------", "---"))
for rec in data:
    print(template.format(*rec))
