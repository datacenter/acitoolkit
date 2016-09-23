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
Simple application to statically connect an EPG to a specific interface using
a specific VLAN.

It logs in to the APIC and will create the tenant, application profile,
and EPG if they do not exist already.  It then connects it to the specified
interface using the VLAN encapsulation specified.

Before running, please make sure that the credentials.py
file has the URL, LOGIN, and PASSWORD set for your APIC environment.
"""
import acitoolkit.acitoolkit as ACI
import credentials

# Define static values to pass (edit these if you wish to set differently)
TENANT_NAME = 'cisco'
APP_NAME = 'fancyapp'
EPG_NAME = 'redis'
INTERFACE = {'type': 'eth',
             'pod': '1', 'node': '101', 'module': '1', 'port': '65'}
VLAN = {'name': 'vlan5',
        'encap_type': 'vlan',
        'encap_id': '5'}

# Login to the APIC
session = ACI.Session(credentials.URL, credentials.LOGIN, credentials.PASSWORD)
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')

# Create the Tenant, App Profile, and EPG
tenant = ACI.Tenant(TENANT_NAME)
app = ACI.AppProfile(APP_NAME, tenant)
epg = ACI.EPG(EPG_NAME, app)

# Create the physical interface object
intf = ACI.Interface(INTERFACE['type'],
                     INTERFACE['pod'],
                     INTERFACE['node'],
                     INTERFACE['module'],
                     INTERFACE['port'])

# Create a VLAN interface and attach to the physical interface
vlan_intf = ACI.L2Interface(VLAN['name'], VLAN['encap_type'], VLAN['encap_id'])
vlan_intf.attach(intf)

# Attach the EPG to the VLAN interface
epg.attach(vlan_intf)

# Push the tenant config to the APIC
resp = tenant.push_to_apic(session)
if not resp.ok:
    print('%% Error: Could not push tenant configuration to APIC')

# Push the interface attachment to the APIC
resp = intf.push_to_apic(session)
if not resp.ok:
    print('%% Error: Could not push interface configuration to APIC')
