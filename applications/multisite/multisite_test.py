from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from acitoolkit.acitoolkit import *
import time
import subprocess
import unittest
import os
import sys
from aci_multisite_config_test import setup_multisite_test
try:
    from multisite_credentials import *
except ImportError:
    print 'Please create a multisite_credentials.py file with the following variables filled in: '
    print """
    SITE1_LOGIN = ''
    SITE1_PASSWORD = ''
    SITE1_IP = ''
    SITE1_URL = ''

    SITE2_LOGIN = ''
    SITE2_PASSWORD = ''
    SITE2_IP = ''
    SITE2_URL = ''
    """
    sys.exit(0)

class TestBasicExport(unittest.TestCase):
    @staticmethod
    def _start_server(db_filename, server_port):
        os.environ["MULTISITE_DATABASE_FILE"] = db_filename
        subprocess.call(["rm", "-rf", db_filename])
        subprocess.Popen(["python", "multisite-gui.py", "--port", server_port, "--test"])
        time.sleep(1)

    @classmethod
    def setUpClass(cls):
        # Run the multisite tool for first site
        cls._start_server('site1_db.sqlite', '5000')

        # Run the multisite tool for second site
        cls._start_server('site2_db.sqlite', '5001')

        # Start the browser
        cls.driver = webdriver.Firefox()

    def _enter_credentials(self, driver, site_name, ip_address, user_name, password, local):
        # Enter the Site 1 credentials
        typing = [('site_name', site_name),
                  ('ip_address', ip_address),
                  ('user_name', user_name),
                  ('password', password)]
        for (field, data) in typing:
            input_elem = driver.find_element_by_id(field)
            input_elem.send_keys(data)
        if local:
            input_elem = driver.find_element_by_id('local')
            input_elem.click()

    def _login_session(self, url, login, password):
        session = Session(url, login, password)
        resp = session.login()
        self.assertTrue(resp.ok)
        return session


    def setup_site(self, url, site1_local=True):
        driver = self.__class__.driver
        driver.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 't')

        driver.get(url)
        assert 'ACI Multisite' in driver.title

        driver.find_element_by_link_text('Site Credentials').click()
        assert 'Site Credentials' in driver.title

        driver.find_element_by_link_text('Create').click()

        # Enter the Site 1 credentials
        self._enter_credentials(driver, 'Site1', SITE1_IP, SITE1_LOGIN,
                                SITE1_PASSWORD, site1_local)

        # Save the credentials
        input_elem = driver.find_element_by_name('_add_another')
        input_elem.click()

        # Enter the Site 2 credentials
        self._enter_credentials(driver, 'Site2', SITE2_IP, SITE2_LOGIN,
                                SITE2_PASSWORD, not site1_local)

        # Save the credentials
        input_elem = driver.find_element_by_name('_add_another')
        input_elem.click()

        # Finished, click Cancel
        input_elem = driver.find_element_by_link_text('Cancel')
        input_elem.click()

        # TODO: go to the site screen and verify that both sites are present

    def _verify_l3extsubnet(self, session, tenant_name, mac, ip, present=True):
        class_query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                           "target-subtree-class=l3extSubnet" % tenant_name)
        resp = session.get(class_query_url)
        data = resp.json()['imdata']
        if present:
            self.assertTrue(len(data))
        found = False
        for subnet in data:
            self.assertTrue('l3extSubnet' in subnet)
            dn = subnet['l3extSubnet']['attributes']['dn']
            if mac in dn and ip in dn:
                found = True
        if present:
            self.assertTrue(found)
        else:
            self.assertFalse(found)


    def test_01_site1(self):
        self.setup_site('http://127.0.0.1:5000', site1_local=True)

    def test_02_site2(self):
        self.setup_site('http://127.0.0.1:5001', site1_local=False)

    # TODO test removing a site
    # TODO test adding the same site twice
    # TODO

    def test_03_export_contract(self):
        driver = self.__class__.driver
        # Switch to the site 1 tool
        driver.get('http://127.0.0.1:5000')

        # Click on Site Contracts
        driver.find_element_by_link_text('Site Contracts').click()

        # Select the contract to export
        driver.find_element_by_xpath("//td[contains(text(),'multisite')]/preceding-sibling::td/input[@name='rowid']").click()

        # Select the pulldown
        driver.find_element_by_link_text('With selected').click()
        driver.find_element_by_link_text('Change Export Settings').click()
        assert 'Export Contracts' in driver.title

        # Check that the Sites checkbox is not checked
        checkbox = driver.find_element_by_id('sites-0')
        self.assertFalse(checkbox.is_selected())

        # Select the site
        checkbox.click()
        # Export the contract
        driver.find_element_by_id('submit').click()

        time.sleep(1)
        # Verify that the export to the other APIC was successful
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        tenants = Tenant.get_deep(session, names=['multisite'], limit_to=['fvTenant', 'vzBrCP'])
        self.assertTrue(len(tenants) > 0)
        multisite_tenant = tenants[0]
        self.assertIsNotNone(multisite_tenant.get_child(Contract, 'Site1:mysql-contract'))

    def test_04_consume_exported_contract(self):
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        # Create the Tenant
        tenant = Tenant('multisite')
        # Create the Application Profile
        app = AppProfile('my-demo-app', tenant)
        # Create the EPGs
        web_epg = EPG('web-frontend', app)
        contract = Contract('Site1:mysql-contract', tenant)
        web_epg.consume(contract)
        tenant.push_to_apic(session)

        # Verify that the EPG is indeed consuming the contract
        tenants = Tenant.get_deep(session, names=['multisite'], limit_to=['fvTenant', 'fvAp', 'fvAEPg',
                                                                          'fvRsCons', 'vzBrCP'])
        self.assertTrue(len(tenants) > 0)
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, 'web-frontend')
        self.assertIsNotNone(epg)
        contract = multisite_tenant.get_child(Contract, 'Site1:mysql-contract')
        self.assertIsNotNone(contract)
        self.assertTrue(epg.does_consume(contract))

    def test_05_add_consuming_static_endpoint(self):
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        web_epg = EPG('web-frontend', app)

        # Create the Endpoint
        ep = Endpoint('00:33:33:33:33:33', web_epg)
        ep.mac = '00:33:33:33:33:33'
        ep.ip = '2.3.4.5'

        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        web_epg.attach(vlan_intf)
        # Assign Endpoint to the L2Interface
        ep.attach(vlan_intf)

        print 'Pushing json to tenant', tenant.get_json()
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        tenants = Tenant.get_deep(session, names=['multisite'])
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, 'web-frontend')
        self.assertIsNotNone(epg)
        ep = epg.get_child(Endpoint, '00:33:33:33:33:33')
        self.assertIsNotNone(ep)

        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._verify_l3extsubnet(session,
                                 tenant_name='multisite',
                                 mac='00:33:33:33:33:33',
                                 ip='2.3.4.5/32',
                                 present=True)

    def test_06_add_providing_static_endpoint(self):
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        web_epg = EPG('database-backend', app)

        # Create the Endpoint
        ep = Endpoint('00:44:44:44:44:44', web_epg)
        ep.mac = '00:44:44:44:44:44'
        ep.ip = '7.8.9.10'

        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        web_epg.attach(vlan_intf)
        # Assign Endpoint to the L2Interface
        ep.attach(vlan_intf)

        print 'Pushing json to tenant', tenant.get_json()
        resp = tenant.push_to_apic(session)
        if not resp.ok:
            print resp, resp.text

        time.sleep(1)
        # Verify that the Endpoint was pushed successfully
        tenants = Tenant.get_deep(session, names=['multisite'])
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, 'database-backend')
        self.assertIsNotNone(epg)
        ep = epg.get_child(Endpoint, '00:44:44:44:44:44')
        self.assertIsNotNone(ep)

        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._verify_l3extsubnet(session,
                                 tenant_name = 'multisite',
                                 mac='00:44:44:44:44:44',
                                 ip='7.8.9.10/32',
                                 present=True)

    def test_07_remove_consuming_static_endpoint(self):
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        web_epg = EPG('web-frontend', app)

        # Create the Endpoint
        ep = Endpoint('00:33:33:33:33:33', web_epg)
        ep.mac = '00:33:33:33:33:33'
        ep.ip = '2.3.4.5'

        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        web_epg.attach(vlan_intf)
        # Assign Endpoint to the L2Interface
        ep.attach(vlan_intf)

        # Mark the Endpoint as deleted
        ep.mark_as_deleted()

        print 'Pushing json to tenant', tenant.get_json()
        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        # Verify that the Endpoint has been removed
        time.sleep(1)
        tenants = Tenant.get_deep(session, names=['multisite'])
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, 'web-frontend')
        self.assertIsNotNone(epg)
        ep = epg.get_child(Endpoint, '00:33:33:33:33:33')
        self.assertIsNone(ep)

        # Verify that the l3extSubnet has been removed from the other site
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._verify_l3extsubnet(session,
                                 tenant_name = 'multisite',
                                 mac='00:33:33:33:33:33',
                                 ip='2.3.4.5/32',
                                 present=False)

    @classmethod
    def tearDownClass(cls):
        driver = cls.driver
        driver.get('http://127.0.0.1:5000/shutdown')
        driver.get('http://127.0.0.1:5001/shutdown')
        driver.close()


def verify_remote_l3extsubnet(session, mac):
    class_query_url = ('/api/mo/uni/tn-multisite/out-multisite-l3out.json?'
                       'query-target=subtree&target-subtree-class=l3extSubnet'
                       '&rsp-prop-include=config-only')
    resp = session.get(class_query_url)
    data = resp.json()['imdata']
    for item in data:
        print 'ITEM:', item

# session1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
# resp = session1.login()
# if not resp.ok:
#     print "%% Couldn't login to APIC"
#
# session2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
# resp = session2.login()
# if not resp.ok:
#     print "%% Couldn't login to APIC"
#
# # Start applications
# print 'starting app'
# subprocess.Popen(["python", "multisite-gui.py", "--port", "5000", "--test"])
#
# time.sleep(2)

setup_multisite_test(delete=True)
setup_multisite_test()
live = unittest.TestSuite()
live.addTest(unittest.makeSuite(TestBasicExport))
unittest.main(defaultTest='live')


#test_export_contract()
#test_consume_exported_contract(session1)
#test_add_consuming_static_endpoint(session1)
#test_add_providing_static_endpoint(session2)
# print 'Verify session1'
#verify_remote_l3extsubnet(session1, mac='')
#print 'Verify session2'
#verify_remote_l3extsubnet(session2, mac='')
#driver.close()
