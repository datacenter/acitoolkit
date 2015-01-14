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


def set_default(key):
    if 'APIC_'+key.upper() in os.environ.keys():
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


DEFAULT_URL = set_default('apicurl')
DEFAULT_LOGIN = set_default('apiclogin')
DEFAULT_PASSWORD = set_default('apicpassword')
DEFAULT_MYSQL_IP = set_default('mysqlip')
DEFAULT_MYSQL_LOGIN = set_default('mysqllogin')
DEFAULT_MYSQL_PASSWORD = set_default('mysqlpassword')

def get_login_info(description='No description'):

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-u', '--apicurl', default=DEFAULT_URL, help='APIC IP address.')
    parser.add_argument('-l', '--apiclogin', default=DEFAULT_LOGIN, help='APIC login ID.')
    parser.add_argument('-p', '--apicpassword', default=DEFAULT_PASSWORD, help='APIC login password.')
    parser.add_argument('-i', '--mysqlip', default=DEFAULT_MYSQL_IP, help='MySQL IP address.')
    parser.add_argument('-a', '--mysqllogin', default=DEFAULT_MYSQL_LOGIN, help='MySQL login ID.')
    parser.add_argument('-s', '--mysqlpassword', default=DEFAULT_MYSQL_PASSWORD, help='MySQL login password.')

    return parser

