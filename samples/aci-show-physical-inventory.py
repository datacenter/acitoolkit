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

from acitoolkit.aciphysobject import *
from acisampleslib import get_login_info

def print_inventory(item):
    for child in item.get_children():
        print_inventory(child)
    print item.info()

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables
description = 'Simple application that logs on to the APIC and displays the physical inventory.'
parser = get_login_info(description)
args = parser.parse_args()

# Login to APIC
session = Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

# Print the inventory of each Pod
pods = Pod.get(session) 
for pod in pods:
    pod.populate_children(deep=True)
    pod_name = 'Pod: %s' % pod.name
    print pod_name
    print '=' * len(pod_name)
    print_inventory(pod)
    
