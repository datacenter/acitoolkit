#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
of the Contracts.
"""
import sys
import acitoolkit.acitoolkit as aci

data = []
longest_names = {'Tenant': len('Tenant'),
                 'Contract': len('Contract')}
def main():
    """
    Main show contracts routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC'
                   'and displays all of the Contracts.')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--tenant', help='The name of Tenant')
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    # Download all of the contracts
    # and store the data as tuples in a list
    tenants = aci.Tenant.get(session)
    for tenant in tenants:
        check_longest_name(tenant.name, "Tenant")
        if args.tenant is None:
            get_contract(session, tenant)
        else:
            if tenant.name == args.tenant:
                get_contract(session, tenant)

    # IPython.embed()

    # Display the data downloaded
    template = '{0:' + str(longest_names["Tenant"]) + '} ' \
               '{1:' + str(longest_names["Contract"]) + '}'
    print(template.format("Tenant", "Contract"))
    print(template.format('-' * longest_names["Tenant"],
                          '-' * longest_names["Contract"]))
    for rec in sorted(data):
        print(template.format(*rec))

def get_contract(session, tenant):
    contracts = aci.Contract.get(session, tenant)
    for contract in contracts:
        check_longest_name(contract.name, "Contract")
        data.append((tenant.name, contract.name))

def check_longest_name(item, title):
    if len(item) > longest_names[title]:
        longest_names[title] = len(item)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
