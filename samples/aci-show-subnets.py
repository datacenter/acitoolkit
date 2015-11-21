#!/usr/bin/env python
import acitoolkit.acitoolkit as aci


def main():
    """
    Main show Subnets routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the Subnets.')
    creds = aci.Credentials('apic', description)
    args = creds.get()
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Download all of the tenants, app profiles, and Subnets
    # and store the names as tuples in a list
    data = []
    tenants = aci.Tenant.get(session)
    for tenant in tenants:
        apps = aci.AppProfile.get(session, tenant)
        for app in apps:
            bds = aci.BridgeDomain.get(session, tenant)
            for bd in bds:
                subnets = aci.Subnet.get(session, bd, tenant)
                if len(subnets) == 0:
                    data.append((tenant.name, app.name, bd.name, "", ""))
                else:
                    for subnet in subnets:
                        data.append((tenant.name, app.name, bd.name, subnet.addr, subnet.get_scope()))

    # Display the data downloaded
    template = "{0:20} {1:20} {2:20} {3:18} {4:15}"
    print(template.format("Tenant              ", "AppProfile          ", "BridgeDomain        ", "Subnet            ", "Scope          "))
    print(template.format("--------------------", "--------------------", "--------------------", "------------------", "---------------"))
    for rec in data:
        print(template.format(*rec))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
