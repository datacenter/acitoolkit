#!/usr/bin/env python

"""
Simple application that shows all of the processes running on a switch
"""
import sys
import acitoolkit as ACI
from acitoolkit.acitoolkitlib import Credentials


def main():
    """
    Main show Process routine
    :return: None
    """
    description = 'Simple application that logs on to the APIC and displays process information for a switch'
    creds = Credentials('apic', description)

    creds.add_argument('-s', '--switch',
                       type=str,
                       default=None,
                       help='Specify a particular switch id, e.g. "102"')
    args = creds.get()

    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    switches = ACI.Node.get(session, '1', args.switch)
    for switch in switches:
        if switch.role != 'controller':
            processes = ACI.Process.get(session, switch)
            tables = ACI.Process.get_table(processes, 'Process list for Switch ' + switch.name + '::')
            for table in tables:
                try:
                    print(table.get_text(tablefmt='fancy_grid') + '\n')
                except UnicodeEncodeError:
                    print(table.get_text(tablefmt='plain') + '\n')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
