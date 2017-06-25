#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
EPGs.
"""
import acitoolkit.acitoolkit as aci

data = []
longest_names = {'Tenant': len('Tenant'),
                 'Application Profile': len('Application Profile'),
                 'EPG': len('EPG')}
def main():
    """
    Main show EPGs routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the EPGs.')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--tenant', help='The name of Tenant')
    args = creds.get()

    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')

    # Download all of the tenants, app profiles, and EPGs
    # and store the names as tuples in a list
    tenants = aci.Tenant.get(session)
    for tenant in tenants:
        check_longest_name(tenant.name, "Tenant")
        if args.tenant is None:
            get_epg(session, tenant)
        else:
            if tenant.name == args.tenant:
                get_epg(session, tenant)

    # Display the data downloaded
    template = '{0:' + str(longest_names["Tenant"]) + '} ' \
               '{1:' + str(longest_names["Application Profile"]) + '} ' \
               '{2:' + str(longest_names["EPG"]) + '}'
    print(template.format("Tenant", "Application Profile","EPG"))
    print(template.format('-' * longest_names["Tenant"],
                          '-' * longest_names["Application Profile"],
                          '-' * longest_names["EPG"]))
    for rec in sorted(data):
        print(template.format(*rec))

def get_epg(session, tenant):
    apps = aci.AppProfile.get(session, tenant)
    for app in apps:
        check_longest_name(app.name, "Application Profile")
        epgs = aci.EPG.get(session, app, tenant)
        for epg in epgs:
            check_longest_name(epg.name, "EPG")
            data.append((tenant.name, app.name, epg.name))

def check_longest_name(item, title):
    if len(item) > longest_names[title]:
        longest_names[title] = len(item)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
