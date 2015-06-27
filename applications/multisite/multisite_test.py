import argparse
import unittest
import random
from multisite import *
import time

config = None
site1_tool = MultisiteCollector()
site2_tool = MultisiteCollector()
collectors = [site1_tool, site2_tool]

def setup_local_apic(session, delete=False):
    # Create the Tenant
    tenant1 = Tenant('multisite-testsuite')

    # Create the Application Profile
    app = AppProfile('my-demo-app', tenant1)

    # Create the EPGs
    web_epg = EPG('web-frontend', app)
    db_epg = EPG('database-backend', app)

    # Create a Context and BridgeDomain
    # Place both EPGs in the Context and in the same BD
    context = Context('VRF-1', tenant1)
    bd = BridgeDomain('BD-1', tenant1)
    bd.add_context(context)
    web_epg.add_bd(bd)
    db_epg.add_bd(bd)

    # Define a contract with a single entry
    contract = Contract('http-contract', tenant1)
    entry1 = FilterEntry('entry1',
                         applyToFrag='no',
                         arpOpc='unspecified',
                         dFromPort='3306',
                         dToPort='3306',
                         etherT='ip',
                         prot='tcp',
                         sFromPort='1',
                         sToPort='65535',
                         tcpRules='unspecified',
                         parent=contract)

    # Provide the contract from 1 EPG and consume from the other
    db_epg.provide(contract)
    web_epg.consume(contract)

    context = Context('ctx0', tenant1)
    #contract = Contract('contract', tenant)
    phyif = Interface('eth', '1', '102', '1', '25')
    l2if = L2Interface('eth 1/102/1/25', 'vlan', '500')
    l2if.attach(phyif)
    l3if = L3Interface('l3if')
    l3if.set_l3if_type('ext-svi')
    l3if.set_addr('20.0.0.1/16')
    l3if.add_context(context)
    l3if.attach(l2if)

    #l3if.networks.append('1.1.1.1/32')
    #outside.provide(contract)
    l3if.attach(l2if)
    rtr = OSPFRouter('rtr-1')
    rtr.set_router_id('101.101.101.101')
    rtr.set_node_id('102')
    # net1 = OutsideNetwork('1.1.1.1/32')
    # net1.network = '1.1.1.1/32'
    # net1.provide(contract)
    ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='0.0.0.1')
    ospfif.attach(l3if)
    # ospfif.networks.append(net1)
    outside = OutsideEPG('multisite-testsuite-l3out', tenant1)
    outside.attach(ospfif)
    #outside.add_context(context)

    # Cleanup (uncomment the next line to delete the config)
    if delete:
        print 'Deleting...'
        tenant1.mark_as_deleted()
    resp = tenant1.push_to_apic(session)
    if not resp.ok:
        print resp, resp.text, session.ipaddr
    assert resp.ok
    return resp

def setup_remote_apic(session, delete=False):
    # Create the Tenant
    tenant = Tenant('multisite-testsuite')

    # Create the Application Profile
    app = AppProfile('my-demo-app', tenant)

    # Create the EPGs
    web_epg = EPG('web-frontend', app)

    # Create a Context and BridgeDomain
    # Place both EPGs in the Context and in the same BD
    context = Context('VRF-1', tenant)
    bd = BridgeDomain('BD-1', tenant)
    bd.add_context(context)
    web_epg.add_bd(bd)

    context = Context('ctx0', tenant)
    phyif = Interface('eth', '1', '102', '1', '25')
    l2if = L2Interface('eth 1/102/1/25', 'vlan', '500')
    l2if.attach(phyif)
    l3if = L3Interface('l3if')
    l3if.set_l3if_type('ext-svi')
    l3if.set_addr('20.0.0.2/16')
    l3if.add_context(context)
    l3if.attach(l2if)
    l3if.attach(l2if)
    rtr = OSPFRouter('rtr-1')
    rtr.set_router_id('102.102.102.102')
    rtr.set_node_id('102')
    ospfif = OSPFInterface('ospfif-1', router=rtr, area_id='0.0.0.1')
    ospfif.attach(l3if)
    outside = OutsideEPG('multisite-testsuite-l3out', tenant)
    outside.attach(ospfif)

    # Cleanup (uncomment the next line to delete the config)
    if delete:
        tenant.mark_as_deleted()
    resp = tenant.push_to_apic(session)
    assert resp.ok
    return resp

def verify_tag(session, tenant_name, tag):
    class_query_url = ('/api/mo/uni/tn-%s.json?query-target=subtree&'
                       'target-subtree-class=tagInst&'
                       'query-target-filter=eq(tagInst.name,"%s")' % (tenant_name, tag))
    resp = session.get(class_query_url)
    data = resp.json()['imdata']
    return len(data)

def has_contract(session, tenant_name, contract_name):
    tenant = Tenant(tenant_name)
    contracts = Contract.get(session, tenant)
    found = False
    for contract in contracts:
        if contract.name == contract_name:
            found = True
    return found

def has_l3extsubnet(session, tenant_name, mac, ip):
    class_query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                       "target-subtree-class=l3extSubnet" % tenant_name)
    resp = session.get(class_query_url)
    data = resp.json()['imdata']
    if len(data) == 0:
        return False
    found = False
    for subnet in data:
        assert 'l3extSubnet' in subnet
        dn = subnet['l3extSubnet']['attributes']['dn']
        if mac in dn and ip in dn:
            found = True
    return found


def has_l3extInstP_consuming_contract(session, tenant_name, mac, ip, contract_name, tag):
    # Get all of the l3extOuts in the tenant
    query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                 "target-subtree-class=l3extOut" % tenant_name)
    resp = session.get(query_url)
    l3extout_data = resp.json()['imdata']
    if len(l3extout_data) == 0:
        return False

    for l3extout in l3extout_data:
        l3extout_name = l3extout['l3extOut']['attributes']['name']
        # Verify that the l3extSubnet is in each l3extOut
        query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                     'target-subtree-class=l3extSubnet'
                     '&query-target-filter=eq(l3extSubnet.ip,"%s/32")' % (tenant_name, l3extout_name, ip))
        resp = session.get(query_url)
        l3extsubnet_data = resp.json()['imdata']
        if len(l3extsubnet_data) == 0:
            return False

        # Verify that the l3extInstP is each l3extOut
        query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                     'target-subtree-class=l3extInstP' % (tenant_name, l3extout_name))
        resp = session.get(query_url)
        l3extinstp_data = resp.json()['imdata']
        if len(l3extinstp_data) == 0:
            return False

        # Verify that the l3extInstP is consuming the contract
        all_consume = True
        for l3extinstp in l3extinstp_data:
            query_url = '/api/mo/' + l3extinstp['l3extInstP']['attributes']['dn']
            query_url += '.json?query-target=subtree&target-subtree-class=fvRsCons'
            query_url += '&query-target-filter=eq(fvRsCons.tnVzBrCPName,"%s")' % contract_name
            resp = session.get(query_url)
            contract_data = resp.json()['imdata']
            if len(contract_data) == 0:
                all_consume = False
        if not all_consume:
            return False

        # Verify that the l3extInstP is tagged
        for l3extinstp in l3extinstp_data:
            query_url = '/api/mo/' + l3extinstp['l3extInstP']['attributes']['dn']
            query_url += '.json?query-target=subtree&target-subtree-class=tagInst'
            query_url += '&query-target-filter=eq(tagInst.name,"%s")' % tag
            resp = session.get(query_url)
            tag_data = resp.json()['imdata']
            if len(tag_data) == 0:
                return False

        return True


class TestMultisite(unittest.TestCase):
    def setup_tool(self, collector, config_params):
        # Configure all of the sites
        for site in config_params['config']:
            if 'site' in site:
                if site['site']['use_https'] == 'True':
                    use_https = True
                else:
                    use_https = False
                creds = SiteLoginCredentials(site['site']['ip_address'],
                                             site['site']['username'],
                                             site['site']['password'],
                                             use_https)
                if site['site']['local'] == 'True':
                    is_local = True
                else:
                    is_local = False

                # Set the APIC into a known state
                if use_https:
                    url = 'https://'
                else:
                    url = 'http://'
                url += site['site']['ip_address']
                session = Session(url,
                                  site['site']['username'],
                                  site['site']['password'])
                session.login(timeout=5)
                if is_local:
                    resp = setup_local_apic(session)
                else:
                    resp = setup_remote_apic(session)
                session.close()

                collector.add_site(site['site']['name'],
                                   creds,
                                   is_local)
        # Initialize the local site
        local_site = collector.get_local_site()
        if local_site is None:
            print '%% No local site configured'
            return
        local_site.initialize_from_apic()


    def setUp(self):
        global config

        assert len(config['sitetoolconfig']) == len(collectors)
        for i in range(0, len(config['sitetoolconfig'])):
            collector = collectors[i]
            config_params = config['sitetoolconfig'][i]
            self.setup_tool(collector, config_params)

    def test_export_contract(self):
        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', 'multisite-testsuite', ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Verify that the local tag was created
        mtag = MultisiteTag('http-contract', 'exported', 'Site2')
        self.assertTrue(verify_tag(local_site.session, 'multisite-testsuite', mtag))

        # Verify contract was actually pushed to the other site
        session = site1_tool.get_site('Site2').session
        self.assertTrue(has_contract(session, 'multisite-testsuite', 'Site1:http-contract'))

        # Verify that the Remote Tag was created
        mtag = MultisiteTag('http-contract', 'imported', 'Site1')
        self.assertTrue(verify_tag(session, 'multisite-testsuite', mtag))

    def test_unexport_contract(self):
        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', 'multisite-testsuite', ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Unexport the contract
        local_site.unexport_contract('http-contract', 'multisite-testsuite', 'Site2')

        # Verify that the local tag was removed
        mtag = MultisiteTag('http-contract', 'exported', 'Site2')
        self.assertFalse(verify_tag(local_site.session, 'multisite-testsuite', mtag))

        # Verify that the Remote Tag was removed
        session = site1_tool.get_site('Site2').session
        mtag = MultisiteTag('http-contract', 'imported', 'Site1')
        self.assertFalse(verify_tag(session, 'multisite-testsuite', mtag))

        # Verify contract was removed from the other site
        session = site1_tool.get_site('Site2').session
        self.assertFalse(has_contract(session, 'multisite-testsuite', 'Site1:http-contract'))

    def test_consume_contract_in_local_site(self):
        tenant_name = 'multisite-testsuite'

        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Consume the contract
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('http-contract')
        epg.consume(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Push to the local site
        resp = tenant.push_to_apic(local_site.session)
        self.assertTrue(resp.ok)

        # Verify that the EPG DB is updated
        found = False
        epgdb_entries = local_site.epg_db.find_entries(tenant.name, app.name, epg.name)
        for epgdb_entry in epgdb_entries:
            self.assertTrue(epgdb_entry.state == 'consumes')
            contract_db_entry = local_site.contract_db.find_entry(tenant.name, epgdb_entry.contract_name)
            if contract_db_entry is not None:
                found = True

        self.assertTrue(found)

    def test_consume_contract_in_remote_site(self):
        tenant_name = 'multisite-testsuite'

        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        remote_site = site1_tool.get_site('Site2')

        # Consume the contract
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('Site1:http-contract')
        epg.consume(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Push to the local site
        resp = tenant.push_to_apic(remote_site.session)
        self.assertTrue(resp.ok)

        time.sleep(2)
        local_site = site2_tool.get_local_site()
        # Verify that the EPG DB is updated
        found = False
        epgdb_entries = local_site.epg_db.find_entries(tenant.name, app.name, epg.name)
        for epgdb_entry in epgdb_entries:
            self.assertTrue(epgdb_entry.state == 'consumes')
            contract_db_entry = local_site.contract_db.find_entry(tenant.name, epgdb_entry.contract_name)
            if contract_db_entry is not None:
                found = True

        self.assertTrue(found)


    def test_unconsume_contract_in_local_site(self):
        tenant_name = 'multisite-testsuite'

        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Consume the contract
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('http-contract')
        epg.consume(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Push to the local site
        resp = tenant.push_to_apic(local_site.session)
        self.assertTrue(resp.ok)

        # Remove the consume
        epg.dont_consume(contract)
        resp = tenant.push_to_apic(local_site.session)
        self.assertTrue(resp.ok)

        # Wait for the event to clear things up
        time.sleep(2)

        # Verify that the EPG DB is updated
        found = False
        epgdb_entries = local_site.epg_db.find_entries(tenant.name, app.name, epg.name)
        for epgdb_entry in epgdb_entries:
            if epgdb_entry.state != 'consumes':
                continue
            contract_db_entry = local_site.contract_db.find_entry(tenant.name, epgdb_entry.contract_name)
            if contract_db_entry is not None:
                found = True

        self.assertFalse(found)

    def test_unconsume_contract_in_remote_site(self):
        tenant_name = 'multisite-testsuite'

        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        remote_site = site1_tool.get_site('Site2')

        # Consume the contract
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('Site1:http-contract')
        epg.consume(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Push to the remote site
        resp = tenant.push_to_apic(remote_site.session)
        self.assertTrue(resp.ok)

        # Remove the consume
        time.sleep(2)
        epg.dont_consume(contract)
        resp = tenant.push_to_apic(remote_site.session)
        self.assertTrue(resp.ok)
        time.sleep(2)

        # Verify that the EPG DB is updated
        local_site = site2_tool.get_local_site()
        found = False
        epgdb_entries = local_site.epg_db.find_entries(tenant.name, app.name, epg.name)
        for epgdb_entry in epgdb_entries:
            contract_db_entry = local_site.contract_db.find_entry(tenant.name, epgdb_entry.contract_name)
            if contract_db_entry is not None:
                found = True
        self.assertFalse(found)

    def test_consume_imported_contract(self):
        tenant_name = 'multisite-testsuite'
        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Verify that the local tag was created
        mtag = MultisiteTag('http-contract', 'exported', 'Site2')
        self.assertTrue(verify_tag(local_site.session, tenant_name, mtag))

        # Verify contract was actually pushed to the other site
        session = site1_tool.get_site('Site2').session
        self.assertTrue(has_contract(session, tenant_name, 'Site1:http-contract'))

        # Verify that the Remote Tag was created
        mtag = MultisiteTag('http-contract', 'imported', 'Site1')
        self.assertTrue(verify_tag(session, tenant_name, mtag))

        # Consume the contract on the Imported Site
        session = site1_tool.get_site('Site2').session
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('Site1:http-contract')
        epg.consume(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Add an Endpoint to the consuming EPG
        mac = '00:33:33:33:33:33'
        ip = '1.2.3.4'
        ep = Endpoint(mac, epg)
        ep.mac = mac
        ep.ip = ip
        ep.attach(vlan_intf)

        # Push to the APIC
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        # Give enough time for the event to be handled
        time.sleep(2)

        # Verify that the l3extSubnet shows up on the local
        # site (Site1) as consuming the contract
        site1_session = site1_tool.get_local_site().session
        self.assertTrue(has_l3extsubnet(site1_session, tenant_name, mac, ip))

        # Verify that the l3InstP is consuming the contract
        tag = MultisiteTag(epg.name, app.name, 'Site2')
        self.assertTrue(has_l3extInstP_consuming_contract(site1_session, tenant_name, mac, ip, 'http-contract', tag))

    def test_provide_contract_in_local_site(self):
        tenant_name = 'multisite-testsuite'

        contract_name = 'http-contract'
        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract(contract_name, tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Provide the contract
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract(contract_name)
        epg.provide(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Push to the local site
        resp = tenant.push_to_apic(local_site.session)
        self.assertTrue(resp.ok)

        time.sleep(2)

        # Verify that the EPG DB is updated
        found = False
        epgdb_entries = local_site.epg_db.find_entries(tenant.name, app.name, epg.name)
        for epgdb_entry in epgdb_entries:
            self.assertTrue(epgdb_entry.state == 'provides')
            contract_db_entry = local_site.contract_db.find_entry(tenant.name, epgdb_entry.contract_name)
            if contract_db_entry is not None:
                if contract_name == contract_db_entry.contract_name:
                    found = True
        self.assertTrue(found)

    def test_unprovide_contract_in_local_site(self):
        tenant_name = 'multisite-testsuite'

        contract_name = 'http-contract'
        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract(contract_name, tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Provide the contract
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract(contract_name)
        epg.provide(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Push to the local site
        resp = tenant.push_to_apic(local_site.session)
        self.assertTrue(resp.ok)

        time.sleep(2)

        epg.dont_provide(contract)
        resp = tenant.push_to_apic(local_site.session)
        self.assertTrue(resp.ok)

        time.sleep(2)

        # Verify that the EPG DB is updated
        found = False
        epgdb_entries = local_site.epg_db.find_entries(tenant.name, app.name, epg.name)
        for epgdb_entry in epgdb_entries:
            self.assertFalse(epgdb_entry.state == 'provides')
            contract_db_entry = local_site.contract_db.find_entry(tenant.name, epgdb_entry.contract_name)
            if contract_db_entry is not None:
                if contract_name == contract_db_entry.contract_name:
                    found = True
        self.assertFalse(found)

    def test_remove_endpoint_from_consuming_imported_contract(self):
        tenant_name = 'multisite-testsuite'
        # Export the contract
        local_site = site1_tool.get_local_site()
        problem_sites = local_site.export_contract('http-contract', tenant_name, ['Site2'])

        # Verify successful
        self.assertFalse(len(problem_sites))

        # Consume the contract on the Imported Site
        session = site1_tool.get_site('Site2').session
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('Site1:http-contract')
        epg.consume(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # "Un-consume" the contract on the Imported Site
        tenant_name = 'multisite-testsuite'
        session = site1_tool.get_site('Site2').session
        tenant = Tenant(tenant_name)
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)
        contract = Contract('Site1:http-contract')
        epg.consume(contract)
        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Add an Endpoint to the consuming EPG
        mac = '00:33:33:33:33:33'
        ip = '1.2.3.4'
        ep = Endpoint(mac, epg)
        ep.mac = mac
        ep.ip = ip
        ep.attach(vlan_intf)

        # Push to the APIC
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        # Give enough time for the event to be handled
        time.sleep(2)

        ep.mark_as_deleted()

        # Push to the APIC
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)
        time.sleep(2)

        # Verify that the l3InstP is consuming the contract
        tag = MultisiteTag(epg.name, app.name, 'Site2')
        site1_session = site1_tool.get_local_site().session
        self.assertFalse(has_l3extInstP_consuming_contract(site1_session, tenant_name, mac, ip, 'http-contract', tag))

        self.assertFalse(has_l3extsubnet(site1_session, tenant_name, mac, ip))

    def tearDown(self):
        # Delete tenant from the APIC
        for collector in collectors:
            for site in collector.get_sites():
                if site.local:
                    setup_local_apic(site.session, delete=True)
                else:
                    setup_remote_apic(site.session, delete=True)
                site.session.close()


def main():
    global config
    parser = argparse.ArgumentParser(description='ACI Multisite Test Suite')
    parser.add_argument('--config', default=None, help='Configuration file')
    parser.add_argument('unittest_args', nargs='*')
    args = parser.parse_args()

    if args.config is None:
        print '%% No configuration file given.'
        parser.print_help()
        return

    with open(args.config) as config_file:
        config = json.load(config_file)
    if 'sitetoolconfig' not in config:
        print '%% Invalid configuration file'
        return

    sys.argv[1:] = args.unittest_args
    full = unittest.TestSuite()
    full.addTest(unittest.makeSuite(TestMultisite))

    unittest.main()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass