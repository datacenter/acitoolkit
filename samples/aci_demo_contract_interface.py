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
Sample configuration showing the usage of the ContractInterface class to allow
exporting a Contract from 1 tenant to another.
"""
from acitoolkit.acisession import Session
from acitoolkit.acitoolkit import Credentials, Tenant, AppProfile, EPG
from acitoolkit.acitoolkit import ContractInterface, Contract, FilterEntry


def main():
    """ Create 2 Tenants with a single EPG in each. Between the 2 tenants, the EPGs
        communicate through an exported contract.
    """
    description = ('Create 2 Tenants with a single EPG in each. Between the 2 tenants,'
                   'the EPGs communicate through an exported contract.Create 2 EPGs '
                   'within the same Context and have 1 EPG provide a contract to the '
                   'other EPG.')
    creds = Credentials('apic', description)
    args = creds.get()

    # Create the first Tenant
    tenant1 = Tenant('aci-toolkit-demo-1')
    app1 = AppProfile('my-demo-app-1', tenant1)
    web_epg = EPG('web-frontend', app1)

    # Create the second Tenant
    tenant2 = Tenant('aci-toolkit-demo-2')
    app2 = AppProfile('my-demo-app-2', tenant2)
    db_epg = EPG('database-backend', app2)

    # Define a contract with a single entry
    contract = Contract('mysql-contract', tenant2)
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

    # Provide the contract from 1 EPG
    db_epg.provide(contract)

    # Import the contract into the other tenant
    imported_contract = ContractInterface('mysql-imported-contract', tenant1)
    imported_contract.import_contract(contract)

    # Consume the contract in the second tenant
    web_epg.consume_cif(imported_contract)

    # Login to APIC and push the config
    session = Session(args.url, args.login, args.password)
    session.login()
    # Cleanup (uncomment the next 2 lines to delete the config)
    # tenant1.mark_as_deleted()
    # tenant2.mark_as_deleted()
    for tenant in [tenant2, tenant1]:
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
