#!/usr/bin/env python
# Copyright (c) 2015 Cisco Systems
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
import acitoolkit.aciphysobject as ACI_PHYS
from ReportLib import Report
# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application that logs on to the APIC and displays stats for all of the Interfaces.'
creds = ACI.Credentials('apic', description)
creds.add_argument('-s', '--switch',
                   type=str,
                   default = None,
                   help='Specify a particular switch id, e.g. "102"')
creds.add_argument('-v', '--verbose',action="store_true",
                   help='Show detailed information')
args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

def show_switch_short(switch_id) :
    
    # setup template and display header information
    template = "{0:^7} | {1:^12} | {2:^5} | {3:^15} | {4:^5} | {5:^16} | {6:^6} | {7:^20} | {8:^20} | {9:^8} | {10:^11}"
    line_template = "{0:-^7}-+-{0:-^12}-+-{0:-^5}-+-{0:-^15}-+-{0:-^5}-+-{0:-^16}-+-{0:-^6}-+-{0:-^20}-+-{0:-^20}-+-{0:-^8}-+-{0:-^11}"
    print template.format("Node ID", "Name","Role","Model","Ports","State","Health","In-Band Mgmt IP", "Out-of-band Mgmt IP", "Firmware", "Serial")
    print line_template.format("")
    
    if switch_id:
        switches = ACI_PHYS.Node.get(session,'1',switch_id)
    else:
        switches = ACI_PHYS.Node.get(session)
    for switch in sorted(switches):
        if switch.role != 'controller':
            print template.format(switch.node,
                              switch.name,
                              switch.role,
                              switch.model,
                              switch.num_ports,
                              switch.state,
                              switch.health,
                              switch.inb_mgmt_ip,
                              switch.oob_mgmt_ip,
                              switch.firmware,
                              switch.serial)

def show_switch_long(switch_id) :
    report = Report(session)
    report.switch(switch_id,'text')

if args.verbose:
    show_switch_long(args.switch)
else:
    show_switch_short(args.switch)
    


    

