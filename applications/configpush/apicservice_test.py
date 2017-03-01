"""
apicservice_test.py
"""
import json
import unittest
from apicservice import ApicService
from acitoolkit import (Tenant, Session, Filter, EPG, Contract, Context, ContractSubject, AppProfile, BridgeDomain,
                        AttributeCriterion, OutsideL3, OutsideEPG, OutsideNetwork, Session)
import sys
import time
from deepdiff import DeepDiff
import gzip
from pprint import pprint
import ast

try:
    from apicservice_test_credentials import (LOGIN, PASSWORD, IPADDR)
except ImportError:
    print '''
            Please create a file called apicservice_test_credentials.py with the following:

            IPADDR = ''
            LOGIN = ''
            PASSWORD = ''
            '''
    sys.exit(0)


class LoadConfig(object):
    """
    class to load the config file, to create a session and ApicService object
    """

    def __init__(self):
        self.config = ''
        self.session = ''
        self.tool = ''

    def login(self):
        self.config = {}
        self.config['apic'] = {'user_name': LOGIN,
                               'password': PASSWORD,
                               'ip_address': IPADDR,
                               'use_https': False}
        session = Session(
            'http://' + self.config['apic']['ip_address'],
            self.config['apic']['user_name'],
            self.config['apic']['password'])
        resp = session.login()
        if not resp.ok:
            print('%% Could not login to APIC')
            sys.exit(0)
        return session

    def delete_tenant(self, tenant_name=''):
        load_config = LoadConfig()
        session = load_config.login()
        tenants = Tenant.get(session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(session)
                if not resp.ok:
                    print "tenant deletion failed"

    def load_configFile(self, config_file, is_file=True, prompt=False, displayonly=False, tenant_name='configpush-test',
                        app_name='appProfile-test', l3ext_name='l3ext-test', useipEpgs=False):
        """
        load_configFile

        :param config_file:
        :param is_file:
        :param displayonly:
        :param tenant_name:
        :param app_name:
        :param app_name:
        :param useipEpgs:
        :return:
        """
        if is_file:
            with gzip.open(config_file, 'rb') as config_file:
                self.config = json.load(config_file)
        else:
            self.config = json.loads(config_file)
        self.config['apic'] = {'user_name': LOGIN,
                               'password': PASSWORD,
                               'ip_address': IPADDR,
                               'use_https': False}

        self.session = Session('http://' + self.config['apic']['ip_address'], self.config['apic']['user_name'],
                               self.config['apic']['password'])
        resp = self.session.login()
        if not resp.ok:
            print('%% Could not login to APIC')
            sys.exit(0)

        self.tool = ApicService()
        self.tool.displayonly = displayonly
        self.tool.prompt = prompt
        self.tool.set_tenant_name(tenant_name)
        self.tool.set_app_name(app_name)
        self.tool.set_l3ext_name(l3ext_name)
        if useipEpgs:
            self.tool.use_ip_epgs()
        resp = self.tool.add_config(self.config)
        if resp != 'OK':
            print "ERROR in config. " + resp


class TestConfigpush(unittest.TestCase):
    """
    test case to push a contract config to APIC and update it in the next revision by changing some policies, filters, contracts
    """

    def test_initial_configpush(self):
        """
        initial test to configpush
        push a sample config with 2 clusters, 1 policy.
        check the tenant config after it is pushed to apic by tenant.get_deep()
        verify the num of children expected and existing in apic for this tenant
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        tenant_name = 'configpush-test'

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(
                    app.name,
                    'appProfile-test',
                    "application profile name didnot match with the default appProfile-test")

                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEquals(
                    outsideL3s[0].name,
                    'l3ext-test',
                    "External routed network with default name doesnot exist l3ext-test")

                for outsideL3 in outsideL3s:
                    if outsideL3.name == 'l3ext-test':
                        outsideEpgs = outsideL3.get_children(OutsideEPG)
                        self.assertEquals(len(outsideEpgs), 0, "the num of outside epgs didnot match")

                existing_epgs = app.get_children(EPG)
                self.assertEquals(len(existing_epgs), 2,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_2_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contractSubject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contractSubject.get_filters()), 2,
                                         "num of filters in contract subject did not match " + child_contractSubject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_tenantname_in_configpush(self):
        """
        this should test the tenant name. the tenant name pushed and the existing tenant name should match.
        to test this first i am deleting the tenant if exits and then  push the config,test the tenant name of existing tenant.
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1'
        load_config.load_configFile(config_file, is_file=False, tenant_name=tenant_name)
        time.sleep(5)

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        time.sleep(5)
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                self.assertTrue(True, "tennat exists with name " + tenant_name)
                
    def test_tenantname_for_invalidname_in_configpush(self):
        """
        this should test the tenant name of tenant. the invalid characters in tenant name should be removed.
        to test this first i am deleting the tenant if exits and then push the config,the tenant name in existing config from APIC should have valid characters.
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1**#####{{{{}}}}}$$$$$$######################abcdefgh'
        load_config.load_configFile(config_file, is_file=False, tenant_name=tenant_name)
        time.sleep(5)

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        time.sleep(5)
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get(load_config.session)# names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == "configpush-test1____________________________________________abc":
                self.assertTrue(True, "tennat exists with name " + tenant_name)

    def test_appProfilename_in_configpush(self):
        """
        this should test the application Profile name of tenant. the application Profile name pushed and the existing application Profile name should match.
        to test this first i am deleting the tenant if exits and then  push the config,the application Profile name in config and the application Profile name in existing tenant should match.
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1'
        app_name = 'app-test'
        load_config.load_configFile(config_file, is_file=False, tenant_name=tenant_name, app_name=app_name)
        time.sleep(5)

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        time.sleep(5)
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                self.assertTrue(True, "tennat exists with name " + tenant_name)
                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(app[0].name, app_name, "application profile with given name doesnot exist")
                
    def test_appProfilename_for_invalidname_in_configpush(self):
        """
        this should test the application Profile name of tenant. the invalid characters in application profile should be removed.
        to test this first i am deleting the tenant if exits and then  push the config,the application Profile name in existing config from APIC should have valid characters.
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1'
        app_name = 'app-test**-#.{}'
        load_config.load_configFile(config_file, is_file=False, tenant_name=tenant_name, app_name=app_name)
        time.sleep(5)

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        time.sleep(5)
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                self.assertTrue(True, "tennat exists with name " + tenant_name)
                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(app[0].name, "app-test**-_.__", "application profile with given name doesnot exist")
    
    def test_appProfilename_for_change_in_name_configpush(self):
        """
        this should test the application Profile name of tenant.push the same json with diferent --app name for the second time.
        so that the tenant should have the new application profile and the old one should be deleted
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1'
        app_name = 'app-test**-#.{}_changed'
        load_config.load_configFile(config_file, is_file=False, tenant_name=tenant_name, app_name=app_name)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                self.assertTrue(True, "tennat exists with name " + tenant_name)
                app_profiles = tenant.get_children(AppProfile)
                self.assertEqual(len(app_profiles), 1, "len(app_profiles)!=1")
                for app in app_profiles:
                    self.assertEquals(app.name, "app-test__-_.___changed", "application profile with name is not updated to the changed name")
        
        app_name = 'app-test_second**-#.{}_changed'
        load_config.load_configFile(config_file, is_file=False, tenant_name=tenant_name, app_name=app_name)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                self.assertTrue(True, "tennat exists with name " + tenant_name)
                app_profiles = tenant.get_children(AppProfile)
                self.assertEqual(len(app_profiles), 2, "len(app_profiles)!=2")


    def test_l3ext_name_in_configpush(self):
        """
        this should test the external routed network name of tenant. the external routed network name pushed and the existing external routed network name should match.
        to test this first i am deleting the tenant if exits and then  push the config,the external routed network name in config and the external routed network name in existing tenant should match.
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1'
        app_name = 'app-test'
        l3ext_name = 'l3external-test'
        load_config.load_configFile(
            config_file,
            is_file=False,
            tenant_name=tenant_name,
            app_name=app_name,
            l3ext_name=l3ext_name)
        time.sleep(5)

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        time.sleep(5)
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                self.assertTrue(True, "tenant exists with name " + tenant_name)
                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(app[0].name, app_name, "application profile with given name doesnot exist" + app_name)

                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEquals(
                    outsideL3s[0].name,
                    l3ext_name,
                    "External routed network with name doesnot exist" +
                    l3ext_name)
                
    def test_l3ext_name_for_invalidname_in_configpush(self):
        """
        this should test the external routed network name of tenant. the invalid characters in external routed network name should be removed.
        to test this first i am deleting the tenant if exits and then  push the config,the external routed network name in existing config from APIC should have valid characters.
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1'
        app_name = 'app-test'
        l3ext_name = 'l3external-test***#####:::{{{}}}}'
        load_config.load_configFile(
            config_file,
            is_file=False,
            tenant_name=tenant_name,
            app_name=app_name,
            l3ext_name=l3ext_name)
        time.sleep(5)

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        time.sleep(5)
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                self.assertTrue(True, "tenant exists with name " + tenant_name)
                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(app[0].name, app_name, "application profile with given name doesnot exist" + app_name)

                outsideL3s = tenant.get_children(OutsideL3)
                print "outsideL3s[0].name  is  "+outsideL3s[0].name
                self.assertEquals(
                    outsideL3s[0].name,
                    l3ext_name,
                    "External routed network with name doesnot exist" +
                    l3ext_name)
                
    def test_manglenames_in_configpush(self):
        """
        this should test the mangle_names method defined in apicserive.py.
        which will make sure the length of the names of EPGS,Filters, app_profiles, nodes, contracts not to exceed 64 characters 
        and also replaces the invalid characters
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest_____..***()()()%%%%%%%%%%%%*_to_test_length_of_Cluster_name*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "external": true,
      "route_tag": {
        "subnet_mask": "240.0.0.0/24",
        "name": "mcast-net"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "240.0.0.0",
          "name": "240.0.0.0/24",
          "prefix_len": 24
        }
      ]
    },
    {
      "name": "Configpushtest2____..***()()()%%%%%%%%%%%%*_to_test_length_of_Cluster_name*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "N/A"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "0.0.0.0",
          "name": "0.0.0.0/0",
          "prefix_len": 0
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy1_____..***()()()%%%%%%%%%%%%*to_test_length_of_Cluster_name*-(1)",
      "dst_name": "Configpushtest-policy2_____..***()()()%%%%%%%%%%%%*to_test_length_of_Cluster_name*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            81,
            81
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        tenant_name = 'configpush-test1***#####:::{{{}}}}'
        app_name = 'app-test***#####:::{{{}}}}'
        l3ext_name = 'l3external-test***#####:::{{{}}}}'
        load_config.load_configFile(
            config_file,
            is_file=False,
            tenant_name=tenant_name,
            app_name=app_name,
            l3ext_name=l3ext_name)
        time.sleep(5)

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        time.sleep(5)
        load_config = LoadConfig()
        load_config.load_configFile(
            config_file,
            is_file=False,
            tenant_name=tenant_name,
            app_name=app_name,
            l3ext_name=l3ext_name)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == "configpush-test1__________________":
                self.assertEqual("configpush-test1__________________", tenant.name, "tenant name mangled successfully")
                app_profiles = tenant.get_children(AppProfile)
                self.assertEqual(1, len(app_profiles), "num of app_profiles didnot match")
                for app_profile in app_profiles:
                    self.assertEqual("app-test__________________", app_profile.name, "app_profile name mangled successfully")
                    epgs = app_profile.get_children(EPG)
                    self.assertEqual(1, len(epgs), "num of epgs didnot match")
                    for epg in epgs:
                        self.assertEqual(epg.name, "Configpushtest2____..____-1", "epg name mangled successfully")
                    
                filters = tenant.get_children(Filter)
                self.assertEqual(1, len(filters), "num of filters didnot match")
                    
                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEqual(1, len(outsideL3s), "num of outsideL3s didnot match")
                for outsideL3 in outsideL3s:
                    self.assertEqual("l3external-test__________________", outsideL3.name, "outsideL3 name mangled successfully")
                    outsideEpgs = outsideL3.get_children(OutsideEPG)
                    self.assertEqual(1, len(outsideEpgs), "num 0f outsideEpgs didnot match")
                    for outsideEpg in outsideEpgs:
                        self.assertEqual(outsideEpg.name, "Configpushtest_____..____-0", "outsideEpg name mangled successfully")
                        outsideNetworks = outsideEpg.get_children(OutsideNetwork)
                        self.assertEqual(1, len(outsideNetworks), "num 0f outsideEpgs didnot match")
                        for outsideNetwork in outsideNetworks:
                            self.assertEqual(outsideNetwork.name, "240.0.0.0_24", "outsideNetwork name mangled successfully")
                    
                contracts = tenant.get_children(Contract)
                self.assertEqual(1, len(contracts), "num of contracts didnot match")
                for contract in contracts:
                    self.assertEqual(contract.name, "Configpushtest_____..____-0::Configpushtest2____..____-1", "contract name mangled successfully")
                    contract_subjects = contract.get_children(ContractSubject)
                    self.assertEqual(1, len(contract_subjects), "num 0f contract_subjects didnot match")
                    for contract_subject in contract_subjects:
                        self.assertEqual(contract_subject.name, "Configpushtest_____..____-0::Configpushtest2____..____-1_Subject", "contract_subject name mangled successfully")

    def test_update_configpush_for_clusters(self):
        """
        after the initial push
        adding a new cluster with name Configpushtest*-(3) without touching any others
        the epgs count should be only 2 now
        when we push this config to apic, the EPGs should stay as is and the new EPGS should not be added, count should match to two.
        """

        config_file = """
                {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    },
    {
      "name": "Configpushtest*-(3)",
      "id": "56c3d31561707035c0c13b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 2,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_2_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    self.assertNotEquals(existing_epg.name, "Configpushtest_-_3_-1", "the unwanted epg exists")

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    self.assertEqual(existing_contract.name, "Configpushtest_-_1_-0::Configpushtest_-_2_-1",
                                     "contract name did not match with the config")
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)
                        self.assertEqual(child_contract_subject.name,
                                         "Configpushtest_-_1_-0::Configpushtest_-_2_-1_Subject",
                                         "contract_subject name did not match with the config")

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_for_clusters_deletion(self):
        """
        deleting a new cluster with name Configpushtest*-(3) without touching any others
        the epgs count should be only 2 now
        when we push this config tp apic, the EPGs should stay as is and the new EPGS should not be added, count should match to two.
        """

        config_file = """
                {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 2,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_2_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    self.assertNotEquals(existing_epg.name, "Configpushtest_-_3_-1", "the unwanted epg exists")

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    self.assertEqual(existing_contract.name, "Configpushtest_-_1_-0::Configpushtest_-_2_-1",
                                     "contract name did not match with the config")
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)
                        self.assertEqual(child_contract_subject.name,
                                         "Configpushtest_-_1_-0::Configpushtest_-_2_-1_Subject",
                                         "contract_subject name did not match with the config")

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_for_filter_in_policies(self):
        """
        deleting a filter 6.0.0 and adding a filter 17.0.0
        when we push this config to apic, filter 6.0.0 should be deleted and filter 17.0.0 should be added in Filters
        Also this change should be reflected in Contracts. the relation in ContractSubject should point to 17.0.0 instead of 6.0.0
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            1,
            1
          ],
          "proto": 17,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")
                for existing_filter in existing_filters:
                    self.assertTrue(existing_filter.name in ['1.0.0_Filter', '17.1.1_Filter'])
                    self.assertTrue(existing_filter.name != '6.0.0_Filter')

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 2,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_2_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)
                        for contract_subject_filter in child_contract_subject.get_filters():
                            self.assertTrue(contract_subject_filter.name in ['1.0.0_Filter', '17.1.1_Filter'])
                            self.assertTrue(contract_subject_filter.name != '6.0.0_Filter')

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_for_filter_addition(self):
        """
        adding a filter 18.0.0, 19.1.1
        when we push this config to apic, filters 18.0.0 and 19.1.1 should be added in Filters and the count should be 4
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            1,
            1
          ],
          "proto": 17,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 18,
          "action": "ALLOW"
        },
        {
          "port": [
            1,
            1
          ],
          "proto": 19,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 4,
                                  "filter count did not match for the pushed config and existing config")
                for existing_filter in existing_filters:
                    self.assertTrue(
                        existing_filter.name in [
                            '1.0.0_Filter',
                            '17.1.1_Filter',
                            '18.0.0_Filter',
                            '19.1.1_Filter'])
                    self.assertTrue(existing_filter.name != '6.0.0_Filter')

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 2,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_2_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 4,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)
                        for contract_subject_filter in child_contract_subject.get_filters():
                            self.assertTrue(
                                contract_subject_filter.name in [
                                    '1.0.0_Filter',
                                    '17.1.1_Filter',
                                    '18.0.0_Filter',
                                    '19.1.1_Filter'])
                            self.assertTrue(contract_subject_filter.name != '6.0.0_Filter')

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_for_policies(self):
        """
        changing the source and destination of the policy. so the contract should be updated with respect to this
        """

        config_file = """
                {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c3d31561707035c0c12b00",
      "dst": "56c55b8761707062b2d11b00",
      "src_name": "Configpushtest-policy*-(2)",
      "dst_name": "Configpushtest-policy*-(1)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 2,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_2_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    self.assertEqual(existing_contract.name, "Configpushtest_-_2_-1::Configpushtest_-_1_-0",
                                     "contract name did not match with the config")
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)
                        self.assertEqual(child_contract_subject.name,
                                         "Configpushtest_-_2_-1::Configpushtest_-_1_-0_Subject",
                                         "contract_subject name did not match with the config")

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_for_policies_addition(self):
        """
        adding a new policy.
        now the contracts should be 2 without changing the filters and epgs
        the epgs count should be only 2 now
        when we push this config tp apic, the EPGs should stay as is and the new EPGS should not be added, count should match to two.
        """

        config_file = """
                {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    },
    {
      "src":  "56c3d31561707035c0c12b00",
      "dst": "56c55b8761707062b2d11b00",
      "src_name": "Configpushtest-policy*-(2)",
      "dst_name": "Configpushtest-policy*-(1)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 17,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 18,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 4,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 2,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_2_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 2,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    if existing_contract.name == "Configpushtest_-_1_-0::Configpushtest_-_2_-1":
                        self.assertEqual(existing_contract.name, "Configpushtest_-_1_-0::Configpushtest_-_2_-1",
                                         "contract name did not match with the config")
                        for child_contract_subject in existing_contract.get_children(ContractSubject):
                            self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                             "num of filters in contract_subject did not match " + child_contract_subject.name)
                            self.assertEqual(child_contract_subject.name,
                                             "Configpushtest_-_1_-0::Configpushtest_-_2_-1_Subject",
                                             "contract_subject name did not match with the config")

                    elif existing_contract.name == "Configpushtest_-_2_-1::Configpushtest_-_1_-0":
                        self.assertEqual(existing_contract.name, "Configpushtest_-_2_-1::Configpushtest_-_1_-0",
                                         "contract name did not match with the config")
                        for child_contract_subject in existing_contract.get_children(ContractSubject):
                            self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                             "num of filters in contract_subject did not match " + child_contract_subject.name)
                            self.assertEqual(child_contract_subject.name,
                                             "Configpushtest_-_2_-1::Configpushtest_-_1_-0_Subject",
                                             "contract_subject name did not match with the config")

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_l3out_external_initial(self):
        """
        initial test to configpush with l3out epgs
        firstly delete the existing tenant and push the config for the first time.
        config has external true for 1 policy and external false for the other
        after pushing the config there should be 1 epg in appProfile and 1 in External routed networks
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "external": true,
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        tenant_name = 'configpush-test'

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(
                    app.name,
                    'appProfile-test',
                    "application profile name didnot match with the default appProfile-test")

                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEquals(
                    outsideL3s[0].name,
                    'l3ext-test',
                    "External routed network with default name doesnot exist l3ext-test")

                for outsideL3 in outsideL3s:
                    if outsideL3.name == 'l3ext-test':
                        outsideEpgs = outsideL3.get_children(OutsideEPG)
                        self.assertEquals(len(outsideEpgs), 1, "the num of outside epgs didnot match")
                        for outsideEpg in outsideEpgs:
                            self.assertEquals(outsideEpg.name, "Configpushtest_-_2_-1", "outside EPG name didnot match")
                            self.assertNotEquals(
                                outsideEpg.name,
                                "Configpushtest_-_1_-0",
                                "outside EPG name didnot match")
                            self.assertEqual(len(outsideEpg.get_all_consumed()), 0,
                                             "consumed EPG did not match for EPG " + outsideEpg.name)
                            self.assertEqual(len(outsideEpg.get_all_provided()), 1,
                                             "provided EPG did not match for EPG " + outsideEpg.name)

                existing_epgs = app.get_children(EPG)
                self.assertEquals(len(existing_epgs), 1,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    self.assertNotEquals(existing_epg.name, "Configpushtest_-_2_-1", "outside EPG name didnot match")
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contractSubject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contractSubject.get_filters()), 2,
                                         "num of filters in contract subject did not match " + child_contractSubject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_l3out_for_external(self):
        """
        after the initial l3out push changing the external to true for the cluster with name Configpushtest*-(1)
        after pushing this there should be 2 l3out epgs in external routed netwroks and no epg in appProfile
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "external": true,
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "external": true,
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        tenant_name = 'configpush-test'

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(
                    app.name,
                    'appProfile-test',
                    "application profile name didnot match with the default appProfile-test")

                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEquals(
                    outsideL3s[0].name,
                    'l3ext-test',
                    "External routed network with default name doesnot exist l3ext-test")

                for outsideL3 in outsideL3s:
                    if outsideL3.name == 'l3ext-test':
                        outsideEpgs = outsideL3.get_children(OutsideEPG)
                        self.assertEquals(len(outsideEpgs), 2, "the num of outside epgs didnot match")
                        for existing_epg in outsideEpgs:
                            if existing_epg.name == 'Configpushtest_-_1_-0':
                                self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                                 "consumed EPG did not match for EPG " + existing_epg.name)
                                self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                                 "provided EPG did not match for EPG " + existing_epg.name)
                            elif existing_epg.name == 'Configpushtest_-_2_-1':
                                self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                                 "consumed EPG did not match for EPG " + existing_epg.name)
                                self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                                 "provided EPG did not match for EPG " + existing_epg.name)

                existing_epgs = app.get_children(EPG)
                self.assertEquals(len(existing_epgs), 0,
                                  "epgs count did not match for the pushed config and existing config")

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contractSubject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contractSubject.get_filters()), 2,
                                         "num of filters in contract subject did not match " + child_contractSubject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_l3out_for_external_delete(self):
        """
        changing the external to false for the cluster with name Configpushtest*-(1)
        after pushing this there should be 2 l3out epgs in external routed netwroks and a single epg in appProfile
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "external": true,
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(
                    app.name,
                    'appProfile-test',
                    "application profile name didnot match with the default appProfile-test")

                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEquals(
                    outsideL3s[0].name,
                    'l3ext-test',
                    "External routed network with default name doesnot exist l3ext-test")

                for outsideL3 in outsideL3s:
                    if outsideL3.name == 'l3ext-test':
                        outsideEpgs = outsideL3.get_children(OutsideEPG)
                        self.assertEquals(len(outsideEpgs), 2, "the num of outside epgs didnot match")
                        for existing_epg in outsideEpgs:
                            if existing_epg.name == 'Configpushtest_-_1_-0':
                                self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                                 "consumed EPG did not match for EPG " + existing_epg.name)
                                self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                                 "provided EPG did not match for EPG " + existing_epg.name)
                            elif existing_epg.name == 'Configpushtest_-_2_-1':
                                self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                                 "consumed EPG did not match for EPG " + existing_epg.name)
                                self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                                 "provided EPG did not match for EPG " + existing_epg.name)

                existing_epgs = app.get_children(EPG)
                self.assertEquals(len(existing_epgs), 0,
                                  "epgs count did not match for the pushed config and existing config")
                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contractSubject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contractSubject.get_filters()), 2,
                                         "num of filters in contract subject did not match " + child_contractSubject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_l3out_for_external_policy(self):
        """
        changing the source and destination of the policy. so the contract should be updated with respect to this
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "external": true,
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "external": true,
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c3d31561707035c0c12b00",
      "dst": "56c55b8761707062b2d11b00",
      "src_name": "Configpushtest-policy*-(2)",
      "dst_name": "Configpushtest-policy*-(1)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 7,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")
                for existing_filter in existing_filters:
                    self.assertTrue(existing_filter.name in ['1.0.0_Filter', '7.0.0_Filter'])
                    self.assertTrue(existing_filter.name != '6.0.0_Filter')

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(
                    app.name,
                    'appProfile-test',
                    "application profile name didnot match with the default appProfile-test")

                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEquals(
                    outsideL3s[0].name,
                    'l3ext-test',
                    "External routed network with default name doesnot exist l3ext-test")

                for outsideL3 in outsideL3s:
                    if outsideL3.name == 'l3ext-test':
                        outsideEpgs = outsideL3.get_children(OutsideEPG)
                        self.assertEquals(len(outsideEpgs), 2, "the num of outside epgs didnot match")
                        for existing_epg in outsideEpgs:
                            if existing_epg.name == 'Configpushtest_-_1_-0':
                                self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                                 "consumed EPG did not match for EPG " + existing_epg.name)
                                self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                                 "provided EPG did not match for EPG " + existing_epg.name)
                            elif existing_epg.name == 'Configpushtest_-_2_-1':
                                self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                                 "consumed EPG did not match for EPG " + existing_epg.name)
                                self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                                 "provided EPG did not match for EPG " + existing_epg.name)

                existing_epgs = app.get_children(EPG)
                self.assertEquals(len(existing_epgs), 0,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    self.assertNotEquals(existing_epg.name, "Configpushtest_-_2_-1", "outside EPG name didnot match")
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contractSubject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contractSubject.get_filters()), 2,
                                         "num of filters in contract subject did not match " + child_contractSubject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_useipEpg_configpush_for_policy(self):
        """
        after the initial push
        when we use ipEpgs, uSeg EPGS are created instead of Application EPGs
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(4)",
      "id": "56c55b8761707062b2d14b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(5)",
      "id": "56c3d31561707035c0c15b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.129",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d14b00",
      "dst": "56c3d31561707035c0c15b00",
      "src_name": "Configpushtest-policy*-(6)",
      "dst_name": "Configpushtest-policy*-(7)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            1,
            1
          ],
          "proto": 17,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        tenant_name = 'configpush-test'

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tenant deletion failed"

        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False, useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 3,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    if existing_epg.name != 'base':
                        self.assertTrue(existing_epg.is_attributed_based,
                                        "uSeg EPG is not created for " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 1,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 1,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_useipEpg_node_update_configpush_for_policy(self):
        """
        after the initial push of useipepgs
        when we use ipEpgs, uSeg EPGS are created instead of Application EPGs
        and the 2 uSeg Attribute should be existing in both EPGS from the previous run
        and the contract should be pointing to the latest epgs
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(4)",
      "id": "56c55b8761707062b2d14b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-421"
        }
      ]
    },
    {
      "name": "Configpushtest*-(5)",
      "id": "56c3d31561707035c0c15b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-423"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d14b00",
      "dst": "56c3d31561707035c0c15b00",
      "src_name": "Configpushtest-policy*-(6)",
      "dst_name": "Configpushtest-policy*-(7)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            1,
            1
          ],
          "proto": 17,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False, useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 3,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    if existing_epg.name != 'base':
                        self.assertTrue(existing_epg.is_attributed_based,
                                        "uSeg EPG is not created for " + existing_epg.name)
                        existing_attributeCriterions = existing_epg.get_children(AttributeCriterion)
                        for existing_attributeCriterion in existing_attributeCriterions:
                            self.assertTrue(len(existing_attributeCriterion.get_ip_addresses()) == 2,
                                            "uSeg Attributes did not match")

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 1,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 1,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_useipepgs_update_for_bridgeDomain(self):
        """
        push without useipepgs and check for bridgeDomain
        bridgeDomain should not be deleted once it is created
        """

        config_file = """
        {
  "clusters": [
    {
      "name": "Configpushtest*-(1)",
      "id": "56c55b8761707062b2d11b00",
      "descr": "sample description",
      "route_tag": {
        "subnet_mask": "173.38.111.0/24",
        "name": "rtp1-dcm01n-gp-db-dr2:iv2133"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.127",
          "name": "lnxdb-dr-vm-421"
        },
        {
          "ip": "173.38.111.131",
          "name": "lnxdb-dr-vm-422"
        }
      ]
    },
    {
      "name": "Configpushtest*-(2)",
      "id": "56c3d31561707035c0c12b00",
      "descr": "sample description",
      "approved": true,
      "route_tag": {
        "subnet_mask": "0.0.0.0/0",
        "name": "INTERNET-EXTNET"
      },
      "labels": [

      ],
      "nodes": [
        {
          "ip": "173.38.111.126",
          "name": "lnxdb-dr-vm-423"
        },
        {
          "ip": "173.38.111.128",
          "name": "lnxdb-dr-vm-424"
        }
      ]
    }
   ],
  "policies": [
    {
      "src": "56c55b8761707062b2d11b00",
      "dst": "56c3d31561707035c0c12b00",
      "src_name": "Configpushtest-policy*-(1)",
      "dst_name": "Configpushtest-policy*-(2)",
      "descr": "sample description",
      "whitelist": [
        {
          "port": [
            0,
            0
          ],
          "proto": 1,
          "action": "ALLOW"
        },
        {
          "port": [
            0,
            0
          ],
          "proto": 6,
          "action": "ALLOW"
        }
      ]
    }
  ]
}
        """
        load_config = LoadConfig()
        load_config.load_configFile(config_file, is_file=False)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                existing_filters = tenant.get_children(Filter)
                self.assertEquals(len(existing_filters), 2,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                self.assertEquals(
                    app.name,
                    'appProfile-test',
                    "application profile name didnot match with the default appProfile-test")

                outsideL3s = tenant.get_children(OutsideL3)
                self.assertEquals(
                    outsideL3s[0].name,
                    'l3ext-test',
                    "External routed network with default name doesnot exist l3ext-test")

                for outsideL3 in outsideL3s:
                    if outsideL3.name == 'l3ext-test':
                        outsideEpgs = outsideL3.get_children(OutsideEPG)
                        self.assertEquals(len(outsideEpgs), 0, "the num of outside epgs didnot match")

                existing_epgs = app.get_children(EPG)
                self.assertEquals(len(existing_epgs), 3,
                                  "epgs count did not match for the pushed config and existing config")

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contractSubject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contractSubject.get_filters()), 2,
                                         "num of filters in contract subject did not match " + child_contractSubject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 1,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 1,
                                  "existing_contexts count did not match for the pushed config and existing config")


class TestCheckForAllTheJsonConfigs(unittest.TestCase):
    """
    test case to push a ontract config from a specific json.
    After it is pushed successfully using Apicservice,
    then tenant.get_deep() is compared with the expected json
    """

    def test_configpush_test1_policies(self):
        """
        configpush_test1_policies.json
        providing configpush_test1_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test1_policies.json.gz'

        tenant_name = 'configpush_test1_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test1_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test1_policies_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

    def test_configpush_test1_policies_with_useipEpgs(self):
        """
        configpush_test1_policies.json
        providing configpush_test1_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test1_policies.json.gz'

        tenant_name = 'configpush_test1_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test1_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test1_policies_with_useipEpgs_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

    def test_configpush_test2_policies(self):
        """
        configpush_test2_policies.json
        providing configpush_test2_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test2_policies.json.gz'

        tenant_name = 'configpush_test2_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test2_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test2_policies_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

    def test_configpush_test2_policies_with_useipEpgs(self):
        """
        configpush_test2_policies.json
        providing configpush_test2_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test2_policies.json.gz'

        tenant_name = 'configpush_test2_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test2_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test2_policies_with_useipEpgs_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

    def test_configpush_test3_policies(self):
        """
        configpush_test3_policies.json
        providing configpush_test3_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test3_policies.json.gz'

        tenant_name = 'configpush_test3_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test3_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test3_policies_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

    def test_configpush_test3_policies_with_useipEpgs(self):
        """
        configpush_test3_policies.json
        providing configpush_test3_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test3_policies.json.gz'

        tenant_name = 'configpush_test3_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test3_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test3_policies_with_useipEpgs_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

    def test_configpush_test4_policies(self):
        """
        configpush_test4_policies.json
        providing configpush_test4_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test4_policies.json.gz'

        tenant_name = 'configpush_test4_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test4_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test4_policies_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

    def test_configpush_test4_policies_with_useipEpgs(self):
        """
        configpush_test4_policies.json
        providing configpush_test4_policies.json to apicservice and
        comparing with the expected json
        """
        config_file = 'configpush_test4_policies.json.gz'

        tenant_name = 'configpush_test4_policies'
        load_config = LoadConfig()
        load_config.delete_tenant(tenant_name)

        load_config.load_configFile(config_file, tenant_name="configpush_test4_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == tenant_name:
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test4_policies_with_useipEpgs_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

if __name__ == '__main__':
    configpush = unittest.TestSuite()
    configpush.addTest(unittest.makeSuite(TestConfigpush))
    configpush.addTest(unittest.makeSuite(TestCheckForAllTheJsonConfigs))
    unittest.main()
