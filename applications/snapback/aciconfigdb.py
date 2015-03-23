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
"""  Snapback: Configuration Snapshot and Rollback for ACI fabrics

     This file contains the main engine for the Snapback tool that handles
     taking the actual configuration snapshots and performing the rollback
"""
import os
import git
import acitoolkit.acitoolkit as ACI
import time
import json
import threading
import datetime
import sys
from requests import Timeout, ConnectionError


class SnapshotScheduler(threading.Thread):
    """
    Scheduler thread responsible for ongoing snapshots
    """
    def __init__(self, cdb):
        threading.Thread.__init__(self)
        self._schedule = None
        self._exit = False
        self._cdb = cdb
        self._next_snapshot_time = None

    def set_schedule(self, frequency='onetime', interval=None,
                     granularity='days', start_date=None,
                     start_time=None, callback=None):
        """
        Set the scheduler interval
        """
        print 'Set schedule'
        self._schedule = {}
        self._schedule['frequency'] = frequency
        self._schedule['interval'] = interval
        self._schedule['granularity'] = granularity
        self._schedule['start_date'] = start_date
        self._schedule['start_time'] = start_time
        self._callback = callback
        start = datetime.datetime(start_date.year, start_date.month, start_date.day,
                                  start_time.hour, start_time.minute)
        self._next_snapshot_time = start

    def get_current_schedule(self):
        """
        Return the current schedule settings
        """
        return self._schedule

    def get_next_snapshot_time(self):
        if self._next_snapshot_time:
            return self._next_snapshot_time.strftime('%Y-%m-%d %H:%M')
        else:
            return None

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._schedule = {}
        self._next_snapshot_time = None
        self._exit = True

    def run(self):
        assert 'start_date' in self._schedule
        assert 'start_time' in self._schedule
        sdate = self._schedule['start_date']
        stime = self._schedule['start_time']
        start = datetime.datetime(sdate.year, sdate.month, sdate.day,
                                  stime.hour, stime.minute)
        while not self._exit:
            cur_time = datetime.datetime.now()
            if start < cur_time:
                print 'Taking snapshot'
                self._cdb.take_snapshot(self._callback)
                if self._schedule['frequency'] == 'onetime':
                    self.exit()
                else:
                    seconds = self._schedule['interval']
                    granularity = self._schedule['granularity']
                    seconds = seconds * 60
                    if granularity == 'hours' or granularity == 'days':
                        seconds = seconds * 60
                    if granularity == 'days':
                        seconds = seconds * 24
                    addnl_days = 0
                    addnl_hours = 0
                    addnl_minutes = 0
                    if granularity == 'minutes':
                        addnl_minutes = self._schedule['interval']
                        if addnl_minutes / 60:
                            addnl_hours = addnl_hours + (addnl_minutes / 60)
                            addnl_minutes = addnl_minutes % 60
                    if granularity == 'hours':
                        addnl_hours = self._schedule['interval']
                        if addnl_hours / 24:
                            addnl_days = addnl_days + (addnl_hours / 24)
                            addnl_hours = addnl_hours % 24
                    if granularity == 'days':
                        addnl_days = self._schedule['interval']
                    next_snapshot = datetime.datetime(cur_time.year,
                                                      cur_time.month,
                                                      cur_time.day + addnl_days,
                                                      cur_time.hour + addnl_hours,
                                                      cur_time.minute + addnl_minutes)
                    self._next_snapshot_time = next_snapshot
                    print 'Next snapshot in', self._next_snapshot_time
                    time.sleep(seconds)
            else:
                delta = datetime.datetime.now() - start
                seconds = delta.seconds + delta.days * (24*60*60)
                self._next_snapshot_time = start
                time.sleep(seconds)


class ConfigDB(object):
    def __init__(self):
        self.session = None
        # Create the Git repository
        repo_parent_dir = os.getcwd()
        self.repo_dir = os.path.join(repo_parent_dir, 'apic-config-db')
        self.repo = git.Repo.init(self.repo_dir)
        self._snapshot_scheduler = None

    def login(self, args):
        # Login to the APIC
        self.session = ACI.Session(args.url, args.login, args.password)

        resp = self.session.login(timeout=2)
        return resp

    def is_logged_in(self):
        return self.session is not None

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

    def take_snapshot(self, callback=None):
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

        if callback:
            callback()

    def get_current_schedule(self):
        if self._snapshot_scheduler:
            return self._snapshot_scheduler.get_current_schedule()
        else:
            return None

    def schedule_snapshot(self, frequency='onetime', interval=None, interval_granularity='days',
                          start_date=None, start_time=None, callback=None):
        if self._snapshot_scheduler is not None:
            self.cancel_schedule()
        self._snapshot_scheduler = SnapshotScheduler(self)
        self._snapshot_scheduler.daemon = True
        self._snapshot_scheduler.set_schedule(frequency, interval, interval_granularity,
                                              start_date, start_time, callback)
        self._snapshot_scheduler.start()

    def cancel_schedule(self):
        if self._snapshot_scheduler:
            self._snapshot_scheduler.exit()

    def get_latest_file_version(self, filename):
        versions = str(self.repo.git.show('--tags', '--name-only', '--oneline', filename))
        versions = versions.split('\n')
        assert len(versions) >= 2
        latest_version = versions[-2]
        assert ' ' in latest_version
        latest_version = latest_version.split(' ')
        assert len(versions) >= 2
        return latest_version[1]

    def get_versions(self, with_changes=False):
        if not with_changes:
            versions = str(self.repo.git.tag())
            if len(versions) == 0:
                # No snapshots exist
                no_versions = []
                return no_versions
            return versions.split('\n')
        else:
            resp = []
            versions = self.repo.git.tag()
            if len(versions) == 0:
                # No snapshots exist
                no_versions = []
                return no_versions
            versions = str(versions).split('\n')
            previous_version = None
            for version in versions:
                additions = '0'
                deletions = '0'
                if previous_version is not None:
                    changes = str(self.repo.git.diff('--shortstat',
                                                     previous_version,
                                                     version))
                else:
                    changes = str(self.repo.git.show('--shortstat',
                                                     '--oneline',
                                                     version))
                if 'insertions' in changes:
                    additions = changes.split(' insertions')[0].split(' ')[-1]
                if 'deletions' in changes:
                    deletions = changes.split(' deletions')[0].split(' ')[-1]
                resp.append((version, additions, deletions))
                previous_version = version
            return resp

    def get_filenames(self, version,
                      prev_version=None, with_changes=False):
        filenames = str(self.repo.git.show('--name-only', '--oneline', version))
        filenames = filenames.split('\n')[1:]
        if with_changes is False:
            return filenames
        resp = []
        for filename in filenames:
            additions = '0'
            deletions = '0'
            if prev_version is not None:
                try:
                    changes = str(self.repo.git.diff('--shortstat',
                                                     prev_version + ':' + filename,
                                                     version + ':' + filename))
                except git.exc.GitCommandError:
                    changes = ''
                if 'insertions' in changes:
                    additions = changes.split(' insertions')[0].split(' ')[-1]
                if 'deletions' in changes:
                    deletions = changes.split(' deletions')[0].split(' ')[-1]
            else:
                try:
                    content = self.repo.git.show('--shortstat',
                                                 '--oneline',
                                                 version + ':' + filename)
                    num_lines = len(str(content).split('\n')) - 1
                    additions = str(num_lines)
                except git.exc.GitCommandError:
                    pass
            resp.append((filename, additions, deletions))
        return resp

    def get_file(self, filename, version):
        return self.repo.git.show(version + ':' + filename)

    def get_next_snapshot_time(self):
        if self._snapshot_scheduler:
            return self._snapshot_scheduler.get_next_snapshot_time()
        else:
            return None

    def get_latest_snapshot_time(self):
        if len(self.get_versions()) == 0:
            return None
        latest_tag = self.repo.git.describe('--abbrev=0', '--tags')
        if latest_tag is None:
            return None
        (latest_date, latest_time) = latest_tag.split('_')
        year, month, day = latest_date.split('-')
        hour, minute, msec = latest_time.split('.')
        latest_snapshot = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
        return latest_snapshot

    def _print(self, title, items):
        underline = 0
        assert items is not None
        if len(items):
            for item in items:
                if len(item) > underline:
                    underline = len(item)
        else:
            underline = len(title)
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
                            current[key]['children'][child_idx][child_key]['attributes']['status'] = 'deleted'

                old_child_idx = 0
                for child in range(0, len(current[key]['children'])):
                    child_key = current[key]['children'][child].keys()[0]
                    current_attributes = current[key]['children'][child][child_key]['attributes']
                    if ('status' in current_attributes and
                        current_attributes['status'] == 'deleted'):
                        continue
                    # skip deleted children but contine with the old
                    # using lower index
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
            old_version = self.get_file(filename, version)
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

    def sdiff(self, version1, version2, filename):
        resp = self.repo.git.difftool('-y',
                                      version1 + ':' + filename,
                                      version2 + ':' + filename)

    def has_diffs(self, version1, version2, filename):
        resp = self.repo.git.diff(version1 + ':' + filename,
                                  version2 + ':' + filename)
        if len(resp):
            return True
        else:
            return False


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
    commands.add_argument('-lc', '--list-configfiles', nargs='*',
                          metavar=('VERSION'),
                          default=None,
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

    cdb = ConfigDB()
    try:
        resp = cdb.login(args)
        if not resp.ok:
            print '%% Could not login to APIC'
            sys.exit(0)
    except (Timeout, ConnectionError):
        print '%% Could not login to APIC'
        sys.exit(0)
    if args.list_configfiles is not None:
        if len(args.list_configfiles):
            version = args.list_configfiles[0]
            cdb.print_filenames(version)
        else:
            versions = cdb.get_versions()
            if len(versions):
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
            filenames = cdb.get_filenames(version)
        cdb.rollback(version, filenames)
    elif args.show is not None:
        version = args.show[0]
        filename = args.show[1]
        config = cdb.get_file(version, filename)
        print config
