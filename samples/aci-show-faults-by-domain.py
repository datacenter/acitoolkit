#!/usr/bin/env python

"""
simple application that logs on to apic and displays all the faults.
if a particular tenant is given shows faults of that tenant
and if a domain is given displays faults related to that domain.
list of domains can also be given
"""
from acitoolkit import (Credentials, Session, Faults)


def main():
    """
    Main execution routine
    """
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
        help="name of the tenant of which faults are to be displayed. If not given faults of all the tenants are shown")
    creds.add_argument('--continuous', action='store_true',
                       help='Continuously monitor for faults')
    args = creds.get()

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    faults_obj = Faults()
    fault_filter = None
    if args.domain_name is not None:
        fault_filter = {'domain': args.domain_name.split(',')}
    tenant_name = None
    if args.tenant_name is not None:
        tenant_name = args.tenant_name

    faults_obj.subscribe_faults(session, fault_filter)
    while faults_obj.has_faults(session, fault_filter) or args.continuous:
        if faults_obj.has_faults(session, fault_filter):
            faults = faults_obj.get_faults(
                session, fault_filter=fault_filter, tenant_name=tenant_name)
            if faults is not None:
                for fault in faults:
                    if fault is not None:
                        print("---------------")
                        if fault.descr is not None:
                            print("     descr     : " + fault.descr)
                        else:
                            print("     descr     : " + "  ")
                        print("     dn        : " + fault.dn)
                        print("     rule      : " + fault.rule)
                        print("     severity  : " + fault.severity)
                        print("     type      : " + fault.type)
                        print("     domain    : " + fault.domain)


if __name__ == '__main__':
    main()
