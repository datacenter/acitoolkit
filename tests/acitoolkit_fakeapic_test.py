"""acitoolkit_fakeapic_test.py Test module
"""
import unittest
import argparse
import sys
from acitoolkit import FakeSession
from os import listdir
import json


class TestFakeApic(unittest.TestCase):
    """
    Tests for the Fake APIC
    """
    @classmethod
    def setUpClass(cls):
        cls.session = FakeSession(filenames)

    def test_get(self):
        """
        Test a basic get() call
        """
        query = '/api/class/fvTenant.json'
        fake_ret = self.session.get(query)
        data = fake_ret.json()['imdata']

        for tenant in data:
            self.assertIn('fvTenant', tenant)

    def test_get_epgs(self):
        """
        Test a basic class get() call to a class that is not top level
        """
        query = '/api/class/fvAEPg.json'
        fake_ret = self.session.get(query)
        data = fake_ret.json()['imdata']

        for epg in data:
            self.assertIn('fvAEPg', epg)

    def test_get_with_subtree(self):
        """
        Test a get() call querying the subtree
        """
        query = ('/api/mo/uni/tn-common.json?query-target=subtree&'
                 'target-subtree-class=fvAEPg')
        fake_ret = self.session.get(query)
        data = fake_ret.json()['imdata']
        for epg in data:
            self.assertIn('fvAEPg', epg)

    def test_get_with_self(self):
        """
        Test a get() call querying self
        """
        query = '/api/mo/uni/tn-common.json?query-target=self'
        fake_ret = self.session.get(query)
        data = fake_ret.json()['imdata']
        for tenant in data:
            self.assertIn('fvTenant', tenant)

    def test_get_with_children(self):
        """
        Test a get() call querying children
        """
        query = ('/api/mo/uni/tn-common.json?query-target=children&'
                 'target-subtree-class=fvAEPg')
        fake_ret = self.session.get(query)
        data = fake_ret.json()['imdata']
        for epg in data:
            self.assertIn('fvAEPg', epg)

    def test_get_with_children_rsp_subtree_children(self):
        """
        Test a get() call querying children with rsp-subtree option
        """
        query = ('/api/mo/uni/tn-common.json?query-target=children&'
                 'target-subtree-class=fvAEPg&rsp-subtree=children')
        fake_ret = self.session.get(query)
        data = fake_ret.json()['imdata']
        for epg in data:
            self.assertIn('fvAEPg', epg)

    def test_get_bad_class(self):
        """
        Test a get() class call to an unknown class
        """
        query = '/api/class/fvBadClass.json'
        fake_ret = self.session.get(query)
        self.assertEqual([], fake_ret.json()['imdata'])

    def test_socket(self):
        """
        Test a get() call for a websokcet connection
        """
        query = '/socket123456765476'
        fake_ret = self.session.get(query)
        data = fake_ret.json()['imdata']
        self.assertEqual(data, [{}])

    def test_login(self):
        """
        Test a login
        """
        login_url = '/api/aaaLogin.json'
        name_pwd = {'aaaUser': {'attributes': {'name': 'admin',
                                               'pwd': 'password'}}}
        resp = self.session.push_to_apic(login_url, data=json.dumps(name_pwd))
        self.assertTrue(resp.ok)
        self.assertIn('aaaLogin', resp.json()['imdata'][0])

        resp = self.session.login()
        self.assertTrue(resp.ok)

    def test_push_to_apic(self):
        """
        Test push_to_apic
        """
        login_url = '/api/mo/uni/tn-acitoolkit.json'
        data = {'fvTenant': {'attributes': {'name': 'acitookit'}}}
        resp = self.session.push_to_apic(login_url, data=json.dumps(data))
        self.assertTrue(resp.ok)

    def test_subscribe(self):
        """
        Test event subscriptions.
        Not implemented in FakeAPIC so checking very little functionality
        """
        url = '/api/class/fvTenant.json'
        self.session.subscribe(url)
        self.assertFalse(self.session.has_events(url))
        self.assertIsNone(self.session.get_event(url))
        self.session.unsubscribe(url)


if __name__ == '__main__':
    global filenames

    parser = argparse.ArgumentParser(description='Fake APIC test suite')
    parser.add_argument('--directory', default=None,
                        help='Directory containing the Snapshot files')
    args, unittest_args = parser.parse_known_args()

    # Set the directory to the location of the JSON files
    directory = args.directory
    filenames = [directory + filename for filename in listdir(directory)
                 if filename.endswith('.json')]

    # Run the tests
    fake = unittest.TestSuite()
    fake.addTest(unittest.makeSuite(TestFakeApic))
    unittest.main(defaultTest='fake', argv=sys.argv[:1] + unittest_args)
