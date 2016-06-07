from acitoolkit.acisession import Session
import unittest
import sys
import time
import sqlite3

from acitoolkit.acitoolkit import *
from acitoolkit.aciphysobject import *


class TestTenantUpdateInDatabase(unittest.TestCase):
    def setUp(self):
        session = Session("http://172.31.216.100", "admin", "ins3965!")
        try:
            resp = session.login()
            self.session = session
            print resp
            if not resp.ok:
                print('%% Could not login to APIC')
                sys.exit(0)
        except:
            print "unable to login"
        conn = sqlite3.connect("searchdatabase.db")
        self.conn = conn.cursor()

    def test_addNewTenant(self):
        tenant = Tenant('test_Tenant')
        self.assertNotEqual(tenant, None)
        app = AppProfile('test_App', tenant)
        self.assertNotEqual(app, None)
        epg = EPG('test_epg', app)
        self.assertNotEqual(epg, None)
        endpoint = Endpoint("00-11-22-33-44-55", epg)
        self.assertNotEqual(endpoint, None)
        attributeCriterion = AttributeCriterion('test_attr', epg)
        self.assertNotEqual(attributeCriterion, None)

        bridgeDomain = BridgeDomain('test_BridgeDomain', tenant)
        self.assertNotEqual(bridgeDomain, None)
        subnet = Subnet('test_subnet', bridgeDomain)
        subnet.set_addr('1.1.1.1/24')
        self.assertNotEqual(subnet, None)

        contractInterface = ContractInterface('test_ContractInterface', tenant)
        self.assertNotEqual(contractInterface, None)
        context = Context('test_Context', tenant)
        self.assertNotEqual(context, None)
        any_epg = AnyEPG('test_anyEPG', context)
        self.assertTrue(isinstance(any_epg, AnyEPG))

        contract = Contract('test_Contract', tenant)
        self.assertNotEqual(contract, None)
        contractSubject = ContractSubject('test_ContractSubject', contract)
        self.assertTrue(isinstance(contractSubject, ContractSubject))

        filter = Filter('test_Filter', tenant)
        self.assertNotEqual(filter, None)
        filt_entry = FilterEntry("test_filter_entry", filter)
        self.assertTrue(isinstance(filt_entry, FilterEntry))

        taboo = Taboo('test_Taboo', tenant)
        self.assertNotEqual(taboo, None)

        outsideL3 = OutsideL3('test_OutsideL3', tenant)
        self.assertNotEqual(outsideL3, None)
        self.assertTrue(isinstance(outsideL3, OutsideL3))

        outside_epg = OutsideEPG('test_outsideEPG', outsideL3)
        self.assertTrue(isinstance(outside_epg, OutsideEPG))
        outsideNetwork = OutsideNetwork('5.1.1.1', outside_epg)
        outsideNetwork.ip = '5.1.1.1/8'
        self.assertTrue(isinstance(outsideNetwork, OutsideNetwork))

        output_terminal = OutputTerminal('test_OutputTerminal', contractSubject)
        self.assertTrue(isinstance(output_terminal, OutputTerminal))

        resp = self.session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        if resp.ok:
            print 'Success'

        time.sleep(10)
        self.conn.execute("SELECT * FROM avc where class='Tenant' and attribute='name' and value='test_Tenant'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding tenant")
        self.assertTrue(result[0][1] == "test_Tenant", "value didnot match for the added tenant")

        self.conn.execute("SELECT * FROM avc where class='AppProfile' and attribute='name' and value='test_App'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding AppProfile")
        self.assertTrue(result[0][1] == "test_App", "value didnot match for the added AppProfile")

        self.conn.execute("SELECT * FROM avc where class='EPG' and attribute='name' and value='test_epg'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding Epg")
        self.assertTrue(result[0][1] == "test_epg", "value didnot match for the added epg")

        self.conn.execute("SELECT * FROM avc where class='Endpoint' and attribute='name'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding Endpoint")

        self.conn.execute("SELECT * FROM avc where class='AttributeCriterion' and attribute='name' and value='test_attr'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding AttributeCriterion")
        self.assertTrue(result[0][1] == "test_attr", "value didnot match for the added AttributeCriterion")

        self.conn.execute("SELECT * FROM avc where class='BridgeDomain' and attribute='name' and value='test_BridgeDomain'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding BridgeDomain")
        self.assertTrue(result[0][1] == "test_BridgeDomain", "value didnot match for the added BridgeDomain")

        self.conn.execute("SELECT * FROM avc where class='Taboo' and attribute='name' and value='test_Taboo'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding Taboo")
        self.assertTrue(result[0][1] == "test_Taboo", "value didnot match for the added Taboo")

        self.conn.execute("SELECT * FROM avc where class='OutsideL3' and attribute='name' and value='test_OutsideL3'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding OutsideL3")
        self.assertTrue(result[0][1] == "test_OutsideL3", "value didnot match for the added OutsideL3")

        self.conn.execute("SELECT * FROM avc where class='Filter' and attribute='name' and value='test_Filter'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding Filter")
        self.assertTrue(result[0][1] == "test_Filter", "value didnot match for the added Filter")

        self.conn.execute("SELECT * FROM avc where class='Context' and attribute='name' and value='test_Context'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding Context")
        self.assertTrue(result[0][1] == "test_Context", "value didnot match for the added Context")

        self.conn.execute("SELECT * FROM avc where class='Contract' and attribute='name' and value='test_Contract'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding Contract")
        self.assertTrue(result[0][1] == "test_Contract", "value didnot match for the added Contract")

        self.conn.execute("SELECT * FROM avc where class='ContractInterface' and attribute='name' and value='test_ContractInterface'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding ContractInterface")
        self.assertTrue(result[0][1] == "test_ContractInterface", "value didnot match for the added ContractInterface")

        self.conn.execute("SELECT * FROM avc where class='AnyEPG' and attribute='name' and uid='uni/tn-test_Tenant/ctx-test_Context/any'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding AnyEPG")

        self.conn.execute("SELECT * FROM avc where class='Subnet' and attribute='name' and value='test_subnet'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding Subnet")
        self.assertTrue(result[0][1] == "test_subnet", "value didnot match for the added Subnet")

        self.conn.execute("SELECT * FROM avc where class='OutsideEPG' and attribute='name' and value='test_outsideEPG'")
        result = self.conn.fetchall()
        self.assertTrue(result > 0, "successful in adding OutsideEPG")
        self.assertTrue(result[0][1] == "test_outsideEPG", "value didnot match for the added OutsideEPG")

        self.conn.execute("SELECT * FROM avc where class='OutsideNetwork' and attribute='name' and value='5.1.1.1'")
        result = self.conn.fetchall()

        self.assertTrue(result > 0, "successful in adding OutsideNetwork")
        self.assertTrue(result[0][1] == "5.1.1.1", "value didnot match for the added OutsideNetwork")

        self.conn.execute("SELECT * FROM avc where class='ContractSubject' and attribute='name' and value='test_ContractSubject'")
        result = self.conn.fetchall()

        self.assertTrue(result > 0, "successful in adding ContractSubject")
        self.assertTrue(result[0][1] == "test_ContractSubject", "value didnot match for the added ContractSubject")

        self.conn.execute("SELECT * FROM avc where class='OutputTerminal' and attribute='name' and value='test_OutputTerminal'")
        result = self.conn.fetchall()

        self.assertTrue(result > 0, "successful in adding OutputTerminal")
        self.assertTrue(result[0][1] == "test_OutputTerminal", "value did not match for the added OutputTerminal")

        self.conn.execute("SELECT * FROM avc where class='FilterEntry' and attribute='name' and value='test_filter_entry'")
        result = self.conn.fetchall()

        self.assertTrue(result > 0, "successful in adding FilterEntry")

        app.mark_as_deleted()
        epg.mark_as_deleted()
        bridgeDomain.mark_as_deleted()
        subnet.mark_as_deleted()
        contractInterface.mark_as_deleted()
        context.mark_as_deleted()
        any_epg.mark_as_deleted()
        contract.mark_as_deleted()
        filter.mark_as_deleted()
        contractSubject.mark_as_deleted()
        taboo.mark_as_deleted()
        outsideL3.mark_as_deleted()
        outside_epg.mark_as_deleted()
        outsideNetwork.mark_as_deleted()

        attributeCriterion.mark_as_deleted()
        endpoint.mark_as_deleted()
        filt_entry.mark_as_deleted()
        output_terminal.mark_as_deleted()
        tenant.mark_as_deleted()
        resp = self.session.push_to_apic(tenant.get_url(), data=tenant.get_json())
        if resp.ok:
            print 'Success'

        time.sleep(10)
        self.conn.execute("SELECT * FROM avc where class='Tenant' and attribute='name' and value='test_Tenant'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting tenant")

        self.conn.execute("SELECT * FROM avc where class='AppProfile' and attribute='name' and value='test_App'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting appprofile")

        self.conn.execute("SELECT * FROM avc where class='EPG' and attribute='name' and value='test_epg'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting Epg")

        self.conn.execute("SELECT * FROM avc where class='BridgeDomain' and attribute='name' and value='test_BridgeDomain'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting BridgeDomain")

        self.conn.execute("SELECT * FROM avc where class='Taboo' and attribute='name' and value='test_Taboo'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting Taboo")

        self.conn.execute("SELECT * FROM avc where class='OutsideL3' and attribute='name' and value='test_OutsideL3'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting OutsideL3")

        self.conn.execute("SELECT * FROM avc where class='Filter' and attribute='name' and value='test_Filter'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting Filter")

        self.conn.execute("SELECT * FROM avc where class='Context' and attribute='name' and value='test_Context'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting Context")

        self.conn.execute("SELECT * FROM avc where class='Contract' and attribute='name' and value='test_Contract'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting Contract")

        self.conn.execute("SELECT * FROM avc where class='ContractInterface' and attribute='name' and value='test_ContractInterface'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting ContractInterface")

        self.conn.execute("SELECT * FROM avc where class='OutsideEPG' and attribute='name' and value='test_outsideEPG'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting OutsideEPG")

        self.conn.execute("SELECT * FROM avc where class='OutsideNetwork' and attribute='name' and value='5.1.1.1'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting OutsideNetwork")

        self.conn.execute("SELECT * FROM avc where class='ContractSubject' and attribute='name' and value='test_ContractSubject'")
        result = self.conn.fetchall()
        self.assertTrue(len(result) == 0, "successful in deleting ContractSubject")


def main_test():
    full = unittest.TestSuite()
    full.addTest(unittest.makeSuite(TestTenantUpdateInDatabase))
    unittest.main()

if __name__ == '__main__':
    main_test()
