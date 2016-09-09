from acitoolkit import (Credentials, Session, Tenant, BridgeDomain, Context, AppProfile, EPG,
                        Contract, ContractSubject, Filter, FilterEntry)
import random
import string
import ConfigParser


def random_chance(percentage):
    return random_number(0, 99) < percentage


def random_string(size, char_set=[]):
    if len(char_set) == 0:
        char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits + '_.-'
    return ''.join(random.choice(char_set) for x in range(size))


def random_number(min_size, max_size):
    return random.randint(min_size, max_size)


def random_range(low, high):
    # Choose 0,0 25% of the time
    if random_chance(25):
        return str(low), str(low)
    # Choose the low number
    low = random_number(low+1, high)
    # Choose single number range 25% of the time
    if random_chance(25):
        return str(low), str(low)
    # Choose the high number above the low number
    high = random_number(low, high)
    return str(low), str(high)


def create_random_tenant_config(config):
    # Create the Tenant object
    tenant_prefix = 'acitoolkitrandomized-'
    tenant_name = tenant_prefix + random_string(random_number(1, 63 - len(tenant_prefix)))
    tenant = Tenant(tenant_name)

    # Create some number of BridgeDomains
    bridge_domains = []
    for i in range(0, random_number(0, random_number(int(config.get('BridgeDomains', 'Minimum')),
                                                     int(config.get('BridgeDomains', 'Maximum'))))):
        bd = BridgeDomain(random_string(random_number(1, 64)), tenant)
        # Randomly choose settings for the BridgeDomain
        if config.get('BridgeDomains', 'AllowFloodUnkMacUcast').lower() == 'true':
            bd.set_unknown_mac_unicast(random.choice(['proxy', 'flood']))
        if config.get('BridgeDomains', 'AllowOptimizedFloodUnknownMcast').lower() == 'true':
            bd.set_unknown_multicast(random.choice(['flood', 'opt-flood']))
        if config.get('BridgeDomains', 'AllowArpFlood').lower() == 'true':
            bd.set_arp_flood(random.choice(['yes', 'no']))
        if config.get('BridgeDomains', 'AllowDisableUnicastRoute').lower() == 'true':
            bd.set_unicast_route(random.choice(['yes', 'no']))
        if config.get('BridgeDomains', 'AllowNonDefaultMultiDstPkt').lower() == 'true':
            bd.set_multidestination(random.choice(['drop', 'bd-flood', 'encap-flood']))
        bridge_domains.append(bd)

    # Create some number of Contexts
    contexts = []
    for i in range(0, random_number(0, random_number(int(config.get('Contexts', 'Minimum')),
                                                     int(config.get('Contexts', 'Maximum'))))):
        context = Context(random_string(random_number(1, 64)), tenant)
        if config.get('Contexts', 'AllowUnenforced').lower() == 'true':
            context.set_allow_all(random.choice([True, False]))
        contexts.append(context)

    # Randomly associate BridgeDomains with the Contexts (or use default)
    for bd in bridge_domains:
        if random.choice([True, True, False]) and len(contexts):
            bd.add_context(random.choice(contexts))

    # Create some number of Application Profiles
    apps = []
    for i in range(0, random_number(0, random_number(int(config.get('ApplicationProfiles', 'Minimum')),
                                                     int(config.get('ApplicationProfiles', 'Maximum'))))):
        app = AppProfile(random_string(random_number(1, 64)), tenant)
        apps.append(app)

    # Create some number of EPGs and place in AppProfiles
    epgs = []
    if len(apps):
        for i in range(0, random_number(0, random_number(int(config.get('EPGs', 'Minimum')),
                                                         int(config.get('EPGs', 'Maximum'))))):
            epg = EPG(random_string(random_number(1, 64)), random.choice(apps))
            epgs.append(epg)

    # Randomly associate the EPGs to BridgeDomains
    for epg in epgs:
        if random_number(0, 9) == 1 and len(bridge_domains):  # 1 in 10 chance for no bridgedomain
            epg.add_bd(random.choice(bridge_domains))

    # Create some filters
    filters = []
    for i in range(0, random_number(0, random_number(int(config.get('Filters', 'Minimum')),
                                                     int(config.get('Filters', 'Maximum'))))):
        filter = Filter(random_string(random_number(1, 64)), tenant)
        filters.append(filter)

    # Create some filter entries
    filter_entries = []
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
        for i in range(0, random_number(0, random_number(int(config.get('FilterEntries', 'Minimum')),
                                                         int(config.get('FilterEntries', 'Maximum'))))):
            applyToFrag='0'
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
                            if random_chance(30):
                                tcpRules = random.choice(['est', 'syn', 'ack', 'fin'])
            parent = random.choice(filters)
            if not parent.has_entry(applyToFrag, arpOpc, dFromPort, dToPort, etherT, prot, sFromPort, sToPort,
                                    tcpRules, stateful):
                filter_entry = FilterEntry(name=random_string(random_number(1, 64)),
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

    # Create some Contracts
    contracts = []
    for i in range(0, random_number(0, random_number(int(config.get('Contracts', 'Minimum')),
                                                     int(config.get('Contracts', 'Maximum'))))):
        contract = Contract(random_string(random_number(1, 64)), tenant)
        contracts.append(contract)

    # Create some ContractSubjects
    if len(contracts):
        contract_subjects = []
        for i in range(0, random_number(0, random_number(int(config.get('ContractSubjects', 'Minimum')),
                                                         int(config.get('ContractSubjects', 'Maximum'))))):
            contract_subject = ContractSubject(random_string(random_number(1, 64)), random.choice(contracts))
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
    for action in ['provide', 'consume']:
        for epg in epgs:
            already_picked = []
            for i in range(0, random_number(0, len(contracts))):
                pick = random_number(0, len(contracts) - 1)
                if pick not in already_picked:
                    getattr(epg, action)(contracts[pick])
                    already_picked.append(pick)

    return tenant


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


def main():
    # Set up the Command Line options
    creds = Credentials(('apic', 'nosnapshotfiles'), description='')
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

    config = ConfigParser.ConfigParser()
    config.read(args.config)

    # Handle the random creation
    num_tenants = random_number(int(config.get('Tenants', 'Minimum')),
                                int(config.get('Tenants', 'Maximum')))
    for i in range(0, num_tenants):
        tenant = create_random_tenant_config(config)
        print 'TENANT CONFIG'
        print '-------------'
        print tenant.get_json()
        print
        print
        resp = tenant.push_to_apic(session)
        if not resp.ok:
            print resp.status_code, resp.text
        assert resp.ok
    print 'Total number of tenants pushed:', num_tenants

if __name__ == '__main__':
    main()
