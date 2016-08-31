from acitoolkit import (Credentials, Session, Tenant, BridgeDomain, Context, AppProfile, EPG)
import random
import string
import ConfigParser


def random_string(size, char_set=[]):
    if len(char_set) == 0:
        char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits + '_.-'
    return ''.join(random.choice(char_set) for x in range(size))


def random_number(min_size, max_size):
    return random.randint(min_size, max_size)


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
        bridge_domains.append(bd)

    # Create some number of Contexts
    contexts = []
    for i in range(0, random_number(0, random_number(int(config.get('Contexts', 'Minimum')),
                                                     int(config.get('Contexts', 'Maximum'))))):
        context = Context(random_string(random_number(1, 64)), tenant)
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
        associate = random_number(0, 10)  # 1 in 10 chance for no bridgedomain
        if associate and len(bridge_domains):
            epg.add_bd(random.choice(bridge_domains))

    return tenant


def delete_all_randomized_tenants(session):
    tenants = Tenant.get(session)
    for tenant in tenants:
        if tenant.name.startswith('acitoolkitrandomized-'):
            tenant.mark_as_deleted()
            resp = tenant.push_to_apic(session)
            if not resp.ok:
                print 'Could not delete tenant', tenant.name
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
        print resp.text
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
    for i in range(0, random_number(int(config.get('Tenants', 'Minimum')),
                                    int(config.get('Tenants', 'Maximum')))):
        tenant = create_random_tenant_config(config)
        print 'TENANT CONFIG'
        print '-------------'
        print tenant.get_json()
        print
        print
        resp = tenant.push_to_apic(session)
        assert resp.ok


if __name__ == '__main__':
    main()
