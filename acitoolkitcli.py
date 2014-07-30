"""This module implements a CLI similar to Cisco IOS and NXOS
   for use with the ACI Toolkit.
"""
import sys, getopt, logging
from cmd import Cmd
from acitoolkit import *
import pprint
import pdb
READLINE = True
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

    def do_show(self, args):
        """Show running system information"""
        #sys.stdout.write('Executing Show Command\n')
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
            pprint.pprint(tenant_dict)
            #print 'Tenant'
            #print '------'
            #for tenant in tenants:
            #    print tenant
        elif words[0] == 'bridgedomain':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            for tenant in tenants:
                bds = BridgeDomain.get(self.apic, tenant)
                bd_dict = {}
                bd_dict[tenant.name] = []
                for bd in bds:
                    bd_dict[tenant.name].append(bd.name)
                pprint.pprint(bd_dict)
        elif words[0] == 'context':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            for tenant in tenants:
                contexts = Context.get(self.apic, tenant)
                context_dict = {}
                context_dict[tenant.name] = []
                for context in contexts:
                    context_dict[tenant.name].append(context.name)
                pprint.pprint(context_dict)
        elif words[0] == 'contract':
            raise NotImplementedError
            contracts = self.db.get_class(Contract)
            contract_dict = {}
            for contract in contracts:
                if self.tenant is not None and self.tenant != contract.get_parent():
                    continue
                if contract.get_parent().name not in contract_dict:
                    contract_dict[contract.get_parent().name] = {}
                contract_dict[contract.get_parent().name][contract.name] = {}
                subjects = contract.get_children()
                for subject in subjects:
                    filts = subject.get_children()
                    for filt in filts:
                        filt = filt.get_relation()
                    if filt:
                        for entry in filt.get_children():
                            contract_dict[contract.get_parent().name][contract.name][entry.name] = {}
            pprint.pprint(contract_dict)
        elif words[0] == 'interface':
            ifs = Interface.get(self.apic)
            print 'Interface\tType\tStatus\tSpeed\tMTU'
            for interface in ifs:
                print interface
        elif words[0] == 'port-channel':
            pcs = PortChannel
        elif words[0] == 'app':
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [Tenant(self.tenant.name)]
            for tenant in tenants:
                apps = AppProfile.get(self.apic, tenant)
                app_dict = {}
                for app in apps:
                    if tenant is not None and tenant != app.get_parent():
                        continue
                    if app.get_parent().name not in app_dict:
                        app_dict[app.get_parent().name] = []
                    app_dict[app.get_parent().name].append(app.name)
                if app_dict:
                    pprint.pprint(app_dict)
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
        show_args = ['bridgedomain', 'context', 'contract', 'app', 'port-channel', 'epg', 'interface', 'tenant']
        completions = [a for a in show_args if a.startswith(line[5:])]
        return completions

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
        if self.tenant != None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-bd)# '

    def do_ip(self, args):
        " Context Creation\tcontext <context-name> "
        args = args.split()
        if len(args) <= 1:
            print '%% ip requires at least two arguments: method and ip'
            return
        elif len(args) > 3:
            print '%% ip takes 3 arguments (%i are given). %len(args.split())'
            return
        if self.tenant == None:
            print '%% context requires switchto tenant'
            return
        subnet_name = args[1].replace('/',':')
        subnet = Subnet(subnet_name, self.bridgedomain)
        subnet.set_addr(args[1])

        if args[0] == 'address':
            if self.negative:
                print 'Executing delete subnet command'
                # self.bridgedomain.remove_subnet(subnet)  ## remove_subnet()
                subnet.mark_as_deleted()
            else:
                print 'Executing create subnet command'
                # self.bridgedomain.add_subnet(subnet)  ## remove_subnet()
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
            if not resp.ok:
                error_message(resp)

    def complete_ip(self, text, line, begidx, endidx):
        ip_args = ['address']
        completions = [a for a in ip_args if a.startswith(line[3:])]
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
        if self.tenant != None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-ctx)# '

    def do_allowall(self,args):
        if self.negative:
            self.context.set_allow_all(False)
        else:
            self.context.set_allow_all(True)
        resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
        if not resp.ok:
            error_message(resp)
        else:
            print 'push configuration to APIC'

    def do_getjson(self,args):
        pdb.set_trace()
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
        " Endpoint Group assignment\tepg <app-name>/<epg-name> [vlan <vlanid>] "
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
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
            if not resp.ok:
                error_message(resp)

    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-if)#
        """
        self.prompt = 'fabric'
        if self.tenant != None:
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
        if self.tenant != None:
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
        if self.tenant == None:
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

    def do_context(self, args):
        " Context Creation\tcontext <context-name> "
        if len(args.split()) == 0:
            print '%% context requires a name'
            return
        elif len(args.split()) > 1:
            print '%% context requires only 1 name'
            return
        if self.tenant == None:
            print '%% context requires switchto tenant'
            return
        context = Context(args.strip(), self.tenant)
        context.set_allow_all(False)
        if self.negative:
            print 'Executing delete context command'
            context.mark_as_deleted()
        else:
            print 'Executing create context command'
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                self.context_submode.tenant = self.tenant
                self.context_submode.context = context
                self.context_submode.set_prompt()
                self.context_submode.cmdloop()

    def do_interface(self, args):
        "Interface Configuration\ninterface eth <pod>/<node>/<module>/<port>\ninterface port-channel <port>\n"
        if len(args.split()) > 2:
            sys.stdout.write('%% Invalid interface name\n')
            return
        if self.negative:
            pass # only relevant for port-channels
        else:
            sys.stdout.write('Executing interface command\n')
            name = args.strip()
            try: # Physical Interface
                (interface_type, pod, node, module, port) = Interface.parse_name(name)
                intf = Interface(interface_type, pod, node, module, port)
                self.interface_submode.tenant = self.tenant
                self.interface_submode.intf = intf
                self.interface_submode.set_prompt()
                self.interface_submode.cmdloop()
            except ValueError: # Port Channel
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
            
                url = 'mo/uni.json'
                data = {'infraInfra':{'children':[{'infraFuncP':{'children':[{'infraAccBndlGrp':{'attributes':{'name':'portchannelgroup2', 'lagT':'link'}}}]}}]}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text
                
                data = {'infraInfra':{'children':[{'infraAccPortP':{'attributes':{'name':'ports22and23'}, 'children':[{'infraHPortS':{'attributes':{'name':'ports', 'type':'range'}, 'children':[{'infraPortBlk':{'attributes':{'name':'blk', 'fromCard':'1', 'toCard':'1', 'fromPort':'22','toPort':'23'}}},{'infraRsAccBaseGrp':{'attributes':{'tDn':'uni/infra/funcprof/accbundle-portchannelgroup2'}}}]}}]}}]}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text

                data = {'infraInfra':{'children':[{'infraAccPortP':{'attributes':{'name':'ports22and23'}, 'children':[{'infraHPortS':{'attributes':{'name':'ports', 'type':'range'}, 'children':[{'infraPortBlk':{'attributes':{'name':'blk', 'fromCard':'1', 'toCard':'1', 'fromPort':'20','toPort':'21'}}},{'infraRsAccBaseGrp':{'attributes':{'tDn':'uni/infra/funcprof/accbundle-portchannelgroup2'}}}]}}, {'infraHPortS':{'attributes':{'name':'ports2', 'type':'range'}, 'children':[{'infraPortBlk':{'attributes':{'name':'blk', 'fromCard':'1', 'toCard':'1', 'fromPort':'15','toPort':'16'}}},{'infraRsAccBaseGrp':{'attributes':{'tDn':'uni/infra/funcprof/accbundle-portchannelgroup2'}}}]}}]}}]}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text

                return
            
                data = {'infraInfra':{'children':[{'infraNodeP':{'attributes':{'name':'leafs101'}, 'children':[{'infraLeafS':{'attributes':{'name':'leafsforpc', 'type':'range'}, 'children':[{'infraNodeBlk':{'attributes':{'name':'test', 'from_':'101', 'to_':'101'}}}]}},{'infraRsAccPortP':{'attributes':{'tDn':'uni/infra/accportprof-ports22and23'}}}]}}]}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text


            
                url = 'node/mo/uni/infra/funcprof/accbundle-%s.json' % 'pc1'
                
                #data = {'infraAccBndlGrp':{'attributes':{'lagT':'link'}}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text

                url = 'node/mo/uni/infra/accportprof-%s.json' % 'pc1'
                data = {'infraAccPortP':{'attributes':{}}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text

                url = 'node/mo/uni/infra/accportprof-%s/hports-%s-typ-%s.json' % ('pc1','pc1','range')
                data = {'infraHPortS':{'attributes':{}}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text
                
                url = 'node/mo/uni/infra/accportprof-%s/hports-%s-typ-%s/portblk-%s.json' % ('pc1','pc1','range','blk')
                data = {'infraPortBlk':{'attributes':{'fromCard':'1', 'toCard':'1',
                                                      'fromPort':'37', 'toPort':'38'}}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text

                url = 'node/mo/uni/infra/accportprof-%s/hports-%s-typ-%s/rsaccBaseGrp.json' % ('pc1','pc1','range')
                data = {'infraRsAccBaseGrp':{'attributes':{'tDn':'uni/infra/funcprof/accbundle-pc1.json'}}}
                resp = self.apic.post(url, data=json.dumps(data))
                print 'Response:', resp, resp.text
                
                print 'Must be port channel', interface_type, port

    def do_app(self, args):
        " Application Profile Creation\tapp <app-profile-name> "
        if len(args.split()) > 1 or len(args.split()) == 0:
            print '%% app requires 1 name\n'
            return
        if self.tenant == None:
            print '%% app requires switchto tenant\n'
            return
        if self.negative:
            print 'Executing delete app command\n'
            app = AppProfile(args.strip(), self.tenant)
            app.mark_as_deleted()
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
        else:
            print 'Executing create app command'
            app = AppProfile(args.strip(), self.tenant)
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
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
        if self.tenant == None:
            sys.stdout.write('%% contract requires switchto tenant\n')
            return
        if self.negative:
            contract = Contract(args.strip(), self.tenant)
            contract.mark_as_deleted()
            print 'Deleting Contract'
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
            else:
                print 'Deleted contract'
        else:
            print 'Executing create contract command'
            contract = Contract(args.strip(), self.tenant)
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
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
        if self.tenant != None:
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
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
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
        #self.app = None
        
    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-app)#
        """
        self.prompt = 'fabric'
        if self.tenant != None:
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
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
            if not resp.ok:
                error_message(resp)
        else:
            print 'Executing create epg command'
            epg_name = args.strip()
            epg = EPG(epg_name, self.app)
            resp = self.apic.push_to_apic(self.tenant.get_url(), self.tenant.get_json())
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

    def do_permit(self, args):
        """ Filter Entry\n\tpermit <protocol> [src-port <operator> {port|protocol-port}]
            \t[dest-port <operator> {port|protocol-port}] [fragments]
            \n\tpermit tcp [src-port <operator> {port|protocol-port}][dest-port <operator>
            \t{port|protocol-port}] [fragments] [{+|-} <flag-name>]
        """
        args = args.strip().split()
        protocol = None
        src_port = None
        dest_port = None
        fragments = False
        
        while len(args):
            if protocol is None:
                protocol = args.pop(0)
            elif args[0] == 'src-port':
                args.pop(0)
                if len(args) == 0:
                    return
                src_port = args.pop(0)
            elif args[0] == 'dest-port':
                args.pop(0)
                if len(args) == 0:
                    return
                dest_port = args.pop(0)
            elif args[0] == 'fragments':
                args.pop(0)
                fragments = True
            else:
                print '%% Unrecognized command'
                return
                
        print 'name:',self.entry_name,'protocol:',protocol,'src_port:',src_port,'dest_port:',dest_port,'fragments:',fragments
        
    def set_prompt(self):
        """
        Set the prompt to something like:
        fabric-tenant(config-contract)#
        """
        self.prompt = 'fabric'
        if self.tenant != None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '(config-contract)# '

    def precmd(self, line):
        line = SubMode.precmd(self, line)

        # Get the entry name from the start
        if line.strip().split()[0] != 'exit':
            self.entry_name = line.strip().split()[0]
            line = line.strip()[len(self.entry_name):]
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
        if self.tenant != None:
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
        print 'text:', text, 'line:', line, 'begidx:', begidx, 'endidx:', endidx

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
    def __init__(self, filename):
        f = open(filename)
        self.lines = f.readlines()
        f.close()

    def readline(self):
        line = self.lines.pop(0)
        print line
        return line

# *** MAIN LOOP ***
if __name__ == '__main__':
    LOGIN = ''
    PASSWORD = ''
    URL = ''
    OUTPUTFILE = ''
    DEBUGFILE = None
    DEBUGLEVEL = logging.CRITICAL
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hl:p:u:do:f:t:",
                                   ["help", "apic-login=", "apic-password=",
                                    "apic-url=", "enable-debug", "output-file=",
                                    "debug-file=", "test-file="])
    except getopt.GetoptError:
        print 'aci-toolkit-cli.py -l <login> -p <password> -u <url>'
        print 'aci-toolkit-cli.py -o <output-file> -t <test-file>'
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print 'TODO help'
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

    logging.basicConfig(format=('%(levelname)s:[%(module)s:'
                                '%(funcName)s]:%(message)s'),
                        filename=DEBUGFILE, filemode='w',
                        level=DEBUGLEVEL)

    apic = Session(URL, LOGIN, PASSWORD)
    apic.login()

    if 'TESTFILE' in locals():
        sys.stdin = MockStdin(TESTFILE)

    cmdLine = CmdLine()
    cmdLine.apic = apic
    cmdLine.cmdloop()
    
