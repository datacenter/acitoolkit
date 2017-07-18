#!/usr/bin/env python

import os
import acitoolkit.acitoolkit as aci


def main():
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the External Subnets.')
    creds = aci.Credentials('apic', description)
    creds.add_argument('--tenant', help='The name of Tenant')
    args = creds.get()

    option = ''
    if args.tenant is not None:
        option = ' --tenant ' + args.tenant

    execute('show contexts', 'aci-show-contexts.py' + option)
    execute('show contracts', 'aci-show-contracts.py' + option)
    execute('show epgs', 'aci-show-epgs.py' + option)
    execute('show external epgs', 'aci-show-external-networks.py' + option)
    execute('show ip interface brief', 'aci-show-ip-int-brief.py' + option)
    execute('show subnets', 'aci-show-subnets.py' + option)


def execute(title, command):
    show_header(title)
    os.system('./' + command)


def show_header(title):
    print("\n==================== " + title + " ====================")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
