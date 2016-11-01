"""
simple application that logs on to apic and displays all the faults.
if a particular tenant is given shows faults of that tenant
and if a domain is given displays faults related to that domain.
list of domains can also be given
"""
import sys
from pprint import pprint
from acitoolkit import (Credentials, Session)
from acitoolkit.aciFaults import Faults


def main():
    description = 'Simple application that logs on to the APIC and displays all of the Tenants.'
    creds = Credentials('apic', description)
    creds.add_argument(
        "-d",
        "--domain-name",
        type=str,
        help="list of domains. usage -d tennat.infra")
    creds.add_argument(
        "-t",
        "--tenant-name",
        type=str,
        help="name of the tenant of which faults are to be displayed.If not given faults of all the tenants are shown")
    args = creds.get()

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    faults_obj = Faults()
    fault_filter = None
    if not args.domain_name is None:
        fault_filter = {'domain': args.domain_name.split(',')}
    tenant_name = None
    if not args.tenant_name is None:
        tenant_name = args.tenant_name

    faults_obj.subscribe_faults(session, fault_filter)
    while True:
        if faults_obj.has_faults(session, fault_filter):
            faults = faults_obj.get_faults(
                session, fault_filter=fault_filter, tenant_name=tenant_name)
            if not faults is None:
                for fault in faults:
                    if not fault is None:
                        print "---------------"
                        if not fault.descr is None:
                            print "     descr     : " + fault.descr
                        else:
                            print "     descr     : " + "  "
                        print "     dn        : " + fault.dn
                        print "     rule      : " + fault.rule
                        print "     severity  : " + fault.severity
                        print "     type      : " + fault.type
                        print "     domain    : " + fault.domain

if __name__ == '__main__':
    main()
