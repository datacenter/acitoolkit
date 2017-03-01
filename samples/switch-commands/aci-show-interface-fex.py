#!/usr/bin/env python
"""
This application replicates the switch CLI command 'show interface fex'
It largely uses raw queries to the APIC API
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate


def show_interface_fex(apic, node_ids):
    """
    Show interface fex

    :param apic: Session instance logged in to the APIC
    :param node_ids: List of strings containing node ids
    :return: None
    """
    for node_id in node_ids:
        query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                     '&target-subtree-class=satmDExtCh' % node_id)
        resp = apic.get(query_url)
        if not resp.ok:
            print 'Could not collect APIC data for switch %s.' % node_id
            print resp.text
            return
        fex_list = {}
        for obj in resp.json()['imdata']:
            obj_attr = obj['satmDExtCh']['attributes']
            fex_list[obj_attr['id']] = (obj_attr['model'], obj_attr['ser'])
        query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                     '&target-subtree-class=satmFabP' % node_id)
        resp = apic.get(query_url)
        if not resp.ok:
            print 'Could not collect APIC data for switch %s.' % node_id
            print resp.text
            return
        data = []
        for obj in resp.json()['imdata']:
            obj_attr = obj['satmFabP']['attributes']
            fex = obj_attr['extChId']
            fabric_port = obj_attr['id']
            if fabric_port.startswith('po'):
                continue
            fabric_port_state = obj_attr['fsmSt']
            fex_uplink = obj_attr['remoteLinkId']
            try:
                model, serial = fex_list[fex]
            except KeyError:
                model, serial = '--', '--'
            data.append((int(fex), fabric_port, fabric_port_state, fex_uplink, model, serial))
        data.sort(key=lambda tup: tup[0])
        if len(data):
            print 'Switch:', node_id
            print tabulate(data, headers=['Fex', 'Fabric Port', 'Fabric Port State',
                                          'Fex uplink', 'Fex model', 'Fex serial'])
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
                                     "CLI command 'show interface fex'"))
    creds.add_argument('-s', '--switch',
                       type=str,
                       default=None,
                       help='Specify a particular switch id, e.g. "101"')
    args = creds.get()

    # Login to APIC
    apic = Session(args.url, args.login, args.password)
    if not apic.login().ok:
        print('%% Could not login to APIC')
        return

    # Show interface description
    node_ids = get_node_ids(apic, args)
    show_interface_fex(apic, node_ids)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
