from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from acitoolkit.acitoolkit import *
from multisite import MultisiteTag
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

SITE1_FILENAME = 'site1_db.sqlite'
SITE1_GUI = 'http://127.0.0.1:5000'
SITE2_FILENAME = 'site2_db.sqlite'
SITE2_GUI = 'http://127.0.0.1:5001'


class TestSite(object):
    def __init__(self):
        self.name = None
        self.username = None
        self.password = None
        self.ip = None
        self.url = None


class TestBasicExport(unittest.TestCase):
    @staticmethod
    def _start_server(db_filename, server_port):
        """
        Start the GUI server application using a certain filename and TCP port

        :param db_filename: String containing the database filename
        :param server_port: String containing the TCP L4 port number to host the application
        """
        os.environ["MULTISITE_DATABASE_FILE"] = db_filename
        subprocess.call(["rm", "-rf", db_filename])
        subprocess.Popen(["python", "multisite-gui.py", "--port", server_port, "--test"])
        time.sleep(1)

    def setUp(self):
        time.sleep(2)

    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment
        Run the application for 2 sites and start a web browser to access them
        """
        setup_multisite_test(delete=True)
        setup_multisite_test()

        # Run the multisite tool for first site
        cls._start_server(SITE1_FILENAME, SITE1_GUI.split(':')[2])

        # Run the multisite tool for second site
        cls._start_server(SITE2_FILENAME, SITE2_GUI.split(':')[2])

        # Start the browser
        cls.driver = webdriver.Firefox()

    def _enter_credentials(self, driver, site_name, ip_address, user_name, password, local):
        """
        Enter the site credentials into the GUI

        :param driver: Instance of webdriver
        :param site_name: String containing the site name
        :param ip_address: String containing the APIC IP address of the site
        :param user_name: String containing the APIC username of the site
        :param password: String containing the APIC password of the site
        :param local: True or False.  True if this site is the local site for the tool.
        :return: None
        """
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
        """
        Login to a particular APIC

        :param url: String containing the URL to login to the APIC
        :param login: String containing the username to login to the APIC
        :param password: String containing the password to login to the APIC
        :return: Instance of Session class
        """
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
        assert input_elem is not None
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

    def teardown_site(self, url):
        driver = self.__class__.driver
        time.sleep(1)
        driver.get(url)
        driver.find_element_by_link_text('Site Credentials').click()
        assert 'Site Credentials' in driver.title
        try:
            driver.find_element_by_xpath("//td[text()='Site1']/preceding-sibling::td/input[@name='rowid']").click()
        except NoSuchElementException:
            self.fail('Could not find Site1')
        try:
            driver.find_element_by_xpath("//td[text()='Site2']/preceding-sibling::td/input[@name='rowid']").click()
        except NoSuchElementException:
            self.fail('Could not find Site2')
        driver.find_element_by_link_text('With selected').click()
        driver.find_element_by_link_text('Delete').click()
        driver.switch_to.alert.accept()
        time.sleep(1)

    def _verify_tag(self, session, tenant_name, tag, exists=True):
        class_query_url = ('/api/mo/uni/tn-%s.json?query-target=subtree&'
                           'target-subtree-class=tagInst&'
                           'query-target-filter=eq(tagInst.name,"%s")' % (tenant_name, tag))
        resp = session.get(class_query_url)
        data = resp.json()['imdata']
        if exists:
            self.assertTrue(len(data))
        else:
            self.assertFalse(len(data))

    def _has_l3extsubnet(self, session, tenant_name, mac, ip):
        class_query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                           "target-subtree-class=l3extSubnet" % tenant_name)
        resp = session.get(class_query_url)
        data = resp.json()['imdata']
        if len(data) == 0:
            return False
        found = False
        for subnet in data:
            self.assertTrue('l3extSubnet' in subnet)
            dn = subnet['l3extSubnet']['attributes']['dn']
            if mac in dn and ip in dn:
                found = True
        return found

    def _assert_all_l3extsubnets_are_removed(self, session, tenant_name):
        # Get all of the l3extOuts in the tenant
        query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                     "target-subtree-class=l3extOut" % tenant_name)
        resp = session.get(query_url)
        l3extout_data = resp.json()['imdata']
        self.assertTrue(len(l3extout_data))

        for l3extout in l3extout_data:
            l3extout_name = l3extout['l3extOut']['attributes']['name']
            # Verify that the l3extSubnet is not in each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extSubnet' % (tenant_name, l3extout_name))
            resp = session.get(query_url)
            l3extsubnet_data = resp.json()['imdata']
            self.assertFalse(len(l3extsubnet_data))

            # Verify that the l3extInstP is not in each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extInstP' % (tenant_name, l3extout_name))
            resp = session.get(query_url)
            l3extinstp_data = resp.json()['imdata']
            self.assertFalse(len(l3extinstp_data))

    def _assert_l3extsubnet_does_not_exist(self, session, tenant_name, mac, ip):
        time.sleep(2)
        # Get all of the l3extOuts in the tenant
        query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                     "target-subtree-class=l3extOut" % tenant_name)
        resp = session.get(query_url)
        l3extout_data = resp.json()['imdata']
        self.assertTrue(len(l3extout_data))

        for l3extout in l3extout_data:
            l3extout_name = l3extout['l3extOut']['attributes']['name']
            # Verify that the l3extSubnet is not in each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extSubnet'
                         '&query-target-filter=eq(l3extSubnet.ip,"%s/32")' % (tenant_name, l3extout_name, ip))
            resp = session.get(query_url)
            l3extsubnet_data = resp.json()['imdata']
            self.assertFalse(len(l3extsubnet_data))

            # Verify that the l3extInstP is not in each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extInstP' % (tenant_name, l3extout_name))
            resp = session.get(query_url)
            l3extinstp_data = resp.json()['imdata']
            self.assertFalse(len(l3extinstp_data))

    def _assert_l3extsubnet_exists(self, session, tenant_name, mac, ip):
        # Get all of the l3extOuts in the tenant
        query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                     "target-subtree-class=l3extOut" % tenant_name)
        resp = session.get(query_url)
        l3extout_data = resp.json()['imdata']
        self.assertTrue(len(l3extout_data))

        for l3extout in l3extout_data:
            l3extout_name = l3extout['l3extOut']['attributes']['name']
            # Verify that the l3extSubnet is in each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extSubnet'
                         '&query-target-filter=eq(l3extSubnet.ip,"%s/32")' % (tenant_name, l3extout_name, ip))
            resp = session.get(query_url)
            l3extsubnet_data = resp.json()['imdata']
            self.assertTrue(len(l3extsubnet_data))

            # Verify that the l3extInstP is each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extInstP' % (tenant_name, l3extout_name))
            resp = session.get(query_url)
            l3extinstp_data = resp.json()['imdata']
            self.assertTrue(len(l3extinstp_data))

    def _assert_l3extsubnet_consumes_contract(self, session, tenant_name, mac, ip, contract_name):
        # Get all of the l3extOuts in the tenant
        query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                     "target-subtree-class=l3extOut" % tenant_name)
        resp = session.get(query_url)
        l3extout_data = resp.json()['imdata']
        self.assertTrue(len(l3extout_data))

        for l3extout in l3extout_data:
            l3extout_name = l3extout['l3extOut']['attributes']['name']
            # Verify that the l3extSubnet is in each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extSubnet'
                         '&query-target-filter=eq(l3extSubnet.ip,"%s/32")' % (tenant_name, l3extout_name, ip))
            resp = session.get(query_url)
            l3extsubnet_data = resp.json()['imdata']
            self.assertTrue(len(l3extsubnet_data))

            # Verify that the l3extInstP is each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extInstP' % (tenant_name, l3extout_name))
            resp = session.get(query_url)
            l3extinstp_data = resp.json()['imdata']
            self.assertTrue(len(l3extinstp_data))

            # Verify that the l3extInstP is consuming the contract
            for l3extinstp in l3extinstp_data:
                query_url = '/api/mo/' + l3extinstp['l3extInstP']['attributes']['dn']
                query_url += '.json?query-target=subtree&target-subtree-class=fvRsCons'
                query_url += '&query-target-filter=eq(fvRsCons.tnVzBrCPName,"%s")' % contract_name
                resp = session.get(query_url)
                contract_data = resp.json()['imdata']
                self.assertTrue(len(contract_data))

    def _assert_l3extsubnet_provides_contract(self, session, tenant_name, mac, ip, contract_name):
        # Get all of the l3extOuts in the tenant
        query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                     "target-subtree-class=l3extOut" % tenant_name)
        resp = session.get(query_url)
        l3extout_data = resp.json()['imdata']
        self.assertTrue(len(l3extout_data))

        for l3extout in l3extout_data:
            l3extout_name = l3extout['l3extOut']['attributes']['name']
            # Verify that the l3extSubnet is in each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extSubnet'
                         '&query-target-filter=eq(l3extSubnet.ip,"%s/32")' % (tenant_name, l3extout_name, ip))
            resp = session.get(query_url)
            l3extsubnet_data = resp.json()['imdata']
            self.assertTrue(len(l3extsubnet_data))

            # Verify that the l3extInstP is each l3extOut
            query_url = ('/api/mo/uni/tn-%s/out-%s.json?query-target=subtree&'
                         'target-subtree-class=l3extInstP' % (tenant_name, l3extout_name))
            resp = session.get(query_url)
            l3extinstp_data = resp.json()['imdata']
            self.assertTrue(len(l3extinstp_data))

            # Verify that the l3extInstP is providing the contract
            for l3extinstp in l3extinstp_data:
                query_url = '/api/mo/' + l3extinstp['l3extInstP']['attributes']['dn']
                query_url += '.json?query-target=subtree&target-subtree-class=fvRsProv'
                query_url += '&query-target-filter=eq(fvRsProv.tnVzBrCPName,"%s")' % contract_name
                resp = session.get(query_url)
                contract_data = resp.json()['imdata']
                self.assertTrue(len(contract_data))

    def _verify_l3extsubnet(self, session, tenant_name, mac, ip, present=True):
        # TODO need to check each l3extOut on the site
        class_query_url = ("/api/mo/uni/tn-%s.json?query-target=subtree&"
                           "target-subtree-class=l3extOut" % tenant_name)
        resp = session.get(class_query_url)
        data = resp.json()['imdata']
        if len(data) == 0:
            return False

        found = self._has_l3extsubnet(session, tenant_name, mac, ip)
        if present:
            self.assertTrue(found)
        else:
            self.assertFalse(found)

    def setup_and_teardown_test(self, url, site1_local):
        self.setup_site(url, site1_local)
        driver = self.__class__.driver
        try:
            driver.find_element_by_xpath("//td[text()='Site1']/preceding-sibling::td/input[@name='rowid']")
        except NoSuchElementException:
            self.fail('Could not find Site1')
        try:
            driver.find_element_by_xpath("//td[text()='Site2']/preceding-sibling::td/input[@name='rowid']")
        except NoSuchElementException:
            self.fail('Could not find Site2')
        self.teardown_site(url)

    def test_site1(self):
        self.setup_and_teardown_test(SITE1_GUI, site1_local=True)

    def test_site2(self):
        self.setup_and_teardown_test(SITE2_GUI, site1_local=False)

    # def test_03_remove_site1(self):
    #     pass  # TODO implement and renumber tests
    #
    # def test_04_remove_site2(self):
    #     pass  # TODO implement and renumber tests
    #
    # def test_05_add_same_site_twice
    # # TODO test removing a site
    # # TODO test adding the same site twice
    # # TODO

    def click_on_contract(self, contract_name):
        driver = self.__class__.driver
        # Select the contract to export
        page_number = '2'
        loop_again = True
        while loop_again:
            loop_again = False
            try:
                driver.find_element_by_xpath("//td[text()='%s']/preceding-sibling::td/input[@name='rowid']" % contract_name).click()
            except NoSuchElementException:
                loop_again = True
                driver.find_element_by_link_text(page_number).click()
                page_number = str(int(page_number) + 1)

    def export_contract(self, url):
        driver = self.__class__.driver
        # Switch to the site 1 tool
        driver.get(url)

        # Click on Site Contracts
        driver.find_element_by_link_text('Site Contracts').click()

        self.click_on_contract('multisite_mysqlcontract')

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
        self.assertIsNotNone(multisite_tenant.get_child(Contract, 'Site1:multisite_mysqlcontract'))

        # Verify that the tag is saved in the remote site
        mtag = MultisiteTag('multisite_mysqlcontract', 'imported', 'Site1')
        self._verify_tag(session, 'multisite', str(mtag))

        # Verify that the tag is saved locally
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        mtag = MultisiteTag('multisite_mysqlcontract', 'exported', 'Site2')
        self._verify_tag(session, 'multisite', str(mtag))

        # TODO Verify that the DBs are as expected

    def setup_export_contract(self):
        self.setup_site(SITE1_GUI, site1_local=True)
        self.setup_site(SITE2_GUI, site1_local=False)
        self.export_contract(SITE1_GUI)

    def unexport_contract(self, url):
        time.sleep(5)

        driver = self.__class__.driver
        # Switch to the site 1 tool
        driver.get(url)

        # Click on Site Contracts
        driver.find_element_by_link_text('Site Contracts').click()

        self.click_on_contract('multisite_mysqlcontract')

        # Select the pulldown
        driver.find_element_by_link_text('With selected').click()
        driver.find_element_by_link_text('Change Export Settings').click()
        assert 'Export Contracts' in driver.title

        # Check that the Sites checkbox is checked
        checkbox = driver.find_element_by_id('sites-0')
        self.assertTrue(checkbox.is_selected())

        # Select the site
        checkbox.click()
        # Export the contract
        driver.find_element_by_id('submit').click()

        time.sleep(1)

        # Verify that the unexport from the other APIC was successful
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        tenants = Tenant.get_deep(session, names=['multisite'], limit_to=['fvTenant', 'vzBrCP'])
        self.assertTrue(len(tenants) > 0)
        multisite_tenant = tenants[0]
        self.assertIsNone(multisite_tenant.get_child(Contract, 'Site1:multisite_mysqlcontract'))

        # Verify that the tag is removed in the remote site
        mtag = MultisiteTag('multisite_mysqlcontract', 'imported', 'Site1')
        self._verify_tag(session, 'multisite', str(mtag), exists=False)

        # Verify that the tag is removed locally
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        mtag = MultisiteTag('multisite_mysqlcontract', 'exported', 'Site2')
        self._verify_tag(session, 'multisite', str(mtag), exists=False)

        # TODO: Verify that the contract still exists on the local site

        # TODO Verify that the DBs are as expected

    def teardown_export_contract(self):
        self.unexport_contract(SITE1_GUI)
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._assert_all_l3extsubnets_are_removed(session, 'multisite')
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._assert_all_l3extsubnets_are_removed(session, 'multisite')
        self.teardown_site(SITE1_GUI)
        self.teardown_site(SITE2_GUI)

    def test_export_contract(self):
        self.setup_export_contract()
        self.teardown_export_contract()

    def consume_exported_contract(self, epg_name='web-frontend'):
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        # Create the Tenant
        tenant = Tenant('multisite')
        # Create the Application Profile
        app = AppProfile('my-demo-app', tenant)
        # Create the EPGs
        web_epg = EPG(epg_name, app)
        contract = Contract('Site1:multisite_mysqlcontract', tenant)
        web_epg.consume(contract)
        tenant.push_to_apic(session)

        # Verify that the EPG is indeed consuming the contract
        tenants = Tenant.get_deep(session, names=['multisite'], limit_to=['fvTenant', 'fvAp', 'fvAEPg',
                                                                          'fvRsCons', 'vzBrCP'])
        self.assertTrue(len(tenants) > 0)
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, epg_name)
        self.assertIsNotNone(epg)
        contract = multisite_tenant.get_child(Contract, 'Site1:multisite_mysqlcontract')
        self.assertIsNotNone(contract)
        self.assertTrue(epg.does_consume(contract))

    def unconsume_exported_contract(self, epg_name):
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        # Create the Tenant
        tenant = Tenant('multisite')
        # Create the Application Profile
        app = AppProfile('my-demo-app', tenant)
        # Create the EPGs
        web_epg = EPG(epg_name, app)
        contract = Contract('Site1:multisite_mysqlcontract', tenant)
        web_epg.consume(contract)
        web_epg.dont_consume(contract)
        resp = tenant.push_to_apic(session)
        if not resp.ok:
            print resp, resp.text
            self.assertTrue(resp.ok)

    def test_consume_exported_contract(self):
        self.setup_export_contract()
        self.consume_exported_contract()
        self.teardown_export_contract()

    def add_consuming_static_endpoint(self, mac, ip, site1=False, epg_name='web-frontend'):
        if site1:
            session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        else:
            session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        web_epg = EPG(epg_name, app)

        # Create the Endpoint
        ep = Endpoint(mac, web_epg)
        ep.mac = mac
        ep.ip = ip

        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        web_epg.attach(vlan_intf)
        # Assign Endpoint to the L2Interface
        ep.attach(vlan_intf)

        resp = tenant.push_to_apic(session)
        self.assertTrue(resp.ok)

        tenants = Tenant.get_deep(session, names=['multisite'])
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, epg_name)
        self.assertIsNotNone(epg)
        ep = epg.get_child(Endpoint, mac)
        self.assertIsNotNone(ep)

        if site1:
            session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        else:
            session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._assert_l3extsubnet_exists(session,
                                        tenant_name='multisite',
                                        mac=mac,
                                        ip=ip)

    def remove_consuming_static_endpoint(self, mac, ip):
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        web_epg = EPG('web-frontend', app)

        # Create the Endpoint
        ep = Endpoint(mac, web_epg)
        ep.mac = mac
        ep.ip = ip

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
        ep = epg.get_child(Endpoint, mac)
        self.assertIsNone(ep)

    def remove_providing_static_endpoint(self, mac, ip):
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        web_epg = EPG('database-backend', app)

        # Create the Endpoint
        ep = Endpoint(mac, web_epg)
        ep.mac = mac
        ep.ip = ip

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
        ep = epg.get_child(Endpoint, mac)
        self.assertIsNone(ep)

    def test_add_consuming_static_endpoint(self):
        self.setup_export_contract()
        self.consume_exported_contract()
        mac = '00:33:33:33:33:33'
        ip = '2.3.4.5'
        self.add_consuming_static_endpoint(mac, ip)

        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._assert_l3extsubnet_consumes_contract(session, 'multisite', mac, ip, 'multisite_mysqlcontract')
        # TODO teardown properly
        self.teardown_export_contract()

    def test_add_consuming_static_endpoint_on_both_sites(self):
        self.setup_export_contract()
        self.consume_exported_contract()

        self.add_consuming_static_endpoint('00:33:33:33:33:33', '2.3.4.5')
        self.add_consuming_static_endpoint('00:33:33:33:33:34', '2.3.4.6', site1=True, epg_name='web-frontend')

        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._assert_l3extsubnet_consumes_contract(session, 'multisite', '00:33:33:33:33:33', '2.3.4.5', 'multisite_mysqlcontract')
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._assert_l3extsubnet_consumes_contract(session, 'multisite', '00:33:33:33:33:34', '2.3.4.6', 'Site1:multisite_mysqlcontract')

        # TODO teardown properly
        self.teardown_export_contract()

    def test_preexisting_endpoints_consume_imported_contract(self):
        self.setup_export_contract()
        self.consume_exported_contract()

        session2 = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        new_epg_name = 'another-epg'
        web_epg = EPG(new_epg_name, app)

        # Create the Endpoint
        mac = '00:77:55:44:33:22'
        ip = '8.3.2.1'
        ep = Endpoint(mac, web_epg)
        ep.mac = mac
        ep.ip = ip

        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        web_epg.attach(vlan_intf)
        # Assign Endpoint to the L2Interface
        ep.attach(vlan_intf)

        resp = tenant.push_to_apic(session2)
        self.assertTrue(resp.ok)

        self.consume_exported_contract(epg_name=new_epg_name)

        tenants = Tenant.get_deep(session2, names=['multisite'])
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, new_epg_name)
        self.assertIsNotNone(epg)
        multisite_ep = epg.get_child(Endpoint, mac)
        self.assertIsNotNone(multisite_ep)

        session1 = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._assert_l3extsubnet_exists(session1,
                                        tenant_name='multisite',
                                        mac=mac,
                                        ip=ip)

        self.unconsume_exported_contract(new_epg_name)
        time.sleep(2)

        self._assert_l3extsubnet_does_not_exist(session1,
                                                tenant_name='multisite',
                                                mac=mac,
                                                ip=ip)
        web_epg.mark_as_deleted()
        tenant.push_to_apic(session2)

        time.sleep(1)

        self.teardown_export_contract()

    def test_add_multiple_consuming_static_endpoints(self):
        self.setup_export_contract()
        self.consume_exported_contract()

        self.add_consuming_static_endpoint('00:33:33:33:33:33', '2.3.4.5')
        self.add_consuming_static_endpoint('00:33:33:33:33:34', '2.3.4.6')

        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._assert_l3extsubnet_exists(session, 'multisite', '00:33:33:33:33:33', '2.3.4.5')
        self._assert_l3extsubnet_exists(session, 'multisite', '00:33:33:33:33:34', '2.3.4.6')

        self.teardown_export_contract()

    def add_providing_static_endpoint(self, mac, ip):
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)

        tenant = Tenant('multisite')
        app = AppProfile('my-demo-app', tenant)
        web_epg = EPG('database-backend', app)

        # Create the Endpoint
        ep = Endpoint(mac, web_epg)
        ep.mac = mac
        ep.ip = ip

        intf = Interface('eth', '1', '101', '1', '38')
        # Create a VLAN interface and attach to the physical interface
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)
        # Attach the EPG to the VLAN interface
        web_epg.attach(vlan_intf)
        # Assign Endpoint to the L2Interface
        ep.attach(vlan_intf)

        resp = tenant.push_to_apic(session)
        if not resp.ok:
            self.assertTrue(resp.ok)
            print resp, resp.text

        time.sleep(1)
        # Verify that the Endpoint was pushed successfully
        tenants = Tenant.get_deep(session, names=['multisite'])
        multisite_tenant = tenants[0]
        app = multisite_tenant.get_child(AppProfile, 'my-demo-app')
        self.assertIsNotNone(app)
        epg = app.get_child(EPG, 'database-backend')
        self.assertIsNotNone(epg)
        ep = epg.get_child(Endpoint, mac)
        self.assertIsNotNone(ep)

        # Verify that the entry was pushed to the other site
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._assert_l3extsubnet_exists(session,
                                        tenant_name='multisite',
                                        mac=mac,
                                        ip=ip)

    def test_add_providing_static_endpoint(self):
        self.setup_export_contract()
        self.consume_exported_contract()

        self.add_providing_static_endpoint('00:44:44:44:44:44', '7.8.9.10')

        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._assert_l3extsubnet_provides_contract(session,
                                                   tenant_name='multisite',
                                                   mac='00:44:44:44:44:44',
                                                   ip='7.8.9.10',
                                                   contract_name='Site1:multisite_mysqlcontract')
        self.remove_providing_static_endpoint('00:44:44:44:44:44', '7.8.9.10')
        self.teardown_export_contract()

    def test_add_multiple_providing_static_endpoint(self):
        self.setup_export_contract()
        self.consume_exported_contract()

        self.add_providing_static_endpoint('00:44:44:44:44:44', '7.8.9.10')
        self.add_providing_static_endpoint('00:44:44:44:44:45', '7.8.9.11')

        # Make sure that the first endpoint is still pushed to the other site
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._assert_l3extsubnet_exists(session,
                                        tenant_name='multisite',
                                        mac='00:44:44:44:44:44',
                                        ip='7.8.9.10')
        self._assert_l3extsubnet_exists(session,
                                        tenant_name='multisite',
                                        mac='00:44:44:44:44:45',
                                        ip='7.8.9.11')

        self.remove_providing_static_endpoint('00:44:44:44:44:44', '7.8.9.10')
        self.remove_providing_static_endpoint('00:44:44:44:44:45', '7.8.9.11')

        self.teardown_export_contract()

    # def test_remove_providing_static_endpoint(self):
    #     self.setup_export_contract()
    #     self.consume_exported_contract()
    #     self.add_providing_static_endpoint('00:33:33:33:33:33', '2.3.4.5')
    #     self.remove_providing_static_endpoint('00:33:33:33:33:33', '2.3.4.5')
    #
    #     # Verify that the l3extSubnet has been removed from the other site
    #     session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
    #     self._verify_l3extsubnet(session,
    #                              tenant_name = 'multisite',
    #                              mac='00:33:33:33:33:33',
    #                              ip='2.3.4.5/32',
    #                              present=False)
    #     self.teardown_export_contract()

    def test_remove_consuming_static_endpoint(self):
        self.setup_export_contract()
        self.consume_exported_contract()
        self.add_consuming_static_endpoint('00:33:33:33:33:33', '2.3.4.5')
        self.remove_consuming_static_endpoint('00:33:33:33:33:33', '2.3.4.5')

        # Verify that the l3extSubnet has been removed from the other site
        session = self._login_session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        self._verify_l3extsubnet(session,
                                 tenant_name='multisite',
                                 mac='00:33:33:33:33:33',
                                 ip='2.3.4.5/32',
                                 present=False)
        self.teardown_export_contract()

    def test_remove_one_of_multiple_consuming_static_endpoints(self):
        self.setup_export_contract()
        self.consume_exported_contract()

        # Add 2 static endpoints
        self.add_consuming_static_endpoint('00:33:33:33:33:33', '2.3.4.5')
        self.add_consuming_static_endpoint('00:33:33:33:33:34', '2.3.4.6')

        # Verify that the 2 l3extsubnets are there
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._verify_l3extsubnet(session,
                                 tenant_name='multisite',
                                 mac='00:33:33:33:33:33',
                                 ip='2.3.4.5/32',
                                 present=True)
        self._verify_l3extsubnet(session,
                                 tenant_name='multisite',
                                 mac='00:33:33:33:33:34',
                                 ip='2.3.4.6/32',
                                 present=True)

        # Remove one of the static endpoints
        self.remove_consuming_static_endpoint('00:33:33:33:33:33', '2.3.4.5')

        # Verify that the l3extSubnet has been removed from the other site
        session = self._login_session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        self._verify_l3extsubnet(session,
                                 tenant_name='multisite',
                                 mac='00:33:33:33:33:33',
                                 ip='2.3.4.5/32',
                                 present=False)
        # Verify that the remaining l3extSubnet is still there
        self._verify_l3extsubnet(session,
                                 tenant_name='multisite',
                                 mac='00:33:33:33:33:34',
                                 ip='2.3.4.6/32',
                                 present=True)
        self.teardown_export_contract()

    @classmethod
    def tearDownClass(cls):
        driver = cls.driver
        time.sleep(1)
        driver.get(SITE1_GUI + '/shutdown')
        driver.get(SITE2_GUI + '/shutdown')
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

# setup_multisite_test(delete=True)
# setup_multisite_test()
live = unittest.TestSuite()
live.addTest(unittest.makeSuite(TestBasicExport))
unittest.main(defaultTest='live')

# test_export_contract()
# test_consume_exported_contract(session1)
# test_add_consuming_static_endpoint(session1)
# test_add_providing_static_endpoint(session2)
# print 'Verify session1'
# verify_remote_l3extsubnet(session1, mac='')
# print 'Verify session2'
# verify_remote_l3extsubnet(session2, mac='')
# driver.close()
