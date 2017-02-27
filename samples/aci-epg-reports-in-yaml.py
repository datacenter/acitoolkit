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
Simple application that logs on to the APIC and displays all
EPGs.
"""
import socket
import yaml
import sys
from pprint import pprint
import acitoolkit.acitoolkit as aci
from acitoolkit.acitoolkit import Tenant, AppProfile, EPG, Endpoint

def main():
    """
    Main show EPGs routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the EPGs.')
    creds = aci.Credentials('apic', description)
    args = creds.get()
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Download all of the tenants, app profiles, and EPGs
    # and store the names as tuples in a list
    tenants = Tenant.get_deep(session)
    tenants_list = []
    for tenant in tenants:
        tenants_dict = {}
        tenants_dict['name'] = tenant.name
        
        if tenant.descr:
            tenants_dict['description'] = tenant.descr
            
        tenants_dict['app-profiles'] = []
        for app in tenant.get_children(AppProfile):
            app_profiles = {}
            app_profiles['name'] =app.name
            if app.descr:
                app_profiles['description'] = app.descr
            app_profiles['epgs'] = []
            
            
            for epg in app.get_children(EPG):
                epgs_info = {}
                epgs_info['name'] = epg.name
                if epg.descr:
                    epgs_info['description']  = epg.descr
                epgs_info['endpoints'] = []
                
                for endpoint in epg.get_children(Endpoint):
                    endpoint_info = {}
                    endpoint_info['name'] = endpoint.name
                    if endpoint.ip != '0.0.0.0':
                        endpoint_info['ip'] = endpoint.ip
                        try:
                            hostname = socket.gethostbyaddr(endpoint.ip)[0]
                        except socket.error:
                            hostname = None
                        if hostname:
                            endpoint_info['hostname'] = hostname
                    if endpoint.descr:
                        endpoint_info['description'] = endpoint.descr
                        
                    epgs_info['endpoints'].append(endpoint_info)
                app_profiles['epgs'].append(epgs_info)
            tenants_dict['app-profiles'].append(app_profiles)
        tenants_list.append(tenants_dict)

    tenants_info = {}
    tenants_info['tenants'] = tenants_list
    print yaml.safe_dump(tenants_info,sys.stdout, indent= 4,default_flow_style=False)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
