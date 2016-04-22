"""
Snapback test suite
"""
from snapback import app
import unittest
import json
import requests


class TestLogin(unittest.TestCase):
    '''
    test case for testing the login in JsonInterface
    with all the valid inputs
    and invalid inputs for frequency, username, password,ipaddr
    '''
    def setUp(self):
        self.app = app.test_client()

    def test_invalid_username(self):
        """
        test invalid username
        """
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "ipaddr": "172.31.216.100",
            "secure": "",
            "username": "tester",
            "password": "ins3965!"
        }
        response = self.app.post('http://127.0.0.1:5000/login',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_invalid_password(self):
        """
        test invalid password
        """
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
        """
        test invalid ipaddr
        """
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
        """
        test Login
        """
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
        self.assertEquals(response.status_code, 200)


class TestScheduleSnapshot(unittest.TestCase):
    """
    testcase for schedulesnapshot in JsonInterface
    for all the valid inputs for frequency ,date,starttime,number
    and asserting the status of respose
    """
    def setUp(self):
        self.app = app.test_client()

    def test_isloggedin(self):
        """
        test isloggedin
        """
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "frequency": "onetime",
            "date": "Jun 1 2005",
            "starttime": "1:33PM",
            "number": "",
            "interval": "minutes"
        }
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_scheduleSnapshot(self):
        """
        test scheduleSnapshot
        """
        headers = {
            'Content-Type': 'application/json'
        }
        data_input = {
            "frequency": "onetime",
            "date": "Jun 1 2005",
            "starttime": "1:33PM",
            "number": "",
            "interval": "minutes"
        }
        data1 = json.dumps(dict(data_input))
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data1)
        self.assertGreaterEqual(5, len(data_input),
                                "should not be more than 5")
        self.assertEqual(response.status_code, 200)

    def test_scheduleSnapshot_for_frequency(self):
        """
        test scheduleSnapshot for frequency
        """
        headers = {
            'Content-Type': 'application/json'
        }
        data1 = json.dumps(dict(
            {
                "frequency": "",
                "date": "Jun 1 2005",
                "starttime": "1:33PM",
                "number": "",
                "interval": "minutes"
            }
        ))
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data1)
        self.assertEqual(response.status_code, 200)

    def test_scheduleSnapshot_for_interval(self):
        """
        test scheduleSnapshot for interval
        """
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

    def test_scheduleSnapshot_for_date(self):
        """
        test scheduleSnapshot for date
        """
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
        response = self.app.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 400)

    def test_scheduleSnapshot_for_starttime(self):
        """
        test scheduleSnapshot for starttime
        """
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

    def test_cancelSnapshot(self):
        """
        test cancelSnapshot
        """
        headers = {
            'Content-Type': 'application/json'
        }
        data = json.dumps(dict(
            {
                "frequency": "onetime",
                "date": "Jun 1 2005",
                "starttime": "1:33PM",
                "number": "",
                "interval": "minutes"
            }
        ))
        response = requests.post('http://127.0.0.1:5000/schedulesnapshot',
                                 headers=headers,
                                 data=data)
        self.assertEqual(response.status_code, 200)
        response = self.app.post('http://127.0.0.1:5000/cancelschedule')
        self.assertEqual(response.status_code, 200)


class TestSnapshot(unittest.TestCase):
    """
    testcase for viewsnapshots in JsonInterface
    checking if the snapshots are returned
    (viewsnapshots return some snapshots if there exists in configdb )
    and checking the status of response
    """
    def setUp(self):
        self.app = app.test_client()

    def test_snapshot(self):
        """
        test snapshot
        """
        headers = {
            'Content-Type': 'application/json'
        }
        data = 'output.txt'
        response = self.app.post('http://127.0.0.1:5000/viewsnapshots',
                                 headers=headers,
                                 data=data)
        data_returned = json.loads(response.data)
        self.assertTrue(data_returned is not None, "no snapshot is returned")
        self.assertEqual(response.status_code, 200)


def main_test():
    """Main test routine"""
    full = unittest.TestSuite()
    full.addTest(unittest.makeSuite(TestLogin))
    full.addTest(unittest.makeSuite(TestScheduleSnapshot))
    full.addTest(unittest.makeSuite(TestSnapshot))

    unittest.main()


if __name__ == '__main__':
    main_test()
