#!/usr/bin/env python
"""
This application replicates the switch CLI command 'show vlan info'
It largely uses raw queries to the APIC API
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate


def show_vlan_brief(apic, node_ids):
    """
    show vlan brief
    :param apic: Session instance logged in to the APIC
    :param node_ids: List of strings containing node ids
    """
    for node_id in node_ids:
        query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree&'
                     'target-subtree-class=l2BD,l2RsPathDomAtt' % node_id)
        resp = apic.get(query_url)
        if not resp.ok:
            print 'Could not collect APIC data for switch %s.' % node_id
            return
        l2bd_data = []
        port_data = {}
        for obj in resp.json()['imdata']:
            if 'l2BD' in obj:
                obj_attr = obj['l2BD']['attributes']
                l2bd_data.append((int(obj_attr['id']), str(obj_attr['name']),
                                  str(obj_attr['adminSt']), str(obj_attr['fabEncap'])))
            else:
                dn = obj['l2RsPathDomAtt']['attributes']['dn']
                port_id = str(dn.rpartition('/path-[')[2].partition(']')[0])
                port_bd_encap = str(dn.partition('/bd-[')[2].partition(']')[0])
                if port_bd_encap not in port_data:
                    port_data[port_bd_encap] = port_id
                port_data[port_bd_encap] += ', ' + port_id
        output_data = []
        for (l2bd_id, l2bd_name, l2bd_admin_state, l2bd_fab_encap) in l2bd_data:
            try:
                ports = port_data[str(l2bd_fab_encap)]
            except KeyError:
                ports = ''
            output_data.append((l2bd_id, l2bd_name, l2bd_admin_state, ports))
        output_data.sort(key=lambda tup: tup[0])
        print 'Switch:', node_id
        print tabulate(output_data, headers=["VLAN", "Name", "Status", "Ports"])


def show_vlan_info(apic, node_ids):
    """
    show vlan info
    :param apic: Session instance logged in to the APIC
    :param node_ids: List of strings containing node ids
    """
    for node_id in node_ids:
        query_url = '/api/mo/topology/pod-1/node-%s.json?query-target=subtree&target-subtree-class=l2BD' % node_id
        resp = apic.get(query_url)
        if not resp.ok:
            print 'Could not collect APIC data for switch %s.' % node_id
            return
        data = []
        for l2bd in resp.json()['imdata']:
            l2bd_attr = l2bd['l2BD']['attributes']
            encap = str(l2bd_attr['fabEncap'])
            if str(l2bd_attr['accEncap']) != 'unknown':
                encap += ', ' + str(l2bd_attr['accEncap'])
            data.append((int(l2bd_attr['id']), 'enet', str(l2bd_attr['mode']), encap))
        data.sort(key=lambda tup: tup[0])
        print 'Switch:', node_id
        print tabulate(data, headers=["VLAN", "Type", "Vlan-mode", "Encap"])


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
        query_url = '/api/node/class/fabricNode.json?query-target-filter=eq(fabricNode.role,"leaf")'
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
    Main common routine for show vlan ext, show vlan brief, and show vlan info
    :return: None
    """
    # Set up the command line options
    creds = Credentials(['apic', 'nosnapshotfiles'],
                        description="This application replicates the switch CLI command 'show vlan extended'")
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

    node_ids = get_node_ids(apic, args)
    show_vlan_brief(apic, node_ids)
    show_vlan_info(apic, node_ids)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
