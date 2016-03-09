"""
Test routines for aciconfigdb
"""
import unittest
import aciconfigdb
import credentials
import mock
import sys


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

    def clear_output(self):
        self.output = []


class TestBasicSnapshot(unittest.TestCase):
    """
    Basic snapshot testcases
    """
    def setUp(self):
        self.args = mock.Mock()
        self.args.list_snapshots = False
        self.args.url = credentials.URL
        self.args.login = credentials.LOGIN
        self.args.password = credentials.PASSWORD
        self.args.list_configfiles = None
        self.stdout = sys.stdout
        self.fake_out = FakeStdio()
        sys.stdout = self.fake_out

    def tearDown(self):
        sys.stdout = self.stdout

    def test_basic_list_snapshots(self):
        """
        Test the basic snapshot
        """
        # Set the arguments to just list the snapshot versions
        self.args.list_snapshots = True

        # Call the tool to list the snapshots
        aciconfigdb.main(self.args)

        # Check the output
        self.assertEquals(self.fake_out.output[0], 'Versions')
        self.assertEquals(self.fake_out.output[1], '\n')

    def test_basic_snapshot_v1(self):
        """
        Test the basic snapshot
        """
        # Call the tool to list the snapshots
        self.args.list_snapshots = True
        aciconfigdb.main(self.args)

        # Get the number of snapshots
        num_versions = len(self.fake_out.output)

        # Take the snapshot
        self.args.list_snapshots = False
        aciconfigdb.main(self.args)
        self.fake_out.clear_output()

        # Call the tool to list the snapshots
        self.args.list_snapshots = True
        aciconfigdb.main(self.args)

        # Get the number of snapshots
        num_new_versions = len(self.fake_out.output)
        self.assertEquals(num_versions + 2, num_new_versions)

    def test_basic_snapshot_with_export_policy(self):
        """
        Test the basic snapshot
        """
        # Call the tool to list the snapshots
        self.args.list_snapshots = True
        aciconfigdb.main(self.args)

        # Get the number of snapshots
        num_versions = len(self.fake_out.output)

        # Take the snapshot
        self.args.list_snapshots = False
        self.args.v1 = False
        aciconfigdb.main(self.args)
        self.fake_out.clear_output()

        # Call the tool to list the snapshots
        self.args.list_snapshots = True
        aciconfigdb.main(self.args)

        # Get the number of snapshots
        num_new_versions = len(self.fake_out.output)
        self.assertEquals(num_versions + 2, num_new_versions)


if __name__ == '__main__':

    full_suite = unittest.TestSuite()
    full_suite.addTest(unittest.makeSuite(TestBasicSnapshot))

    unittest.main()
