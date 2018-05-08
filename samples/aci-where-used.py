#!/usr/bin/env python

"""
Find out where a DN is used
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate

data = []


def main():
    """
    Main execution routine
    """
    description = ('Simple application that logs on to the APIC'
                   ' and displays usage information for a given DN')
    creds = Credentials('apic', description)
    creds.add_argument("-d", "--dn_name",
                       help="DN to query for usage information")

    args = creds.get()

    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
    url = '/api/mo/{}.json?query-target=children&target-subtree-class=relnFrom'
    url = url.format(args.dn_name)

    resp = session.get(url)

    if resp.ok:
        used_by = resp.json()['imdata']
        for item in used_by:
            kls = next(iter(item))
            attributes = item[kls]['attributes']
            data.append((attributes['tDn'], kls))
    print(tabulate(data, headers=["Used by", "Class"]))


if __name__ == '__main__':
    main()
