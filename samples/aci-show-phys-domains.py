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
Print all physical domains with the network associated to them
"""


import acitoolkit.acitoolkit as aci

def main():

    # Get the APIC login credentials
    description = 'testing tags'
    creds = aci.Credentials('apic', description)
    args = creds.get()


    # Login to APIC and push the config
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return
    # get all physical domains
    phydms = aci.PhysDomain.get(session)
    template = "{0:30} {1:30} {2:25}"
    if len(phydms)>0:
        print(template.format("Physical Domain","Network","encap_type"))
    for p in phydms:
        pool_name = ""
        encap_type = ""
        if p.has_network():
            net = p.get_network()
            pool_name = net.name
            encap_type = net.encap_type
        print(template.format(p.name,pool_name,encap_type))

    # networks = aci.NetworkPool.get(session)
    # for net in networks:
    #     #print(net.name)
    #     print("{} {} {} ".format(net.name,net.encap_type,net.mode))
    # Get tenants from the APIC
    # if args.tenant:
    #     tenants = aci.Tenant.get_deep(session, names=[args.tenant])
    # else:
    #     tenants = aci.Tenant.get(session)
    # # get all EPGs with their tag
    # data = []
    # for tenant in tenants:
    #     print("1")
    #     for contract in tenant.get_children(aci.Contract):
    #         print('2')
    #         subjects = contract.get_children(aci.ContractSubject)
    #         for subject in subjects:
    #             bidir_filters = subject.get_filters()
    #             data.append(contract.name)
    #             data.append([f.name for f in bidir_filters])
    # for d in data:
    #     print(d)

    # for tenant in tenants:
    #     for contract in tenant.get_children(aci.Contract):
    #         subjects = contract.get_children(aci.ContractSubject)
    #         for subject in subjects:
    #
    #             # let's ask the REST API directly:
    #             contract = subject.get_parent()
    #             tenant = contract.get_parent()
    #             params = {'query-target': 'children'}
    #             #query = 'query-target=children&'
    #             query_url = '/api/mo/uni/tn-{}/brc-{}/subj-{}.json?query-target=children&'.format(tenant.name, contract.name, subject.name)
    #             ret = session.get(query_url)
    #             data = ret.json()['imdata']
    #             if len(data):
    #                 for child in data:
    #                     if 'vzRsSubjFiltAtt' in child:
    #                         for attrib in child['vzRsSubjFiltAtt']['attributes']:
    #                             if 'tnVzFilterName' in attrib:
    #                                 filterName = child['vzRsSubjFiltAtt']['attributes']['tnVzFilterName']
    #                                 filterDn = child['vzRsSubjFiltAtt']['attributes']['tDn']
    #
    #                                 # now... find the Filter object with this specific name/tDn
    #                                 candidate_filters = subject.get_filters()
    #                                 for candidate_filter in candidate_filters:
    #                                     if candidate_filter.name == filterName:
    #                                         data.append(contract.name)
    #                                         data.append(candidate_filter)
    # for d in data:
    #     print(d)


if __name__ == '__main__':
    main()


