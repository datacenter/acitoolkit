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
description = 'Simple application that logs on to the APIC and displays stats for all of the Interfaces.'
parser = get_login_info(description)
args = parser.parse_args()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

# setup template and display header information
template = "{0:17} {1:12} {2:12} {3:16} {4:16} {5:16} {6:16}"
print template.format("   INTERFACE  ", "TOT RX PACKETS", "TOT TX PACKETS", "RX PKTs/Sec", "TX PKTs/Sec", "RX BYTES/Sec", "TX BYTES/Sec")
print template.format("--------------", "------------ ", "------------ ", "---------------", "---------------", "---------------", "---------------")
template = "{0:17} {1:12,} {2:12,} {3:16,.2f} {4:16,.2f} {5:16,.2f} {6:16,.2f}"
    
# Download all of the interfaces and get their stats
# and display the stats
data = []
interfaces = ACI.Interface.get(session)
for interface in sorted(interfaces):
    interface.stats.get()
    
    rec = []
    for (counterFamily, counterName) in [('ingrTotal','pktsAvg'),('egrTotal','pktsAvg'),
                            ('ingrTotal','pktsRateAvg'),('egrTotal','pktsRateAvg'),
                            ('ingrTotal','bytesRateAvg'),('egrTotal','bytesRateAvg')] :
        
        rec.append(interface.stats.retrieve(counterFamily,'5min',0,counterName))
        
    print template.format(interface.name, *rec)


    

