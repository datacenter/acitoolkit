################################################################################
#                                  _    ____ ___                               #
#                                 / \  / ___|_ _|                              #
#                                / _ \| |    | |                               #
#                               / ___ \ |___ | |                               #
#                         _____/_/   \_\____|___|_ _                           #
#                        |_   _|__   ___ | | | _(_) |_                         #
#                          | |/ _ \ / _ \| | |/ / | __|                        #
#                          | | (_) | (_) | |   <| | |_                         #
#                          |_|\___/ \___/|_|_|\_\_|\__|                        #
#                                                                              #
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""acitoolkitlib.py Test module
"""
from acitoolkit.acitoolkitlib import Credentials
import unittest


class TestCredentials(unittest.TestCase):
    """
    Test Credentials class from acitoolkitlib.py
    """
    def test_create_all(self):
        """
        Basic test for all Credentials qualifiers
        """
        creds = Credentials(['apic', 'mysql'])

        def return_empty_string(disp):
            """ Return an empty string """
            return ''

        creds._get_from_user = return_empty_string
        creds._get_password = return_empty_string
        self.assertTrue(isinstance(creds, Credentials))
        creds.get()
        creds.verify()

    def test_create_apic_string_only(self):
        """
        Basic test for only APIC Credentials qualifiers
        passed as a single string
        """
        creds = Credentials('apic')
        self.assertTrue(isinstance(creds, Credentials))

    def test_create_apic_list_only(self):
        """
        Basic test for only APIC Credentials qualifiers
        passed as a single string in a list
        """
        creds = Credentials(['apic'])
        self.assertTrue(isinstance(creds, Credentials))

if __name__ == '__main__':

    offline = unittest.TestSuite()
    offline.addTest(unittest.makeSuite(TestCredentials))

    unittest.main()
