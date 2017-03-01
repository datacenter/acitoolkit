#!/usr/bin/env python
"""
This application replicates the switch CLI command 'show interface description'
It largely uses raw queries to the APIC API
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate


def show_interface_description(apic, node_ids, apic_intf_class='l1PhysIf',
                               specific_interface=None):
    """
    Show the interface description

    :param apic: Session instance logged in to the APIC
    :param node_ids: List of strings containing node ids
    :param apic_intf_class: String containing the APIC interface class
    :param specific_interface: String containing the specific interface name
                               to limit the command
    :return: None
    """
    for node_id in node_ids:
        query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                     '&target-subtree-class=%s' % (node_id, apic_intf_class))
        if specific_interface is not None:
            query_url += '&query-target-filter=eq(%s.id,"%s")' % (apic_intf_class,
                                                                  specific_interface)
        resp = apic.get(query_url)
        if not resp.ok:
            print 'Could not collect APIC data for switch %s.' % node_id
            print resp.text
            return
        data = []
        headers = []
        for obj in resp.json()['imdata']:
            obj_attr = obj[apic_intf_class]['attributes']
            if obj_attr['descr'] == '':
                description = '--'
            else:
                description = obj_attr['descr']
            if 'speed' in obj_attr:
                data.append((obj_attr['id'], 'eth', obj_attr['speed'], description))
                headers = ["Port", "Type", "Speed", "Description"]
            else:
                data.append((obj_attr['id'], description))
                headers = ["Interfaces", "Description"]
        if len(headers) and len(data):
            print 'Switch:', node_id
            print tabulate(data, headers=headers)
            print '\n'


def get_node_ids(apic, args):
    """
    Get the list of node ids from the command line arguments.
    If none, get all of the node ids
    :param apic: Session instance logged in to the APIC
    :param args: Command line arguments
    :return: List of strings containing node ids
    """
    if args.switch is not None:
        names = [args.switch]
    else:
        names = []
        query_url = ('/api/node/class/fabricNode.json?'
                     'query-target-filter=eq(fabricNode.role,"leaf")')
        resp = apic.get(query_url)
        if not resp.ok:
            print 'Could not get switch list from APIC.'
            return
        nodes = resp.json()['imdata']
        for node in nodes:
            names.append(str(node['fabricNode']['attributes']['id']))
    return names


def main():
    """
    Main common routine for show interface description
    :return: None
    """
    # Set up the command line options
    creds = Credentials(['apic', 'nosnapshotfiles'],
                        description=("This application replicates the switch "
                                     "CLI command 'show interface description'"))
    creds.add_argument('-s', '--switch',
                       type=str,
                       default=None,
                       help='Specify a particular switch id, e.g. "101"')
    creds.add_argument('-i', '--interface',
                       type=str,
                       default=None,
                       help='Specify a specific interface, e.g. "eth1/1"')
    args = creds.get()

    # Login to APIC
    apic = Session(args.url, args.login, args.password)
    if not apic.login().ok:
        print('%% Could not login to APIC')
        return

    # Show interface description
    node_ids = get_node_ids(apic, args)
    apic_intf_classes = ['l1PhysIf', 'pcAggrIf', 'l3EncRtdIf', 'sviIf',
                         'tunnelIf', 'mgmtMgmtIf', 'l3LbRtdIf']
    for apic_intf_class in apic_intf_classes:
        show_interface_description(apic, node_ids, apic_intf_class=apic_intf_class,
                                   specific_interface=args.interface)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
