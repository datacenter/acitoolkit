#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
of the Subnets.
"""
import acitoolkit.acitoolkit as aci

data = []
longest_names = {'Tenant': len('Tenant'),
                 'Application Profile': len('Application Profile'),
                 'Bridge Domain': len('Bridge Domain'),
                 'Subnet': len('Subnet'),
                 'Scope': len('Scope')}
def main():
    """
    Main show Subnets routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the Subnets.')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--tenant', help='The name of Tenant')
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Download all of the tenants, app profiles, and Subnets
    # and store the names as tuples in a list
    tenants = aci.Tenant.get(session)
    for tenant in tenants:
        check_longest_name(tenant.name, "Tenant")
        if args.tenant is None:
            get_subnet(session, tenant)
        else:
            if tenant.name == args.tenant:
                get_subnet(session, tenant)

    # Display the data downloaded
    template = '{0:' + str(longest_names["Tenant"]) + '} ' \
               '{1:' + str(longest_names["Application Profile"]) + '} ' \
               '{2:' + str(longest_names["Bridge Domain"]) + '} ' \
               '{3:' + str(longest_names["Subnet"]) + '} ' \
               '{4:' + str(longest_names["Scope"]) + '}'
    print(template.format("Tenant", "Application Profile", "Bridge Domain", "Subnet", "Scope"))
    print(template.format('-' * longest_names["Tenant"],
                          '-' * longest_names["Application Profile"],
                          '-' * longest_names["Bridge Domain"],
                          '-' * longest_names["Subnet"],
                          '-' * longest_names["Scope"]))
    for rec in sorted(data):
        print(template.format(*rec))

def get_subnet(session, tenant):
    apps = aci.AppProfile.get(session, tenant)
    for app in apps:
        check_longest_name(app.name, "Application Profile")
        bds = aci.BridgeDomain.get(session, tenant)
        for bd in bds:
            check_longest_name(bd.name, "Bridge Domain")
            subnets = aci.Subnet.get(session, bd, tenant)
            if len(subnets) == 0:
                data.append((tenant.name, app.name, bd.name, "", ""))
            else:
                for subnet in subnets:
                    check_longest_name(subnet.addr, "Subnet")
                    check_longest_name(subnet.get_scope(), "Scope")
                    data.append((tenant.name, app.name, bd.name, subnet.addr, subnet.get_scope()))

def check_longest_name(item, title):
    if len(item) > longest_names[title]:
        longest_names[title] = len(item)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
