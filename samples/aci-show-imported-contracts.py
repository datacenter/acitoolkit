"""
Find out where a contract has been imported and consumed on an EPG.

"""
import acitoolkit.acitoolkit as aci
from acitoolkit.acitoolkit import *

def main():
    description = ('Simple application that logs on to the APIC'
                   ' and displays all the tenant info of the contract_interface related to the imported contract.')
    creds = aci.Credentials('apic', description)
    creds.add_argument("-t", "--tenant_name", help="Tenant Name of where the contract is created")
    creds.add_argument("-i", "--contract_name", help="Imported Contract Name")
    args = creds.get()

    if not args.tenant_name:
        args.tenant_name = raw_input("Tenant Name: ")
    if not args.contract_name:
        args.contract_name = raw_input("Contract Name: ")
        
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        
    
    tenants = aci.Tenant.get_deep(session)
    for tenant in tenants:
        contracts_interfaces= tenant.get_children(only_class=ContractInterface)
        for contractInterface in contracts_interfaces:
            importedContracts = contractInterface.get_import_contract()
            if importedContracts is not None:
                if importedContracts.name == args.contract_name and importedContracts.get_parent().name == args.tenant_name:
                    print "Tenant: "+tenant.name
                    apps = aci.AppProfile.get(session, tenant)
                    for app in apps:
                        print "    App-Profile: "+app.name
                        epgs = aci.EPG.get(session, app, tenant)
                        for epg in epgs:
                            print "        EPG: "+epg.name
    
if __name__ == '__main__':
    main()