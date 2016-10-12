# Copyright (c) 2014, 2015 Cisco Systems, Inc.
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
"""  This module contains code that emulates the Session class except that
     there is no actual APIC and the configuration comes from JSON files.
"""
from copy import deepcopy
import json
import re
try:
    import urlparse
except ImportError:
    from urllib.parse import urlparse

from .acisession import Session
import logging


class FakeResponse(object):
    """
    Create a Fake shell of a Requests.Response object
    """
    def __init__(self, data=None):
        self.ok = True
        self._data = {}
        self._data['imdata'] = data
        self._content = ''

    def json(self):
        """
        Get the JSON format of the Response data

        :return: dictionary with the JSON formatted data
        """
        return self._data


class FakeSubscriber(object):
    """
    Create a fake shell of a Subscriber object from acisession module
    """
    def refresh_subscriptions(self):
        """
        Filler function to replace refresh_subscriptions

        :return: None
        """
        pass

    def _resubscribe(self):
        """
        Filler function to replace _resubscribe

        :return: None
        """
        pass


class FakeSession(Session):
    """
    Class to fake an APIC Session
    """
    def __init__(self, filenames=()):
        """
        Create a fake APIC session based off of the supplied JSON files
        :param filenames: list of filenames containing the JSON configuration
        :return: None
        """
        self.db = []
        self.subscription_thread = FakeSubscriber()
        self._classes = {}
        for filename in filenames:
            with open(filename, 'r') as f:
                try:
                    data = json.loads(f.read())
                except ValueError:
                    continue
                # Skip invalid formatted files
                if 'imdata' not in data:
                    continue
                # Skip files that are timeout and other errors
                if len(data['imdata']) == 1:
                    if 'error' in data['imdata'][0]:
                        continue
                self._fill_data(data['imdata'], None)
                self.db.append(data)
            with open(filename, "w") as f:
                f.write(unicode(json.dumps(data, indent=4)))

    def _get_config(self, url):
        """
        Get the configuration of a specified URL

        :param url: string containing the URL to search the configuration
        :return: list of the found objects
        """
        queries = self._parse_url(url)
        dn, query_target, rsp_subtree, target_cls, node_cl = queries
        data, cl_data = [], []
        # the loop will execute even if there are no target classes
        # this ensures the get_class function gets called at least once
        for target in target_cls.split(','):
            cl_data = self._get_class(dn, node_cl, target, query_target)
            data.extend(cl_data)
        return self._rsp_subtree_data(data, rsp_subtree)

    @staticmethod
    def _parse_url(url):
        """
        Parse the url to get the dn, query-target, rsp-subtree,
        target-subtree-class(es), and the node class

        :param url: string containing the URL to be parsed
        :return: a tuple of data
        """
        # set a dummy url scheme to make the url look like a real one
        url = 'scheme://apic' + url
        url_parsed = urlparse.urlparse(url)
        cl_path = url_parsed.path.partition('.json')[0]
        path_regex = r'/api/(?:mo|node/class|class|node/mo)/(([^/]*).*)'
        dn, root_cl = re.search(path_regex, cl_path).groups()
        # get the queries as a dict
        url_queries = urlparse.parse_qs(url_parsed.query)
        # get the queries and convert them to a string
        query_target = ''.join(url_queries.get('query-target', ['self']))
        rsp_subtree = ''.join(url_queries.get('rsp-subtree', ['no']))
        target_classes = ','.join(url_queries.get('target-subtree-class',
                                                  ['']))
        node_class = None
        if dn == root_cl:
            node_class = root_cl
            if node_class == 'uni':
                node_class = target_classes
            dn = None
        return dn, query_target, rsp_subtree, target_classes, node_class

    def _get_class(self, dn, cl, target, query_target='self'):
        """
        Gets the configuration for the specified class instances based on
        the dn, node class, target class, and query-target

        :param dn: The distinguished name of the class
        :param cl: The node class
        :param target: The target class based on the target-subtree-class
        :param query_target: The query-target class in the url
        :return list of found objects
        """
        resp = []
        if cl:
            try:
                lst = self._classes[cl]
            except KeyError:
                logging.error('Unknown class %s', cl)
                return []
            return [cl_obj for _, cl_obj in lst]
        for _, lst in self._classes.iteritems():
            if target and query_target != 'self':
                lst = self._classes[target]
            for tup in lst:
                node_dn, node_cl = tup
                valid_dn = (dn == node_dn)
                if query_target == 'self' and valid_dn:
                    resp.append(node_cl)
                elif query_target == 'children':
                    if self._is_child(node_dn, dn):
                        resp.append(node_cl)
                elif query_target == 'subtree':
                    if self._is_subtree(node_dn, dn):
                        resp.append(node_cl)
            if target and resp:
                return resp
        return resp

    def _rsp_subtree_data(self, db, rsp_subtree='no'):
        """
        Gets the configuration based on the rsp-subtree value

        This function will copy the class objects and checks if
        deleting subchildren is necessary.

        :param db: The list of class objects to search
        :rsp_subtree: The rsp-subtree value
        :return: a list objects
        """
        if rsp_subtree != 'full':
            resp = []
            for node in db:
                node_cl, _ = next(node.iteritems())
                # make a deep copy to avoid deleting other nodes
                node_cl_copy = deepcopy(node[node_cl])
                ret = {}
                ret[node_cl] = {}
                ret[node_cl]['attributes'] = node_cl_copy['attributes']
                has_children = node_cl_copy.get('children')
                #  check if the response asks for only direct children
                if rsp_subtree == 'children' and has_children:
                    ret[node_cl]['children'] = node_cl_copy['children']
                    #  delete for subchildren
                    self._delete_subchildren(ret[node_cl]['children'])
                resp.append(ret)
            return resp
        return db

    @staticmethod
    def _delete_subchildren(db):
        """
        Deletes the children of the class object

        :param db: The list of class objects
        :return: None
        """
        for child in db:
            _, contents = next(child.iteritems())
            if contents.get('children'):
                del contents['children']

    @staticmethod
    def _is_child(child_dn, parent_dn):
        """
        Checks if the child dn is a direct child of the parent dn

        :param child_dn: The child distinguished name
        :param parent_dn: The parent distinguished name
        :return: True or False. True if the child_dn is a child
        """
        if not child_dn.startswith(parent_dn):
            return False
        child_dn_parse = child_dn[len(parent_dn) + 1:]
        # checks for a foward slash outside brackets (may be nested)
        if '[' in child_dn_parse:
            count = 0
            for char in child_dn_parse:
                if char == '[':
                    count += 1
                elif char == ']':
                    count -= 1
                elif char == '/' and not count:
                    return False
            return True
        return '/' not in child_dn_parse and child_dn_parse

    @staticmethod
    def _is_subtree(child_dn, parent_dn):
        """
        Checks if child dn is a subtree of the parent dn

        :param child_dn: The child distinguished name
        :param parent_dn: The parent distinguished name
        :return: True or False. True if the child_dn is a subtree
        """
        if not child_dn.startswith(parent_dn):
            return False
        path_parse = child_dn[len(parent_dn):]
        # the empty string means the two dn's are the same
        # therefore it should be included as a subtree
        return (not path_parse or path_parse[0] == '/')

    def _fill_data(self, children, parent_dn):
        """
        Recursively fill in the distinguished name (dn) for the
        configuration JSON files and sets the classes dictionary
        to be used for searching for class objects

        The classes dict is a key: list(tuple()...) configuration
        The key is the class name (e.g. fvTenant)
        The list contains a tuple of dn's and the class object itself

        :param children: Children of the parent node
        :param parent_dn: Parent dn to be passed on to their children
        :return: None
        """
        for child in children:
            node_cl, contents = next(child.iteritems())
            attributes = contents['attributes']
            if not attributes.get('dn'):
                rn = attributes['rn']
                attributes['dn'] = parent_dn + '/' + rn
            tup = (attributes['dn'], child)
            if not self._classes.get(node_cl):
                self._classes[node_cl] = []
            self._classes[node_cl].append(tup)
            if contents.get('children'):
                self._fill_data(contents['children'], attributes['dn'])

    def login(self, timeout=None):
        """
        Initiate login to the APIC.  Opens a communication session with the\
        APIC using the python requests library.

        :returns: Response class instance from the requests library.\
        response.ok is True if login is successful.
        """
        resp = FakeResponse()
        return resp

    def subscribe(self, url):
        """
        Subscribe to events for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string to issue subscription
        """
        pass

    def has_events(self, url):
        """
        Check if there are events for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string belonging to subscription
        :returns: True or False. True if an event exists for this subscription.
        """
        return False

    def get_event(self, url):
        """
        Get an event for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string belonging to subscription
        :returns: Object belonging to the instance or class that the
                  subscription was made.
        """
        return None

    def unsubscribe(self, url):
        """
        Unsubscribe from events for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string to remove issue subscription
        """
        pass

    @staticmethod
    def get_login_response(name='admin'):
        """
        Get the response to a login request
        :param name: String containing the user name
        :return: FakeResponse instance containing the login response
        """
        resp_data = [
            {
                "aaaLogin": {
                    "attributes": {
                        "token": "123456789",
                        "siteFingerprint": "123456789",
                        "refreshTimeoutSeconds": "600",
                        "maximumLifetimeSeconds": "86400",
                        "guiIdleTimeoutSeconds": "1200",
                        "restTimeoutSeconds": "90",
                        "creationTime": "2222222",
                        "firstLoginTime": "222222",
                        "userName": "%s" % name,
                        "remoteUser": "false",
                        "unixUserId": "12345",
                        "sessionId": "12345==",
                        "lastName": "",
                        "firstName": "",
                        "version": "1.2(1.216a)",
                        "buildTime": "Sat Feb 13 01:56:41 PST 2016",
                        "node": "topology/pod-1/node-1"
                    },
                    "children": [
                        {
                            "aaaUserDomain": {
                                "attributes": {
                                    "name": "all",
                                    "rolesR": "admin",
                                    "rolesW": "admin"
                                },
                                "children": []
                            }
                        }
                    ]
                }
            }
        ]
        return FakeResponse(data=resp_data)

    def push_to_apic(self, url, data):
        """
        Push the object data to the APIC

        :param url: String containing the URL that will be used to\
                    send the object data to the APIC.
        :param data: Dictionary containing the JSON objects to be sent\
                     to the APIC.
        :returns: Response class instance from the requests library.\
                  response.ok is True if request is sent successfully.
        """
        if 'aaaUser' in data:
            name = json.loads(data)['aaaUser']['attributes']['name']
            return self.get_login_response(name)
        resp = FakeResponse()
        return resp

    def get(self, url):
        """
        Perform a REST GET call to the APIC.

        :param url: String containing the URL that will be used to\
        send the object data to the APIC.
        :returns: Response class instance from the requests library.\
        response.ok is True if request is sent successfully.\
        response.json() will return the JSON data sent back by the APIC.
        """
        if '/api/aaaRefresh' in url:
            return self.get_login_response()
        if url.startswith('/socket'):
            resp_data = [{}]
            resp = FakeResponse(data=resp_data)
        else:
            resp = FakeResponse(self._get_config(url))
        return resp
