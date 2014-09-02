"""This module implements a CLI similar to Cisco IOS and NXOS
   for use with the ACI Toolkit.
"""
import re
import sys
import getopt
import logging
from cmd import Cmd
from acitoolkit import *
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
    print 'Error:  Unable to push configuration to APIC'
    print 'Reason:', resp.text


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

    def do_show(self, args, to_return=False):
        """Show running system information"""
        detail = False
        words = args.strip().split(' ')
        if len(words) > 1:
            if words[1] == 'detail':
                detail = True
        temp = self.complete_show('', 'show '+args, 0, 0)
        if len(temp) == 1:
            words[0] = temp[0]

        if words[0] == 'tenant':
            tenants = Tenant.get(self.apic)
            tenant_dict = {}
            for tenant in tenants:
                tenant_dict[tenant.name] = []
            if to_return:
                return tenant_dict
            print 'Tenant'
            print '------'
            for tenant in tenants:
                print tenant.name
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
            print template.format('Tenant', 'BridgeDomain')
            print template.format('------', '------------')
            for rec in output:
                print template.format(*rec)
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
            print template.format('Tenant', 'Context')
            print template.format('------', '-------')
            for rec in output:
                print template.format(*rec)
        elif words[0] == 'contract':
            raise NotImplementedError
        elif words[0] == 'interface':
            ifs = Interface.get(self.apic)
            print 'Interface\tType\tStatus\tSpeed\tMTU'
            for interface in ifs:
                print interface
        elif words[0] == 'port-channel':
            portchannels = PortChannel.get(self.apic)
            print 'Port Channel'
            print '------------'
            for pc in portchannels:
                print pc
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
            print template.format('Tenant', 'App Profile')
            print template.format('------', '-----------')
            for rec in output:
                print template.format(*rec)
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
        else:
            sys.stdout.write('%% Unrecognized command\n')

    def emptyline(self):
        pass

    def complete_show(self, text, line, begidx, endidx):
        show_args = ['bridgedomain', 'context', 'contract', 'app',
                     'port-channel', 'epg', 'interface', 'tenant']
        completions = [a for a in show_args if a.startswith(line[5:])]
        return completions

    def complete_no(self, text, line, begidx, endidx):
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
        pass

    def do_exit(self, args):
        " Exit the command mode "
        return -1

    def precmd(self, line):

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
        
    def get_args_num_last(self, text, line):
        args = line.split()
        # the number of completed argument
        num_completed_arg = len(args) - 1 if text == args[len(args)-1] else len(args)
        # the last completed argument
        last_completed_arg = args[num_completed_arg-1]
        return args, num_completed_arg, last_completed_arg
    
    def get_completions(self, text, array):
        if args == '':
            return array
        return [a for a in array if a.startswith(text)]
    
    def get_operator_port(self, line, arg):
        line = line.split(' ')
        if arg in line:
            index = line.index(arg)
            return line[index+1:index+3]
    
    def filter_args(self, line, array):
        return list(set(array) - set(line.split()) & set(array))


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
                print 'Executing delete subnet command'
                self.bridgedomain.remove_subnet(subnet)
                subnet.mark_as_deleted()
            else:
                print 'Executing create subnet command'
                self.bridgedomain.add_subnet(subnet)
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)

    def complete_ip(self, text, line, begidx, endidx):
        line = re.sub('\s+', ' ', line)
        ip_args = ['address']
        num_args = line.count(' ')
        if num_args == 1:
            completions = ip_args
        elif num_args == 2:
            completions = [a for a in [a.get_addr() for a in self.bridgedomain.get_subnets()] if a.startswith(line[11:])]
        elif num_args == 3:
            completions = ['name']
        else:
            completions = ''
        return completions

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
        if self.negative:
            self.context.set_allow_all(False)
        else:
            self.context.set_allow_all(True)
        resp = self.apic.push_to_apic(self.tenant.get_url(),
                                      self.tenant.get_json())
        if not resp.ok:
            error_message(resp)
        else:
            print 'push configuration to APIC'

    def do_getjson(self, args):
        print self.context.get_json()


class InterfaceConfigSubMode(SubMode):
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
            print '%% epg called with no epg-name'
            return
        if self.tenant is None:
            print '%% epg requires switchto tenant'
            return
        if self.negative:
            print 'Removing epg from interface'
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
                print '%% Improper encap specified'
                return
            try:
                (app_name, epg_name) = args[0].split('/')
            except:
                print '%% epg called with misformed name.'
                print '%% Proper format is epg <app-name>/<epg-name>'
                return
            print 'Adding epg to interface'
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

    def do_shutdown(self, args):
        num_args = len(args.split())
        if num_args:
            print '%% shutdown takes no arguments'
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
            print '%% speed called with invalid format'
            print '%% Proper format is speed <speed-value>'
            return
        speed = args.upper()
        if speed not in ('100M', '1G', '10G', '40G'):
            print '%% Valid speed values are 100M, 1G, 10G, and 40G'
            return
        if self.negative:
            print 'Reverting to default speed (10G)'
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
        self.apic = apic
        self.bridgedomain_submode.apic = apic
        self.context_submode.apic = apic
        self.app_submode.apic = apic
        self.app_submode.epg_submode.apic = apic
        self.interface_submode.apic = apic

    def do_tenant(self, args):
        " Tenant Creation\ttenant <tenant-name> "
        if len(args.split()) > 1:
            print '%% tenant must be called with 1 tenant-name\n'
            return
        if len(args.split()) == 0:
            print '%% tenant called with no tenant-name\n'
            return
        tenant = Tenant(args.strip())
        if self.negative:
            print 'Executing delete tenant command\n'
            tenant.mark_as_deleted()
        else:
            sys.stdout.write('Executing create tenant command\n')
        resp = self.apic.push_to_apic(tenant.get_url(), tenant.get_json())

    def do_bridgedomain(self, args):
        " Bridge Domain Creation\tbridge-domain <bridge-domain-name> "
        if len(args.split()) > 1:
            print '%% bridge-domain requires only 1 name'
            return
        if self.tenant is None:
            print '%% bridge-domain requires switchto tenant'
            return
        bridgedomain = BridgeDomain(args.strip(), self.tenant)
        if self.negative:
            print 'Executing delete bridgedomain command'
            bridgedomain.mark_as_deleted()
        else:
            print 'Executing create bridgedomain command'
        resp = self.apic.push_to_apic(self.tenant.get_url(),
                                      self.tenant.get_json())
        if not self.negative:
            self.bridgedomain_submode.tenant = self.tenant
            self.bridgedomain_submode.bridgedomain = bridgedomain
            self.bridgedomain_submode.set_prompt()
            self.bridgedomain_submode.cmdloop()

    def complete_bridgedomain(self, text, line, begidx, endidx):
        bridgedomain_args = [a for a in self.do_show('bridgedomain',
                                                     to_return=True).values()[0]]
        completions = [a for a in bridgedomain_args if a.startswith(line[13:])]
        return completions

    def do_context(self, args):
        " Context Creation\tcontext <context-name> "
        if len(args.split()) == 0:
            print '%% context requires a name'
            return
        elif len(args.split()) > 1:
            print '%% context requires only 1 name'
            return
        if self.tenant is None:
            print '%% context requires switchto tenant'
            return
        context = Context(args.strip(), self.tenant)
        context.set_allow_all(False)
        if self.negative:
            print 'Executing delete context command'
            context.mark_as_deleted()
        else:
            print 'Executing create context command'
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
            print 'Executing interface command'
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

                portchannels = PortChannel.get2(self.apic)
                return
                try:
                    for pc in portchannels:
                        print pc
                    return
                except:
                    return

    def do_app(self, args):
        " Application Profile Creation\tapp <app-profile-name> "
        if len(args.split()) > 1 or len(args.split()) == 0:
            print '%% app requires 1 name\n'
            return
        if self.tenant is None:
            print '%% app requires switchto tenant\n'
            return
        if self.negative:
            print 'Executing delete app command\n'
            app = AppProfile(args.strip(), self.tenant)
            app.mark_as_deleted()
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
        else:
            print 'Executing create app command'
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
            print 'Deleting Contract'
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                print 'Deleted contract'
        else:
            print 'Executing create contract command'
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
                print 'Assigned bridgedomain to EPG.'


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
            print 'Executing delete epg command'
            epg = EPG(args.strip(), self.app)
            epg.mark_as_deleted()
            resp = self.apic.push_to_apic(self.tenant.get_url(),
                                          self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
        else:
            print 'Executing create epg command'
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
        self.seq_num_array = ['123', '456', '789', '100']  # TODO: Bon we need a get method to obtain the array.
        self.operators = ['lt', 'gt', 'eq', 'neq', 'range']
        self.permit_args = [ 'eigrp', 'gre', 'icmp', 'igmp', 'igrp', 'ip', 'ipinip', 'nos', 'ospf', 'pim', 'tcp', 'udp']

    def do_scope(self, args):
        if self.negative is True:
            print 'You can not delete contract scope'
            return
        self.contract.set_scope(args.split()[0])
        print 'contract scope change to be ', self.contract.get_scope()

    def complete_scope(self, text, line, begidx, endidx):
        text = text.lstrip()
        scope_args = ['context', 'global', 'tenant', 'application-profile']
        return self.get_completions(text, scope_args)

    def do_permit(self, args):

        def check_from_to_args(args, cmd):
            if cmd in args:
                idx = args.index(cmd)
                try:
                    oprt = args[idx+1]
                    if oprt not in self.operators:
                        print 'Error, invalid Operator.'
                        return
                    port = args[idx+2: idx+4 if oprt == 'range' else idx+3]
                except IndexError:
                    print 'too few arguemnts.'
                    return
                port.insert(0, oprt)
                port.insert(0, cmd)
                return port
            else:
                return [cmd]

        def check_flag_name(args):
            def check_name(args, sign):
                idx = args.index(sign)
                try:
                    return [sign, args[idx+1]]
                except IndexError:
                    print 'Error, flag name is not defined.'
            if ('+') in args:
                flag_sign = '+'
                return check_name(args, flag_sign)
            elif ('-') in args:
                flag_sign = '-'
                return check_name(args, flag_sign)

        args = args.split()
        if args[0] == 'arp':
            if len(args) > 2:
                print '%% arp takes one arguments, %s are given\n' % len(args)
                return
            arp_arg = 0
            if args[1] in ['request', '1', 1]:
                arp_arg = 1
            elif args[1] in ['response', '2', 2]:
                arp_arg = 2
            else:
                print 'Invalid argument. Default value', arp_arg, 'is applied.'
            print [self.negative, self.sequence_number, args[0], arp_arg]
        elif args[0] == 'ethertype':
            if len(args) != 2:
                print '%% ethertype must be called with 1 ethertype number\n'
            else:
                print [self.negative] + [self.sequence_number] + args
        elif args[0] in self.permit_args + ['unspecified'] and args[0] not in ['tcp', 'udp']:
            apply_fra = False
            if args[len(args)-1] == 'fragment':
                apply_fra = True
            print [self.negative, self.sequence_number, args[0], apply_fra]
        elif args[0] in ['tcp', 'udp']:
            out_put = [self.negative, self.sequence_number, args[0]]
            from_arg = check_from_to_args(args, 'from-port')
            to_arg = check_from_to_args(args, 'to-port')
            if args[0] == 'tcp':
                flag_name = check_flag_name(args)
                print out_put, from_arg, to_arg, flag_name
                return
            print out_put, from_arg, to_arg


    def complete_permit(self, text, line, begidx, endidx):
        signs = ['+', '-']
        protocol_args = ['from-port', 'to-port']

        args, num, cmd = self.get_args_num_last(text, line)
        if cmd == 'permit':
            return self.get_completions(text, self.permit_args+['arp', 'ethertype'])
        elif cmd == 'ethertype':
            if num == 2:
                ethertype_args = ['unspecified', 'trill', 'arp', 'mpls_ucast', 'mac_security', 'fcoe', 'ip', 'DEFAULT']
                return self.get_completions(text, ethertype_args)
        elif cmd == 'arp':
            if num == 2:
                arp_args = ['unspecified', 'response', 'request', 'DEFAULT']
                return self.get_completions(text, arp_args)
        elif cmd in self.permit_args and cmd not in ['tcp', 'udp']:
            return ['fragment']
        elif cmd in ['tcp', 'udp'] or cmd.isdigit():
            return self.get_completions(text, self.filter_args(line, protocol_args + signs if args[2] == 'tcp' else protocol_args))
        elif cmd in ['+', '-'] and num > 2 and args[1] == 'tcp':
            flag_name_array = ['unspecified', 'est', 'syn', 'ack', 'fin', 'rst']
            return self.get_completions(text, flag_name_array)
        elif cmd in protocol_args and num > 2:
            return self.get_completions(text, self.operators)

    def complete_sequence_number(self, text, line, begidx, endidx, with_do_args=True):
        do_array = self.completenames(text) if with_do_args else []
        pos_args = self.get_completions(text, self.seq_num_array+do_array)
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
            if begidx>0:
                cmd, args, foo = self.parseline(line)
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
            return [a for a in pos_args if a.startswith(text)]
        elif num == 2:
            if args[1] == 'scope':
                return self.complete_scope(text, line.partition(' ')[2], begidx, endidx)
            elif 'permit'.startswith(text):
                return ['permit']
        elif num >= 3 and args[2] == 'permit':
            return self.complete_permit(text, line.partition(' ')[2], begidx, endidx)

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
        except ValueError:
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
                      ' 2014, Cisco Systems, Inc.  All rights reserved.')
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
        if num_cmds == 1:
            getattr(self, 'do_'+cmds[0])(arg)
        elif num_cmds > 1:
            sys.stdout.write('%% Ambiguous command:\t"%s"\n' % cmd)
        else:
            sys.stdout.write('% Unrecognized command\n')

    def do_help(self, arg):
        doc_strings = [(i[3:], getattr(self, i).__doc__)
                       for i in dir(self) if i.startswith('do_')]
        doc_strings = ['  %s\t%s\n' % (i, j)
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
            print '%% Tenant %s does not exist' % tenant.name

    def complete_switchto(self, text, line, begidx, endidx):
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
        completions = ['terminal']
        return completions


class MockStdin:
    def __init__(self, filename, original_stdin):
        self.original_stdin = original_stdin
        f = open(filename)
        self.lines = f.readlines()
        f.close()

    def readline(self):
        line = self.lines.pop(0)
        print line
        if len(self.lines) == 0:
            sys.stdin = self.original_stdin
        return line

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
        print sys.argv[0], ': illegal option'
        print usage
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print usage
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

    if URL == '':
        print usage
        sys.exit(2)

    logging.basicConfig(format=('%(levelname)s:[%(module)s:'
                                '%(funcName)s]:%(message)s'),
                        filename=DEBUGFILE, filemode='w',
                        level=DEBUGLEVEL)

    apic = Session(URL, LOGIN, PASSWORD)
    apic.login()

    if 'TESTFILE' in locals():
        sys.stdin = MockStdin(TESTFILE, sys.stdin)

    cmdLine = CmdLine()
    cmdLine.apic = apic
    cmdLine.cmdloop()
