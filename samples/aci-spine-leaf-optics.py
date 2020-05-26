#!/usr/bin/env python
"""
This application is made to gather the inventory of all the Optics 
connecting Leaf and Spines.  It largely uses raw queries to the APIC API
"""
import acitoolkit.acitoolkit as ACI
from acitoolkit import Credentials, Session
from tabulate import tabulate
import logging
logging.basicConfig()


def interface_detail(apic, args, switch_attributes, intf_ids):
    """
    Capture Optics Between Leaf and Spine
    :param apic: Session instance logged in to the APIC
    :switch_attributes: Node ID, Hostname, Fabric Role
    :param intf_ids: List of Interfaces with PortType Fabric
    :return: None
    """
    data = []
    headers = []
    for list in intf_ids:
        node_id,hostname,role,switch_intf = list
        #print(node)
        #print(switch_intf)
        query_url1 = ('/api/node/mo/topology/pod-1/node-%s/sys/phys-[%s]/phys.json'
                      '?query-target=children&target-subtree-class=ethpmFcot&subscription=yes' % (node_id, switch_intf))
        query_url2 = ('/api/node/mo/topology/pod-1/node-%s/sys/lldp/inst/if-[%s].json'
                      '?query-target=children&target-subtree-class=lldpAdjEp' % (node_id, switch_intf))
        resp1 = apic.get(query_url1)
        if not resp1.ok:
            print('Could not collect Optic data for switch %s Interface %s.' % (node_id, switch_intf))
            print(resp1.text)
            return
        resp2 = apic.get(query_url2)
        if not resp2.ok:
            print('Could not collect LLDP Neigbhor data for switch %s Interface %s.' % (node_id, switch_intf))
            print(resp2.text)
            return
        for obj1 in resp1.json()['imdata']:
            obj_attr1 = obj1['ethpmFcot']['attributes']
            if obj_attr1['typeName'] == '':
                optic = '--'
            else:
                optic = obj_attr1['typeName']
            for obj2 in resp2.json()['imdata']:
                obj_attr2 = obj2['lldpAdjEp']['attributes']
                if obj_attr2['sysName'] == '':
                    neighbor = '--'
                else:
                    neighbor = obj_attr2['sysName']
                if obj_attr2['portIdV'] == '':
                    port = '--'
                else:
                    port = obj_attr2['portIdV']
                for group in switch_attributes:
                    node_x,hostx,rolex = group
                    lport = port.lower()
                    #print(node_x)
                    #print(hostx)
                    #print(rolex)
                    #print(neighbor)
                    #print(port)
                    #print(lport)
                    if hostx == neighbor:
                        query_url3 = ('/api/node/mo/topology/pod-1/node-%s/sys/phys-[%s]/phys.json'
                                      '?query-target=children&target-subtree-class=ethpmFcot&subscription=yes' % (node_x, lport))
                        resp3 = apic.get(query_url3)
                        if not resp3.ok:
                            print('Could not collect Optic data for Spine %s Interface %s.' % (node_x, lport))
                            print(resp3.text)
                            return
                        for obj3 in resp3.json()['imdata']:
                            obj_attr3 = obj3['ethpmFcot']['attributes']
                            if obj_attr3['typeName'] == '':
                                spine_optic = '--'
                            else:
                                spine_optic = obj_attr3['typeName']
                            data.append((node_id, hostname, switch_intf, optic, spine_optic, port, neighbor))
                    #elif rolex == 'spine':
                    #    print(node_x)
                    #elif rolex == 'leaf':
                    #    print(node_x)
                    #else:
                    #    data.append((node_id, hostname, switch_intf, optic, '--', port, neighbor))
    headers = ["Node_ID", "Hostname", "Interface", "Local Optic", "Remote Optic" , "Neighbor Interface", "LLDP Neighbor"]
    if len(headers) and len(data):
        print(tabulate(data, headers=headers))
        print('\n')


def get_intf_ids(apic, args, switch_attributes):
    """
    Get the list of Physical Interface IDs from the command line arguments.
    If none, get all of the node ids
    :param apic: Session instance logged in to the APIC
    :param args: Command line arguments
    :return: List of strings containing Interface ids
    """
    intfs = []
    for Attributes in switch_attributes:
        node_id,hostname,Role = Attributes
        if Role == 'leaf':
            query_url = ('/api/node/class/topology/pod-1/node-%s/l1PhysIf.json?'
                         'rsp-subtree=children&rsp-subtree-class=ethpmPhysIf' % (node_id))
                         
            resp = apic.get(query_url)
            if not resp.ok:
                print('Could not get Interface list from APIC.')
                return
            ints = resp.json()['imdata']
            for int in ints:
                if int['l1PhysIf']['attributes']['portT'] == 'fab':
                    intx = node_id,hostname,Role,str(int['l1PhysIf']['attributes']['id'])
                    #print intx
                    intfs.append(intx)
    return intfs

def get_switch_attributes(apic, args):
    """
    Get the list of node ids from the command line arguments.
    If none, get all of the node ids
    :param apic: Session instance logged in to the APIC
    :param args: Command line arguments
    :return: List of strings containing node ids
    """
    names = []
    query_url = ('/api/node/class/fabricNode.json?'
                 'query-target-filter=or(eq(fabricNode.role,"leaf"),'
                 'eq(fabricNode.role,"spine"))')
                 
    resp = apic.get(query_url)
    if not resp.ok:
        print('Could not get switch list from APIC.')
        return
    nodes = resp.json()['imdata']
    for node in nodes:
        switch_attr = (str(node['fabricNode']['attributes']['id']),
                      str(node['fabricNode']['attributes']['name']),
                      str(node['fabricNode']['attributes']['role']))
        #print(switch_attr)
        names.append(switch_attr)
    return names


def main():
    """
    Main common routine for show interface description
    :return: None
    """
    # Set up the command line options
    description = ('Simple application that logs in to the APIC'
                   'and displays the Interface Optics and Neighbors')
    creds = ACI.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    apic = ACI.Session(args.url, args.login, args.password)
    resp = apic.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Show interface Optic & LLDP Neighbor
    #print('starting node_ids')
    switch_attributes = get_switch_attributes(apic, args)
    #print('starting intf_ids')
    intf_ids = get_intf_ids(apic, args, switch_attributes)
    #print('starting Section for Optics and Neighbors')
    interface_detail(apic, args, switch_attributes, intf_ids)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
