"""
Snapback test suite
"""
from snapback import app
import unittest
import json
import requests
import datetime
import time


def setUpModule():
    now = datetime.datetime.now()
    global version_needed, filename_needed, filename_needed1
    version_needed = now.strftime("%Y-%m-%d_%H.%M.%S")
    filename_needed = "snapshot_172.31.216.100_10.json"
    filename_needed1 = "snapshot_172.31.216.100_11.json"


class Test01Login(unittest.TestCase):
    """
    test case for testing the login in JsonInterface
    with all the valid inputs
    and invalid inputs for frequency, username, password,ipaddr
    """
    def setUp(self):
        self.app = app.test_client()

    def test_invalid_username(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "ipaddr": "172.31.216.100",
            "secure": "",
            "username": "tester",
            "password": "ins3965!"}
        response = self.app.post('http://127.0.0.1:5000/login',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_invalid_password(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "ipaddr": "172.31.216.100",
            "secure": "",
            "username": "admin",
            "password": "12345%"
        }
        response = self.app.post('http://127.0.0.1:5000/login',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_invalid_ipaddr(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "ipaddr": "173.1.1.1",
            "secure": "",
            "username": "admin",
            "password": "12345%"
        }
        response = self.app.post('http://127.0.0.1:5000/login',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_Login(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "ipaddr": "172.31.216.100",
            "secure": None,
            "username": "admin",
            "password": "ins3965!"
        }
        data1 = json.dumps(dict(data))
        response = self.app.post('http://127.0.0.1:5000/login',
                                 headers=headers,
                                 data=data1)
        self.assertEquals(4, len(data))
        self.assertEquals(response.data, "loged in")
        self.assertEquals(response.status_code, 200)


class Test02ScheduleSnapshot(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "ipaddr": "172.31.216.100",
            "secure": None,
            "username": "admin",
            "password": "ins3965!"
        }
        data1 = json.dumps(dict(data))
        response_login = self.app.post('http://127.0.0.1:5000/login',
                                       headers=headers,
                                       data=data1)
        self.assertEquals(response_login.data, "loged in")
        self.assertEquals(response_login.status_code, 200)

    '''
    testcase for schedulesnapshot in JsonInterface
    for all the valid inputs for frequency ,date,starttime,number
    and asserting the status of respose
    '''

    def test_020isloggedin(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "frequency": "onetime",
            "date": "Jun 1 2005",
            "starttime": "1:33PM",
            "number": "", "interval": "minutes"
        }
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_021scheduleSnapshot(self):
        """
        test scheduleSnapshot
        """

        headers = {
            'Content-Type': 'application/json'
        }
        """
        data = {
            "ipaddr": "172.31.216.100",
            "secure": None,
            "username": "admin",
            "password": "ins3965!"
        }
        data1 = json.dumps(dict(data))
        response_login = self.app.post('http://127.0.0.1:5000/login',
                                 headers=headers,
                                 data=data1)
        self.assertEquals(response_login.data, "loged in")
        self.assertEquals(response_login.status_code, 200)
        """
        data_input = {
            "frequency": "onetime",
            "date": "Jun 1 2005",
            "starttime": "1:33PM",
            "number": None,
            "interval": "minutes"
        }
        data1 = json.dumps(dict(data_input))
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data1)
        self.assertGreaterEqual(5, len(data_input),
                                "should not be more than 5")
        time.sleep(50)
        self.assertEquals(response.data, "Snapshot successfully scheduled\n")
        self.assertEqual(response.status_code, 200)

    def test_022scheduleSnapshot_for_frequency(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data1 = json.dumps(dict({"frequency": "",
                                 "date": "Jun 1 2005",
                                 "starttime": "1:33PM",
                                 "number": "",
                                 "interval": "minutes"
                                 }))
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data1)
        self.assertEqual(response.status_code, 200)

    def test_023scheduleSnapshot_for_interval(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "frequency": "onetime",
            "date": "Jun 1 2005",
            "starttime": "1:33PM",
            "number": "",
            "interval": "xxx"
        }
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_024scheduleSnapshot_for_date(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "frequency": "onetime",
            "date": "Jun 1",
            "starttime": "1:33PM",
            "number": "",
            "interval": "minutes"
        }
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot', headers=headers, data=data)
        self.assertEqual(response.status_code, 400)

    def test_025scheduleSnapshot_for_starttime(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "frequency": "onetime",
            "date": "Jun 1 2005",
            "starttime": "1:",
            "number": "",
            "interval": "minutes"
        }
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data)
        self.assertLessEqual(len(data), 5, "should not be more than 5")
        self.assertEqual(response.status_code, 400)

    def test_026cancelSnapshot(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = json.dumps(dict(
            {"frequency": "onetime", "date": "Jun 1 2005", "starttime": "1:33PM", "number": "", "interval": "minutes"}))
        response = requests.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 200)
        response = self.app.post('http://127.0.0.1:5000/cancelschedule')
        self.assertEqual(response.status_code, 200)


class Test04FilterSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        now = datetime.datetime.now()
        version_needed = now.strftime("%Y-%m-%d_%H.%M.%S")

    def setUp(self):
        self.app = app.test_client()

    '''
        test for filtering using key version and match for equals, by default equals is considered true
    '''

    def test_filterVersionEquals(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "version": version_needed,
                        "match": "equals"}
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertEqual(snapshot['version'], version_needed, "both are not equal")

    '''
        test for filtering using key version and match for not equal, by default equals is considered true
    '''

    def test_filterVersionNotEqual(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "version": version_needed,
                        "match": "not equal"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertNotEqual(snapshot['version'], version_needed, "both are not equal")

    '''
        test for filtering using key version and match for contains, by default equals is considered true
    '''

    def test_filterVersionContains(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Version": [{
                    "version": version_needed,
                    "match": "contains"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertRegexpMatches(snapshot['version'], version_needed, "both are not equal")

    '''
        test for filtering using key version and match for not contains, by default equals is considered true
    '''

    def test_filterVersionNotContains(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "version": version_needed,
                        "match": "not contains"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertNotRegexpMatches(snapshot['version'], version_needed, "both are not equal")

    def test_filterVersionEmpty(self):
        headers = {
            'Content-Type': 'application/json',
        }
        '''
        test for filtering using key version and match for empty, by default empty is considered tru
        should return some snapshots
        '''
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "match": "empty"}
                ]}}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) == 0, "doesnot return empty")
        '''
        test for filtering using key version and match for empty true
        should return no snapshots
        '''
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "match": "empty",
                        "match_for": True}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) == 0, "doesnot return empty")
        '''
        test for filtering using key version and match for empty no
        should return all the snapshots
        '''
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "match": "empty",
                        "match_for": False}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) != 0, "returned no snapshots")

    '''
        test for filtering using key version and match for in list, by default equals is considered true,this takes multiple version comma seperated
    '''

    def test_filterVersionInList(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "version": [version_needed, "2016-04-11_14.11.11"],
                        "match": "in list"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        versions_expected = [version_needed, "2016-04-11_14.11.11"]
        for snapshot in result['snapshots']:
            self.assert_((snapshot['version'] in versions_expected), "snapshot with different version is filtered")

    '''
        test for filtering using key version and match for not in list, by default equals is considered true,this takes multiple version comma seperated
    '''

    def test_filterVersionNotInList(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "version": [version_needed, "2016-04-11_14.11.11"],
                        "match": "not in list"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        versions_expected = [version_needed, "2016-04-11_14.11.11"]
        for snapshot in result['snapshots']:
            self.assert_((snapshot['version'] not in versions_expected), "snapshot with different version is filtered")

    '''
    tests for filename filter
    '''
    '''
        test for filtering using key Filename and match for equals, by default equals is considered true
    '''

    def test_filterFilenameEquals(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "filename": filename_needed,
                        "match": "equals"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertEqual(snapshot['filename'], filename_needed, "both are not equal")

    '''
        test for filtering using key Filename and match for not equal, by default equals is considered true
    '''

    def test_filterFilenameNotEqual(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "filename": filename_needed,
                        "match": "not equal"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertNotEquals(snapshot['filename'], filename_needed, "both are not equal")

    '''
        test for filtering using key Filename and match for contains, by default equals is considered true
    '''

    def test_filterFilenameContains(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "filename": "snapshot_172.31.216.100_10", "match": "contains"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertRegexpMatches(snapshot['filename'], 'snapshot_172.31.216.100_10', "both are not equal")

    '''
        test for filtering using key Filename and match for not contains, by default equals is considered true
    '''

    def test_filterFilenameNotContains(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "filename": "snapshot_172.31.216.100_10",
                        "match": "not contains"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertNotRegexpMatches(snapshot['filename'], 'snapshot_172.31.216.100_10', "both are not equal")

    def test_filterFilenameEmpty(self):
        headers = {
            'Content-Type': 'application/json',
        }
        '''
        test for filtering using key Filename and match for empty, by default empty is considered true
        should return some snapshots
        '''
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {"match": "empty"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) == 0, "doesnot return empty")
        '''
        test for filtering using key Filename and match for empty true
        should return no snapshots
        '''
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "match": "empty",
                        "match_for": True
                    }
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) == 0, "doesnot return empty")
        '''
        test for filtering using key Filename and match for empty no
        should return all the snapshots
        '''
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "match": "empty",
                        "match_for": False}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) != 0, "returned no snapshots")

    '''
        test for filtering using key Filename and match for in list, by default equals is considered true,this takes multiple filename comma seperated
    '''

    def test_filterFilenameInList(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "filename": [
                            "snapshot_172.31.216.100_10", "snapshot_172.31.216.100_11"
                        ],
                        "match": "in list"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        versions_expected = ["snapshot_172.31.216.100_10", "snapshot_172.31.216.100_11"]
        for snapshot in result['snapshots']:
            self.assert_((snapshot['filename'] in versions_expected), "snapshot with different filename is filtered")

    '''
        test for filtering using key filename and match for not in list, by default equals is considered true,this takes multiple filename comma seperated
    '''

    def test_filterFilenameNotInList(self):
        headers = {
            'Content-Type': 'application/json',
        }
        data = json.dumps(dict({
            "filter": {
                "Filename": [
                    {
                        "filename": "snapshot_172.31.216.100_10,snapshot_172.31.216.100_11",
                        "match": "not in list"}
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        versions_expected = ["snapshot_172.31.216.100_10", "snapshot_172.31.216.100_11"]
        for snapshot in result['snapshots']:
            self.assert_((snapshot['filename'] not in versions_expected),
                         "snapshot with different filename is filtered")

    '''
    tests for latest
    '''

    def test_filterLatest(self):
        headers = {
            'Content-Type': 'application/json',
        }
        '''
        test for filtering using key latest and match for equals false and not equal false,as they are mutually exclusive result should be 0, by default equals is considered true
        '''
        data = json.dumps(dict({
            "filter": {
                "Latest": [
                    {
                        "match": "equals",
                        "match_for": False},
                    {
                        "match": "not equal",
                        "match_for": False
                    }
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) == 0, "snapshot with wrong latest is filtered")

        '''
        test for filtering using key latest and match for equals false, by default equals is considered true
        '''
        data = json.dumps(dict({
            "filter": {
                "Latest": [
                    {
                        "match": "equals",
                        "match_for": False
                    },
                    {
                        "match": "not equal",
                        "match_for": True
                    }
                ]
            }}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) == 0, "snapshot with wrong latest is filtered")

        data = json.dumps(dict({
            "filter": {
                "Latest": [
                    {
                        "match": "equals",
                        "match_for": True
                    },
                    {
                        "match": "not equal",
                        "match_for": False
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) != 0, "snapshot with wrong latest is filtered")

        data = json.dumps(dict({
            "filter": {
                "Latest": [
                    {
                        "match": "equals",
                        "match_for": True
                    },
                    {
                        "match": "not equal",
                        "match_for": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        self.assert_(len(result['snapshots']) == 0, "snapshot with wrong latest is filtered")

        data = json.dumps(dict({
            "filter": {
                "Latest": [
                    {
                        "match": "equals",
                        "match_for": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assert_((snapshot['latest']), "snapshot with different filename is filtered")

        data = json.dumps(dict({
            "filter": {
                "Latest": [
                    {
                        "match": "not equal",
                        "match_for": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assert_((not snapshot['latest']), "snapshot with different filename is filtered")

    def test_multipleFilters(self):
        """
        test for filtering using key latest and match for equals false,
            and key filename is snapshot_172.31.216.100_10.json and match_for equals,
            and key version is 2016-04-22_14.33.39 and match_for equals
        """
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "filter": {
                "Version": [
                    {
                        "version": version_needed,
                        "match": "equals"
                    }
                ],
                "Filename": [
                    {
                        "filename": filename_needed,
                        "match": "equals"
                    }
                ],
                "Latest": [
                    {
                        "match": "not equal",
                        "match_for": False
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        result = json.loads(response.data)
        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(result, "returned no data")
        for snapshot in result['snapshots']:
            self.assertEqual(snapshot['filename'], filename_needed, "both filenames are not equal")
            self.assertEqual(snapshot['version'], version_needed, "both versions are not equal")
            self.assertNotEqual(snapshot['latest'], False, "both are not equal")


class Test05Action(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        now = datetime.datetime.now()
        version_needed = now.strftime("%Y-%m-%d_%H.%M.%S")

    def setUp(self):
        self.app = app.test_client()

    def test_viewDiffWithNoFile(self):
        """
        test for view diffs of files
        """
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "View Diffs": []
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, "Please select at least one record", "given arguments did not match")

    def test_viewDiffWithOneFile(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "View Diffs": [
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, "Please select 2 snapshots to view diffs", "given arguments did not match")

    def test_viewDiffWithMultipleFiles(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "View Diffs": [
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    },
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    },
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, "Please select only 2 snapshots to view diffs",
                          "given arguments did not match")

    def test_viewDiffs(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "View Diffs": [
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    },
                    {
                        "filename": filename_needed1,
                        "version": version_needed,
                        "latest": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        if response.data != "":
            result = json.loads(response.data)
            print response.data
            self.assertEquals(response.status_code, 200)
            self.assertIsNotNone(result, "returned no data")

    def test_viewWithNoFile(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "View": []
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, "Please select at least one record", "given arguments did not match")

    def test_viewWithOneFile(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "View": [
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        if response.data != "":
            result = json.loads(response.data)
            self.assertEquals(response.status_code, 200)
            self.assertIsNotNone(result, "returned no data")

    def test_viewMultipleFiles(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "View": [
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    },
                    {
                        "filename": filename_needed1,
                        "version": version_needed,
                        "latest": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        if response.data != "":
            self.assertEquals(response.status_code, 200)
            self.assertIsNotNone(response.data, "returned no data")

    def test_deleteWithNoSnapshot(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({
            "action": {
                "Delete": []
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, "Please select at least one record.", "given arguments did not match")

    def test_deleteSnapshots(self):
        headers = {'Content-Type': 'application/json', }

        response = self.app.post('http://127.0.0.1:5000/viewsnapshots')
        data_returned = json.loads(response.data)
        no_of_snapshots = len(data_returned['snapshots'])

        data = json.dumps(dict({
            "action": {
                "Delete": [
                    {
                        "filename": filename_needed,
                        "version": version_needed,
                        "latest": True
                    }
                ]
            }
        }))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        data_returned = json.loads(response.data)
        no_of_snapshots_after_deletion = len(data_returned['snapshots'])
        self.assertEquals(response.status_code, 200)


class Test03Snapshot(unittest.TestCase):
    """
    testcase for viewsnapshots in JsonInterface
    checking if the snapshots are returned (viewsnapshots return some snapshots if there exists in configdb )
    and checking the status of response
    """

    def setUp(self):
        self.app = app.test_client()

    def test_snapshot(self):
        headers = {'Content-Type': 'application/json', }
        data = json.dumps(dict({"outputfile": "output1.txt"}))
        # data = json.dumps(dict({"action":{"View Diffs" :[{"filename":"snapshot_172.31.216.100_10.json","version":"2016-04-22_14.33.39","latest":True},{"filename":"snapshot_172.31.216.100_10.json","version":"2016-04-22_14.33.39","latest":True}]}}))
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        if response.data != "no snapshots":
            data_returned = json.loads(response.data)
            self.assertTrue(response.data is not None, "no snapshot is returned")
            self.assertEqual(response.status_code, 200)


def main_test():
    full = unittest.TestSuite()
    full.addTest(unittest.makeSuite(Test01Login))
    full.addTest(unittest.makeSuite(Test02ScheduleSnapshot))
    full.addTest(unittest.makeSuite(Test03Snapshot))
    full.addTest(unittest.makeSuite(Test04FilterSnapshot))
    full.addTest(unittest.makeSuite(Test05Action))
    unittest.main()


if __name__ == '__main__':
    main_test()
