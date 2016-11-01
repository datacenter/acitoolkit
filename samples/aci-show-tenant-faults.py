"""
Simple application that logs on to the APIC and displays all
of the faults on all the Tenants.
If a particular tenant is given, shows all the faults of that tenant
and cotinuously keeps logging the faults.
"""
import sys
import acitoolkit.acitoolkit as ACI
from pprint import pprint
from tabulate import tabulate
from acitoolkit.aciFaults import Faults, BaseFaults


def main():
    description = ('Simple application that logs on to the APIC'
                   ' and displays all the faults. If tenant name is given, shows the faults assosciated with that tenant')
    creds = ACI.Credentials('apic', description)
    creds.add_argument("-t", "--tenant_name", help="name of the tenant of which faults are to be displayed")
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)
    if not args.tenant_name is None:
        tenant_name = args.tenant_name
    else:
        tenant_name = None

    faults_obj = Faults()
    faults_obj.subscribe_to_Faults(session)
    while True:
        if faults_obj.has_faults(session):
            faults = faults_obj.get_faults(session, tenant_name=tenant_name)
            if not faults is None:
                for fault in faults:
                    if not fault is None:
                        print "****************"
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
