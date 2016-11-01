"""
Simple application that logs on to the APIC and displays all
of the faults on all the Tenants.
If a particular tenant is given, shows all the faults of that tenant
and cotinuously keeps logging the faults.
"""
import sys
import acitoolkit as ACI
from pprint import pprint
from tabulate import tabulate
from acitoolkit import Faults


def main():
    """
    Main execution routine
    """
    description = ('Simple application that logs on to the APIC'
                   ' and displays all the faults. If tenant name is given, '
                   ' shows the faults associated with that tenant')
    creds = ACI.Credentials('apic', description)
    creds.add_argument("-t", "--tenant_name",
                       help="name of the tenant of which faults are to be displayed")
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)
    if args.tenant_name is not None:
        tenant_name = args.tenant_name
    else:
        tenant_name = None

    faults_obj = Faults()
    faults_obj.subscribe_faults(session)
    while True:
        if faults_obj.has_faults(session):
            faults = faults_obj.get_faults(session, tenant_name=tenant_name)
            if faults is not None:
                for fault in faults:
                    if fault is not None:
                        print "****************"
                        if fault.descr is not None:
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
