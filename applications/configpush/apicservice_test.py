"""
apicservice_test.py
"""
import json
import unittest
from apicservice import ApicService
from acitoolkit import (Tenant, Session, Filter, EPG, Contract, Context, ContractSubject, AppProfile, BridgeDomain,
                        AttributeCriterion)
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

    def load_configFile(self, config_file, is_file=True, prompt=False, displayonly=False, tenant_name='configpush-test',
                        app_name='appProfile-test', useipEpgs=False):
        """
        load_configFile

        :param config_file:
        :param is_file:
        :param displayonly:
        :param tenant_name:
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
        if useipEpgs:
            self.tool.use_ip_epgs()
        resp = self.tool.add_config(self.config)
        if resp != 'OK':
            print "ERROR in config. " + resp


class TestConfigpush(unittest.TestCase):
    """
    test case to push a contract config to APIC and update it in the next revision by changing some policies, filters, contracts
    """

    def test_displayonly_configpush(self):
        """
        this should just display the configuration. it shud not push to apic.
        to test this first i am deleting the tenant if exits and then with displayOnly uses the configpush and test the existence of tenant.
        the tenant should not exist.
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

        tenants = Tenant.get(load_config.session)
        for tenant in tenants:
            if tenant.name == 'configpush-test':
                tenant.mark_as_deleted()
                resp = tenant.push_to_apic(load_config.session)
                if not resp.ok:
                    print "tennat deletion failed"

        time.sleep(5)
        load_config.tool.displayonly = True
        resp = load_config.tool.add_config(load_config.config)
        if resp != 'OK':
            print "failed to login"

        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        tenant = Tenant(load_config.tool.tenant_name)
        self.assertFalse(Tenant.exists(load_config.session, tenant), "tenant exits")

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

    def test_update_configpush_for_filter_in_clusters(self):
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

    def test_update_configpush_for_epgs(self):
        """
        after the initial push
        deleting a cluster with name Configpushtest*-(2) and adding a cluster with name Configpushtest*-(3)
        when we push this config to apic, EPG Configpushtest_-_2_-1 shud be deleted and Configpushtest_-_3_-1 should be added.
        and also Contract Configpushtest_-_1_-0::Configpushtest_-_2_-1 should consume EPG Configpushtest_-_3_-1 should be consumed by
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
      "dst": "56c3d31561707035c0c13b00",
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
                    elif existing_epg.name == 'Configpushtest_-_3_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    self.assertTrue(existing_epg.name != 'Configpushtest_-_2_-1', "epg is not deleted successfully")

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
                                  "existing_contexts count did not match for the pushed config and existing config")

    def test_update_configpush_for_policy(self):
        """
        after the initial push
        deleting a policy with "src": "56c55b8761707062b2d11b00" and "dst": "56c3d31561707035c0c13b00",
        adding a new policy with "src": "56c55b8761707062b2d14b00" and "dst": "56c3d31561707035c0c15b00".
        But leaving the existing EPGs assosciated to previous one.
        when we push this config tp apic, the untouched EPGs should stay as is and the new EPGS assosciated the new policy should be added and the unwanted policy should be dleted.
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
    },
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
      "src_name": "Configpushtest-policy*-(4)",
      "dst_name": "Configpushtest-policy*-(5)",
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

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)

                self.assertEquals(len(existing_epgs), 4,
                                  "epgs count did not match for the pushed config and existing config")
                for existing_epg in existing_epgs:
                    self.assertEqual(existing_epg.is_attributed_based, False,
                                     "attribute based is true for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_1_-0':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_3_-1':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    if existing_epg.name == 'Configpushtest_-_4_-2':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 1,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 0,
                                         "provided EPG did not match for EPG " + existing_epg.name)
                    elif existing_epg.name == 'Configpushtest_-_5_-3':
                        self.assertEqual(len(existing_epg.get_all_consumed()), 0,
                                         "consumed EPG did not match for EPG " + existing_epg.name)
                        self.assertEqual(len(existing_epg.get_all_provided()), 1,
                                         "provided EPG did not match for EPG " + existing_epg.name)

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 1,
                                  "contracts count did not match for the pushed config and existing config")
                for existing_contract in existing_contracts:
                    self.assertEqual(existing_contract.name, "Configpushtest_-_4_-2::Configpushtest_-_5_-3",
                                     "contract name did not match with the config")
                    self.assertNotEqual(existing_contract.name, "Configpushtest_-_1_-0::Configpushtest_-2_-1",
                                        "contract name did not match with the config")
                    for child_contract_subject in existing_contract.get_children(ContractSubject):
                        self.assertEqual(len(child_contract_subject.get_filters()), 2,
                                         "num of filters in contract_subject did not match " + child_contract_subject.name)
                        self.assertEqual(child_contract_subject.name,
                                         "Configpushtest_-_4_-2::Configpushtest_-_5_-3_Subject",
                                         "contract_subject name did not match with the config")
                        self.assertNotEqual(child_contract_subject.name,
                                            "Configpushtest_-_1_-0::Configpushtest_-2_-1_Subject",
                                            "contract_subject name did not match with the config")

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
        after the initial push
        when we use ipEpgs, uSeg EPGS are created instead of Application EPGs
        and the only one uSeg Attribute should be existing in both EPGS
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
                            self.assertTrue(len(existing_attributeCriterion.get_ip_addresses()) == 1,
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

    def test_without_useipEpg_again_push_initial_configpush(self):
        """
        after useipepgs pushing back the initial config and check the tenant config doesnot change
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
                for existing_epg in existing_epgs:
                    self.assertTrue(existing_epg.name != 'Base',
                                    "Base EPG exists without useipEpgs" + existing_epg.name)

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

    def test_without_any_EPG_and_Contracts(self):
        """
        push a sample config with 0 clusters, 0 policy.
        check the tenant config after it is pushed to apic by tenant.get_deep()
        verify the num of children expected and existing in apic for this tenant
        """

        config_file = """
        {
  "clusters": [
   ],
  "policies": [
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
                self.assertEquals(len(existing_filters), 0,
                                  "filter count did not match for the pushed config and existing config")

                app_profiles = tenant.get_children(AppProfile)
                app = app_profiles[0]
                existing_epgs = app.get_children(EPG)
                self.assertEquals(len(existing_epgs), 0,
                                  "epgs count did not match for the pushed config and existing config")

                existing_contracts = tenant.get_children(Contract)
                self.assertEquals(len(existing_contracts), 0,
                                  "contracts count did not match for the pushed config and existing config")

                existing_bds = tenant.get_children(BridgeDomain)
                self.assertEquals(len(existing_bds), 0,
                                  "bridgeDomains count did not match for the pushed config and existing config")

                existing_contexts = tenant.get_children(Context)
                self.assertEquals(len(existing_contexts), 0,
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test1_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test1_policies':
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test1_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test1_policies':
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test2_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test2_policies':
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test2_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test2_policies':
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test3_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test3_policies':
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test3_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test3_policies':
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test4_policies")
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test4_policies':
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
        load_config = LoadConfig()
        load_config.load_configFile(config_file, tenant_name="configpush_test4_policies", useipEpgs=True)
        time.sleep(5)
        tenants = Tenant.get_deep(load_config.session, names=[load_config.tool.tenant_name])
        for tenant in tenants:
            if tenant.name == 'configpush_test4_policies':
                tenant_existing = ast.literal_eval(json.dumps(tenant.get_json()))
                with gzip.open('configpush_test4_policies_with_useipEpgs_tenant_golden.json.gz', 'rb') as data_file:
                    tenant_expected = ast.literal_eval(data_file.read())
                self.assertEqual(DeepDiff(tenant_existing, tenant_expected, ignore_order=True), {})

if __name__ == '__main__':
    configpush = unittest.TestSuite()
    configpush.addTest(unittest.makeSuite(TestConfigpush))
    configpush.addTest(unittest.makeSuite(TestCheckForAllTheJsonConfigs))
    unittest.main()
