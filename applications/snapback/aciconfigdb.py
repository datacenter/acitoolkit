################################################################################
#         _    ____ ___    ____                    _                _          #
#        / \  / ___|_ _|  / ___| _ __   __ _ _ __ | |__   __ _  ___| | __      #
#       / _ \| |    | |   \___ \| '_ \ / _` | '_ \| '_ \ / _` |/ __| |/ /      #
#      / ___ \ |___ | |    ___) | | | | (_| | |_) | |_) | (_| | (__|   <       #
#     /_/   \_\____|___|  |____/|_| |_|\__,_| .__/|_.__/ \__,_|\___|_|\_\      #
#                                           |_|                                #
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
"""  Snapback: Configuration Snapshot and Rollback for ACI fabrics

     This file contains the main engine for the Snapback tool that handles
     taking the actual configuration snapshots and performing the rollback.
     It runs as a standalone tool in addition, it can be imported as a library
     such as when used by the GUI frontend.
"""
import os
import git
import time
import json
import threading
import datetime
import sys

import acitoolkit as ACI
from requests import Timeout, ConnectionError
try:
    from paramiko import SSHClient, AutoAddPolicy
except ImportError:
    raise ImportError("Paramiko is required to run snapback, please install it.")
import tarfile
import StringIO


class SnapshotScheduler(threading.Thread):
    """
    Scheduler thread responsible for ongoing snapshots.  Used internally
    by the ConfigDB class.  There should be no need for a user to create
    this class directly.
    """
    def __init__(self, cdb):
        threading.Thread.__init__(self)
        self._schedule = None
        self._exit = False
        self._cdb = cdb
        self._next_snapshot_time = None
        self._callback = None

    def set_schedule(self, frequency='onetime', interval=None,
                     granularity='days', start_date=None,
                     start_time=None, callback=None):
        """
        Set the scheduler interval

        :param frequency: string indicating the snapshot frequency.  Valid
                          values are 'onetime' and 'interval'.  Default is
                          'onetime'.
        :param interval: string containing the number to be used for the
                         interval. Used in conjunction with the granularity
                         parameter to set the snapshot interval.  Default is
                         None.
        :param granularity: Provides the unit of measurement of the interval
                            value. Valid values are 'minutes', 'hours', and
                            'days'.  Default is 'days'.
        :param start_date: String containing the date that the initial snapshot
                           in the interval will begin.  Expected in to be
                           provided in the format '%Y-%m-%d'. Default is None.
        :param start_time: String containing the time that the initial snapshot
                           in the interval will begin.  Expected to be provided
                           in the format '%H:%M'. Default is None.
        :param callback: Optional callback function that is called when the
                         schedule settings change.
        """
        print 'Set schedule'
        assert frequency in ['onetime', 'interval']
        assert granularity in ['minutes', 'hours', 'days']
        self._schedule = {}
        self._schedule['frequency'] = frequency
        self._schedule['interval'] = interval
        self._schedule['granularity'] = granularity
        self._schedule['start_date'] = start_date
        self._schedule['start_time'] = start_time
        self._callback = callback
        start = datetime.datetime(start_date.year, start_date.month,
                                  start_date.day, start_time.hour,
                                  start_time.minute)
        self._next_snapshot_time = start

    def get_current_schedule(self):
        """
        Return the current schedule settings

        :returns: dictionary containing current schedule settings
        """
        return self._schedule

    def get_next_snapshot_time(self):
        """
        Return the time of the next snapshot

        :returns: String with the format '%Y-%m-%d %H:%M' that indicates when
                  the next snapshot is scheduled.
        """
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
        """
        Runs the snapshot interval.  This function will invoke the ConfigDB
        object to take the configuration snapshot.
        """
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
                # self._cdb.take_snapshot(self._callback)
                self._cdb.take_snapshot_using_export_policy(self._callback)
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
                    next_snapshot = cur_time + datetime.timedelta(days=addnl_days,
                                                                  hours=addnl_hours,
                                                                  minutes=addnl_minutes)
                    self._next_snapshot_time = next_snapshot
                    print 'Next snapshot in', self._next_snapshot_time
                    time.sleep(seconds)
            else:
                delta = start - datetime.datetime.now()
                seconds = delta.seconds + delta.days * (24 * 60 * 60)
                self._next_snapshot_time = start
                if seconds == 0:
                    seconds = 1
                time.sleep(seconds)


class ConfigDB(object):
    """
    Main configuration snapshot and rollback engine.  Instantiate this
    class when importing the functionality into other applications.
    """
    def __init__(self):
        self.session = None
        # Create the Git repository
        repo_parent_dir = os.getcwd()
        self.repo_dir = os.path.join(repo_parent_dir, 'apic-config-db')
        try:
            self.repo = git.Repo.init(self.repo_dir)
        except:
            print 'Unable to initialize repository. Are you sure git is installed ?'
            sys.exit(0)
        self._snapshot_scheduler = None
        self.rsp_prop_include = 'config-only'

    def login(self, args, timeout=2):
        """
        Login to the APIC

        :param args: An instance containing the APIC credentials.  Expected to
                     have the following instance variables; url, login, and
                     password.
        :param timeout:  Optional integer argument that indicates the timeout
                         value in seconds to use for APIC communication.
                         Default value is 2.
        :returns: Instance of Requests Response indicating the connection
                  status
        """
        self.session = ACI.Session(args.url, args.login, args.password)

        resp = self.session.login(timeout)
        return resp

    def is_logged_in(self):
        """
        Returns the status of the APIC login.

        :returns:  True or False.  True indicates that the ConfigDB instance
                   has logged in to the APIC.
        """
        return self.session is not None

    def _get_from_apic(self, url):
        """
        Internal wrapper function for communicating with the APIC

        :returns: JSON dictionary of returned data
        """
        ret = self.session.get(url)
        ret._content = ret.content.replace('\n', '')
        ret._content = ret.content.replace("\\\'", "'")
        data = ret.json()
        return data

    def _snapshot(self, query_url, filename):
        """
        Internal function to perform a single snapshot file

        :param query_url: string containing URL to send to APIC to
                          grab configuration
        :param filename: string containing the filename where the
                         configuration should be written
        """
        filename = os.path.join(self.repo_dir, filename)
        data = self._get_from_apic(query_url)

        # sort the JSON format if the filename is a domain
        if filename.endswith('domain.json'):
            # Extract the domain key based on the filename
            domain_key = filename.rpartition('/')[2].partition('-')[0] + 'DomP'
            # sort the "imdata" list from the nested dict based on the key "name"
            data['imdata'] = sorted(data['imdata'], key=lambda k: k[domain_key]['attributes']['name'])

        # Write the config to a file
        config_file = open(filename, 'w')
        config_file.write(json.dumps(data, indent=4, separators=(',', ':')))
        config_file.close()

        # Add the file to Git
        self.repo.index.add([filename])

    def _get_url_for_file(self, filename):
        """
        Internal function to generate a URL for communicating with the APIC
        that will get the configuration for a given filename

        :param filename: string containing the filename
        """
        config_resp = self.rsp_prop_include
        if filename.startswith('tenant-'):
            tenant_name = filename.split('tenant-')[1].split('.json')[0]
            url = ('/api/mo/uni/tn-%s.json?rsp-subtree=full&'
                   'rsp-prop-include=%s' % (tenant_name, config_resp))
        elif filename.startswith('node-'):
            url = ('/api/mo/', '/sys.json?query-target=subtree'
                   '&rsp-prop-include=%s' % config_resp)
        elif filename == 'infra.json':
            url = ('/api/mo/uni/infra.json?rsp-subtree=full&'
                   'rsp-prop-include=%s' % config_resp)
        elif filename == 'fabric.json':
            url = ('/api/mo/uni/fabric.json?rsp-subtree=full&'
                   'rsp-prop-include=%s' % config_resp)
        elif filename == 'phys-domain.json':
            url = ('/api/node/class/physDomP.json?query-target=self&'
                   'rsp-subtree=full&rsp-prop-include=%s' % config_resp)
        elif filename == 'vmm-domain.json':
            url = ('/api/node/class/vmmDomP.json?query-target=self&'
                   'rsp-subtree=full&rsp-prop-include=%s' % config_resp)
        elif filename == 'l2ext-domain.json':
            url = ('/api/node/class/l2extDomP.json?query-target=self&'
                   'rsp-subtree=full&rsp-prop-include=%s' % config_resp)
        elif filename == 'l3ext-domain.json':
            url = ('/api/node/class/l3extDomP.json?query-target=self&'
                   'rsp-subtree=full&rsp-prop-include=%s' % config_resp)
        elif filename == 'topology.json':
            url = ('/api/mo/topology.json?query-target=subtree'
                   '&rsp-prop-include=%s' % config_resp)
        elif filename == 'comp.json':
            url = ('/api/mo/comp.json?query-target=subtree'
                   '&rsp-prop-include=%s' % config_resp)
        return url

    def take_snapshot(self, callback=None):
        """
        Perform an immediate snapshot of the APIC configuration.

        :param callback: Optional callback function that can be used to notify
                         applications when a snapshot is taken.  Used by the
                         GUI to update the snapshots view when recurring
                         snapshots are taken.
        """
        tag_name = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())

        # Save each tenants config
        tenants = ACI.Tenant.get(self.session)
        for tenant in tenants:
            filename = 'tenant-%s.json' % tenant.name
            url = self._get_url_for_file(filename)
            self._snapshot(url, filename)

        # Save each nodes config
        nodes = ACI.Node.get(self.session)
        for node in nodes:
            filename = 'node-%s.json' % node.name
            url_prefix, url_suff = self._get_url_for_file(filename)
            url = '%s%s%s' % (url_prefix, node.dn, url_suff)
            self._snapshot(url, filename)

        # Save the rest of the config
        filenames = ['infra.json', 'fabric.json', 'phys-domain.json',
                     'vmm-domain.json', 'l2ext-domain.json', 'l3ext-domain.json',
                     'topology.json', 'comp.json']
        for filename in filenames:
            url = self._get_url_for_file(filename)
            self._snapshot(url, filename)

        # Commit the files and tag with the timestamp
        self.repo.index.commit(tag_name)
        self.repo.git.tag(tag_name)

        if callback:
            callback()

    def take_snapshot_using_export_policy(self, callback=None):
        """
        Perform an immediate snapshot of the APIC configuration.

        :param callback: Optional callback function that can be used to notify
                         applications when a snapshot is taken.  Used by the
                         GUI to update the snapshots view when recurring
                         snapshots are taken.
        """
        tag_name = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())

        url = '/api/node/mo/uni/fabric.json'
        remote_path_payload = {
            "fileRemotePath": {
                "attributes": {
                    "remotePort": "22",
                    "name": "snapback",
                    "host": "%s" % self.session.ipaddr,
                    "remotePath": "/home/%s" % self.session.uid,
                    "protocol": "scp",
                    "userName": "%s" % self.session.uid,
                    "userPasswd": "%s" % self.session.pwd
                },
                "children": []
            }
        }
        resp = self.session.push_to_apic(url, remote_path_payload)

        export_policy_payload = {
            "configExportP": {
                "attributes": {
                    "name": "snapback",
                    "adminSt": "triggered"
                },
                "children": [
                    {
                        "configRsRemotePath": {
                            "attributes": {
                                "tnFileRemotePathName": "snapback"
                            },
                            "children": []
                        }
                    }
                ]
            }
        }
        resp = self.session.push_to_apic(url, export_policy_payload)
        if not resp.ok:
            print resp, resp.text

        time.sleep(10)
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(self.session.ipaddr, username=self.session.uid, password=self.session.pwd)

        sftp = ssh.open_sftp()
        sftp.chdir('/home/%s' % self.session.uid)
        file_names = sftp.listdir()
        print file_names
        for file_name in file_names:
            if str(file_name).startswith('ce2_snapback-'):
                sftp.get('/home/' + self.session.uid + '/' + file_name, './' + file_name)
                sftp.remove('/home/' + self.session.uid + '/' + file_name)
                with tarfile.open(file_name, 'r:gz') as tfile:
                    tfile.extractall(self.repo_dir)
                os.remove(file_name)
                for json_filename in os.listdir(self.repo_dir):
                    print 'checking', json_filename
                    if json_filename.startswith('ce2_snapback') and json_filename.endswith('.json'):
                        new_filename = 'snapshot_' + self.session.ipaddr + '_' + json_filename.rpartition('_')[2]
                        new_filename = os.path.join(self.repo_dir, new_filename)
                        print 'renaming', json_filename, 'to', new_filename
                        json_filename = os.path.join(self.repo_dir, json_filename)
                        with open(json_filename, 'r') as old_file:
                            config = json.loads(old_file.read())
                        with open(new_filename, 'w') as new_file:
                            new_file.write(json.dumps(config, indent=4, separators=(',', ':')))
                        os.remove(json_filename)
                        # Add the file to Git
                        self.repo.index.add([new_filename])

        # Commit the files and tag with the timestamp
        self.repo.index.commit(tag_name)
        self.repo.git.tag(tag_name)

        if callback:
            callback()

    def get_current_schedule(self):
        """
        Gets the current snapshot schedule

        :returns: dictionary containing the snapshot schedule settings
        """
        if self._snapshot_scheduler:
            return self._snapshot_scheduler.get_current_schedule()
        else:
            return None

    def schedule_snapshot(self, frequency='onetime', interval=None,
                          interval_granularity='days',
                          start_date=None, start_time=None, callback=None):
        """
        Schedule a (potentially ongoing) snapshot of the APIC configuration.

        :param frequency: string containing whether the snapshot is a one time
                          occurence or ongoing.  Valid values are 'onetime' and
                          'interval'.  Default is 'onetime'.
        :param interval: string containing the number to be used for the
                         interval. Used in conjunction with the granularity
                         parameter to set the snapshot interval.  Default is
                         None.
        :param granularity: Provides the unit of measurement of the interval
                            value. Valid values are 'minutes', 'hours', and
                            'days'.  Default is 'days'.
        :param start_date: String containing the date that the initial snapshot
                           in the interval will begin.  Expected in to be
                           provided in the format '%Y-%m-%d'. Default is None.
        :param start_time: String containing the time that the initial snapshot
                           in the interval will begin.  Expected to be provided
                           in the format '%H:%M'. Default is None.
        :param callback: Optional callback function that is called when the
                         snapshot has occurred.
        """
        if self._snapshot_scheduler is not None:
            self.cancel_schedule()
        self._snapshot_scheduler = SnapshotScheduler(self)
        self._snapshot_scheduler.daemon = True
        self._snapshot_scheduler.set_schedule(frequency, interval,
                                              interval_granularity,
                                              start_date, start_time, callback)
        self._snapshot_scheduler.start()

    def cancel_schedule(self):
        """
        Cancel the current snapshot schedule
        """
        if self._snapshot_scheduler:
            self._snapshot_scheduler.exit()

    def get_latest_file_version(self, filename):
        """
        Get the latest version identifier of a given filename

        :param filename: string containing the file name
        :returns: string containing the latest version identifier for the
                  specified file
        """
        try:
            versions = str(self.repo.git.show('--tags',
                                              '--name-only',
                                              '--oneline',
                                              filename))
        except git.exc.GitCommandError:
            return None
        versions = versions.split('\n')
        assert len(versions) >= 2
        latest_version = versions[-2]
        assert ' ' in latest_version
        latest_version = latest_version.split(' ')
        assert len(versions) >= 2
        return latest_version[1]

    def get_versions(self, with_changes=False):
        """
        Get the list of version identifiers that exist for the configuration
        snapshots held in the snapshot repository.  Optionally, the number of
        additions/deletions per version can be requested as well.

        :param with_changes: Boolean containing whether changes
                             (additions / deletions) are to be included with
                             the version identifiers.
        :returns: list of strings where each string represents a version
                  identifier OR a list of tuples where each tuple contains
                  a string representing the version identifier, a string
                  representing the number of additions in this version in
                  comparison with the previous version, and a string
                  representing the number of deletions in this version in
                  comparison with the previous version.
        """
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
                elif 'insertion' in changes:
                    additions = '1'
                if 'deletions' in changes:
                    deletions = changes.split(' deletions')[0].split(' ')[-1]
                elif 'deletion' in changes:
                    deletions = '1'
                resp.append((version, additions, deletions))
                previous_version = version
            return resp

    def get_latest_version(self):
        """
        Get the latest snapshot version

        :returns: string containing the latest snapshot version
        """
        versions = self.get_versions()
        if len(versions) < 1:
            return None
        return self.get_versions()[-1]

    def get_filenames(self, version,
                      prev_version=None, with_changes=False):
        """
        Get the list of filenames for a specific snapshot version
        Optionally, the number of changes (additions/deletions) in
        comparison with the previous version.

        :param version: string containing the version identifier of the
                        snapshot configuration
        :param prev_version: Optional string containing the previous version
                             identifier for the purposes of calculating
                             additions/deletions.  Default is None.
        :param with_changes: Optional boolean indicating whether changes
                             (additions/deletions) should be included in the
                             response.
        :returns: list of strings where each string is a file name OR a list
                  of tuples where each tuple contains a string representing
                  the file name, a string representing the number of additions
                  in this file in comparison with the previous version, and a
                  string representing the number of deletions in this file in
                  comparison with the previous version.
        """
        filenames = str(self.repo.git.show('--name-only',
                                           '--oneline',
                                           version))
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
                elif 'insertion' in changes:
                    additions = '1'
                if 'deletions' in changes:
                    deletions = changes.split(' deletions')[0].split(' ')[-1]
                elif 'deletion' in changes:
                    deletions = '1'
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
        """
        Get the file of a specific version from the snapshot repository

        :param filename: string containing the file name
        :param version: string containing the version
        :returns: string containing the JSON contained within the specified
                  file
        """
        return self.repo.git.show(version + ':' + filename)

    def get_next_snapshot_time(self):
        """
        Get the next snapshot time according to the snapshot scheduler

        :returns: string containing the next snapshot time or None if
                  no snapshot is currently scheduled
        """
        if self._snapshot_scheduler:
            return self._snapshot_scheduler.get_next_snapshot_time()
        else:
            return None

    def get_latest_snapshot_time(self):
        """
        Get the most recent snapshot time contained with the snapshot
        repository

        :returns: string containing the latest snapshot time or None if
                  the repository doesn't contain any snapshots
        """
        if len(self.get_versions()) == 0:
            return None
        latest_tag = self.repo.git.describe('--abbrev=0', '--tags')
        if latest_tag is None:
            return None
        (latest_date, latest_time) = latest_tag.split('_')
        year, month, day = latest_date.split('-')
        hour, minute, msec = latest_time.split('.')
        latest_snapshot = datetime.datetime(int(year), int(month), int(day),
                                            int(hour), int(minute))
        return latest_snapshot

    @staticmethod
    def _print(title, items):
        """
        Internal function to iterate through a number of items for printing

        :param title: string containing the title to print before iterating
                      through the items
        :param items: list of strings that need to be printed
        """
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
        """
        Print all of the version identifiers contained within the snapshot
        repository
        """
        title = 'Versions'
        versions = self.get_versions()
        self._print(title, versions)

    def print_filenames(self, version):
        """
        Print all of the file names contained within the snapshot repository
        for a given snapshot version

        :param version: string containing the version identifier
        """
        title = 'Filenames'
        filenames = self.get_filenames(version)
        self._print(title, filenames)

    def _ordered(self, obj):
        """
        Internal function used within rollback
        """
        if isinstance(obj, dict):
            return {k: self._ordered(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return sorted(self._ordered(x) for x in obj)
        else:
            return obj

    def _mark_mismatching(self, current, old):
        """
        Internal function used within rollback
        """
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
                    self._mark_mismatching(current[key]['children'][child],
                                           old[key]['children'][old_child_idx])
                    old_child_idx = old_child_idx + 1
            else:
                current[key]['attributes']['status'] = 'deleted'

    def _check_versions(self, filename, current_version, old_version):
        """
        Internal function used within rollback
        """
        current_version = self._ordered(current_version)
        old_version = self._ordered(old_version)

        if current_version == old_version:
            return True
        else:
            self._mark_mismatching(current_version, old_version)
            # Push it to the APIC
            url = self._get_url_for_file(filename)
            self.session.push_to_apic(url, current_version)
            return False

    def rollback(self, version, filenames=None):
        """
        Rollback the configuration of the selected files to the specified
        version

        :param version: string containing the version identifier
        :param filenames: list of strings containing file names that are
                          subject to rollback.  If None, then it is assumed
                          that all files for that version are to be rolled
                          back to the specified version
        """
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
            for data in old_version['imdata']:
                self.session.push_to_apic(url, data)
                print 'Pushing....'
                print data

            # Get the current version
            current_version = self._get_from_apic(url)

            # Look for any remaining differences
            # If differences exist, it is new config and will be removed.
            self._check_versions(filename, current_version, old_version)

    def _generate_tar_gz(self, filenames, version):
        """
        Generate a .tar.gz compressed archive file
        :param filenames: list of strings containing the filenames to add to the tar.gz file
        :param version: Version of the snapshot
        :return: None
        """
        tar = tarfile.open('ce2_snapback.tar.gz', 'w:gz')
        for filename in filenames:
            content = self.get_file(filename, version)
            content = json.loads(content)
            output = StringIO.StringIO()
            output.write(json.dumps(content))
            output.seek(0)
            info = tarfile.TarInfo(name=filename)
            info.size = len(output.buf)
            info.mtime = time.time()
            tar.addfile(tarinfo=info, fileobj=output)
        tar.close()

    def rollback_using_import_policy(self, version):
        """
        Rollback the configuration using the Import policy for a specific version
        :param version: Version to rollback to
        :return: Requests Response object indicating the success of pushing the config to the APIC
        """

        filenames = self.get_filenames(version)

        # Create the tar file of the selected JSON files
        self._generate_tar_gz(filenames, version)

        # Put the tar file on the APIC
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(self.session.ipaddr, username=self.session.uid, password=self.session.pwd)
        sftp = ssh.open_sftp()
        sftp.chdir('/home/%s' % self.session.uid)
        sftp.put('./ce2_snapback.tar.gz', 'ce2_snapback.tar.gz')

        # Remove the local tar file
        os.remove('./ce2_snapback.tar.gz')

        # Send the import policy to the APIC
        url = '/api/node/mo/uni/fabric.json'
        payload = {"configImportP": {"attributes": {"name": "snapback",
                                                    "fileName": "ce2_snapback.tar.gz",
                                                    "adminSt": "triggered",
                                                    "importType": "replace",
                                                    "importMode": "atomic"},
                                     "children": [{"configRsImportSource": {"attributes": {"tnFileRemotePathName": "snapback"},
                                                                            "children": []
                                                                            }}]}}
        resp = self.session.push_to_apic(url, payload)
        return resp

    def has_diffs(self, version1, version2, filename):
        """
        Check whether there are any changes in the specified file between the
        2 specified snapshot versions

        :param version1:  string containing the first version identifier
        :param version2:  string containing the second version identifier
        :param filename: string containing the file name
        :returns: True or False.  True if there are changes between the 2
                  versions of the file.
        """
        resp = self.repo.git.diff(version1 + ':' + filename,
                                  version2 + ':' + filename)
        if len(resp):
            return True
        else:
            return False


def main(args=None):
    """
    Main execution path when run from the command line
    """
    # Get all the arguments
    if args is None:
        description = 'Configuration Snapshot and Rollback tool for APIC. v0.2'
        creds = ACI.Credentials('apic', description)
        commands = creds.add_mutually_exclusive_group()
        commands.add_argument('-s', '--snapshot', action='store_true',
                              help='Take a snapshot of the APIC configuration')
        commands.add_argument('-ls', '--list-snapshots', action='store_true',
                              help='List all of the available snapshots')
        help_txt = ('Configuration file responses include all properties of'
                    ' the returned managed objects.')
        creds.add_argument('-a', '--all-properties', action='store_true',
                           default=False,
                           help=help_txt)
        help_txt = ('Configuration snapshot using the method available in v0.1.')
        creds.add_argument('--v1', action='store_true',
                           default=False,
                           help=help_txt)
        help_txt = 'List all of the available configuration files.'
        commands.add_argument('-lc', '--list-configfiles', nargs='*',
                              metavar=('VERSION'),
                              default=None,
                              help=help_txt)
        help_txt = ('Rollback the configuration to the specified version.'
                    ' Optionally only for certain configuration files.')
        commands.add_argument('--rollback', nargs='+',
                              metavar=('VERSION'),
                              help=help_txt)
        help_txt = ('Show the contents of a particular configfile'
                    ' from a particular snapshot version.')
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
        if args.all_properties:
            cdb.rsp_prop_include = 'all'
        if args.v1:
            cdb.take_snapshot()
        else:
            cdb.take_snapshot_using_export_policy()
    elif args.rollback is not None:
        version = args.rollback[0]
        cdb.rollback_using_import_policy(version)
    elif args.show is not None:
        version = args.show[0]
        filename = args.show[1]
        config = cdb.get_file(version, filename)
        print config

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
