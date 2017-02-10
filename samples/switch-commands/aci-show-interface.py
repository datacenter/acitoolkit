#!/usr/bin/env python
"""
This application replicates the switch CLI command 'show interface'
It largely uses raw queries to the APIC API
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate
import datetime
import dateutil.parser

class InterfaceBriefCollector(object):
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

    # def show_detailed(self, node=None, intf_id=None):
    #     """
    #     show interface
    #
    #     :param node: String containing the specific switch id. If none, all switches are used
    #     :param intf_id: String containing the specific interface id. If none, all interfaces are used
    #     :return: None
    #     """
    #     for node_id in self.get_node_ids(node):
    #         self.populate_detailed_interfaces(node_id, intf_id)
    #     raise NotImplementedError

class Interface(object):
    def __init__(self, data):
        self._data = data
        self._beacon_state = '--'
        for key in self._data:
            self.if_type = key
            break

    def is_ether(self):
        if self.if_type == 'l1PhysIf':
            return True
        return False

    def is_vfc(self):
        if self.if_type == 'l2VfcIf':
            return True
        return False

    def is_mgmt(self):
        if self.if_type == 'mgmtMgmtIf':
            return True
        return False

    def is_loop(self):
        if self.if_type == 'l3LbRtdIf':
            return True
        return False

    def is_pc(self):
        if self.if_type == 'pcAggrIf':
            return True
        return False

    def is_tun(self):
        if self.if_type == 'tunnelIf':
            return True
        return False

    def is_sub(self):
        if self.if_type == 'l3EncRtdIf':
            return True
        return False

    def is_svi(self):
        if self.if_type == 'sviIf':
            return True
        return False

    def is_member_pc(self):
        if 'children' not in self._data[self.if_type]:
            return False
        for child in self._data[self.if_type]['children']:
            if 'l1RtMbrIfs' in child:
                return True
        return False

    def _get_child_attribute(self, child_type, child_attribute):
        if 'children' not in self._data[self.if_type]:
            return ''
        for child in self._data[self.if_type]['children']:
            if child_type in child:
                return child[child_type]['attributes'][child_attribute]
        return ''

    def _get_grandchild_attribute(self, child_type, grandchild_type, grandchild_attribute):
        if 'children' not in self._data[self.if_type]:
            return ''
        for child in self._data[self.if_type]['children']:
            if child_type in child:
                if 'children' not in child[child_type]:
                    continue
                for grandchild in child[child_type]['children']:
                    if grandchild_type in grandchild:
                        return str(grandchild[grandchild_type]['attributes'][grandchild_attribute])
        return ''

    @property
    def port_channel_id(self):
        if not self.is_member_pc():
            return ''
        for child in self._data[self.if_type]['children']:
            if 'l1RtMbrIfs' in child:
                return str(child['l1RtMbrIfs']['attributes']['tSKey'])

    @property
    def port_cap_speed(self):
        return self._get_grandchild_attribute('ethpmPhysIf', 'ethpmPortCap', 'speed')

    @property
    def port_cap_fcot_capable(self):
        return self._get_grandchild_attribute('ethpmPhysIf', 'ethpmPortCap', 'fcotCapable')

    @property
    def port_cap_rate_mode(self):
        return self._get_grandchild_attribute('ethpmPhysIf', 'ethpmPortCap', 'rateMode')

    @property
    def interface_type(self):
        return self._get_grandchild_attribute('ethpmPhysIf', 'ethpmPortCap', 'type')


    def _attribute(self, attribute):
        return self._data[self.if_type]['attributes'][attribute]

    @property
    def backplane_mac(self):
        return self._get_child_attribute('ethpmPhysIf', 'backplaneMac')

    @property
    def last_link_st_chg(self):
        return self._get_child_attribute('ethpmPhysIf', 'lastLinkStChg')

    @property
    def router_mac(self):
        return self._attribute('routerMac')

    @property
    def layer(self):
        return self._attribute('layer')

    @property
    def mode(self):
        return self._attribute('mode')

    @property
    def mdix(self):
        return self._attribute('mdix')

    @property
    def bw(self):
        return self._attribute('bw')

    @property
    def delay(self):
        return self._attribute('delay')

    @property
    def mtu(self):
        return self._attribute('mtu')

    @property
    def auto_neg(self):
            return self._attribute('autoNeg')

    @property
    def span_mode(self):
        return self._attribute('spanMode')

    @property
    def dot1q_ethertype(self):
        return self._attribute('dot1qEtherType')

    @property
    def address(self):
        if self.layer == 'Layer2':
            return self.backplane_mac
        else:
            return self.router_mac

    @property
    def id(self):
        return self._data[self.if_type]['attributes']['id']

    @property
    def descr(self):
        if 'descr' not in self._data[self.if_type]['attributes']:
            return ''
        return str(self._data[self.if_type]['attributes']['descr'])

    @property
    def switching_st(self):
        return self._data[self.if_type]['attributes']['switchingSt']

    @property
    def oper_st_qual(self):
        return self._get_child_attribute('ethpmPhysIf', 'operStQual')

    @property
    def oper_err_dis_qual(self):
        return self._get_child_attribute('ethpmPhysIf', 'operErrDisQual')

    @property
    def oper_mode(self):
        return self._get_child_attribute('ethpmPhysIf', 'operMode')

    @property
    def oper_duplex(self):
        return self._get_child_attribute('ethpmPhysIf', 'operDuplex')

    @property
    def speed(self):
        return self._get_child_attribute('ethpmPhysIf', 'operSpeed')

    @property
    def oper_fec_mode(self):
        return self._get_child_attribute('ethpmPhysIf', 'operFecMode')

    @property
    def reset_ctr(self):
        return self._get_child_attribute('ethpmPhysIf', 'resetCtr')

    @property
    def eee_state(self):
        return self._get_child_attribute('l1EeeP', 'eeeState')

    @property
    def fcot_str(self):
        resp = ''
        if self.port_cap_speed != '':
            if self.port_cap_fcot_capable == '1':
                # TODO: Interface type is a list of numbers what are they ?
                if self.interface_type == "sfp":
                    resp = ", media type is 1G"
                elif self.interface_type == "xfp" or self.interface_type == "x2":
                    resp = ", media type is 10G"
                elif self.interface_type == "sfp28":
                    resp = ", media type is 25G"
                elif self.interface_type == "qsfp" or self.interface_type == "cfp-40g":
                    resp = ", media type is 40G"
                elif self.interface_type == "cfp" or self.interface_type == "cfp-100g":
                    resp = ", media type is 100G"
                # if self.flags == 'ok-no-md5':
                #     resp += ' (Xcvr authentication in progress)'
        return resp

    @property
    def reliability(self):
        input_errors = int(self._get_child_attribute('rmonIfIn', 'errors'))
        output_errors = int(self._get_child_attribute('rmonIfOut', 'errors'))
        errors = input_errors + output_errors
        ingress_packets = int(self._get_child_attribute('rmonEtherStats', 'rXNoErrors'))
        egress_packets = int(self._get_child_attribute('rmonEtherStats', 'tXNoErrors'))
        frames = ingress_packets + egress_packets
        if frames > 0:
            reliability = 255 - ((255 * errors) / frames)
        else:
            reliability = 255
        return reliability

    @property
    def clear_ts(self):
        return self._get_child_attribute('rmonEtherStats', 'clearTs')

    @property
    def tx_load(self):
        tx_load = self._get_child_attribute('eqptEgrTotal5min', 'bytesRate')
        if tx_load == '':
            tx_load = 1
        bw = int(self.bw)
        if bw == 0:
            return 0
        return 255 * (int(tx_load) * 8) / (bw * 1000)

    @property
    def rx_load(self):
        rx_load = self._get_child_attribute('eqptIngrTotal5min', 'bytesRate')
        bw = int(self.bw)
        if rx_load == '':
            rx_load = 1
        if bw == 0:
            return 0
        return 255 * (int(rx_load) * 8) / (bw * 1000)

    def _get_child_counter(self, child_type, child_attribute ):
        rate = self._get_child_attribute(child_type, child_attribute)
        if rate == '':
            rate = '0'
        return rate

    @property
    def input_bitrate_30sec(self):
        return int(self._get_child_counter('eqptIngrTotal5min', 'bytesRateLast')) * 8

    @property
    def input_packetrate_30sec(self):
        return int(self._get_child_counter('eqptIngrTotal5min', 'pktsRateLast'))

    @property
    def output_bitrate_30sec(self):
        return int(self._get_child_counter('eqptEgrTotal5min', 'bytesRateLast')) * 8

    @property
    def output_packetrate_30sec(self):
        return int(self._get_child_counter('eqptEgrTotal5min', 'pktsRateLast'))

    @property
    def input_bitrate_300sec(self):
        return int(self._get_child_counter('eqptIngrTotal5min', 'bytesRate')) * 8

    @property
    def input_packetrate_300sec(self):
        return int(self._get_child_counter('eqptIngrTotal5min', 'pktsRate'))

    @property
    def output_bitrate_300sec(self):
        return int(self._get_child_counter('eqptEgrTotal5min', 'bytesRate')) * 8

    @property
    def output_packetrate_300sec(self):
        return int(self._get_child_counter('eqptEgrTotal5min', 'pktsRate'))

    @property
    def oper_st(self):
        if 'children' not in self._data[self.if_type]:
            return None
        for child in self._data[self.if_type]['children']:
            if 'ethpmPhysIf' in child:
                return child['ethpmPhysIf']['attributes']['operSt']

    @property
    def admin_st(self):
        if_type = self.if_type
        resp = str(self._data[if_type]['attributes']['adminSt'])
        if if_type == 'l1PhysIf':
            resp += ', Dedicated Interface'
        return resp

    @property
    def beacon_state(self):
        return self._beacon_state

    @beacon_state.setter
    def beacon_state(self, value):
        self._beacon_state = value

    @property
    def rx_unicast_packets(self):
        return int(self._get_child_counter('rmonIfIn', 'ucastPkts'))

    @property
    def rx_error_packets(self):
        return int(self._get_child_counter('rmonIfIn', 'errors'))

    @property
    def rx_input_packets(self):
        return self.rx_unicast_packets + self.rx_error_packets

    @property
    def rx_input_discard(self):
        return int(self._get_child_counter('rmonIfIn', 'discards'))

    @property
    def rx_multicast_packets(self):
        return int(self._get_child_counter('rmonIfIn', 'multicastPkts'))

    @property
    def rx_broadcast_packets(self):
        return int(self._get_child_counter('rmonIfIn', 'broadcastPkts'))

    @property
    def rx_input_bytes(self):
        return int(self._get_child_counter('rmonIfIn', 'octets'))

    @property
    def rx_pause_frames(self):
        return int(self._get_child_counter('rmonDot3Stats', 'inPauseFrames'))

    @property
    def bad_proto_drop(self):
        return int(self._get_child_counter('rmonIfIn', 'unknownProtos'))

    @property
    def rx_oversize_packets(self):
        return self._get_child_counter('rmonEtherStats', 'rxOversizePkts')

    @property
    def rx_storm_supression_packets(self):
        return self._get_child_counter('rmonIfStorm', 'dropBytes')

    @property
    def rx_runts(self):
        return self._get_child_counter('rmonEtherStats', 'undersizePkts')

    @property
    def rx_crc(self):
        return self._get_child_counter('rmonEtherStats', 'cRCAlignErrors')

    @property
    def tx_unicast_packets(self):
        return int(self._get_child_counter('rmonIfOut', 'ucastPkts'))

    @property
    def tx_error_packets(self):
        return int(self._get_child_counter('rmonIfOut', 'errors'))

    @property
    def tx_output_packets(self):
        return self.tx_unicast_packets + self.tx_error_packets

    @property
    def tx_output_discard(self):
        return int(self._get_child_counter('rmonIfOut', 'discards'))

    @property
    def tx_multicast_packets(self):
        return int(self._get_child_counter('rmonIfOut', 'multicastPkts'))

    @property
    def tx_broadcast_packets(self):
        return int(self._get_child_counter('rmonIfOut', 'broadcastPkts'))

    @property
    def tx_output_bytes(self):
        return int(self._get_child_counter('rmonIfOut', 'octets'))

    @property
    def tx_oversize_packets(self):
        return self._get_child_counter('rmonEtherStats', 'txOversizePkts')

    @property
    def collisions(self):
        return self._get_child_counter('rmonEtherStats', 'collisions')

    @property
    def deferred_transmissions(self):
        return self._get_child_counter('rmonDot3Stats', 'deferredTransmissions')

    @property
    def late_collisions(self):
        return self._get_child_counter('rmonDot3Stats', 'lateCollisions')

    @property
    def carrier_sense_errors(self):
        return self._get_child_counter('rmonDot3Stats', 'carrierSenseErrors')

    @property
    def out_pause_frames(self):
        return self._get_child_counter('rmonDot3Stats', 'outPauseFrames')


class InterfaceDetailedCollector(object):
    def __init__(self, url, login, password):
        # Login to APIC
        self._apic = Session(url, login, password)
        if not self._apic.login().ok:
            self._logged_in = False
            print '%% Could not login to APIC'
        else:
            self._logged_in = True
        self._interfaces = []

    def _get_query(self, query_url, error_msg):
        resp = self._apic.get(query_url)
        if not resp.ok:
            print error_msg
            print resp.text
            return []
        return resp.json()['imdata']

    def _populate_beacon_states(self, data):
        for beacon_data in data:
            if 'eqptLocLed' not in beacon_data:
                continue
            dn = beacon_data['eqptLocLed']['attributes']['dn']
            oper_state = beacon_data['eqptLocLed']['attributes']['operSt']
            if 'leafport-' in dn:
                port_num = dn.partition('/leafport-')[2].partition('/')[0]
                mod_num = dn.partition('/lcslot-')[2].partition('/')[0]
                node_num = dn.partition('/node-')[2].partition('/')[0]
                beacon_interface_id = 'eth' + mod_num + '/' + port_num
                beacon_node_id = '/node-%s/' % node_num
                for interface in self._interfaces:
                    if not interface.is_ether():
                        continue
                    if interface.id == beacon_interface_id:
                        if beacon_node_id in dn:
                            interface.beacon_state = oper_state

    def populate_detailed_interfaces(self, node_id, intf_id=None):
        query_url = ('/api/mo/topology/pod-1/node-%s/sys.json?query-target=subtree'
                     '&target-subtree-class=l1PhysIf,pcAggrIf,l3LbRtdIf,tunnelIf,sviIf,l3EncRtdIf,'
                     'mgmtMgmtIf,l2ExtIf,l2VfcIf,eqptLocLed&rsp-subtree=full&'
                     'rsp-subtree-class=ethpmPhysIf,ethpmPortCap,l1RtMbrIfs,ethpmAggrIf,'
                     'rmonEtherStats,rmonIfIn,rmonIfOut,rmonIfStorm,eqptIngrTotal5min,'
                     'eqptEgrTotal5min,l1EeeP,rmonDot3Stats' % node_id)
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        interfaces = self._get_query(query_url, error_message)
        self._interfaces = []
        if intf_id is None:
            for interface in interfaces:
                self._interfaces.append(Interface(interface))
        else:
            for interface in interfaces:
                for if_type in interface:
                    if if_type == 'eqptLocLed':
                        continue
                    if interface[if_type]['attributes']['id'] == intf_id:
                        self._interfaces.append(Interface(interface))
        self._populate_beacon_states(interfaces)


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

    def show_detailed(self, node=None, intf_id=None):
        """
        show interface

        :param node: String containing the specific switch id. If none, all switches are used
        :param intf_id: String containing the specific interface id. If none, all interfaces are used
        :return: None
        """
        for node_id in self.get_node_ids(node):
            print 'Switch', node_id
            self.populate_detailed_interfaces(node_id, intf_id)
            for interface in self._interfaces:
                if interface.if_type == 'l1PhysIf':
                    if interface.is_ether or interface.is_pc() or interface.is_tun():
                        state = interface.oper_st
                        rsn = interface.oper_st_qual
                        if state is None:
                            state = "unknown"
                            rsn = "unknown"
                        if state == 'link-up':
                            # see ethpm_copy_eth_port_log_info()
                            # link-up state is physical up, but not operationally up
                            state = 'down'
                        if state == 'up':
                            if not interface.is_tun() and interface.switching_st == 'disabled':
                                print "%s is %s (%s)" % (interface.id, state, "out-of-service")
                            else:
                                print "%s is %s" % (interface.id, state)
                        elif interface.oper_st_qual == "err-disabled":
                            print "%s is %s (%s)" % (interface.id, state, interface.oper_err_dis_qual)
                        else:
                            print "%s is %s (%s)" % (interface.id, state, rsn)

                    print 'admin state is', interface.admin_st
                    if interface.is_member_pc():
                        print "  Belongs to %s" % interface.port_channel_id
                    if not interface.descr == '':
                        print '  Port description is', interface.descr
                    print '  Hardware:', interface.port_cap_speed, 'Ethernet, address:', interface.address, \
                          '(bia', interface.backplane_mac, ')'
                    print '  MTU', interface.mtu, 'bytes, BW', interface.bw, 'Kbit, DLY', interface.delay, 'usec'
                    print '  reliability', '%s/255' % interface.reliability, \
                          'txload %d/255, rxload %d/255' %  (interface.tx_load, interface.rx_load)
                    print '  Encapsulation ARPA, medium is broadcast'
                    if interface.layer != 'Layer2':
                        print '  Port mode is routed'
                    else:
                        print "  Port mode is %s" % interface.mode
                    if not interface.is_mgmt() and interface.oper_mode == 'ips':
                        duplex = 'auto'
                    else:
                        duplex = interface.oper_duplex
                    print "  %s-duplex, %sb/s%s" % (duplex, interface.speed, interface.fcot_str)
                    if (interface.is_ether() and not interface.is_sub()) or interface.is_mgmt():
                        if not interface.is_mgmt():
                            print '  FEC (forward-error-correction) :', interface.oper_fec_mode
                        print "  Beacon is turned", interface.beacon_state
                        print "  Auto-Negotiation is turned", interface.auto_neg
                    if interface.is_ether() or interface.is_pc() or interface.is_mgmt():
                        print "  Input flow-control is off, output flow-control is off"
                        if interface.mdix == 'auto':
                            print "  Auto-mdix is turned on"
                        else:
                            print "  Auto-mdix is turned off"
                    elif interface.is_loop():
                        print "  Auto-mdix is turned off"
                    if interface.is_ether() and not interface.is_sub() and interface.port_cap_fcot_capable == '1':
                        if interface.port_cap_rate_mode == "1":
                            rateMode = "dedicated"
                        elif interface.port_cap_rate_mode == "2":
                            rateMode = "shared"
                        else:
                            rateMode = interface.port_cap_rate_mode
                        print "  Rate mode is %s" % rateMode

                    if interface.is_ether():
                        if interface.span_mode == "not-a-span-dest":
                            print '  Switchport monitor is off'
                        else:
                            print '  Switchport monitor is on'

                    if interface.is_ether() or interface.is_pc() or interface.is_mgmt():
                        print '  EtherType is', interface.dot1q_ethertype

                    if interface.is_ether():
                        if interface.eee_state == "not-applicable":
                            print "  EEE (efficient-ethernet) : n/a"
                        elif interface.eee_state == "enable":
                            print "  EEE (efficient-ethernet) : Operational"
                        elif interface.eee_state == "disable":
                            print "  EEE (efficient-ethernet) : Disabled"
                        elif interface.eee_state == "disagreed":
                            print "  EEE (efficient-ethernet) : Disagreed"

                        if interface.last_link_st_chg.startswith('1970-'):
                            print "  Last link flapped never"
                        else:
                            last_flap = dateutil.parser.parse(interface.last_link_st_chg).replace(tzinfo=None)
                            seconds_since_flap = datetime.datetime.now() - last_flap
                            print "  Last link flapped", seconds_since_flap

                    if interface.is_ether() or interface.is_pc() or interface.is_svi():
                        last_clear = 'never'
                        if interface.clear_ts != 'never':
                            last_clear = dateutil.parser.parse(interface.clear_ts).replace(tzinfo=None)
                        print '  Last clearing of "show interface" counters %s' % last_clear
                        if not interface.is_svi():
                            print '  ', interface.reset_ctr,'interface resets'
                    elif interface.is_tun():
                        pass
                    if interface.is_svi():
                        pass
                    elif interface.is_ether() or interface.is_pc():
                        print "  30 seconds input rate %d bits/sec, %d packets/sec" % \
                               (interface.input_bitrate_30sec, interface.input_packetrate_30sec)
                        print "  30 seconds output rate %d bits/sec, %d packets/sec" % \
                               (interface.output_bitrate_30sec, interface.output_packetrate_30sec)
                        print "  Load-Interval #2: 5 minute (300 seconds)"
                        print "    input rate %d bps, %d pps; output rate %d bps, %d pps" % \
                                (interface.input_bitrate_300sec, interface.input_packetrate_300sec,
                                 interface.output_bitrate_300sec, interface.output_packetrate_300sec)
                        if interface.layer == 'Layer3':
                            print "  L3 in Switched:"
                            print "    ucast: %d pkts, %d bytes - mcast: %d pkts, %d bytes" % \
                                  (0, 0, 0, 0)
                                                        # (stats.l3InSwitchedUcastPackets,
                                                        #  stats.l3InSwitchedUcastBytes,
                                                        #  stats.l3InSwitchedMcastPackets,
                                                        #  stats.l3InSwitchedMcastBytes)
                            print "  L3 out Switched:"
                            print "    ucast: %d pkts, %d bytes - mcast: %d pkts, %d bytes" % \
                                  (0, 0, 0, 0)
                                                        # (stats.l3OutSwitchedUcastPackets,
                                                        #  stats.l3OutSwitchedUcastBytes,
                                                        #  stats.l3OutSwitchedMcastPackets,
                                                        #  stats.l3OutSwitchedMcastBytes)
                    if (interface.is_ether() or interface.is_pc()) and not interface.is_sub():
                        print "  RX"
                        ucast = "%d unicast packets" % interface.rx_unicast_packets
                        mcast = "%d multicast packets" % interface.rx_multicast_packets
                        bcast = "%d broadcast packets" % interface.rx_broadcast_packets
                        print "    %s  %s  %s" % (ucast, mcast, bcast)

                        pkts = "%d input packets" % interface.rx_input_packets
                        bytes = "%d bytes" % interface.rx_input_bytes
                        print "    %s  %s" % (pkts, bytes)

                        print '   ', interface.rx_oversize_packets, 'jumbo packets ',\
                              interface.rx_storm_supression_packets, 'storm suppression bytes'

                        print '   ', interface.rx_runts, 'runts', interface.rx_oversize_packets,\
                              'giants', interface.rx_crc, 'CRC  0 no buffer'

                        print '   ', interface.rx_error_packets, 'input error',\
                              interface.rx_runts, 'short frame  0 overrun  0 underrun  0 ignored'

                        print '    0 watchdog  0 bad etype drop', interface.bad_proto_drop,\
                              'bad proto drop  0 if down drop'

                        print '    0 input with dribble', interface.rx_input_discard, 'input discard'

                        print '   ', interface.rx_pause_frames, 'Rx pause'

                        print '  TX'
                        print '   ', interface.tx_unicast_packets, 'unicast packets', interface.tx_multicast_packets,\
                              'multicast packets', interface.tx_broadcast_packets, 'broadcast packets'

                        print '   ', interface.tx_output_packets, 'output packets', interface.tx_output_bytes, 'bytes'
                        print '   ', interface.tx_oversize_packets, 'jumbo packets'
                        print '   ', interface.tx_error_packets, 'output error', interface.collisions, 'collision',\
                              interface.deferred_transmissions, 'deferred', interface.late_collisions, 'late collision'
                        print '    0 lost carrier', interface.carrier_sense_errors, '0 babble',\
                              interface.tx_output_discard, 'output discard'
                        print '   ', interface.out_pause_frames, 'Tx pause'

                    print ""


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


    if args.brief:
        interface_collector = InterfaceBriefCollector(args.url, args.login, args.password)
        interface_collector.show_brief(node=args.switch, intf_id=args.interface)
    else:
        interface_collector = InterfaceDetailedCollector(args.url, args.login, args.password)
        interface_collector.show_detailed(node=args.switch, intf_id=args.interface)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
