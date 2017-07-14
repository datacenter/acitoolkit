#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays
health on all the Tenants.
"""
import acitoolkit.acitoolkit as ACI
import re


def main():
    """
    Main execution routine

    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC and displays '
                   ' health all of the Tenants,keeps on checking continuously')
    creds = ACI.Credentials('apic', description)
    creds.add_argument('--continuous', action='store_true',
                       help='Continuously monitor for tenant health changes')
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    extension = '&rsp-subtree-include=health,no-scoped'

    ACI.Tenant.subscribe(session, extension)

    template = "{0:70} {1:6}  "
    print(template.format("tenant", "current_health"))
    print(template.format("---------", "----"))
    try:
        while ACI.Tenant.has_events(session, extension) or args.continuous:
            if ACI.Tenant.has_events(session, extension):
                health_object = ACI.Tenant.get_fault(session, extension)
                health_inst = health_object['healthInst']['attributes']
                tenant_name = health_inst['dn']
                health = health_inst['cur']
                match_obj = re.match(r'uni/tn-(.*)/health', tenant_name)
                print(template.format(match_obj.group(1), health))
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    main()
