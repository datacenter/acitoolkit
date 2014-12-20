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
of the Contexts.
"""
import sys
import acitoolkit.acitoolkit as ACI
from acisampleslib import get_login_info

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application that logs on to the APIC and displays all of the Contexts.'
parser = get_login_info(description)
args = parser.parse_args()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

# Download all of the contexts
# and store the data as tuples in a list
data = []
tenants = ACI.Tenant.get(session)
for tenant in tenants:
    contexts = ACI.Context.get(session, tenant)
    for context in contexts:
        data.append((tenant.name, context.name))

# IPython.embed()

# Display the data downloaded
template = '{0:19} {1:20}'
print template.format("Tenant", "Context")
print template.format("------", "-------")
for rec in data:
    print template.format(*rec)
