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
of the physical nodes; both belonging to and connected to the
fabric.
"""
import sys
from acitoolkit.acitoolkit import Session, Credentials
from acitoolkit.aciphysobject import Node, ENode

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application that logs on to the APIC and displays all of the physical nodes; both belonging to and connected to the fabric.'
creds = Credentials('apic', description)
args = creds.get()

# Login to APIC
session = Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print('%% Could not login to APIC')
    sys.exit(0)

# List of classes to get and print
phy_classes = (Node, ENode)

for phy_class in phy_classes:
    # Print the class name
    class_name = phy_class.__name__
    print(class_name)
    print('=' * len(class_name))

    # Get and print all of the items from the APIC
    items = phy_class.get(session)
    for item in items:
        print(item.info())
