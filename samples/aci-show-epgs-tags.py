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
Print all tenants which have the tag specified by the user
"""


import acitoolkit.acitoolkit as aci


def main():

    # Get the APIC login credentials
    description = 'testing tags'
    creds = aci.Credentials('apic', description)
    creds.add_argument('--tenant', help='show tags of this tenant if specify')
    args = creds.get()


    # Login to APIC and push the config
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return
    # Get tenants from the APIC
    if args.tenant:
        tenants = aci.Tenant.get_deep(session, limit_to=['fvTenant'], names=[args.tenant])
    else:
        tenants = aci.Tenant.get(session)
    # get all EPGs with their tag
    data = []
    for tenant in tenants:
        apps = aci.AppProfile.get(session, tenant)
        for app in apps:
            epgs = aci.EPG.get(session, app, tenant)
            for epg in epgs:
                tag_list = aci.Tag.get(session, parent=epg, tenant=tenant)
                if len(tag_list):
                    tag_list = [tag.name for tag in tag_list]
                    if len(tag_list):
                        data.append((tenant.name, app.name, epg.name, ",".join(tag_list)))

    template = "{0:20} {1:20} {2:20} {3:20}"
    if len(data):

        print(template.format("Tenant",
                              "App",
                              "EPG",
                              "Tag"))
        print(template.format("-" * 20,
                              "-" * 20,
                              "-" * 20,
                              "-" * 20))
        for d in data:
            print(template.format(*d))


if __name__ == '__main__':
    main()


