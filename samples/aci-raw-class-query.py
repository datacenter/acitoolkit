#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
the response of an API query given the class name and scope
"""
import sys
from pprint import pprint
import acitoolkit.acitoolkit as aci


def main():
    description = ('Simple application that logs on to the APIC and displays the'
                   ' response of a given query')
    creds = aci.Credentials('apic', description)
    creds.add_argument('-c', '--class_name', help='The class which is to be queried', required=True)
    creds.add_argument('-q', '--query_target', default='self',
                       help=('This restricts the scope of the query,query_target takes self'
                             '| children | subtree. ex: -q self.  The default is self.'))
    args = creds.get()

    if not args.class_name:
        args.class_name = raw_input("Class Name: ")

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    class_url = '/api/node/class/'+args.class_name+'.json?query-target='+args.query_target
    print("class_url is "+class_url)
    ret = session.get(class_url)
    response = ret.json()
    imdata = response['imdata']
    pprint(imdata)

if __name__ == '__main__':
    main()
