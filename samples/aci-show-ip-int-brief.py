#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
of the Interfaces.
"""
import sys
import re
import json
from acitoolkit import Credentials, Session

data = {}
longest_names = {'Node': len('Node'),
                 'Interface': len('Interface'),
                 'IP Address': len('IP Address'),
                 'Admin Status': len('Admin Status'),
                 'Status': len('Status')}


def main():
    """
    Main execution routine

    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = 'Simple application that logs on to the APIC and displays all of the Interfaces.'
    creds = Credentials('apic', description)
    creds.add_argument('--tenant', help='The name of Tenant')
    args = creds.get()

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    resp = session.get('/api/class/ipv4Addr.json')
    intfs = json.loads(resp.text)['imdata']

    for i in intfs:
        ip = i['ipv4Addr']['attributes']['addr']
        op = i['ipv4Addr']['attributes']['operSt']
        cfg = i['ipv4Addr']['attributes']['operStQual']
        dn = i['ipv4Addr']['attributes']['dn']
        node = dn.split('/')[2]
        intf = re.split(r'\[|\]', dn)[1]
        vrf = re.split(r'/|dom-', dn)[7]
        tn = vrf
        if vrf.find(":") != -1:
            tn = re.search("(.*):(.*)", vrf).group(1)

        check_longest_name(node, "Node")
        check_longest_name(intf, "Interface")
        check_longest_name(ip, "IP Address")
        check_longest_name(cfg, "Admin Status")
        check_longest_name(op, "Status")

        if args.tenant is None:
            if vrf not in data.keys():
                data[vrf] = []
            else:
                data[vrf].append((node, intf, ip, cfg, op))
        else:
            if tn == args.tenant:
                if vrf not in data.keys():
                    data[vrf] = []
                else:
                    data[vrf].append((node, intf, ip, cfg, op))

    for k in data.keys():
        header = 'IP Interface Status for VRF "{}"'.format(k)
        print(header)
        template = '{0:' + str(longest_names["Node"]) + '} ' \
                   '{1:' + str(longest_names["Interface"]) + '} ' \
                   '{2:' + str(longest_names["IP Address"]) + '} ' \
                   '{3:' + str(longest_names["Admin Status"]) + '} ' \
                   '{4:' + str(longest_names["Status"]) + '}'
        print(template.format("Node", "Interface", "IP Address", "Admin Status", "Status"))
        print(template.format('-' * longest_names["Node"],
                              '-' * longest_names["Interface"],
                              '-' * longest_names["IP Address"],
                              '-' * longest_names["Admin Status"],
                              '-' * longest_names["Status"]))
        for rec in sorted(data[k]):
            print(template.format(*rec))
        print('')


def check_longest_name(item, title):
    """
    Check the longest name
    :param item: String containing the name
    :param title: String containing the column title
    """
    if len(item) > longest_names[title]:
        longest_names[title] = len(item)


if __name__ == '__main__':
    main()
