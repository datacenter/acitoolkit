#!/usr/bin/env python
"""
Sample of creating a BridgeDomain
"""

from acitoolkit.acitoolkit import Credentials, Session, Tenant, Context, BridgeDomain, Subnet


def main():
    """
    Main execution routine

    :return: None
    """
    creds = Credentials('apic')
    creds.add_argument('--tenant', help='The name of Tenant')
    creds.add_argument('--vrf', help='The name of VRF')
    creds.add_argument('--bd', help='The name of BridgeDomain')
    creds.add_argument('--address', help='Subnet IPv4 Address')
    creds.add_argument('--scope', help='The scope of subnet ("public", "private", "shared", "public,shared", "private,shared", "shared,public", "shared,private")')
    creds.add_argument('--json', const='false', nargs='?', help='Json output only')

    args = creds.get()
    session = Session(args.url, args.login, args.password)
    session.login()

    tenant = Tenant(args.tenant)
    vrf = Context(args.vrf)
    bd = BridgeDomain(args.bd, tenant)
    bd.add_context(vrf)

    if args.address is None:
        bd.set_arp_flood('yes')
        bd.set_unicast_route('no')
    else:
        bd.set_arp_flood('no')
        bd.set_unicast_route('yes')

        subnet = Subnet('', bd)
        subnet.addr = args.address

        if args.scope is None:
            subnet.set_scope("private")
        else:
            subnet.set_scope(args.scope)

    if args.json:
        print(tenant.get_json())
    else:
        resp = session.push_to_apic(tenant.get_url(),
                                    tenant.get_json())

        if not resp.ok:
            print('%% Error: Could not push configuration to APIC')
            print(resp.text)

if __name__ == '__main__':
    main()
