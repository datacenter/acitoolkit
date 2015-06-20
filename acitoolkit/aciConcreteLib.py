#!/usr/bin/env python
################################################################################
# #
################################################################################
# #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
# #
# Licensed under the Apache License, Version 2.0 (the "License"); you may   #
# not use this file except in compliance with the License. You may obtain   #
# a copy of the License at                                                  #
# #
# http://www.apache.org/licenses/LICENSE-2.0                           #
# #
# Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""
This is a library of all the Concrete classes that are on a switch.
"""
"""
"""
# all the import
from .acibaseobject import BaseACIPhysObject
import acitoolkit as ACI
import copy
from .aciTable import Table
from .aciSearch import Searchable


class ConcreteArp(BaseACIPhysObject):
    """
    This class is for the ARP state on a switch.  It is organized into two data structures.
    The first is self.attr which holds attributes for the Arp in general.
    The second is self.domain which is a list of arp domains.  Each arp domain then has
    a few fields:
    self.domain[x].stats
    self.domain[x].entry
    self.domain[x].name
    self.domain[x].encap
    """

    def __init__(self, parent=None):
        """
            Initialize the ARP object.
            """

        super(ConcreteArp, self).__init__(parent=parent)
        self.attr = {}
        self.domain = []
        self._parent = parent
        if parent is not None:
            self._parent.add_child(self)

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['arpInst', 'arpDomStatsAdj', 'arpDomStatsRx', 'arpDomStatsTx', 'arpDom', 'arpDb', 'arpAdjEp']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        Will retrieve all of the ARP information for the specified
        switch node
        :param parent: Parent object of type Node
        :param top:
        """
        cls.check_parent(parent)

        result = []
        node_data = top.get_class('arpInst')
        for data in node_data:
            if 'arpInst' in data:
                arp = cls()
                arp.attr['adminSt'] = data['arpInst']['attributes']['adminSt']
                arp.attr['dn'] = data['arpInst']['attributes']['dn']
                arp.get_arp_domain(top)
                result.append(arp)
            if parent:
                arp._parent = parent
                arp._parent.add_child(arp)
        return result

    def get_arp_domain(self, working_data):
        """
        Get various attributes from the arp domain
        :param working_data:
        """

        data = working_data.get_subtree('arpDom', self.attr['dn'])
        for domain in data:
            result = {'stats': {},
                      'entry': [],
                      'name': domain['arpDom']['attributes']['name'],
                      'encap': domain['arpDom']['attributes']['encap']}
            arpdom_dn = domain['arpDom']['attributes']['dn']
            result['stats'].update(self.get_stats('arpDomStatsAdj',arpdom_dn, working_data))
            result['stats'].update(self.get_stats('arpDomStatsRx', arpdom_dn, working_data))
            result['stats'].update(self.get_stats('arpDomStatsTx', arpdom_dn, working_data))

            arpdb_data = working_data.get_subtree('arpDb', arpdom_dn)
            for arpdb_datum in arpdb_data:
                entry = self.get_arp_entry(arpdb_datum['arpDb']['attributes']['dn'], working_data)
                result['entry'].append(entry)

            if ':' in result['name']:
                result['tenant'] = result['name'].split(':')[0]
                result['context'] = result['name'].split(':')[1]
            else:
                result['tenant'] = ''
                result['context'] = result['name']

            self.domain.append(result)

    def get_stats(self, apic_class, dn, working_data):
        stat_data = working_data.get_subtree(apic_class, dn)
        if stat_data:
            return stat_data[0][apic_class]['attributes']
        return {}

    @staticmethod
    def get_arp_entry(dn, working_data):
        """
        parses arpAdjEp
        :param working_data:
        :param dn:
        """
        data = working_data.get_subtree('arpAdjEp', dn)
        entry = {}
        for datum in data:

            entry = {'interface_id': datum['arpAdjEp']['attributes']['ifId'],
                     'ip': datum['arpAdjEp']['attributes']['ip'],
                     'mac': datum['arpAdjEp']['attributes']['mac'],
                     'physical_interface': datum['arpAdjEp']['attributes']['physIfId'],
                     'oper_st': datum['arpAdjEp']['attributes']['operSt']}
        return entry

    @staticmethod
    def get_table(arps, title=''):
        """
        Returns arp information in a displayable format.
        :param title:
        :param arps:
        """
        result = []
        headers = ['Tenant', 'Context', 'Add', 'Delete', 'Timeout.',
                   'Resolved', 'Incomplete', 'Total', 'Rx Pkts',
                   'Rx Drop', 'Tx Pkts', 'Tx Drop', 'Tx Req',
                   'Tx Grat Req', 'Tx Resp']
        data = []
        for arp in arps:
            for domain in arp.domain:
                data.append([
                    domain.get('tenant', ''),
                    domain.get('context', ''),
                    domain['stats'].get('adjAdd', ''),
                    domain['stats'].get('adjDel', ''),
                    domain['stats'].get('adjTimeout', ''),
                    domain['stats'].get('resolved', ''),
                    domain['stats'].get('incomplete', ''),
                    domain['stats'].get('total', ''),
                    domain['stats'].get('pktRcvd', ''),
                    domain['stats'].get('pktRcvdDrp', ''),
                    domain['stats'].get('pktSent', ''),
                    domain['stats'].get('pktSentDrop', ''),
                    domain['stats'].get('pktSentReq', ''),
                    domain['stats'].get('pktSentGratReq', ''),
                    domain['stats'].get('pktSentRsp', '')
                ])

            data = sorted(data)
            result.append(Table(data, headers, title=title + 'ARP Stats'))

            headers = ['Tenant', 'Context', 'MAC Address', 'IP Address',
                       'Physical I/F', 'Interface ID', 'Oper Status']
            data = []
            for domain in arp.domain:
                for entry in domain['entry']:
                    data.append([
                        str(domain.get('tenant', '')),
                        str(domain.get('context', '')),
                        str(entry.get('mac', '')),
                        str(entry.get('ip', '')),
                        str(entry.get('physical_interface', '')),
                        str(entry.get('interface_id', '')),
                        str(entry.get('oper_st', ''))
                    ])
            result.append(Table(data, headers, title=title + 'ARP Entries'))

        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        """
        result = [Searchable('arp')]

        for domain in self.domain:
            if 'entry' in domain:
                for entry in domain['entry']:
                    if entry['ip'] is not None:
                        result.append(Searchable('ipv4', entry['ip'], 'indirect'))
                    if entry['mac'] is not None:
                        result.append(Searchable('mac', entry['mac'], 'indirect'))
                    if entry['physical_interface'] is not None:
                        result.append(Searchable('interface', entry['physical_interface']))
            if domain['name']:
                result.append(Searchable('context', domain['context'], 'indirect'))
                result.append(Searchable('name', domain['name'], 'primary'))
            if domain['tenant']:
                result.append(Searchable('tenant', domain['tenant'], 'indirect'))

        return result

    def __str__(self):
        return 'ConcreteARP'

    def __eq__(self, other):

        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteVpc(BaseACIPhysObject):
    """
    class for the VPC information for a switch

    It will contain peer info and port membership.
    """

    def __init__(self, parent=None):
        """
        VPC info for a switch
        """
        super(ConcreteVpc, self).__init__(parent=parent)
        self.member_ports = []
        self.peer_info = {}
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['vpcEntity', 'vpcDom']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        Will retrieve all of the VPC information for the switch
        and returns the ConcreteVPC object.

        :param parent:
        :param top: the topSystem level json object
        :returns: list of Switch context
        """
        cls.check_parent(parent)

        result = []
        vpc_data = top.get_class('vpcEntity')
        for vpc_d in vpc_data:
            if 'vpcEntity' in vpc_d:
                vpc = cls()
                vpc._populate_from_attributes(vpc_d['vpcEntity']['attributes'])
                vpc._populate_from_inst(top)
                vpc.member_ports = ConcreteVpcIf.get(top, vpc)
                result.append(vpc)
            if parent:
                vpc._parent = parent
                vpc._parent.add_child(vpc)

        return result

    def _populate_from_attributes(self, attr):
        """
        Fill in attribute
        """
        self.attr['oper_st'] = str(attr['operSt'])
        self.attr['dn'] = str(attr['dn'])

    def _populate_from_inst(self, top):
        """
        get info from the instance
        """
        inst_data = top.get_subtree('vpcInst', self.attr['dn'])
        self.attr['admin_st'] = None
        for inst in inst_data:
            if 'vpcInst' in inst:
                self.attr['admin_st'] = str(inst['vpcInst']['attributes']['adminSt'])
                self._populate_from_dom(top, inst['vpcInst']['attributes']['dn'])

    def _populate_from_dom(self, top, dname):
        """
        Populate attributes from dom
        """
        dom_data = top.get_subtree('vpcDom', dname)
        self.attr['dom_present'] = False
        for dom in dom_data:
            if 'vpcDom' in dom:
                self.attr['dom_present'] = True
                attr = dom['vpcDom']['attributes']
                self.attr['compat_str'] = str(attr['compatQualStr'])
                self.attr['compat_st'] = str(attr['compatSt'])
                self.attr['dual_active_st'] = str(attr['dualActiveSt'])
                self.attr['id'] = str(attr['id'])
                self.attr['role'] = str(attr['lacpRole'])
                self.attr['local_mac'] = str(attr['localMAC'])
                self.attr['modify_time'] = str(attr['modTs'])
                self.attr['name'] = str(attr['name'])
                self.attr['dom_oper_st'] = str(attr['operSt'])
                self.attr['orphan_ports'] = str(attr['orphanPortList'])
                self.peer_info['ip'] = str(attr['peerIp'])
                self.peer_info['mac'] = str(attr['peerMAC'])
                self.peer_info['state'] = str(attr['peerSt'])
                self.peer_info['st_qual'] = str(attr['peerStQual'])
                self.peer_info['version'] = str(attr['peerVersion'])
                self.attr['sys_mac'] = str(attr['sysMac'])
                self.attr['virtual_ip'] = str(attr['virtualIp'])
                self.attr['virtual_mac'] = str(attr['vpcMAC'])

    @staticmethod
    def get_table(vpcs, title=''):
        """
        Will create table of switch VPC information
        :param title:
        :param vpcs:
        """
        result = []
        for vpc in vpcs:
            if vpc.attr['admin_st'] == 'enabled' and vpc.attr['dom_present']:
                headers = ['Name',
                           'ID',
                           'Virtual MAC',
                           'Virtual IP',
                           'Admin State',
                           'Oper State',
                           'Domain Oper State',

                           'Role',
                           'Peer Version',
                           'Peer MAC',
                           'Peer IP',
                           'Peer State',
                           'Peer State Qualifier',

                           'Compatibility State',
                           'Compatibility String',
                           'Dual Active State',
                           'Local MAC',
                           'System MAC']

                data = [[vpc.attr.get('name', ''),
                         vpc.attr.get('id', ''),
                         vpc.attr.get('virtual_mac', ''),
                         vpc.attr.get('virtual_ip', ''),
                         vpc.attr.get('admin_st', ''),
                         vpc.attr.get('oper_st', ''),
                         vpc.attr.get('dom_oper_st', ''),
                         vpc.attr.get('role', ''),
                         vpc.peer_info.get('version', ''),
                         vpc.peer_info.get('mac', ''),
                         vpc.peer_info.get('ip', ''),
                         vpc.peer_info.get('state', ''),
                         vpc.peer_info.get('st_qual', ''),
                         vpc.attr.get('compat_st', ''),
                         vpc.attr.get('compat_str', ''),
                         vpc.attr.get('dual_active_st', ''),
                         vpc.attr.get('local_mac', ''),
                         vpc.attr.get('sys_mac', '')]]

                table = Table(data, headers, title=title + 'Virtual Port Channel (VPC)',
                              table_orientation='vertical', columns=2)
                result.append(table)
            else:
                headers = ['Admin State', 'Oper State']
                data = [[vpc.attr.get('admin_st', ''), vpc.attr.get('oper_st', '')]]

                table = Table(data, headers, title=title + 'Virtual Port Channel (VPC)')
                result.append(table)
        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        """
        result = [Searchable('vpc')]
        if 'name' in self.attr:
            result.append(Searchable('name', self.attr['name']))

        if 'virtual_mac' in self.attr:
            result.append(Searchable('mac', self.attr['virtual_mac']))

        if 'local_mac' in self.attr:
            result.append(Searchable('mac', self.attr['local_mac']))

        if 'sys_mac' in self.attr:
            result.append(Searchable('mac', self.attr['sys_mac']))

        if 'id' in self.attr:
            result.append(Searchable('id', self.attr['id']))

        if 'role' in self.attr:
            result.append(Searchable('role', self.attr['role']))

        if 'mac' in self.peer_info:
            result.append(Searchable('mac', self.peer_info['mac'], 'indirect'))

        if 'ip' in self.peer_info:
            result.append(Searchable('ipv4', self.peer_info['ip'].split('/')[0], 'indirect'))

        if 'virtual_ip' in self.attr:
            result.append(Searchable('ipv4', self.attr['virtual_ip'].split('/')[0]))

        return result

    def __str__(self):
        return 'VPC_' + self.attr['id']

    def __eq__(self, other):

        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteVpcIf(BaseACIPhysObject):
    """
    Class to hold a VPC interface
    """

    def __init__(self, parent=None):
        super(ConcreteVpcIf, self).__init__(parent=parent)
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ConcreteVpc

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['vpcIf', 'vpcRsVpcConf']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get the port members of the VPC.  Each
        port member will be a port-channel instance.
        :param parent:
        :param top:
        """
        cls.check_parent(parent)

        result = []
        vpc_members = top.get_class('vpcIf')
        for vpc_member in vpc_members:
            if 'vpcIf' in vpc_member:
                member = cls()
                member._populate_from_attributes(vpc_member['vpcIf']['attributes'])
                member._get_interface(top, vpc_member['vpcIf']['attributes']['dn'])
                result.append(member)
                if parent:
                    member._parent = parent
                    member._parent.add_child(member)
        return result

    def _populate_from_attributes(self, attr):
        """
        Populate attribute
        """
        self.attr['compat_st'] = str(attr['compatSt'])
        self.attr['id'] = str(attr['id'])
        self.attr['remote_oper_st'] = str(attr['remoteOperSt'])

        if attr['cfgdAccessVlan']:
            if 'vlan-' in attr['cfgdAccessVlan']:
                self.attr['access_vlan'] = str(attr['cfgdAccessVlan']).split('-')[1]
            else:
                self.attr['access_vlan'] = str(attr['cfgdAccessVlan'])

        self.attr['trunk_vlans'] = str(attr['cfgdTrunkVlans'])
        self.attr['vlans'] = str(attr['cfgdVlans'])
        self.attr['compat_qual'] = str(attr['compatQual'])
        self.attr['compat_qual_str'] = str(attr['compatQualStr'])
        self.attr['compat_st'] = str(attr['compatSt'])
        self.attr['oper_st'] = str(attr['localOperSt'])
        self.attr['remote_vlans'] = str(attr['peerCfgdVlans'])
        self.attr['remote_up_vlans'] = str(attr['peerUpVlans'])
        self.attr['remote_oper_st'] = str(attr['remoteOperSt'])
        self.attr['susp_vlans'] = str(attr['suspVlans'])
        self.attr['up_vlans'] = str(attr['upVlans'])
        self.attr['dn'] = str(attr['dn'])

    def _get_interface(self, top, dname):
        """
        Retrieves the VPC interface
        """
        vpc_data = top.get_object(dname + '/rsvpcConf')
        if vpc_data:
            self.attr['interface'] = str(vpc_data['vpcRsVpcConf']['attributes']['tSKey'])

    @staticmethod
    def get_table(vpc_ifs, title=''):
        """
        Will generate a text report for a list of vpc_ifs.
        :param title:
        :param vpc_ifs:
        """

        result = []

        headers = ['ID', 'Interface', 'Oper St', 'Remote Oper State',
                   'Access VLAN', 'Up VLANS', 'Remote Up VLANs', 'Suspended VLANs']
        data = []
        for intf in vpc_ifs:
            data.append([
                intf.attr.get('id', ''),
                intf.attr.get('interface', ''),
                intf.attr.get('oper_st', ''),
                intf.attr.get('remote_oper_st', ''),
                intf.attr.get('access_vlan', ''),
                intf.attr.get('up_vlans', ''),
                intf.attr.get('remote_up_vlans', ''),
                intf.attr.get('susp_vlans', '')])

        data = sorted(data)
        result.append(Table(data, headers, title=title + 'VPC Interfaces'))
        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'id' in self.attr:
            result.append(Searchable('id', self.attr['id']))

        if 'interface' in self.attr:
            result.append(Searchable('interface', self.attr['interface']))

        if 'up_vlans' in self.attr:
            vlan_list = self.expand_vlans(self.attr['up_vlans'].replace(' ', ''))
            for vlan in vlan_list:
                result.append(Searchable('vlan', str(vlan)))
        if 'remote_up_vlans' in self.attr:
            vlan_list = self.expand_vlans(self.attr['remote_up_vlans'].replace(' ', ''))
            for vlan in vlan_list:
                result.append(Searchable('vlan', str(vlan), 'indirect'))

        if 'access_vlan' in self.attr:
            result.append(Searchable('vlan', self.attr['access_vlan']))

        if 'susp_vlans' in self.attr:
            vlan_list = self.expand_vlans(self.attr['susp_vlans'].replace(' ', ''))
            for vlan in vlan_list:
                result.append(Searchable('vlan', str(vlan)))

        return result

    @staticmethod
    def expand_vlans(vlans):
        """
        Will expand a comma separated list of vlan ids into a list of discrete vlan ids
        :rtype : list
        :param vlans: str of comma separated vlan lists
        """
        vlan_ranges = vlans.split(',')
        vlan_list = []
        for v_range in vlan_ranges:
            if '-' in v_range:
                [v_low, v_hi] = v_range.split('-')
                vlan_list.extend(range(int(v_low), int(v_hi) + 1))
            else:
                vlan_list.append(v_range)
        return vlan_list

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'VPC_Interface' + self.attr.get('id')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteContext(BaseACIPhysObject):
    """
    The l3-context on a switch.  This is derived from
    the concrete model
    """

    def __init__(self, parent=None):
        """
        l3-context on a switch
        """
        super(ConcreteContext, self).__init__(parent=parent)
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['l3Ctx', 'l3Inst']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all of the switch contexts on the
        specified node.  If no node is specified, then
        it will get all of the switch contexts on all
        of the switches.

        :param parent:
       :param top: the topSystem level json object
       :returns: list of Switch context
        """
        cls.check_parent(parent)

        result = []
        ctx_data = top.get_class('l3Ctx')[:]
        ctx_data.extend(top.get_class('l3Inst')[:])
        for ctx in ctx_data:
            context = cls()
            if 'l3Ctx' in ctx:
                context._populate_from_attributes(ctx['l3Ctx']['attributes'])
            else:
                context._populate_from_attributes(ctx['l3Inst']['attributes'])
            result.append(context)
            if parent:
                context._parent = parent
                context._parent.add_child(context)

        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the context object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['dn'] = str(attr['dn'])
        self.attr['oper_st'] = str(attr['operState'])
        self.attr['create_time'] = str(attr['createTs'])
        self.attr['admin_st'] = str(attr['adminState'])
        self.attr['oper_st_qual'] = str(attr['operStQual'])
        self.attr['encap'] = str(attr['encap'])
        self.attr['modified_time'] = str(attr['lastChgdTs'])
        self.attr['name'] = str(attr['name'])
        if ':' in self.attr['name']:
            self.attr['tenant'] = self.attr['name'].split(':')[0]
            self.attr['context'] = self.attr['name'].split(':')[1]
        else:
            self.attr['tenant'] = ''
            self.attr['context'] = self.attr['name']

        if 'pcTag' in attr:
            self.attr['mcst_class_id'] = str(attr['pcTag'])
        else:
            self.attr['mcst_class_id'] = ''

        self.attr['scope'] = str(attr['scope'])
        self.attr['type'] = str(attr.get('type'))
        self.attr['vrf_id'] = str(attr['id'])
        self.attr['vrf_oui'] = str(attr['oui'])
        self.attr['mgmt_class_id'] = str(attr.get('mgmtPcTag'))
        if 'vxlan-' in self.attr['encap']:
            self.attr['vnid'] = self.attr['encap'].split('-')[1]
        else:
            self.attr['vnid'] = ''

    @staticmethod
    def get_table(contexts, title=''):
        """
        Will create table of switch context information
        :param title:
        :param contexts:
        """

        headers = ['Tenant', 'Context', 'VNID', 'Scope', 'Type', 'VRF Id',
                   'MCast Class Id', 'Admin St', 'Oper St', 'Modified']
        data = []
        for context in sorted(contexts, key=lambda x: (x.attr['tenant'], x.attr['context'])):
            data.append([
                context.attr.get('tenant', ''),
                context.attr.get('context', ''),
                context.attr.get('vnid', ''),
                context.attr.get('scope', ''),
                context.attr.get('type', ''),
                context.attr.get('vrf_id', ''),
                context.attr.get('mcst_class_id', ''),
                context.attr.get('admin_st', ''),
                context.attr.get('oper_st', ''),
                context.attr.get('modified_time', '')])

        data = sorted(data)
        table = Table(data, headers, title=title + 'Contexts (VRFs)')
        return [table, ]

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'name' in self.attr:
            result.append(Searchable('name', self.attr['name']))
            result.append(Searchable('context', self.attr['name']))

        if 'vnid' in self.attr:
            result.append(Searchable('vnid', self.attr['vnid']))

        if 'scope' in self.attr:
            result.append(Searchable('scope', self.attr['scope']))

        if 'mcst_class_id' in self.attr:
            result.append(Searchable('class', self.attr['mcst_class_id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Context' + self.attr.get('name')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteSVI(BaseACIPhysObject):
    """
    The SVIs on a switch.  This is derived from
    the concrete model in the switch
    """

    def __init__(self, parent=None):
        """
        SVI on a switch
        """
        super(ConcreteSVI, self).__init__(parent=parent)
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['sviIf']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all the SVIs on the switch

        :param parent:
        :param top:  json record of entire switch config
        :returns: list of SVI
        """
        cls.check_parent(parent)
        result = []

        svi_data = top.get_class('sviIf')
        for svi_obj in svi_data:
            svi = cls()
            if 'sviIf' in svi_obj:
                svi._populate_from_attributes(svi_obj['sviIf']['attributes'])

            result.append(svi)
            if parent:
                svi._parent = parent
                svi._parent.add_child(svi)

        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the context object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['bandwidth'] = str(attr['bw'])
        self.attr['admin_st'] = str(attr['adminSt'])
        self.attr['oper_st_qual'] = str(attr['operStQual'])
        self.attr['oper_st'] = str(attr['operSt'])
        self.attr['modified_time'] = str(attr['modTs'])
        self.attr['name'] = str(attr['name'])
        self.attr['mac'] = str(attr['mac'])
        self.attr['id'] = str(attr['id'])
        self.attr['vlan_id'] = str(attr['vlanId'])
        self.attr['vlan_type'] = str(attr['vlanT'])
        self.attr['dn'] = str(attr['dn'])

    @staticmethod
    def get_table(aci_objects, title=''):
        """
        Create table object for concrete SVI
        :param aci_objects:
        :param title:
        """
        result = []

        headers = ['Name', 'ID', 'VLAN', 'Router MAC', 'Bandwidth', 'Admin State', 'Oper State', 'Oper Qualifier']
        data = []
        for aci_object in aci_objects:
            data.append([
                aci_object.attr.get('name', ''),
                aci_object.attr.get('id', ''),
                aci_object.attr.get('vlan_id', ''),
                aci_object.attr.get('mac', ''),
                aci_object.attr.get('bw', ''),
                aci_object.attr.get('admin_st', ''),
                aci_object.attr.get('oper_st', ''),
                aci_object.attr.get('oper_st_qual', '')
            ])

        data = sorted(data, key=lambda x: (x[0], x[1]))
        result.append(Table(data, headers, title=title + 'SVI (Router Interfaces)'))
        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = [(Searchable('svi'))]

        if 'name' in self.attr:
            result.append(Searchable('name', self.attr['name']))

        if 'mac' in self.attr:
            result.append(Searchable('mac', self.attr['mac']))

        if 'id' in self.attr:
            result.append(Searchable('id', self.attr['id']))

        if 'vlan_id' in self.attr:
            result.append(Searchable('vlan', self.attr['vlan_id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_SVI' + self.attr.get('name')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteLoopback(BaseACIPhysObject):
    """
    Loopback interfaces on the switch
    """

    def __init__(self, parent=None):
        """
        SVI on a switch
        """
        super(ConcreteLoopback, self).__init__(parent=parent)
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['l3LbRtdIf', 'ethpmLbRtdIf']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all the loopback interfaces on the switch

        :param parent:
       :param top: the topSystem level json object
       :returns: list of loopback
        """
        cls.check_parent(parent)

        result = []

        data = top.get_class('l3LbRtdIf')
        for obj in data:
            lbif = cls()
            if 'l3LbRtdIf' in obj:
                lbif._populate_from_attributes(obj['l3LbRtdIf']['attributes'])
                lbif._get_oper_st(obj['l3LbRtdIf']['attributes']['dn'], top)
            result.append(lbif)
            if parent:
                lbif._parent = parent
                lbif._parent.add_child(lbif)
        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['descr'] = str(attr['descr'])
        self.attr['admin_st'] = str(attr['adminSt'])
        self.attr['id'] = str(attr['id'])
        self.attr['dn'] = str(attr['dn'])

    def _get_oper_st(self, dname, top):
        """
        Gets the operational state
        """
        data = top.get_subtree('ethpmLbRtdIf', dname)
        self.attr['oper_st'] = ''
        self.attr['oper_st_qual'] = ''
        for obj in data:
            self.attr['oper_st'] = str(obj['ethpmLbRtdIf']['attributes']['operSt'])
            self.attr['oper_st_qual'] = str(obj['ethpmLbRtdIf']['attributes']['operStQual'])

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'id' in self.attr:
            result.append(Searchable('id', self.attr['id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Loopback' + self.attr.get('id')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteBD(BaseACIPhysObject):
    """
    The bridge domain on a switch.  This is derived from
    the concrete model
    """

    def __init__(self, parent=None):
        """
        bridge domain on a switch
        """
        super(ConcreteBD, self).__init__(parent=parent)
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['l2BD', 'l3Ctx', 'l3Inst', 'fmcastGrp']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all of the switch bd on the
        specified node.  If no node is specified, then
        it will get all of the bds on all
        of the switches.

        :param parent:
       :param top: the topSystem level json object
       :returns: list of Switch bridge domain
        """
        cls.check_parent(parent)

        result = []
        bd_data = top.get_class('l2BD')
        for l2bd in bd_data:
            bdomain = cls()
            bdomain._populate_from_attributes(l2bd['l2BD']['attributes'])

            # get the context name by reading the context
            bdomain._get_cxt_name(top)
            bdomain._get_multicast_flood_address(top)
            result.append(bdomain)
            if parent:
                bdomain._parent = parent
                bdomain._parent.add_child(bdomain)

        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the bridge domain object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['dn'] = str(attr['dn'])
        self.attr['oper_st'] = str(attr['operSt'])
        self.attr['create_time'] = str(attr['createTs'])
        self.attr['admin_st'] = str(attr['adminSt'])

        self.attr['access_encap'] = str(attr['accEncap'])
        self.attr['bridge_mode'] = str(attr['bridgeMode'])
        self.attr['modified_time'] = str(attr['modTs'])
        self.attr['name'] = str(attr['name'])
        self.attr['unknown_ucast_class_id'] = str(attr['pcTag'])
        self.attr['fabric_encap'] = str(attr['fabEncap'])
        if 'vxlan-' in self.attr['fabric_encap']:
            self.attr['vnid'] = self.attr['fabric_encap'].split('-')[1]
        else:
            self.attr['vnid'] = ''

        if not self.attr['name']:
            self.attr['name'] = self.attr['vnid']

        self.attr['type'] = str(attr['type'])
        if 'arp-flood' in attr['fwdCtrl']:
            self.attr['arp_flood'] = True
        else:
            self.attr['arp_flood'] = False

        if 'mdst-flood' in attr['fwdCtrl']:
            self.attr['mcst_flood'] = True
        else:
            self.attr['mcst_flood'] = False

        if 'bridge' in attr['fwdMode']:
            self.attr['bridge'] = True
        else:
            self.attr['bridge'] = False

        if 'route' in attr['fwdMode']:
            self.attr['route'] = True
        else:
            self.attr['route'] = False

        self.attr['learn_disable'] = str(attr['epOperSt'])
        self.attr['unknown_mac_ucast'] = str(attr['unkMacUcastAct'])
        self.attr['unknown_mcast'] = str(attr['unkMcastAct'])

    def _get_cxt_name(self, top):
        """
        Gets the context name by reading the context object
        """
        fields = self.attr['dn'].split('/')
        context_dn = '/'.join(fields[0:-1])
        bd_data = top.get_object(context_dn)
        name = ''
        if 'l3Ctx' in bd_data:
            name = str(bd_data['l3Ctx']['attributes']['name'])
        elif 'l3Inst' in bd_data:
            name = str(bd_data['l3Inst']['attributes']['name'])

        if ':' in name:
            self.attr['tenant'] = name.split(':')[0]
            self.attr['context'] = name.split(':')[1]
        else:
            self.attr['tenant'] = ''
            self.attr['context'] = name

    def _get_multicast_flood_address(self, top):
        """
        Will read the fmcastGrp to get the multicast addre
        used when flooding across the fabric.
        """
        bd_data = top.get_subtree('fmcastGrp', self.attr['dn'])
        for obj in bd_data:
            if 'fmcastGrp' in obj:
                self.attr['flood_gipo'] = str(obj['fmcastGrp']['attributes']['addr'])
                break
            else:
                self.attr['flood_gipo'] = ''

    @staticmethod
    def get_table(bridge_domains, title=''):
        """
        Will create table of switch bridge domain information
        :param title:
        :param bridge_domains:
        """
        result = []

        headers = ['Tenant', 'Context', 'Name', 'VNID', 'Mode',
                   'Route', 'Type', 'ARP Flood', 'MCST Flood',
                   'Unk UCAST', 'Unk MCAST', 'Learn', 'Flood GIPo',
                   'Admin St', 'Oper St']
        data = []
        for bdomain in bridge_domains:
            if ':' in bdomain.attr['name']:
                name = bdomain.attr['name'].split(':')[-1]
            else:
                name = str(bdomain.attr.get('name', ''))

            data.append([
                bdomain.attr.get('tenant', ''),
                bdomain.attr.get('context', ''),
                name,
                str(bdomain.attr.get('vnid', '')),
                str(bdomain.attr.get('bridge_mode', '')),
                str(bdomain.attr.get('route', '')),
                str(bdomain.attr.get('type', '')),
                str(bdomain.attr.get('arp_flood', '')),
                str(bdomain.attr.get('mcst_flood', '')),
                str(bdomain.attr.get('unknown_mac_ucast', '')),
                str(bdomain.attr.get('unknown_mcast', '')),
                str(bdomain.attr.get('learn_disable', '')),
                str(bdomain.attr.get('flood_gipo', '')),
                str(bdomain.attr.get('admin_st', '')),
                str(bdomain.attr.get('oper_st', ''))])

        data = sorted(data)
        result.append(Table(data, headers, title=title + 'Bridge Domains (BDs)'))
        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if ':' in self.attr['name']:
            result.append(Searchable('name', self.attr['name'].split(':')[-1]))
        else:
            result.append(Searchable('name', self.attr['name']))

        if 'context_name' in self.attr:
            if ':' in self.attr['context_name']:
                tenant = self.attr['context_name'].split(':')[0]
                context = self.attr['context_name'].split(':')[1]
                result.append(Searchable('context', context))
                result.append(Searchable('tenant', tenant))
            else:
                result.append(Searchable('context', self.attr['context_name']))

        if 'vnid' in self.attr:
            result.append(Searchable('vnid', self.attr['vnid']))
        if 'flood_gipo' in self.attr:
            result.append(Searchable('ipv4', self.attr['flood_gipo']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_BD' + self.attr.get('name')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteAccCtrlRule(BaseACIPhysObject):
    """
    Access control rules on a switch
    """

    def __init__(self, parent=None):
        """
        access control rules on a switch
        """
        super(ConcreteAccCtrlRule, self).__init__(parent=parent)
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['actrlRule']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all of the access rules on the
        specified node.  If no node is specified, then
        it will get all of the access rules on all
        of the switches.

        :param parent:
        :param top: the topSystem level json object
        :returns: list of Switch bridge domain
        """
        cls.check_parent(parent)

        result = []

        rule_data = top.get_class('actrlRule')
        epgs = ACI.EPG.get(top.session)
        contexts = ACI.Context.get(top.session)

        for actrl_rule in rule_data:
            rule = cls()
            rule._populate_from_attributes(actrl_rule['actrlRule']['attributes'])
            # get the context name by reading the context
            rule._get_tenant_context(contexts)
            rule._get_epg_names(epgs)
            rule._get_pod_node()
            result.append(rule)
            if parent:
                rule._parent = parent
                rule._parent.add_child(rule)
        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['action'] = str(attr['action'])
        self.attr['dclass'] = str(attr['dPcTag'])
        self.attr['sclass'] = str(attr['sPcTag'])
        self.attr['descr'] = str(attr['descr'])
        self.attr['direction'] = str(attr['direction'])
        self.attr['filter_id'] = str(attr['fltId'])
        self.attr['mark_dscp'] = str(attr['markDscp'])
        self.attr['name'] = str(attr['name'])
        self.attr['oper_st'] = str(attr['operSt'])
        self.attr['priority'] = str(attr['prio'])
        self.annotate_priority()
        self.attr['qos_group'] = str(attr['qosGrp'])
        self.attr['scope'] = str(attr['scopeId'])
        self.attr['type'] = str(attr['type'])
        self.attr['status'] = str(attr['status'])
        self.attr['modified_time'] = str(attr['modTs'])
        self.attr['dn'] = str(attr['dn'])

    def annotate_priority(self):
        """
        Annotate the priority string with a number that indicates its relative priority
        :return:None
        """
        prio_map = {'black_list': 1,
                    'fabric_infra': 2,
                    'fully_qual': 3,
                    'system_incomplete': 4,
                    'src_dst_any': 5,
                    'src_any_filter': 6,
                    'any_dest_filter': 7,
                    'src_any_any': 8,
                    'any_dest_any': 9,
                    'any_any_filter': 10,
                    'any_any_any': 12}
        self.attr['relative_priority'] = prio_map.get(self.attr['priority'], 'unknown')

    def _get_tenant_context(self, contexts):
        """
        This will map from scope to tenant name
        and context
        """
        # contexts = ACI.Context.get(session)
        for context in contexts:
            if self.attr['scope'] == context.scope:
                self.attr['context'] = context.name
                self.attr['tenant'] = context.tenant
                return
        self.attr['context'] = ''
        self.attr['tenant'] = ''

    def _get_epg_names(self, epgs):
        """
        This will derive source and destination EPG
        names from dclass and sclass - if possible

        """
        self.attr['s_epg'] = ''
        self.attr['d_epg'] = ''
        if self.attr['dclass'] == 'any':
            self.attr['d_epg'] = 'any'
        if self.attr['sclass'] == 'any':
            self.attr['s_epg'] = 'any'

        # if no lookup needed then return
        if self.attr['sclass'] == 'any' and self.attr['dclass'] == 'any':
            return

        # get all the EPG
        # epgs = ACI.EPG.get(session)
        for epg in epgs:
            if epg.class_id == self.attr['dclass']:
                self.attr['d_epg'] = epg.name
            if epg.class_id == self.attr['sclass']:
                self.attr['s_epg'] = epg.name

    def _get_pod_node(self):
        """
        This will populate pod and node ID from the
        dn.
        """
        name = self.attr['dn'].split('/')
        self.attr['pod'] = str(name[1].split('-')[1])
        self.attr['node'] = str(name[2].split('-')[1])

    @staticmethod
    def get_table(data, title=''):
        """
        Will create table of access rule
        :param title:
        :param data:
        """
        result = []

        headers = ['Tenant', 'Context', 'Type', 'Scope', 'Src EPG',
                   'Dst EPG', 'Filter', 'Action', 'DSCP', 'QoS', 'Priority', 'Relative Prio']
        table = []
        for rule in data:
            table.append([
                rule.attr.get('tenant', ''),
                rule.attr.get('context', ''),
                rule.attr.get('type', ''),
                rule.attr.get('scope', ''),
                rule.attr.get('s_epg', ''),
                rule.attr.get('d_epg', ''),
                rule.attr.get('filter_id', ''),
                rule.attr.get('action', ''),
                rule.attr.get('mark_dscp', ''),
                rule.attr.get('qos_grp', ''),
                rule.attr.get('priority', ''),
                rule.attr.get('relative_priority', '')])

        table = sorted(table, key=lambda x: (x[11], x[0], x[1]))
        result.append(Table(table, headers, title=title + 'Access Rules (Contracts/Access Policies)'))

        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'tenant' in self.attr:
            result.append(Searchable('tenant', self.attr['tenant']))

        if 'context' in self.attr:
            result.append(Searchable('context', self.attr['context']))

        if 'scope' in self.attr:
            result.append(Searchable('scope', self.attr['scope']))

        if 's_epg' in self.attr:
            result.append(Searchable('epg', self.attr['s_epg']))

        if 'd_epg' in self.attr:
            result.append(Searchable('epg', self.attr['d_epg']))

        if 'dclass' in self.attr:
            result.append(Searchable('class', self.attr['dclass']))

        if 'sclass' in self.attr:
            result.append(Searchable('class', self.attr['sclass']))

        if 'scope' in self.attr:
            result.append(Searchable('scope', self.attr['scope']))

        if 'name' in self.attr:
            result.append(Searchable('name', self.attr['name']))

        if 'filter_id' in self.attr:
            result.append(Searchable('filter', self.attr['filter_id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Access_Rule' + self.attr.get('name')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteFilter(BaseACIPhysObject):
    """
    Access control filters on a switch
    """

    def __init__(self, parent=None):
        """
        access control filters on a switch
        """
        super(ConcreteFilter, self).__init__(parent=parent)
        self.entries = []
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['actrlFlt']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all of the access filters on the
        specified node.  If no node is specified, then
        it will get all of the access rules on all
        of the switches.

        :param parent:
        :param top: the topSystem level json object
        :returns: list of Switch bridge domain
        """
        cls.check_parent(parent)

        result = []
        filter_data = top.get_class('actrlFlt')

        for filter_object in filter_data:
            acc_filter = cls()
            acc_filter._populate_from_attributes(filter_object['actrlFlt']['attributes'])
            # get the context name by reading the context
            acc_filter._get_entries(top)
            acc_filter._get_pod_node()
            result.append(acc_filter)
            if parent:
                acc_filter._parent = parent
                acc_filter._parent.add_child(acc_filter)
        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['name'] = str(attr['name'])
        self.attr['id'] = str(attr['id'])
        self.attr['descr'] = str(attr['descr'])
        self.attr['status'] = str(attr['status'])
        self.attr['modified_time'] = str(attr['modTs'])
        self.attr['dn'] = str(attr['dn'])

    def _get_entries(self, top):
        """
        This will get all of the entries of the filter
        """

        self.entries = ConcreteFilterEntry.get(top, self)

    def _get_pod_node(self):
        """
        This will populate pod and node ID from the
        dn.
        """
        name = self.attr['dn'].split('/')
        self.attr['pod'] = name[1].split('-')[1]
        self.attr['node'] = name[2].split('-')[1]

    @staticmethod
    def get_table(data, title=''):
        """
        Will create table of access filter
        :param title:
        :param data:
        """
        result = []

        headers = ['Filter', 'Entry #', 'EtherType',
                   'Protocol/Arp Opcode', 'L4 DPort', 'L4 SPort', 'TCP Flags', 'Apply to Frag', 'Priority']

        table = []
        for acc_filter in sorted(data, key=lambda x: (x.attr['id'])):
            sorted_entries = sorted(acc_filter.entries,
                                    key=lambda x: (x.attr['filter_name'], x.attr['relative_priority'], x.attr['id']))
            for sorted_entry in sorted_entries:
                dst_port = ConcreteFilter._get_port(sorted_entry.attr['dst_from_port'],
                                                    sorted_entry.attr['dst_to_port'])
                src_port = ConcreteFilter._get_port(sorted_entry.attr['src_from_port'],
                                                    sorted_entry.attr['src_to_port'])
                table.append([sorted_entry.attr.get('filter_name', ''),
                              sorted_entry.attr.get('id', ''),
                              sorted_entry.attr.get('ether_type', ''),
                              sorted_entry.attr.get('protocol', ''),
                              dst_port,
                              src_port,
                              sorted_entry.attr.get('tcp_rules', ''),
                              sorted_entry.attr.get('apply_to_frag', ''),
                              sorted_entry.attr.get('relative_priority', '')])
        result.append(Table(table, headers, title=title + 'Access Filters'))
        return result

    @staticmethod
    def _get_port(from_port, to_port):
        """
        will build a string that is a port range or a port number
        depending upon the from_port and to_port value
        """
        if from_port == to_port:
            return str(from_port)
        return '{0}-{1}'.format(str(from_port), str(to_port))

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'name' in self.attr:
            result.append(Searchable('name', self.attr['name']))

        if 'id' in self.attr:
            result.append(Searchable('id', self.attr['id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Filter' + self.attr.get('id')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteFilterEntry(BaseACIPhysObject):
    """
    Access control entries of a filter
    """

    def __init__(self, parent=None):
        """
        access control filters of a filter
        """
        super(ConcreteFilterEntry, self).__init__(parent=parent)
        self.attr = {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ConcreteFilter

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['actrlEntry']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all of the access filter entries of the
        specified filter.  If no filter is specified, then
        it will get all of the access rules on all
        of the switches.

        :param parent:
        :param top: the topSystem level json object
        :returns: list of Switch bridge domain
        """
        cls.check_parent(parent)
        result = []
        entry_data = top.get_subtree('actrlEntry', parent.attr['dn'])

        for entry_object in entry_data:
            acc_entry = cls()
            acc_entry._populate_from_attributes(entry_object['actrlEntry']['attributes'])
            # get the context name by reading the context
            acc_entry._get_filter_name()
            acc_entry._get_entry_id()
            result.append(acc_entry)
            if parent:
                acc_entry._parent = parent
                acc_entry._parent.add_child(acc_entry)
        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['apply_to_frag'] = str(attr['applyToFrag'])
        self.attr['arp_opcode'] = str(attr['arpOpc'])
        self.attr['dst_from_port'] = str(attr['dFromPort'])
        self.attr['dst_to_port'] = str(attr['dToPort'])
        self.attr['descr'] = str(attr['descr'])
        self.attr['dn'] = str(attr['dn'])
        self.attr['ether_type'] = str(attr['etherT'])
        self.attr['modified_time'] = str(attr['modTs'])
        self.attr['name'] = str(attr['name'])
        self.attr['priority'] = str(attr['prio'])
        self.annotate_priority()
        self.attr['protocol'] = str(attr['prot'])
        self.attr['src_from_port'] = str(attr['sFromPort'])
        self.attr['src_to_port'] = str(attr['sToPort'])
        self.attr['status'] = str(attr['status'])
        self.attr['tcp_rules'] = str(attr['tcpRules'])

    def annotate_priority(self):
        """
        Will create a relative priority field from the priority field
        :return:None
        """
        prio_map = {'flags': 1,
                    'sport_dport': 2,
                    'dport': 3,
                    'sport': 4,
                    'proto': 5,
                    'frag': 6,
                    'def': 7}
        if self.attr['priority'] in prio_map:
            self.attr['relative_priority'] = prio_map[self.attr['priority']]
        else:
            self.attr['relative_priority'] = 'unknown'

    def _get_filter_name(self):
        """
        Will get the name of the filter from the dn
        """
        self.attr['filter_name'] = self.attr['dn'].split('/filt-')[1].split('/')[0]

    def _get_entry_id(self):
        """
        Will create an entry ID from the entry name
        """
        self.attr['id'] = self.attr['name'].split('_')[-1]

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'name' in self.attr:
            result.append(Searchable('name', self.attr['name']))

        if 'filter_name' in self.attr:
            result.append(Searchable('name', self.attr['filter_name']))

        if 'id' in self.attr:
            result.append(Searchable('id', self.attr['id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Filter_Entry' + self.attr.get('id')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteEp(BaseACIPhysObject):
    """
    Endpoint on the switch
    """

    def __init__(self, parent=None):
        """
        endpoints on a switch
        """
        super(ConcreteEp, self).__init__(parent=parent)
        self.attr = {'ip': None, 'mac': None}

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['epmIpEp', 'epmMacEp', 'epmRsMacEpToIpEpAtt']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all of the endpoints known to the switch
        If the parent is provided, this object will be added as a child
        to the parent.

        :param parent: Parent switch object
        :param top: the topSystem level json object
        :returns: list of endpoint
        """
        cls.check_parent(parent)

        result = []

        ep_data = top.get_class('epmIpEp')[:]
        ep_data.extend(top.get_class('epmMacEp')[:])

        for ep_object in ep_data:
            end_point = cls()
            if 'epmIpEp' in ep_object:
                end_point._populate_from_attributes(ep_object['epmIpEp']['attributes'])
                end_point.attr['address_family'] = 'ipv4'
                end_point.attr['ip'] = str(ep_object['epmIpEp']['attributes']['addr'])
            if 'epmMacEp' in ep_object:
                end_point._populate_from_attributes(ep_object['epmMacEp']['attributes'])
                end_point.attr['address_family'] = 'mac'
                end_point.attr['mac'] = str(ep_object['epmMacEp']['attributes']['addr'])

            end_point._get_context_bd(top)
            result.append(end_point)

        # all the EP info has been gathered - now clean up
        rem_ep = []
        new_ep_list = []
        for end_point in result:
            if end_point.attr['address_family'] == 'mac':
                rel_data = top.get_subtree('epmRsMacEpToIpEpAtt', end_point.attr['dn'])
                for rel in rel_data:
                    ip_add = str(rel['epmRsMacEpToIpEpAtt']['attributes']['tDn'].
                                 split('/ip-[')[1].split(']')[0])
                    if 'ctx-[vxlan-' in rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']:

                        ip_ctx = str(rel['epmRsMacEpToIpEpAtt']['attributes']['tDn'].
                                     split('/ctx-[vxlan-')[1].split(']/')[0])
                    elif '/inst-' in rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']:
                        ip_ctx = str(rel['epmRsMacEpToIpEpAtt']['attributes']['tDn'].
                                     split('/inst-')[1].split('/')[0])
                        if ip_ctx in top.ctx_dict:
                            ip_ctx = top.ctx_dict[ip_ctx]
                    else:
                        ip_ctx = None
                    ip_bd = str(rel['epmRsMacEpToIpEpAtt']['attributes']['tDn'].
                                split('/bd-[vxlan-')[1].split(']/')[0])
                    if ip_ctx == end_point.attr['ctx_vnid'] and ip_bd == \
                            end_point.attr['bd_vnid']:
                        # we have an IP address for this MAC
                        if end_point.attr['ip']:
                            # one already exists, must be new one
                            new_ep = copy.deepcopy(end_point)
                            new_ep.attr['ip'] = ip_add
                            new_ep_list.append(new_ep)
                        else:
                            end_point.attr['ip'] = ip_add
                        rem_ep.append((ip_add, ip_ctx, ip_bd))
                    else:
                        print ('unexpected context or bd mismatch', ip_add, ip_ctx, ip_bd)
        result.extend(new_ep_list)
        final_result = []
        for ept in result:
            if (ept.attr['address'], ept.attr['ctx_vnid'], ept.attr['bd_vnid']) not in rem_ep:
                final_result.append(ept)

        # convert SVIs to more useful info
        svis = ConcreteSVI.get(top)
        svi_table = {}
        for svi in svis:
            svi_table[svi.attr['id']] = svi
        for ept in final_result:
            if 'vlan' in ept.attr['interface_id'] and ept.attr['mac'] is None:
                ept.attr['mac'] = svi_table[ept.attr['interface_id']].attr['mac']
                # noinspection PyAugmentAssignment
                ept.attr['interface_id'] = 'svi-' + ept.attr['interface_id']

        # mark loopback interfaces as loopback
        lbifs = ConcreteLoopback.get(top)
        lbif_table = {}
        for lbif in lbifs:
            lbif_table[lbif.attr['id']] = lbif
        for ep in final_result:
            # noinspection PyAugmentAssignment
            if ep.attr['interface_id'] in lbif_table:
                ep.attr['interface_id'] = 'loopback-' + ep.attr['interface_id']
            if parent:
                ep._parent = parent
                ep._parent.add_child(ep)

        return final_result

    def _get_context_bd(self, top):
        """ will extract the context and bridge domain
        from the dn
        """
        if '/ctx-[vxlan-' in self.attr['dn']:
            self.attr['ctx_vnid'] = self.attr['dn'].split('/ctx-[vxlan-')[1].split(']/')[0]
            ctx = top.vnid_dict.get(self.attr['ctx_vnid'])
            if ctx:
                self.attr['context'] = ctx['name']
            else:
                self.attr['context'] = self.attr['ctx_vnid']

        elif '/inst-' in self.attr['dn']:
            self.attr['ctx_vnid'] = 'unknown'
            self.attr['context'] = self.attr['dn'].split('/inst-')[1].split('/')[0]
            if self.attr['context'] in top.ctx_dict:
                self.attr['ctx_vnid'] = top.ctx_dict[self.attr['context']]
        else:
            self.attr['ctx_vnid'] = 'unknown'
            self.attr['context'] = 'unknown'

        if '/bd-[vxlan-' in self.attr['dn']:
            self.attr['bd_vnid'] = self.attr['dn'].split('/bd-[vxlan-')[1].split(']/')[0]
            bdomain = top.vnid_dict.get(self.attr['bd_vnid'])
            if bdomain:
                self.attr['bridge_domain'] = bdomain['name']
            else:
                self.attr['bridge_domain'] = self.attr['bd_vnid']
        else:
            self.attr['bd_vnid'] = 'unknown'
            self.attr['bridge_domain'] = 'unknown'

        # change context to tenant plus context

        if ':' in self.attr['context']:
            context = self.attr['context'].split(':')[1]
            tenant = self.attr['context'].split(':')[0]
            self.attr['context'] = context
            self.attr['tenant'] = tenant
        else:
            self.attr['tenant'] = ''
            # context already set

    def _populate_from_attributes(self, attr):
        """
        This will populate the object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['address'] = str(attr['addr'])
        self.attr['name'] = str(attr['name'])
        self.attr['flags'] = str(attr['flags'])
        self.attr['interface_id'] = str(attr['ifId'])
        self.attr['create_time'] = str(attr['createTs'])
        self.attr['dn'] = str(attr['dn'])

    @staticmethod
    def get_table(end_points, title=''):
        """
        Will create table of switch end point information
        :param title:
        :param end_points:
        """
        result = []
        headers = ['Tenant', 'Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                   'Interface', 'Flags']

        def flt_local_external(end_point):
            """

            :param end_point:
            :return:
            """
            if 'loopback' not in str(end_point.attr.get('interface_id')):
                if 'svi' not in str(end_point.attr.get('interface_id')):
                    if 'local' in str(end_point.attr.get('flags')):
                        return True
            return False

        data = []
        for ept in filter(flt_local_external, sorted(end_points, key=lambda x: (x.attr['tenant'],
                                                                                x.attr['context'],
                                                                                x.attr['bridge_domain'],
                                                                                x.attr['mac'],
                                                                                x.attr['ip']))):
            data.append([
                ept.attr.get('tenant', ''),
                ept.attr.get('context', ''),
                ept.attr.get('bridge_domain', ''),
                ept.attr.get('mac', ''),
                ept.attr.get('ip', ''),
                ept.attr.get('interface_id', ''),
                ept.attr.get('flags', '')])

        result.append(Table(data, headers, title=title + 'Local External End Points'))

        def flt_remote(end_point):
            """

            :param end_point:
            :return:
            """
            if 'loopback' not in str(end_point.attr.get('interface_id')):
                if 'svi' not in str(end_point.attr.get('interface_id')):
                    if 'peer' in str(end_point.attr.get('flags')):
                        return True
            return False

        data = []
        for ept in filter(flt_remote, sorted(end_points, key=lambda x: (x.attr['tenant'],
                                                                        x.attr['context'],
                                                                        x.attr['bridge_domain'],
                                                                        x.attr['mac'],
                                                                        x.attr['ip']))):
            data.append([
                ept.attr.get('tenant', ''),
                ept.attr.get('context', ''),
                ept.attr.get('bridge_domain', ''),
                ept.attr.get('mac', ''),
                ept.attr.get('ip', ''),
                ept.attr.get('interface_id', ''),
                ept.attr.get('flags', '')])

        result.append(Table(data, headers, title=title + 'Remote (vpc-peer) External End Points'))

        def flt_svi(end_point):
            """

            :param end_point:
            :return:
            """
            if 'svi' in str(end_point.attr.get('interface_id')):
                return True
            else:
                return False

        data = []
        for ept in filter(flt_svi, sorted(end_points, key=lambda x: (x.attr['tenant'],
                                                                     x.attr['context'],
                                                                     x.attr['bridge_domain'],
                                                                     x.attr['mac'],
                                                                     x.attr['ip']))):
            data.append([
                ept.attr.get('tenant', ''),
                ept.attr.get('context', ''),
                ept.attr.get('bridge_domain', ''),
                ept.attr.get('mac', ''),
                ept.attr.get('ip', ''),
                ept.attr.get('interface_id', ''),
                ept.attr.get('flags', '')])

        result.append(Table(data, headers, title=title + 'SVI End Points (default gateway endpoint)'))

        def flt_lb(end_point):
            """
            Filter function to select only end_points with interface_id containing 'loopback'
            :param end_point:
            :return: boolean
            """
            if 'loopback' in str(end_point.attr.get('interface_id')):
                return True
            else:
                return False

        data = []
        for ept in filter(flt_lb, sorted(end_points, key=lambda x: (x.attr['tenant'],
                                                                    x.attr['context'],
                                                                    x.attr['bridge_domain'],
                                                                    x.attr['mac'],
                                                                    x.attr['ip']))):
            data.append([
                ept.attr.get('tenant', ''),
                ept.attr.get('context', ''),
                ept.attr.get('bridge_domain', ''),
                ept.attr.get('mac', ''),
                ept.attr.get('ip', ''),
                ept.attr.get('interface_id', ''),
                ept.attr.get('flags', '')])

        result.append(Table(data, headers, title=title + 'Loopback End Points'))

        def flt_other(end_point):
            """

            :param end_point:
            :return: boolean
            """
            if 'loopback' not in str(end_point.attr.get('interface_id')):
                if 'svi' not in str(end_point.attr.get('interface_id')):
                    if 'local' not in str(end_point.attr.get('flags')):
                        if 'peer' not in str(end_point.attr.get('flags')):
                            return True
            return False

        data = []
        for ept in filter(flt_other, sorted(end_points, key=lambda x: (x.attr['context'],
                                                                       x.attr['bridge_domain'],
                                                                       x.attr['mac'],
                                                                       x.attr['ip']))):
            data.append([
                ept.attr.get('tenant', ''),
                ept.attr.get('context', ''),
                ept.attr.get('bridge_domain', ''),
                ept.attr.get('mac', ''),
                ept.attr.get('ip', ''),
                ept.attr.get('interface_id', ''),
                ept.attr.get('flags', '')])

        result.append(Table(data, headers, title=title + 'Other End Points'))

        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'context' in self.attr:
            result.append(Searchable('context', self.attr['context']))

        if 'bridge_domain' in self.attr:
            result.append(Searchable('bridgedomain', self.attr['bridge_domain']))

        if 'mac' in self.attr:
            result.append(Searchable('mac', self.attr['mac']))
        if 'ip' in self.attr:
            result.append(Searchable('ipv4', self.attr['ip']))
        if 'interface_id' in self.attr:
            result.append(Searchable('interface', self.attr['interface_id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Endpoint' + 'MAC-{0} IP-{1}'.format(self.attr.get('mac'), self.attr.get('ip'))

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcretePortChannel(BaseACIPhysObject):
    """
    This gets the port channels for the switch
    """

    def __init__(self, parent=None):
        """
        port channel on a switch
        """
        super(ConcretePortChannel, self).__init__(parent=parent)
        self.attr = {}
        self.members = []

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['pcAggrIf', 'ethpmAggrIf', 'pcRsMbrIfs']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all the SVIs on the switch

        :param parent:
        :param top: the topSystem level json object
        :returns: list of port channel
        """
        cls.check_parent(parent)

        result = []
        apic_class = 'pcAggrIf'
        data = top.get_class(apic_class)
        for obj in data:
            pch = cls()
            if apic_class in obj:
                pch._populate_from_attributes(obj[apic_class]['attributes'])
                pch._populate_oper_st(obj[apic_class]['attributes']['dn'], top)
                pch._populate_members(obj[apic_class]['attributes']['dn'], top)
            result.append(pch)
            if parent:
                pch._parent = parent
                pch._parent.add_child(pch)
        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the context object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['dn'] = str(attr['dn'])
        self.attr['active_ports'] = str(attr['activePorts'])
        self.attr['admin_st'] = str(attr['adminSt'])
        self.attr['auto_neg'] = str(attr['autoNeg'])
        self.attr['bandwidth'] = str(attr['bw'])
        self.attr['dot1q_ether_type'] = str(attr['dot1qEtherType'])
        self.attr['id'] = str(attr['id'])
        self.attr['max_active'] = str(attr['maxActive'])
        self.attr['max_links'] = str(attr['maxLinks'])
        self.attr['min_links'] = str(attr['minLinks'])
        self.attr['mode'] = str(attr['mode'])
        self.attr['mtu'] = str(attr['mtu'])
        self.attr['name'] = str(attr['name'])
        self.attr['switching_st'] = str(attr['switchingSt'])
        self.attr['usage'] = str(attr['usage'])

    def _populate_oper_st(self, dname, top):
        """
        will get the operational state
        """
        data = top.get_subtree('ethpmAggrIf', dname)
        for obj in data:
            attr = obj['ethpmAggrIf']['attributes']
            self.attr['access_vlan'] = str(attr['accessVlan'])
            self.attr['allowed_vlans'] = str(attr['allowedVlans'])
            self.attr['backplane_mac'] = str(attr['backplaneMac'])
            self.attr['native_vlan'] = str(attr['nativeVlan'])
            self.attr['duplex'] = str(attr['operDuplex'])
            self.attr['flow_control'] = str(attr['operFlowCtrl'])
            self.attr['router_mac'] = str(attr['operRouterMac'])
            self.attr['speed'] = str(attr['operSpeed'])
            self.attr['oper_st'] = str(attr['operSt'])
            self.attr['oper_st_qual'] = str(attr['operStQual'])
            self.attr['oper_vlans'] = str(attr['operVlans'])

    def _populate_members(self, dname, top):
        """ will get all the port member
        """
        data = top.get_subtree('pcRsMbrIfs', dname)
        for obj in data:
            member = {}
            attr = obj['pcRsMbrIfs']['attributes']
            member['state'] = str(attr['state'])
            phys_if = top.get_object(attr['tDn'])['l1PhysIf']['attributes']
            member['id'] = str(phys_if['id'])
            member['admin_st'] = str(phys_if['adminSt'])
            member['usage'] = str(phys_if['usage'])
            eth_if = top.get_subtree('ethpmPhysIf',
                                     phys_if['dn'])[0]['ethpmPhysIf']['attributes']
            member['oper_st'] = str(eth_if['operSt'])
            member['oper_st_qual'] = str(eth_if['operStQual'])
            self.members.append(member)

    @staticmethod
    def get_table(port_ch, title=''):
        """
        Will create table of switch port channel information
        :param port_ch:
        :param title:
        """
        result = []

        # noinspection PyListCreation

        for pch in sorted(port_ch, key=lambda x: (x.attr['id'])):
            headers = ['Name',
                       'ID',
                       'Mode',
                       'Bandwidth',
                       'MTU',
                       'Speed',
                       'Duplex',
                       'Active Links',
                       'Max Active',
                       'Max Links',
                       'Min Links',
                       'Auto Neg',
                       'Flow Control',
                       'Admin State',
                       'Oper State',
                       'Oper Qualifier',
                       'Switching State',
                       'Usage',
                       'Dot1Q EtherType',
                       'Oper VLANs',
                       'Allowed VLANs',
                       'Access VLAN',
                       'Native VLAN',
                       'Router MAC',
                       'Backplane MAC']

            table = [[pch.attr['name'],
                      pch.attr.get('id', ''),
                      pch.attr.get('mode', ''),
                      pch.attr.get('bandwidth', ''),
                      pch.attr.get('mtu', ''),
                      pch.attr.get('speed', ''),
                      pch.attr.get('duplex', ''),
                      pch.attr.get('active_ports', ''),
                      pch.attr.get('max_active', ''),
                      pch.attr.get('max_links', ''),
                      pch.attr.get('min_links', ''),
                      pch.attr.get('auto_neg', ''),
                      pch.attr.get('flow_control', ''),
                      pch.attr.get('admin_st', ''),
                      pch.attr.get('oper_st', ''),
                      pch.attr.get('oper_st_qual', ''),
                      pch.attr.get('switching_st', ''),
                      pch.attr.get('usage', ''),
                      pch.attr.get('dot1q_ether_type', ''),
                      pch.attr.get('oper_vlans', ''),
                      pch.attr.get('allowed_vlans', ''),
                      pch.attr.get('access_vlan', ''),
                      pch.attr.get('native_vlan', ''),
                      pch.attr.get('router_mac', ''),
                      pch.attr.get('backplane_mac', '')]]

            result.append(Table(table, headers, title=title + 'Port Channel:{0}'.format(pch.attr['id']),
                                table_orientation='vertical', columns=2))

            headers = ['Interface', 'PC State', 'Admin State', 'Oper State',
                       'Oper Qualifier', 'Usage']

            table = []
            for member in sorted(pch.members, key=lambda x: (x['id'])):
                table.append([member.get('id', ''),
                              member.get('state', ''),
                              member.get('admin_st', ''),
                              member.get('oper_st', ''),
                              member.get('oper_st_qual', ''),
                              member.get('usage', '')])

            result.append(Table(table, headers, title=title +
                                'Port Channel ({0}) Link Members'.format(pch.attr['id'])))

        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = []

        if 'name' in self.attr:
            result.append(Searchable('name', self.attr['name']))

        if 'id' in self.attr:
            result.append(Searchable('id', self.attr['id']))

        if 'router_mac' in self.attr:
            result.append(Searchable('mac', self.attr['router_mac']))

        if 'backplane_mac' in self.attr:
            result.append(Searchable('mac', self.attr['backplane_mac']))

        for member in self.members:
            if 'id' in member:
                result.append(Searchable('interface', member['id']))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Portchannel' + self.attr.get('id')

    def __eq__(self, other):

        """
        Checks that the interfaces are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False

        return self.attr.get('dn') == other.attr.get('dn')


class ConcreteOverlay(BaseACIPhysObject):
    """
    Will retrieve the overlay information for the switch
    """

    def __init__(self, parent=None):
        """
        overlay information
        """
        super(ConcreteOverlay, self).__init__(parent=parent)
        self.attr = {'vpc_tep_ip': None}
        # adding VPC VTEP info to the Overlay Class
        self.tunnels = []

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return ACI.Node

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['tunnelIf']

        return resp

    @classmethod
    def get(cls, top, parent=None):
        """
        Gather all the Overlay information for a switch

        :param parent:
        :param top: the topSystem level json object
        :returns: Single overlay object
        """
        cls.check_parent(parent)

        apic_class = cls._get_apic_classes()[0]
        data = top.get_class(apic_class)
        ovly = cls()
        tunnels = []

        # Adding the VPC VTEP to the list to help figure Tunnel endpoints
        if parent.vpc_info:
            if parent.vpc_info['oper_state'] == 'active':
                ovly.attr['vpc_tep_ip'] = parent.vpc_info['vtep_ip'].split('/')[0]

        for obj in data:
            if apic_class in obj:
                tunnels.append(ovly._populate_from_attributes(obj['tunnelIf']['attributes']))
        if tunnels:
            ovly.tunnels = sorted(tunnels, key=lambda x: (x['id']))
        else:
            ovly.tunnels = tunnels
        if parent:
            ovly._parent = parent
            ovly._parent.add_child(ovly)

        return ovly

    def _populate_from_attributes(self, attr):
        """
        This will populate the tunnel object

        :param attr: Attributes of the APIC object
        """
        self.attr['src_tep_ip'] = str(attr['src']).split('/')[0]
        tunnel = {'dest_tep_ip': str(attr['dest']),
                  'id': str(attr['id']),
                  'oper_st': str(attr['operSt']),
                  'oper_st_qual': str(attr['operStQual']),
                  'context': str(attr['vrfName']),
                  'type': str(attr['type']),
                  'dn': str(attr['dn'])}

        if 'proxy-acast-mac' in tunnel['type']:
            self.attr['proxy_ip_mac'] = tunnel['dest_tep_ip']
        if 'proxy-acast-v4' in tunnel['type']:
            self.attr['proxy_ip_v4'] = tunnel['dest_tep_ip']
        if 'proxy-acast-v6' in tunnel['type']:
            self.attr['proxy_ip_v6'] = tunnel['dest_tep_ip']
        return tunnel

    @staticmethod
    def get_table(overlay, title=''):
        """
        Create print string for overlay information
        :param overlay:
        :param title:
        """
        result = []
        for ovly in overlay:
            headers = ['Source VPC TEP address',
                       'Source TEP address:',
                       'IPv4 Proxy address:',
                       'IPv6 Proxy address:',
                       'MAC Proxy address:']
            table = [[ovly.attr.get('vpc_tep_ip', ''),
                      ovly.attr.get('src_tep_ip', ''),
                      ovly.attr.get('proxy_ip_v4', ''),
                      ovly.attr.get('proxy_ip_v6', ''),
                      ovly.attr.get('proxy_ip_mac', '')]]

            result.append(
                Table(table, headers, title=title + 'Overlay Config', table_orientation='vertical', columns=1))

            headers = ['Tunnel', 'Context', 'Dest TEP IP', 'Type', 'Oper St',
                       'Oper State Qualifier']
            table = []
            for tunnel in ovly.tunnels:
                table.append([tunnel.get('id', ''),
                              tunnel.get('context', ''),
                              tunnel.get('dest_tep_ip', ''),
                              tunnel.get('type', ''),
                              tunnel.get('oper_st', ''),
                              tunnel.get('oper_st_qual', '')])
            result.append(Table(table, headers, title=title + 'Overlay Tunnels'))
        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        result = [Searchable('overlay')]
        if 'src_tep_ip' in self.attr:
            result.append(Searchable('ipv4', self.attr['src_tep_ip']))

        if 'proxy_ip_v4' in self.attr:
            result.append(Searchable('ipv4', self.attr['proxy_ip_v4'], 'indirect'))

        if 'proxy_ip_v6' in self.attr:
            result.append(Searchable('ipv4', self.attr['proxy_ip_v6'], 'indirect'))

        if 'proxy_ip_mac' in self.attr:
            result.append(Searchable('ipv4', self.attr['proxy_ip_mac'], 'indirect'))

        for tunnel in self.tunnels:
            result.append(Searchable('tunnel'))
            if 'id' in tunnel:
                result.append(Searchable('id', tunnel['id']))

            if 'context' in tunnel:
                result.append(Searchable('context', tunnel['context']))

            if 'dest_tep_ip' in tunnel:
                result.append(Searchable('ipv4', tunnel['dest_tep_ip'], 'indirect'))

        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Concrete_Overlay'

    def __eq__(self, other):

        """
        Checks that the overlays are equal
        :param other:
        :return: True if equal
        """
        if type(self) != type(other):
            return False
        if self.get_parent() != other.get_parent():
            return False
        return self.attr.get('dn') == other.attr.get('dn')
