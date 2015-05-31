from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from acitoolkit.acitoolkit import *
import time
import subprocess
import unittest
import os
import sys

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

# driver.get(SITE1_URL)
# driver.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 't')
# driver.get(SITE2_URL)
# driver.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 't')

class TestBasicExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):


        # Run the multisite tool for first site
        site1_db_filename = "site1_db.sqlite"
        os.environ["MULTISITE_DATABASE_FILE"] = site1_db_filename
        subprocess.call(["rm", "-rf", site1_db_filename])
        subprocess.Popen(["python", "multisite-gui.py", "--port", "5000", "--test"])
        time.sleep(1)

        # Run the multisite tool for second site
        site2_db_filename = "site2_db.sqlite"
        os.environ["MULTISITE_DATABASE_FILE"] = site2_db_filename
        subprocess.call(["rm", "-rf", site2_db_filename])
        subprocess.Popen(["python", "multisite-gui.py", "--port", "5001", "--test"])
        time.sleep(1)

        cls.driver = webdriver.Firefox()

    def setup_site(self, url, site1_local=True):
        # driver = webdriver.Firefox()
        # driver.maximize_window()
        driver = self.__class__.driver
        driver.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 't')

        driver.get(url)
        assert 'ACI Multisite' in driver.title


        driver.find_element_by_link_text('Site Credentials').click()
        assert 'Site Credentials' in driver.title


        driver.find_element_by_link_text('Create').click()



        # Enter the Site 1 credentials
        typing = [('site_name', 'Site1'),
                  ('ip_address', SITE1_IP),
                  ('user_name', 'admin'),
                  ('password', 'ins3965!')]
        for (field, data) in typing:
            input_elem = driver.find_element_by_id(field)
            input_elem.send_keys(data)
        if site1_local:
            input_elem = driver.find_element_by_id('local')
            input_elem.click()



        # Save the credentials
        input_elem = driver.find_element_by_name('_add_another')
        input_elem.click()



        # Enter the Site 2 credentials
        typing = [('site_name', 'Site2'),
                  ('ip_address', SITE2_IP),
                  ('user_name', 'admin'),
                  ('password', 'ins3965!')]
        for (field, data) in typing:
            input_elem = driver.find_element_by_id(field)
            input_elem.send_keys(data)
        if not site1_local:
            input_elem = driver.find_element_by_id('local')
            input_elem.click()



        # Save the credentials
        input_elem = driver.find_element_by_name('_add_another')
        input_elem.click()



        # Finished, click Cancel
        input_elem = driver.find_element_by_link_text('Cancel')
        input_elem.click()

        # TODO: go to the site screen and verify that both sites are present

    def test_01_site1(self):
        self.setup_site('http://127.0.0.1:5000', site1_local=True)

    def test_02_site2(self):
        self.setup_site('http://127.0.0.1:5001', site1_local=False)

    def test_03_export_contract(self):
        driver = self.__class__.driver
        # Switch to the second site tool
        driver.get('http://127.0.0.1:5001')

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

        # Verify that the export to the other APIC was successful
        session = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)
        tenants = Tenant.get_deep(session, names=['multisite'], limit_to=['fvTenant', 'vzBrCP'])
        self.assertTrue(len(tenants) > 0)
        multisite_tenant = tenants[0]
        contracts = multisite_tenant.get_children(only_class=Contract)
        found = False
        for contract in contracts:
            if contract.name == 'Site2:mysql-contract':
                found = True
                break
        self.assertTrue(found)

    def test_04_consume_exported_contract(self):
        time.sleep(1)

        session = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)

        # Create the Tenant
        tenant = Tenant('multisite')
        # Create the Application Profile
        app = AppProfile('my-demo-app', tenant)
        # Create the EPGs
        web_epg = EPG('web-frontend', app)
        contract = Contract('Site2:mysql-contract', tenant)
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
        contract = multisite_tenant.get_child(Contract, 'Site2:mysql-contract')
        self.assertIsNotNone(contract)
        self.assertTrue(epg.does_consume(contract))

    def test_05_add_consuming_static_endpoint(self):
        session = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = session.login()
        self.assertTrue(resp.ok)

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

    @classmethod
    def tearDownClass(cls):
        driver = cls.driver
        driver.get('http://127.0.0.1:5000/shutdown')
        driver.get('http://127.0.0.1:5001/shutdown')
        driver.close()




def test_add_providing_static_endpoint(session):
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
