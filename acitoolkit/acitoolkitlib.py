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
"""
Used to get the APIC and MySQL login credentials from the command
line (--help gives usage).

The login credentials are taken in the following order

* Command line arguments
* Environment variables
* File named credentials.py
* From an interactive prompt

These are done in a per credential basis so it is possible to specify only
some of the arguments.  For instance, the username and URL can be specified
in credentials.py but the password can be taken from the user through the
interactive prompt.  Another example is using the command line argument to
override the URL specified in credentials.py to temporarily connect to a
different APIC.
"""
import argparse
import os
import sys
import getpass


class Credentials(object):
    """
    Main class to derive the credentials from the user
    """
    def __init__(self, qualifier='apic', description=''):
        def set_default(key):
            """
            Check for the following:
             - environmental variables
             - credentials.py file
            """
            if 'APIC_' + key.upper() in os.environ.keys():
                return os.environ['APIC_' + key.upper()]
            else:
                try:
                    import credentials
                except ImportError:
                    return None
                try:
                    default = credentials.__getattribute__(key.upper())
                    return default
                except AttributeError:
                    return None

        if isinstance(qualifier, str):
            qualifier = (qualifier)
        self._qualifier = qualifier
        self._args = None
        self._parser = argparse.ArgumentParser(description=description)
        if 'apic' in qualifier:
            DEFAULT_URL = set_default('url')
            DEFAULT_LOGIN = set_default('login')
            DEFAULT_PASSWORD = set_default('password')
            self._parser.add_argument('-u', '--url',
                                      default=DEFAULT_URL,
                                      help='APIC IP address.')
            self._parser.add_argument('-l', '--login',
                                      default=DEFAULT_LOGIN,
                                      help='APIC login ID.')
            self._parser.add_argument('-p', '--password',
                                      default=DEFAULT_PASSWORD,
                                      help='APIC login password.')
            self._parser.add_argument('--snapshotfiles', nargs='+',
                                      help='APIC configuration files')
        if 'mysql' in qualifier:
            DEFAULT_MYSQL_IP = set_default('mysqlip')
            DEFAULT_MYSQL_LOGIN = set_default('mysqllogin')
            DEFAULT_MYSQL_PASSWORD = set_default('mysqlpassword')
            self._parser.add_argument('-i', '--mysqlip',
                                      default=DEFAULT_MYSQL_IP,
                                      help='MySQL IP address.')
            self._parser.add_argument('-a', '--mysqllogin',
                                      default=DEFAULT_MYSQL_LOGIN,
                                      help='MySQL login ID.')
            self._parser.add_argument('-s', '--mysqlpassword',
                                      default=DEFAULT_MYSQL_PASSWORD,
                                      help='MySQL login password.')
        if 'server' in qualifier:
            DEFAULT_PORT = '5000'
            DEFAULT_IPADDRESS = '127.0.0.1'
            self._parser.add_argument('--ip',
                                      default=DEFAULT_IPADDRESS,
                                      help='IP address to listen on.')
            self._parser.add_argument('--port',
                                      default=DEFAULT_PORT,
                                      help='Port number to listen on.')
            self._parser.add_argument('--test',
                                      action='store_true', default=False,
                                      help='Enable functions for lab testing.')

    @staticmethod
    def _get_from_user(prompt):
        """
        Get the input from the user through interactive prompt.
        Use raw_input or input based on the Python version.
        """
        try:
            resp = raw_input(prompt)
        except NameError:
            resp = input(prompt)
        return resp

    @staticmethod
    def _get_password(prompt):
        """
        Get the password from the user through interactive prompt.
        Using this will ensure that the password is not displayed as
        it is typed.
        """
        return getpass.getpass(prompt)

    def get(self):
        """
        Get the arguments and verify them
        """
        self._args = self._parser.parse_args()
        self.verify()
        return self._args

    def add_argument(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        self._parser.add_argument(*args, **kwargs)

    def add_mutually_exclusive_group(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        return self._parser.add_mutually_exclusive_group(*args, **kwargs)

    def add_argument_group(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        return self._parser.add_argument_group(*args, **kwargs)

    def print_help(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        return self._parser.print_help(*args, **kwargs)

    def verify(self):
        """
        Verify that the arguments have been passed in some way.  If not,
        ask the user through interactive prompt.
        """
        if 'apic' in self._qualifier and self._args.snapshotfiles is None:
            if self._args.login is None:
                self._args.login = self._get_from_user('APIC login username: ')
            if self._args.url is None:
                self._args.url = self._get_from_user('APIC URL: ')
            if self._args.password is None:
                self._args.password = self._get_password('APIC Password: ')
        if 'mysql' in self._qualifier:
            if self._args.mysqlip is None:
                self._args.mysqlip = self._get_from_user('MySQL IP address: ')
            if self._args.mysqllogin is None:
                prompt = 'MySQL login username: '
                self._args.mysqllogin = self._get_from_user(prompt)
            if self._args.mysqlpassword is None:
                prompt = 'MySQL Password: '
                self._args.mysqlpassword = self._get_password(prompt)
