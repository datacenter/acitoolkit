################################################################################
#                                  _    ____ ___                               #
#                                 / \  / ___|_ _|                              #
#                                / _ \| |    | |                               #
#                               / ___ \ |___ | |                               #
#                         _____/_/   \_\____|___|_ _                           #
#                        |_   _|__   ___ | | | _(_) |_                         #
#                          | |/ _ \ / _ \| | |/ / | __|                        #
#                          | | (_) | (_) | |   <| | |_                         #
#                          |_|\___/ \___/|_|_|\_\_|\__|                        #
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
"""  This module contains the Session class that controls communication
     with the APIC.
"""
import logging
import json
import requests
from requests import Timeout, ConnectionError
import threading
import time
from websocket import create_connection, WebSocketException
# import websocket
import ssl

# Queue library is named "queue" in Python3
try:
    # Python2 naming
    from Queue import Queue
except ImportError:
    # Python3 naming
    from queue import Queue

try:
    import urllib3
except ImportError:
    pass
else:
    try:
        urllib3.disable_warnings()
    except AttributeError:
        pass

# Time before login timer expiration to send refresh
TIMEOUT_GRACE_SECONDS = 10


class Login(threading.Thread):
    """
    Login thread responsible for refreshing the APIC login before timeout.
    """
    def __init__(self, apic):
        threading.Thread.__init__(self)
        self._apic = apic
        self._login_timeout = 0
        self._exit = False

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def run(self):
        while not self._exit:
            time.sleep(self._login_timeout)
            self._apic._send_login()
            self._apic.resubscribe()


class EventHandler(threading.Thread):
    """
    Thread responsible for websocket communication.
    Receives events through the websocket and places them into a Queue
    """
    def __init__(self, subscriber):
        threading.Thread.__init__(self)
        self.subscriber = subscriber
        self._exit = False

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def run(self):
        while not self._exit:
            try:
                event = self.subscriber._ws.recv()
            except:
                break
            if not len(event):
                continue
            self.subscriber._event_q.put(event)


class Subscriber(threading.Thread):
    """
    Thread responsible for event subscriptions.
    Issues subscriptions, creates the websocket, and refreshes the
    subscriptions before timer expiry.  It also reissues the
    subscriptions when the APIC login is refreshed.
    """
    def __init__(self, apic):
        threading.Thread.__init__(self)
        self._apic = apic
        self._subscriptions = {}
        self._ws = None
        self._ws_url = None
        self._refresh_time = 45
        self._event_q = Queue()
        self._events = {}
        self._exit = False

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def _send_subscription(self, url):
        """
        Send the subscription for the specified URL.

        :param url: URL string to issue the subscription
        """
        resp = self._apic.get(url)
        resp_data = json.loads(resp.text)
        subscription_id = resp_data['subscriptionId']
        self._subscriptions[url] = subscription_id
        while int(resp_data['totalCount']):
            event = {"totalCount": "1",
                     "subscriptionId": [resp_data['subscriptionId']],
                     "imdata": [resp_data["imdata"][0]]}
            self._event_q.put(json.dumps(event))
            resp_data['totalCount'] = str(int(resp_data['totalCount']) - 1)
            resp_data["imdata"].remove(resp_data["imdata"][0])
        return resp

    def refresh_subscriptions(self):
        """
        Refresh all of the subscriptions.
        """
        for subscription in self._subscriptions:
            subscription_id = self._subscriptions[subscription]
            refresh_url = '/api/subscriptionRefresh.json?id=' + str(subscription_id)
            resp = self._apic.get(refresh_url)

    def _open_web_socket(self, use_secure=True):
        """
        Opens the web socket connection with the APIC.

        :param use_secure: Boolean indicating whether the web socket
                           should be secure.  Default is True.
        """
        sslopt = {}
        if use_secure:
            sslopt['cert_reqs'] = ssl.CERT_NONE
            self._ws_url = 'wss://%s/socket%s' % (self._apic.ipaddr,
                                                  self._apic.token)
        else:
            self._ws_url = 'ws://%s/socket%s' % (self._apic.ipaddr,
                                                 self._apic.token)

        kwargs = {}
        if self._ws is not None:
            if self._ws.connected:
                self._ws.close()
                self.event_handler_thread.exit()
        self._ws = create_connection(self._ws_url, sslopt=sslopt, **kwargs)
        self.event_handler_thread = EventHandler(self)
        self.event_handler_thread.daemon = True
        self.event_handler_thread.start()

    def _resubscribe(self):
        """
        Reissue the subscriptions.
        Used to when the APIC login timeout occurs and a new subscription
        must be issued instead of simply a refresh.  Not meant to be called
        directly by end user applications.
        """
        self._process_event_q()
        urls = []
        for url in self._subscriptions:
            urls.append(url)
        self._subscriptions = {}
        for url in urls:
            self.subscribe(url)

    def _process_event_q(self):
        """
        Put the event into correct bucket based on URLs that have been
        subscribed.
        """
        if self._event_q.empty():
            return

        while not self._event_q.empty():
            event = self._event_q.get()
            event = json.loads(event)
            # Find the URL for this event
            url = None
            for k in self._subscriptions:
                for id in event['subscriptionId']:
                    if self._subscriptions[k] == str(id):
                        url = k
                        break
            if url not in self._events:
                self._events[url] = []
            self._events[url].append(event)

    def subscribe(self, url):
        """
        Subscribe to a particular APIC URL.  Used internally by the
        Class and Instance subscriptions.

        :param url: URL string to send as a subscription
        """
        # Check if already subscribed.  If so, skip
        if url in self._subscriptions:
            return

        if self._ws is not None:
            if not self._ws.connected:
                self._open_web_socket('https://' in url)

        resp = self._send_subscription(url)
        return resp

    def has_events(self, url):
        """
        Check if a particular APIC URL subscription has any events.
        Used internally by the Class and Instance subscriptions.

        :param url: URL string to check for pending events
        """
        self._process_event_q()
        if url not in self._events:
            return False
        result = len(self._events[url]) != 0
        return result

    def get_event(self, url):
        """
        Get an event for a particular APIC URL subscription.
        Used internally by the Class and Instance subscriptions.

        :param url: URL string to get pending event
        """
        if url not in self._events:
            raise ValueError
        event = self._events[url].pop(0)
        return event

    def unsubscribe(self, url):
        """
        Unsubscribe from a particular APIC URL.  Used internally by the
        Class and Instance subscriptions.

        :param url: URL string to unsubscribe
        """
        if url not in self._subscriptions:
            return
        del self._subscriptions[url]
        if not self._subscriptions:
            self._ws.close()

    def run(self):
        while not self._exit:
            # Sleep for some interval and send subscription list
            time.sleep(self._refresh_time)
            self.refresh_subscriptions()


class Session(object):
    """
       Session class
       This class is responsible for all communication with the APIC.
    """
    def __init__(self, url, uid, pwd, verify_ssl=False,
                 subscription_enabled=True):
        """
        :param url:  String containing the APIC URL such as ``https://1.2.3.4``
        :param uid: String containing the username that will be used as\
        part of the  the APIC login credentials.
        :param pwd: String containing the password that will be used as\
        part of the  the APIC login credentials.
        :param verify_ssl:  Used only for SSL connections with the APIC.\
        Indicates whether SSL certificates must be verified.  Possible\
        values are True and False with the default being False.
        """
        if 'https://' in url:
            self.ipaddr = url[len('https://'):]
        else:
            self.ipaddr = url[len('http://'):]
        self.uid = uid
        self.pwd = pwd
        # self.api = 'http://%s:80/api/' % self.ip # 7580
        self.api = url
        self.session = None
        self.verify_ssl = verify_ssl
        self.token = None
        self.login_thread = Login(self)
        self._subscription_enabled = subscription_enabled
        if subscription_enabled:
            self.subscription_thread = Subscriber(self)
            self.subscription_thread.daemon = True
            self.subscription_thread.start()

    def _send_login(self, timeout=None):
        """
        Send the actual login request to the APIC and open the web
        socket interface.
        """
        login_url = self.api + '/api/aaaLogin.json'
        name_pwd = {'aaaUser': {'attributes': {'name': self.uid,
                                               'pwd': self.pwd}}}
        jcred = json.dumps(name_pwd)
        self.session = requests.Session()
        ret = self.session.post(login_url, data=jcred, verify=self.verify_ssl, timeout=timeout)
        if not ret.ok:
            self.login_thread.exit()
            self.subscription_thread.exit()
            return ret
        ret_data = json.loads(ret.text)['imdata'][0]
        timeout = ret_data['aaaLogin']['attributes']['refreshTimeoutSeconds']
        self.token = str(ret_data['aaaLogin']['attributes']['token'])
        if self._subscription_enabled:
            self.subscription_thread._open_web_socket('https://' in self.api)
        timeout = int(timeout)
        if (timeout - TIMEOUT_GRACE_SECONDS) > 0:
            timeout = timeout - TIMEOUT_GRACE_SECONDS
        self.login_thread._login_timeout = timeout
        return ret

    def login(self, timeout=None):
        """
        Initiate login to the APIC.  Opens a communication session with the\
        APIC using the python requests library.

        :returns: Response class instance from the requests library.\
        response.ok is True if login is successful.
        """
        logging.info('Initializing connection to the APIC')
        resp = self._send_login(timeout)
        self.login_thread.daemon = True
        self.login_thread.start()
        return resp

    def close(self):
        self.session.close()

    def subscribe(self, url):
        """
        Subscribe to events for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string to issue subscription
        """
        if self._subscription_enabled:
            resp = self.subscription_thread.subscribe(url)
            return resp

    def resubscribe(self):
        """
        Resubscribe to the current subscriptions.  Used by the login thread after a re-login

        :return: None
        """
        if self._subscription_enabled:
            return self.subscription_thread._resubscribe()

    def has_events(self, url):
        """
        Check if there are events for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string belonging to subscription
        :returns: True or False. True if an event exists for this subscription.
        """
        return self.subscription_thread.has_events(url)

    def get_event(self, url):
        """
        Get an event for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string belonging to subscription
        :returns: Object belonging to the instance or class that the
                  subscription was made.
        """
        return self.subscription_thread.get_event(url)

    def unsubscribe(self, url):
        """
        Unsubscribe from events for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string to remove issue subscription
        """
        if self._subscription_enabled:
            self.subscription_thread.unsubscribe(url)

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
        post_url = self.api + url
        logging.debug('Posting url: %s data: %s', post_url, data)
        resp = self.session.post(post_url, data=json.dumps(data, sort_keys=True))
        logging.debug('Response: %s %s', resp, resp.text)
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
        get_url = self.api + url
        logging.debug(get_url)
        resp = self.session.get(get_url, verify=self.verify_ssl)
        logging.debug(resp)
        logging.debug(resp.text)
        return resp
