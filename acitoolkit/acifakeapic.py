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
from acisession import Session


class FakeResponse(object):
    """
    Create a Fake shell of a Requests.Response object
    """
    def __init__(self, data=None):
        self.ok = True
        self._data = {}
        self._data['imdata'] = data

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

    def _get_class(self, class_name, resp, db,
                   with_children=False, with_name=None):
        """
        Recursively search the configuration for the specified class instances

        :param class_name: APIC class to search the config
        :param resp: list of found configuration
        :param db: JSON configuration to search
        :param with_children: True or False.  True if the response should
                              include the children of the found objects.
        :param with_name: Name of the object to find.  If None, then all
                          objects of the specified class will be found.
        :return: list of found objects
        """
        if isinstance(db, list):
            for obj in db:
                assert not isinstance(obj, list)
                self._get_class(class_name, resp, obj,
                                with_children, with_name)
            return resp
        if class_name in db:
            if with_name and db[class_name]['attributes']['name'] != with_name:
                return resp
            if with_children:
                resp.append(db)
            else:
                ret = {}
                ret[class_name] = {}
                ret[class_name]['attributes'] = db[class_name]['attributes']
                resp.append(ret)
        else:
            for key in db:
                if 'imdata' == key:
                    for child in db[key]:
                        self._get_class(class_name, resp, child,
                                        with_children, with_name)
                elif 'children' in db[key]:
                    for child in db[key]['children']:
                        self._get_class(class_name, resp, child,
                                        with_children, with_name)
        return resp

    def _get_config(self, url):
        """
        Get the configuration of a specified URL

        :param url: string containing the URL to search the configuration
        :return: list of the found objects
        """
        # Check for class queries made under uni using class filter
        class_query = ('/api/mo/uni.json?query-target=subtree'
                       '&target-subtree-class=')
        if class_query in url:
            search_class = url[len(class_query):]
            resp = []
            self._get_class(search_class, resp, self.db)
            return resp
        # Check for other class queries
        class_query = '/api/node/class/'
        if url.startswith(class_query) and '?query-target=self' in url:
            search_class = url.rpartition('/')[2].partition('.')[0]
            resp = []
            self._get_class(search_class, resp, self.db)
            return resp
        subtree_class_query = ('.json?query-target=subtree&'
                               'target-subtree-class=')
        if url.startswith(class_query) and subtree_class_query in url:
            (parent_class, subtree_class) = url.split(subtree_class_query)
            parent_class = parent_class.split(class_query)[1]
            search_db = []
            self._get_class(parent_class, search_db, self.db,
                            with_children=True)
            resp = []
            self._get_class(subtree_class, resp, search_db)
            return resp
        tenant_query = '/api/mo/uni/tn-'
        if url.startswith(tenant_query) and subtree_class_query in url:
            tenant_name = url.split(tenant_query)[1]
            tenant_name = tenant_name.split(subtree_class_query)[0]
            subtree_class = url.split(subtree_class_query)[1]
            if '/' in tenant_name:
                name = tenant_name.split('/')
                tenant_name = name[0]
                bd_name = name[1]
                if '/' in bd_name:
                    print url
                    raise NotImplementedError
                search_db = []
                self._get_class('fvTenant', search_db, self.db,
                                with_children=True,
                                with_name=tenant_name)
                bd_search_db = []
                self._get_class('fvBD', bd_search_db, search_db,
                                with_children=True,
                                with_name=bd_name)
                resp = []
                self._get_class(subtree_class, resp, bd_search_db)
                return resp
            search_db = []
            self._get_class('fvTenant', search_db, self.db,
                            with_children=True,
                            with_name=tenant_name)
            resp = []
            self._get_class(subtree_class, resp, search_db)
            return resp
        object_subtree_query = '.json?query-target=self&rsp-subtree=full'
        if url.startswith(tenant_query) and object_subtree_query in url:
            tenant_name = url.split(tenant_query)[1]
            tenant_name = tenant_name.split(object_subtree_query)[0]
            if '/' in tenant_name:
                raise NotImplementedError
            resp = []
            self._get_class('fvTenant', resp, self.db,
                            with_children=True,
                            with_name=tenant_name)
            return resp
        else:
            raise NotImplementedError
        
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
