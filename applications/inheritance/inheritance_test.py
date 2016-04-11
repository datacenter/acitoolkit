"""
Inheritance test suite
"""
import unittest
from inheritance import execute_tool
from acitoolkit import (Tenant, Context, OutsideL3, OutsideEPG, OutsideNetwork,
                        Contract, FilterEntry, Session, AppProfile, EPG,
                        ContractInterface, Fabric)
import time
import sys
import logging
from logging.handlers import RotatingFileHandler
import argparse
from os import getpid
from ConfigParser import ConfigParser, NoSectionError, NoOptionError

DEFAULT_INI_FILENAME = 'inheritance_apic_credentials.ini'


class ApicCredentials(object):
    """
    Class to collect the APIC credentials from an configuration file
    """
    def __init__(self):
        self._config = None
        self._username = None
        self._password = None
        self._url = None
        self._ip_address = None

    def set_config(self, filename):
        """
        Set the configuration file name
        :param filename: String containing the configuration file name
        :return: None
        """
        if filename is None:
            return
        self._config = ConfigParser()
        self._config.read(filename)

    def _get_attribute(self, attr_name):
        """
        Get the requested configuration attribute
        :param attr_name: String containing the attribute name
        :return: String containing the requested configuration attribute
        :raises: ValueError: An error occurred accessing the requested configuration attribute
        """
        try:
            return self._config.get('Credentials', attr_name)
        except AttributeError:
            raise ValueError('Credentials configuration file not found')
        except(NoSectionError, NoOptionError):
            raise ValueError('Requested credential attribute not present')

    @property
    def username(self):
        """
        APIC username
        :return: String containing APIC username
        """
        return self._get_attribute('Username')

    @property
    def password(self):
        """
        APIC password
        :return: String containing APIC password
        """
        return self._get_attribute('Password')

    @property
    def url(self):
        """
        APIC URL
        :return: String containing APIC URL
        """
        return self._get_attribute('URL')

    @property
    def ip_address(self):
        """
        APIC IP address as parsed from the URL
        :return: String containing APIC IP address
        """
        return self.url.partition('://')[-1].split('/')[0]


class TestArgs(object):
    """
    Fake class to mock out Command line arguments
    """
    def __init__(self):
        self.debug = 'verbose'
        self.maxlogfiles = 10
        self.generateconfig = False


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


class BaseTestCase(unittest.TestCase):
    """
    Base class for the various test cases
    """
    def delete_tenant(self):
        """
        Delete the tenant config. Called before and after test
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        tenant.mark_as_deleted()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(4)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)
        tenants = Tenant.get(apic)
        for tenant in tenants:
            self.assertTrue(tenant.name != 'inheritanceautomatedtest')

    def setUp(self):
        self.delete_tenant()

    def tearDown(self):
        self.delete_tenant()


class TestWithoutApicCommunication(unittest.TestCase):
    """
    Tests that do not communicate with the APIC
    """
    def test_generate_config(self):
        """
        Generate the test configuration
        """
        args = TestArgs()
        args.generateconfig = True

        sample_config = """
{
    "apic": {
        "user_name": "admin",
        "password": "password",
        "ip_address": "0.0.0.0",
        "use_https": false
    },
    "inheritance_policies": [
        {
            "epg": {
                "tenant": "tenant-name",
                "epg_container": {
                    "name": "l3out-name",
                    "container_type": "l3out"
                },
                "name": "epg-name"
            },
            "allowed": true,
            "enabled": true
        },
        {
            "epg": {
                "tenant": "tenant-name",
                "epg_container": {
                    "name": "l3out-name",
                    "container_type": "l3out"
                },
                "name": "epg-name"
            },
            "allowed": true,
            "enabled": true
        },
    ]
}
        """
        temp = sys.stdout
        fake_out = FakeStdio()
        sys.stdout = fake_out

        tool = execute_tool(args)
        sys.stdout = temp
        self.assertTrue(fake_out.verify_output([sample_config, '\n']))


class BaseBasicL3Out(BaseTestCase):
    """
    Base class for basic Inheritance test cases enabled on OutsideEPGs
    """
    def setup_tenant(self, apic):
        """
        Setup the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        context = Context('mycontext', tenant)
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        parent_network = OutsideNetwork('5.1.1.1', parent_epg)
        parent_network.ip = '5.1.1.1/8'
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('5.2.1.1', child_epg)
        child_network.ip = '5.2.1.1/16'
        contract = Contract('mycontract', tenant)
        parent_epg.provide(contract)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        l3out = tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract'))
        contract = tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract)
        if not_inherited:
            self.assertFalse(childepg.does_provide(contract))
        else:
            self.assertTrue(childepg.does_provide(contract))

    def verify_not_inherited(self, apic):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        self.verify_inherited(apic, not_inherited=True)


class TestBasicL3Out(BaseBasicL3Out):
    """
    Basic Inheritance test cases enabled on OutsideEPGs
    """
    def test_basic_inherit_contract(self):
        """
        Basic inherit contract test
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)
        tool.exit()
        # self.delete_tenant()

    def test_basic_inheritance_disallowed(self):
        """
        Basic test for when inheritance is disallowed
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": False,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_not_inherited(apic)
        # self.delete_tenant()
        tool.exit()

    def test_basic_inheritance_disabled(self):
        """
        Basic test for when inheritance is disabled
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": False
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_not_inherited(apic)
        tool.exit()
        # self.delete_tenant()

    def test_get_config(self):
        """
        Basic test for getting the configuration
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": False
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        config = tool.get_config()
        # Verify that the contract is now inherited by the child EPG
        self.assertEqual(config, config_json)

        tool.exit()


class TestBasicL3OutWithInheritFrom(BaseBasicL3Out):
    """
    Basic Inheritance test cases enabled on OutsideEPGs that also use the inherit_from clause
    """
    def setup_tenant(self, apic):
        """
        Setup the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        app = AppProfile('myapp', tenant)
        epg = EPG('myepg', app)
        contract = Contract('mycontract-app', tenant)
        epg.provide(contract)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        super(TestBasicL3OutWithInheritFrom, self).setup_tenant(apic)

    def verify_inherited(self, apic, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        l3out = tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract'))
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract-app'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract'))
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract-app'))
        for contract_name in ['mycontract', 'mycontract-app']:
            contract = tenant.get_child(Contract, contract_name)
            self.assertIsNotNone(contract)
            if not_inherited:
                self.assertFalse(childepg.does_provide(contract))
            else:
                self.assertTrue(childepg.does_provide(contract))

    def test_basic_inherit_contract(self):
        """
        Basic inherit contract test
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True,
                    "inherit_from": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "myepg"
                    }
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)
        tool.exit()


class TestContractEvents(BaseTestCase):
    """
    Test contract events
    """
    def get_config_json(self):
        """
        Get the JSON configuration
        :return: Dictionary containing the JSON configuration
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        return config_json

    def get_contract(self, tenant):
        """
        Get a contract
        :param tenant: Instance of Tenant class to contain the contract
        :return: Instance of Contract class
        """
        contract = Contract('mycontract', tenant)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        return contract

    def setup_tenant(self, apic):
        """
        Setup the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        context = Context('mycontext', tenant)
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        parent_network = OutsideNetwork('5.1.1.1', parent_epg)
        parent_network.ip = '5.1.1.1/8'
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('5.2.1.1', child_epg)
        child_network.ip = '5.2.1.1/16'
        contract = self.get_contract(tenant)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def setup_tenant_with_2_parent_epgs(self, apic):
        """
        Setup the tenant configuration with 2 parent EPGs
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        context = Context('mycontext', tenant)
        l3out = OutsideL3('myl3out', tenant)
        parent_epg1 = OutsideEPG('parentepg1', l3out)
        parent_network = OutsideNetwork('5.1.1.1', parent_epg1)
        parent_network.ip = '5.1.1.1/8'
        contract = self.get_contract(tenant)
        parent_epg1.provide(contract)
        parent_epg2 = OutsideEPG('parentepg2', l3out)
        parent_epg2.provide(contract)
        parent_network = OutsideNetwork('5.3.1.1', parent_epg2)
        parent_network.ip = '5.3.1.1/12'
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('5.2.1.1', child_epg)
        child_network.ip = '5.2.1.1/16'
        contract = self.get_contract(tenant)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def add_contract(self, apic):
        """
        Add the contract
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        contract = self.get_contract(tenant)
        parent_epg.provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def remove_contract(self, apic):
        """
        Remove the contract
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        contract = self.get_contract(tenant)
        parent_epg.provide(contract)
        parent_epg.dont_provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        l3out = tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract'))
        contract = tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract)
        if not_inherited:
            self.assertFalse(childepg.does_provide(contract))
        else:
            self.assertTrue(childepg.does_provide(contract))

    def verify_not_inherited(self, apic):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        self.verify_inherited(apic, not_inherited=True)

    def test_basic_inherit_contract(self):
        """
        Basic test for inheriting contract
        """
        self.delete_tenant()
        config_json = self.get_config_json()
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic)
        time.sleep(2)

        # Add the contract
        self.add_contract(apic)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        self.delete_tenant()

    def test_inherit_contract_and_delete(self):
        """
        Test inheriting the contract and delete the contract
        """
        self.delete_tenant()
        config_json = self.get_config_json()
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic)
        time.sleep(2)

        # Add the contract
        self.add_contract(apic)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        # Remove the contract from the parent EPG
        self.remove_contract(apic)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic)

        self.delete_tenant()

    def test_dual_inheritance_contract(self):
        """
        Test for inheriting from 2 EPGs
        """
        self.delete_tenant()
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg1"
                    },
                    "allowed": True,
                    "enabled": False
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg2"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }

        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant_with_2_parent_epgs(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        self.delete_tenant()

    def test_dual_inheritance_contract_delete_one_relation(self):
        """
        Test for inheriting from 2 EPGs and one relation deleted
        """
        self.delete_tenant()
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg1"
                    },
                    "allowed": True,
                    "enabled": False
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg2"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }

        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant_with_2_parent_epgs(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        # Remove contract
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg1', l3out)
        contract = self.get_contract(tenant)
        parent_epg.provide(contract)
        parent_epg.dont_provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        # Verify that the contract is still inherited by the child EPG
        time.sleep(2)
        self.verify_inherited(apic)

        self.delete_tenant()

    def test_dual_inheritance_contract_delete_both_relations(self):
        """
        Test for inheriting from 2 EPGs and both relations deleted
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg1"
                    },
                    "allowed": True,
                    "enabled": False
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg2"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }

        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant_with_2_parent_epgs(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        # Remove contracts
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        contract = self.get_contract(tenant)
        parent_epg1 = OutsideEPG('parentepg1', l3out)
        parent_epg1.provide(contract)
        parent_epg1.dont_provide(contract)
        parent_epg2 = OutsideEPG('parentepg2', l3out)
        parent_epg2.provide(contract)
        parent_epg2.dont_provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        # Verify that the contract is still inherited by the child EPG
        time.sleep(4)
        self.verify_not_inherited(apic)

        self.delete_tenant()

# multiple children
# - verify that an inherited relation can go from parent to child to grandchild

# contract cases
# - add another contract and verify that it gets inherited
# - delete the contract and verify that it gets removed

# subnet cases
# - add subnet and verify that causes to be inherited
# - remove subnet and verify inheritance removed
# - add 2 subnets and verify that causes to be inherited, remove 1 verify still inherited
# - remove inherited relation


class TestSubnetEvents(BaseTestCase):
    """
    Test subnet events
    """
    def setup_tenant(self, apic):
        """
        Setup the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        context = Context('mycontext', tenant)
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        parent_network = OutsideNetwork('5.1.1.1', parent_epg)
        parent_network.ip = '5.1.1.1/8'
        _ = OutsideEPG('childepg', l3out)
        contract = Contract('mycontract', tenant)
        parent_epg.provide(contract)
        _ = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def add_child_subnet(self, apic):
        """
        Add a child subnet
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('5.2.1.1', child_epg)
        child_network.ip = '5.2.1.1/16'
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        l3out = tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract'))
        contract = tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract)
        if not_inherited:
            self.assertFalse(childepg.does_provide(contract))
        else:
            self.assertTrue(childepg.does_provide(contract))

    def verify_not_inherited(self, apic):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        self.verify_inherited(apic, not_inherited=True)

    def test_basic_inherit_add_subnet(self):
        """
        Basic test to inherit after adding a subnet
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic)

        # Add the child subnet
        self.add_child_subnet(apic)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        self.delete_tenant()


class TestMultipleOutsideEPGLevels(BaseTestCase):
    """
    Test multiple OutsideEPG levels
    """
    def setup_tenant(self, apic):
        """
        Setup the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        context = Context('mycontext', tenant)
        l3out = OutsideL3('myl3out', tenant)
        grandparent_epg = OutsideEPG('grandparentepg', l3out)
        grandparent_network = OutsideNetwork('10.0.0.0', grandparent_epg)
        grandparent_network.ip = '10.0.0.0/8'
        parent_epg = OutsideEPG('parentepg', l3out)
        parent_network = OutsideNetwork('10.1.0.0', parent_epg)
        parent_network.ip = '10.1.0.0/16'
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('10.1.1.0', child_epg)
        child_network.ip = '10.1.1.0/24'
        contract = Contract('mycontract', tenant)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        l3out = tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract'))
        contract = tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract)
        if not_inherited:
            self.assertFalse(childepg.does_provide(contract))
        else:
            self.assertTrue(childepg.does_provide(contract))

    def verify_not_inherited(self, apic):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        self.verify_inherited(apic, not_inherited=True)

    def test_provide_contract_directly_on_parent_epg(self):
        """
        Basic test to inherit after adding a subnet
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": False,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "grandparentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }

            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic)

        # Provide the contract from the parent EPG
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        parent_network = OutsideNetwork('10.1.0.0', parent_epg)
        parent_network.ip = '10.1.0.0/16'
        contract = Contract('mycontract', tenant)
        parent_epg.provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)

        # Verify that the contract is still not inherited by the child EPG
        self.verify_not_inherited(apic)

        time.sleep(2)

        # Verify that the parent EPG still provides the contract
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        l3out = tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        parentepg = l3out.get_child(OutsideEPG, 'parentepg')
        self.assertIsNotNone(parentepg)
        self.assertFalse(parentepg.has_tag('inherited:fvRsProv:mycontract'))
        contract = tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract)
        self.assertTrue(parentepg.does_provide(contract))

        self.delete_tenant()


class BaseImportedContract(unittest.TestCase):
    """
    Base class for tests for ContractInterface
    """
    def delete_tenants(self, provider_tenant_name, consumer_tenant_name):
        """
        Delete the tenants.  Called before and after tests automatically

        :param provider_tenant_name: String containing the tenant name exporting the contract
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :return: None
        """
        provider_tenant = Tenant(provider_tenant_name)
        provider_tenant.mark_as_deleted()
        consumer_tenant = Tenant(consumer_tenant_name)
        consumer_tenant.mark_as_deleted()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(4)
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)
        tenants = Tenant.get(apic)
        for tenant in tenants:
            self.assertTrue(tenant.name != provider_tenant_name)
            self.assertTrue(tenant.name != consumer_tenant_name)

    def setUp(self):
        self.delete_tenants('inheritanceautomatedtest-provider', 'inheritanceautomatedtest-consumer')

    def tearDown(self):
        self.delete_tenants('inheritanceautomatedtest-provider', 'inheritanceautomatedtest-consumer')

    def setup_tenants(self, apic, provider_tenant_name, consumer_tenant_name, use_contract_if=True):
        """
        Setup 2 tenants with 1 providing a contract that is consumed by the
        other tenant
        :param apic: Session instance that is assumed to be logged into the APIC
        :param provider_tenant_name: String containing the tenant name exporting the contract
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :return: None
        """
        provider_tenant = Tenant(provider_tenant_name)
        app = AppProfile('myinheritanceapp', provider_tenant)
        epg = EPG('myepg', app)
        contract = Contract('mycontract', provider_tenant)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        epg.provide(contract)
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        consumer_tenant = Tenant(consumer_tenant_name)
        context = Context('mycontext', consumer_tenant)
        l3out = OutsideL3('myl3out', consumer_tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        parent_network = OutsideNetwork('5.1.1.1', parent_epg)
        parent_network.ip = '5.1.1.1/8'
        child_epg = OutsideEPG('childepg', l3out)
        if use_contract_if:
            contract_if = ContractInterface('mycontract', consumer_tenant)
            contract_if.import_contract(contract)
            parent_epg.consume_cif(contract_if)
            resp = consumer_tenant.push_to_apic(apic)
            self.assertTrue(resp.ok)
        else:
            parent_epg.consume(contract)
            consumer_tenant_json = consumer_tenant.get_json()
            for child in consumer_tenant_json['fvTenant']['children']:
                if 'vzBrCP' in child:
                    consumer_tenant_json['fvTenant']['children'].remove(child)
            resp = apic.push_to_apic(consumer_tenant.get_url(), consumer_tenant_json)
            self.assertTrue(resp.ok)

    def add_child_subnet(self, apic, consumer_tenant_name):
        """
        Add a child subnet
        :param apic: Session instance that is assumed to be logged into the APIC
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :return: None
        """
        tenant = Tenant(consumer_tenant_name)
        l3out = OutsideL3('myl3out', tenant)
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('5.2.1.1', child_epg)
        child_network.ip = '5.2.1.1/16'
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, provider_tenant_name, consumer_tenant_name,
                         not_inherited=False, use_contract_if=True):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param provider_tenant_name: String containing the tenant name exporting the contract
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        fabric = Fabric()
        tenants = Tenant.get_deep(apic, names=[consumer_tenant_name, provider_tenant_name], parent=fabric)
        self.assertTrue(len(tenants) > 0)
        consumer_tenant = None
        provider_tenant = None
        for tenant in tenants:
            if tenant.name == consumer_tenant_name:
                consumer_tenant = tenant
            if tenant.name == provider_tenant_name:
                provider_tenant = tenant
        self.assertIsNotNone(consumer_tenant)
        l3out = consumer_tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        cons_word = 'fvRsCons'
        if use_contract_if:
            cons_word += 'If'
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:%s:mycontract' % cons_word))
        else:
            self.assertTrue(childepg.has_tag('inherited:%s:mycontract' % cons_word))
        if use_contract_if:
            contract_if = consumer_tenant.get_child(ContractInterface, 'mycontract')
        else:
            contract_if = provider_tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract_if)
        if not_inherited:
            if use_contract_if:
                self.assertFalse(childepg.does_consume_cif(contract_if))
            else:
                self.assertFalse(childepg.does_consume(contract_if))
        else:
            if use_contract_if:
                self.assertTrue(childepg.does_consume_cif(contract_if))
            else:
                self.assertTrue(childepg.does_consume(contract_if))

    def verify_not_inherited(self, apic, provider_tenant_name, consumer_tenant_name, use_contract_if=True):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :param provider_tenant_name: String containing the tenant name exporting the contract
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :return: None
        """
        self.verify_inherited(apic, provider_tenant_name, consumer_tenant_name,
                              not_inherited=True, use_contract_if=use_contract_if)

    def run_basic_test(self, provider_tenant_name, consumer_tenant_name, use_contract_if=True):
        """
        Run the test using the specified tenant names
        :param provider_tenant_name: String containing the tenant to export the contract
        :param consumer_tenant_name: String containing the tenant to import the contract
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "%s" % consumer_tenant_name,
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "%s" % consumer_tenant_name,
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenants(apic, provider_tenant_name, consumer_tenant_name, use_contract_if=use_contract_if)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic, provider_tenant_name, consumer_tenant_name, use_contract_if=use_contract_if)

        # Add the child subnet
        self.add_child_subnet(apic, consumer_tenant_name)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic, provider_tenant_name, consumer_tenant_name, use_contract_if=use_contract_if)


class TestImportedContract(BaseImportedContract):
    """
    Tests for ContractInterface
    """
    def test_basic_inherit_add_subnet(self):
        """
        Basic test for inheriting after adding a subnet
        """
        provider_tenant_name = 'inheritanceautomatedtest-provider'
        consumer_tenant_name = 'inheritanceautomatedtest-consumer'
        self.run_basic_test(provider_tenant_name, consumer_tenant_name)


class TestImportedContractFromTenantCommon(BaseImportedContract):
    """
    Tests for ContractInterface when Contract is imported from Tenant common
    """
    def delete_tenants(self, provider_tenant_name, consumer_tenant_name):
        """
        Delete the tenants.  Called before and after tests automatically

        :param provider_tenant_name: String containing the tenant name exporting the contract
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :return: None
        """
        provider_tenant = Tenant(provider_tenant_name)
        app = AppProfile('myinheritanceapp', provider_tenant)
        app.mark_as_deleted()
        contract = Contract('mycontract', provider_tenant)
        contract.mark_as_deleted()

        consumer_tenant = Tenant(consumer_tenant_name)
        consumer_tenant.mark_as_deleted()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(4)
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)
        tenants = Tenant.get(apic)
        for tenant in tenants:
            self.assertTrue(tenant.name != consumer_tenant_name)

    def setUp(self):
        self.delete_tenants('common', 'inheritanceautomatedtest-consumer')

    def tearDown(self):
        self.delete_tenants('common', 'inheritanceautomatedtest-consumer')

    def test_basic_inherit_add_subnet_provided_by_tenant_common(self):
        """
        Basic test for ContractInterface when Contract is imported from Tenant common
        """
        provider_tenant_name = 'common'
        consumer_tenant_name = 'inheritanceautomatedtest-consumer'
        self.run_basic_test(provider_tenant_name, consumer_tenant_name)


class TestImportedContractInterfaceFromTenantCommon(unittest.TestCase):
    """
    Tests for contract exported from 1 tenant to tenant common and consumed by another tenant
    """
    def delete_tenants(self):
        """
        Delete the tenants.  Called before and after tests automatically

        :return: None
        """
        # Login to the APIC
        apic = Session(credentials.url, credentials.username, credentials.password)
        resp = apic.login()
        self.assertTrue(resp.ok)

        # Delete the tenant common ContractInterface
        common_tenant = Tenant('common')
        contract_if = ContractInterface('contract-a-exported', common_tenant)
        contract_if.mark_as_deleted()
        resp = common_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)

        # Delete the consumer tenant
        consumer_tenant = Tenant('inheritanceautomatedtest-consumer')
        consumer_tenant.mark_as_deleted()
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)

        # Delete the provider tenant
        provider_tenant = Tenant('inheritanceautomatedtest-provider')
        provider_tenant.mark_as_deleted()
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)

        # Delete the consumer tenant
        consumer_tenant = Tenant('inheritanceautomatedtest-consumer')
        consumer_tenant.mark_as_deleted()
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)

        tenants = Tenant.get(apic)
        for tenant in tenants:
            self.assertTrue(tenant.name != consumer_tenant.name and tenant.name != provider_tenant.name)

    def setUp(self):
        self.delete_tenants()

    def tearDown(self):
        self.delete_tenants()

    def verify_inherited(self, apic, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        fabric = Fabric()
        tenants = Tenant.get_deep(apic,
                                  names=['common',
                                         'inheritanceautomatedtest-provider',
                                         'inheritanceautomatedtest-consumer'],
                                  parent=fabric)
        self.assertTrue(len(tenants) > 0)
        consumer_tenant = None
        provider_tenant = None
        common_tenant = None
        for tenant in tenants:
            if tenant.name == 'inheritanceautomatedtest-consumer':
                consumer_tenant = tenant
            if tenant.name == 'inheritanceautomatedtest-provider':
                provider_tenant = tenant
            if tenant.name == 'common':
                common_tenant = tenant
        self.assertIsNotNone(consumer_tenant)
        self.assertIsNotNone(provider_tenant)
        self.assertIsNotNone(common_tenant)
        l3out = consumer_tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsConsIf:contract-a-exported'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsConsIf:contract-a-exported'))
        contract_if = consumer_tenant.get_child(ContractInterface, 'contract-a-exported')
        self.assertIsNone(contract_if)
        contract_if = common_tenant.get_child(ContractInterface, 'contract-a-exported')
        self.assertEqual(contract_if.get_parent(), common_tenant)
        if not_inherited:
            self.assertFalse(childepg.does_consume_cif(contract_if))
        else:
            self.assertTrue(childepg.does_consume_cif(contract_if))

    def verify_not_inherited(self, apic):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        self.verify_inherited(apic, not_inherited=True)

    def setup_tenants(self, apic):
        """
        Setup 2 tenants with 1 providing a contract that is consumed by the
        other tenant
        :param apic: Session instance that is assumed to be logged into the APIC
        :return: None
        """
        provider_tenant = Tenant('inheritanceautomatedtest-provider')
        app = AppProfile('myinheritanceapp', provider_tenant)
        epg = EPG('myepg', app)
        contract = Contract('mycontract', provider_tenant)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        epg.provide(contract)
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        common_tenant = Tenant('common')
        contract_if = ContractInterface('contract-a-exported', common_tenant)
        contract_if.import_contract(contract)
        resp = common_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)

        consumer_tenant = Tenant('inheritanceautomatedtest-consumer')
        context = Context('mycontext', consumer_tenant)
        l3out = OutsideL3('myl3out', consumer_tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        parent_network = OutsideNetwork('5.1.1.1', parent_epg)
        parent_network.ip = '5.1.1.1/8'
        child_epg = OutsideEPG('childepg', l3out)
        parent_epg.consume_cif(contract_if)
        consumer_tenant_json = consumer_tenant.get_json()
        for child in consumer_tenant_json['fvTenant']['children']:
            if 'vzCPIf' in child:
                consumer_tenant_json['fvTenant']['children'].remove(child)
        resp = apic.push_to_apic(consumer_tenant.get_url(), consumer_tenant_json)
        self.assertTrue(resp.ok)

    def test_basic_inherit(self):
        """
        Basic test for when ContractInterface is imported from Tenant common
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest-consumer",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest-consumer",
                        "epg_container": {
                            "name": "myl3out",
                            "container_type": "l3out"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenants(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic)

        # Add the child subnet
        tenant = Tenant('inheritanceautomatedtest-consumer')
        l3out = OutsideL3('myl3out', tenant)
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('5.2.1.1', child_epg)
        child_network.ip = '5.2.1.1/16'
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)


class TestContractFromTenantCommonUsedInTenant(BaseImportedContract):
    """
    Tests for when Contract is imported from Tenant common not using ContractInterface
    """
    def delete_tenants(self, provider_tenant_name, consumer_tenant_name, use_contract_if=True):
        """
        Delete the tenants.  Called before and after tests automatically

        :param provider_tenant_name: String containing the tenant name exporting the contract
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :return: None
        """
        provider_tenant = Tenant(provider_tenant_name)
        app = AppProfile('myinheritanceapp', provider_tenant)
        app.mark_as_deleted()
        contract = Contract('mycontract', provider_tenant)
        contract.mark_as_deleted()

        consumer_tenant = Tenant(consumer_tenant_name)
        consumer_tenant.mark_as_deleted()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(4)
        resp = provider_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        resp = consumer_tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)
        time.sleep(2)
        tenants = Tenant.get(apic)
        for tenant in tenants:
            self.assertTrue(tenant.name != consumer_tenant_name)

    def setUp(self):
        self.delete_tenants('common', 'inheritanceautomatedtest-consumer')

    def tearDown(self):
        self.delete_tenants('common', 'inheritanceautomatedtest-consumer')

    def test_basic_inherit_add_subnet_provided_by_tenant_common(self):
        """
        Basic test for ContractInterface when Contract is imported from Tenant common
        """
        provider_tenant_name = 'common'
        consumer_tenant_name = 'inheritanceautomatedtest-consumer'
        self.run_basic_test(provider_tenant_name, consumer_tenant_name, use_contract_if=False)


class TestBasicAppProfile(BaseTestCase):
    """
    Basic Inheritance test cases enabled on Application Profile EPGs
    """
    def setup_tenant(self, apic):
        """
        Setup the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        context = Context('mycontext', tenant)
        app = AppProfile('myapp', tenant)
        parent_epg = EPG('parentepg', app)
        child_epg = EPG('childepg', app)
        contract = Contract('mycontract', tenant)
        parent_epg.provide(contract)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        app = tenant.get_child(AppProfile, 'myapp')
        self.assertIsNotNone(app)
        childepg = app.get_child(EPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract'))
        contract = tenant.get_child(Contract, 'mycontract')
        self.assertIsNotNone(contract)
        if not_inherited:
            self.assertFalse(childepg.does_provide(contract))
        else:
            self.assertTrue(childepg.does_provide(contract))

    def verify_not_inherited(self, apic):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        self.verify_inherited(apic, not_inherited=True)

    def test_basic_inherit_contract(self):
        """
        Basic inherit contract test
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True,
                    "inherit_from": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "parentepg"
                    }
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)
        tool.exit()
        # self.delete_tenant()

    def test_basic_inheritance_disallowed(self):
        """
        Basic test for when inheritance is disallowed
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "parentepg"
                    },
                    "allowed": False,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_not_inherited(apic)
        # self.delete_tenant()
        tool.exit()

    def test_basic_inheritance_disabled(self):
        """
        Basic test for when inheritance is disabled
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": False
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_not_inherited(apic)
        tool.exit()
        # self.delete_tenant()

    def test_get_config(self):
        """
        Basic test for getting the configuration
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": False
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(2)

        config = tool.get_config()
        self.assertEqual(config, config_json)

        tool.exit()


class TestBasicToolRestart(BaseTestCase):
    """
    Basic Inheritance test cases for when the inheritance tool is run and then restarted
    """
    def setup_tenant(self, apic, provide_contract=True):
        """
        Setup the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        context = Context('mycontext', tenant)
        app = AppProfile('myapp', tenant)
        parent_epg = EPG('parentepg', app)
        child_epg = EPG('childepg', app)
        if provide_contract:
            contract = Contract('mycontract', tenant)
            parent_epg.provide(contract)
            entry = FilterEntry('webentry1',
                                applyToFrag='no',
                                arpOpc='unspecified',
                                dFromPort='80',
                                dToPort='80',
                                etherT='ip',
                                prot='tcp',
                                sFromPort='1',
                                sToPort='65535',
                                tcpRules='unspecified',
                                parent=contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def add_contract_to_parent(self, apic):
        tenant = Tenant('inheritanceautomatedtest')
        app = AppProfile('myapp', tenant)
        parent_epg = EPG('parentepg', app)
        contract = Contract('mycontract', tenant)
        parent_epg.provide(contract)
        entry = FilterEntry('webentry1',
                            applyToFrag='no',
                            arpOpc='unspecified',
                            dFromPort='80',
                            dToPort='80',
                            etherT='ip',
                            prot='tcp',
                            sFromPort='1',
                            sToPort='65535',
                            tcpRules='unspecified',
                            parent=contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def remove_contract_from_parent(self, apic):
        """
        Remove the contract previously added in the setup of the tenant configuration
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        tenant = Tenant('inheritanceautomatedtest')
        app = AppProfile('myapp', tenant)
        parent_epg = EPG('parentepg', app)
        contract = Contract('mycontract', tenant)
        parent_epg.dont_provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, contract_provided=True, not_inherited=False):
        """
        Verify that the contracts have properly been inherited (or not inherited)
        :param apic: Session instance assumed to be logged into the APIC
        :param not_inherited: Boolean to indicate whether to verify that the contracts have properly been inherited or not
        :return: None
        """
        tenants = Tenant.get_deep(apic, names=['inheritanceautomatedtest'])
        self.assertTrue(len(tenants) > 0)
        tenant = tenants[0]
        app = tenant.get_child(AppProfile, 'myapp')
        self.assertIsNotNone(app)
        childepg = app.get_child(EPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsProv:mycontract'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsProv:mycontract'))
        contract = tenant.get_child(Contract, 'mycontract')
        if not contract_provided:
            self.assertIsNone(contract)
            return
        self.assertIsNotNone(contract)
        if not_inherited:
            self.assertFalse(childepg.does_provide(contract))
        else:
            self.assertTrue(childepg.does_provide(contract))

    def verify_not_inherited(self, apic, contract_provided=True):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :return: None
        """
        self.verify_inherited(apic, contract_provided=contract_provided, not_inherited=True)

    @staticmethod
    def get_config():
        """
        Get the configuration
        :return: Dictionary containing the JSON configuration
        """
        config_json = {
            "apic": {
                "user_name": credentials.username,
                "password": credentials.password,
                "ip_address": credentials.ip_address,
                "use_https": False
            },
            "inheritance_policies": [
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "childepg"
                    },
                    "allowed": True,
                    "enabled": True,
                    "inherit_from": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "parentepg"
                    }
                },
                {
                    "epg": {
                        "tenant": "inheritanceautomatedtest",
                        "epg_container": {
                            "name": "myapp",
                            "container_type": "app"
                        },
                        "name": "parentepg"
                    },
                    "allowed": True,
                    "enabled": False
                }
            ]
        }
        return config_json

    def test_basic_inherit_contract_add_parent_contract_during_outage(self):
        """
        Basic inherit contract test where the parent contract is added during the outage
        """
        config_json = self.get_config()
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic, provide_contract=False)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic, contract_provided=False)
        tool.exit()
        time.sleep(4)

        # Remove the contract from the parent EPG
        self.add_contract_to_parent(apic)

        # Start the tool again
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)
        tool.exit()

    def test_basic_inherit_contract_remove_parent_contract_during_outage(self):
        """
        Basic inherit contract test where the parent contract is removed during the outage
        """
        config_json = self.get_config()
        args = TestArgs()
        apic = Session(credentials.url, credentials.username, credentials.password)
        apic.login()
        self.setup_tenant(apic, provide_contract=True)
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is now inherited by the child EPG
        tool.exit()
        self.verify_inherited(apic)
        time.sleep(4)

        # Remove the contract from the parent EPG
        self.remove_contract_from_parent(apic)

        time.sleep(2)

        # Start the tool again
        tool = execute_tool(args)
        tool.add_config(config_json)
        time.sleep(6)

        # Verify that the contract is no longer inherited by the child EPG
        tool.exit()
        self.verify_not_inherited(apic)


credentials = ApicCredentials()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ACI Inheritance Tool')
    parser.add_argument('--config', default=None,
                        help='.ini file providing APIC credentials')
    parser.add_argument('--maxlogfiles', type=int, default=10,
                        help='Maximum number of log files (default is 10)')
    parser.add_argument('--debug', nargs='?',
                        choices=['verbose', 'warnings', 'critical'],
                        const='critical',
                        help='Enable debug messages.')
    args, unittest_args = parser.parse_known_args()

    # Deal with logging
    if args.debug is not None:
        if args.debug == 'verbose':
            level = logging.DEBUG
        elif args.debug == 'warnings':
            level = logging.WARNING
        else:
            level = logging.CRITICAL
    else:
        level = logging.CRITICAL
    format_string = '%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s'
    log_formatter = logging.Formatter(format_string)
    log_file = 'inheritance_test.%s.log' % str(getpid())
    my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5 * 1024 * 1024,
                                     backupCount=args.maxlogfiles,
                                     encoding=None, delay=0)
    my_handler.setLevel(level)
    my_handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(my_handler)
    logging.getLogger().setLevel(level)

    # Deal with credentials
    config_filename = args.config
    if config_filename is None:
        config_filename = DEFAULT_INI_FILENAME
    credentials.set_config(config_filename)
    if credentials.ip_address == '0.0.0.0':
        print 'APIC credentials not given. Please ensure that there is a .ini file present and credentials are filled in.'
        sys.exit()

    # Run the tests
    live = unittest.TestSuite()
    live.addTest(unittest.makeSuite(TestWithoutApicCommunication))
    live.addTest(unittest.makeSuite(TestBasicL3Out))
    live.addTest(unittest.makeSuite(TestContractEvents))
    live.addTest(unittest.makeSuite(TestSubnetEvents))
    live.addTest(unittest.makeSuite(TestImportedContract))
    live.addTest(unittest.makeSuite(TestImportedContractFromTenantCommon))
    live.addTest(unittest.makeSuite(TestBasicAppProfile))
    unittest.main(defaultTest='live', argv=sys.argv[:1] + unittest_args)
