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
of the Physical Domains, VMM Domains, and EPG associations.
"""
import sys
import acitoolkit.acitoolkit as aci


def main():
    """
    Main Show Domains Routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the Endpoints.')
    creds = aci.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    domains = aci.PhysDomain.get(session)

    if len(domains) > 0:
        print ('---------------')
        print ('Physical Domain')
        print ('---------------')

    for domain in domains:
        print domain.name

    if len(domains) > 0:
        print '\n'

    domains = aci.VmmDomain.get(session)

    if len(domains) > 0:
        print ('----------')
        print ('VMM Domain')
        print ('----------')

    for domain in domains:
        print (domain.name)

    if len(domains) > 0:
        print ('\n')

    domains = aci.L2ExtDomain.get(session)

    if len(domains) > 0:
        print ('------------------')
        print ('L2 External Domain')
        print ('------------------')

    for domain in domains:
        print (domain.name)

    if len(domains) > 0:
        print ('\n')

    domains = aci.L3ExtDomain.get(session)

    if len(domains) > 0:
        print ('------------------')
        print ('L3 External Domain')
        print ('------------------')

    for domain in domains:
        print (domain.name)

    if len(domains) > 0:
        print ('\n')

    domains = aci.EPGDomain.get(session)

    output = []
    for domain in domains:
        association = domain.tenant_name + ':' + domain.app_name + ':' + domain.epg_name
        output.append((domain.domain_name, domain.domain_type,
                       association))

    if len(domains) > 0:
        template = '{0:20} {1:11} {2:26}'
        print (template.format('Infra Domain Profile', 'Domain Type', 'TENANT:APP:EPG Association'))
        print (template.format('--------------------', '-----------', '--------------------------'))
        for rec in output:
            print (template.format(*rec))
        print ('\n')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
