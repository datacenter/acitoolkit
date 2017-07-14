#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
of the Contexts.
"""
import sys
import acitoolkit.acitoolkit as ACI

data = []
longest_names = {'Tenant': len('Tenant'),
                 'Context': len('Context')}
def main():
    """
    Main execution routine

    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = 'Simple application that logs on to the APIC and displays all of the Contexts.'
    creds = ACI.Credentials('apic', description)
    creds.add_argument('--tenant', help='The name of Tenant')
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    # Download all of the contexts
    # and store the data as tuples in a list
    tenants = ACI.Tenant.get(session)
    for tenant in tenants:
        check_longest_name(tenant.name, "Tenant")
        if args.tenant is None:
            get_context(session, tenant)
        else:
            if tenant.name == args.tenant:
                get_context(session, tenant)

    # IPython.embed()

    # Display the data downloaded
    template = '{0:' + str(longest_names["Tenant"]) + '} ' \
               '{1:' + str(longest_names["Context"]) + '}'
    print(template.format("Tenant", "Context"))
    print(template.format('-' * longest_names["Tenant"],
                          '-' * longest_names["Context"]))
    for rec in sorted(data):
        print(template.format(*rec))

def get_context(session, tenant):
    contexts = ACI.Context.get(session, tenant)
    for context in contexts:
        check_longest_name(context.name, "Context")
        data.append((tenant.name, context.name))

def check_longest_name(item, title):
    if len(item) > longest_names[title]:
        longest_names[title] = len(item)

if __name__ == '__main__':
    main()
