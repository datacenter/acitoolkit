"""
Inheritance test suite
"""
import unittest
from inheritance import execute_tool
from acitoolkit import (Tenant, Context, OutsideL3, OutsideEPG, OutsideNetwork,
                        Contract, FilterEntry, Session, AppProfile, EPG,
                        ContractInterface, Fabric)
import time
try:
    from inheritance_test_credentials import *
except ImportError:
    print ('Please create a file named inheritance_test_credentials.py with the following content,'
           'replacing the values as approriate for your system:')
    print 'APIC_IP = "0.0.0.0"'
    print 'APIC_URL = "http://" + APIC_IP'
    print 'APIC_USERNAME = "admin"'
    print 'APIC_PASSWORD = "password"'


class TestArgs(object):
    """
    Fake class to mock out Command line arguments
    """
    def __init__(self):
        self.debug = 'verbose'
        self.maxlogfiles = 10
        self.generateconfig = False


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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
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


class TestBasic(BaseTestCase):
    """
    Basic Inheritance test cases
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

    def test_basic_inherit_contract(self):
        """
        Basic inherit contract test
        """
        config_json = {
            "apic": {
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args, cli_mode=False)
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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args, cli_mode=False)
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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args, cli_mode=False)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_not_inherited(apic)
        tool.exit()
        # self.delete_tenant()


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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args, cli_mode=False)
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args, cli_mode=False)
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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant_with_2_parent_epgs(apic)
        tool = execute_tool(args, cli_mode=False)
        tool.add_config(config_json)
        time.sleep(2)

        print 'STARTING VERIFICATION...'
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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant_with_2_parent_epgs(apic)
        tool = execute_tool(args, cli_mode=False)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        print 'REMOVING 1 CONTRACT'

        # Remove contract
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg1', l3out)
        contract = self.get_contract(tenant)
        parent_epg.provide(contract)
        parent_epg.dont_provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

        print 'STARTING VERIFICATION'

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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant_with_2_parent_epgs(apic)
        tool = execute_tool(args, cli_mode=False)
        tool.add_config(config_json)
        time.sleep(4)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic)

        print 'REMOVING 1 CONTRACT'

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

        print 'STARTING VERIFICATION'

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
        child_epg = OutsideEPG('childepg', l3out)
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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args, cli_mode=False)
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
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenant(apic)
        tool = execute_tool(args, cli_mode=False)
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
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

    def setup_tenants(self, apic, provider_tenant_name, consumer_tenant_name):
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
        contract_if = ContractInterface('mycontract', consumer_tenant)
        contract_if.import_contract(contract)
        parent_epg.consume_cif(contract_if)
        resp = consumer_tenant.push_to_apic(apic)
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

    def verify_inherited(self, apic, provider_tenant_name, consumer_tenant_name, not_inherited=False):
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
        for tenant in tenants:
            if tenant.name == consumer_tenant_name:
                consumer_tenant = tenant
                break
        self.assertIsNotNone(consumer_tenant)
        l3out = consumer_tenant.get_child(OutsideL3, 'myl3out')
        self.assertIsNotNone(l3out)
        childepg = l3out.get_child(OutsideEPG, 'childepg')
        self.assertIsNotNone(childepg)
        if not_inherited:
            self.assertFalse(childepg.has_tag('inherited:fvRsConsIf:mycontract'))
        else:
            self.assertTrue(childepg.has_tag('inherited:fvRsConsIf:mycontract'))
        contract_if = consumer_tenant.get_child(ContractInterface, 'mycontract')
        self.assertIsNotNone(contract_if)
        if not_inherited:
            self.assertFalse(childepg.does_consume_cif(contract_if))
        else:
            self.assertTrue(childepg.does_consume_cif(contract_if))

    def verify_not_inherited(self, apic, provider_tenant_name, consumer_tenant_name):
        """
        Verify that the contracts have not been inherited
        :param apic: Session instance assumed to be logged into the APIC
        :param provider_tenant_name: String containing the tenant name exporting the contract
        :param consumer_tenant_name: String containing the tenant name consuming the imported contract
        :return: None
        """
        self.verify_inherited(apic, provider_tenant_name, consumer_tenant_name, not_inherited=True)

    def run_basic_test(self, provider_tenant_name, consumer_tenant_name):
        """
        Run the test using the specified tenant names
        :param provider_tenant_name: String containing the tenant to export the contract
        :param consumer_tenant_name: String containing the tenant to import the contract
        """
        config_json = {
            "apic": {
                "user_name": APIC_USERNAME,
                "password": APIC_PASSWORD,
                "ip_address": APIC_IP,
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
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
        apic.login()
        self.setup_tenants(apic, provider_tenant_name, consumer_tenant_name)
        tool = execute_tool(args, cli_mode=False)
        tool.add_config(config_json)
        time.sleep(2)

        # Verify that the contract is not inherited by the child EPG
        self.verify_not_inherited(apic, provider_tenant_name, consumer_tenant_name)

        # Add the child subnet
        self.add_child_subnet(apic, consumer_tenant_name)
        time.sleep(2)

        # Verify that the contract is now inherited by the child EPG
        self.verify_inherited(apic, provider_tenant_name, consumer_tenant_name)


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

        consumer_tenant = Tenant(consumer_tenant_name)
        consumer_tenant.mark_as_deleted()
        apic = Session(APIC_URL, APIC_USERNAME, APIC_PASSWORD)
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


if __name__ == '__main__':
    try:
        if APIC_IP == '0.0.0.0':
            print 'Invalid APIC IP address in inheritance_test_credentials.py'
            raise ValueError
    except (NameError, ValueError):
        pass
    else:
        live = unittest.TestSuite()
        live.addTest(unittest.makeSuite(TestBasic))
        live.addTest(unittest.makeSuite(TestContractEvents))
        live.addTest(unittest.makeSuite(TestSubnetEvents))
        live.addTest(unittest.makeSuite(TestImportedContract))
        live.addTest(unittest.makeSuite(TestImportedContractFromTenantCommon))
        unittest.main(defaultTest='live')
