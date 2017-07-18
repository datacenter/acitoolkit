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
Simple demonstration application configuring a basic ACI fabric
"""
from acitoolkit.acisession import Session
from acitoolkit.acitoolkit import Credentials, Tenant, AppProfile, EPG
from acitoolkit.acitoolkit import Context, BridgeDomain, Contract, FilterEntry


def main():
    """ Create 2 EPGs within the same Context and have
        1 EPG provide a contract to the other EPG.
    """
    description = ('Create 2 EPGs within the same Context and have'
                   '1 EPG provide a contract to the other EPG.')
    creds = Credentials('apic', description)
    args = creds.get()

    # Create the Tenant
    tenant = Tenant('aci-toolkit-demo')

    # Create the Application Profile
    app = AppProfile('my-demo-app', tenant)

    # Create the EPGs
    web_epg = EPG('web-frontend', app)
    db_epg = EPG('database-backend', app)
    web_epg.set_intra_epg_isolation(False)
    db_epg.set_intra_epg_isolation(True)

    # Create a Context and BridgeDomain
    # Place both EPGs in the Context and in the same BD
    context = Context('VRF-1', tenant)
    bd = BridgeDomain('BD-1', tenant)
    bd.add_context(context)
    web_epg.add_bd(bd)
    db_epg.add_bd(bd)

    # Define a contract with a single entry
    contract = Contract('mysql-contract', tenant)
    entry1 = FilterEntry('entry1',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='3306',
                         dToPort='3306',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='1',
                         sToPort='65535',
                         tcpRules='unspecified',
                         parent=contract)

    # Provide the contract from 1 EPG and consume from the other
    db_epg.provide(contract)
    web_epg.consume(contract)

    # Login to APIC and push the config
    session = Session(args.url, args.login, args.password)
    session.login()

    # Cleanup (uncomment the next line to delete the config)
    # tenant.mark_as_deleted()
    resp = tenant.push_to_apic(session)

    if resp.ok:
        # Print what was sent
        print('Pushed the following JSON to the APIC')
        print('URL: ' + str(tenant.get_url()))
        print('JSON: ' + str(tenant.get_json()))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
