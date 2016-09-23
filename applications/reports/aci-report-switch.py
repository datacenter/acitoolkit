#!/usr/bin/env python
################################################################################
#               _    ____ ___   ____                       _                   #
#              / \  / ___|_ _| |  _ \ ___ _ __   ___  _ __| |_ ___             #
#             / _ \| |    | |  | |_) / _ \ '_ \ / _ \| '__| __/ __|            #
#            / ___ \ |___ | |  |  _ <  __/ |_) | (_) | |  | |_\__ \            #
#           /_/   \_\____|___| |_| \_\___| .__/ \___/|_|   \__|___/            #
#                                        |_|                                   #
#                                                                              #
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
Simple application that logs on to the APIC and displays all
of the Interfaces.
"""
import datetime
from operator import attrgetter
import sys

# noinspection PyPep8Naming
import acitoolkit as ACI

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application that logs on to the APIC and displays reports for the switches.'
creds = ACI.Credentials('apic, nosnapshotfiles', description)
creds.add_argument('-s', '--switch',
                   type=str,
                   default=None,
                   help='Specify a particular switch id, e.g. "102"')
creds.add_argument('-all', action="store_true",
                   help='Show all detailed information')
creds.add_argument('-basic', action="store_true", help='Show basic switch info')
creds.add_argument('-linecard', action="store_true", help='Show Lincard info')
creds.add_argument('-supervisor', action="store_true", help='Show Supervisor Card info')
creds.add_argument('-fantray', action="store_true", help='Show Fantray info')
creds.add_argument('-powersupply', action="store_true", help='Show Power Supply info')
creds.add_argument('-arp', action="store_true", help='Show ARP info')
creds.add_argument('-cdp', action="store_true", help='Show CDP info')
creds.add_argument('-context', action="store_true", help='Show Context (VRF) info')
creds.add_argument('-bridgedomain', action="store_true", help='Show Bridge Domain info')
creds.add_argument('-svi', action="store_true", help='Show SVI info')
creds.add_argument('-accessrule', action="store_true", help='Show Access Rule and Filter info')
creds.add_argument('-endpoint', action="store_true", help='Show End Point info')
creds.add_argument('-portchannel', action="store_true", help='Show Port Channel and Virtual Port Channel info')
creds.add_argument('-overlay', action="store_true", help='Show Overlay info')
creds.add_argument('-tablefmt', type=str, default='fancy_grid',
                   help='Table format [fancy_grid, plain, simple, grid, '
                        'pipe, orgtbl, rst, mediawiki, latex, latex_booktabs]')
args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)


def show_switch_short(switch_id, table_format):
    """
    Setup template and display header information for summary version of switch info

    :param table_format: The format to be used when rendering the table
    :param switch_id: Optional switch Id to select a specific switch.  If ommitted, will be all switches.
    """

    if switch_id:
        switches = ACI.Node.get(session, '1', switch_id)
    else:
        switches = ACI.Node.get(session)

    tables = ACI.Node.get_table(switches, title='All Switches')
    text_string = tables[0].get_text(tablefmt=table_format) + '\n'
    print text_string


def render_text_switch(switch, table_format):
    """
    Render the switch info into a text string that can be directly display on
    a text monitor.
    :param table_format: format for displaying table
    :param switch:
    """

    title = 'Switch:{0} ("{1}") - '.format(switch.node, switch.name)
    text_string = ''
    if args.all or args.basic:
        tables = ACI.Node.get_table([switch], title)
        text_string += tables[0].get_text(tablefmt=table_format) + '\n'

    if args.all or args.supervisor:
        tables = ACI.Supervisorcard.get_table(switch.get_children(ACI.Supervisorcard), title)
        text_string += tables[0].get_text(tablefmt=table_format) + '\n'

    if args.all or args.linecard:
        tables = ACI.Linecard.get_table(switch.get_children(ACI.Linecard), title)
        text_string += tables[0].get_text(tablefmt=table_format) + '\n'

    if args.all or args.powersupply:
        tables = ACI.Powersupply.get_table(switch.get_children(ACI.Powersupply), title)
        text_string += tables[0].get_text(tablefmt=table_format) + '\n'

    if args.fantray or args.all:
        tables = ACI.Fantray.get_table(switch.get_children(ACI.Fantray), title)
        text_string += tables[0].get_text(tablefmt=table_format) + '\n'

    if args.all or args.overlay:
        overlays = switch.get_children(ACI.ConcreteOverlay)
        tables = ACI.ConcreteOverlay.get_table(overlays, title)
        for table in tables:
            text_string += table.get_text(tablefmt=table_format) + '\n'

        tunnels = overlays[0].get_children(ACI.ConcreteTunnel)
        tables = ACI.ConcreteTunnel.get_table(tunnels, title)
        for table in tables:
            text_string += table.get_text(tablefmt=table_format) + '\n'

    if args.all or args.context:
        text_string += render_tables(switch, ACI.ConcreteContext, title, table_format)

    if args.all or args.bridgedomain:
        text_string += render_tables(switch, ACI.ConcreteBD, title, table_format)

    if args.all or args.svi:
        text_string += render_tables(switch, ACI.ConcreteSVI, title, table_format)

    if args.all or args.accessrule:
        text_string += render_tables(switch, ACI.ConcreteAccCtrlRule, title, table_format)
        text_string += render_tables(switch, ACI.ConcreteFilter, title, table_format)

    if args.all or args.arp:
        text_string += render_tables(switch, ACI.ConcreteArp, title, table_format)

    if args.all or args.cdp:
        text_string += render_tables(switch, ACI.ConcreteCdp, title, table_format)

    if args.all or args.endpoint:
        text_string += render_tables(switch, ACI.ConcreteEp, title, table_format)

    if args.all or args.portchannel:
        text_string += render_tables(switch, ACI.ConcretePortChannel, title, table_format)
        text_string += render_tables(switch, ACI.ConcreteVpc, title, table_format)
        vpc_ifs = []
        for vpc in switch.get_children(ACI.ConcreteVpc):
            vpc_ifs.extend(vpc.get_children(ACI.ConcreteVpcIf))
        if vpc_ifs:
            tables = ACI.ConcreteVpcIf.get_table(vpc_ifs, title)
            for table in tables:
                text_string += table.get_text(tablefmt=table_format) + '\n'
    return text_string


def render_tables(switch, concrete_class, title, table_format):
    """
    Will create a table and return it as a string
    with the title

    :param table_format: format for displaying table
    :param switch:
    :param title: Title string for table
    :param concrete_class:  Concrete class to build the table for
    :return: String version of the table
    """
    text_string = ''
    tables = concrete_class.get_table(switch.get_children(concrete_class), title)
    for table in tables:
        text_string += table.get_text(tablefmt=table_format) + '\n'
    return text_string


def show_switch_long():
    """
    This function will display the long version of the switch information.
    What to display is controlled through args
    """
    if args.switch:
        switches = ACI.Node.get(session, '1', args.switch)
    else:
        switches = ACI.Node.get(session)

    for switch in sorted(switches, key=attrgetter('node')):
        if switch.role != 'controller':

            switch.populate_children(deep=True, include_concrete=True)

            print render_text_switch(switch, args.tablefmt)


if (args.all or
        args.basic or
        args.linecard or
        args.supervisor or
        args.fantray or
        args.powersupply or
        args.arp or
        args.cdp or
        args.context or
        args.bridgedomain or
        args.svi or
        args.accessrule or
        args.endpoint or
        args.portchannel or
        args.overlay):

    start_time = datetime.datetime.now()
    show_switch_long()
    end_time = datetime.datetime.now()
    print 'Elapsed time=', end_time - start_time

else:
    show_switch_short(args.switch, args.tablefmt)
