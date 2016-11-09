"""
Find out where a contract has been imported and consumed on an EPG.

"""
import acitoolkit.acitoolkit as aci
from acitoolkit.acitoolkit import *
from tabulate import tabulate


def main():
    description = ('Simple application that logs on to the APIC'
                   ' and displays all the tenant info of the contract_interface related to the imported contract.')
    creds = aci.Credentials('apic', description)
    creds.add_argument("-t", "--tenant_name", help="Tenant Name of where the contract is created")
    creds.add_argument("-i", "--contract_name", help="Imported Contract Name")
    args = creds.get()

    if (args.tenant_name is not None) and (args.contract_name is None):
        args.contract_name = raw_input("Contract Name: ")

    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    data = []
    tenants = aci.Tenant.get_deep(session)
    for tenant in tenants:
        contracts_interfaces = tenant.get_children(only_class=ContractInterface)
        for contractInterface in contracts_interfaces:
            importedContract = contractInterface.get_import_contract()
            if importedContract is not None:
                if args.tenant_name is not None:
                    if (importedContract.name == args.contract_name) and (importedContract.get_parent().name == args.tenant_name):
                        apps = aci.AppProfile.get(session, tenant)
                        for app in apps:
                            epgs = aci.EPG.get(session, app, tenant)
                            for epg in epgs:
                                data.append((importedContract.name,tenant.name, app.name, epg.name))
                else:
                    apps = aci.AppProfile.get(session, tenant)
                    for app in apps:
                        epgs = aci.EPG.get(session, app, tenant)
                        for epg in epgs:
                            data.append((importedContract.name,tenant.name, app.name, epg.name))
    print tabulate(data, headers=["IMPORTED_CONTRACT","TENANT", "APP_PROFILE", "EPG"])

if __name__ == '__main__':
    main()
