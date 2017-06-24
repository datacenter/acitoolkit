#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
of the Contracts.
"""
import sys
import acitoolkit.acitoolkit as aci


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
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    # Download all of the contracts
    # and store the data as tuples in a list
    data = []
    tenants = aci.Tenant.get(session)
    for tenant in tenants:
        contracts = aci.Contract.get(session, tenant)
        for contract in contracts:
            data.append((tenant.name, contract.name))

    # IPython.embed()

    # Display the data downloaded
    template = '{0:19} {1:20}'
    print(template.format("Tenant", "Contract"))
    print(template.format("------", "--------"))
    for rec in data:
        print(template.format(*rec))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
