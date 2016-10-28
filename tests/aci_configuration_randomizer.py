from acitoolkit import (Credentials, Session, Tenant, BridgeDomain, Context, AppProfile, EPG,
                        Contract, ContractSubject, Filter, FilterEntry, Interface, L2Interface)
import random
import string
import ConfigParser
import json
import time


def random_chance(percentage):
    return random_number(0, 99) < percentage


def random_string(size, char_set=[]):
    if len(char_set) == 0:
        char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits + '_.-'
    return ''.join(random.choice(char_set) for x in range(size))


def random_number(min_size, max_size):
    if max_size < min_size:
        min_size = max_size
    if min_size == max_size:
        return min_size
    return random.randint(min_size, max_size)


def random_range(low, high):
    # Choose 0,0 25% of the time
    if random_chance(25):
        return str(low), str(low)
    # Choose the low number
    low = random_number(low + 1, high)
    # Choose single number range 25% of the time
    if random_chance(25):
        return str(low), str(low)
    # Choose the high number above the low number
    high = random_number(low, high)
    return str(low), str(high)


class Flow(object):
    def __init__(self, ipv4=True, unicast=True):
        self.dmac = None
        self.smac = None
        self.svlan = 0
        self.dvlan = 0
        self.ethertype = 0
        self.dip = None
        self.sip = None
        self.proto = None
        self.sport = None
        self.dport = None
        self.arp_opcode = None
        self.src_intf = None
        self.expected_action = None
        self.dst_intf = None
        self.tcp_rules = None

    @staticmethod
    def _get_random_ipv4_address(unicast=True):
        octets = []
        # Pick random first octet
        if unicast:
            choice = 127
            while choice == 127:
                choice = random_number(1, 255)
            octets.append(choice)
        else:
            octets.append(random_number(224, 239))
        # Pick the remaining 3 octets
        for i in range(1, 4):
            octets.append(random_number(0, 255))
        # Build the string
        addr = str(octets[0])
        for i in range(1, 4):
            addr += '.' + str(octets[i])
        return addr

    @staticmethod
    def _get_random_mac_address():
        addr = random_number(0, 255)
        # Ensure first bit is unicast
        if addr % 2:
            addr += 1
        addr = str(hex(addr))[2:].zfill(2)
        # Get the next bytes
        for i in range(1, 6):
            addr = addr + '-' + str(hex(random_number(0, 255)))[2:].zfill(2)
        return addr

    def populate_random_mac_addresses(self, unicast=True):
        if not unicast:
            raise NotImplementedError
        self.smac = self._get_random_mac_address()
        self.dmac = self._get_random_mac_address()

    def populate_random_ip_addresses(self, ipv4=True, unicast=True):
        if not ipv4:
            raise NotImplementedError
        if not unicast:
            raise NotImplementedError
        self.sip = self._get_random_ipv4_address()
        self.dip = self._get_random_ipv4_address(unicast=unicast)

    def __str__(self):
        resp = 'dmac: ' + self.dmac + ' smac: ' + self.smac
        resp = resp + ' ethertype: ' + self.ethertype
        resp = resp + ' svlan: ' + str(self.svlan) + ' dvlan: ' + str(self.dvlan)
        resp = resp + ' src_intf: ' + str(self.src_intf) + ' dst_intf: ' + str(self.dst_intf)
        if self.ethertype == 'ip':
            resp = resp + ' sip: ' + self.sip + ' dip: ' + self.dip
            if self.proto == '6' or self.proto == '17':
                resp = resp + ' dport: ' + self.dport + ' sport: ' + self.sport
            if self.proto == '6':
                resp = resp + ' tcp_rules: ' + self.tcp_rules
        if self.proto is not None:
            resp = resp + ' proto: ' + self.proto
        resp = resp + ' expected_action: ' + self.expected_action
        return resp

    def get_json(self):
        resp = {}
        for key in self.__dict__:
            if self.__dict__[key]:
                resp[key] = self.__dict__[key]
        return resp


class Limits(object):
    def __init__(self, config):
        self.max_bds = int(config.get('BridgeDomains', 'GlobalMaximum'))
        self.max_contexts = int(config.get('Contexts', 'GlobalMaximum'))
        self.max_epgs = int(config.get('EPGs', 'GlobalMaximum'))
        self.max_filters = int(config.get('Filters', 'GlobalMaximum'))
        self.max_filter_entries = int(config.get('FilterEntries', 'GlobalMaximum'))
        self.max_contracts = int(config.get('Contracts', 'GlobalMaximum'))


class ConfigRandomizer(object):
    def __init__(self, config):
        self._config = config
        self._global_limits = Limits(config)
        self._tenants = []
        self._interfaces = {}

    def create_random_tenant(self, interfaces=[]):
        max_string_length = int(self._config.get('GlobalDefaults', 'MaximumStringLength'))
        # Create the Tenant object
        tenant_prefix = 'acitoolkitrandomized-'
        tenant_name_len = random_number(1, max_string_length - len(tenant_prefix))
        tenant_name = tenant_prefix + random_string(tenant_name_len)
        tenant = Tenant(tenant_name)

        # Create some number of BridgeDomains
        bridge_domains = []
        maximum_bds = int(self._config.get('BridgeDomains', 'Maximum'))
        if maximum_bds > self._global_limits.max_bds:
            maximum_bds = self._global_limits.max_bds
        for i in range(0, random_number(0, random_number(int(self._config.get('BridgeDomains', 'Minimum')),
                                                         maximum_bds))):
            self._global_limits.max_bds -= 1
            bd = BridgeDomain(random_string(random_number(1, max_string_length)), tenant)
            # Randomly choose settings for the BridgeDomain
            if self._config.get('BridgeDomains', 'AllowFloodUnkMacUcast').lower() == 'true':
                bd.set_unknown_mac_unicast(random.choice(['proxy', 'flood']))
            if self._config.get('BridgeDomains', 'AllowOptimizedFloodUnknownMcast').lower() == 'true':
                bd.set_unknown_multicast(random.choice(['flood', 'opt-flood']))
            if self._config.get('BridgeDomains', 'AllowArpFlood').lower() == 'true':
                bd.set_arp_flood(random.choice(['yes', 'no']))
            if self._config.get('BridgeDomains', 'AllowDisableUnicastRoute').lower() == 'true':
                bd.set_unicast_route(random.choice(['yes', 'no']))
            if self._config.get('BridgeDomains', 'AllowNonDefaultMultiDstPkt').lower() == 'true':
                bd.set_multidestination(random.choice(['drop', 'bd-flood', 'encap-flood']))
            bridge_domains.append(bd)

        # Create some number of Contexts
        contexts = []
        max_contexts = int(self._config.get('Contexts', 'Maximum'))
        if max_contexts > self._global_limits.max_contexts:
            max_contexts = self._global_limits.max_contexts
        if max_contexts > int(self._config.get('Contexts', 'MaximumPerTenant')):
            max_contexts = int(self._config.get('Contexts', 'MaximumPerTenant'))
        for i in range(0, random_number(0, random_number(int(self._config.get('Contexts', 'Minimum')),
                                                         max_contexts))):
            context = Context(random_string(random_number(1, max_string_length)), tenant)
            self._global_limits.max_contexts -= 1
            if self._config.get('Contexts', 'AllowUnenforced').lower() == 'true':
                context.set_allow_all(random.choice([True, False]))
            contexts.append(context)

        # Randomly associate BridgeDomains with the Contexts (or use default)
        for bd in bridge_domains:
            if random.choice([True, True, False]) and len(contexts):
                bd.add_context(random.choice(contexts))

        # Create some number of Application Profiles
        apps = []
        for i in range(0, random_number(0, random_number(int(self._config.get('ApplicationProfiles', 'Minimum')),
                                                         int(self._config.get('ApplicationProfiles', 'Maximum'))))):
            app = AppProfile(random_string(random_number(1, max_string_length)), tenant)
            apps.append(app)

        # Create some number of EPGs and place in AppProfiles
        epgs = []
        max_epgs = int(self._config.get('EPGs', 'Maximum'))
        if max_epgs > self._global_limits.max_epgs:
            max_epgs = self._global_limits.max_epgs
        if len(apps):
            for i in range(0, random_number(0, random_number(int(self._config.get('EPGs', 'Minimum')),
                                                             max_epgs))):
                epg = EPG(random_string(random_number(1, max_string_length)), random.choice(apps))
                self._global_limits.max_epgs -= 1
                epgs.append(epg)

        # Randomly associate the EPGs to BridgeDomains
        bd_epg_count = [0] * len(bridge_domains)
        for epg in epgs:
            if random_number(0, 9) == 1 or len(bridge_domains) == 0:   # 1 in 10 chance for no bridgedomain
                continue
            keep_trying = 100
            while keep_trying:
                bd_choice = random_number(0, len(bridge_domains) - 1)
                if bd_epg_count[bd_choice] <= int(self._config.get('BridgeDomains', 'MaximumEPGs')):
                    epg.add_bd(bridge_domains[bd_choice])
                    bd_epg_count[bd_choice] += 1
                    break
                else:
                    keep_trying -= 1

        # Randomly assign the EPGs to the interfaces provided
        interface_objs = {}
        for interface in interfaces:
            # Create the Interface objects
            interface_objs[interface] = Interface.create_from_name(interface)
        for epg in epgs:
            # Pick an interface
            interface_choice = random.choice(interfaces)
            # Pick a VLAN
            vlan_choice = 0
            keep_trying = 100
            while vlan_choice in self._interfaces[interface_choice]:
                vlan_choice = random_number(int(self._config.get('VLANs', 'Minimum')),
                                            int(self._config.get('VLANs', 'Maximum')))
                keep_trying -= 1
            if not keep_trying:
                continue
            # Create the VLAN interface
            vlan_intf = L2Interface('vlan%s-on-%s' % (str(vlan_choice),
                                                      interface_objs[interface_choice].name.replace(' ', '')),
                                    'vlan',
                                    str(vlan_choice))
            # Attach the VLAN interface to the Interface object
            vlan_intf.attach(interface_objs[interface_choice])
            # Attach the EPG to the VLAN interface
            epg.attach(vlan_intf)

        # Create some filters
        filters = []
        max_filters = int(self._config.get('Filters', 'Maximum'))
        if max_filters > self._global_limits.max_filters:
            max_filters = self._global_limits.max_filters
        for i in range(0, random_number(0, random_number(int(self._config.get('Filters', 'Minimum')),
                                                         max_filters))):
            filter = Filter(random_string(random_number(1, max_string_length)), tenant)
            self._global_limits.max_filters -= 1
            filters.append(filter)

        # Create some filter entries
        filter_entries = []
        max_filter_entries = int(self._config.get('FilterEntries', 'Maximum'))
        if max_filter_entries > self._global_limits.max_filter_entries:
            max_filter_entries = self._global_limits.max_filter_entries
        ip_protocols = {
            'icmp': '1',
            'igmp': '2',
            'tcp': '6',
            'egp': '8',
            'igp': '9',
            'udp': '17',
            'icmpv6': '58',
            'eigrp': '88',
            'ospfigp': '89',
            'pim': '103',
            'l2tp': '115'
        }
        if len(filters):
            for i in range(0, random_number(0, random_number(int(self._config.get('FilterEntries', 'Minimum')),
                                                             max_filter_entries))):
                applyToFrag = '0'
                arpOpc = '0'
                dFromPort = '0'
                dToPort = '0'
                prot = '0'
                sFromPort = '0'
                sToPort = '0'
                tcpRules = '0'
                stateful = '0'
                if random_chance(20):  # 20% chance of ARP
                    arpOpc = random.choice(['req', 'reply'])
                    etherT = 'arp'
                elif random_chance(25):  # 20% of remaining 80% is non-IP (16% of total)
                    ethertype_choices = ['trill', 'mpls_ucast', 'mac_security', 'fcoe']
                    # if not filter.has_wildcard_entry():
                    #     ethertype_choices += ['0']
                    etherT = random.choice(ethertype_choices)
                else:  # remaining is IP
                    applyToFrag = random.choice(['0', '1'])
                    etherT = 'ip'
                    if random_chance(20):  # Choose more obscure protocols 20% of the time
                        prot = ip_protocols[random.choice(['igmp', 'egp', 'igp', 'eigrp', 'ospfigp', 'pim', 'l2tp'])]
                    else:
                        prot = ip_protocols[random.choice(['icmp', 'tcp', 'udp', 'icmpv6'])]
                        if prot == ip_protocols['icmp']:
                            pass
                        elif prot == ip_protocols['icmpv6']:
                            pass
                        else:
                            # Remainder is TCP or UDP
                            dFromPort, dToPort = random_range(0, 65535)
                            sFromPort, sToPort = random_range(0, 65535)
                            if dFromPort != '0' or dToPort != '0' or sFromPort != '0' or sToPort != '0':
                                applyToFrag = '0'
                            if prot == ip_protocols['tcp']:
                                # Randomly choose whether to specify tcpRules
                                if random_chance(30):
                                    # TODO: should actually take odds from the config file
                                    # Choose a random number of the possible tcpRules but
                                    # if est is chosen, then it must be the only tcpRule. Otherwise, APIC rejects it
                                    tcp_rule_choices = []
                                    tcp_rule_possibilities = ['est', 'syn', 'ack', 'fin', 'rst']
                                    tcp_choice = random.choice(tcp_rule_possibilities)
                                    tcp_rule_choices.append(tcp_choice)
                                    while tcp_choice != 'est':
                                        tcp_choice = random.choice(tcp_rule_possibilities)
                                        if tcp_choice != 'est' and tcp_choice not in tcp_rule_choices:
                                            tcp_rule_choices.append(tcp_choice)
                                    tcpRules = ''
                                    for tcp_choice in tcp_rule_choices:
                                        tcpRules += str(tcp_choice) + ','
                parent = random.choice(filters)
                if not parent.has_entry(applyToFrag, arpOpc, dFromPort, dToPort, etherT, prot, sFromPort, sToPort,
                                        tcpRules, stateful):
                    filter_entry = FilterEntry(name=random_string(random_number(1, max_string_length)),
                                               parent=random.choice(filters),
                                               applyToFrag=applyToFrag,
                                               arpOpc=arpOpc,
                                               dFromPort=dFromPort,
                                               dToPort=dToPort,
                                               etherT=etherT,
                                               prot=prot,
                                               sFromPort=sFromPort,
                                               sToPort=sToPort,
                                               tcpRules=tcpRules,
                                               stateful=stateful)
                self._global_limits.max_filter_entries -= 1

        # Create some Contracts
        contracts = []
        max_contracts = int(self._config.get('Contracts', 'Maximum'))
        if max_contracts > self._global_limits.max_contracts:
            max_contracts = self._global_limits.max_contracts
        for i in range(0, random_number(0, random_number(int(self._config.get('Contracts', 'Minimum')),
                                                         max_contracts))):
            contract = Contract(random_string(random_number(1, max_string_length)), tenant)
            self._global_limits.max_contracts -= 1
            contracts.append(contract)

        # Create some ContractSubjects
        if len(contracts):
            contract_subjects = []
            for i in range(0, random_number(0, random_number(int(self._config.get('ContractSubjects', 'Minimum')),
                                                             int(self._config.get('ContractSubjects', 'Maximum'))))):
                contract_subject = ContractSubject(random_string(random_number(1, max_string_length)), random.choice(contracts))
                contract_subjects.append(contract_subject)

        # Randomly assign Filters to the ContractSubjects
        for filter in filters:
            if len(contracts) and len(contract_subjects):
                already_picked = []
                # Pick an arbitrary number of Subjects
                for i in range(0, random_number(1, len(contract_subjects))):
                    pick = random_number(0, len(contract_subjects) - 1)
                    # Only choose each subject at most once
                    if pick not in already_picked:
                        contract_subjects[pick].add_filter(filter)
                        already_picked.append(pick)

        # Randomly provide and consume the Contracts from the EPGs
        for action, max_num_epgs in [('provide', int(self._config.get('Contracts', 'MaximumProvidingEPGs'))),
                                     ('consume', int(self._config.get('Contracts', 'MaximumConsumingEPGs')))]:
            contract_count = [0] * len(contracts)
            for epg in epgs:
                already_picked = []
                for i in range(0, random_number(0, len(contracts))):
                    keep_trying = 20  # Try 20 times to randomly pick a contract
                    while keep_trying:
                        pick = random_number(0, len(contracts) - 1)
                        if pick not in already_picked and contract_count[pick] < max_num_epgs:
                            getattr(epg, action)(contracts[pick])
                            already_picked.append(pick)
                            contract_count[pick] += 1
                            keep_trying = 0
                        else:
                            keep_trying -= 1
        return tenant

    def create_random_config(self, interfaces=[]):
        num_tenants = random_number(int(self._config.get('Tenants', 'Minimum')),
                                    int(self._config.get('Tenants', 'Maximum')))
        if int(self._config.get('Tenants', 'GlobalMaximum')) < int(self._config.get('Tenants', 'Maximum')):
            print 'Tenant Maximum cannot be greater than Tenant GlobalMaximum'
            return
        for interface in interfaces:
            self._interfaces[interface] = [0]
        for i in range(0, num_tenants):
            self._tenants.append(self.create_random_tenant(interfaces))

    def get_flows(self, num_flows_per_entry):
        """
        Returns a collection of random flows that when sent on the indicated interface should have the
        specified action applied.

        :param num_flows_per_entry: integer indicating how many random flows for each entry to send
        :return: List of Flows
        """
        flows = []
        for tenant in self._tenants:
            for contract in tenant.get_children(only_class=Contract):
                providing_epgs = contract.get_all_providing_epgs()
                consuming_epgs = contract.get_all_consuming_epgs()
                for providing_epg in providing_epgs:
                    vlan_ifs = providing_epg.get_all_attached(L2Interface)
                    if len(vlan_ifs):
                        providing_vlan = vlan_ifs[0].encap_id
                        phys_ifs = vlan_ifs[0].get_all_attached(Interface)
                        if len(phys_ifs):
                            providing_phys_if = phys_ifs[0].name
                    for consuming_epg in consuming_epgs:
                        vlan_ifs = consuming_epg.get_all_attached(L2Interface)
                        if len(vlan_ifs):
                            consuming_vlan = vlan_ifs[0].encap_id
                            phys_ifs = vlan_ifs[0].get_all_attached(Interface)
                            if len(phys_ifs):
                                consuming_phys_if = phys_ifs[0].name
                        if providing_vlan == consuming_vlan and providing_phys_if == consuming_phys_if:
                            # Skip this case since traffic would be switched outside fabric
                            continue
                        for filter_entry in contract.get_all_filter_entries():
                            for i in range(0, num_flows_per_entry):
                                flow = Flow()
                                flow.ethertype = filter_entry.etherT
                                if flow.ethertype == 'arp':
                                    flow.arp_opcode = filter_entry.arpOpc
                                elif flow.ethertype == 'ip':
                                    flow.populate_random_ip_addresses()
                                    flow.proto = filter_entry.prot
                                    if flow.proto == '6' or flow.proto == '17':
                                        dFromPort = int(filter_entry.dFromPort)
                                        dToPort = int(filter_entry.dToPort)
                                        sFromPort = int(filter_entry.sFromPort)
                                        sToPort = int(filter_entry.sToPort)
                                        if dFromPort == 0:
                                            dFromPort = 1
                                            dToPort += 1
                                        if sFromPort == 0:
                                            sFromPort = 1
                                            sToPort += 1
                                        if dToPort > 65534:
                                            dToPort = 65534
                                        if sToPort > 65534:
                                            sToPort = 65534
                                        flow.dport = str(random_number(dFromPort,
                                                                       dToPort))
                                        flow.sport = str(random_number(sFromPort,
                                                                       sToPort))
                                        if flow.proto == '6':
                                            flow.tcp_rules = filter_entry.tcpRules
                                flow.svlan = providing_vlan
                                flow.dvlan = consuming_vlan
                                flow.src_intf = providing_phys_if
                                flow.dst_intf = consuming_phys_if

                                # Is the flow expected to succeed ?
                                flow.expected_action = 'drop'
                                providing_bd = providing_epg.get_bd()
                                consuming_bd = consuming_epg.get_bd()
                                if providing_bd and consuming_bd:
                                    if providing_bd == consuming_bd:
                                        if providing_bd.get_context() == consuming_bd.get_context():
                                            flow.expected_action = 'permit'
                                flow.populate_random_mac_addresses()
                                flows.append(flow)
        return flows

    @property
    def tenants(self):
        return self._tenants


def delete_all_randomized_tenants(session):
    tenants = Tenant.get(session)
    for tenant in tenants:
        if tenant.name.startswith('acitoolkitrandomized-'):
            tenant.mark_as_deleted()
            resp = tenant.push_to_apic(session)
            if not resp.ok:
                print 'Could not delete tenant', tenant.name
                print resp.status_code, resp.text
            else:
                print 'Deleted tenant', tenant.name


def generate_config(session, args):
    config = ConfigParser.ConfigParser()
    config.read(args.config)
    randomizer = ConfigRandomizer(config)
    interfaces = ['eth 1/101/1/17', 'eth 1/102/1/17']
    randomizer.create_random_config(interfaces)
    flows = randomizer.get_flows(1)
    flow_json = []
    for flow in flows:
        flow_json.append(flow.get_json())
    flow_json = json.dumps({'flows': flow_json})

    for tenant in randomizer.tenants:
        print 'TENANT CONFIG'
        print '-------------'
        print tenant.get_json()
        print
        print
        if not args.printonly:
            resp = tenant.push_to_apic(session)
            if not resp.ok:
                print resp.status_code, resp.text
            assert resp.ok
    print 'Total number of tenants pushed:', len(randomizer.tenants)


def main():
    # Set up the Command Line options
    creds = Credentials(('apic', 'nosnapshotfiles'), description='')
    creds.add_argument('--printonly', action='store_true',
                       help='Only print the JSON but do not push to APIC.')
    creds.add_argument('--testloop', action='store_true',
                       help='Run in a continual testing loop.')
    group = creds.add_mutually_exclusive_group()
    group.add_argument('--config', default=None,
                       help='Optional .ini file providing failure scenario configuration')
    group.add_argument('--delete', action='store_true',
                       help='Delete ALL of the randomized configuration from the APIC')
    args = creds.get()

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        print resp.status_code, resp.text
        return

    # Handle the delete case
    if args.delete:
        delete_all_randomized_tenants(session)
        return

    # Ensure that a config file has been given
    if args.config is None:
        print '%% Expected --config or --delete option'
        return

    if args.testloop:
        while True:
            generate_config(session, args)
            time.sleep(random_number(5, 30))
            delete_all_randomized_tenants(session)
            time.sleep(random_number(5, 30))
    else:
        generate_config(session, args)

if __name__ == '__main__':
    main()
