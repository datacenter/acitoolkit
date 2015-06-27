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
import json
import urlparse
import re
from copy import deepcopy
from acisession import Session

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
    def __init__(self, filenames=[]):
        """
        Create a fake APIC session based off of the supplied JSON files
        :param filenames: list of filenames containing the JSON configuration
        :return: None
        """
        self.db = []
        self.subscription_thread = FakeSubscriber()
        for filename in filenames:
            f = open(filename, 'r')
            data = json.loads(f.read())
            self._fill_dn(data['imdata'], None)
            self.db.append(data)
            f.close()
            with open(filename, "w") as f:
                 f.write(unicode(json.dumps(data, indent=4)))

    def _get_config(self, url):
        """
        Get the configuration of a specified URL

        :param url: string containing the URL to search the configuration
        :return: list of the found objects
        """
        queries = self._parse_url(url)
        root_n, root_cl, cln, cl, query_target, rsp_subtree, target_classes = queries
        root_data, init_data, q_data = [], [], []
        # The root class cases that cannot be found in the JSON files
        class_cases = ['uni', 'topology']
        root = root_cl in class_cases
        # find the class data to start with
        for db in self.db:
            children = db['imdata']
            self._get_class(children, root_data, root_n, root_cl, root)
            # if root_data and not root:
                # break
        # find the class to traverse through from root_data
        self._get_class(root_data, init_data, cln, cl, root)
        no_child_data = (query_target in ('self', 'subtree') and not target_classes)
        self_data = (query_target == 'self' and target_classes)
        if self_data or no_child_data:
            q_data.extend(init_data)
        # get the data specified for the query-target and target class(es)
        for target_class in target_classes.split(','):
            self._query_target_data(init_data, q_data, query_target, target_class)
        return self._rsp_subtree_data(q_data, rsp_subtree)

    def _parse_url(self, url):
        """
        """
        url = 'scheme://apic' + url
        url_parsed = urlparse.urlparse(url)
        cl_path = url_parsed.path.partition('.json')[0]
        root_regex = '/api/(?:mo|node/class)/([^/\n]*(?:/[^/\n]*)?)'
        root = re.search(root_regex, cl_path).groups(0)[0].rpartition('/')[-1]
        root_n, root_cl = self._get_class_name(root)
        cl_n, cl = self._get_class_name(cl_path.rpartition('/')[-1])
        # get the queries as a dict
        url_queries = urlparse.parse_qs(url_parsed.query)
        # get the queries and parse convert them to a string
        query_target = ''.join(url_queries.get('query-target', ['self']))
        rsp_subtree = ''.join(url_queries.get('rsp-subtree', ['no']))
        target_classes = ','.join(url_queries.get('target-subtree-class', ['']))
        # add unimplemented queries
        if url_queries.get('rsp-subtree-include'):
            raise NotImplementedError('url: ' + url)
        return root_n, root_cl, cl_n, cl, query_target, rsp_subtree, target_classes
    
    def _get_class(self, db, resp, cl_n, cl, root=False):
        """
        """
        for node in db:
            node_cl, contents = next(node.iteritems())
            attributes = contents['attributes']
            if attributes.get('name'):
                valid_name = (cl_n == attributes['name'])
                valid_class = (node_cl == cl)
                if (valid_class and valid_name) or root:
                    resp.append(node)
            if contents.get('children'):
                kids = contents['children']
                self._get_class(kids, resp, cl_n, cl, root)
        
    def _query_target_data(self, db, resp, q_target='self', cl=None, depth=0):
        """
        """
        if q_target != 'self':
            for node in db:
                node_cl, contents = next(node.iteritems())
                if node_cl == cl and (depth == 1 or q_target == 'subtree'):
                    resp.append(node)
                if contents.get('children'):
                    children = contents['children']
                    #  if we're not looking for a target-subtree-class
                    if not cl and q_target in ('children', 'subtree'):
                        resp.extend(children)
                    if q_target in ('subtree', 'children'):
                        if q_target == 'children':
                            #  go only 1 recursive call if the query target is children
                            q_target, depth = (None, 1)
                        self._query_target_data(children, resp, q_target, cl, depth)

    def _rsp_subtree_data(self, db, rsp_subtree='no'):
        """
        """
        if rsp_subtree != 'full':
            resp = []
            for node in db:
                node_cl, contents = next(node.iteritems())
                # make a deep copy to avoid deleting other node
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

    def _delete_subchildren(self, children):
        """

        """
        for child in children:
            _, contents = next(child.iteritems())
            if contents.get('children'):
                del contents['children']
            
    def _get_class_name(self, cln):
        """
        Extracts the class name from the class name prefix and returns a
        tuple with the class name and its class.

        Example cln: 'tn-Tenant12'
        
        :param cln: The class name prefix with the class name
        :return: The class name with its class
        """
        cln_dct = {
            'uni': 'uni',
            'tn-': 'fvTenant',
            'ap-': 'fvAp',
            'BD-': 'fvBD',
            'epg-': 'fvAEPg',
            'flt-': 'vzFilter',
            'sys': 'topSystem'
        }
        for k, v in cln_dct.iteritems():
            if cln.startswith(k):
                return (cln.partition(k)[-1], v)
        raise NotImplementedError('This class is not in the dict: ' + cln)
    
    def _fill_dn(self, children, parent_dn):
        """
        Recursively fill in the distinguished name (dn) for the configuration 
        JSON files.

        :param children: Children of the parent node
        :param parent_dn: Parent dn to be passed on to their children
        :return: None
        """
        for child in children:
            for node in child:
                attributes = child[node]['attributes']
                if not attributes.get('dn'):
                    rn = attributes['rn']
                    attributes['dn'] = parent_dn + '/' + rn
                if child[node].get('children'):
                    self._fill_dn(child[node]['children'], attributes['dn'])


                    
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
        resp = FakeResponse(self._get_config(url))
        return resp
