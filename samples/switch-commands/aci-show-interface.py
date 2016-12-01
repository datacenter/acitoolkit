#!/usr/bin/env python
"""
This application replicates the switch CLI command 'show interface'
It largely uses raw queries to the APIC API
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate


class InterfaceCollector(object):
    def __init__(self, url, login, password):
        # Login to APIC
        self._apic = Session(url, login, password)
        self._if_brief_headers = {
            'l1PhysIf': ['Ethernet Interface', 'VLAN', 'Type', 'Mode', 'Status', 'Reason', 'Speed', 'Port Ch #'],
            'pcAggrIf': ['Port-channel Interface', 'VLAN', 'Type', 'Mode', 'Status', 'Reason', 'Speed', 'Protocol'],
            'l3LbRtdIf': ['Interface', 'Status', 'Description'],
            'tunnelIf': ['Interface', 'Status', 'IP Address', 'Encap type', 'MTU'],
            'sviIf': ['Interface', 'Secondary VLAN(Type)', 'Status', 'Reason'],
            'l3EncRtdIf': [],
            'mgmtMgmtIf': ['Port', 'VRF', 'Status', 'IP Address', 'Speed', 'MTU'],
            'l2ExtIf': [],
            'l2VfcIf': ['Interface', 'Vsan', 'Admin\nMode', 'Admin Trunk Mode', 'Status',
                        'Bind Info', 'Oper Mode', 'Oper Speed (Gbps)']
        }
        self._if_types = self._if_brief_headers.keys()
        if not self._apic.login().ok:
            self._logged_in = False
            print '%% Could not login to APIC'
        else:
            self._logged_in = True
        self._interfaces = []

    @property
    def _all_if_types_as_string(self):
        resp = ''
        for if_type in self._if_types:
            if len(resp):
                resp += ','
            resp += if_type
        return resp

    def _get_query(self, query_url, error_msg):
        resp = self._apic.get(query_url)
        if not resp.ok:
            print error_msg
            print resp.text
            return []
        return resp.json()['imdata']

    def populate_interfaces(self, node_id, intf_id=None):
        query_url = ('/api/mo/topology/pod-1/node-%s/sys.json?query-target=subtree'
                     '&target-subtree-class=%s&rsp-subtree=children&'
                     'rsp-subtree-class=ethpmPhysIf,l1RtMbrIfs,ethpmAggrIf' % (node_id, self._all_if_types_as_string))
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        interfaces = self._get_query(query_url, error_message)
        if intf_id is None:
            self._interfaces = interfaces
        else:
            self._interfaces = []
            for interface in interfaces:
                for if_type in interface:
                    if interface[if_type]['attributes']['id'] == intf_id:
                        self._interfaces.append(interface)

    def _has_interface_type(self, if_type, intf_id=None):
        for interface in self._interfaces:
            if if_type in interface:
                if intf_id is None or intf_id == interface[if_type]['attributes']['id']:
                    return True
        return False

    def _get_interface_type(self, if_type):
        resp = []
        for interface in self._interfaces:
            if if_type in interface:
                resp.append(interface)
        return resp

    def get_node_ids(self, node_id):
        """
        Get the list of node ids from the command line arguments.
        If none, get all of the node ids
        :param args: Command line arguments
        :return: List of strings containing node ids
        """
        if node_id is not None:
            names = [node_id]
        else:
            names = []
            query_url = ('/api/node/class/fabricNode.json?'
                         'query-target-filter=eq(fabricNode.role,"leaf")')
            error_message = 'Could not get switch list from APIC.'
            nodes = self._get_query(query_url, error_message)
            for node in nodes:
                names.append(str(node['fabricNode']['attributes']['id']))
        return names

    @staticmethod
    def convert_to_ascii(data):
        data = str(data).split(',')
        resp = ''
        for letter in data:
            resp += str(unichr(int(letter)))
        return resp

    def _get_interface_type_brief_data(self, if_type, intf_id=None):
        data = []
        for interface in self._interfaces:
            if if_type in interface:
                if intf_id is not None and intf_id != interface[if_type]['attributes']['id']:
                    continue
                if_attrs = interface[if_type]['attributes']
                if if_type == 'mgmtMgmtIf':
                    data.append((if_attrs['id'], '--', if_attrs['adminSt'], '', if_attrs['speed'], if_attrs['mtu']))
                elif if_type == 'l1PhysIf':
                    port_channel = '--'
                    for child in interface[if_type]['children']:
                        if 'l1RtMbrIfs' in child:
                            port_channel = child['l1RtMbrIfs']['attributes']['tSKey']
                        else:
                            oper_attrs = child['ethpmPhysIf']['attributes']
                    data.append((if_attrs['id'], '--', 'eth', oper_attrs['operMode'], oper_attrs['operSt'],
                                 oper_attrs['operStQual'], oper_attrs['operSpeed'], port_channel))
                elif if_type == 'tunnelIf':
                    data.append((if_attrs['id'], if_attrs['operSt'], '--', if_attrs['tType'], if_attrs['cfgdMtu']))
                elif if_type == 'pcAggrIf':
                    for child in interface[if_type]['children']:
                        protocol = '--'
                        if if_attrs['pcMode'] in ['active', 'passive', 'mac-pin']:
                            protocol = 'lacp'
                        elif if_attrs['pcMode'] == 'static':
                            protocol = 'none'
                        if 'ethpmAggrIf' in child:
                            oper_attrs = child['ethpmAggrIf']['attributes']
                    data.append((if_attrs['id'], '--', 'eth', oper_attrs['operMode'], oper_attrs['operSt'],
                                 oper_attrs['operStQual'], oper_attrs['operSpeed'], protocol))
                elif if_type == 'sviIf':
                    data.append((if_attrs['id'], '--', if_attrs['operSt'], if_attrs['operStQual']))
                elif if_type == 'l3LbRtdIf':
                    if len(if_attrs['descr']):
                        description = if_attrs['descr']
                    else:
                        description = '--'
                    data.append((if_attrs['id'], if_attrs['adminSt'], description))
                elif if_type == 'l2VfcIf':
                    raise NotImplementedError
                    # TODO: finish this
        return data

    def show_brief(self, node=None, intf_id=None):
        """
        show interface brief

        :param node: String containing the specific switch id. If none, all switches are used
        :param intf_id: String containing the specific interface id. If none, all interfaces are used
        :return: None
        """
        for node_id in self.get_node_ids(node):
            self.populate_interfaces(node_id, intf_id)

            for if_type in self._if_types:
                if self._has_interface_type(if_type, intf_id):
                    data = self._get_interface_type_brief_data(if_type, intf_id)
                    data.sort(key=lambda tup: tup[0])
                    if len(data):
                        print tabulate(data, headers=self._if_brief_headers[if_type])
                        print

    def show_detailed(self, node=None, intf_id=None):
        """
        show interface

        :param node: String containing the specific switch id. If none, all switches are used
        :param intf_id: String containing the specific interface id. If none, all interfaces are used
        :return: None
        """
        raise NotImplementedError


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
    creds.add_argument('-i', '--interface',
                       type=str,
                       default=None,
                       help='Specify a particular interface id, e.g. "eth1/10"')
    creds.add_argument('-b', '--brief',
                       action='store_true',
                       help='Display a brief summary')
    args = creds.get()

    interface_collector = InterfaceCollector(args.url, args.login, args.password)

    if args.brief:
        interface_collector.show_brief(node=args.switch, intf_id=args.interface)
    else:
        print 'detailed view is still under development...try brief view instead'

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
