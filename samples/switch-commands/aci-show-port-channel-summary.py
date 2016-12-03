#!/usr/bin/env python
"""
This application replicates the switch CLI command 'show port-channel summary'
It largely uses raw queries to the APIC API
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate


class InterfaceCollector(object):
    def __init__(self, url, login, password):
        # Login to APIC
        self._apic = Session(url, login, password)
        if not self._apic.login().ok:
            self._logged_in = False
            print '%% Could not login to APIC'
        else:
            self._logged_in = True
        self._interfaces = []
        self._port_channels = []

    def _get_query(self, query_url, error_msg):
        resp = self._apic.get(query_url)
        if not resp.ok:
            print error_msg
            print resp.text
            return []
        return resp.json()['imdata']

    def populate_port_channels(self, node_id, intf_id=None):
        query_url = ('/api/mo/topology/pod-1/node-%s/sys.json?query-target=subtree'
                     '&target-subtree-class=pcAggrIf&rsp-subtree=children&'
                     'rsp-subtree-class=ethpmAggrIf,pcRsMbrIfs' % node_id)
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        port_channels = self._get_query(query_url, error_message)
        if intf_id is None:
            self._port_channels = port_channels
        else:
            self._port_channels = []
            for port_channel in port_channels:
                for if_type in port_channel:
                    if port_channel[if_type]['attributes']['id'] == intf_id:
                        self._port_channels.append(port_channel)

    def populate_interfaces(self, node_id):
        query_url = ('/api/mo/topology/pod-1/node-%s/sys.json?query-target=subtree'
                     '&target-subtree-class=l1PhysIf&rsp-subtree=children&'
                     'rsp-subtree-class=pcAggrMbrIf' % node_id)
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        self._interfaces = self._get_query(query_url, error_message)

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

    def _get_member_extension(self, port_channel):
        resp = ''
        for child in port_channel['pcAggrIf']['children']:
            if 'pcRsMbrIfs' in child:
                for interface in self._interfaces:
                    if child['pcRsMbrIfs']['attributes']['tDn'] == interface['l1PhysIf']['attributes']['dn']:
                        oper_attr = interface['l1PhysIf']['children'][0]['pcAggrMbrIf']['attributes']
                        if oper_attr['operSt'] == 'module-removed':
                            resp = '(r)'
                        elif oper_attr['operSt'] == 'up':
                            resp = '(P)'
                        elif oper_attr['channelingSt'] == 'individual':
                            resp = "(I)"
                        elif oper_attr['channelingSt'] == 'suspended':
                            resp = "(s)"
                        elif oper_attr['channelingSt'] == 'hot-standby':
                            resp = "(H)"
                        else:
                            resp = "(D)"
                    if resp != '':
                        break
        return resp

    def show_summary(self, node=None, intf_id=None):
        """
        show port-channel summary

        :param node: String containing the specific switch id. If none, all switches are used
        :param intf_id: String containing the specific interface id. If none, all interfaces are used
        :return: None
        """
        for node_id in self.get_node_ids(node):
            self.populate_interfaces(node_id)
            self.populate_port_channels(node_id, intf_id)
            if not len(self._port_channels):
                continue
            print "Switch:", node_id
            print "Flags:  D - Down        P - Up in port-channel (members)"
            print "        I - Individual  H - Hot-standby (LACP only)"
            print "        s - Suspended   r - Module-removed"
            print "        S - Switched    R - Routed"
            print "        U - Up (port-channel)"
            print "        M - Not in use. Min-links not met"
            print "        F - Configuration failed"
            data = []
            for interface in self._port_channels:
                intf_attr = interface['pcAggrIf']['attributes']
                name = intf_attr['id']
                if intf_attr['layer'] == 'Layer2':
                    name += "(S"
                else:
                    name += "(R"

                for child in interface['pcAggrIf']['children']:
                    if 'ethpmAggrIf' in child:
                        oper_attr = child['ethpmAggrIf']['attributes']
                        if oper_attr['operSt'] == 'up':
                            name += "U)"
                        elif intf_attr['suspMinlinks'] == 'yes':
                            name += "M)"
                        else:
                            name += "D)"
                        members = oper_attr['activeMbrs']
                        while ',unspecified,' in members:
                            members = members.replace(',unspecified,', ',')
                        members = members.replace(',unspecified', '')

                members += self._get_member_extension(interface)
                protocol = 'none'
                if intf_attr['pcMode'] in ['active', 'passive', 'mac-pin']:
                    protocol = 'lacp'
                data.append((int(intf_attr['id'][2:]), name, 'eth', protocol, members))
            data.sort(key=lambda tup: tup[0])
            headers = ['Group', 'Port channel', 'Type', 'Protocol', 'Member Ports']
            print tabulate(data, headers=headers)


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
                       help='Specify a particular interface id, e.g. "po101"')
    args = creds.get()

    interface_collector = InterfaceCollector(args.url, args.login, args.password)

    interface_collector.show_summary(node=args.switch, intf_id=args.interface)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
