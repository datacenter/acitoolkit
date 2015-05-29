#!/usr/bin/env python
################################################################################
#                 _    ____ ___   _____           _ _    _ _                   #
#                / \  / ___|_ _| |_   _|__   ___ | | | _(_) |_                 #
#               / _ \| |    | |    | |/ _ \ / _ \| | |/ / | __|                #
#              / ___ \ |___ | |    | | (_) | (_) | |   <| | |_                 #
#        ____ /_/   \_\____|___|___|_|\___/ \___/|_|_|\_\_|\__|                #
#       / ___|___   __| | ___  / ___|  __ _ _ __ ___  _ __ | | ___  ___        #
#      | |   / _ \ / _` |/ _ \ \___ \ / _` | '_ ` _ \| '_ \| |/ _ \/ __|       #
#      | |__| (_) | (_| |  __/  ___) | (_| | | | | | | |_) | |  __/\__ \       #
#       \____\___/ \__,_|\___| |____/ \__,_|_| |_| |_| .__/|_|\___||___/       #
#                                                    |_|                       #
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""
Simple application that shows all of the processes running on a switch
"""
import sys
import acitoolkit.acitoolkit as ACI
#import acitoolkit.aciphysobject as ACI_PHYS
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
        print '%% Could not login to APIC'
        sys.exit(0)

    switches = ACI.Node.get(session, '1', args.switch)
    for switch in switches:
        if switch.role != 'controller':
            processes = ACI.Process.get(session, switch)
            tables = ACI.Process.get_table(processes, 'Process list for Switch ' + switch.name + '::')
            for table in tables:
                print table.get_text(tablefmt='fancy_grid') + '\n'


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
