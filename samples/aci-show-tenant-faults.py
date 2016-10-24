"""
Simple application that logs on to the APIC and displays all
of the faults severity on all the Tenants.
If a particular tenant is given, shows all the faults of that tenant
and cotinuously keeps logging the faults.
"""
import sys
import acitoolkit.acitoolkit as ACI
from pprint import pprint
from tabulate import tabulate


def main():
    description = ('Simple application that logs on to the APIC'
                   ' and displays all the faults severity. If tenant name is given also shows the faults assosciated with that tenant')
    creds = ACI.Credentials('apic', description)
    creds.add_argument("-t", "--tenant_name", help="name of the tenant of which faults are to be displayed")
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    tenants = ACI.Tenant.get_deep(session)
    extension = '&rsp-subtree-include=faults,no-scoped'

    data = []
    for tenant in tenants:
        tenant.subscribe_to_fault_instances_subtree(session, extension, deep=True)

    if args.tenant_name is not None:
        while True:
            for tenant in tenants:
                if tenant.name == args.tenant_name:
                    try:
                        if tenant._instance_has_subtree_faults(session, extension, deep=True):
                            fault_objs = []
                            fault_objects = tenant._instance_get_subtree_faults(
                                session, fault_objs, extension, deep=True)
                            if len(fault_objects) > 0:
                                print "faults of Tenant " + tenant.name
                                for fault_obj in fault_objects:
                                    print "---------------------------------"
                                    faultInst = fault_obj['faultInst']['attributes']
                                    print "     cause     : " + faultInst['cause']
                                    print "     descr     : " + faultInst['descr']
                                    print "     dn        : " + faultInst['dn']
                                    print "     rule      : " + faultInst['rule']
                                    print "     severity  : " + faultInst['severity']
                                    print "     type      : " + faultInst['type']

                    except KeyboardInterrupt:
                        return
    else:
        headers = ["Tenant", "critical", "major", "minor", "warning"]
        for tenant in tenants:
            severity_critical = severity_major = severity_minor = severity_warning = 0
            try:
                if tenant._instance_has_subtree_faults(session, extension, deep=True):
                    fault_objs = []
                    fault_objects = tenant._instance_get_subtree_faults(session, fault_objs, extension, deep=True)
                    if len(fault_objects) > 0:
                        for fault_obj in fault_objects:
                            faultInst = fault_obj['faultInst']['attributes']
                            severity = faultInst['severity']
                            if severity == 'major':
                                severity_major += 1
                            elif severity == 'minor':
                                severity_minor += 1
                            elif severity == 'critical':
                                severity_critical += 1
                            elif severity == 'warning':
                                severity_warning += 1

            except KeyboardInterrupt:
                print "some exception"
                return

            data.append((tenant.name, severity_major, severity_minor, severity_critical, severity_warning))
        print tabulate(data, headers, tablefmt="plain")

if __name__ == '__main__':
    main()
