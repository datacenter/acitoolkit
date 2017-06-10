#!/usr/bin/env python
"""
Sample of creating a EPG
"""

from acitoolkit.acitoolkit import Credentials, Session, Tenant, AppProfile, BridgeDomain, EPG

def main():
    """
    Main execution routine

    :return: None
    """
    creds = Credentials('apic')
    creds.add_argument('--tenant', help='The name of Tenant')
    creds.add_argument('--app', help='The name of ApplicationProfile')
    creds.add_argument('--bd', help='The name of BridgeDomain')
    creds.add_argument('--epg', help='The name of EPG')

    args = creds.get()
    session = Session(args.url, args.login, args.password)
    session.login()

    tenant = Tenant(args.tenant)
    app = AppProfile(args.app, tenant)
    bd = BridgeDomain(args.bd, tenant)
    epg = EPG(args.epg, app)
    epg.add_bd(bd)

    resp = session.push_to_apic(tenant.get_url(),
                                tenant.get_json())

    if not resp.ok:
        print('%% Error: Could not push configuration to APIC')
        print(resp.text)

if __name__ == '__main__':
    main()

