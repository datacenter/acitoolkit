# Copyright (c) 2014 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
"""
Function used by samples to get the APIC login credentials from the command
line (--help gives usage).  If login credentials are not provided on the
command line, the bash environment variables are taken from the file ~/.profile.
"""
import argparse
import os
import sys

class Credentials(object):
    def __init__(self, qualifier='apic', description=''):
        def set_default(key):
            if 'APIC_' + key.upper() in os.environ.keys():
                return os.environ['APIC_'+key.upper()]
            else:
                try:
                    import credentials
                except ImportError:
                    print 'credentials.py does not exist.'
                    return ''
                try:
                    default = credentials.__getattribute__(key.upper())
                    return default
                except AttributeError:
                    return ''

        if isinstance(qualifier, str):
            qualifier = (qualifier)
        self._qualifier = qualifier
        self._parser = argparse.ArgumentParser(description=description)
        if 'apic' in qualifier:
            DEFAULT_URL = set_default('url')
            DEFAULT_LOGIN = set_default('login')
            DEFAULT_PASSWORD = set_default('password')
            self._parser.add_argument('-u', '--url', default=DEFAULT_URL, help='APIC IP address.')
            self._parser.add_argument('-l', '--login', default=DEFAULT_LOGIN, help='APIC login ID.')
            self._parser.add_argument('-p', '--password', default=DEFAULT_PASSWORD, help='APIC login password.')
        if 'mysql' in qualifier:
            DEFAULT_MYSQL_IP = set_default('mysqlip')
            DEFAULT_MYSQL_LOGIN = set_default('mysqllogin')
            DEFAULT_MYSQL_PASSWORD = set_default('mysqlpassword')
            self._parser.add_argument('-i', '--mysqlip', default=DEFAULT_MYSQL_IP, help='MySQL IP address.')
            self._parser.add_argument('-a', '--mysqllogin', default=DEFAULT_MYSQL_LOGIN, help='MySQL login ID.')
            self._parser.add_argument('-s', '--mysqlpassword', default=DEFAULT_MYSQL_PASSWORD, help='MySQL login password.')

    def get(self):
        self._args = self._parser.parse_args()
        self.verify()
        return self._args

    def add_argument(self, *args, **kwargs):
        self._parser.add_argument(*args, **kwargs)

    def verify(self):
        def error_msg(msg):
            print '%s has not been provided (try --help for options)' % msg
            sys.exit()
        if 'apic' in self._qualifier:
            if self._args.login == '':
                error_msg('APIC LOGIN')
            if self._args.url == '':
                error_msg('APIC URL')
        if 'mysql' in self._qualifier:
            if self._args.mysqlip == '':
                error_msg('MYSQL IP')
            if self._args.mysqllogin == '':
                error_msg('MYSQL LOGIN')
