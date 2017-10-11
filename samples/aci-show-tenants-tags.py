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
    creds.add_argument('--tenant', help='show tag of this tenant if specify')
    args = creds.get()


    # Login to APIC and push the config
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    if args.tenant:
        tenants_with_tag = aci.Tenant.get_deep(session, limit_to=['tagInst'], names=[args.tenant])
    else:
        # Get all Tenants within APIC
        tenants = aci.Tenant.get(session)

        names_tenants = [tenant.name for tenant in tenants]
        tenants_with_tag = aci.Tenant.get_deep(session, limit_to=['tagInst'], names=names_tenants)

    data = []
    for tenant in tenants_with_tag:
        if tenant.has_tags():
            tag_list = [tag.name for tag in tenant.get_tags()]
            if len(tag_list):
                data.append((tenant.name,",".join(tag_list)))

    template = "{0:20} {1:20}"
    if len(data):
        print(template.format("Tenant","Tag"))
        print(template.format("-" * 20, "-" * 20))
        for d in data:
            print(template.format(*d))



if __name__ == '__main__':
    main()
