#!/usr/bin/env python
###############################################################################
#           _    ____ ___ _____           _ _    _ _    ____ _     ___        #
#          / \  / ___|_ _|_   _|__   ___ | | | _(_) |_ / ___| |   |_ _|       #
#         / _ \| |    | |  | |/ _ \ / _ \| | |/ / | __| |   | |    | |        #
#        / ___ \ |___ | |  | | (_) | (_) | |   <| | |_| |___| |___ | |        #
#       /_/   \_\____|___| |_|\___/ \___/|_|_|\_\_|\__|\____|_____|___|       #
#                                                                             #
###############################################################################
#                                                                             #
# Copyright (c) 2015 Cisco Systems                                            #
# All Rights Reserved.                                                        #
#                                                                             #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may  #
#    not use this file except in compliance with the License. You may obtain  #
#    a copy of the License at                                                 #
#                                                                             #
#         http://www.apache.org/licenses/LICENSE-2.0                          #
#                                                                             #
#    Unless required by applicable law or agreed to in writing, software      #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT#
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the #
#    License for the specific language governing permissions and limitations  #
#    under the License.                                                       #
#                                                                             #
###############################################################################

"""This module implements a CLI similar to Cisco IOS and NXOS
   for use with the ACI Toolkit.
"""
import sys
import getopt
import logging
from cmd import Cmd
from acitoolkit import (Tenant, Contract, AppProfile, EPG, Interface, PortChannel, L2ExtDomain, Subnet,
                        PhysDomain, VmmDomain, L3ExtDomain, EPGDomain, Context, BridgeDomain, L2Interface,
                        FilterEntry, Session, Tag)
import requests
import pprint
READLINE = True
NOT_NO_ARGS = 'show exit help configure switchto switchback interface no'
try:
    import readline
    # The following is required for command completion on Mac OS
    import rlcompleter
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
except:
    try:
        import pyreadline
    except:
        READLINE = False


def error_message(resp):
    """
    Print an error message

    :param resp: Response object from Requests library
    :return: None
    """
    print('Error:  Unable to push configuration to APIC')
    print('Reason: ' + str(resp.text))


class SubMode(Cmd):
    """
    Implements the basic commands for all modes
    """
    def __init__(self):
        Cmd.__init__(self)
        self.tenant = None
        self.app = None
        self.epg = None
        self.contract = None
        self.set_prompt()
        self.negative = False
        self.apic = None

    def set_prompt(self):
        """ Should be overridden by inheriting classes """
        pass

    def do_show(self, args, to_return=False):
        """ Show running system information"""
        words = args.strip().split(' ')
        if len(words) > 1:
            if words[1] == 'detail':
                detail = True
        temp = self.complete_show('', 'show ' + args, 0, 0)
        if len(temp) == 1:
            words[0] = temp[0]

        if words[0] == 'tenant':
            tenants = Tenant.get(self.apic)
            tenant_dict = {}
            for tenant in tenants:
                tenant_dict[tenant.name] = []
            if to_return:
                return tenant_dict
            print('Tenant')
            print('------')
            for tenant in tenants:
                print(tenant.name)
        elif words[0] == 'bridgedomain':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            output = []
            for tenant in tenants:
                bds = BridgeDomain.get(self.apic, tenant)
                bd_dict = {}
                bd_dict[tenant.name] = []
                for bd in bds:
                    bd_dict[tenant.name].append(bd.name)
                if to_return:
                    return bd_dict
                for bd in bds:
                    output.append((tenant.name, bd.name))
            template = '{0:19} {1:20}'
            print(template.format('Tenant', 'BridgeDomain'))
            print(template.format('------', '------------'))
            for rec in output:
                print(template.format(*rec))
        elif words[0] == 'context':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            output = []
            for tenant in tenants:
                contexts = Context.get(self.apic, tenant)
                for context in contexts:
                    output.append((tenant.name, context.name))
            template = '{0:19} {1:20}'
            print(template.format('Tenant', 'Context'))
            print(template.format('------', '-------'))
            for rec in output:
                print(template.format(*rec))
        elif words[0] == 'contract':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            output = []
            for tenant in tenants:
                contracts = Contract.get(self.apic, tenant)
                for contract in contracts:
                    output.append((tenant.name, contract.name))
            template = '{0:19} {1:20}'
            print(template.format('Tenant', 'Contract'))
            print(template.format('------', '-------'))
            for rec in output:
                print(template.format(*rec))
        elif words[0] == 'interface':
            ifs = Interface.get(self.apic)
            print('Interface\tType\tStatus\tSpeed\tMTU')
            for interface in ifs:
                print(interface)
        elif words[0] == 'port-channel':
            portchannels = PortChannel.get(self.apic)
            print('Port Channel')
            print('------------')
            for pc in portchannels:
                print(pc)
        elif words[0] == 'tag':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [Tenant(self.tenant.name)]
            output = []
            if len(words) == 2:
                if words[1] == 'epg':
                    for tenant in tenants:
                        apps = AppProfile.get(self.apic, tenant)
                        for app in apps:
                            epgs = EPG.get(self.apic, app, tenant)
                            for epg in epgs:
                                tag_list = Tag.get(self.apic, parent=epg, tenant=tenant)
                                if len(tag_list):
                                    tag_list = [tag.name for tag in tag_list]
                                    if len(tag_list):
                                        output.append((tenant.name, app.name, epg.name, ",".join(tag_list)))
                    template = "{0:20} {1:20} {2:20} {3:20}"
                    if len(output):
                        print(template.format("Tenant",
                                              "App",
                                              "EPG",
                                              "Tag"))
                        print(template.format("-" * 20,
                                              "-" * 20,
                                              "-" * 20,
                                              "-" * 20))
                        for rec in output:
                            print(template.format(*rec))

                elif words[1] == 'bd':
                    print("bd")
            else:
                for tenant in tenants:
                    tag_list = Tag.get(self.apic, parent=tenant, tenant=tenant)
                    tag_list = [tag.name for tag in tag_list]
                    if len(tag_list):
                        output.append((tenant.name, ",".join(tag_list)))
                template = '{0:20} {1:20}'
                print(template.format('Tenant', 'Tag'))
                print(template.format('------', '-----------'))
                for rec in output:
                    print(template.format(*rec))
        elif words[0] == 'app':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [Tenant(self.tenant.name)]
            output = []
            for tenant in tenants:
                apps = AppProfile.get(self.apic, tenant)
                for app in apps:
                    if tenant is not None and tenant != app.get_parent():
                        continue
                    output.append((app.get_parent().name, app.name))
            template = '{0:19} {1:20}'
            print(template.format('Tenant', 'App Profile'))
            print(template.format('------', '-----------'))
            for rec in output:
                print(template.format(*rec))
        elif words[0] == 'epg':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [Tenant(self.tenant.name)]
            for tenant in tenants:
                apps = AppProfile.get(self.apic, tenant)
                for app in apps:
                    epgs = EPG.get(self.apic, app, tenant)
                    epg_dict = {}
                    for epg in epgs:
                        assert app == epg.get_parent()
                        app = epg.get_parent()
                        if app is not None:
                            tenant = app.get_parent()
                        if self.app is not None and self.app != app:
                            continue
                        if self.tenant is not None and self.tenant != tenant:
                            continue
                        if tenant.name not in epg_dict:
                            epg_dict[tenant.name] = {}
                        if app.name not in epg_dict[tenant.name]:
                            epg_dict[tenant.name][app.name] = []
                        epg_dict[tenant.name][app.name].append(epg.name)
                    if epg_dict:
                        pprint.pprint(epg_dict)
        elif words[0] == 'infradomains':
            infradomains = PhysDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('---------------')
                print('Physical Domain')
                print('---------------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = []
            infradomains = VmmDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('----------')
                print('VMM Domain')
                print('----------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = L2ExtDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('------------------')
                print('L2 External Domain')
                print('------------------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = L3ExtDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('------------------')
                print('L3 External Domain')
                print('------------------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = EPGDomain.get(self.apic)

            for domain in infradomains:
                association = domain.tenant_name + ':' + domain.app_name + ':' + domain.epg_name
                output.append((domain.domain_name, domain.domain_type,
                               association))

            if len(infradomains) > 0:
                template = '{0:20} {1:11} {2:26}'
                print(template.format('Infra Domain Profile', 'Domain Type', 'TENANT:APP:EPG Association'))
                print(template.format('--------------------', '-----------', '--------------------------'))
                for rec in output:
                    print(template.format(*rec))
                print('\n')
        else:
            sys.stdout.write('%% Unrecognized command\n')

    def emptyline(self):
        pass

    def complete_show(self, text, line, begidx, endidx):
        " Complete the show command "
        show_args = ['bridgedomain', 'context', 'contract', 'app',
                     'port-channel', 'epg', 'infradomains', 'interface',
                     'tenant']
        completions = [a for a in show_args if a.startswith(line[5:])]
        return completions

    def complete_no(self, text, line, begidx, endidx):
        " Complete the negative command "
        args, num, last_arg = self.get_args_num_last(text, line)
        do_args = self.completenames('' if len(args) <= 1 else args[1])
        pos_args = self.filter_args(NOT_NO_ARGS, do_args)
        if num <= 1:
            return pos_args
        if args[1] in pos_args:
            try:
                compfunc = getattr(self, 'complete_' + args[1])
            except AttributeError:
                compfunc = self.completedefault
            return compfunc(text, line.partition(' ')[2], begidx, endidx)

    def do_no(self, *args):
        " Negate the command "
        pass

    def do_exit(self, args):
        " Exit the command mode "
        return -1

    def precmd(self, line):
        """precmd"""
        # Check for negative of the command (no in front)
        if line.strip()[0:len('no')] == 'no':
            line = line.strip()[len('no'):]
            self.negative = True
        else:
            self.negative = False

        if line.strip() == 'help':
            sys.stdout.write('%s\n' % self.__doc__)
            return ''
        cmd, arg, line = self.parseline(line)
        if arg == '?':
            cmds = self.completenames(cmd)
            if cmds:
                self.columnize(cmds)
                sys.stdout.write('\n')
            return ''
        return line

    def get_args_num_nth(self, text, line, nth='last'):
        """get_args_num_nth"""
        args = line.split()
        # the number of completed argument
        num_completed_arg = len(args) - 1 if text == args[len(args) - 1] else len(args)
        # the last completed argument
        first_cmd = args[0]
        last_cmd = args[num_completed_arg - 1]
        try:
            nth_cmd = args[nth]
        except (TypeError, IndexError):
            nth_cmd = args[num_completed_arg - 1]
        return args, num_completed_arg, first_cmd, nth_cmd, last_cmd

    def get_args_num_last(self, text, line):
        """get_args_num_last"""
        args = line.split()
        # the number of completed argument
        num_completed_arg = len(args) - 1 if text == args[len(args) - 1] else len(args)
        # the last completed argument
        last_completed_arg = args[num_completed_arg - 1]
        return args, num_completed_arg, last_completed_arg

    def get_completions(self, text, array):
        """get_completions"""
        if args == '':
            return array
        return [a for a in array if a.startswith(text)]

    def get_operator_port(self, line, arg):
        """get_operator_port"""
        line = line.split(' ')
        if arg in line:
            index = line.index(arg)
            return line[index + 1:index + 3]

    def filter_args(self, black_list, array):
        """filter_args"""
        if type(black_list) == str:
            black_list = black_list.split()
        return list(set(array) - set(black_list) & set(array))


class BridgeDomainConfigSubMode(SubMode):
    """
    Bridge domain configuration sub mode
    """

    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-bd)#
        """
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-bd)# '

    def do_ip(self, args):
        """ IP subnet creation\nip address <ip-address>/<mask> """
        args = args.split()
        if len(args) <= 1:
            print('%% ip command requires the following '
                  'format: ip address <ip-address>/<mask>')
            return
        elif len(args) > 2:
            print('%% ip command requires the following '
                  'format: ip address <ip-address>/<mask>')
            return
        if args[0] == 'address':
            subnet_name = args[1].replace('/', ':')
            subnet = Subnet(subnet_name, self.bridgedomain)
            subnet.set_addr(args[1])

            if self.negative:
                print('Executing delete subnet command')
                self.bridgedomain.remove_subnet(subnet)
                subnet.mark_as_deleted()
            else:
                print('Executing create subnet command')
                self.bridgedomain.add_subnet(subnet)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)

    def complete_ip(self, text, line, begidx, endidx):
        """ip"""
        # TODO: need to replace the "get_ip_mask" function
        def get_ip_mask():
            """get ip mask"""
            # return ['ip_mask_1', 'ip_mask_2']
            pass

        args, num, first_cmd, nth_cmd, last_cmd = self.get_args_num_nth(text, line, 1)

        if first_cmd == 'ip':
            if num == 1:
                return self.get_completions(text, ['address'])
            elif nth_cmd == 'address':
                if num == 2:
                    return self.get_completions(text, get_ip_mask())
                elif num == 3:
                    return self.get_completions(text, ['name'])

    def do_context(self, args):
        """context"""
        context = Context(args, self.tenant)
        if self.negative:
            print('Bridgedomain to Context assignment cannot be deleted,'
                  ' only reassigned to another Context')
            return
        else:
            self.bridgedomain.add_context(context)
        resp = self.apic.push_to_apic(self.tenant.get_url(),
                                      self.tenant.get_json())
        if not resp.ok:
            error_message(resp)

    def complete_context(self, text, line, begidx, endidx):
        """context"""
        # TODO: need to replace the "get_context" function
        def get_context():
            """get context"""
            # return ['context_1', 'context_2']
            pass

        args, num, first_cmd, nth_cmd, last_cmd = self.get_args_num_nth(text, line, 1)

        if first_cmd == 'context' and num == 1:
            return self.get_completions(text, get_context())


class ContextConfigSubMode(SubMode):
    """
    Context domain configuration sub mode
    """

    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-ctx)#
        """
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-ctx)# '

    def do_allowall(self, args):
        """do_allowall"""
        if self.negative:
            self.context.set_allow_all(False)
        else:
            self.context.set_allow_all(True)
        resp = self.apic.push_to_apic(self.tenant.get_url(),
                                      self.tenant.get_json())
        if not resp.ok:
            error_message(resp)
        else:
            print('push configuration to APIC')

    def do_getjson(self, args):
        """do_getjson"""
        print(self.context.get_json())


class InterfaceConfigSubMode(SubMode):
    """Interface configuration submode"""
    def __init__(self):
        SubMode.__init__(self)
        self.tenant = None
        self.set_prompt()
        self.negative = False
        self.apic = None
        self.intf = None

    def do_epg(self, args):
        """ Endpoint Group assignment
            \tepg <app-name>/<epg-name> [vlan <vlanid>]
        """
        num_args = len(args.split())
        if num_args == 0:
            print('%% epg called with no epg-name')
            return
        if self.tenant is None:
            print('%% epg requires switchto tenant')
            return
        if self.negative:
            print('Removing epg from interface')
            raise NotImplementedError
        else:
            args = args.split()
            encap_present = False
            encap_type = None
            encap_id = None
            try:
                encap_present = True
                encap_type = args[1]
                encap_id = args[2]
            except:
                print('%% Improper encap specified')
                return
            try:
                (app_name, epg_name) = args[0].split('/')
            except:
                print('%% epg called with misformed name.')
                print('%% Proper format is epg <app-name>/<epg-name>')
                return
            print('Adding epg to interface')
            app = AppProfile(app_name, self.tenant)
            epg = EPG(epg_name, app)
            l2if_name = '%s-%s-%s' % (self.intf.name, encap_type, encap_id)
            l2if = L2Interface(l2if_name, encap_type, encap_id)
            l2if.attach(self.intf)
            epg.attach(l2if)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)

    def complete_epg(self, text, line, begidx, endidx):
        """epg"""
        # TODO: need to replace the five "get" functions
        def get_epg_name():
            """get epg name"""
            # return ['epg_1', 'epg_2']
            pass

        def get_vlan_id():
            """get vlan id"""
            # return ['vlan_id_1', 'vlan_id_2']
            pass

        def get_vnid():
            """get vnid"""
            # return ['vnid_1', 'vnid_2']
            pass

        def get_mcast_addr():
            """get mcast addr"""
            # return ['mcast_addr_1', 'mcast_addr_2']
            pass

        def get_vsid():
            """get vsid"""
            # return ['vsid_1', 'vsid_2']
            pass

        args, num, first_cmd, nth_cmd, last_cmd = self.get_args_num_nth(text, line, 2)

        if nth_cmd == 'vlan':
            if num == 3:
                return self.get_completions(text, get_vlan_id())
        elif nth_cmd == 'vxlan':
            if num == 3:
                return self.get_completions(text, get_vnid())
            if num == 4:
                return self.get_completions(text, get_mcast_addr())
        elif nth_cmd == 'nvgre':
            if num == 3:
                return self.get_completions(text, get_vsid())
        elif last_cmd == 'epg':
            if num == 1:
                return self.get_completions(text, get_epg_name())
        elif first_cmd == 'epg':
            if num == 2:
                return self.get_completions(text, ['vlan', 'vxlan', 'nvgre'])

    def do_shutdown(self, args):
        """shutdown"""
        num_args = len(args.split())
        if num_args:
            print('%% shutdown takes no arguments')
            return
        if self.negative:
            self.intf.adminstatus = 'up'
        else:
            self.intf.adminstatus = 'down'
        (phys_domain_url, fabric_url, infra_url) = self.intf.get_url()
        phys_domain, fabric, infra = self.intf.get_json()
        resp = self.apic.push_to_apic(phys_domain_url, phys_domain)
        if not resp.ok:
            error_message(resp)
        if fabric is not None:
            resp = self.apic.push_to_apic(fabric_url, fabric)
            if not resp.ok:
                error_message(resp)
        resp = self.apic.push_to_apic(infra_url, infra)
        if not resp.ok:
            error_message(resp)

    def do_speed(self, args):
        """ Interface speed assignment
            \tspeed <speed-value>
            Valid speed values: 100M, 1G, 10G, 40G
        """
        num_args = len(args.split())
        if num_args != 1:
            print('%% speed called with invalid format')
            print('%% Proper format is speed <speed-value>')
            return
        speed = args.upper()
        if speed not in ('100M', '1G', '10G', '40G'):
            print('%% Valid speed values are 100M, 1G, 10G, and 40G')
            return
        if self.negative:
            print('Reverting to default speed (10G)')
            speed = '10G'
        self.intf.speed = speed

        (phys_domain_url, fabric_url, infra_url) = self.intf.get_url()
        phys_domain, fabric, infra = self.intf.get_json()
        resp = self.apic.push_to_apic(phys_domain_url, phys_domain)
        if not resp.ok:
            error_message(resp)
        if fabric is not None:
            resp = self.apic.push_to_apic(fabric_url, fabric)
            if not resp.ok:
                error_message(resp)
        resp = self.apic.push_to_apic(infra_url, infra)
        if not resp.ok:
            error_message(resp)

    def do_ip(self):
        """ip"""
        pass

    def complete_ip(self, text, line, begidx, endidx):
        """ip"""
        # TODO: need to replace the five "get" functions
        def get_ip_mask():
            """get ip mask"""
            # return ['ip_mask_1', 'ip_mask_2']
            pass

        def get_context():
            """get context"""
            # return ['context_1', 'context_2']
            pass

        def get_area_id():
            """get area id"""
            # return ['area_id_1', 'area_id_2']
            pass

        def get_key_id():
            """get key id"""
            # return ['key_id_1', 'key_id_2']
            pass

        def get_auth_key():
            """get_auth_key"""
            # return ['auth_key_1', 'auth_key_2']
            pass

        args, num, first_cmd, nth_cmd, last_cmd = self.get_args_num_nth(text, line, 1)
        if last_cmd == 'ip':
            return self.get_completions(text, ['address', 'router', 'ospf'])
        elif nth_cmd == 'address':
            if num == 2:
                return self.get_completions(text, get_ip_mask())
        elif nth_cmd == 'router':
            if num == 2:
                return self.get_completions(text, ['ospf'])
            if num == 3:
                return self.get_completions(text, get_context())
            if num == 4:
                return self.get_completions(text, ['area'])
            if num == 5:
                return self.get_completions(text, get_area_id())
        elif nth_cmd == 'ospf':
            if num == 2:
                return self.get_completions(text, ['authentication', 'message-digest-key'])
            if num == 3:
                if last_cmd == 'authentication':
                    return self.get_completions(text, ['message-digest-key'])
                if last_cmd == 'message-digest-key':
                    return self.get_completions(text, get_key_id())
            if num == 4:
                return self.get_completions(text, ['mad5'])
            if num == 5:
                return self.get_completions(text, get_auth_key())

    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-if)#
        """
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-if)# '


class ConfigSubMode(SubMode):
    """Configuration submode"""
    def __init__(self):
        SubMode.__init__(self)
        self.tenant = None
        self.set_prompt()
        self.negative = False
        self.apic = None
        self.bridgedomain_submode = BridgeDomainConfigSubMode()
        self.context_submode = ContextConfigSubMode()
        self.app_submode = AppProfileConfigSubMode()
        self.contract_submode = ContractConfigSubMode()
        self.interface_submode = InterfaceConfigSubMode()

    def set_prompt(self):
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config)# '

    def set_apic(self, apic):
        """set the apic"""
        self.apic = apic
        self.bridgedomain_submode.apic = apic
        self.context_submode.apic = apic
        self.contract_submode.apic = apic
        self.app_submode.apic = apic
        self.app_submode.epg_submode.apic = apic
        self.interface_submode.apic = apic

    def do_tenant(self, args):
        " Tenant Creation\ttenant <tenant-name> "
        if len(args.split()) > 1:
            print('%% tenant must be called with 1 tenant-name\n')
            return
        if len(args.split()) == 0:
            print('%% tenant called with no tenant-name\n')
            return
        tenant = Tenant(args.strip())
        if self.negative:
            print('Executing delete tenant command\n')
            tenant.mark_as_deleted()
        else:
            sys.stdout.write('Executing create tenant command\n')
        resp = self.apic.push_to_apic(tenant.get_url(), tenant.get_json())

    def do_bridgedomain(self, args):
        " Bridge Domain Creation\tbridge-domain <bridge-domain-name> "
        if len(args.split()) > 1:
            print('%% bridge-domain requires only 1 name')
            return
        if self.tenant is None:
            print('%% bridge-domain requires switchto tenant')
            return
        bridgedomain = BridgeDomain(args.strip(), self.tenant)
        if self.negative:
            print('Executing delete bridgedomain command')
            bridgedomain.mark_as_deleted()
        else:
            print('Executing create bridgedomain command')
        resp = self.apic.push_to_apic(self.tenant.get_url(),
                                      self.tenant.get_json())
        if not self.negative:
            self.bridgedomain_submode.tenant = self.tenant
            self.bridgedomain_submode.bridgedomain = bridgedomain
            self.bridgedomain_submode.set_prompt()
            self.bridgedomain_submode.cmdloop()

    def complete_bridgedomain(self, text, line, begidx, endidx):
        """bridgedomain"""
        bridgedomain_args = [a for a in self.do_show('bridgedomain',
                                                     to_return=True).values()[0]]
        completions = [a for a in bridgedomain_args if a.startswith(line[13:])]
        return completions

    def do_context(self, args):
        " Context Creation\tcontext <context-name> "
        if len(args.split()) == 0:
            print('%% context requires a name')
            return
        elif len(args.split()) > 1:
            print('%% context requires only 1 name')
            return
        if self.tenant is None:
            print('%% context requires switchto tenant')
            return
        context = Context(args.strip(), self.tenant)
        context.set_allow_all(False)
        if self.negative:
            print('Executing delete context command')
            context.mark_as_deleted()
        else:
            print('Executing create context command')
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                self.context_submode.tenant = self.tenant
                self.context_submode.context = context
                self.context_submode.set_prompt()
                self.context_submode.cmdloop()

    def do_interface(self, args):
        """Interface Configuration
           interface eth <pod>/<node>/<module>/<port>
           interface port-channel <port>
        """
        if len(args.split()) > 2:
            sys.stdout.write('%% Invalid interface name\n')
            return
        if self.negative:
            pass  # only relevant for port-channels
        else:
            print('Executing interface command')
            name = args.strip()
            try:  # Physical Interface
                (if_type, pod, node, module, port) = Interface.parse_name(name)
                intf = Interface(if_type, pod, node, module, port)
                self.interface_submode.tenant = self.tenant
                self.interface_submode.intf = intf
                self.interface_submode.set_prompt()
                self.interface_submode.cmdloop()
            except ValueError:  # Port Channel
                interface_type = args.split()[0]
                if interface_type != 'port-channel':
                    sys.stdout.write('%% Invalid interface name\n')
                    return
                port = args.split()[1]

                portchannels = PortChannel.get(self.apic)
                return
                try:
                    for pc in portchannels:
                        print(pc)
                    return
                except:
                    return

    def do_tag(self, args):
        " tag creation <tag-name>"
        if len(args.split()) > 1 or len(args.split()) == 0:
            print('%% tag requires 1 name\n')
            return
        if self.tenant is None:
            print('%% tag requires switchto tenant\n')
            return
        if self.negative:
            print('Executing delete tag command\n')
            self.tenant.add_tag(args.strip())
            self.tenant.delete_tag(args.strip())
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
        else:
            print('Executing create tag command')
            self.tenant.add_tag(args.strip())
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            # else:
            #     self.cmdloop()

    def do_app(self, args):
        " Application Profile Creation\tapp <app-profile-name> "
        if len(args.split()) > 1 or len(args.split()) == 0:
            print('%% app requires 1 name\n')
            return
        if self.tenant is None:
            print('%% app requires switchto tenant\n')
            return
        if self.negative:
            print('Executing delete app command\n')
            app = AppProfile(args.strip(), self.tenant)
            app.mark_as_deleted()
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
        else:
            print('Executing create app command')
            app = AppProfile(args.strip(), self.tenant)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                self.app_submode.tenant = self.tenant
                self.app_submode.set_prompt()
                self.app_submode.app = app
                self.app_submode.cmdloop()

    def do_contract(self, args):
        " Contract Creation\tcontract <contract-name> "
        if len(args.split()) > 1:
            sys.stdout.write('%% contract requires only 1 name\n')
            return
        if self.tenant is None:
            sys.stdout.write('%% contract requires switchto tenant\n')
            return
        if self.negative:
            contract = Contract(args.strip(), self.tenant)
            contract.mark_as_deleted()
            print('Deleting Contract')
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                print('Deleted contract')
        else:
            print('Executing create contract command')
            contract = Contract(args.strip(), self.tenant)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                self.contract_submode.tenant = self.tenant
                self.contract_submode.set_prompt()
                self.contract_submode.contract = contract
                self.contract_submode.cmdloop()

    def do_exit(self, args):
        " Exit the Configuration submode "
        return -1


class EPGConfigSubMode(SubMode):

    """
    Endpoint Group configuration sub mode
    """

    def __init__(self):
        SubMode.__init__(self)

    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-epg)#
        """
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-epg)# '

    def do_tag(self, args):
        " Create tag <tag-name>"
        if len(args.split()) != 1:
            sys.stdout.write('%% tag requires 1 name\n')
            return
        if self.negative:
            print('Executing delete tag command\n')
            self.epg.add_tag(args.strip())
            #print(self.epg.has_tags())
            self.epg.delete_tag(args.strip())
            #print ('JSON:', self.tenant.get_json())
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            #resp = self.tenant.push_to_apic(self.apic)
            if not resp.ok:
                error_message(resp)
        else:
            print('Executing create tag command')
            self.epg.add_tag(args.strip())
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)


    def do_bridgedomain(self, args):
        " Bridge Domain\tbridge-domain <bridge-domain-name> "
        if len(args.split()) != 1:
            sys.stdout.write('%% bridge-domain requires 1 name\n')
            return
        if self.negative:
            pass
        else:
            bridgedomain = BridgeDomain(args.strip(), self.tenant)
            self.epg.add_bd(bridgedomain)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                print('Assigned bridgedomain to EPG.')

    def do_infradomain(self, args):
        " Infrastructure Domain\infradomain <infra-domain-name> "

        if len(args.split()) != 1:
            sys.stdout.write('%% infradomain requires 1 name\n')
            return
        if self.negative:
            pass
        else:
            epgdomain = EPGDomain.get_by_name(self.apic, args.strip())

            if epgdomain is None:
                sys.stdout.write('%% infradomain does not exist. You need to create one first! "show infradomains"\n')
                return

            self.epg.add_infradomain(epgdomain)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())

            if not resp.ok:
                error_message(resp)
            else:
                print('Assigned Infrastructure Domain to EPG.')


class AppProfileConfigSubMode(SubMode):

    """
    Application Profile configuration sub mode
    """

    def __init__(self):
        SubMode.__init__(self)
        self.epg_submode = EPGConfigSubMode()
        # self.app = None

    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-app)#
        """
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-app)# '

    def do_epg(self, args):
        " Endpoint Group Creation\tepg <epg-name> "
        if len(args.split()) > 1:
            sys.stdout.write('%% epg must be called with 1 epg-name\n')
            return
        if len(args.split()) == 0:
            sys.stdout.write('%% epg called with no epg-name\n')
            return
        if self.negative:
            print('Executing delete epg command')
            epg = EPG(args.strip(), self.app)
            epg.mark_as_deleted()
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
        else:
            print('Executing create epg command')
            epg_name = args.strip()
            epg = EPG(epg_name, self.app)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                self.epg_submode.tenant = self.tenant
                self.epg_submode.set_prompt()
                self.epg_submode.app = self.app
                self.epg_submode.epg = epg
                self.epg_submode.cmdloop()


class ContractConfigSubMode(SubMode):

    """
    Contract configuration sub mode
    """

    def __init__(self):
        SubMode.__init__(self)
        self.entry_name = None
        self.sequence_number = None
        self.aa = 0
        self.operators = ['lt', 'gt', 'eq', 'neq', 'range']
        self.permit_args = ['eigrp', 'gre', 'icmp', 'igmp', 'igrp', 'ip', 'ipinip', 'nos', 'ospf', 'pim', 'tcp', 'udp']
        self.scope_args = ['context', 'global', 'tenant', 'application-profile']

    def do_scope(self, args):
        """scope"""
        if self.negative is True:
            print('You can not delete contract scope')
            return
        if args.split()[0] not in self.scope_args:
            print('%% Unknown scope. Valid values are: ' + str(self.scope_args))
            return
        self.contract.set_scope(args.split()[0])
        print('contract scope set to ' + str(self.contract.get_scope()))

    def complete_scope(self, text, line, begidx, endidx):
        """complete_scope"""
        text = text.lstrip()
        return self.get_completions(text, self.scope_args)

    def do_permit(self, args):
        """permit"""
        def check_from_to_args(args, cmd):
            """check_from_to_args"""
            if cmd in args:
                idx = args.index(cmd)
                try:
                    oprt = args[idx + 1]
                    if oprt not in self.operators:
                        print('Error, invalid Operator.')
                        return
                    port = args[idx + 2: idx + 4 if oprt == 'range' else idx + 3]
                except IndexError:
                    print('too few arguemnts.')
                    return
                if oprt == 'range':
                    pass
                elif oprt == 'lt':
                    port.insert(0, '1')
                elif oprt == 'gt':
                    port.insert(1, 65535)
                elif oprt == 'eq':
                    port.insert(0, args[idx + 3])
                return port
            else:
                return [0, 0]

        def check_tcp_rule(args):
            """check tcp rule"""
            def check_name(args, sign):
                """ check name """
                idx = args.index(sign)
                try:
                    return [sign, args[idx + 1]]
                except IndexError:
                    print('Error, tcp rule is not defined.')
            if ('+') in args:
                return check_name(args, '+')[1]
            elif ('-') in args:
                return 'unspecified'

        args = args.split()
        if args[0] == 'arp':
            arp_arg = 0
            if len(args) > 2:
                print('%% arp takes one arguments, %s are given\n' % len(args))
                return
            elif len(args) <= 1:
                print('Invalid argument. Default value ' + str(arp_arg) + ' is applied.')
            else:
                if args[1] in ['request', '1', 1]:
                    arp_arg = 1
                elif args[1] in ['reply', '2', 2]:
                    arp_arg = 2
            FilterEntry(str(self.sequence_number),
                        self.contract,
                        arpOpc=str(arp_arg),
                        etherT='arp')
        elif args[0] == 'ethertype':
            if len(args) != 2:
                print('%% ethertype must be called with 1 ethertype number\n')
            else:
                FilterEntry(str(self.sequence_number),
                            self.contract,
                            etherT=str(args[1]))
        elif args[0] in self.permit_args + ['unspecified'] and args[0] not in ['tcp', 'udp']:
            apply_fra = 'false'
            if args[len(args) - 1] == 'fragment':
                apply_fra = 'true'
            FilterEntry(str(self.sequence_number),
                        self.contract,
                        etherT='ip',
                        prot=args[0],
                        applyToFrag=str(apply_fra))
        elif args[0] in ['tcp', 'udp']:
            out_put = [self.negative, self.sequence_number, args[0]]
            from_arg = check_from_to_args(args, 'from-port')
            to_arg = check_from_to_args(args, 'to-port')
            tcp_rule = '0'
            if args[0] == 'tcp':
                tcp_rule = check_tcp_rule(args)
            FilterEntry(str(self.sequence_number),
                        self.contract,
                        etherT='ip',
                        prot=args[0],
                        dFromPort=str(to_arg[0]),
                        dToPort=str(to_arg[1]),
                        sFromPort=str(from_arg[0]),
                        sToPort=str(from_arg[1]),
                        tcpRules=tcp_rule)

        resp = self.apic.push_to_apic(self.tenant.get_url(),
                                      self.tenant.get_json())
        if not resp.ok:
            error_message(resp)

    def complete_permit(self, text, line, begidx, endidx):
        """
        complete permit
        """
        signs = ['+', '-']
        protocol_args = ['from-port', 'to-port']
        tcp_rule_array = ['unspecified', 'est', 'syn', 'ack', 'fin', 'rst']

        args, num, first_cmd, nth_cmd, cmd = self.get_args_num_nth(text, line)
        if cmd == 'permit':
            return self.get_completions(text, self.permit_args + ['arp', 'ethertype'])
        elif cmd == 'ethertype':
            if num == 2:
                ethertype_args = ['unspecified', 'trill', 'arp', 'mpls_ucast', 'mac_security', 'fcoe', 'ip', 'DEFAULT']
                return self.get_completions(text, ethertype_args)
        elif cmd == 'arp':
            if num == 2:
                arp_args = ['unspecified', 'reply', 'request', 'DEFAULT']
                return self.get_completions(text, arp_args)
        elif cmd in self.permit_args and cmd not in ['tcp', 'udp']:
            return ['fragment']
        elif cmd in ['tcp', 'udp'] or cmd.isdigit() or cmd in tcp_rule_array:
            return self.get_completions(text, self.filter_args(line, protocol_args + signs if args[1] == 'tcp' else protocol_args))
        elif cmd in ['+', '-'] and num > 2 and args[1] == 'tcp':
            return self.get_completions(text, tcp_rule_array)
        elif cmd in protocol_args and num > 2:
            return self.get_completions(text, self.operators)

    def complete_sequence_number(self, text, line, begidx, endidx, with_do_args=True):
        """
        Complete the sequence number
        """
        # TODO: Bon we need a get method to obtain the array.
        def get_seq_nums():
            """
            Get sequence numbers
            """
            # return ['123', '456', '789', '100']
            return []

        do_array = self.completenames(text) if with_do_args else []
        pos_args = self.get_completions(text, get_seq_nums() + do_array)
        if 'permit' in pos_args:
            pos_args.remove('permit')
        return pos_args

    def completedefault(self, text, line, begidx, endidx):
        return SubMode.complete_no(self, text, line, begidx, endidx)

    def complete(self, text, state):
        """
        overwrite the origin complete function, but only change one line:
        self.completenames => self.complete_sequence_number
        """
        if state == 0:
            import readline
            origline = readline.get_line_buffer()
            line = origline.lstrip()
            stripped = len(origline) - len(line)
            begidx = readline.get_begidx() - stripped
            endidx = readline.get_endidx() - stripped
            if begidx > 0:
                cmd, args, _ = self.parseline(line)
                if cmd == '':
                    compfunc = self.completedefault
                else:
                    try:
                        compfunc = getattr(self, 'complete_' + cmd)
                    except AttributeError:
                        compfunc = self.completedefault
            else:
                compfunc = self.complete_sequence_number
            self.completion_matches = compfunc(text, line, begidx, endidx)
        try:
            return self.completion_matches[state]
        except IndexError:
            return None

    def complete_no(self, text, line, begidx, endidx):
        args, num, last = self.get_args_num_last(text, line)
        if num == 1:
            pos_args = self.complete_sequence_number(text, line, begidx, endidx, with_do_args=False)
            return self.get_completions(text, pos_args + ['scope'])
        elif num == 2:
            if args[1] == 'scope':
                return self.complete_scope(text, line.partition(' ')[2].partition(' ')[2], begidx, endidx)
            elif 'permit'.startswith(text):
                return ['permit']
        elif num >= 3 and args[2] == 'permit':
            return self.complete_permit(text, line.partition(' ')[2].partition(' ')[2], begidx, endidx)

    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-contract)#
        """
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-contract)# '

    def precmd(self, line, check_no=False):
        # Check for negative of the command (no in front)
        if line.strip()[0:len('no ')] == 'no ':
            line = line.strip()[len('no'):]
            self.negative = True
        else:
            self.negative = False

        if line.strip() == 'help':
            sys.stdout.write('%s\n' % self.__doc__)
            return ''

        cmd, arg, line = self.parseline(line)

        # to achieve the sequence_number of the subject.
        try:
            self.sequence_number = int(cmd)
            cmd, arg, line = self.parseline(arg)
        except (ValueError, TypeError):
            pass

        if arg == '?':
            cmds = self.completenames(cmd)
            if cmds:
                self.columnize(cmds)
                sys.stdout.write('\n')
            return ''
        return line


class CmdLine(SubMode):

    """
    Help is available through '?'
    """

    def __init__(self):
        Cmd.__init__(self)
        self.apic = apic
        if not READLINE:
            self.completekey = None
        self.tenant = None
        self.app = None
        self.epg = None
        self.set_prompt()
        self.intro = ('\nCisco ACI Toolkit Command Shell\nCopyright (c)'
                      ' 2015, Cisco Systems, Inc.  All rights reserved.')
        self.negative = False
        self.configsubmode = ConfigSubMode()
        self.configsubmode.set_apic(apic)

    def set_prompt(self):
        self.prompt = 'fabric'
        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '# '

    def default(self, line):
        cmd, arg, line = self.parseline(line)
        cmds = self.completenames(cmd)
        num_cmds = len(cmds)
        print(cmds)
        if num_cmds == 1:
            getattr(self, 'do_' + cmds[0])(arg)
        elif num_cmds > 1:
            sys.stdout.write('%% Ambiguous command:\t"%s"\n' % cmd)
        else:
            sys.stdout.write('% Unrecognized command\n')

    def do_help(self, arg):
        doc_strings = [(i[3:], getattr(self, i).__doc__)
                       for i in dir(self) if i.startswith('do_')]
        doc_strings = ['  {!s:12}\t{!s}\n'.format(i, j)
                       for i, j in doc_strings if j is not None]
        sys.stdout.write('Commands:\n%s\n' % ''.join(doc_strings))

    def completedefault(self, text, line, begidx, endidx):
        print('text:', text, 'line:', line,
              'begidx:', begidx, 'endidx:', endidx)

    def do_configure(self, args):
        " Enter the Configuration submode "
        if self.negative:
            return
        self.configsubmode.tenant = self.tenant
        self.configsubmode.set_prompt()
        self.configsubmode.cmdloop()

    def do_switchto(self, args):
        " Switch to a particular tenant "
        if self.negative:
            return
        if len(args.split()) > 1 or len(args.split()) == 0:
            sys.stdout.write('%% switchto tenant requires 1 tenant-name\n')
            return
        tenant = Tenant(args.strip())
        if Tenant.exists(self.apic, tenant):
            self.tenant = Tenant(args.strip())
            self.set_prompt()
        else:
            print('%% Tenant %s does not exist' % tenant.name)

    def complete_switchto(self, text, line, begidx, endidx):
        """
        Switch to a particular tenant
        :return: List of possible tenants for completions
        """
        switchto_args = [a for a in self.do_show('tenant',
                                                 to_return=True).keys()]
        completions = [a for a in switchto_args if a.startswith(line[9:])]
        return completions

    def do_switchback(self, args):
        " Switch back out of a particular tenant "
        if len(args.split()) > 0:
            sys.stdout.write('%% switchback has no extra parameters\n')
            return
        self.tenant = None
        self.set_prompt()

    def do_exit(self, args):
        " Exit the Configuration submode "
        return -1

    def complete_configure(self, text, line, begidx, endidx):
        """
        Complete the configuration commands
        :return: List of strings that can be completed
        """
        completions = ['terminal']
        return completions


class MockStdin(object):
    """
    Mock of the Stdin
    """
    def __init__(self, filename, original_stdin):
        self.original_stdin = original_stdin
        f = open(filename)
        self.lines = f.readlines()
        f.close()

    def readline(self):
        """
        Mock reading a single line from stdin
        :return: String containing the line
        """
        line = self.lines.pop(0)
        print(line)
        if len(self.lines) == 0:
            sys.stdin = self.original_stdin
        return line


def main(apic):
    """
    Main execution routine

    :param apic: Instance of Session class
    """
    cmdLine = CmdLine()
    cmdLine.apic = apic
    cmdLine.cmdloop()


# *** MAIN LOOP ***
if __name__ == '__main__':
    LOGIN = ''
    PASSWORD = ''
    URL = ''
    OUTPUTFILE = ''
    DEBUGFILE = None
    DEBUGLEVEL = logging.CRITICAL
    usage = ('Usage: acitoolkitcli.py -l <login> -p <password> -u <url> '
             '[-o <output-file>] [-t <test-file>]')
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hl:p:u:do:f:t:",
                                   ["help", "apic-login=", "apic-password=",
                                    "apic-url=", "enable-debug",
                                    "output-file=", "debug-file=",
                                    "test-file="])
    except getopt.GetoptError:
        print(str(sys.argv[0]) + ' : illegal option')
        print(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(usage)
            sys.exit()
        elif opt in ('-l', '--apic-login'):
            LOGIN = arg
        elif opt in ('-p', '--apic-password'):
            PASSWORD = arg
        elif opt in ('-u', '--apic-url'):
            URL = arg
        elif opt in ('-o', '--output-file'):
            OUTPUTFILE = arg
        elif opt in ('-d', '--enable-debug'):
            DEBUGLEVEL = logging.DEBUG
        elif opt in ('-f', '--debug-file'):
            DEBUGFILE = arg
        elif opt in ('-t', '--test-file'):
            TESTFILE = arg

    if URL == '' or LOGIN == '' or PASSWORD == '':
        print(usage)
        sys.exit(2)

    logging.basicConfig(format=('%(levelname)s:[%(module)s:'
                                '%(funcName)s]:%(message)s'),
                        filename=DEBUGFILE, filemode='w',
                        level=DEBUGLEVEL)

    apic = Session(URL, LOGIN, PASSWORD)
    try:
        apic.login()
    except requests.exceptions.ConnectionError:
        print('%% Could not connect to APIC.')
        sys.exit(2)
    except requests.exceptions.MissingSchema:
        print('%% Invalid URL.')
        sys.exit(2)

    if 'TESTFILE' in locals():
        sys.stdin = MockStdin(TESTFILE, sys.stdin)

    try:
        main(apic)
    except KeyboardInterrupt:
        pass
