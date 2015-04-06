################################################################################
#                  _    ____ ___    ____             __ _                      #
#                 / \  / ___|_ _|  / ___|___  _ __  / _(_) __ _                #
#                / _ \| |    | |  | |   / _ \| '_ \| |_| |/ _` |               #
#               / ___ \ |___ | |  | |__| (_) | | | |  _| | (_| |               #
#              /_/  _\_\____|___|_ \____\___/|_| |_|_| |_|\__, |               #
#                  |  _ \ ___ | | | |__   __ _  ___| | __ |___/                #
#                  | |_) / _ \| | | '_ \ / _` |/ __| |/ /                      #
#                  |  _ < (_) | | | |_) | (_| | (__|   <                       #
#                  |_| \_\___/|_|_|_.__/ \__,_|\___|_|\_\                      #
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
import os
import git
import acitoolkit.acitoolkit as ACI
import time
import json


class ConfigDB(object):
    def __init__(self, args):
        # Login to the APIC
        self.session = ACI.Session(args.url, args.login, args.password)
        resp = self.session.login()
        if not resp.ok:
            print '%% Could not login to APIC'

        # Create the Git repository
        repo_parent_dir = os.getcwd()
        self.repo_dir = os.path.join(repo_parent_dir, 'apic-config-db')
        self.repo = git.Repo.init(self.repo_dir)

    def _get_from_apic(self, url):
        ret = self.session.get(url)
        data = ret.json()['imdata'][0]
        return data

    def _snapshot(self, query_url, file_name):
        file_name = os.path.join(self.repo_dir, file_name)
        data = self._get_from_apic(query_url)

        # Write the config to a file
        f = open(file_name, 'w')
        f.write(json.dumps(data, indent=4, separators=(',', ':')))
        f.close()

        # Add the file to Git
        self.repo.index.add([file_name])

    def _get_url_for_file(self, filename):
        if filename.startswith('tenant-'):
            tenant_name = filename.split('tenant-')[1].split('.json')[0]
            url = ('/api/mo/uni/tn-%s.json?rsp-subtree=full&'
                   'rsp-prop-include=config-only' % tenant_name)
        elif filename == 'infra.json':
            url = ('/api/mo/uni/infra.json?rsp-subtree=full&'
                   'rsp-prop-include=config-only')
        elif filename == 'fabric.json':
            url = ('/api/mo/uni/fabric.json?rsp-subtree=full&'
                   'rsp-prop-include=config-only')
        return url

    def take_snapshot(self):
        tag_name = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())

        # Save each tenants config
        tenants = ACI.Tenant.get(self.session)
        for tenant in tenants:
            filename = 'tenant-%s.json' % tenant.name
            url = self._get_url_for_file(filename)
            self._snapshot(url, filename)

        # Save the Infra config
        filename = 'infra.json'
        url = self._get_url_for_file(filename)
        self._snapshot(url, filename)

        # Save the Fabric config
        filename = 'fabric.json'
        url = self._get_url_for_file(filename)
        self._snapshot(url, filename)

        # Commit the files and tag with the timestamp
        self.repo.index.commit(tag_name)
        self.repo.git.tag(tag_name)

    def get_versions(self):
        versions = str(self.repo.git.tag())
        return versions.split('\n')

    def get_filenames(self, version):
        filenames = str(self.repo.git.ls_files())
        return filenames.split('\n')

    def _print(self, title, items):
        underline = 0
        for item in items:
            if len(item) > underline:
                underline = len(item)
        print title
        print '=' * underline
        for item in items:
            print item

    def print_versions(self):
        title = 'Versions'
        versions = self.get_versions()
        self._print(title, versions)

    def print_filenames(self, version):
        title = 'Filenames'
        filenames = self.get_filenames(version)
        self._print(title, filenames)

    def ordered(self, obj):
        if isinstance(obj, dict):
            return {k: self.ordered(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return sorted(self.ordered(x) for x in obj)
        else:
            return obj

    def mark_mismatching(self, current, old):
        for key in current.keys():
            if key not in old:
                current[key]['attributes']['status'] = 'deleted'
                continue
            if current[key] == old[key]:
                continue
            if current[key]['attributes'] == old[key]['attributes']:
                # check if no children
                if 'children' not in current[key]:
                    continue

                # check if children only in the current config
                if 'children' not in old[key]:
                    for child in range(0, len(current[key]['children'])):
                        current[key]['attributes']['status'] = 'deleted'
                    continue

                # find extra children and mark deleted
                num_old_children = len(old[key]['children'])
                num_curr_children = len(current[key]['children'])
                if num_old_children != num_curr_children:
                    old_child_idx = 0
                    for child_idx in range(0, num_curr_children):
                        if (old_child_idx < num_old_children and
                            current[key]['children'][child_idx] == old[key]['children'][old_child_idx]):
                            old_child_idx = old_child_idx + 1
                        else:
                            child_key = current[key]['children'][child_idx].keys()[0]
                            print 'marked as deleted michsmit'
                            print key, child_idx, child_key
                            print current[key]['children'][child_idx][child_key]['attributes']['name']
                            current[key]['children'][child_idx][child_key]['attributes']['status'] = 'deleted'

                old_child_idx = 0
                for child in range(0, len(current[key]['children'])):
                    child_key = current[key]['children'][child].keys()[0]
                    current_attributes = current[key]['children'][child][child_key]['attributes']
                    if 'status' in current_attributes and current_attributes['status'] == 'deleted':
                        continue
                    # skip deleted children but contine with the old using lower index
                    self.mark_mismatching(current[key]['children'][child],
                                          old[key]['children'][old_child_idx])
                    old_child_idx = old_child_idx + 1
            else:
                current[key]['attributes']['status'] = 'deleted'

    def check_versions(self, filename, current_version, old_version):
        current_version = self.ordered(current_version)
        old_version = self.ordered(old_version)

        if current_version == old_version:
            return True
        else:
            self.mark_mismatching(current_version, old_version)
            # Push it to the APIC
            url = self._get_url_for_file(filename)
            self.session.push_to_apic(url, current_version)
            return False

    def rollback(self, version, filenames=None):
        if version not in self.get_versions():
            raise ValueError('Version not found')

        assert not isinstance(filenames, str)

        # If no filename given, assume all
        if filenames is None:
            filenames = self.get_filenames(version)

        for filename in filenames:
            # Get the rollback version from the repo
            old_version = self.repo.git.show(version + ':' + filename)
            old_version = json.loads(old_version)

            # Push it to the APIC
            url = self._get_url_for_file(filename)
            self.session.push_to_apic(url, old_version)
            print 'Pushing....'
            print old_version

            # Get the current version
            current_version = self._get_from_apic(url)

            # Look for any remaining differences
            # If differences exist, it is new config and will be removed.
            self.check_versions(filename, current_version, old_version)


if __name__ == "__main__":
    # Get all the arguments
    description = 'Configuration Snapshot and Rollback tool for APIC.'
    creds = ACI.Credentials('apic', description)
    commands = creds.add_mutually_exclusive_group()
    commands.add_argument('-s', '--snapshot', action='store_true',
                          help='Take a snapshot of the APIC configuration')
    commands.add_argument('-ls', '--list-snapshots', action='store_true',
                          help='List all of the available snapshots')
    help_txt = 'List all of the available configuration files.'
    commands.add_argument('-lc', '--list-configfiles', action='store_true',
                          help=help_txt)
    help_txt = ('Rollback the configuration to the specified version.'
                ' Optionally only for certain configuration files.')
    commands.add_argument('--rollback', nargs='+',
                          metavar=('VERSION', 'CONFIGFILE'),
                          help=help_txt)
    help_txt = ('Show the contents of a particular configfile'
                ' from a particular snaphot version.')
    commands.add_argument('--show', nargs=2,
                          metavar=('VERSION', 'CONFIGFILE'),
                          help=help_txt)
    args = creds.get()

    cdb = ConfigDB(args)
    if args.list_configfiles:
        versions = cdb.get_versions()
        cdb.print_filenames(versions[-1])
    elif args.list_snapshots:
        cdb.print_versions()
    elif args.snapshot:
        cdb.take_snapshot()
    elif args.rollback is not None:
        version = args.rollback[0]
        print 'version:', version
        filenames = args.rollback[1:]
        if len(filenames) == 0:
            latest_version = cdb.get_versions()[-1]
            filenames = cdb.get_filenames(latest_version)
        cdb.rollback(version, filenames)
    elif args.show is not None:
        version = args.show[0]
        filename = args.show[1]
        config = cdb.repo.git.show(version + ':' + filename)
        print config
