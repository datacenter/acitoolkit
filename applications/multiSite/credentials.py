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

# Fill in with the APIC admin userid
LOGIN = 'admin'
# Fill in with the APIC admin password
PASSWORD = 'ins3965!'
# Fill in with the APIC IP address
IPADDR = '172.31.216.100'
URL = 'http://' + IPADDR + ':80/'

# The github account your json file stored to.
git_account = 'yellowbang'
git_pw = '87421github'
# File location in your git account
git_repo = 'PyGithubTest'
git_file = 'textFile.txt'

# Tenant that to be copied
old_tenant = 'bonA'
old_application = '3Tier'

# The new tenant
new_tenant = 'bonB'
new_application = '3TierCopy'
