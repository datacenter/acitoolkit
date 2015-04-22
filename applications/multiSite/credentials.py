################################################################################
#            _    ____ ___   __  __       _ _   _      ____  _ _               #
#           / \  / ___|_ _| |  \/  |_   _| | |_(_)    / ___|(_) |_ ___         #
#          / _ \| |    | |  | |\/| | | | | | __| |____\___ \| | __/ _ \        #
#         / ___ \ |___ | |  | |  | | |_| | | |_| |_____|__) | | ||  __/        #
#        /_/   \_\____|___| |_|  |_|\__,_|_|\__|_|    |____/|_|\__\___|        #
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

# Specify your action
action = {
    # when copy_json is True, json files related to the tenant or application
    # profile will be acquire from APIC and push to your github account.
    # when paste_json is True, json file on your github account will be pulled
    # and applied to your target APIC (to_apic).
    'copy_json': True,
    'paste_json': True
}

# Specify the source from: the APIC, the tenant name and application profile.
from_apic = {
    # Fill in with the APIC admin user id
    'LOGIN': 'admin',
    # Fill in with the APIC admin password
    'PASSWORD': 'password',
    # Fill in with the APIC IP address
    'URL': 'http://' + '1.2.3.4' + ':80/',
    # Tenant or application that to be copied
    'tenant': 'tenantA',
    'application': 'applicationA'
}

# Specify the destination: the APIC, the tenant name and application profile.
to_apic = {
    # Fill in with the APIC admin user id
    'LOGIN': 'admin',
    # Fill in with the APIC admin password
    'PASSWORD': 'password',
    # Fill in with the APIC IP address
    'URL': 'http://' + '1.2.3.4' + ':80/',
    # Tenant or application that to be copied
    'tenant': 'tenantB',
    'application': 'applicationB'
}

# Specify the github account where you want to store your configuration file.
github_info = {
    # The github account your json file stored to.
    'git_account': 'github_account',
    'git_pw': 'password',
    # File location in your git account
    'git_repo': 'repo_name',
    'git_file': 'file_name',
    # commit_message
    'commit_message': 'push json to github',
    # branch of repo:
    'branch': 'master'
}
