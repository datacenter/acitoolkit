import unittest
from acitoolkit import *
from intersite import *
from StringIO import StringIO
import mock
import sys

if sys.version_info.major == 2:
    import __builtin__ as builtins
else:
    import builtins
import json
import time
from requests import ConnectionError

try:
    from multisite_test_credentials import *
except ImportError:
    print '''
            Please create a file called multisite_test_credentials.py with the following:

            SITE1_IPADDR = ''
            SITE1_LOGIN = ''
            SITE1_PASSWORD = ''
            SITE1_URL = 'http://' + SITE1_IPADDR  # change http to https for SSL

            SITE2_IPADDR = ''
            SITE2_LOGIN = ''
            SITE2_PASSWORD = ''
            SITE2_URL = 'http://' + SITE2_IPADDR
            '''
    sys.exit(0)


class FakeStdio(object):
    def __init__(self):
        self.output = []

    def write(self, *args, **kwargs):
        for arg in args:
            self.output.append(arg)

    def verify_output(self, output):
        return output == self.output


class TestToolOptions(unittest.TestCase):
    def get_logging_level(self):
        return logging.getLevelName(logging.getLogger().getEffectiveLevel())

    def test_no_options(self):
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = None
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            execute_tool(args)
            self.assertEqual(fake_out.getvalue(), '%% No configuration file given.\n')

    def test_generateconfig(self):
        args = mock.Mock()
        args.debug = None
        args.generateconfig = True
        args.config = None
        expected_text = ('Sample configuration file written to sample_config.json\n'
                         "Replicate the site JSON for each site.\n"
                         "    Valid values for use_https and local are 'True' and 'False'\n"
                         "    One site must have local set to 'True'\n"
                         'Replicate the export JSON for each exported contract.\n')
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            execute_tool(args)
            self.assertEqual(fake_out.getvalue(), expected_text)

    def test_config_bad_filename(self):
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = 'jkdhfdskjfhdsfkjhdsfdskjhf.jdkhfkfjh'
        expected_text = '%% Unable to open configuration file jkdhfdskjfhdsfkjhdsfdskjhf.jdkhfkfjh\n'
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            execute_tool(args)
            self.assertEqual(fake_out.getvalue(), expected_text)


class TestBadConfiguration(unittest.TestCase):
    def create_empty_config_file(self):
        config = {
            "config": [
                {
                    "site": {
                        "username": "",
                        "name": "",
                        "ip_address": "",
                        "password": "",
                        "local": "",
                        "use_https": ""
                    }
                }
            ]
        }
        return config

    def get_args(self):
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = 'doesntmatter'
        return args

    def test_no_config_keyword(self):
        args = self.get_args()
        config = {
            "site": {
                "username": "",
                "name": "",
                "ip_address": "",
                "password": "",
                "local": "",
                "use_https": ""
            }
        }
        temp = sys.stdout
        fake_out = FakeStdio()
        sys.stdout = fake_out

        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)
        sys.stdout = temp
        self.assertTrue(fake_out.verify_output(['%% Invalid configuration file', '\n']))

    def test_site_with_bad_ipaddress(self):
        args = self.get_args()
        config = self.create_empty_config_file()
        config['config'][0]['site']['ipaddress'] = 'bogu$'
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            self.assertRaises(ValueError, execute_tool, args, test_mode=True)

    def test_site_with_good_ipaddress_and_bad_userid(self):
        args = self.get_args()
        config = self.create_empty_config_file()
        config['config'][0]['site']['ip_address'] = '172.31.216.100'
        config['config'][0]['site']['local'] = 'True'
        config['config'][0]['site']['use_https'] = 'True'
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            self.assertRaises(ConnectionError, execute_tool, args, test_mode=True)

    def rtest_debug_no_level(self):
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = 'sample_config.json'
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            execute_tool(args, test_mode=True)
            self.assertEqual(fake_out.getvalue(), '%% No configuration file given.\n')


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.setup_remote_site()
        self.setup_local_site()

    def tearDown(self):
        self.teardown_local_site()
        self.teardown_remote_site()
        time.sleep(2)

    def create_site_config(self):
        config = {
            "config": [
                {
                    "site": {
                        "username": "%s" % SITE1_LOGIN,
                        "name": "Site1",
                        "ip_address": "%s" % SITE1_IPADDR,
                        "password": "%s" % SITE1_PASSWORD,
                        "local": "True",
                        "use_https": "False"
                    }
                },
                {
                    "site": {
                        "username": "%s" % SITE2_LOGIN,
                        "name": "Site2",
                        "ip_address": "%s" % SITE2_IPADDR,
                        "password": "%s" % SITE2_PASSWORD,
                        "local": "False",
                        "use_https": "False"
                    }
                }
            ]
        }
        return config

    def verify_remote_site_has_entry(self, mac, ip, tenant_name, l3out_name, remote_epg_name):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        query = ('/api/mo/uni/tn-%s/out-%s/instP-%s.json?query-target=children' % (tenant_name, l3out_name, remote_epg_name))
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        found = False
        for item in resp.json()['imdata']:
            if 'l3extSubnet' in item:
                if item['l3extSubnet']['attributes']['ip'] == ip + '/32':
                    found = True
                    break
        if not found:
            return False
        return True

    def verify_remote_site_has_entry_with_provided_contract(self, mac, ip, tenant_name, l3out_name, remote_epg_name, contract_name):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        query = '/api/mo/uni/tn-%s/out-%s.json?query-target=subtree' % (tenant_name, l3out_name)
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        # Look for l3extInstP
        found = False
        for item in resp.json()['imdata']:
            if 'l3extInstP' in item:
                if item['l3extInstP']['attributes']['name'] == remote_epg_name:
                    found = True
                    break
        if not found:
            return False

        # Verify that the l3extInstP is providing the contract
        found = False
        for item in resp.json()['imdata']:
            if 'fvRsProv' in item:
                if item['fvRsProv']['attributes']['tnVzBrCPName'] == contract_name:
                    found = True
                    break
        if not found:
            return False

        return self.verify_remote_site_has_entry(mac, ip, tenant_name, l3out_name, remote_epg_name)

    def verify_remote_site_has_policy(self, tenant_name, l3out_name, instp_name):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        query = ('/api/mo/uni/tn-%s/out-%s/instP-%s.json' % (tenant_name, l3out_name, instp_name))
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        found = False
        for item in resp.json()['imdata']:
            if 'l3extInstP' in item:
                found = True
                break
        if not found:
            return False
        return True

    def teardown_local_site(self):
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)
        time.sleep(2)

    def get_args(self):
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = 'doesntmatter'
        return args

    def remove_endpoint(self, mac, ip, tenant_name, app_name, epg_name):
        self.add_endpoint(mac, ip, tenant_name, app_name, epg_name, mark_as_deleted=True)

    def add_endpoint(self, mac, ip, tenant_name, app_name, epg_name, mark_as_deleted=False):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant(tenant_name)
        app = AppProfile(app_name, tenant)
        epg = EPG(epg_name, app)

        ep = Endpoint(mac, epg)
        ep.mac = mac
        ep.ip = ip
        if mark_as_deleted:
            ep.mark_as_deleted()
        l3ep = IPEndpoint(ip, ep)

        # Create the physical interface object
        intf = Interface('eth', '1', '101', '1', '38')
        vlan_intf = L2Interface('vlan-5', 'vlan', '5')
        vlan_intf.attach(intf)

        # Attach the EPG to the VLAN interface
        epg.attach(vlan_intf)

        # Assign it to the L2Interface
        ep.attach(vlan_intf)

        urls = intf.get_url()
        jsons = intf.get_json()

        # Set the the phys domain, infra, and fabric
        for k in range(0, len(urls)):
            if jsons[k] is not None:
                resp = site1.push_to_apic(urls[k], jsons[k])
                self.assertTrue(resp.ok)

        # Push the endpoint
        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)


class TestBasicEndpoints(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def setup_with_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        return mac, ip

    def test_basic_add_endpoint(self):
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_add_multiple_endpoint(self):
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_one_of_multiple_endpoint(self):
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))


class TestMultipleEPG(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app1 = AppProfile('app1', tenant)
        epg1 = EPG('epg1', app1)
        app2 = AppProfile('app2', tenant)
        epg2 = EPG('epg2', app2)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app1",
                        "epg": "epg1",
                        "remote_epg": "intersite-testsuite-app1-epg1",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app2",
                        "epg": "epg2",
                        "remote_epg": "intersite-testsuite-app2-epg2",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def test_basic_add_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app1-epg1'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app1', 'epg1')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app1-epg1'))

    def test_basic_add_multiple_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app1', 'epg1')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app2', 'epg2')
        mac3 = '00:11:22:33:33:36'
        ip3 = '3.4.3.7'
        self.add_endpoint(mac3, ip3, 'intersite-testsuite', 'app2', 'epg2')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app1-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app2-epg2'))
        self.assertTrue(self.verify_remote_site_has_entry(mac3, ip3, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app2-epg2'))

    def test_basic_remove_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app1', 'epg1')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app1-epg1'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app1', 'epg1')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app1-epg1'))

    def test_basic_remove_one_of_multiple_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app1', 'epg1')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app2', 'epg2')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app1-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app2-epg2'))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app1', 'epg1')
        self.assertFalse(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app1-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app2-epg2'))


class TestBasicExistingEndpoints(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def test_basic_add_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)
        time.sleep(2)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))


class TestBasicExistingEndpointsAddPolicyLater(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        return self.create_site_config()

    def create_export_policy(self):
        config = {
            "export": {
                "tenant": "intersite-testsuite",
                "app": "app",
                "epg": "epg",
                "remote_epg": "intersite-testsuite-app-epg",
                "remote_sites": [
                    {
                        "site": {
                            "name": "Site2",
                            "interfaces": [
                                {
                                    "l3out": {
                                        "name": "l3out",
                                        "tenant": "intersite-testsuite"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        return config

    def test_basic_add_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)
        time.sleep(2)

        config['config'].append(self.create_export_policy())
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()
        time.sleep(2)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        config['config'].append(self.create_export_policy())

        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))


class TestExportPolicyRemoval(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        tenant.mark_as_deleted()
        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)
        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

        time.sleep(2)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg1 = EPG('epg', app)
        epg2 = EPG('epg2', app)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)
        time.sleep(2)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)
        l3out2 = OutsideL3('l3out2', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_diff_epg_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg2",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg2",
                        "remote_epg": "intersite-testsuite-app-epg2",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out2",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def test_basic_remove_policy(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)
        time.sleep(4)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg2'))

        config = self.create_site_config()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()

        time.sleep(4)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg2'))

    def test_basic_change_policy_name(self):
        args = self.get_args()
        config = self.create_config_file()
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)
        time.sleep(4)
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

        config = self.create_diff_epg_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()

        time.sleep(4)

        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg2'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg2'))


class TestBasicEndpointsWithContract(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        contract = Contract('contract-1', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite",
                                                "provides": [
                                                    {
                                                        "contract_name": "contract-1"
                                                    }
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def test_basic_add_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry_with_provided_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                                  'intersite-testsuite-app-epg', 'contract-1'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_provided_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                                 'intersite-testsuite-app-epg', 'contract-1'))

    def test_basic_add_multiple_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_provided_contract(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                                                 'intersite-testsuite-app-epg', 'contract-1'))
        self.assertTrue(self.verify_remote_site_has_entry_with_provided_contract(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                                                 'intersite-testsuite-app-epg', 'contract-1'))

    def test_basic_remove_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_provided_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                                 'intersite-testsuite-app-epg', 'contract-1'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry_with_provided_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                                  'intersite-testsuite-app-epg', 'contract-1'))

    def test_basic_remove_one_of_multiple_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_provided_contract(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                                                 'intersite-testsuite-app-epg', 'contract-1'))
        self.assertTrue(self.verify_remote_site_has_entry_with_provided_contract(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                                                 'intersite-testsuite-app-epg', 'contract-1'))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry_with_provided_contract(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                                                  'intersite-testsuite-app-epg', 'contract-1'))
        self.assertTrue(self.verify_remote_site_has_entry_with_provided_contract(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                                                 'intersite-testsuite-app-epg', 'contract-1'))


class TestBasicEndpointMove(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        context = Context('vrf', tenant)
        bd = BridgeDomain('bd', tenant)
        app = AppProfile('app', tenant)
        epg = EPG('epg1', app)
        epg2 = EPG('epg2', app)
        bd.add_context(context)
        epg.add_bd(bd)
        epg2.add_bd(bd)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg1",
                        "remote_epg": "intersite-testsuite-app-epg1",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg2",
                        "remote_epg": "intersite-testsuite-app-epg2",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def setup_with_endpoint(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg1')
        return mac, ip

    def test_basic_add_endpoint(self):
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))

    def test_basic_add_multiple_endpoint(self):
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg2')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg2'))

    def test_basic_remove_endpoint(self):
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip,  'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg1')
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip,  'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))

    def test_basic_remove_one_of_multiple_endpoint(self):
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg1')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1,  'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2,  'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg1')
        self.assertFalse(self.verify_remote_site_has_entry(mac1, ip1,  'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2,  'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg1'))


class TestPolicyChangeProvidedContract(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        contract = Contract('contract-1', tenant)
        contract = Contract('contract-2', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file_before(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite",
                                                "provides": [
                                                    {
                                                        "contract_name": "contract-1",
                                                    },
                                                    {
                                                        "contract_name": "contract-2",
                                                    }
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def create_config_file_after(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite",
                                                "provides": [
                                                    {
                                                        "contract_name": "contract-1"
                                                    }
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def verify_remote_site_has_entry_before(self, mac, ip):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        query = ('/api/mo/uni/tn-intersite-testsuite/out-l3out.json?query-target=subtree')
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        # Look for l3extInstP
        found = False
        for item in resp.json()['imdata']:
            if 'l3extInstP' in item:
                if item['l3extInstP']['attributes']['name'] == 'intersite-testsuite-app-epg':
                    found = True
                    break
        if not found:
            return False

        # Verify that the l3extInstP is providing the contracts
        found_contract1 = False
        found_contract2 = False
        for item in resp.json()['imdata']:
            if 'fvRsProv' in item:
                if item['fvRsProv']['attributes']['tnVzBrCPName'] == 'contract-1':
                    found_contract1 = True
                if item['fvRsProv']['attributes']['tnVzBrCPName'] == 'contract-2':
                    found_contract2 = True
        if not found_contract1 or not found_contract2:
            return False

        # Look for l3extSubnet
        query = '/api/mo/uni/tn-intersite-testsuite/out-l3out/instP-intersite-testsuite-app-epg.json?query-target=subtree'
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        # Look for l3extSubnet
        found = False
        for item in resp.json()['imdata']:
            if 'l3extSubnet' in item:
                if item['l3extSubnet']['attributes']['name'] == ip:
                    found = True
                    break
        if not found:
            return False
        return True

    def verify_remote_site_has_entry_after(self, mac, ip):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        query = ('/api/mo/uni/tn-intersite-testsuite/out-l3out.json?query-target=subtree')
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        # Look for l3extInstP
        found = False
        for item in resp.json()['imdata']:
            if 'l3extInstP' in item:
                if item['l3extInstP']['attributes']['name'] == 'intersite-testsuite-app-epg':
                    found = True
                    break
        if not found:
            return False

        # Verify that the l3extInstP is providing the contract
        found_contract1 = False
        found_contract2 = False
        for item in resp.json()['imdata']:
            if 'fvRsProv' in item:
                if item['fvRsProv']['attributes']['tnVzBrCPName'] == 'contract-1':
                    found_contract1 = True
                if item['fvRsProv']['attributes']['tnVzBrCPName'] == 'contract-2':
                    found_contract2 = True
        if not found_contract1 or found_contract2:
            return False

        # Look for l3extSubnet
        query = '/api/mo/uni/tn-intersite-testsuite/out-l3out/instP-intersite-testsuite-app-epg.json?query-target=subtree'
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        # Look for l3extSubnet
        found = False
        for item in resp.json()['imdata']:
            if 'l3extSubnet' in item:
                if item['l3extSubnet']['attributes']['ip'] == ip + '/32':
                    found = True
                    break
        if not found:
            return False
        return True

    def test_basic_add_endpoint(self):
        args = self.get_args()
        config = self.create_config_file_before()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry_before(mac, ip))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_before(mac, ip))
        config = self.create_config_file_after()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()
        time.sleep(4)
        self.assertTrue(self.verify_remote_site_has_entry_after(mac, ip))

    def test_basic_add_multiple_endpoint(self):
        args = self.get_args()
        config = self.create_config_file_before()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_before(mac1, ip1))
        self.assertTrue(self.verify_remote_site_has_entry_before(mac2, ip2))

        config = self.create_config_file_after()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry_after(mac1, ip1))
        self.assertTrue(self.verify_remote_site_has_entry_after(mac2, ip2))


class TestChangeL3Out(BaseTestCase):
    def setup_local_site(self):
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out1 = OutsideL3('l3out1', tenant)
        l3out2 = OutsideL3('l3out2', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_export_policy(self, l3out_name):
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": l3out_name,
                                                "tenant": "intersite-testsuite"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        return export_policy

    def create_config_file(self, l3out_name):
        config = self.create_site_config()
        export_policy = self.create_export_policy(l3out_name)
        config['config'].append(export_policy)
        return config

    def test_basic_add_endpoint(self):
        args = self.get_args()
        config = self.create_config_file('l3out1')
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        config = self.create_config_file('l3out2')
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()
        time.sleep(4)

        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_add_endpoint_multiple_l3out(self):
        args = self.get_args()
        config = self.create_config_file('l3out1')
        for policy in config['config']:
            if 'export' in policy:
                for site_policy in policy['export']['remote_sites']:
                    interface_policy = {"l3out": {"name": "l3out2",
                                                  "tenant": "intersite-testsuite"}}
                    site_policy['site']['interfaces'].append(interface_policy)
                policy['export']['remote_sites'].append(site_policy)
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))
        config = self.create_config_file('l3out2')
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()
        time.sleep(4)

        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_add_multiple_endpoint(self):
        args = self.get_args()
        config = self.create_config_file('l3out1')
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector = execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out1', 'intersite-testsuite-app-epg'))

        config = self.create_config_file('l3out2')
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            collector.reload_config()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out2', 'intersite-testsuite-app-epg'))

# test basic install of a single EPG and 1 endpoint being pushed to other site
# test remove EPG from policy and that


class TestDuplicates(BaseTestCase):
    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite-local",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out",
                                                "tenant": "intersite-testsuite-remote"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def setup_local_site(self):
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        l3out = OutsideL3('l3out', tenant)
        epg = OutsideEPG('intersite-testsuite-app-epg', l3out)
        other_epg = OutsideEPG('other', l3out)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def teardown_local_site(self):
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def add_remote_duplicate_entry(self, ip):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        l3out = OutsideL3('l3out', tenant)
        other_epg = OutsideEPG('other', l3out)
        subnet = OutsideNetwork(ip, other_epg)
        subnet.ip = ip + '/32'

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def test_basic_duplicate(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out', 'intersite-testsuite-app-epg'))
        self.add_remote_duplicate_entry(ip)

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite-local', 'app', 'epg')

        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_multiple_duplicate(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out', 'intersite-testsuite-app-epg'))
            self.add_remote_duplicate_entry(ip)

        time.sleep(2)

        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.add_endpoint(mac, ip, 'intersite-testsuite-local', 'app', 'epg')

        time.sleep(2)
        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_partial_duplicate(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        for i in range(0, 7):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out', 'intersite-testsuite-app-epg'))
            self.add_remote_duplicate_entry(ip)

        time.sleep(2)

        for i in range(4, 9):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.add_endpoint(mac, ip, 'intersite-testsuite-local', 'app', 'epg')

        time.sleep(2)
        for i in range(4, 9):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out', 'intersite-testsuite-app-epg'))

class TestDuplicatesTwoL3Outs(BaseTestCase):
    def create_config_file(self):
        config = self.create_site_config()
        export_policy = {
                    "export": {
                        "tenant": "intersite-testsuite-local",
                        "app": "app",
                        "epg": "epg",
                        "remote_epg": "intersite-testsuite-app-epg",
                        "remote_sites": [
                            {
                                "site": {
                                    "name": "Site2",
                                    "interfaces": [
                                        {
                                            "l3out": {
                                                "name": "l3out1",
                                                "tenant": "intersite-testsuite-remote"
                                            }
                                        },
                                        {
                                            "l3out": {
                                                "name": "l3out2",
                                                "tenant": "intersite-testsuite-remote"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
        config['config'].append(export_policy)
        return config

    def setup_local_site(self):
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        l3out1 = OutsideL3('l3out1', tenant)
        l3out2 = OutsideL3('l3out2', tenant)
        epg1 = OutsideEPG('intersite-testsuite-app-epg', l3out1)
        other_epg = OutsideEPG('other', l3out1)
        epg2 = OutsideEPG('intersite-testsuite-app-epg', l3out2)


        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def teardown_local_site(self):
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def add_remote_duplicate_entry(self, ip):
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        l3out = OutsideL3('l3out1', tenant)
        other_epg = OutsideEPG('other', l3out)
        subnet = OutsideNetwork(ip, other_epg)
        subnet.ip = ip + '/32'

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def test_basic_duplicate(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out1', 'intersite-testsuite-app-epg'))
        self.add_remote_duplicate_entry(ip)

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite-local', 'app', 'epg')
        mac2 = '00:11:22:33:33:44'
        ip2 = '3.4.3.44'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite-local', 'app', 'epg')

        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite-remote', 'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out2', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite-remote', 'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_multiple_duplicate(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out1', 'intersite-testsuite-app-epg'))
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out2', 'intersite-testsuite-app-epg'))
            self.add_remote_duplicate_entry(ip)

        time.sleep(2)

        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.add_endpoint(mac, ip, 'intersite-testsuite-local', 'app', 'epg')

        time.sleep(2)
        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out1', 'intersite-testsuite-app-epg'))
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_partial_duplicate(self):
        args = self.get_args()
        config = self.create_config_file()
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=str(json.dumps(config)))):
            execute_tool(args, test_mode=True)

        for i in range(0, 7):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out1', 'intersite-testsuite-app-epg'))
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out2', 'intersite-testsuite-app-epg'))
            self.add_remote_duplicate_entry(ip)

        time.sleep(2)

        for i in range(4, 9):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.add_endpoint(mac, ip, 'intersite-testsuite-local', 'app', 'epg')

        time.sleep(2)
        for i in range(4, 9):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out1', 'intersite-testsuite-app-epg'))
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote', 'l3out2', 'intersite-testsuite-app-epg'))


def main_test():
    full = unittest.TestSuite()
    full.addTest(unittest.makeSuite(TestToolOptions))

    unittest.main()


if __name__ == '__main__':
    try:
        main_test()
    except KeyboardInterrupt:
        pass
