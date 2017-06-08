"""
Test suite for Intersite application
"""
import unittest
from acitoolkit import (AppProfile, EPG, Endpoint, Interface, L2Interface, Context, BridgeDomain, Session, Tenant,
                        IPEndpoint, OutsideL3, OutsideEPG, OutsideNetwork, Contract)
from intersite import execute_tool, IntersiteTag, CommandLine, get_arg_parser
import argparse
import logging
from StringIO import StringIO
import mock
import sys

if sys.version_info.major == 2:
    import __builtin__ as builtins
else:
    import builtins
import json
import time
import logging

try:
    from multisite_test_credentials import (SITE1_IPADDR, SITE1_LOGIN, SITE1_PASSWORD, SITE1_URL,
                                            SITE2_IPADDR, SITE2_LOGIN, SITE2_PASSWORD, SITE2_URL,
                                            SITE3_IPADDR, SITE3_LOGIN, SITE3_PASSWORD, SITE3_URL,
                                            SITE4_IPADDR, SITE4_LOGIN, SITE4_PASSWORD, SITE4_URL)
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

            SITE3_IPADDR = ''
            SITE3_LOGIN = ''
            SITE3_PASSWORD = ''
            SITE3_URL = 'http://' + SITE3_IPADDR

            SITE4_IPADDR = ''
            SITE4_LOGIN = ''
            SITE4_PASSWORD = ''
            SITE4_URL = 'http://' + SITE3_IPADDR
            '''
    sys.exit(0)


class FakeStdio(object):
    """
    FakeStdio : Class to fake writing to stdio and store it so that it can be verified
    """
    def __init__(self):
        self.output = []

    def write(self, *args, **kwargs):
        """
        Mock the write routine

        :param args: Args passed to stdio write
        :param kwargs: Kwargs passed to stdio write
        :return: None
        """
        for arg in args:
            self.output.append(arg)

    def verify_output(self, output):
        """
        Verify that the output is the same as generated previously

        :param output: Output to test for
        :return: True if the same as the stored output. False otherwise
        """
        return output == self.output


class TestToolOptions(unittest.TestCase):
    """
    Test cases for testing the command line arguments
    """
    @staticmethod
    def get_logging_level():
        """
        Return the current logger level

        :return: Logger level
        """
        return logging.getLevelName(logging.getLogger().getEffectiveLevel())

    def test_no_options(self):
        """
        Test no configuration file given.  Verify that it generates an error message
        """
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = None
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            execute_tool(args)
            self.assertEqual(fake_out.getvalue(), '%% No configuration file given.\n')

    def test_generateconfig(self):
        """
        Test generate sample configuration file.  Verify that it generates the correct text message
        """
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

    def test_set_debug_to_verbose(self):
        """
        Test setting the debug level to verbose
        """
        args = mock.Mock()
        args.debug = 'verbose'
        args.config = None
        execute_tool(args)

    def test_set_debug_to_warnings(self):
        """
        Test setting the debug level to warnings
        """
        args = mock.Mock()
        args.debug = 'warnings'
        args.config = None
        execute_tool(args)

    def test_set_debug_to_critical(self):
        """
        Test setting the debug level to critical
        """
        args = mock.Mock()
        args.debug = 'critical'
        args.config = None
        execute_tool(args)

    def test_config_bad_filename(self):
        """
        Test no configuration file given.  Verify that it generates an error message
        """
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = 'jkdhfdskjfhdsfkjhdsfdskjhf.jdkhfkfjh'
        expected_text = '%% Unable to open configuration file jkdhfdskjfhdsfkjhdsfdskjhf.jdkhfkfjh\n'
        with mock.patch('sys.stdout', new=StringIO()) as fake_out:
            execute_tool(args)
            self.assertEqual(fake_out.getvalue(), expected_text)

    def test_get_arg_parser(self):
        self.assertIsInstance(get_arg_parser(), argparse.ArgumentParser)


class TestBadConfiguration(unittest.TestCase):
    """
    Test various invalid configuration files
    """
    @staticmethod
    def create_empty_config_file():
        """
        Generate an empty configuration file with only a single empty Site policy
        :return: dictionary containing the configuration
        """
        config = {
            "config": [
                {
                    "site": {
                        "username": SITE1_LOGIN,
                        "name": "site1",
                        "ip_address": SITE1_IPADDR,
                        "password": SITE1_PASSWORD,
                        "local": "True",
                        "use_https": "True"
                    }
                }
            ]
        }
        return config

    @staticmethod
    def get_args():
        """
        Generate an empty command line arguments
        :return: Instance of Mock to represent the command line arguments
        """
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = 'doesntmatter'
        return args

    @staticmethod
    def create_config_file(args, config, with_bad_json=False):
        config_filename = 'testsuite_cfg.json'
        args.config = config_filename
        config_file = open(config_filename, 'w')
        config_file.write(str(json.dumps(config)))
        if with_bad_json:
            config_file.write(']]]')
        config_file.close()

    def test_no_config_keyword(self):
        """
        Test no "config" present in the JSON.  Verify that the correct error message is generated.
        :return: None
        """
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

        self.create_config_file(args, config)

        execute_tool(args, test_mode=True)
        sys.stdout = temp
        self.assertTrue(fake_out.verify_output(['%% Invalid configuration file', '\n']))

    def test_bad_json_file(self):
        """
        Test bad JSON in the file.  Verify that the correct error message is generated.
        :return: None
        """
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

        self.create_config_file(args, config, with_bad_json=True)

        execute_tool(args, test_mode=True)
        sys.stdout = temp
        self.assertTrue(fake_out.verify_output(['%% File could not be decoded as JSON.', '\n']))

    def test_site_with_bad_ipaddress(self):
        """
        Test invalid IP address value in the JSON.  Verify that the correct exception is generated.
        :return: None
        """
        args = self.get_args()
        config = self.create_empty_config_file()
        config['config'][0]['site']['ip_address'] = 'bogu$'
        self.create_config_file(args, config)

        self.assertRaises(ValueError, execute_tool, args, test_mode=True)

    def test_site_with_bad_ipaddress_as_number(self):
        """
        Test invalid IP address value in the JSON.  Verify that the correct exception is generated.
        :return: None
        """
        args = self.get_args()
        config = self.create_empty_config_file()
        config['config'][0]['site']['ip_address'] = 100
        self.create_config_file(args, config)

        self.assertRaises(TypeError, execute_tool, args, test_mode=True)

    def test_site_with_good_ipaddress_and_bad_userid(self):
        """
        Test good IP address value but invalid username in the JSON.  Verify that the correct exception is generated.
        :return: None
        """
        args = self.get_args()
        config = self.create_empty_config_file()
        config['config'][0]['site']['username'] = ''
        config['config'][0]['site']['ip_address'] = SITE1_IPADDR
        config['config'][0]['site']['local'] = 'True'
        config['config'][0]['site']['use_https'] = 'True'
        self.create_config_file(args, config)

        self.assertRaises(ValueError, execute_tool, args, test_mode=True)

    def test_site_with_bad_local_setting(self):
        """
        Test with bad local setting in the site JSON.  Verify that the correct exception is generated.
        :return: None
        """
        args = self.get_args()
        config = self.create_empty_config_file()
        config['config'][0]['site']['username'] = 'admin'
        config['config'][0]['site']['ip_address'] = SITE1_IPADDR
        config['config'][0]['site']['local'] = 'BAD'
        config['config'][0]['site']['use_https'] = 'True'
        self.create_config_file(args, config)

        self.assertRaises(ValueError, execute_tool, args, test_mode=True)

    def test_site_with_bad_use_https(self):
        """
        Test with bad use_https setting in the site JSON.  Verify that the correct exception is generated.
        :return: None
        """
        args = self.get_args()
        config = self.create_empty_config_file()
        config['config'][0]['site']['username'] = 'admin'
        config['config'][0]['site']['ip_address'] = SITE1_IPADDR
        config['config'][0]['site']['local'] = 'True'
        config['config'][0]['site']['use_https'] = 'BAD'
        self.create_config_file(args, config)

        self.assertRaises(ValueError, execute_tool, args, test_mode=True)

    def test_reload_bad_config_filename(self):
        """
        Test reload_config with a non-existent filename
        :return: None
        """
        # Create a valid configuration
        args = self.get_args()
        config = self.create_empty_config_file()
        self.create_config_file(args, config)
        collector = execute_tool(args, test_mode=True)

        # Check that a bad config filename reload behaves as expected
        collector.config_filename = 'nonexistent.json'
        self.assertFalse(collector.reload_config())

    def test_reload_bad_json_in_file(self):
        """
        Test reload_config with a badly formatted JSON file
        :return: None
        """
        # Create a valid configuration
        args = self.get_args()
        config = self.create_empty_config_file()
        self.create_config_file(args, config)
        collector = execute_tool(args, test_mode=True)

        # Create a badly formatted config file
        self.create_config_file(args, config, with_bad_json=True)
        self.assertFalse(collector.reload_config())

    def test_reload_with_no_config_keyword(self):
        """
        Test reload_config with no 'config' keyword in the JSON
        :return: None
        """
        # Create a valid configuration
        args = self.get_args()
        config = self.create_empty_config_file()
        self.create_config_file(args, config)
        collector = execute_tool(args, test_mode=True)

        # Create a configuration file with no 'config' keyword
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
        self.create_config_file(args, config)
        self.assertFalse(collector.reload_config())

    def test_reload_no_local_site_in_reloaded_config(self):
        """
        Test reload_config with no local site specified in the JSON
        :return: None
        """
        # Create a valid configuration
        args = self.get_args()
        config = self.create_empty_config_file()
        self.create_config_file(args, config)
        collector = execute_tool(args, test_mode=True)

        # Create a configuration with no local site
        config = self.create_empty_config_file()
        config['config'][0]['site']['local'] = 'False'
        self.create_config_file(args, config)

        # Reload
        self.assertFalse(collector.reload_config())

    def test_oversized_intersite_tag(self):
        """
        Test oversized string lengths for the entities that make up a Intersite tag
        """
        # Create a configuration with long names
        args = self.get_args()
        config = self.create_empty_config_file()
        export_policy = {
            "export":
                {
                    "tenant": "a" * 64,
                    "app": "b" * 64,
                    "epg": "c" * 64,
                    "remote_epg": "intersite-testsuite-app-epg",
                    "remote_sites":
                        [
                            {
                                "site":
                                    {
                                        "name": "d" * 64,
                                    }
                            }
                        ]
                }
        }
        config['config'].append(export_policy)

        self.create_config_file(args, config)
        self.assertRaises(ValueError, execute_tool, args, test_mode=True)

    def test_duplicate_export_policy(self):
        """
        Test oversized string lengths for the entities that make up a Intersite tag
        """
        # Create a configuration with long names
        args = self.get_args()
        config = self.create_empty_config_file()
        export_policy = {
            "export":
                {
                    "tenant": "mytenant",
                    "app": "myapp",
                    "epg": "myepg",
                    "remote_epg": "intersite-testsuite-app-epg",
                    "remote_sites":
                        [
                            {
                                "site":
                                    {
                                        "name": "mysite",
                                    }
                            }
                        ]
                }
        }
        config['config'].append(export_policy)
        config['config'].append(export_policy)

        self.create_config_file(args, config)
        self.assertRaises(ValueError, execute_tool, args, test_mode=True)

    def test_bad_intersite_tag(self):
        """
        Test bad intersite tag creation
        """
        with self.assertRaises(AssertionError):
            IntersiteTag.fromstring('badstring')


class BaseTestCase(unittest.TestCase):
    """
    BaseTestCase: Base class to be used for creating other TestCases. Not to be instantiated directly.
    """
    def setup_remote_site(self):
        """
        Set up the remote site. Meant to be overridden by inheriting classes
        """
        raise NotImplementedError

    def setup_local_site(self):
        """
        Set up the local site. Meant to be overridden by inheriting classes
        """
        raise NotImplementedError

    def setUp(self):
        """
        Set up the test case.  Setup the remote and local site.
        :return: None
        """
        self.setup_remote_site()
        self.setup_local_site()

    def tearDown(self):
        """
        Tear down the test case.  Tear down the remote and local site.
        :return: None
        """
        self.teardown_local_site()
        self.teardown_remote_site()
        time.sleep(2)

    @staticmethod
    def create_site_config():
        """
        Generate a basic configuration containing the local and remote site policies.
        Actual site credentials are set in global variables imported from multisite_test_credentials
        :return: dictionary containing the configuration
        """
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

    @staticmethod
    def write_config_file(config, args):
        """
        Write the configuration as a temporary file and set the command line arguments to read the file
        :param config: dictionary containing the configuration
        :param args: Mock of the command line arguments
        :return: None
        """
        config_filename = 'testsuite_cfg.json'
        args.config = config_filename
        config_file = open(config_filename, 'w')
        config_file.write(str(json.dumps(config)))
        config_file.close()

    def verify_remote_site_has_entry(self, mac, ip, tenant_name, l3out_name, remote_epg_name):
        """
        Verify that the remote site has the entry
        :param mac: String containing the MAC address of the endpoint to find on the remote site
        :param ip: String containing the IP address of the endpoint to find on the remote site
        :param tenant_name: String containing the remote tenant name holding the endpoint
        :param l3out_name: String containing the remote OutsideL3 name holding the endpoint
        :param remote_epg_name: String containing the remote OutsideEPG on the remote OutsideL3 holding the endpoint
        :return: True if the remote site has the endpoint. False otherwise
        """
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        query = ('/api/mo/uni/tn-%s/out-%s/instP-%s.json?query-target=children' % (tenant_name,
                                                                                   l3out_name,
                                                                                   remote_epg_name))
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

    def verify_remote_site_has_entry_with_contract(self, mac, ip, tenant_name, l3out_name, remote_epg_name,
                                                   contract_name, contract_type):
        """
        Verify that the remote site has the entry and provides the specfied contract
        :param mac: String containing the MAC address of the endpoint to find on the remote site
        :param ip: String containing the IP address of the endpoint to find on the remote site
        :param tenant_name: String containing the remote tenant name holding the endpoint
        :param l3out_name: String containing the remote OutsideL3 name holding the endpoint
        :param remote_epg_name: String containing the remote OutsideEPG on the remote OutsideL3 holding the endpoint
        :param contract_name: String containing the contract name that the remote OutsideEPG should be providing
        :param contract_type: String containing the contract usage.
                              Valid values are 'provides', 'consumes', 'consumes_interface', and 'protected_by'
        :return: True if the remote site has the endpoint. False otherwise
        """
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        assert contract_type in ['provides', 'consumes', 'consumes_interface', 'protected_by']

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
        contract_types = {'provides': ['fvRsProv', 'tnVzBrCPName'],
                          'consumes': ['fvRsCons', 'tnVzBrCPName'],
                          'consumes_interface': ['fvRsConsIf', 'tnVzCPIfName'],
                          'protected_by': ['fvRsProtBy', 'tnVzTabooName']
                          }
        (aci_class, aci_class_ref) = contract_types[contract_type]
        for item in resp.json()['imdata']:
            if aci_class in item:
                if item[aci_class]['attributes'][aci_class_ref] == contract_name:
                    found = True
                    break
        if not found:
            return False

        return self.verify_remote_site_has_entry(mac, ip, tenant_name, l3out_name, remote_epg_name)

    def verify_remote_site_has_policy(self, tenant_name, l3out_name, instp_name):
        """
        Verify that the remote site has the policy
        :param tenant_name: String containing the remote tenant name holding the policy
        :param l3out_name: String containing the remote OutsideL3 name holding the policy
        :param instp_name: String containing the remote OutsideEPG holding the policy
        :return: True if the remote site has the policy. False otherwise
        """
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
        """
        Teardown the local site configuration
        """
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        if not resp.ok:
            print resp, resp.text
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        """
        Teardown the remote site configuration
        """
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)
        time.sleep(2)

    @staticmethod
    def get_args():
        """
        Get a mock of the command line arguments
        :return: Mock instance representing the command line arguments
        """
        args = mock.Mock()
        args.debug = None
        args.generateconfig = None
        args.config = 'doesntmatter'
        return args

    def remove_endpoint(self, mac, ip, tenant_name, app_name, epg_name):
        """
        Remove the endpoint
        :param mac: String containing the MAC address of the endpoint
        :param ip: String containing the IP address of the endpoint
        :param tenant_name: String containing the tenant name of the endpoint
        :param app_name: String containing the AppProfile name holding the endpoint
        :param epg_name: String containing the EPG name holding the endpoint
        :return: None
        """
        self.add_endpoint(mac, ip, tenant_name, app_name, epg_name, mark_as_deleted=True)

    def add_endpoint(self, mac, ip, tenant_name, app_name, epg_name, mark_as_deleted=False):
        """
        Add the endpoint
        :param mac: String containing the MAC address of the endpoint
        :param ip: String containing the IP address of the endpoint
        :param tenant_name: String containing the tenant name of the endpoint
        :param app_name: String containing the AppProfile name holding the endpoint
        :param epg_name: String containing the EPG name holding the endpoint
        :param mark_as_deleted: True or False. True if the endpoint is to be marked as deleted. Default is False
        :return: None
        """
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
        time.sleep(1)


class BaseEndpointTestCase(BaseTestCase):
    """
    Base class for the endpoint test cases
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
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
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
        config = self.create_site_config()
        export_policy = {
            "export":
                {
                    "tenant": "intersite-testsuite",
                    "app": "app",
                    "epg": "epg",
                    "remote_epg": "intersite-testsuite-app-epg",
                    "remote_sites":
                        [
                            {
                                "site":
                                    {
                                        "name": "Site2",
                                        "interfaces":
                                            [
                                                {
                                                    "l3out":
                                                        {
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

    def setup_with_endpoint(self, mac='00:11:22:33:33:33'):
        """
        Set up the configuration with an endpoint
        :return: 2 strings containing the MAC and IP address of the endpoint
        """
        args = self.get_args()
        self.write_config_file(self.create_config_file(), args)

        execute_tool(args, test_mode=True)

        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out', 'intersite-testsuite-app-epg'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        return mac, ip


class TestBasicEndpoints(BaseEndpointTestCase):
    """
    Basic tests for endpoints
    """
    def test_basic_add_endpoint(self):
        """
        Test add endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_add_multiple_endpoint(self):
        """
        Test add multiple endpoints
        """
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        """
        Test remove endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_one_of_multiple_endpoint(self):
        """
        Test remove one of multiple endpoints
        """
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))


class TestBasicEndpointsWithMultipleRemoteSites(BaseEndpointTestCase):
    """
    Basic tests for endpoints with multiple remote sites
    """
    def setup_remote_site(self):
        """
        Set up the remote site
        """
        # Set up site 2
        super(TestBasicEndpointsWithMultipleRemoteSites, self).setup_remote_site()

        # Create tenant, L3out with contract on site 3
        site3 = Session(SITE3_URL, SITE3_LOGIN, SITE3_PASSWORD)
        resp = site3.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-site3')
        vrf = Context('myvrf', tenant)
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site3)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        """
        Teardown the remote site configuration
        """
        time.sleep(2)
        super(TestBasicEndpointsWithMultipleRemoteSites, self).teardown_remote_site()

        site3 = Session(SITE3_URL, SITE3_LOGIN, SITE3_PASSWORD)
        resp = site3.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-site3')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site3)
        self.assertTrue(resp.ok)
        time.sleep(2)

    def create_additional_site_config(self, login, ip_address, password):
        """
        Add the additional site to the configuration
        :return: Dictionary containing the configuration
        """
        config = super(TestBasicEndpointsWithMultipleRemoteSites, self).create_config_file()
        site3_config = {
            "site": {
                "username": "%s" % login,
                "name": "Site3",
                "ip_address": "%s" % ip_address,
                "password": "%s" % password,
                "local": "False",
                "use_https": "False"
            }
        }
        config['config'].append(site3_config)
        return config

    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
        config = self.create_additional_site_config(SITE3_LOGIN, SITE3_IPADDR, SITE3_PASSWORD)
        site3_export_config = {
            "site":
                {
                    "name": "Site3",
                    "interfaces":
                        [
                            {
                                "l3out":
                                    {
                                        "name": "l3out",
                                        "tenant": "intersite-testsuite-site3"
                                    }
                            }
                        ]
                }
        }
        for item in config['config']:
            if 'export' in item:
                item['export']['remote_sites'].append(site3_export_config)
        return config

    def setup_with_endpoint(self, mac='00:11:22:33:33:33', ip='3.4.3.4'):
        """
        Set up the configuration with an endpoint
        :return: 2 strings containing the MAC and IP address of the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()

        self.write_config_file(config, args)

        execute_tool(args, test_mode=True)

        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        return mac, ip

    def test_basic_add_endpoint(self):
        """
        Test add endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                          'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        """
        Test remove endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                           'l3out', 'intersite-testsuite-app-epg'))


class TestBasicEndpointsWithMultipleRemoteSitesButOnlyExportToOne(TestBasicEndpointsWithMultipleRemoteSites):
    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
        config = self.create_additional_site_config(SITE3_LOGIN, SITE3_IPADDR, SITE3_PASSWORD)
        return config

    def test_basic_add_endpoint(self):
        """
        Test add endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                           'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        """
        Test remove endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                           'l3out', 'intersite-testsuite-app-epg'))


class TestBasicEndpointsWithThreeRemoteSites(TestBasicEndpointsWithMultipleRemoteSites):
    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
        config = super(TestBasicEndpointsWithThreeRemoteSites, self).create_config_file()
        site4_config = {
            "site": {
                "username": "%s" % SITE4_LOGIN,
                "name": "Site4",
                "ip_address": "%s" % SITE4_IPADDR,
                "password": "%s" % SITE4_PASSWORD,
                "local": "False",
                "use_https": "False"
            }
        }
        config['config'].append(site4_config)

        site4_export_config = {
            "site":
                {
                    "name": "Site4",
                    "interfaces":
                        [
                            {
                                "l3out":
                                    {
                                        "name": "l3out",
                                        "tenant": "intersite-testsuite-site4"
                                    }
                            }
                        ]
                }
        }
        for item in config['config']:
            if 'export' in item:
                item['export']['remote_sites'].append(site4_export_config)
        return config

    def test_basic_add_endpoint(self):
        """
        Test add endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site4',
                                                          'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        """
        Test remove endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site4',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site4',
                                                           'l3out', 'intersite-testsuite-app-epg'))


class TestBasicMacMove(BaseEndpointTestCase):
    """
    Basic test for MAC move.
    i.e. the same IP address appears with a different MAC address.  This case can appear in failovers such as redundant
    loadbalancers
    """
    def test_basic_mac_move(self):
        """
        Test basic MAC move
        """

        args = self.get_args()
        self.write_config_file(self.create_config_file(), args)

        execute_tool(args, test_mode=True)

        ip = '3.4.3.4'
        mac = '00:11:22:33:33:33'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out',
                                                           'intersite-testsuite-app-epg'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))

        mac = '00:11:22:33:44:44'
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        self.remove_endpoint('00:11:22:33:33:33', ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))


class TestMultipleEPG(BaseTestCase):
    """
    Test multiple EPGs
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
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
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
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
        """
        Test add endpoint
        """
        args = self.get_args()
        config = self.create_config_file()

        config_filename = 'testsuite_cfg.json'
        args.config = config_filename
        config_file = open(config_filename, 'w')
        config_file.write(str(json.dumps(config)))
        config_file.close()

        execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app1-epg1'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app1', 'epg1')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app1-epg1'))

    def test_basic_add_multiple_endpoint(self):
        """
        Test adding multiple endpoints
        """
        args = self.get_args()
        config = self.create_config_file()

        config_filename = 'testsuite_cfg.json'
        args.config = config_filename
        config_file = open(config_filename, 'w')
        config_file.write(str(json.dumps(config)))
        config_file.close()

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

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app1-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app2-epg2'))
        self.assertTrue(self.verify_remote_site_has_entry(mac3, ip3, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app2-epg2'))

    def test_basic_remove_endpoint(self):
        """
        Test remove the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app1', 'epg1')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app1-epg1'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app1', 'epg1')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app1-epg1'))

    def test_basic_remove_one_of_multiple_endpoint(self):
        """
        Test remove one of multiple endpoints
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app1', 'epg1')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app2', 'epg2')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app1-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app2-epg2'))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app1', 'epg1')
        self.assertFalse(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                           'intersite-testsuite-app1-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app2-epg2'))


class BaseExistingEndpointsTestCase(BaseTestCase):
    """
    Base class for tests where endpoints already exist
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
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


class TestBasicExistingEndpoints(BaseExistingEndpointsTestCase):
    def test_basic_add_endpoint(self):
        """
        Test add the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)
        time.sleep(2)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        """
        Test remove the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))


class BaseExistingEndpointsWith3RemoteSites(BaseExistingEndpointsTestCase):
    def setup_remote_tenant(self, url, login, password, tenant_name):
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site = Session(url, login, password)
        resp = site.login()
        self.assertTrue(resp.ok)

        tenant = Tenant(tenant_name)
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        """
        Set up the remote sites
        """
        self.setup_remote_tenant(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD, 'intersite-testsuite-site-2')
        self.setup_remote_tenant(SITE3_URL, SITE3_LOGIN, SITE3_PASSWORD, 'intersite-testsuite-site-3')
        self.setup_remote_tenant(SITE4_URL, SITE4_LOGIN, SITE4_PASSWORD, 'intersite-testsuite-site-4')

    def teardown_remote_tenant(self, url, login, password, tenant_name):
        """
        Teardown the remote site configuration
        """
        site2 = Session(url, login, password)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant(tenant_name)
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        """
        Teardown the remote sites
        """
        self.teardown_remote_tenant(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD, 'intersite-testsuite-site-2')
        self.teardown_remote_tenant(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD, 'intersite-testsuite-site-3')
        self.teardown_remote_tenant(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD, 'intersite-testsuite-site-4')
        time.sleep(2)

    def add_remote_site_to_config_file(self, config, site_name, ip_address, login, password, tenant_name):
        site_config = {
                          "site": {
                              "username": "%s" % login,
                              "name": "%s" % site_name,
                              "ip_address": "%s" % ip_address,
                              "password": "%s" % password,
                              "local": "False",
                              "use_https": "False"
                          }
                      }
        site_export_config = {
                                 "site": {
                                     "name": site_name,
                                     "interfaces": [
                                         {
                                             "l3out": {
                                                 "name": "l3out",
                                                 "tenant": tenant_name
                                             }
                                         }
                                     ]
                                 }
                             }
        for item in config['config']:
            if 'export' in item:
                item['export']['remote_sites'].append(site_export_config)
        config['config'].append(site_config)
        return config

    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
        config = self.create_site_config()
        export_policy = {
            "export": {
                "tenant": "intersite-testsuite",
                "app": "app",
                "epg": "epg",
                "remote_epg": "intersite-testsuite-app-epg",
                "remote_sites": [
                ]
            }
        }
        config['config'].append(export_policy)
        config = self.add_remote_site_to_config_file(config,
                                                     'Site2',
                                                     SITE2_IPADDR, SITE2_LOGIN, SITE2_PASSWORD,
                                                     'intersite-testsuite-site2')
        config = self.add_remote_site_to_config_file(config,
                                                     'Site3',
                                                     SITE3_IPADDR, SITE3_LOGIN, SITE3_PASSWORD,
                                                     'intersite-testsuite-site3')
        config = self.add_remote_site_to_config_file(config,
                                                     'Site4',
                                                     SITE4_IPADDR, SITE4_LOGIN, SITE4_PASSWORD,
                                                     'intersite-testsuite-site4')
        return config


class TestBasicExistingEndpointsWith3RemoteSites(BaseExistingEndpointsWith3RemoteSites):
    def test_basic_add_endpoint(self):
        """
        Test add the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)
        time.sleep(2)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site2',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site4',
                                                          'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        """
        Test remove the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site2',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site4',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site2',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site3',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-site4',
                                                           'l3out', 'intersite-testsuite-app-epg'))


class TestLargeScaleExistingEndpointsWith3RemoteSites(BaseExistingEndpointsWith3RemoteSites):
    def setup_local_site(self):
        """
        Set up the local site
        """
        for i in range(0, 3):
            # create Tenant, App, EPG on site 1
            site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
            resp = site1.login()
            self.assertTrue(resp.ok)

            tenant = Tenant('intersite-testsuite')
            app = AppProfile('app', tenant)
            epg = EPG('epg', app)

            # Create the physical interface object
            intf = Interface('eth', '1', '101', '1', '38')
            vlan_intf = L2Interface('vlan-5', 'vlan', '5')
            vlan_intf.attach(intf)

            # Attach the EPG to the VLAN interface
            epg.attach(vlan_intf)

            for j in range(0, 254):
                mac = '00:11:22:33:%s:%s' % (hex(i)[2:].zfill(2), hex(j)[2:].zfill(2))
                ip = '3.4.%s.%s' % (i, j)

                ep = Endpoint(mac, epg)
                ep.mac = mac
                ep.ip = ip
                l3ep = IPEndpoint(ip, ep)

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
            time.sleep(1)

    def verify_remote_site_has_entries(self, tenant_name, l3out_name, remote_epg_name):
        """
        Verify that the remote site has the entry
        :param mac: String containing the MAC address of the endpoint to find on the remote site
        :param ip: String containing the IP address of the endpoint to find on the remote site
        :param tenant_name: String containing the remote tenant name holding the endpoint
        :param l3out_name: String containing the remote OutsideL3 name holding the endpoint
        :param remote_epg_name: String containing the remote OutsideEPG on the remote OutsideL3 holding the endpoint
        :return: True if the remote site has the endpoint. False otherwise
        """
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        query = ('/api/mo/uni/tn-%s/out-%s/instP-%s.json?query-target=children' % (tenant_name,
                                                                                   l3out_name,
                                                                                   remote_epg_name))
        resp = site2.get(query)
        self.assertTrue(resp.ok)

        subnets = set()
        for item in resp.json()['imdata']:
            if 'l3extSubnet' in item:
                subnets.add(item['l3extSubnet']['attributes']['ip'])

        for i in range(0, 3):
            for j in range(0, 254):
                ip = '3.4.%s.%s/32' % (i, j)
                if ip not in subnets:
                    return False
        return True

    def test_add_large_scale_endpoints(self):
        """
        Test add the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)
        time.sleep(20)

        self.assertTrue(self.verify_remote_site_has_entries('intersite-testsuite-site2',
                                                            'l3out',
                                                            'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entries('intersite-testsuite-site3',
                                                            'l3out',
                                                            'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entries('intersite-testsuite-site4',
                                                            'l3out',
                                                            'intersite-testsuite-app-epg'))


class TestBasicExistingEndpointsAddPolicyLater(BaseTestCase):
    """
    Tests for previously existing endpoints and policy is added later
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
        # create Tenant, App, EPG on site 1
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
        return self.create_site_config()

    @staticmethod
    def create_export_policy():
        """
        Create the export policy
        :return: Dictionary containing the configuration
        """
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
        """
        Test adding the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        collector = execute_tool(args, test_mode=True)
        time.sleep(2)

        config['config'].append(self.create_export_policy())
        self.write_config_file(config, args)
        collector.reload_config()
        time.sleep(2)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg'))

    def test_basic_remove_endpoint(self):
        """
        Test removing the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        config['config'].append(self.create_export_policy())
        self.write_config_file(config, args)

        collector = execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg'))

        config = self.create_config_file()
        self.write_config_file(config, args)
        collector.reload_config()
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out',
                                                           'intersite-testsuite-app-epg'))


class TestExportPolicyRemoval(BaseTestCase):
    """
    Tests for export policy removal
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
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
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out',
                                                           'intersite-testsuite-app-epg'))
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)
        time.sleep(2)

    def setup_remote_site(self):
        """
        Set up the remote site
        """
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
        """
        Create a configuration with different EPGs
        :return: Dictionary containing the configuration
        """
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
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
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
        """
        Test removing the policy
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        collector = execute_tool(args, test_mode=True)
        time.sleep(4)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite',
                                                           'l3out2', 'intersite-testsuite-app-epg2'))

        config = self.create_site_config()
        self.write_config_file(config, args)
        collector.reload_config()

        time.sleep(4)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite',
                                                            'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite',
                                                            'l3out2', 'intersite-testsuite-app-epg2'))

    def test_basic_change_policy_name(self):
        """
        Test changing the policy name
        """
        args = self.get_args()
        config = self.create_config_file()
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.write_config_file(config, args)
        collector = execute_tool(args, test_mode=True)
        time.sleep(4)
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))

        config = self.create_diff_epg_config_file()
        self.write_config_file(config, args)
        collector.reload_config()

        time.sleep(4)

        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite',
                                                            'l3out', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg2'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg2'))


class BaseTestCaseEndpointsWithContract(BaseTestCase):
    """
    Base class for Tests for endpoints with a contract
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
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
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        contract = Contract('contract-1', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self, contract_type):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
        config = self.create_site_config()
        if contract_type == 'protected_by':
            contract_name = 'taboo_name'
        elif contract_type == 'consumes_interface':
            contract_name = 'cif_name'
        else:
            contract_name = 'contract_name'
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
                                        contract_type: [
                                            {
                                                contract_name: "contract-1"
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

    def common_test_basic_add_endpoint(self, contract_type):
        """
        Test adding endpoint
        """
        args = self.get_args()
        config = self.create_config_file(contract_type)
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry_with_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                         'intersite-testsuite-app-epg', 'contract-1',
                                                                         contract_type))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                        'intersite-testsuite-app-epg', 'contract-1',
                                                                        contract_type))

    def common_test_basic_add_multiple_endpoint(self, contract_type):
        """
        Test adding multiple endpoints
        """
        args = self.get_args()
        config = self.create_config_file(contract_type)
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_contract(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                                        'intersite-testsuite-app-epg', 'contract-1',
                                                                        contract_type))
        self.assertTrue(self.verify_remote_site_has_entry_with_contract(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                                        'intersite-testsuite-app-epg', 'contract-1',
                                                                        contract_type))

    def common_test_basic_remove_endpoint(self, contract_type):
        """
        Test removing endpoint
        """
        args = self.get_args()
        config = self.create_config_file(contract_type)
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        time.sleep(2)
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                        'intersite-testsuite-app-epg', 'contract-1',
                                                                        contract_type))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry_with_contract(mac, ip, 'intersite-testsuite', 'l3out',
                                                                         'intersite-testsuite-app-epg', 'contract-1',
                                                                         contract_type))

    def common_test_basic_remove_one_of_multiple_endpoint(self, contract_type):
        """
        Test removing one of multiple endpoints
        """
        args = self.get_args()
        config = self.create_config_file(contract_type)
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry_with_contract(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                                        'intersite-testsuite-app-epg', 'contract-1',
                                                                        contract_type))
        self.assertTrue(self.verify_remote_site_has_entry_with_contract(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                                        'intersite-testsuite-app-epg', 'contract-1',
                                                                        contract_type))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        self.assertFalse(self.verify_remote_site_has_entry_with_contract(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                                         'intersite-testsuite-app-epg', 'contract-1',
                                                                         contract_type))
        self.assertTrue(self.verify_remote_site_has_entry_with_contract(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                                        'intersite-testsuite-app-epg', 'contract-1',
                                                                        contract_type))


class TestBasicEndpointsWithProvidedContract(BaseTestCaseEndpointsWithContract):
    """
    Basic Tests for endpoints with a provided contract
    """
    def test_basic_add_endpoint(self):
        """
        Test adding endpoint
        """
        self.common_test_basic_add_endpoint(contract_type='provides')

    def test_basic_add_multiple_endpoint(self):
        """
        Test adding multiple endpoints
        """
        self.common_test_basic_add_multiple_endpoint(contract_type='provides')

    def test_basic_remove_endpoint(self):
        """
        Test removing endpoint
        """
        self.common_test_basic_remove_endpoint(contract_type='provides')

    def test_basic_remove_one_of_multiple_endpoint(self):
        """
        Test removing one of multiple endpoints
        """
        self.common_test_basic_remove_one_of_multiple_endpoint(contract_type='provides')


class TestBasicEndpointsWithConsumedContract(BaseTestCaseEndpointsWithContract):
    """
    Basic Tests for endpoints with a consumed contract
    """
    def test_basic_add_endpoint(self):
        """
        Test adding endpoint
        """
        self.common_test_basic_add_endpoint(contract_type='consumes')

    def test_basic_add_multiple_endpoint(self):
        """
        Test adding multiple endpoints
        """
        self.common_test_basic_add_multiple_endpoint(contract_type='consumes')

    def test_basic_remove_endpoint(self):
        """
        Test removing endpoint
        """
        self.common_test_basic_remove_endpoint(contract_type='consumes')

    def test_basic_remove_one_of_multiple_endpoint(self):
        """
        Test removing one of multiple endpoints
        """
        self.common_test_basic_remove_one_of_multiple_endpoint(contract_type='consumes')


class TestBasicEndpointsWithConsumedContractInterface(BaseTestCaseEndpointsWithContract):
    """
    Basic Tests for endpoints with a consumed contract interface
    """
    def test_basic_add_endpoint(self):
        """
        Test adding endpoint
        """
        self.common_test_basic_add_endpoint(contract_type='consumes_interface')

    def test_basic_add_multiple_endpoint(self):
        """
        Test adding multiple endpoints
        """
        self.common_test_basic_add_multiple_endpoint(contract_type='consumes_interface')

    def test_basic_remove_endpoint(self):
        """
        Test removing endpoint
        """
        self.common_test_basic_remove_endpoint(contract_type='consumes_interface')

    def test_basic_remove_one_of_multiple_endpoint(self):
        """
        Test removing one of multiple endpoints
        """
        self.common_test_basic_remove_one_of_multiple_endpoint(contract_type='consumes_interface')


class TestBasicEndpointsWithTaboo(BaseTestCaseEndpointsWithContract):
    """
    Basic Tests for endpoints with a Taboo
    """
    def test_basic_add_endpoint(self):
        """
        Test adding endpoint
        """
        self.common_test_basic_add_endpoint(contract_type='protected_by')

    def test_basic_add_multiple_endpoint(self):
        """
        Test adding multiple endpoints
        """
        self.common_test_basic_add_multiple_endpoint(contract_type='protected_by')

    def test_basic_remove_endpoint(self):
        """
        Test removing endpoint
        """
        self.common_test_basic_remove_endpoint(contract_type='protected_by')

    def test_basic_remove_one_of_multiple_endpoint(self):
        """
        Test removing one of multiple endpoints
        """
        self.common_test_basic_remove_one_of_multiple_endpoint(contract_type='protected_by')


class TestBasicEndpointMove(BaseTestCase):
    """
    Tests for an endpoint that moves
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
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
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out = OutsideL3('l3out', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def create_config_file(self):
        """
        Create the configuration
        :return: Dictionary containing the configuration
        """
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
        """
        Set up the local site with the endpoint
        :return: 2 strings containing the MAC and IP address of the endpoint
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg1'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg1')
        return mac, ip

    def test_basic_add_endpoint(self):
        """
        Test add endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg1'))

    def test_basic_add_multiple_endpoint(self):
        """
        Test add multiple endpoints
        """
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg2')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg2'))

    def test_basic_remove_endpoint(self):
        """
        Test removing the endpoint
        """
        mac, ip = self.setup_with_endpoint()
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg1'))
        self.remove_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg1')
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite', 'l3out',
                                                           'intersite-testsuite-app-epg1'))

    def test_basic_remove_one_of_multiple_endpoint(self):
        """
        Test removing one of multiple endpoints
        """
        mac1, ip1 = self.setup_with_endpoint()
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg1')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg1'))

        self.remove_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg1')
        self.assertFalse(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite', 'l3out',
                                                           'intersite-testsuite-app-epg1'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite', 'l3out',
                                                          'intersite-testsuite-app-epg1'))


class TestPolicyChangeProvidedContract(BaseTestCase):
    """
    Tests to cover changing the provided contract within the policy
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
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
        """
        Set up the remote site
        """
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
        """
        Create the configuration before changing the provided contract
        :return: Dictionary containing the configuration
        """
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
        """
        Create the configuration after changing the provided contract
        :return: Dictionary containing the configuration
        """
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
        """
        Verify that the remote site has the entry before changing the policy
        :param mac: String containing the endpoint MAC address
        :param ip: String containing the endpoint IP address
        :return: True or False.  True if the remote site has the entry
        """
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
        query = ('/api/mo/uni/tn-intersite-testsuite/out-l3out'
                 '/instP-intersite-testsuite-app-epg.json?query-target=subtree')
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
        """
        Verify that the remote site has the entry after changing the policy
        :param mac: String containing the endpoint MAC address
        :param ip: String containing the endpoint IP address
        :return: True or False.  True if the remote site has the entry
        """
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
        query = ('/api/mo/uni/tn-intersite-testsuite/out-l3out'
                 '/instP-intersite-testsuite-app-epg.json?query-target=subtree')
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
        """
        Test add endpoint
        """
        args = self.get_args()
        config = self.create_config_file_before()
        self.write_config_file(config, args)
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
        self.write_config_file(config, args)
        collector.reload_config()
        time.sleep(4)
        self.assertTrue(self.verify_remote_site_has_entry_after(mac, ip))

    def test_basic_add_multiple_endpoint(self):
        """
        Test adding multiple endpoints
        """
        args = self.get_args()
        config = self.create_config_file_before()
        self.write_config_file(config, args)
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
        self.write_config_file(config, args)
        collector.reload_config()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry_after(mac1, ip1))
        self.assertTrue(self.verify_remote_site_has_entry_after(mac2, ip2))


class TestChangeL3Out(BaseTestCase):
    """
    Tests for changing OutsideL3 interfaces
    """
    def setup_local_site(self):
        """
        Set up the local site
        """
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
        """
        Set up the remote site
        """
        # Create tenant, L3out with contract on site 2
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite')
        l3out1 = OutsideL3('l3out1', tenant)
        l3out2 = OutsideL3('l3out2', tenant)

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    @staticmethod
    def create_export_policy(l3out_name):
        """
        Create the export policy
        :param l3out_name: String containing the OutsideL3 name
        :return: Dictionary containing the export policy
        """
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
        """
        Create the configuration
        :param l3out_name: String containing the OutsideL3 name
        :return: Dictionary containing the configuration
        """
        config = self.create_site_config()
        export_policy = self.create_export_policy(l3out_name)
        config['config'].append(export_policy)
        return config

    def test_basic_add_endpoint(self):
        """
        Basic test for adding endpoint
        """
        args = self.get_args()
        config = self.create_config_file('l3out1')
        self.write_config_file(config, args)
        collector = execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out1', 'intersite-testsuite-app-epg'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite',
                                                           'l3out1', 'intersite-testsuite-app-epg'))
        config = self.create_config_file('l3out2')
        self.write_config_file(config, args)
        collector.reload_config()
        time.sleep(4)

        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite',
                                                            'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite',
                                                           'l3out2', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_add_endpoint_multiple_l3out(self):
        """
        Test adding endpoint with multiple OutsideL3 interfaces
        """
        args = self.get_args()
        config = self.create_config_file('l3out1')
        for policy in config['config']:
            if 'export' in policy:
                for site_policy in policy['export']['remote_sites']:
                    interface_policy = {"l3out": {"name": "l3out2",
                                                  "tenant": "intersite-testsuite"}}
                    site_policy['site']['interfaces'].append(interface_policy)
                policy['export']['remote_sites'].append(site_policy)
        self.write_config_file(config, args)
        collector = execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out1', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out2', 'intersite-testsuite-app-epg'))

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out2', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out1',
                                                           'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite', 'l3out2',
                                                           'intersite-testsuite-app-epg'))
        config = self.create_config_file('l3out2')
        self.write_config_file(config, args)
        collector.reload_config()
        time.sleep(4)

        self.assertFalse(self.verify_remote_site_has_policy('intersite-testsuite',
                                                            'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_policy('intersite-testsuite',
                                                           'l3out2', 'intersite-testsuite-app-epg'))
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_add_multiple_endpoint(self):
        """
        Test adding multiple endopoints
        """
        args = self.get_args()
        config = self.create_config_file('l3out1')
        self.write_config_file(config, args)
        collector = execute_tool(args, test_mode=True)

        time.sleep(2)
        mac1 = '00:11:22:33:33:34'
        ip1 = '3.4.3.5'
        self.add_endpoint(mac1, ip1, 'intersite-testsuite', 'app', 'epg')
        mac2 = '00:11:22:33:33:35'
        ip2 = '3.4.3.6'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite', 'app', 'epg')
        time.sleep(2)

        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite',
                                                          'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite',
                                                          'l3out1', 'intersite-testsuite-app-epg'))

        config = self.create_config_file('l3out2')
        self.write_config_file(config, args)
        collector.reload_config()
        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac1, ip1, 'intersite-testsuite',
                                                          'l3out2', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite',
                                                          'l3out2', 'intersite-testsuite-app-epg'))

# test basic install of a single EPG and 1 endpoint being pushed to other site
# test remove EPG from policy and that


class TestDuplicates(BaseTestCase):
    """
    Test duplicate existing entry on the remote site
    """
    def create_config_file(self):
        """
        Create the configuration file
        :return: dictionary containing the configuration
        """
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
        """
        Set up the local site
        """
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        """
        Set up the remote site
        """
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
        """
        Tear down the local site
        """
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        """
        Tear down the remote site
        """
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)

    def add_remote_duplicate_entry(self, ip):
        """
        Add a remote entry
        :param ip: String containing the IP address
        :return: None
        """
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
        """
        Test a basic duplicate entry scenario.  An existing entry exists on the remote site but on
        a different OutsideEPG on the same OutsideL3.
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
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
        """
        Test a basic multiple duplicate entry scenario.
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                               'l3out', 'intersite-testsuite-app-epg'))
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
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                              'l3out', 'intersite-testsuite-app-epg'))

    def test_basic_partial_duplicate(self):
        """
        Test a basic multiple duplicate entry scenario where some of the entries in the set being added are duplicate.
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        for i in range(0, 7):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                               'l3out', 'intersite-testsuite-app-epg'))
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
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                              'l3out', 'intersite-testsuite-app-epg'))


class SetupDuplicateTests(BaseTestCase):
    """
    Base class to setup the duplicate tests
    """
    def create_config_file(self):
        """
        Create the configuration file
        :return: dictionary containing the configuration
        """
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
        """
        Set up the local site
        """
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        app = AppProfile('app', tenant)
        epg = EPG('epg', app)

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def setup_remote_site(self):
        """
        Set up the remote site
        """
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
        """
        Tear down the local site
        """
        site1 = Session(SITE1_URL, SITE1_LOGIN, SITE1_PASSWORD)
        resp = site1.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-local')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site1)
        self.assertTrue(resp.ok)

    def teardown_remote_site(self):
        """
        Tear down the remote site
        """
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)

        tenant = Tenant('intersite-testsuite-remote')
        tenant.mark_as_deleted()

        resp = tenant.push_to_apic(site2)
        self.assertTrue(resp.ok)


class TestDuplicatesTwoL3Outs(SetupDuplicateTests):
    """
    Test duplicate entries with 2 OutsideL3 interfaces on the remote site
    """
    def add_remote_duplicate_entry(self, ip):
        """
        Add a remote entry
        :param ip: String containing the IP address
        :return: None
        """
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
        """
        Test a basic duplicate entry scenario.  An existing entry exists on the remote site but on
        a different OutsideEPG on the same OutsideL3.
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                           'l3out1', 'intersite-testsuite-app-epg'))
        self.add_remote_duplicate_entry(ip)

        time.sleep(2)
        self.add_endpoint(mac, ip, 'intersite-testsuite-local', 'app', 'epg')
        mac2 = '00:11:22:33:33:44'
        ip2 = '3.4.3.44'
        self.add_endpoint(mac2, ip2, 'intersite-testsuite-local', 'app', 'epg')

        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                          'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite-remote',
                                                          'l3out1', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                          'l3out2', 'intersite-testsuite-app-epg'))
        self.assertTrue(self.verify_remote_site_has_entry(mac2, ip2, 'intersite-testsuite-remote',
                                                          'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_multiple_duplicate(self):
        """
        Test a basic multiple duplicate entry scenario.
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        for i in range(0, 5):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                               'l3out1', 'intersite-testsuite-app-epg'))
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                               'l3out2', 'intersite-testsuite-app-epg'))
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
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                              'l3out1', 'intersite-testsuite-app-epg'))
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                              'l3out2', 'intersite-testsuite-app-epg'))

    def test_basic_partial_duplicate(self):
        """
        Test a basic multiple duplicate entry scenario where some of the entries in the set being added are duplicate.
        """
        args = self.get_args()
        config = self.create_config_file()
        self.write_config_file(config, args)
        execute_tool(args, test_mode=True)

        for i in range(0, 7):
            mac = '00:11:22:33:33:3' + str(i)
            ip = '3.4.3.' + str(i)
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                               'l3out1', 'intersite-testsuite-app-epg'))
            self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                               'l3out2', 'intersite-testsuite-app-epg'))
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
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                              'l3out1', 'intersite-testsuite-app-epg'))
            self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite-remote',
                                                              'l3out2', 'intersite-testsuite-app-epg'))


class TestDeletions(BaseEndpointTestCase):
    """
    Tests for deletion of stale entries
    """
    def test_basic_deletion(self):
        """
        Test basic deletion of a stale entry on tool startup
        :return:
        """
        args = self.get_args()
        config_filename = 'testsuite_cfg.json'
        args.config = config_filename
        config = self.create_config_file()

        config_file = open(config_filename, 'w')
        config_file.write(str(json.dumps(config)))
        config_file.close()

        # Create the "stale" entry on the remote site
        mac = '00:11:22:33:33:33'
        ip = '3.4.3.4'
        site2 = Session(SITE2_URL, SITE2_LOGIN, SITE2_PASSWORD)
        resp = site2.login()
        self.assertTrue(resp.ok)
        tag = IntersiteTag('intersite-testsuite', 'app', 'epg', 'Site1')
        remote_tenant = Tenant('intersite-testsuite')
        remote_l3out = OutsideL3('l3out', remote_tenant)
        remote_epg = OutsideEPG('intersite-testsuite-app-epg', remote_l3out)
        remote_ep = OutsideNetwork(ip, remote_epg)
        remote_ep.ip = ip + '/32'
        remote_tenant.push_to_apic(site2)

        time.sleep(2)
        self.assertTrue(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                          'l3out', 'intersite-testsuite-app-epg'))

        execute_tool(args, test_mode=True)

        time.sleep(2)
        self.assertFalse(self.verify_remote_site_has_entry(mac, ip, 'intersite-testsuite',
                                                           'l3out', 'intersite-testsuite-app-epg'))


class TestCli(BaseTestCase):
    """
    Tests for the CLI
    """
    def setup_remote_site(self):
        """
        Set up the remote site.
        """
        pass

    def setup_local_site(self):
        """
        Set up the local site.
        """
        pass

    def teardown_local_site(self):
        """
        Teardown the local site configuration
        """
        pass

    def teardown_remote_site(self):
        """
        Teardown the remote site configuration
        """
        pass

    def _create_commandline(self):
        """
        Internal function to create a CommandLine instance
        """
        args = self.get_args()
        self.write_config_file(self.create_site_config(), args)
        cmdline = CommandLine(execute_tool(args, test_mode=True))
        self.assertTrue(isinstance(cmdline, CommandLine))
        return cmdline

    def _test_show_cmd(self, cmd, output):
        """
        Internal common function for checking show commands
        :param cmd: String containing show command keyword
        :param output: List of strings to compare with the command output
        """
        cmdline = self._create_commandline()
        temp = sys.stdout
        fake_out = FakeStdio()
        sys.stdout = fake_out
        cmdline.do_show(cmd)
        sys.stdout = temp
        self.assertTrue(fake_out.verify_output(output))

    def test_show_debug(self):
        """
        Test show debug command
        """
        self._test_show_cmd('debug', ['Debug level currently set to:', ' ', 'CRITICAL', '\n'])

    def test_show_configfile(self):
        """
        Test show configfile command
        """
        self._test_show_cmd('configfile', ['Configuration file is set to:', ' ', 'testsuite_cfg.json', '\n'])

    def test_show_config(self):
        """
        Test show config command
        """
        self._test_show_cmd('config', [json.dumps(self.create_site_config(), indent=4, separators=(',', ':')), '\n'])

    def test_show_sites(self):
        """
        Test show sites command
        """
        self._test_show_cmd('sites', [u'Site1', ' ', ':', ' ', 'Connected', '\n',
                                      u'Site2', ' ', ':', ' ', 'Connected', '\n'])

    def test_show_stats(self):
        """
        Test show stats command
        """
        self._test_show_cmd('stats', ['Endpoint addition events:', ' ', '0', '\n',
                                      'Endpoint deletion events:', ' ', '0', '\n'])


def main_test():
    """
    Main execution routine.  Create the test suites and run.
    """
    full = unittest.TestSuite()
    full.addTest(unittest.makeSuite(TestToolOptions))
    full.addTest(unittest.makeSuite(TestBadConfiguration))
    full.addTest(unittest.makeSuite(TestBasicEndpoints))
    full.addTest(unittest.makeSuite(TestMultipleEPG))
    full.addTest(unittest.makeSuite(TestBasicExistingEndpoints))
    full.addTest(unittest.makeSuite(TestBasicExistingEndpointsAddPolicyLater))
    full.addTest(unittest.makeSuite(TestExportPolicyRemoval))
    full.addTest(unittest.makeSuite(TestBasicEndpointsWithProvidedContract))
    full.addTest(unittest.makeSuite(TestBasicEndpointsWithConsumedContract))
    full.addTest(unittest.makeSuite(TestBasicEndpointsWithConsumedContractInterface))
    full.addTest(unittest.makeSuite(TestBasicEndpointsWithTaboo))
    full.addTest(unittest.makeSuite(TestBasicEndpointMove))
    full.addTest(unittest.makeSuite(TestPolicyChangeProvidedContract))
    full.addTest(unittest.makeSuite(TestChangeL3Out))
    full.addTest(unittest.makeSuite(TestDuplicates))
    full.addTest(unittest.makeSuite(TestDuplicatesTwoL3Outs))
    full.addTest(unittest.makeSuite(TestDeletions))
    full.addTest(unittest.makeSuite(TestCli))
    full.addTest(unittest.makeSuite(TestBasicEndpointsWithMultipleRemoteSites))
    full.addTest(unittest.makeSuite(TestBasicEndpointsWithMultipleRemoteSitesButOnlyExportToOne))
    full.addTest(unittest.makeSuite(TestBasicEndpointsWithThreeRemoteSites))

    unittest.main()


if __name__ == '__main__':
    try:
        main_test()
    except KeyboardInterrupt:
        pass
