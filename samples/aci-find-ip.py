#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
networks that match the given IP
"""
import sys
from ipaddr import IPNetwork
from acitoolkit import (Credentials, Session, Tenant, AppProfile, BridgeDomain,
                        Subnet, OutsideL3, OutsideEPG, OutsideNetwork)


def main():
    """
    Main routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the External Subnets.')
    creds = Credentials('apic', description)
    creds.add_argument('-f', '--find_ip', help='IP address to search for')
    args = creds.get()

    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    if not args.find_ip:
        print("Error: -f|--find_ip <ip_address> argument required")
        sys.exit(1)

    print("searching for " + args.find_ip)
    # Download all of the tenants, app profiles, and Subnets
    # and store the names as tuples in two lists
    priv = []
    publ = []
    ip = args.find_ip
    tenants = Tenant.get_deep(session, limit_to=['fvTenant',
                                                     'fvSubnet',
                                                     'l3extOut',
                                                     'l3extInstP',
                                                     'l3extSubnet'])

    for tenant in tenants:
        apps = AppProfile.get(session, tenant)
        for app in apps:
            bds = BridgeDomain.get(session, tenant)
            for bd in bds:
                subnets = Subnet.get(session, bd, tenant)
                for subnet in subnets:
                    net = IPNetwork(subnet.addr)
                    if net.Contains(IPNetwork(ip)):
                        priv.append((tenant.name, app.name, bd.name,
                                     subnet.addr, subnet.get_scope()))

    for tenant in tenants:
        outside_l3s = tenant.get_children(only_class=OutsideL3)
        for outside_l3 in outside_l3s:
            outside_epgs = outside_l3.get_children(only_class=OutsideEPG)
            for outside_epg in outside_epgs:
                outside_networks = outside_epg.get_children(only_class=OutsideNetwork)
                for outside_network in outside_networks:
                    net = IPNetwork(outside_network.addr)
                    if net.Contains(IPNetwork(ip)):
                        publ.append((tenant.name,
                                     outside_l3.name,
                                     outside_epg.name,
                                     outside_network.addr,
                                     outside_network.get_scope()))

    # Display
    template = "{0:20} {1:20} {2:20} {3:18} {4:15}"
    if len(priv):
        print("")
        print(template.format("Tenant",
                              "App",
                              "Bridge Domain",
                              "Subnet",
                              "Scope"))
        print(template.format("-" * 20,
                              "-" * 20,
                              "-" * 20,
                              "-" * 18,
                              "-" * 15))
        for rec in priv:
            print(template.format(*rec))
    if len(publ):
        print("")
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
        for rec in publ:
            print(template.format(*rec))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
