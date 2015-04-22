#!/usr/bin/env python
################################################################################
# _    ____ ___   ____                       _                   #
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
import sys
from acitoolkit.aciConcreteLib import *
import acitoolkit.acitoolkit as ACI
import acitoolkit.aciphysobject as ACI_PHYS
from acitoolkit.acitoolkitlib import Credentials

#from SwitchJson import SwitchJson

# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = 'Simple application that logs on to the APIC and displays stats for all of the Interfaces.'
creds = Credentials('apic', description)
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
creds.add_argument('-context', action="store_true", help='Show Context (VRF) info')
creds.add_argument('-bridgedomain', action="store_true", help='Show Bridge Domain info')
creds.add_argument('-accessrule', action="store_true", help='Show Access Rule and Filter info')
creds.add_argument('-endpoint', action="store_true", help='Show End Point info')
creds.add_argument('-portchannel', action="store_true", help='Show Port Channel and Virtual Port Channel info')
creds.add_argument('-overlay', action="store_true", help='Show Overlay info')

args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)


def show_switch_short(switch_id):
    """
    Setup template and display header information for summary version of switch info

    :param switch_id: Optional switch Id to select a specific switch.  If ommitted, will be all switches.
    """
    template = "{0:^7} | {1:^14} | {2:^11} | {3:^15} | {4:^5} | {5:^16} |"\
               "{6:^6} | {7:^20} | {8:^20} | {9:^8} | {10:^11}"
    line_template = "{0:-^7}-+-{0:-^14}-+-{0:-^11}-+-{0:-^15}-+-{0:-^5}-+-"\
                    "{0:-^16}-+-{0:-^6}-+-{0:-^20}-+-{0:-^20}-+-{0:-^8}-+-{0:-^11}"
    print template.format("Node ID", "Name", "Role", "Model", "Ports", "State", "Health", "In-Band Mgmt IP",
                          "Out-of-band Mgmt IP", "Firmware", "Serial")
    print line_template.format("")

    if switch_id:
        switches = ACI_PHYS.Node.get(session, '1', switch_id)
    else:
        switches = ACI_PHYS.Node.get(session)
    for switch in sorted(switches, key=lambda x: x.node):
        if switch.role != 'controller':
            print template.format(switch.node,
                                  switch.name,
                                  switch.role,
                                  switch.model,
                                  switch.num_ports,
                                  switch.state,
                                  switch.health,
                                  switch.inb_mgmt_ip,
                                  switch.oob_mgmt_ip,
                                  switch.firmware,
                                  switch.serial)


def render_text_switch(switch):
    """
    Render the switch info into a text string that can be directly display on
    a text monitor.
    :param top:
    :param switch:
    """
    title = 'Switch:{0} ("{1}") - '.format(switch.node, switch.name)
    text_string = ''
    if args.all or args.basic:
        tables = ACI_PHYS.Node.get_table(switch, title)
        text_string += tables[0].get_text(tablefmt='fancy_grid') + '\n'

    if args.all or args.supervisor:
        tables = ACI_PHYS.Supervisorcard.get_table(switch.get_children(ACI_PHYS.Supervisorcard), title)
        text_string += tables[0].get_text(tablefmt='fancy_grid') + '\n'

    if args.all or args.linecard:
        tables = ACI_PHYS.Linecard.get_table(switch.get_children(ACI_PHYS.Linecard), title)
        text_string += tables[0].get_text(tablefmt='fancy_grid') + '\n'

    if args.all or args.powersupply:
        tables = ACI_PHYS.Powersupply.get_table(switch.get_children(ACI_PHYS.Powersupply), title)
        text_string += tables[0].get_text(tablefmt='fancy_grid') + '\n'

    if args.fantray or args.all:
        tables = ACI_PHYS.Fantray.get_table(switch.get_children(ACI_PHYS.Fantray), title)
        text_string += tables[0].get_text(tablefmt='fancy_grid') + '\n'

    if args.all or args.overlay:
        text_string += render_tables(switch, ConcreteOverlay, title)

    if args.all or args.context:
        text_string += render_tables(switch, ConcreteContext, title)

    if args.all or args.bridgedomain:
        text_string += render_tables(switch, ConcreteBD, title)

    if args.all or args.accessrule:
        text_string += render_tables(switch, ConcreteAccCtrlRule, title)
        text_string += render_tables(switch, ConcreteFilter, title)

    if args.all or args.arp:
        text_string += render_tables(switch, ConcreteArp, title)

    if args.all or args.endpoint:
        text_string += render_tables(switch, ConcreteEp, title)

    if args.all or args.portchannel:
        text_string += render_tables(switch, ConcretePortChannel, title)
        text_string += render_tables(switch, ConcreteVpc, title)

    return text_string


def render_tables(switch, concrete_class, title):
    """
    Will create a table and return it as a string
    with the title

    :param title: Title string for table
    :param top: Source of json data
    :param concrete_class:  Concrete class to build the table for
    :return: String version of the table
    """
    text_string = ''
    tables = concrete_class.get_table(switch.get_children(concrete_class), title)
    for table in tables:
        text_string += table.get_text(tablefmt='fancy_grid') + '\n'
    return text_string


def show_switch_long():
    
    """
    This function will display the long version of the switch information.
    What to display is controlled through args
    """
    if args.switch:
        switches = ACI_PHYS.Node.get(session, '1', args.switch)
    else:
        switches = ACI_PHYS.Node.get(session)

    for switch in sorted(switches, key=lambda x: x.node):
        if switch.role != 'controller':

            switch.populate_children(deep=True, include_concrete=True)

            print render_text_switch(switch)


if (args.all or
        args.basic or
        args.linecard or
        args.supervisor or
        args.fantray or
        args.powersupply or
        args.arp or
        args.context or
        args.bridgedomain or
        args.accessrule or
        args.endpoint or
        args.portchannel or
        args.overlay):
    show_switch_long()
else:
    show_switch_short(args.switch)
