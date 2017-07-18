#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all of
the External Networks.
"""
from acitoolkit import *

data = []
longest_names = {'Tenant': len('Tenant'),
                 'L3Out': len('L3Out'),
                 'External EPG': len('External EPG'),
                 'Subnet': len('Subnet'),
                 'Scope': len('Scope')}


def main():
    """
    Main routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the External Subnets.')
    creds = Credentials('apic', description)
    creds.add_argument('--tenant', help='The name of Tenant')
    args = creds.get()

    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Download all of the tenants, app profiles, and Subnets
    # and store the names as tuples in a list
    tenants = Tenant.get_deep(session, limit_to=['fvTenant',
                                                 'l3extOut',
                                                 'l3extInstP',
                                                 'l3extSubnet'])
    for tenant in tenants:
        check_longest_name(tenant.name, "Tenant")
        if args.tenant is None:
            get_external_epg(session, tenant)
        else:
            if tenant.name == args.tenant:
                get_external_epg(session, tenant)

    # Display the data downloaded
    template = '{0:' + str(longest_names["Tenant"]) + '} ' \
               '{1:' + str(longest_names["L3Out"]) + '} ' \
               '{2:' + str(longest_names["External EPG"]) + '} ' \
               '{3:' + str(longest_names["Subnet"]) + '} ' \
               '{4:' + str(longest_names["Scope"]) + '}'
    print(template.format("Tenant", "L3Out", "External EPG", "Subnet", "Scope"))
    print(template.format('-' * longest_names["Tenant"],
                          '-' * longest_names["L3Out"],
                          '-' * longest_names["External EPG"],
                          '-' * longest_names["Subnet"],
                          '-' * longest_names["Scope"]))
    for rec in sorted(data):
        print(template.format(*rec))


def get_external_epg(session, tenant):
    """
    Get the external EPGs
    :param session: Session class instance
    :param tenant: String containing the Tenant name
    """
    outside_l3s = tenant.get_children(only_class=OutsideL3)
    for outside_l3 in outside_l3s:
        check_longest_name(outside_l3.name, "L3Out")
        outside_epgs = outside_l3.get_children(only_class=OutsideEPG)
        for outside_epg in outside_epgs:
            check_longest_name(outside_epg.name, "External EPG")
            outside_networks = outside_epg.get_children(only_class=OutsideNetwork)
            if len(outside_networks) == 0:
                data.append((tenant.name, outside_l3.name, outside_epg.name, "", ""))
            else:
                for outside_network in outside_networks:
                    check_longest_name(outside_network.addr, "Subnet")
                    check_longest_name(outside_network.get_scope(), "Scope")
                    data.append((tenant.name,
                                 outside_l3.name,
                                 outside_epg.name,
                                 outside_network.addr,
                                 outside_network.get_scope()))


def check_longest_name(item, title):
    """
    Check the longest name
    :param item: String containing the name
    :param title: String containing the column title
    """
    if len(item) > longest_names[title]:
        longest_names[title] = len(item)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
