"""
Simple application that logs on to the APIC and displays
health on all the Tenants.
"""
import sys
import acitoolkit.acitoolkit as ACI
from acitoolkit import (Tenant)
import re


def main():
    """
    Main execution routine

    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = 'Simple application that logs on to the APIC and displays health all of the Tenants,keeps on checking continuously'
    creds = ACI.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    extension = '&rsp-subtree-include=health,no-scoped'

    ACI.Tenant.subscribe(session, extension)

    template = "{0:70} {1:6}  "
    print(template.format("tenant", "current_health"))
    print(template.format("---------", "----"))
    while True:
        try:
            if ACI.Tenant.has_events(session, extension):
                health_object = ACI.Tenant.get_fault(session, extension)
                healthInst = health_object['healthInst']['attributes']
                tenant_name = healthInst['dn']
                health = healthInst['cur']
                matchObj = re.match(r'uni/tn-(.*)/health', tenant_name)
                print(template.format(matchObj.group(1), health))

        except KeyboardInterrupt:
            return

if __name__ == '__main__':
    main()
