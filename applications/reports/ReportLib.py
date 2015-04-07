#!/usr/bin/env python
################################################################################
#               _    ____ ___   ____                       _                   #
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
# all the import
import time
import acitoolkit.acitoolkit as ACI
import acitoolkit.aciphysobject as ACI_PHYS
import copy
from SwitchJson import SwitchJson
from Table import Table

class Report(object):
    """
    This class contains methods to get report data for variou
    objects in the network.

    It is initialized with just the session
    """
    def __init__(self, session):
        """
        Initialize

       :params session:  APIC session
        """
        self.session = session
        self.report_title = ''

    def switch(self, args, resp_format='dict'):
        """
        Returns a report for the switch identified by the switch_id
        string.

        Switch information includes the following:
            Name
            Node ID
            Serial Number
            Model Number
            Management IP addre
            TEP IP addre
            VPC Enabled/Disabled
            VPC Virtual TEP addre
            VPC Partner switch

       :param switch_id: Switch ID string e.g. '102'
       :param resp_format:    Format of the response - text, dict, xml, json

       :returns: Dictionary of switch information
        """
        #
        # General structure is to create a dictionary of the
        # desired result and then convert that dictionary to
        # the desired format.
        switch_id = args.switch
        result = {}
        if switch_id:
            switches = ACI_PHYS.Node.get(self.session, '1', switch_id)
        else:
            switches = ACI_PHYS.Node.get(self.session)


        for switch in sorted(switches, key=lambda x: (x.node)):
            if switch.role != 'controller':
                result[switch.node] = {}
                result[switch.node]['node'] = switch.node
                result[switch.node]['name'] = switch.name
                result[switch.node]['num_sup_slots'] = switch.num_sup_slots
                result[switch.node]['num_lc_slots'] = switch.num_lc_slots
                result[switch.node]['num_ps_slots'] = switch.num_ps_slots
                result[switch.node]['num_fan_slots'] = switch.num_fan_slots

                top = SwitchJson(self.session, switch.node)

                if args.all or args.basic:
                    result[switch.node]['basic'] = self.make_dictionary(switch)

                # initialize arrays for all the module

                result[switch.node]['linecard'] = {}
                for index in range(0, int(switch.num_lc_slots)):
                    result[switch.node]['linecard'][str(index+1)] = {'slot_state':'empty'}

                result[switch.node]['powersupply'] = {}
                for index in range(0, int(switch.num_ps_slots)):
                    result[switch.node]['powersupply'][str(index+1)] = {'slot_state':'empty'}

                result[switch.node]['fantray'] = {}
                for index in range(0, int(switch.num_fan_slots)):
                    result[switch.node]['fantray'][str(index+1)] = {'slot_state':'empty'}

                result[switch.node]['supervisor'] = {}
                for index in range(0, int(switch.num_sup_slots)):
                    result[switch.node]['supervisor'][str(index+1)] = {'slot_state':'empty'}

                modules = switch.populate_children(deep=True)

                for module in modules:
                    result[switch.node][module.type][module.slot] = self.make_dictionary(module)
                    result[switch.node][module.type][module.slot]['slot_state'] = 'inserted'
                    if module.type == 'fantray':
                        fan_objs = module.get_children()
                        fans = {}
                        for fan_obj in fan_objs:
                            fans[fan_obj.id] = self.make_dictionary(fan_obj)
                        result[switch.node]['fantray'][module.slot]['fans'] = fans

                if not args.all and not args.linecard:
                    result[switch.node].pop('linecard', None)
                if not args.all and not args.supervisor:
                    result[switch.node].pop('supervisor', None)
                if not args.all and not args.powersupply:
                    result[switch.node].pop('powersupply', None)
                if not args.all and not args.fantray:
                    result[switch.node].pop('fantray', None)

                self.build_vnid_dictionary(top)
                if args.all or args.arp:
                    result[switch.node]['arp'] = SwitchArp.get(top)
                if args.all or args.context:
                    result[switch.node]['context'] = SwitchContext.get(top)
                if args.all or args.bridgedomain:
                    result[switch.node]['bridge_domain'] = SwitchBD.get(top)
                if args.all or args.accessrule:
                    result[switch.node]['access_rule'] = SwitchAccCtrlRule.get(self.session, top)
                    result[switch.node]['access_filter'] = SwitchFilter.get(top)
                if args.all or args.endpoint:
                    result[switch.node]['end_point'] = SwitchEp.get(top)
                if args.all or args.portchannel:
                    result[switch.node]['port_channel'] = SwitchPortChannel.get(top)
                    result[switch.node]['vpc'] = SwitchVpc.get(top)
                if args.all or args.overlay:
                    result[switch.node]['overlay'] = SwitchOverlay.get(top)

                if resp_format == 'text':
                    self.report_title = 'Switch {0} (node-{1})'.format(switch.name, switch.node)
                    print self.render_text_switch(result[switch.node])

        return result

    def time_since(self, timestamp):
        """
        returns the time since the timestamp.  Useful for
        calculating uptime
        """
        return 'unknown'

    @staticmethod
    def make_dictionary(module):
        """
        Will build a dictionary from an objects attribute
        """
        result = {}
        for attrib in module.__dict__:
            if attrib[0] != '_':
                result[attrib] = getattr(module, attrib)
        return result

    def render_text_switch(self, switch):
        """
        Render the switch info into a text string that can be directly display on
        a text monitor.
        """
        super_title = 'Switch:{0} ("{1}") - '.format(switch['node'], switch['name'])
        text_string = ''
        if 'basic' in switch:
            text_string += self.switch_basic(switch['basic'], super_title)
        if 'supervisor' in switch:
            text_string += self.switch_supervisors(switch['supervisor'],
                                                   super_title)+'\n'
        if 'linecard' in switch:
            text_string += self.switch_linecards(switch['linecard'],
                                                 super_title)+'\n'
        if 'powersupply' in switch:
            text_string += self.switch_power_supply(switch['powersupply'],
                                                    super_title)+'\n'
        if 'fantray' in switch:
            text_string += self.switch_fantray(switch['fantray'],
                                               super_title)+'\n'
        if 'overlay' in switch:
            text_string += SwitchOverlay.gen_report(switch['overlay'],
                                                    super_title) + '\n'
        if 'context' in switch:
            text_string += SwitchContext.gen_report(switch['context'],
                                                    super_title) + '\n'
        if 'bridge_domain' in switch:
            text_string += SwitchBD.gen_report(switch['bridge_domain'],
                                               super_title) + '\n'
        if 'access_rule' in switch:
            text_string += SwitchAccCtrlRule.gen_report(switch['access_rule'],
                                                        super_title) + '\n'
        if 'access_filter' in switch:
            text_string += SwitchFilter.gen_report(switch['access_filter'],
                                                   super_title) + '\n'
        if 'arp' in switch:
            text_string += SwitchArp.gen_report(switch['arp'],
                                                super_title) + '\n'
        if 'end_point' in switch:
            text_string += SwitchEp.gen_report(switch['end_point'],
                                               super_title) + '\n'
        if 'port_channel' in switch:
            text_string += SwitchPortChannel.gen_report(switch['port_channel'],
                                                        super_title)
        if 'vpc' in switch:
            text_string += SwitchVpc.gen_report(switch['vpc'],
                                                super_title)

        return text_string

    def switch_basic(self, info, super_title=None):
        """
        Creates report of basic switch information
        """
        table = []
        table.append([
            ('Name:', info['name']),
            ('Pod ID:', info['pod']),
            ('Node ID:', info['node']),
            ('Serial Number:', info['serial']),
            ('Model:', info['model']),
            ('Role:', info['role']),
            ('State:', info['state']),
            ('Firmware:', info['firmware']),
            ('Health:', info['health']),
            ('In-band managment IP:', info['inb_mgmt_ip']),
            ('Out-of-band managment IP:', info['oob_mgmt_ip']),
            ('Number of ports:', info['num_ports']),
            ('Number of Linecards (inserted):', str(info['num_lc_slots'])+\
                                                '('+str(info['num_lc_modules'])+')'),
            ('Number of Sups (inserted):', str(info['num_sup_slots'])+\
                                           '('+str(info['num_sup_modules'])+')'),
            ('Number of Fans (inserted):', str(info['num_fan_slots'])+\
                                           '('+str(info['num_fan_modules'])+')'),
            ('Number of Power Supplies (inserted):', str(info['num_ps_slots'])+\
                                           '('+str(info['num_ps_modules'])+')'),
            ('System Uptime:', info['system_uptime']),
            ('Dynamic Load Balancing:', info['dynamic_load_balancing_mode'])])
        text_string = Table.column(table, super_title+'Basic Information for {0}'\
                                    .format(info['name']))+'\n'
        return text_string

    def switch_fantray(self, modules, super_title=None):
        """
        Will create table of fantry information
        """
        text_string = ''

        table = []
        table.append(['Slot', 'Model', 'Name', 'Tray Serial',
                      'Fan ID', 'Oper St', 'Direction', 'Speed', 'Fan Serial'])
        for slot in sorted(modules):
            fantray = modules[slot]
            if fantray['slot_state'] == 'inserted':
                first_fan = sorted(fantray['fans'].keys())[0]
                table.append([slot,
                              fantray['model'],
                              fantray['name'],
                              fantray['serial'],
                              'fan-'+first_fan,
                              fantray['fans'][first_fan]['oper_st'],
                              fantray['fans'][first_fan]['direction'],
                              fantray['fans'][first_fan]['speed'],
                              fantray['fans'][first_fan]['serial']])
                for fan_id in sorted(fantray['fans']):
                    if fan_id != first_fan:
                        table.append(['', '', '', '',
                                      'fan-'+fan_id,
                                      fantray['fans'][fan_id]['oper_st'],
                                      fantray['fans'][fan_id]['direction'],
                                      fantray['fans'][fan_id]['speed'],
                                      fantray['fans'][first_fan]['serial']])
            else:
                table.append([slot,
                              'empty'])

        text_string += Table.row_column(table, super_title+'Fan Trays')
        return text_string

    def switch_power_supply(self, modules, super_title=None):
        """
        Will create table of power supply information
        """
        text_string = ''

        table = [['Slot', 'Model', 'Source Power',
                  'Oper St', 'Fan State', 'HW Ver', 'Hw Rev', 'Serial', 'Uptime']]
        for slot in sorted(modules):
            pwr_sup = modules[slot]
            if pwr_sup['slot_state'] == 'inserted':
                table.append([slot,
                              pwr_sup['model'],
                              pwr_sup['voltage_source'],
                              pwr_sup['oper_st'],
                              pwr_sup['fan_status'],
                              pwr_sup['hardware_version'],
                              pwr_sup['hardware_revision'],
                              pwr_sup['serial'],
                              self.time_since(pwr_sup['start_time'])])
            else:
                table.append([slot, 'empty'])

        text_string += Table.row_column(table, super_title+'Power Supplies')
        return text_string

    def switch_linecards(self, linecards, super_title=None):
        """
        Will create table of line card information
        """
        text_string = ''

        for slot in linecards:
            linecard = linecards[slot]
            if linecard['slot_state'] == 'inserted':
                linecard['uptime'] = self.time_since(linecard['start_time'])

        table = []
        table.append(['Slot', 'Model', 'Ports',
                      'Firmware', 'Bios', 'HW Ver', 'Hw Rev',
                      'Oper St', 'Serial', 'Uptime'])
        for slot in sorted(linecards):
            module = linecards[slot]
            if module['slot_state'] == 'inserted':
                table.append([slot,
                              module['model'],
                              module['num_ports'],
                              module['firmware'],
                              module['bios'],
                              module['hardware_version'],
                              module['hardware_revision'],
                              module['oper_st'],
                              module['serial'],
                              module['uptime']])
            else:
                table.append([slot, 'empty'])

        text_string += Table.row_column(table, super_title+'Linecards')
        return text_string

    def switch_supervisors(self, modules, super_title=None):
        """
        Will create table of supervisor information
        """
        text_string = ''

        for slot in modules:
            module = modules[slot]
            if module['slot_state'] == 'inserted':
                module['uptime'] = self.time_since(module['start_time'])
        table = []
        table.append(['Slot', 'Model', 'Ports', 'Firmware', 'Bios',
                      'HW Ver', 'Hw Rev', 'Oper St', 'Serial', 'Uptime'])
        for slot in modules:
            module = modules[slot]
            if module['slot_state'] == 'inserted':
                table.append([slot,
                              module['model'],
                              module['num_ports'],
                              module['firmware'],
                              module['bios'],
                              module['hardware_version'],
                              module['hardware_revision'],
                              module['oper_st'],
                              module['serial'],
                              module['uptime']])
            else:
                table.append([slot, 'empty'])

        text_string += Table.row_column(table, super_title+'Supervisors')
        return text_string

    def build_vnid_dictionary(self, top):
        """
        Will build a dictionary that is indexed by
        vnid and will return context or bridge_domain
        and the name of that segment.
        """
        top.vnid_dict = {}
        # pull in contexts first
        ctx_data = top.get_class('l3Inst')[:]
        ctx_data.extend(top.get_class('l3Ctx')[:])
        for ctx in ctx_data:
            if 'l3Ctx' in ctx:
                class_id = 'l3Ctx'
            else:
                class_id = 'l3Inst'

            vnid = ctx[class_id]['attributes']['encap'].split('-')[1]
            name = ctx[class_id]['attributes']['name']
            record = {'name':name, 'type':'context'}
            top.vnid_dict[vnid] = record

        # pull in bridge domains next
        bd_data = top.get_class('l2BD')
        for l2bd in bd_data:
            vnid = l2bd['l2BD']['attributes']['fabEncap'].split('-')[1]
            name = l2bd['l2BD']['attributes']['name'].split(':')[-1]
            if not name:
                name = vnid
            dname = l2bd['l2BD']['attributes']['dn']
            fields = dname.split('/')
            context_dn = '/'.join(fields[0:-1])
            ctx_data = top.get_object(context_dn)
            if 'l3Ctx' in ctx_data:
                context = ctx_data['l3Ctx']['attributes']['name']
            elif 'l3Inst' in ctx_data:
                context = ctx_data['l3Inst']['attributes']['name']
            else:
                context = None

            record = {'name':name, 'type':'bd', 'context':context}
            top.vnid_dict[vnid] = record

class SwitchArp(object):
    """
    This class is for the ARP state on a switch.
    """
    def __init__(self):
        """
        Initialize the ARP object.
        """
        self.attr = {}
        self.domain = []

    @classmethod
    def get(cls, top):
        """
        Will retrieve all of the ARP information for the specified
        switch node
        """

        result = []
        node_data = top.get_class('arpInst')
        for data in node_data:
            if 'arpInst' in data:
                arp = SwitchArp()
                arp.attr['adminSt'] = data['arpInst']['attributes']['adminSt']
                if 'children' in data['arpInst']:
                    arp.get_arp_domain(data['arpInst']['children'])
                result.append(arp)
        return result


    def get_arp_domain(self,data):
        """
        Get various attributes from the arp domain
        """
        for domain in data:
            result = {}
            result['stats'] = {}
            result['entry'] = []
            result['name'] = domain['arpDom']['attributes']['name']
            result['encap'] = domain['arpDom']['attributes']['encap']
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
        
    def get_arp_entry(self, arp_adj_ep):
        """
        parses arpAdjEp
        """
        entry = {}
        entry['interface_id'] = arp_adj_ep['arpAdjEp']['attributes']['ifId']
        entry['ip'] = arp_adj_ep['arpAdjEp']['attributes']['ip']
        entry['mac'] = arp_adj_ep['arpAdjEp']['attributes']['mac']
        entry['physical_interface'] = arp_adj_ep['arpAdjEp']['attributes']['physIfId']
        entry['oper_st'] = arp_adj_ep['arpAdjEp']['attributes']['operSt']
        return entry

    @staticmethod
    def gen_report(arps, super_title=None):
        """
        Returns arp information in a displayable format.
        """
        text_string = ''

        table_data = [['Context', 'Add', 'Delete', 'Timeout.',
                       'Resolved', 'Incomplete', 'Total', 'Rx Pkts',
                       'Rx Drop', 'Tx Pkts', 'Tx Drop', 'Tx Req',
                       'Tx Grat Req', 'Tx Resp']]
        for arp in arps:
            for domain in arp.domain:
                table_data.append([
                    domain['name'],
                    str(domain['stats'].get('adjAdd')),
                    str(domain['stats'].get('adjDel')),
                    str(domain['stats'].get('adjTimeout')),
                    str(domain['stats'].get('resolved')),
                    str(domain['stats'].get('incomplete')),
                    str(domain['stats'].get('total')),
                    str(domain['stats'].get('pktRcvd')),
                    str(domain['stats'].get('pktRcvdDrp')),
                    str(domain['stats'].get('pktSent')),
                    str(domain['stats'].get('pktSentDrop')),
                    str(domain['stats'].get('pktSentReq')),
                    str(domain['stats'].get('pktSentGratReq')),
                    str(domain['stats'].get('pktSentRsp'))
                    ])

            table_data[1:] = sorted(table_data[1:])
            text_string += Table.row_column(table_data, super_title+'ARP Stats')
    
            table_data = [['Context', 'MAC Address', 'IP Address',
                           'Physical I/F', 'Interface ID', 'Oper Status']]
    
            for domain in arp.domain:
                for entry in domain['entry']:
                    table_data.append([
                        domain['name'],
                        entry.get('mac'),
                        entry.get('ip'),
                        entry.get('physical_interface'),
                        entry.get('interface_id'),
                        entry.get('oper_st')
                        ])
            text_string += '\n'
            text_string += Table.row_column(table_data, super_title+'ARP Entries')

        return text_string

class SwitchVpc(object):
    """
    class for the VPC information for a switch

    It will contain peer info and port membership.
    """
    def __init__(self):
        """
        VPC info for a switch
        """
        self.member_ports = []
        self.peer_info = {}
        self.attr = {}
    @classmethod
    def get(cls, top):
        """
        Will retrieve all of the VPC information for the switch
        and returns the SwitchVPC object.

       :param top: the topSystem level json object
       :returns: list of Switch context
        """
        result = []
        vpc_data = top.get_class('vpcEntity')
        for vpc_d in vpc_data:
            if 'vpcEntity' in vpc_d:
                vpc = SwitchVpc()
                vpc._populate_from_attributes(vpc_d['vpcEntity']['attributes'])
                vpc._populate_from_inst(top)
                vpc.member_ports = SwitchVpcIf.get(top)
                result.append(vpc)
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
    def gen_report(vpcs, super_title=None):
        """
        Will create table of switch VPC information
        """
        text_string = ''

        table = []
        for vpc in vpcs:
            table = []
            if vpc.attr['admin_st'] == 'enabled' and vpc.attr['dom_present']:
                table.append([('Name', vpc.attr['name']),
                              ('ID', vpc.attr['id']),
                              ('Virtual MAC', vpc.attr['virtual_mac']),
                              ('Virtual IP', vpc.attr['virtual_ip']),
                              ('Admin State', vpc.attr['admin_st']),
                              ('Oper State', vpc.attr['oper_st']),
                              ('Domain Oper State', vpc.attr['dom_oper_st'])])

                table.append([('Role', vpc.attr['role']),
                              ('Peer Version', vpc.peer_info['version']),
                              ('Peer MAC', vpc.peer_info['mac']),
                              ('Peer IP', vpc.peer_info['ip']),
                              ('Peer State', vpc.peer_info['state']),
                              ('Peer State Qualifier', vpc.peer_info['st_qual'])])

                table.append([('Compatibility State', vpc.attr['compat_st']),
                              ('Compatibility String', vpc.attr['compat_str']),
                              ('Dual Active State', vpc.attr['dual_active_st']),
                              ('Local MAC', vpc.attr['local_mac']),
                              ('System MAC', vpc.attr['sys_mac'])])

                text_string += Table.column(table, super_title+'Virtual Port Channel (VPC)')
                text_string += '\nOrphan Ports:'+ vpc.attr['orphan_ports']+'\n'
                text_string += SwitchVpcIf.gen_report(vpc.member_ports, super_title)
            else:
                table.append([('Admin State', vpc.attr['admin_st']),
                              ('Oper State', vpc.attr['oper_st'])])
                text_string += Table.column(table, super_title+'Virtual Port Channel (VPC)')

        return text_string

class SwitchVpcIf(object):
    """
    Class to hold a VPC interface
    """
    def __init__(self):
        self.attr = {}

    @classmethod
    def get(cls, top):
        """
        This will get the port members of the VPC.  Each
        port member will be a port-channel instance.
        """
        result = []
        vpc_members = top.get_class('vpcIf')
        for vpc_member in vpc_members:
            if 'vpcIf' in vpc_member:
                member = SwitchVpcIf()
                member._populate_from_attributes(vpc_member['vpcIf']['attributes'])
                member._get_interface(top, vpc_member['vpcIf']['attributes']['dn'])
                result.append(member)
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
        vpc_data = top.get_object(dname+'/rsvpcConf')
        if vpc_data:
            self.attr['interface'] = vpc_data['vpcRsVpcConf']['attributes']['tSKey']

    @staticmethod
    def gen_report(vpc_ifs, super_title=None):
        """
        Will generate a text report for a list of vpc_ifs.
        """

        text_string = ''

        table = []
        table.append(['ID', 'Interface', 'Oper St', 'Remote Oper State',
                      'Up VLANS', 'Remote Up VLANs'])
        for intf in vpc_ifs:
            table.append([
                str(intf.attr.get('id')),
                str(intf.attr.get('interface')),
                str(intf.attr.get('oper_st')),
                str(intf.attr.get('remote_oper_st')),
                str(intf.attr.get('up_vlans')),
                str(intf.attr.get('remote_up_vlans'))])

        table[1:] = sorted(table[1:])
        text_string += Table.row_column(table, super_title+'VPC Interfaces')
        return text_string

class SwitchContext(object):
    """
    The l3-context on a switch.  This is derived from
    the concrete model
    """
    def __init__(self):
        """
        l3-context on a switch
        """
        self.attr = {}

    @classmethod
    def get(cls, top):
        """
        This will get all of the switch contexts on the
        specified node.  If no node is specified, then
        it will get all of the switch contexts on all
        of the switches.

       :param top: the topSystem level json object
       :param node:  Optional switch node id
       :returns: list of Switch context
        """
        result = []
        ctx_data = top.get_class('l3Ctx')[:]
        ctx_data.extend(top.get_class('l3Inst')[:])
        for ctx in ctx_data:
            context = SwitchContext()
            if 'l3Ctx' in ctx:
                context._populate_from_attributes(ctx['l3Ctx']['attributes'])
            else:
                context._populate_from_attributes(ctx['l3Inst']['attributes'])
            result.append(context)
        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate the context object from the APIC attribute

       :param attr: Attributes of the APIC object
        """
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
    def gen_report(contexts, super_title=None):
        """
        Will create table of switch context information
        """
        text_string = ''

        table = []
        table.append(['Name', 'VNID', 'Scope', 'Type', 'VRF Id',
                      'MCast Class Id', 'Admin St', 'Oper St', 'Modified'])
        for context in contexts:
            table.append([
                str(context.attr.get('name')),
                str(context.attr.get('vnid')),
                str(context.attr.get('scope')),
                str(context.attr.get('type')),
                str(context.attr.get('vrf_id')),
                str(context.attr.get('mcst_class_id')),
                str(context.attr.get('admin_st')),
                str(context.attr.get('oper_st')),
                str(context.attr.get('modified_time'))])

        table[1:] = sorted(table[1:])
        text_string += Table.row_column(table, super_title+'Contexts (VRFs)')
        return text_string

class SwitchSVI(object):
    """
    The SVIs a switch.  This is derived from
    the concrete model
    """
    def __init__(self):
        """
        SVI on a switch
        """
        self.attr = {}

    @classmethod
    def get(cls, top):
        """
        This will get all the SVIs on the switch

       :param top: the topSystem level json object
       :param top:  json record of entire switch config
       :returns: list of SVI
        """
        result = []

        svi_data = top.get_class('sviIf')
        for svi_obj in svi_data:
            svi = SwitchSVI()
            if 'sviIf' in svi_obj:
                svi._populate_from_attributes(svi_obj['sviIf']['attributes'])

            result.append(svi)

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

class SwitchLoopback(object):
    """
    Loopback interfaces on the switch
    """
    def __init__(self):
        """
        SVI on a switch
        """
        self.attr = {}

    @classmethod
    def get(cls, top):
        """
        This will get all the loopback interfaces on the switch

       :param top: the topSystem level json object
       :param top:  json record of entire switch config
       :returns: list of loopback
        """
        result = []

        data = top.get_class('l3LbRtdIf')
        for obj in data:
            lbif = SwitchLoopback()
            if 'l3LbRtdIf' in obj:
                lbif._populate_from_attributes(obj['l3LbRtdIf']['attributes'])
                lbif._get_oper_st(obj['l3LbRtdIf']['attributes']['dn'], top)
            result.append(lbif)

        return result

    def _populate_from_attributes(self, attr):
        """
        This will populate from the APIC attribute

       :param attr: Attributes of the APIC object
        """
        self.attr['descr'] = attr['descr']
        self.attr['admin_st'] = attr['adminSt']
        self.attr['id'] = attr['id']

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

class SwitchBD(object):
    """
    The bridge domain on a switch.  This is derived from
    the concrete model
    """
    def __init__(self):
        """
        bridge domain on a switch
        """
        self.attr = {}

    @classmethod
    def get(cls, top):
        """
        This will get all of the switch bd on the
        specified node.  If no node is specified, then
        it will get all of the bds on all
        of the switches.

       :param top: the topSystem level json object
       :param node:  Optional switch node id
       :returns: list of Switch bridge domain
        """
        result = []
        bd_data = top.get_class('l2BD')
        for l2bd in bd_data:
            bdomain = SwitchBD()
            bdomain._populate_from_attributes(l2bd['l2BD']['attributes'])

            # get the context name by reading the context
            bdomain.attr['context_name'] = bdomain.\
              _get_cxt_name(l2bd['l2BD']['attributes']['dn'], top)
            bdomain.attr['flood_gipo'] = bdomain._get_multicast_flood_address( \
                l2bd['l2BD']['attributes']['dn'], top)
            result.append(bdomain)

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

    def _get_cxt_name(self, dname, top):
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
    def _get_multicast_flood_address(self, dname, top):
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
    def gen_report(bridge_domains, super_title=None):
        """
        Will create table of switch bridge domain information
        """
        text_string = ''

        table = []
        table.append(['Context', 'Name', 'VNID', 'Mode', 'Bridge',
                      'Route', 'Type', 'ARP Flood', 'MCST Flood',
                      'Unk UCAST', 'Unk MCAST', 'Learn', 'Flood GIPo',
                      'Admin St', 'Oper St'])
        for bdomain in bridge_domains:
            if ':' in bdomain.attr['name']:
                name = bdomain.attr['name'].split(':')[-1]
            else:
                name = str(bdomain.attr.get('name'))

            table.append([
                str(bdomain.attr.get('context_name')),
                name,
                str(bdomain.attr.get('vnid')),
                str(bdomain.attr.get('bridge_mode')),
                str(bdomain.attr.get('bridge')),
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

        table[1:] = sorted(table[1:])
        text_string += Table.row_column(table, super_title+'Bridge Domains (BDs)')
        return text_string

class SwitchAccCtrlRule(object):
    """
    Access control rules on a switch
    """
    def __init__(self):
        """
        access control rules on a switch
        """
        self.attr = {}

    @classmethod
    def get(cls, session, top):
        """
        This will get all of the access rules on the
        specified node.  If no node is specified, then
        it will get all of the access rules on all
        of the switches.

       :param top: the topSystem level json object
       :param node:  Optional switch node id
       :returns: list of Switch bridge domain
        """
        result = []

        rule_data = top.get_class('actrlRule')
        epgs = ACI.EPG.get(session)
        contexts = ACI.Context.get(session)

        for actrl_rule in rule_data:
            rule = SwitchAccCtrlRule()
            rule._populate_from_attributes(actrl_rule['actrlRule']['attributes'])
            # get the context name by reading the context
            rule._get_tenant_context(contexts)
            rule._get_epg_names(epgs)
            rule._get_pod_node()
            result.append(rule)

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
        #contexts = ACI.Context.get(session)
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

        #get all the EPG
        #epgs = ACI.EPG.get(session)
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
    def gen_report(data, super_title=None):
        """
        Will create table of access rule
        """
        text_string = ''

        table = []
        table.append(['Tenant', 'Context', 'Type', 'Scope', 'Src EPG',
                      'Dst EPG', 'Filter', 'Action', 'DSCP', 'QoS', 'Priority'])
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

        table[1:] = sorted(table[1:], key=lambda x: (x[10], x[0], x[1]))
        text_string += Table.row_column(table, super_title+\
                                        'Access Rules (Contracts/Access Policies)')
        return text_string

class SwitchFilter(object):
    """
    Access control filters on a switch
    """
    def __init__(self):
        """
        access control filters on a switch
        """
        self.entries = []
        self.attr = {}

    @classmethod
    def get(cls, top):
        """
        This will get all of the access filters on the
        specified node.  If no node is specified, then
        it will get all of the access rules on all
        of the switches.

       :param top: the topSystem level json object
       :param node:  Optional switch node id
       :returns: list of Switch bridge domain
        """
        result = []
        filter_data = top.get_class('actrlFlt')

        for filter_object in filter_data:
            acc_filter = SwitchFilter()
            acc_filter._populate_from_attributes(filter_object['actrlFlt']['attributes'])
            # get the context name by reading the context
            acc_filter._get_entries(top)
            acc_filter._get_pod_node()
            result.append(acc_filter)

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

        self.entries = SwitchFilterEntry.get(self, top)

    def _get_pod_node(self):
        """
        This will populate pod and node ID from the
        dn.
        """
        name = self.attr['dn'].split('/')
        self.attr['pod'] = str(name[1].split('-')[1])
        self.attr['node'] = str(name[2].split('-')[1])

    @staticmethod
    def gen_report(data, super_title=None):
        """
        Will create table of access filter
        """
        text_string = ''

        table = []
        table.append(['Filter', 'Name', 'Status', 'Entry #', 'EtherType',
                      'Protocol/Arp Opcode', 'L4 DPort', 'L4 SPort', 'TCP Flags'])
        for acc_filter in sorted(data, key=lambda x: (x.attr['id'])):
            sorted_entries = sorted(acc_filter.entries, key=lambda x: (x.attr['name']))
            first_entry = sorted_entries[0]
            dst_port = SwitchFilter._get_port(sorted_entries[0].attr['dst_from_port'],
                                              sorted_entries[0].attr['dst_to_port'])
            src_port = SwitchFilter._get_port(sorted_entries[0].attr['src_from_port'],
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
                dst_port = SwitchFilter._get_port(sorted_entry.attr['dst_from_port'],
                                                  sorted_entry.attr['dst_to_port'])
                src_port = SwitchFilter._get_port(sorted_entry.attr['src_from_port'],
                                                  sorted_entry.attr['src_to_port'])
                table.append(['', '', '',
                              str(sorted_entry.attr['id']),
                              str(sorted_entry.attr['ether_type']),
                              str(sorted_entry.attr['protocol']),
                              dst_port,
                              src_port,
                              str(sorted_entry.attr['tcp_rules'])])

        text_string += Table.row_column(table, super_title+'Access Filters')
        return text_string

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

class SwitchFilterEntry(object):
    """
    Access control entries of a filter
    """
    def __init__(self):
        """
        access control filters of a filter
        """
        self.attr = {}
    @classmethod
    def get(cls, parent, top):
        """
        This will get all of the access filter entries of the
        specified filter.  If no filter is specified, then
        it will get all of the access rules on all
        of the switches.

       :param top: the topSystem level json object
       :param node:  Optional switch node id
       :returns: list of Switch bridge domain
        """
        result = []
        entry_data = top.get_subtree('actrlEntry', parent.attr['dn'])

        for entry_object in entry_data:
            acc_entry = SwitchFilterEntry()
            acc_entry._populate_from_attributes(entry_object['actrlEntry']['attributes'])
            # get the context name by reading the context
            acc_entry._get_filter_name()
            acc_entry._get_entry_id()
            result.append(acc_entry)

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
        return self.attr['dn'] == other.attr['dn']

class SwitchEp(object):
    """
    Endpoint on the switch
    """
    def __init__(self):
        """
        endpoints on a switch
        """
        self.attr = {}
        self.attr['ip'] = None
        self.attr['mac'] = None

    @classmethod
    def get(cls, top):
        """
        This will get all of the endpoints known to the switch

       :param top: the topSystem level json object
       :param node:  Optional switch node id
       :returns: list of endpoint
        """
        result = []

        ep_data = top.get_class('epmIpEp')[:]
        ep_data.extend(top.get_class('epmMacEp')[:])

        for ep_object in ep_data:
            end_point = SwitchEp()
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
                    ip_add = rel['epmRsMacEpToIpEpAtt']['attributes']['tDn'].\
                        split('/ip-[')[1].split(']')[0]
                    ip_ctx = rel['epmRsMacEpToIpEpAtt']['attributes']['tDn'].\
                        split('/ctx-[vxlan-')[1].split(']/')[0]
                    ip_bd = rel['epmRsMacEpToIpEpAtt']['attributes']['tDn'].\
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
        svis = SwitchSVI.get(top)
        svi_table = {}
        for svi in svis:
            svi_table[svi.attr['id']] = svi
        for ept in final_result:
            if 'vlan' in ept.attr['interface_id'] and ept.attr['mac'] == None:
                ept.attr['mac'] = svi_table[ept.attr['interface_id']].attr['mac']
                ept.attr['interface_id'] = 'svi-'+ept.attr['interface_id']

        # mark loopback interfaces as loopback
        lbifs = SwitchLoopback.get(top)
        lbif_table = {}
        for lbif in lbifs:
            lbif_table[lbif.attr['id']] = lbif
        for ep in final_result:
            if ep.attr['interface_id'] in lbif_table:
                ep.attr['interface_id'] = 'loopback-'+ep.attr['interface_id']


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
    def gen_report(end_points, super_title=None):
        """
        Will create table of switch end point information
        """
        text_string = ''
        table = []
        table.append(['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                      'Interface', 'Flags'])
        def flt_local_external(end_point):
            if 'loopback' not in str(end_point.attr.get('interface_id')) and \
               'svi' not in str(end_point.attr.get('interface_id')) and \
               'local' in str(end_point.attr.get('flags')):
                return True
            else:
                return False
        
        for ept in filter(flt_local_external,sorted(end_points, key=lambda x: (x.attr['context'],
                                                     x.attr['bridge_domain'],
                                                     x.attr['mac'],
                                                     x.attr['ip']))):
            table.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        text_string += Table.row_column(table, super_title+'Local External End Points') +'\n'
        table = []
        table.append(['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                      'Interface', 'Flags'])
        def flt_remote(end_point):
            if 'loopback' not in str(end_point.attr.get('interface_id')) and \
               'svi' not in str(end_point.attr.get('interface_id')) and \
               'peer' in str(end_point.attr.get('flags')):
                return True
            else:
                return False
        
        for ept in filter(flt_remote,sorted(end_points, key=lambda x: (x.attr['context'],
                                                     x.attr['bridge_domain'],
                                                     x.attr['mac'],
                                                     x.attr['ip']))):
            table.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        text_string += Table.row_column(table, super_title+'Remote (vpc-peer) External End Points') +'\n'
        
        table = []
        table.append(['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                      'Interface', 'Flags'])
        
        def flt_svi(end_point):
            if 'svi' in str(end_point.attr.get('interface_id')) :
                return True
            else:
                return False
        for ept in filter(flt_svi,sorted(end_points, key=lambda x: (x.attr['context'],
                                                     x.attr['bridge_domain'],
                                                     x.attr['mac'],
                                                     x.attr['ip']))):
            table.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        text_string += Table.row_column(table, super_title+'SVI End Points (default gateway endpoint)') +'\n'
        table = []
        
        def flt_lb(end_point):
            if 'loopback' in str(end_point.attr.get('interface_id')) :
                return True
            else:
                return False
        table.append(['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                      'Interface', 'Flags'])
        for ept in filter(flt_lb,sorted(end_points, key=lambda x: (x.attr['context'],
                                                     x.attr['bridge_domain'],
                                                     x.attr['mac'],
                                                     x.attr['ip']))):
            table.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        text_string += Table.row_column(table, super_title+'Loopback End Points') + '\n'
        table = []
        table.append(['Context', 'Bridge Domain', 'MAC Address', 'IP Address',
                      'Interface', 'Flags'])
        def flt_other(end_point):
            if 'loopback' not in str(end_point.attr.get('interface_id')) and \
               'svi' not in str(end_point.attr.get('interface_id')) and \
               'local' not in str(end_point.attr.get('flags')) and \
               'peer' not in str(end_point.attr.get('flags')):
                return True
            else:
                return False
        
        for ept in filter(flt_other,sorted(end_points, key=lambda x: (x.attr['context'],
                                                     x.attr['bridge_domain'],
                                                     x.attr['mac'],
                                                     x.attr['ip']))):
            table.append([
                str(ept.attr.get('context')),
                str(ept.attr.get('bridge_domain')),
                str(ept.attr.get('mac')),
                str(ept.attr.get('ip')),
                str(ept.attr.get('interface_id')),
                str(ept.attr.get('flags'))])

        text_string += Table.row_column(table, super_title+'Other End Points') +'\n'
        return text_string

    def __eq__(self, other):
        """
        """
        return self.attr['dn'] == other.attr['dn']

class SwitchPortChannel(object):
    """
    This gets the port channels for the switch
    """
    def __init__(self):
        """
        port channel on a switch
        """
        self.attr = {}
        self.members = []

    @classmethod
    def get(cls, top):
        """
        This will get all the SVIs on the switch

       :param top: the topSystem level json object
       :returns: list of port channel
        """
        result = []

        data = top.get_class('pcAggrIf')
        for obj in data:
            pch = SwitchPortChannel()
            if 'pcAggrIf' in obj:
                pch._populate_from_attributes(obj['pcAggrIf']['attributes'])
                pch._populate_oper_st(obj['pcAggrIf']['attributes']['dn'], top)
                pch._populate_members(obj['pcAggrIf']['attributes']['dn'], top)
            result.append(pch)

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
    def gen_report(port_ch, super_title=None):
        """
        Will create table of switch port channel information
        """
        text_string = ''

        for pch in sorted(port_ch, key=lambda x: (x.attr['id'])):
            table = []
            table.append([('Name', pch.attr['name']),
                          ('ID', pch.attr['id']),
                          ('Mode', pch.attr['mode']),
                          ('Bandwidth', pch.attr['bandwidth']),
                          ('MTU', pch.attr['mtu']),
                          ('Speed', pch.attr['speed']),
                          ('Duplex', pch.attr['duplex'])])

            table.append([('Active Links', pch.attr['active_ports']),
                          ('Max Active', pch.attr['max_active']),
                          ('Max Links', pch.attr['max_links']),
                          ('Min Links', pch.attr['min_links']),
                          ('Auto Neg', pch.attr['auto_neg']),
                          ('Flow Control', pch.attr['flow_control'])])

            table.append([('Admin State', pch.attr['admin_st']),
                          ('Oper State', pch.attr['oper_st']),
                          ('Oper Qualifier', pch.attr['oper_st_qual']),
                          ('Switching State', pch.attr['switching_st']),
                          ('Usage', pch.attr['usage']),
                          ('Dot1Q EtherType', pch.attr['dot1q_ether_type'])])

            table.append([('Oper VLANs', pch.attr['oper_vlans']),
                          ('Allowed VLANs', pch.attr['allowed_vlans']),
                          ('Access VLAN', pch.attr['access_vlan']),
                          ('Native VLAN', pch.attr['native_vlan']),
                          ('Router MAC', pch.attr['router_mac']),
                          ('Backplane MAC', pch.attr['backplane_mac'])])
            text_string += Table.column(table, super_title+'Port Channel:{0}'.\
                                        format(pch.attr['id']))

            text_string += '\n'
            table = []
            table.append(['Interface', 'PC State', 'Admin State', 'Oper State',
                          'Oper Qualifier', 'Usage'])
            for member in sorted(pch.members, key=lambda x: (x['id'])):
                table.append([member['id'],
                              member['state'],
                              member['admin_st'],
                              member['oper_st'],
                              member['oper_st_qual'],
                              member['usage']])
            text_string += Table.row_column(table,
                                            super_title+'Port Channel "{0}" Link Members'.\
                                            format(pch.attr['id']))
            text_string += '\n'

        return text_string

class SwitchOverlay(object):
    """
    Will retrieve the overlay information for the switch
    """
    def __init__(self):
        """
        overlay information
        """
        self.attr = {}
        self.tunnels = []
        self.attr['ipv4-proxy'] = None
        self.attr['ipv6-proxy'] = None
        self.attr['mac-proxy'] = None

    @classmethod
    def get(cls, top):
        """
        Gather all the Overlay information for a switch

       :param top: the topSystem level json object
       :returns: Single overlay object
        """
        data = top.get_class('tunnelIf')
        ovly = SwitchOverlay()
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
        tunnel = {}
        self.attr['src_tep_ip'] = attr['src'].split('/')[0]
        tunnel['dest_tep_ip'] = attr['dest']
        tunnel['id'] = attr['id']
        tunnel['oper_st'] = attr['operSt']
        tunnel['oper_st_qual'] = attr['operStQual']
        tunnel['context'] = attr['vrfName']
        tunnel['type'] = attr['type']

        if 'proxy-acast-mac' in tunnel['type']:
            self.attr['proxy_ip_mac'] = tunnel['dest_tep_ip']
        if 'proxy-acast-v4' in tunnel['type']:
            self.attr['proxy_ip_v4'] = tunnel['dest_tep_ip']
        if 'proxy-acast-v6' in tunnel['type']:
            self.attr['proxy_ip_v6'] = tunnel['dest_tep_ip']
        return tunnel

    @staticmethod
    def gen_report(overlay, super_title=None):
        """
        Create print string for overlay information
        """
        text_string = ""
        table = []
        table.append([('Source TEP address:', overlay.attr.get('src_tep_ip')),
                      ('IPv4 Proxy address:', overlay.attr.get('proxy_ip_v4')),
                      ('IPv6 Proxy address:', overlay.attr.get('proxy_ip_v6')),
                      ('MAC Proxy address:', overlay.attr.get('proxy_ip_mac'))])
        text_string += Table.column(table, super_title+'Overlay Config') + '\n'

        table = []
        table.append(['Tunnel', 'Context', 'Dest TEP IP', 'Type', 'Oper St',
                      'Oper State Qualifier'])
        for tunnel in overlay.tunnels:
            table.append([tunnel['id'],
                          tunnel['context'],
                          tunnel['dest_tep_ip'],
                          tunnel['type'],
                          tunnel['oper_st'],
                          tunnel['oper_st_qual']])
        text_string += Table.row_column(table, super_title+'Overlay Tunnels')
        return text_string

if __name__ == '__main__':

    # Get all the argument
    description = 'Creates Reports for Various Components.'
    creds = ACI.Credentials('apic', description)
    creds.add_argument('-s', '--switch', help='The ID of the Switch',
                       default=None)
    args = creds.get()

    # Login to the APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
    start_time = time.time()
    report = Report(session)
    report.switch(args.switch, 'text')
    finish_time = time.time()
    print 'Elapsed time {0:.3} seconds'.format(finish_time - start_time)

