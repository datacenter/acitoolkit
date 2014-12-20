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
of the Interfaces.
"""
import sys
import acitoolkit.acitoolkit as ACI
from acisampleslib import get_login_info

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application that logs on to the APIC and displays all of the Interfaces.'
parser = get_login_info(description)
args = parser.parse_args()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

# Download all of the interfaces
# and store the data as tuples in a list
data = []
interfaces = ACI.Interface.get(session)
for interface in interfaces:
    data.append((interface.attributes['if_name'],
                 interface.attributes['porttype'],
                 interface.attributes['adminstatus'],
                 interface.attributes['operSt'],
                 interface.attributes['speed'],
                 interface.attributes['mtu']))

# Display the data downloaded
template = "{0:17} {1:6} {2:^6} {3:^6} {4:7} {5:6}"
print template.format("INTERFACE", "TYPE", "ADMIN", "OPER", "SPEED", "MTU")
print template.format("---------", "----", "------", "------", "-----", "___")
for rec in data:
    print template.format(*rec)
