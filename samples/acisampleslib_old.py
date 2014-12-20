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
command line, the credentials are taken from the file credentials.py.
"""
import sys
import getopt


def get_login_info(argv):
    usage = ('Usage: %s -l <login> -p <password> -u <url>\n'
             'Any option not provided will be imported from '
             'credentials.py') % argv[0]

    try:
        from credentials import PASSWORD, LOGIN, URL
    except ImportError:
        PASSWORD = ''
        LOGIN = ''
        URL = ''

    try:
        opts, args = getopt.getopt(argv[1:],
                                   "hl:p:u:",
                                   ["help", "login=", "password=",
                                    "url="])
    except getopt.GetoptError:
        print argv[0], ': illegal option'
        print usage
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print usage
            sys.exit()
        elif opt in ('-l', '--apic-login'):
            LOGIN = arg
        elif opt in ('-p', '--apic-password'):
            PASSWORD = arg
        elif opt in ('-u', '--apic-url'):
            URL = arg
    return (LOGIN, PASSWORD, URL)
