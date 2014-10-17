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
EPGs.  Before running, please make sure that the credentials.py
file has the URL, LOGIN, and PASSWORD set for your APIC environment.
"""
import acitoolkit as ACI
import credentials

# Login to APIC
session = ACI.Session(credentials.URL, credentials.LOGIN, credentials.PASSWORD)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'

# Download all of the tenants, app profiles, and EPGs
# and store the names as tuples in a list
data = []
tenants = ACI.Tenant.get(session)
for tenant in tenants:
    apps = ACI.AppProfile.get(session, tenant)
    for app in apps:
        epgs = ACI.EPG.get(session, app, tenant)
        for epg in epgs:
            data.append((tenant.name, app.name, epg.name))

# Display the data downloaded
template = "{0:19} {1:20} {2:15}"
print template.format("TENANT", "APP_PROFILE", "EPG")
print template.format("------", "-----------", "---")
for rec in data:
    print template.format(*rec)
