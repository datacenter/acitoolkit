import unittest
from inheritance import execute_tool
from acitoolkit import *
import time

APIC_IP = '0.0.0.0'
APIC_URL = 'http://' + APIC_IP
APIC_USERNAME = 'admin'
APIC_PASSWORD = 'password'


class TestArgs(object):
    def __init__(self):
        self.debug = 'verbose'
        self.maxlogfiles = 10
        self.generateconfig = False


class BaseTestCase(unittest.TestCase):
    def delete_tenant(self):
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
    def setup_tenant(self, apic):
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
        self.verify_inherited(apic, not_inherited=True)

    def test_basic_inherit_contract(self):
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": True
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
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
        #self.delete_tenant()

    def test_basic_inheritance_disallowed(self):
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": True
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
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
        #self.delete_tenant()
        tool.exit()

    def test_basic_inheritance_disabled(self):
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": False
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
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
        #self.delete_tenant()

# TODO write tests for all of the events - add subnet later, delete subnet, add contract later, delete contract, remove relation, etc.

class TestContractEvents(BaseTestCase):
    def get_config_json(self):
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": True
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "parentepg"
                          },
                          "allowed": True,
                          "enabled": False
                }

              ]
            }
        return config_json

    def get_contract(self, tenant):
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
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        contract = self.get_contract(tenant)
        parent_epg.provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def remove_contract(self, apic):
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        parent_epg = OutsideEPG('parentepg', l3out)
        contract = self.get_contract(tenant)
        parent_epg.provide(contract)
        parent_epg.dont_provide(contract)
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, not_inherited=False):
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
        self.verify_inherited(apic, not_inherited=True)

    def test_basic_inherit_contract(self):
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
        self.delete_tenant()
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": True
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "parentepg1"
                          },
                          "allowed": True,
                          "enabled": False
                },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
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
        self.delete_tenant()
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": True
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "parentepg1"
                          },
                          "allowed": True,
                          "enabled": False
                },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
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
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": True
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "parentepg1"
                          },
                          "allowed": True,
                          "enabled": False
                },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
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
    def setup_tenant(self, apic):
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
        tenant = Tenant('inheritanceautomatedtest')
        l3out = OutsideL3('myl3out', tenant)
        child_epg = OutsideEPG('childepg', l3out)
        child_network = OutsideNetwork('5.2.1.1', child_epg)
        child_network.ip = '5.2.1.1/16'
        resp = tenant.push_to_apic(apic)
        self.assertTrue(resp.ok)

    def verify_inherited(self, apic, not_inherited=False):
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
        self.verify_inherited(apic, not_inherited=True)

    def test_basic_inherit_add_subnet(self):
        config_json = {
              "apic": {"user_name": APIC_USERNAME,
                             "password": APIC_PASSWORD,
                             "ip_address": APIC_IP,
                             "use_https": False
              },
              "inheritance_policies": [{
                          "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
                              "name": "childepg"
                          },
                          "allowed": True,
                          "enabled": True
              },
                {
                  "epg": {
                              "tenant": "inheritanceautomatedtest",
                              "epg_container": {"name": "myl3out",
                                                "container_type": "l3out"},
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


if __name__ == '__main__':
    if APIC_IP == '0.0.0.0':
        print 'Please set the APIC credentials at the top of the test file'
    else:
        live = unittest.TestSuite()
        live.addTest(unittest.makeSuite(TestBasic))
        live.addTest(unittest.makeSuite(TestContractEvents))

        unittest.main(defaultTest='live')

