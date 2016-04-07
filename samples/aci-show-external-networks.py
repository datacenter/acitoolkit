#!/usr/bin/env python
"""
Simple application that logs on to the APIC and displays all of
the External Networks.
"""
import acitoolkit.acitoolkit as aci


def main():
    """
    Main routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the External Subnets.')
    creds = aci.Credentials('apic', description)
    args = creds.get()
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Download all of the tenants, app profiles, and Subnets
    # and store the names as tuples in a list
    data = []
    tenants = aci.Tenant.get_deep(session, limit_to=['fvTenant',
                                                     'l3extOut',
                                                     'l3extInstP',
                                                     'l3extSubnet'])
    for tenant in tenants:
        outside_l3s = tenant.get_children(only_class=aci.OutsideL3)
        for outside_l3 in outside_l3s:
            outside_epgs = outside_l3.get_children(only_class=aci.OutsideEPG)
            for outside_epg in outside_epgs:
                outside_networks = outside_epg.get_children(only_class=aci.OutsideNetwork)
                if len(outside_networks) == 0:
                    data.append((tenant.name, outside_l3.name, outside_epg.name, "", ""))
                else:
                    for outside_network in outside_networks:
                        data.append((tenant.name,
                                     outside_l3.name,
                                     outside_epg.name,
                                     outside_network.addr,
                                     outside_network.get_scope()))

    # Display the data downloaded
    template = "{0:20} {1:20} {2:20} {3:18} {4:15}"
    print(template.format("Tenant",
                          "OutsideL3",
                          "OutsideEPG",
                          "Subnet",
                          "Scope"))
    print(template.format("-" * 20,
                          "-" * 20,
                          "-" * 20,
                          "-" * 18,
                          "-" * 15))
    for rec in data:
        print(template.format(*rec))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
