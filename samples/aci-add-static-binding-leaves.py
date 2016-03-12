#!/usr/bin/env python
import acitoolkit.acitoolkit as aci

DEFAULT_TENANT     = 'TENANT-001'
DEFAULT_APP        = 'APP-001'
DEFAULT_EPG        = 'EPG-001'
DEFAULT_NODE_ID    = '101'
DEFAULT_ENCAP_TYPE = 'vlan'
DEFAULT_ENCAP_ID   = '101'
DEFAULT_ENCAP_MODE = 'regular'
DEFAULT_IMMEDIACY  = 'immediate'
DEFAULT_POD        = '1'


def main():
    """
    Main show EPGs routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and add static-binding-leaves.')
    creds = aci.Credentials('apic', description)
    creds.add_argument('-t', '--tenant', help='Tenant name', default=DEFAULT_TENANT)
    creds.add_argument('-a', '--app', help='Application profile name', default=DEFAULT_APP)
    creds.add_argument('-e', '--epg', help='EPG name', default=DEFAULT_EPG)
    creds.add_argument('-n', '--node', help='Node ID (e.g. 101)', default=DEFAULT_NODE_ID)
    creds.add_argument('-y', '--type', help='Encapsulation type (vlan | vxlan | nvgre)', default=DEFAULT_ENCAP_TYPE)
    creds.add_argument('-i', '--id', help='Specific identifier representing the virtual L2 network (e.g. 100)', default=DEFAULT_ENCAP_ID)
    creds.add_argument('-m', '--mode', help='Encapsulation mode (regular | untagged | native)', default=DEFAULT_ENCAP_MODE)
    creds.add_argument('-d', '--deploy', help='Deployment immediacy (immediate | lazy)', default=DEFAULT_IMMEDIACY)
    creds.add_argument('-o', '--pod', help='Pod number (e.g. 1)', default=DEFAULT_POD)

    args = creds.get()
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    tenant = aci.Tenant(args.tenant)
    app = aci.AppProfile(args.app, tenant)
    epg = aci.EPG(args.epg, app)
    epg.add_static_leaf_binding(args.node, args.type, args.id, args.mode, args.deploy, args.pod)

    # Push it all to the APIC
    resp = session.push_to_apic(tenant.get_url(), tenant.get_json())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
