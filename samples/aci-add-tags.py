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
Create a tenant with two EPGs and assign a tag to the tenant and all of its children
"""


import acitoolkit.acitoolkit as aci


def main():
    # Get the APIC login credentials
    description = 'testing tags'
    creds = aci.Credentials('apic', description)
    creds.add_argument('--tag',
                       help='Add tag to all objects in this configuration')
    creds.add_argument('--tenant', help='Tenant name to be created')
    args = creds.get()

    #Create the Tenant
    if args.tenant:
        tenant = aci.Tenant(args.tenant)
    else:
        tenant = aci.Tenant('tutorial-tag')

    # Create the Application Profile
    app = aci.AppProfile('myapp', tenant)

    # Create the EPG
    epg1 = aci.EPG('myepg1', app)
    epg2 = aci.EPG('myepg2', app)

    # Create a Context and BridgeDomain
    context = aci.Context('myvrf', tenant)
    bd = aci.BridgeDomain('mybd', tenant)
    bd.add_context(context)

    # Place the EPG in the BD
    epg1.add_bd(bd)
    epg2.add_bd(bd)

    # Add Tag to the EPGs
    epg1.add_tag("web server")
    epg2.add_tag("database")

    # test
    app2 = aci.AppProfile('myapp2', tenant)
    epg21 = aci.EPG('myepg21', app2)
    epg22 = aci.EPG('myepg22', app2)



    # Add Tag to all objects in this configuration
    if args.tag:
        tenant.add_tag(args.tag)
        context.add_tag(args.tag)
        bd.add_tag(args.tag)
        epg1.add_tag(args.tag)
        epg2.add_tag(args.tag)



    # Login to APIC and push the config
    session = aci.Session(args.url, args.login, args.password)
    session.login()
    resp = tenant.push_to_apic(session)
    if resp.ok:
        print ('Success')

    # Print what was sent
    print ('Pushed the following JSON to the APIC')
    print ('URL:', tenant.get_url())
    print ('JSON:', tenant.get_json())



if __name__ == '__main__':
    main()

