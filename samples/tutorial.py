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
from acitoolkit.acitoolkit import *
"""
Create a tenant with a single EPG and assign it statically to 2 interfaces.
This is the minimal configuration necessary to enable packet forwarding
within the ACI fabric.
"""
# Create the Tenant
tenant = Tenant('tutorial')

# Create the Application Profile
app = AppProfile('myapp', tenant)

# Create the EPG
epg = EPG('myepg', app)

# Create a Context and BridgeDomain
context = Context('myvrf', tenant)
bd = BridgeDomain('mybd', tenant)
bd.add_context(context)

# Place the EPG in the BD
epg.add_bd(bd)

# Declare 2 physical interfaces
if1 = Interface('eth', '1', '101', '1', '15')
if2 = Interface('eth', '1', '101', '1', '16')

# Create VLAN 5 on the physical interfaces
vlan5_on_if1 = L2Interface('vlan5_on_if1', 'vlan', '5')
vlan5_on_if1.attach(if1)

vlan5_on_if2 = L2Interface('vlan5_on_if2', 'vlan', '5')
vlan5_on_if2.attach(if2)

# Attach the EPG to the VLANs
epg.attach(vlan5_on_if1)
epg.attach(vlan5_on_if2)

# Get the APIC login credentials
description = 'acitoolkit tutorial application'
creds = Credentials('apic', description)
creds.add_argument('--delete', action='store_true',
                   help='Delete the configuration from the APIC')
args = creds.get()

# Delete the configuration if desired
if args.delete:
    tenant.mark_as_deleted()

# Login to APIC and push the config
session = Session(args.url, args.login, args.password)
session.login()
resp = tenant.push_to_apic(session)
if resp.ok:
    print 'Success'

# Print what was sent
print 'Pushed the following JSON to the APIC'
print 'URL:', tenant.get_url()
print 'JSON:', tenant.get_json()
