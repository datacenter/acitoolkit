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
# all the import
from acibaseobject import BaseACIPhysObject
import copy
from aciTable import Table
#from aciSearch import AciSearch, Searchable
import acitoolkit as ACI


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
        super(ConcreteArp, self).__init__(name='', parent=parent)
        self.attr = {}
        self.domain = []
        self._parent = parent
        if parent is not None:
            self._parent.add_child(self)

    @classmethod
    def get(cls, top, parent=None):
        """
        Will retrieve all of the ARP information for the specified
        switch node
        :param parent: Parent object of type Node
        :param top:
        """

        result = []
        node_data = top.get_class('arpInst')
        for data in node_data:
            if 'arpInst' in data:
                arp = cls()
                arp.attr['adminSt'] = data['arpInst']['attributes']['adminSt']
                if 'children' in data['arpInst']:
                    arp.get_arp_domain(data['arpInst']['children'])
                result.append(arp)
            if parent:
                arp._parent = parent
                arp._parent.add_child(arp)
        return result

    def get_arp_domain(self, data):
        """
        Get various attributes from the arp domain
        :param data:
        """
        for domain in data:
            result = {'stats': {},
                      'entry': [],
                      'name': domain['arpDom']['attributes']['name'],
                      'encap': domain['arpDom']['attributes']['encap']}
            if 'children' in domain['arpDom']:
                for child in domain['arpDom']['children']:
                    if 'arpDomStatsAdj' in child:
                        result['stats'].update(child['arpDomStatsAdj']['attributes'])
                    if 'arpDomStatsRx' in child:
                        result['stats'].update(child['arpDomStatsRx']['attributes'])
                    if 'arpDomStatsTx' in child:
                        result['stats'].update(child['arpDomStatsTx']['attributes'])

                    if 'arpDb' in child:
                        if 'children' in child['arpDb']:
                            for arp_adj_ep in child['arpDb']['children']:
                                entry = self.get_arp_entry(arp_adj_ep)
                                result['entry'].append(entry)
            self.domain.append(result)

    @staticmethod
    def get_arp_entry(arp_adj_ep):
        """
        parses arpAdjEp
        :param arp_adj_ep:
        """
        entry = {'interface_id': arp_adj_ep['arpAdjEp']['attributes']['ifId'],
                 'ip': arp_adj_ep['arpAdjEp']['attributes']['ip'],
                 'mac': arp_adj_ep['arpAdjEp']['attributes']['mac'],
                 'physical_interface': arp_adj_ep['arpAdjEp']['attributes']['physIfId'],
                 'oper_st': arp_adj_ep['arpAdjEp']['attributes']['operSt']}
        return entry

    @staticmethod
    def get_table(arps, super_title=None):
        """
        Returns arp information in a displayable format.
        :param super_title:
        :param arps:
        """
        result = []
        headers = ['Context', 'Add', 'Delete', 'Timeout.',
                   'Resolved', 'Incomplete', 'Total', 'Rx Pkts',
                   'Rx Drop', 'Tx Pkts', 'Tx Drop', 'Tx Req',
                   'Tx Grat Req', 'Tx Resp']
        data = []
        for arp in arps:
            for domain in arp.domain:
                data.append([
                    domain['name'],
                    domain['stats'].get('adjAdd'),
                    domain['stats'].get('adjDel'),
                    domain['stats'].get('adjTimeout'),
                    domain['stats'].get('resolved'),
                    domain['stats'].get('incomplete'),
                    domain['stats'].get('total'),
                    domain['stats'].get('pktRcvd'),
                    domain['stats'].get('pktRcvdDrp'),
                    domain['stats'].get('pktSent'),
                    domain['stats'].get('pktSentDrop'),
                    domain['stats'].get('pktSentReq'),
                    domain['stats'].get('pktSentGratReq'),
                    domain['stats'].get('pktSentRsp')
                ])

            data = sorted(data)
            result.append(Table(data, headers, title=super_title + 'ARP Stats'))

            headers = ['Context', 'MAC Address', 'IP Address',
                       'Physical I/F', 'Interface ID', 'Oper Status']
            data = []
            for domain in arp.domain:
                for entry in domain['entry']:
                    data.append([
                        domain['name'],
                        entry.get('mac'),
                        entry.get('ip'),
                        entry.get('physical_interface'),
                        entry.get('interface_id'),
                        entry.get('oper_st')
                    ])
            result.append(Table(data, headers, title=super_title + 'ARP Entries'))

        return result

    # def _define_searchables(self):
    #     """
    #     Create all of the searchable terms
    #
    #     """
    #     result = []
    #     for domain in self.domain:
    #         if 'entry' in domain:
    #             for entry in domain['entry']:
    #                 if entry['ip'] is not None:
    #                     result.append(Searchable('ipv4', entry['ip'], 'indirect'))
    #                 if entry['mac'] is not None:
    #                     result.append(Searchable('mac', entry['mac'], 'indirect'))
    #                 if entry['physical_interface'] is not None:
    #                     result.append(Searchable('interface', entry['physical_interface']))
    #         if domain['name']:
    #             result.append(Searchable('context', domain['name'], 'indirect'))
    #             result.append(Searchable('name', domain['name'], 'direct'))
    #     return result


class ConcreteVpc(BaseACIPhysObject):
    """
    class for the VPC information for a switch

    It will contain peer info and port membership.
    """

    def __init__(self, parent=None):
        """
        VPC info for a switch
        """
        super(ConcreteVpc, self).__init__(name='', parent=parent)
        self.member_ports = []
        self.peer_info = {}
        self.attr = {}

    @classmethod
    def get(cls, top, parent=None):
        """
        Will retrieve all of the VPC information for the switch
        and returns the ConcreteVPC object.

        :param parent:
        :param top: the topSystem level json object
        :returns: list of Switch context
        """
        result = []
        vpc_data = top.get_class('vpcEntity')
        for vpc_d in vpc_data:
            if 'vpcEntity' in vpc_d:
                vpc = cls()
                vpc._populate_from_attributes(vpc_d['vpcEntity']['attributes'])
                vpc._populate_from_inst(top)
                vpc.member_ports = ConcreteVpcIf.get(top)
                result.append(vpc)
            if parent:
                vpc._parent = parent
                vpc._parent.add_child(vpc)

        return result

    def _populate_from_attributes(self, attr):
        """
        Fill in attribute
        """
        self.attr['oper_st'] = attr['operSt']
        self.attr['dn'] = attr['dn']

    def _populate_from_inst(self, top):
        """
        get info from the instance
        """
        inst_data = top.get_subtree('vpcInst', self.attr['dn'])
        self.attr['admin_st'] = None
        for inst in inst_data:
            if 'vpcInst' in inst:
                self.attr['admin_st'] = inst['vpcInst']['attributes']['adminSt']
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
                self.attr['compat_str'] = attr['compatQualStr']
                self.attr['compat_st'] = attr['compatSt']
                self.attr['dual_active_st'] = attr['dualActiveSt']
                self.attr['id'] = attr['id']
                self.attr['role'] = attr['lacpRole']
                self.attr['local_mac'] = attr['localMAC']
                self.attr['modify_time'] = attr['modTs']
                self.attr['name'] = attr['name']
                self.attr['dom_oper_st'] = attr['operSt']
                self.attr['orphan_ports'] = attr['orphanPortList']
                self.peer_info['ip'] = attr['peerIp']
                self.peer_info['mac'] = attr['peerMAC']
                self.peer_info['state'] = attr['peerSt']
                self.peer_info['st_qual'] = attr['peerStQual']
                self.peer_info['version'] = attr['peerVersion']
                self.attr['sys_mac'] = attr['sysMac']
                self.attr['virtual_ip'] = attr['virtualIp']
                self.attr['virtual_mac'] = attr['vpcMAC']

    @staticmethod
    def get_table(vpcs, super_title=None):
        """
        Will create table of switch VPC information
        :param super_title:
        :param vpcs:
        """
        result = []
        for vpc in vpcs:
            data = []
            if vpc.attr['admin_st'] == 'enabled' and vpc.attr['dom_present']:
                data.extend([['Name', vpc.attr['name']],
                             ['ID', vpc.attr['id']],
                             ['Virtual MAC', vpc.attr['virtual_mac']],
                             ['Virtual IP', vpc.attr['virtual_ip']],
                             ['Admin State', vpc.attr['admin_st']],
                             ['Oper State', vpc.attr['oper_st']],
                             ['Domain Oper State', vpc.attr['dom_oper_st']]])

                data.extend([['Role', vpc.attr['role']],
                             ['Peer Version', vpc.peer_info['version']],
                             ['Peer MAC', vpc.peer_info['mac']],
                             ['Peer IP', vpc.peer_info['ip']],
                             ['Peer State', vpc.peer_info['state']],
                             ['Peer State Qualifier', vpc.peer_info['st_qual']]])

                data.extend([['Compatibility State', vpc.attr['compat_st']],
                             ['Compatibility String', vpc.attr['compat_str']],
                             ['Dual Active State', vpc.attr['dual_active_st']],
                             ['Local MAC', vpc.attr['local_mac']],
                             ['System MAC', vpc.attr['sys_mac']]])

                table = Table(data, title=super_title + 'Virtual Port Channel (VPC)')
                result.append(table)
            else:
                data.append(['Admin State', vpc.attr['admin_st']])
                data.append(['Oper State', vpc.attr['oper_st']])
                table = Table(data, title=super_title + 'Virtual Port Channel (VPC)')
                result.append(table)
        return result


class ConcreteVpcIf(BaseACIPhysObject):
    """
    Class to hold a VPC interface
    """

    def __init__(self, parent=None):
        super(ConcreteVpcIf, self).__init__(name='', parent=parent)
        self.attr = {}

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get the port members of the VPC.  Each
        port member will be a port-channel instance.
        :param parent:
        :param top:
        """
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
        self.attr['compat_st'] = attr['compatSt']
        self.attr['id'] = attr['id']
        self.attr['remote_oper_st'] = attr['remoteOperSt']
        self.attr['access_vlan'] = attr['cfgdAccessVlan']
        self.attr['trunk_vlans'] = attr['cfgdTrunkVlans']
        self.attr['vlans'] = attr['cfgdVlans']
        self.attr['compat_qual'] = attr['compatQual']
        self.attr['compat_qual_str'] = attr['compatQualStr']
        self.attr['compat_st'] = attr['compatSt']
        self.attr['oper_st'] = attr['localOperSt']
        self.attr['remote_vlans'] = attr['peerCfgdVlans']
        self.attr['remote_up_vlans'] = attr['peerUpVlans']
        self.attr['remote_oper_st'] = attr['remoteOperSt']
        self.attr['susp_vlans'] = attr['suspVlans']
        self.attr['up_vlans'] = attr['upVlans']

    def _get_interface(self, top, dname):
        """
        Retrieves the VPC interface
        """
        vpc_data = top.get_object(dname + '/rsvpcConf')
        if vpc_data:
            self.attr['interface'] = vpc_data['vpcRsVpcConf']['attributes']['tSKey']

    @staticmethod
    def get_table(vpc_ifs, super_title=None):
        """
        Will generate a text report for a list of vpc_ifs.
        :param super_title:
        :param vpc_ifs:
        """

        result = []

        headers = ['ID', 'Interface', 'Oper St', 'Remote Oper State',
                   'Up VLANS', 'Remote Up VLANs']
        data = []
        for intf in vpc_ifs:
            data.append([
                str(intf.attr.get('id')),
                str(intf.attr.get('interface')),
                str(intf.attr.get('oper_st')),
                str(intf.attr.get('remote_oper_st')),
                str(intf.attr.get('up_vlans')),
                str(intf.attr.get('remote_up_vlans'))])

        data = sorted(data)
        result.append(Table(data, headers, title=super_title + 'VPC Interfaces'))
        return result


class ConcreteContext(BaseACIPhysObject):
    """
    The l3-context on a switch.  This is derived from
    the concrete model
    """

    def __init__(self, parent=None):
        """
        l3-context on a switch
        """
        super(ConcreteContext, self).__init__(name='', parent=parent)
        self.attr = {}

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
        self.attr['dn'] = attr['dn']
        self.attr['oper_st'] = attr['operState']
        self.attr['create_time'] = attr['createTs']
        self.attr['admin_st'] = attr['adminState']
        self.attr['oper_st_qual'] = attr['operStQual']
        self.attr['encap'] = attr['encap']
        self.attr['modified_time'] = attr['lastChgdTs']
        self.attr['name'] = attr['name']
        if 'pcTag' in attr:
            self.attr['mcst_class_id'] = attr['pcTag']
        else:
            self.attr['mcst_class_id'] = None

        self.attr['scope'] = attr['scope']
        self.attr['type'] = attr.get('type')
        self.attr['vrf_id'] = attr['id']
        self.attr['vrf_oui'] = attr['oui']
        self.attr['mgmt_class_id'] = attr.get('mgmtPcTag')
        if 'vxlan-' in self.attr['encap']:
            self.attr['vnid'] = self.attr['encap'].split('-')[1]
        else:
            self.attr['vnid'] = None

    @staticmethod
    def get_table(contexts, super_title=None):
        """
        Will create table of switch context information
        :param super_title:
        :param contexts:
        """

        headers = ['Name', 'VNID', 'Scope', 'Type', 'VRF Id',
                   'MCast Class Id', 'Admin St', 'Oper St', 'Modified']
        data = []
        for context in contexts:
            data.append([
                context.attr.get('name'),
                context.attr.get('vnid'),
                context.attr.get('scope'),
                context.attr.get('type'),
                context.attr.get('vrf_id'),
                context.attr.get('mcst_class_id'),
                context.attr.get('admin_st'),
                context.attr.get('oper_st'),
                context.attr.get('modified_time')])

        data = sorted(data)
        table = Table(data, headers, title=super_title + 'Contexts (VRFs)')
        return [table, ]


class ConcreteSVI(BaseACIPhysObject):
    """
    The SVIs a switch.  This is derived from
    the concrete model
    """

    def __init__(self, parent=None):
        """
        SVI on a switch
        """
        super(ConcreteSVI, self).__init__(name='', parent=parent)
        self.attr = {}

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all the SVIs on the switch

        :param parent:
       :param top: the topSystem level json object
       :param top:  json record of entire switch config
       :returns: list of SVI
        """
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
        self.attr['bandwidth'] = attr['bw']
        self.attr['admin_st'] = attr['adminSt']
        self.attr['oper_st_qual'] = attr['operStQual']
        self.attr['oper_st'] = attr['operSt']
        self.attr['modified_time'] = attr['modTs']
        self.attr['name'] = attr['name']
        self.attr['mac'] = attr['mac']
        self.attr['id'] = attr['id']
        self.attr['vlan_id'] = attr['vlanId']
        self.attr['vlan_type'] = attr['vlanT']
        self.attr['dn'] = attr['dn']

class ConcreteLoopback(BaseACIPhysObject):
    """
    Loopback interfaces on the switch
    """

    def __init__(self, parent=None):
        """
        SVI on a switch
        """
        super(ConcreteLoopback, self).__init__(name='', parent=parent)
        self.attr = {}

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all the loopback interfaces on the switch

        :param parent:
       :param top: the topSystem level json object
       :returns: list of loopback
        """
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
        self.attr['descr'] = attr['descr']
        self.attr['admin_st'] = attr['adminSt']
        self.attr['id'] = attr['id']
        self.attr['dn'] = attr['dn']

    def _get_oper_st(self, dname, top):
        """
        Gets the operational state
        """
        data = top.get_subtree('ethpmLbRtdIf', dname)
        self.attr['oper_st'] = None
        self.attr['oper_st_qual'] = None
        for obj in data:
            self.attr['oper_st'] = obj['ethpmLbRtdIf']['attributes']['operSt']
            self.attr['oper_st_qual'] = obj['ethpmLbRtdIf']['attributes']['operStQual']


class ConcreteBD(BaseACIPhysObject):
    """
    The bridge domain on a switch.  This is derived from
    the concrete model
    """

    def __init__(self, parent=None):
        """
        bridge domain on a switch
        """
        super(ConcreteBD, self).__init__(name='', parent=parent)
        self.attr = {}

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
        result = []
        bd_data = top.get_class('l2BD')
        for l2bd in bd_data:
            bdomain = cls()
            bdomain._populate_from_attributes(l2bd['l2BD']['attributes'])

            # get the context name by reading the context
            bdomain.attr['context_name'] = bdomain. \
                _get_cxt_name(l2bd['l2BD']['attributes']['dn'], top)
            bdomain.attr['flood_gipo'] = bdomain._get_multicast_flood_address(
                l2bd['l2BD']['attributes']['dn'], top)
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
        self.attr['oper_st'] = attr['operSt']
        self.attr['create_time'] = attr['createTs']
        self.attr['admin_st'] = attr['adminSt']

        self.attr['access_encap'] = attr['accEncap']
        self.attr['bridge_mode'] = attr['bridgeMode']
        self.attr['modified_time'] = attr['modTs']
        self.attr['name'] = attr['name']
        self.attr['unknown_ucast_class_id'] = attr['pcTag']
        self.attr['fabric_encap'] = attr['fabEncap']
        if 'vxlan-' in self.attr['fabric_encap']:
            self.attr['vnid'] = self.attr['fabric_encap'].split('-')[1]
        else:
            self.attr['vnid'] = None

        if not self.attr['name']:
            self.attr['name'] = self.attr['vnid']

        self.attr['type'] = attr['type']
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

        self.attr['learn_disable'] = attr['epOperSt']
        self.attr['unknown_mac_ucast'] = attr['unkMacUcastAct']
        self.attr['unknown_mcast'] = attr['unkMcastAct']

    @staticmethod
    def _get_cxt_name(dname, top):
        """
        Gets the context name by reading the context object
        """
        fields = dname.split('/')
        context_dn = '/'.join(fields[0:-1])
        bd_data = top.get_object(context_dn)
        name = None
        if 'l3Ctx' in bd_data:
            name = bd_data['l3Ctx']['attributes']['name']
        elif 'l3Inst' in bd_data:
            name = bd_data['l3Inst']['attributes']['name']

        return name

    @staticmethod
    def _get_multicast_flood_address(dname, top):
        """
        Will read the fmcastGrp to get the multicast addre
        used when flooding across the fabric.
        """
        bd_data = top.get_subtree('fmcastGrp', dname)
        for obj in bd_data:
            if 'fmcastGrp' in obj:
                return obj['fmcastGrp']['attributes']['addr']
            else:
                return None

    @staticmethod
    def get_table(bridge_domains, super_title=None):
        """
        Will create table of switch bridge domain information
        :param super_title:
        :param bridge_domains:
        """
        result = []

        headers = ['Context', 'Name', 'VNID', 'Mode',
                   'Route', 'Type', 'ARP Flood', 'MCST Flood',
                   'Unk UCAST', 'Unk MCAST', 'Learn', 'Flood GIPo',
                   'Admin St', 'Oper St']
        data = []
        for bdomain in bridge_domains:
            if ':' in bdomain.attr['name']:
                name = bdomain.attr['name'].split(':')[-1]
            else:
                name = str(bdomain.attr.get('name'))

            data.append([
                str(bdomain.attr.get('context_name')),
                name,
                str(bdomain.attr.get('vnid')),
                str(bdomain.attr.get('bridge_mode')),
                # str(bdomain.attr.get('bridge')),
                str(bdomain.attr.get('route')),
                str(bdomain.attr.get('type')),
                str(bdomain.attr.get('arp_flood')),
                str(bdomain.attr.get('mcst_flood')),
                str(bdomain.attr.get('unknown_mac_ucast')),
                str(bdomain.attr.get('unknown_mcast')),
                str(bdomain.attr.get('learn_disable')),
                str(bdomain.attr.get('flood_gipo')),
                str(bdomain.attr.get('admin_st')),
                str(bdomain.attr.get('oper_st'))])

        data = sorted(data)
        result.append(Table(data, headers, title=super_title + 'Bridge Domains (BDs)'))
        return result


class ConcreteAccCtrlRule(BaseACIPhysObject):
    """
    Access control rules on a switch
    """

    def __init__(self, parent=None):
        """
        access control rules on a switch
        """
        super(ConcreteAccCtrlRule, self).__init__(name='', parent=parent)
        self.attr = {}

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
        self.attr['action'] = attr['action']
        self.attr['dclass'] = attr['dPcTag']
        self.attr['sclass'] = attr['sPcTag']
        self.attr['descr'] = attr['descr']
        self.attr['direction'] = attr['direction']
        self.attr['filter_id'] = attr['fltId']
        self.attr['mark_dscp'] = attr['markDscp']
        self.attr['name'] = attr['name']
        self.attr['oper_st'] = attr['operSt']
        self.attr['priority'] = attr['prio']
        self.attr['qos_group'] = attr['qosGrp']
        self.attr['scope'] = attr['scopeId']
        self.attr['type'] = attr['type']
        self.attr['status'] = attr['status']
        self.attr['modified_time'] = attr['modTs']
        self.attr['dn'] = attr['dn']

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
        self.attr['context'] = None
        self.attr['tenant'] = None

    def _get_epg_names(self, epgs):
        """
        This will derive source and destination EPG
        names from dclass and sclass - if possible

        """
        self.attr['s_epg'] = None
        self.attr['d_epg'] = None
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
    def get_table(data, super_title=None):
        """
        Will create table of access rule
        :param super_title:
        :param data:
        """
        result = []

        headers = ['Tenant', 'Context', 'Type', 'Scope', 'Src EPG',
                   'Dst EPG', 'Filter', 'Action', 'DSCP', 'QoS', 'Priority']
        table = []
        for rule in data:
            table.append([
                str(rule.attr.get('tenant')),
                str(rule.attr.get('context')),
                str(rule.attr.get('type')),
                str(rule.attr.get('scope')),
                str(rule.attr.get('s_epg')),
                str(rule.attr.get('d_epg')),
                str(rule.attr.get('filter_id')),
                str(rule.attr.get('action')),
                str(rule.attr.get('mark_dscp')),
                str(rule.attr.get('qos_grp')),
                str(rule.attr.get('priority'))])

        table = sorted(table, key=lambda x: (x[10], x[0], x[1]))
        result.append(Table(table, headers, title=super_title + 'Access Rules (Contracts/Access Policies)'))

        return result


class ConcreteFilter(BaseACIPhysObject):
    """
    Access control filters on a switch
    """

    def __init__(self, parent=None):
        """
        access control filters on a switch
        """
        super(ConcreteFilter, self).__init__(name='', parent=parent)
        self.entries = []
        self.attr = {}

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
        self.attr['name'] = attr['name']
        self.attr['id'] = attr['id']
        self.attr['descr'] = attr['descr']
        self.attr['status'] = attr['status']
        self.attr['modified_time'] = attr['modTs']
        self.attr['dn'] = attr['dn']

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
        self.attr['pod'] = str(name[1].split('-')[1])
        self.attr['node'] = str(name[2].split('-')[1])

    @staticmethod
    def get_table(data, super_title=None):
        """
        Will create table of access filter
        :param super_title:
        :param data:
        """
        result = []

        headers = ['Filter', 'Name', 'Status', 'Entry #', 'EtherType',
                   'Protocol/Arp Opcode', 'L4 DPort', 'L4 SPort', 'TCP Flags']

        table = []
        for acc_filter in sorted(data, key=lambda x: (x.attr['id'])):
            sorted_entries = sorted(acc_filter.entries, key=lambda x: (x.attr['name']))
            first_entry = sorted_entries[0]
            dst_port = ConcreteFilter._get_port(sorted_entries[0].attr['dst_from_port'],
                                                sorted_entries[0].attr['dst_to_port'])
            src_port = ConcreteFilter._get_port(sorted_entries[0].attr['src_from_port'],
                                                sorted_entries[0].attr['src_to_port'])
            table.append([
                str(acc_filter.attr.get('id')),
                str(acc_filter.attr.get('name')),
                str(acc_filter.attr.get('status')),
                str(sorted_entries[0].attr['id']),
                str(sorted_entries[0].attr['ether_type']),
                str(sorted_entries[0].attr['protocol']),
                dst_port,
                src_port,
                str(sorted_entries[0].attr['tcp_rules'])])
            for sorted_entry in sorted_entries:
                if sorted_entry == first_entry:
                    continue
                dst_port = ConcreteFilter._get_port(sorted_entry.attr['dst_from_port'],
                                                    sorted_entry.attr['dst_to_port'])
                src_port = ConcreteFilter._get_port(sorted_entry.attr['src_from_port'],
                                                    sorted_entry.attr['src_to_port'])
                table.append(['', '', '',
                              str(sorted_entry.attr['id']),
                              str(sorted_entry.attr['ether_type']),
                              str(sorted_entry.attr['protocol']),
                              dst_port,
                              src_port,
                              str(sorted_entry.attr['tcp_rules'])])
        result.append(Table(table, headers, title=super_title + 'Access Filters'))
        return result

    @staticmethod
    def _get_port(from_port, to_port):
        """
        will build a string that is a port range or a port number
        depending upon the from_port and to_port value
        """
        if from_port == to_port:
            return from_port
        return '{0}-{1}'.format(from_port, to_port)

    def __str__(self):
        return self.attr['name']


class ConcreteFilterEntry(BaseACIPhysObject):
    """
    Access control entries of a filter
    """

    def __init__(self, parent=None):
        """
        access control filters of a filter
        """
        super(ConcreteFilterEntry, self).__init__(name='', parent=parent)
        self.attr = {}

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
        self.attr['apply_to_frag'] = attr['applyToFrag']
        self.attr['arp_opcode'] = attr['arpOpc']
        self.attr['dst_from_port'] = attr['dFromPort']
        self.attr['dst_to_port'] = attr['dToPort']
        self.attr['descr'] = attr['descr']
        self.attr['dn'] = attr['dn']
        self.attr['ether_type'] = attr['etherT']
        self.attr['modified_time'] = attr['modTs']
        self.attr['name'] = attr['name']
        self.attr['priority'] = attr['prio']
        self.attr['protocol'] = attr['prot']
        self.attr['src_from_port'] = attr['sFromPort']
        self.attr['src_to_port'] = attr['sToPort']
        self.attr['status'] = attr['status']
        self.attr['tcp_rules'] = attr['tcpRules']

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

    def __eq__(self, other):
        """
        """
        if type(self) != type(other):
            return False
        return self.attr['dn'] == other.attr['dn']


class ConcreteEp(BaseACIPhysObject):
    """
    Endpoint on the switch
    """

    def __init__(self, parent=None):
        """
        endpoints on a switch
        """
        super(ConcreteEp, self).__init__(name='', parent=parent)
        self.attr = {'ip': None, 'mac': None}

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
        result = []

        ep_data = top.get_class('epmIpEp')[:]
        ep_data.extend(top.get_class('epmMacEp')[:])

        for ep_object in ep_data:
            end_point = cls()
            if 'epmIpEp' in ep_object:
                end_point._populate_from_attributes(ep_object['epmIpEp']['attributes'])
                end_point.attr['address_family'] = 'ipv4'
                end_point.attr['ip'] = ep_object['epmIpEp']['attributes']['addr']
            if 'epmMacEp' in ep_object:
                end_point._populate_from_attributes(ep_object['epmMacEp']['attributes'])
                end_point.attr['address_family'] = 'mac'
                end_point.attr['mac'] = ep_object['epmMacEp']['attributes']['addr']

            end_point._get_context_bd(top)
            result.append(end_point)

        # all the EP info has been gathered - now clean up
        rem_ep = []
        new_ep_list = []
        for end_point in result:
            if end_point.attr['address_family'] == 'mac':
                rel_data = top.get_subtree('epmRsMacEpToIpEpAtt', end_point.attr['dn'])
                for rel in rel_data:
                    ip_add = rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']. \
                        split('/ip-[')[1].split(']')[0]
                    if 'ctx-[vxlan-' in rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']:

                        ip_ctx = rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']. \
                            split('/ctx-[vxlan-')[1].split(']/')[0]
                    elif '/inst-' in rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']:
                        ip_ctx = rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']. \
                            split('/inst-')[1].split('/')[0]
                        if ip_ctx in top.ctx_dict:
                            ip_ctx = top.ctx_dict[ip_ctx]
                    else:
                        ip_ctx = None
                    ip_bd = rel['epmRsMacEpToIpEpAtt']['attributes']['tDn']. \
                        split('/bd-[vxlan-')[1].split(']/')[0]
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
                        print 'unexpected context or bd mismatch', ip_add, ip_ctx, ip_bd
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
            # noinspection PyAugmentAssignment
            if 'vlan' in ept.attr['interface_id'] and ept.attr['mac'] is None:
                ept.attr['mac'] = svi_table[ept.attr['interface_id']].attr['mac']
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

    def _populate_from_attributes(self, attr):
        """
        This will populate the object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['address'] = attr['addr']
        self.attr['name'] = attr['name']
        self.attr['flags'] = attr['flags']
        self.attr['interface_id'] = attr['ifId']
        self.attr['create_time'] = attr['createTs']
        self.attr['dn'] = attr['dn']

    @staticmethod
    def get_table(end_points, super_title=None):
        """
        Will create table of switch end point information
        :param super_title:
        :param end_points:
        """
        result = []
        headers = ['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
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
        for ept in filter(flt_local_external, sorted(end_points, key=lambda x: (x.attr['context'],
                                                                                x.attr['bridge_domain'],
                                                                                x.attr['mac'],
                                                                                x.attr['ip']))):
            data.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        result.append(Table(data, headers, title=super_title + 'Local External End Points'))

        headers = ['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                   'Interface', 'Flags']

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
        for ept in filter(flt_remote, sorted(end_points, key=lambda x: (x.attr['context'],
                                                                        x.attr['bridge_domain'],
                                                                        x.attr['mac'],
                                                                        x.attr['ip']))):
            data.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        result.append(Table(data, headers, title=super_title + 'Remote (vpc-peer) External End Points'))

        headers = ['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                   'Interface', 'Flags']

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
        for ept in filter(flt_svi, sorted(end_points, key=lambda x: (x.attr['context'],
                                                                     x.attr['bridge_domain'],
                                                                     x.attr['mac'],
                                                                     x.attr['ip']))):
            data.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        result.append(Table(data, headers, title=super_title + 'SVI End Points (default gateway endpoint)'))

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

        headers = ['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                   'Interface', 'Flags']
        data = []
        for ept in filter(flt_lb, sorted(end_points, key=lambda x: (x.attr['context'],
                                                                    x.attr['bridge_domain'],
                                                                    x.attr['mac'],
                                                                    x.attr['ip']))):
            data.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        result.append(Table(data, headers, title=super_title + 'Loopback End Points'))
        headers = ['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                   'Interface', 'Flags']

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
                ept.attr.get('context'),
                ept.attr.get('bridge_domain'),
                ept.attr.get('mac'),
                ept.attr.get('ip'),
                ept.attr.get('interface_id'),
                ept.attr.get('flags')])

        result.append(Table(data, headers, title=super_title + 'Other End Points'))

        return result

    def __eq__(self, other):
        """
        """
        return self.attr['dn'] == other.attr['dn']


class ConcretePortChannel(BaseACIPhysObject):
    """
    This gets the port channels for the switch
    """

    def __init__(self, parent=None):
        """
        port channel on a switch
        """
        super(ConcretePortChannel, self).__init__(name='', parent=parent)
        self.attr = {}
        self.members = []

    @classmethod
    def get(cls, top, parent=None):
        """
        This will get all the SVIs on the switch

        :param parent:
       :param top: the topSystem level json object
       :returns: list of port channel
        """
        result = []

        data = top.get_class('pcAggrIf')
        for obj in data:
            pch = cls()
            if 'pcAggrIf' in obj:
                pch._populate_from_attributes(obj['pcAggrIf']['attributes'])
                pch._populate_oper_st(obj['pcAggrIf']['attributes']['dn'], top)
                pch._populate_members(obj['pcAggrIf']['attributes']['dn'], top)
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
        self.attr['active_ports'] = attr['activePorts']
        self.attr['admin_st'] = attr['adminSt']
        self.attr['auto_neg'] = attr['autoNeg']
        self.attr['bandwidth'] = attr['bw']
        self.attr['dot1q_ether_type'] = attr['dot1qEtherType']
        self.attr['id'] = attr['id']
        self.attr['max_active'] = attr['maxActive']
        self.attr['max_links'] = attr['maxLinks']
        self.attr['min_links'] = attr['minLinks']
        self.attr['mode'] = attr['mode']
        self.attr['mtu'] = attr['mtu']
        self.attr['name'] = attr['name']
        self.attr['switching_st'] = attr['switchingSt']
        self.attr['usage'] = attr['usage']

    def _populate_oper_st(self, dname, top):
        """
        will get the operational state
        """
        data = top.get_subtree('ethpmAggrIf', dname)
        for obj in data:
            attr = obj['ethpmAggrIf']['attributes']
            self.attr['access_vlan'] = attr['accessVlan']
            self.attr['allowed_vlans'] = attr['allowedVlans']
            self.attr['backplane_mac'] = attr['backplaneMac']
            self.attr['native_vlan'] = attr['nativeVlan']
            self.attr['duplex'] = attr['operDuplex']
            self.attr['flow_control'] = attr['operFlowCtrl']
            self.attr['router_mac'] = attr['operRouterMac']
            self.attr['speed'] = attr['operSpeed']
            self.attr['oper_st'] = attr['operSt']
            self.attr['oper_st_qual'] = attr['operStQual']
            self.attr['oper_vlans'] = attr['operVlans']

    def _populate_members(self, dname, top):
        """ will get all the port member
        """
        data = top.get_subtree('pcRsMbrIfs', dname)
        for obj in data:
            member = {}
            attr = obj['pcRsMbrIfs']['attributes']
            member['state'] = attr['state']
            phys_if = top.get_object(attr['tDn'])['l1PhysIf']['attributes']
            member['id'] = phys_if['id']
            member['admin_st'] = phys_if['adminSt']
            member['usage'] = phys_if['usage']
            eth_if = top.get_subtree('ethpmPhysIf',
                                     phys_if['dn'])[0]['ethpmPhysIf']['attributes']
            member['oper_st'] = eth_if['operSt']
            member['oper_st_qual'] = eth_if['operStQual']
            self.members.append(member)

    @staticmethod
    def get_table(port_ch, super_title=None):
        """
        Will create table of switch port channel information
        :param port_ch:
        :param super_title:
        """
        result = []

        # noinspection PyListCreation
        for pch in sorted(port_ch, key=lambda x: (x.attr['id'])):
            table = []
            table.extend([['Name', pch.attr['name']],
                          ['ID', pch.attr['id']],
                          ['Mode', pch.attr['mode']],
                          ['Bandwidth', pch.attr['bandwidth']],
                          ['MTU', pch.attr['mtu']],
                          ['Speed', pch.attr['speed']],
                          ['Duplex', pch.attr['duplex']]])

            table.extend([['Active Links', pch.attr['active_ports']],
                          ['Max Active', pch.attr['max_active']],
                          ['Max Links', pch.attr['max_links']],
                          ['Min Links', pch.attr['min_links']],
                          ['Auto Neg', pch.attr['auto_neg']],
                          ['Flow Control', pch.attr['flow_control']]])

            table.extend([['Admin State', pch.attr['admin_st']],
                          ['Oper State', pch.attr['oper_st']],
                          ['Oper Qualifier', pch.attr['oper_st_qual']],
                          ['Switching State', pch.attr['switching_st']],
                          ['Usage', pch.attr['usage']],
                          ['Dot1Q EtherType', pch.attr['dot1q_ether_type']]])

            table.extend([['Oper VLANs', pch.attr['oper_vlans']],
                          ['Allowed VLANs', pch.attr['allowed_vlans']],
                          ['Access VLAN', pch.attr['access_vlan']],
                          ['Native VLAN', pch.attr['native_vlan']],
                          ['Router MAC', pch.attr['router_mac']],
                          ['Backplane MAC', pch.attr['backplane_mac']]])

            result.append(Table(table, title=super_title + 'Port Channel:{0}'.format(pch.attr['id'])))

            headers = ['Interface', 'PC State', 'Admin State', 'Oper State',
                       'Oper Qualifier', 'Usage']

            table = []
            for member in sorted(pch.members, key=lambda x: (x['id'])):
                table.append([member['id'],
                              member['state'],
                              member['admin_st'],
                              member['oper_st'],
                              member['oper_st_qual'],
                              member['usage']])

            result.append(Table(table, headers, title=super_title +
                                   'Port Channel "{0}" Link Members'.format(pch.attr['id'])))

        return result


class ConcreteOverlay(BaseACIPhysObject):
    """
    Will retrieve the overlay information for the switch
    """

    def __init__(self, parent=None):
        """
        overlay information
        """
        super(ConcreteOverlay, self).__init__(name='', parent=parent)
        self.attr = {}
        self.tunnels = []
        self.attr['ipv4-proxy'] = None
        self.attr['ipv6-proxy'] = None
        self.attr['mac-proxy'] = None

    @classmethod
    def get(cls, top, parent=None):
        """
        Gather all the Overlay information for a switch

        :param parent:
       :param top: the topSystem level json object
       :returns: Single overlay object
        """
        data = top.get_class('tunnelIf')
        ovly = cls(parent)
        tunnels = []
        for obj in data:
            if 'tunnelIf' in obj:
                tunnels.append(ovly._populate_from_attributes(obj['tunnelIf']['attributes']))
        if tunnels:
            ovly.tunnels = sorted(tunnels, key=lambda x: (x['id']))
        else:
            ovly.tunnels = tunnels

        return ovly

    def _populate_from_attributes(self, attr):
        """
        This will populate the tunnel object

        :param attr: Attributes of the APIC object
        """
        self.attr['src_tep_ip'] = attr['src'].split('/')[0]
        tunnel = {'dest_tep_ip': attr['dest'],
                  'id': attr['id'],
                  'oper_st': attr['operSt'],
                  'oper_st_qual': attr['operStQual'],
                  'context': attr['vrfName'],
                  'type': attr['type']}

        if 'proxy-acast-mac' in tunnel['type']:
            self.attr['proxy_ip_mac'] = tunnel['dest_tep_ip']
        if 'proxy-acast-v4' in tunnel['type']:
            self.attr['proxy_ip_v4'] = tunnel['dest_tep_ip']
        if 'proxy-acast-v6' in tunnel['type']:
            self.attr['proxy_ip_v6'] = tunnel['dest_tep_ip']
        return tunnel

    @staticmethod
    def get_table(overlay, super_title=None):
        """
        Create print string for overlay information
        :param overlay:
        :param super_title:
        """
        for ovly in overlay:
            result = []
            table = [['Source TEP address:', ovly.attr.get('src_tep_ip')],
                     ['IPv4 Proxy address:', ovly.attr.get('proxy_ip_v4')],
                     ['IPv6 Proxy address:', ovly.attr.get('proxy_ip_v6')],
                     ['MAC Proxy address:', ovly.attr.get('proxy_ip_mac')]]
            result.append(Table(table, title=super_title + 'Overlay Config'))

            headers = ['Tunnel', 'Context', 'Dest TEP IP', 'Type', 'Oper St',
                       'Oper State Qualifier']
            table = []
            for tunnel in ovly.tunnels:
                table.append([tunnel['id'],
                              tunnel['context'],
                              tunnel['dest_tep_ip'],
                              tunnel['type'],
                              tunnel['oper_st'],
                              tunnel['oper_st_qual']])
            result.append(Table(table, headers, title=super_title + 'Overlay Tunnels'))
        return result

