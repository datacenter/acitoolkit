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
Simple application using event subscription for the Tenant class.
When run, this application will log into the APIC and subscribe to
events on the Tenant class.  If a new tenant is created, the event
will be printed on the screen.  Likewise, if an existing tenant is
deleted.
"""
import sys
import acitoolkit.acitoolkit as ACI
from acisampleslib import get_login_info

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application using event subscription for the Tenant class. When run, this application will log into the APIC and subscribe to events on the Tenant class.  If a new tenant is created, the event will be printed on the screen.  Likewise, if an existing tenant is deleted.'
parser = get_login_info(description)
args = parser.parse_args()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

ACI.Tenant.subscribe(session)

while True:
    if ACI.Tenant.has_events(session):
        tenant = ACI.Tenant.get_event(session)
        if tenant.is_deleted():
            print 'Tenant', tenant.name, 'has been deleted.'
        else:
            print 'Tenant', tenant.name, 'has been created or modified.'
    
