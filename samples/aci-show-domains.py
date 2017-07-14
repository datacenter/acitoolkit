#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
of the Physical Domains, VMM Domains, and EPG associations.
"""
import sys
import acitoolkit.acitoolkit as aci

def main():
    """
    Main Show Domains Routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the Endpoints.')
    creds = aci.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    domains = aci.PhysDomain.get(session)

    if len(domains) > 0:
        print ('---------------')
        print ('Physical Domain')
        print ('---------------')

    for domain in domains:
        print domain.name

    if len(domains) > 0:
        print '\n'

    domains = aci.VmmDomain.get(session)

    if len(domains) > 0:
        print ('----------')
        print ('VMM Domain')
        print ('----------')

    for domain in domains:
        print (domain.name)

    if len(domains) > 0:
        print ('\n')

    domains = aci.L2ExtDomain.get(session)

    if len(domains) > 0:
        print ('------------------')
        print ('L2 External Domain')
        print ('------------------')

    for domain in domains:
        print (domain.name)

    if len(domains) > 0:
        print ('\n')

    domains = aci.L3ExtDomain.get(session)

    if len(domains) > 0:
        print ('------------------')
        print ('L3 External Domain')
        print ('------------------')

    for domain in domains:
        print (domain.name)

    if len(domains) > 0:
        print ('\n')

    domains = aci.EPGDomain.get(session)

    output = []
    for domain in domains:
        association = domain.tenant_name + ':' + domain.app_name + ':' + domain.epg_name
        output.append((domain.domain_name, domain.domain_type,
                       association))

    if len(domains) > 0:
        template = '{0:20} {1:11} {2:26}'
        print (template.format('Infra Domain Profile', 'Domain Type', 'TENANT:APP:EPG Association'))
        print(template.format("-" * 20, "-" * 11, "-" * 26))
        for rec in output:
            print (template.format(*rec))
        print ('\n')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
