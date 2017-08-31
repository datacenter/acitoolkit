#!/usr/bin/env python

"""
Find out where a contract has been imported and consumed on an EPG.
"""
from acitoolkit import (Credentials, Session, Tenant, ContractInterface, AppProfile,
                        EPG)
from tabulate import tabulate

data = []


def main():
    """
    Main execution routine
    """
    description = ('Simple application that logs on to the APIC'
                   ' and displays all the tenant info of the contract_interface related to the imported contract.')
    creds = Credentials('apic', description)
    creds.add_argument("-t", "--tenant_name", help="Tenant Name of where the contract is created")
    creds.add_argument("-i", "--contract_name", help="Imported Contract Name")
    args = creds.get()

    if (args.tenant_name is not None) and (args.contract_name is None):
        args.contract_name = raw_input("Contract Name: ")

    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    tenants = Tenant.get_deep(session)
    for tenant in tenants:
        contracts_interfaces = tenant.get_children(only_class=ContractInterface)
        for contract_interface in contracts_interfaces:
            imported_contract = contract_interface.get_import_contract()
            if imported_contract is not None:
                if args.tenant_name is not None:
                    if (imported_contract.name == args.contract_name) and (imported_contract.get_parent().name == args.tenant_name):
                        apps = AppProfile.get(session, tenant)
                        for app in apps:
                            epgs = EPG.get(session, app, tenant)
                            for epg in epgs:
                                data.append((imported_contract.name, tenant.name, app.name, epg.name))
                else:
                    apps = AppProfile.get(session, tenant)
                    for app in apps:
                        epgs = EPG.get(session, app, tenant)
                        for epg in epgs:
                            data.append((imported_contract.name, tenant.name, app.name, epg.name))
    print tabulate(data, headers=["IMPORTED_CONTRACT", "TENANT", "APP_PROFILE", "EPG"])


if __name__ == '__main__':
    main()
