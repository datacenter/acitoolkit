#!/usr/bin/env python
################################################################################
# _    ____ ___   ____                       _                   #
# / \  / ___|_ _| |  _ \ ___ _ __   ___  _ __| |_ ___             #
# / _ \| |    | |  | |_) / _ \ '_ \ / _ \| '__| __/ __|            #
# / ___ \ |___ | |  |  _ <  __/ |_) | (_) | |  | |_\__ \            #
#           /_/   \_\____|___| |_| \_\___| .__/ \___/|_|   \__|___/            #
#                                        |_|                                   #
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


class SwitchJson(object):
    """
    This class will hold the entire json tree
    from topSystem down, for a switch.
    The attributes of a specific class can be retrieved
    in which case it will be as a list of objects.
    It will allow all children of an object to be retrieved
    result is list of objects
    It will allow an instance of a class to be retrieved returned
    as a single object.
    """

    def __init__(self, session, node_id):
        self.session = session
        self.node_id = node_id

        self.by_class = {}
        self.by_dn = {}

        pod_id = '1'
        self.top_dn = 'topology/pod-' + pod_id + '/node-' + self.node_id + '/sys'
        query_url = ('/api/mo/' + self.top_dn + '.json?'
                                                'query-target=self&rsp-subtree=full')

        ret = session.get(query_url)
        data = ret.json()['imdata']
        if data:
            self.json = ret.json()['imdata'][0]
        else:
            self.json = None
        self._index_objects()

    def _index_objects(self):
        """
        This will go throught the object tree and
        add absolute dns to each object

        create a dictionary indexed by dn that points to each object dictionary

        create a dictionary indexed by class name that
        has a list of objects of that class.
        """
        self.by_class = {}
        self.by_dn = {}

        dn_root = self.top_dn
        self._index_recurse_dn(self.json, dn_root)
        self._index_by_dn_class(self.json)

    def _index_by_dn_class(self, branch):
        """
        Will index the json by dn and by class for quick reference
        """
        if branch:
            for apic_class in branch:
                self.by_dn[branch[apic_class]['attributes']['dn']] = {apic_class: branch[apic_class]}

                if apic_class not in self.by_class:
                    self.by_class[apic_class] = []

                self.by_class[apic_class].append({apic_class: branch[apic_class]})

                if 'children' in branch[apic_class]:
                    for child in branch[apic_class]['children']:
                        self._index_by_dn_class(child)

    def _index_recurse_dn(self, branch, dn_root):
        """
        recursive part of _index_objects
        """
        if branch:
            for apic_class in branch:
                if 'dn' not in branch[apic_class]['attributes']:
                    branch[apic_class]['attributes']['dn'] = dn_root + \
                        '/' + branch[apic_class]['attributes']['rn']
                new_root_dn = branch[apic_class]['attributes']['dn']
                if 'children' in branch[apic_class]:
                    for child in branch[apic_class]['children']:
                        self._index_recurse_dn(child, new_root_dn)

    def get_class(self, class_name):
        """
        returns all the objects of a given class
        """
        result = self.by_class.get(class_name)
        if not result:
            return []
        return result

    def get_subtree(self, class_name, dname):
        """
        will return list of matching classes and their attributes

        It will get all classes that
        are classes under dn.
        """
        result = []

        classes = self.get_class(class_name)
        if classes:
            for class_record in classes:
                for class_id in class_record:
                    obj_dn = class_record[class_id]['attributes']['dn']
                    if obj_dn[0:len(dname)] == dname:
                        result.append(class_record)
        return result

    def get_object(self, dname):
        """
        Will return the object specified by dn.
        """
        # start at top
        result = self.by_dn.get(dname)
        if not result:
            return None
        return result
