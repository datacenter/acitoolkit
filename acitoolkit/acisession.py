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
"""  This module contains the Session class that controls communication
     with the APIC.
"""
import logging
import json
import requests
import threading
import time
from websocket import create_connection, WebSocketConnectionClosedException
import websocket
from Queue import Queue
import ssl

# Time before login timer expiration to send refresh
TIMEOUT_GRACE_SECONDS = 10


class Login(threading.Thread):
    def __init__(self, apic):
        threading.Thread.__init__(self)
        self._apic = apic
        self._login_timeout = 0

    def run(self):
        while True:
            time.sleep(self._login_timeout)
            print 'Login timer expired.  Sending new login'
            resp = self._apic._send_login()
            self._apic.subscription_thread._resubscribe()


class EventHandler(threading.Thread):
    def __init__(self, subscriber):
        threading.Thread.__init__(self)
        self.subscriber = subscriber
        self._exit = False

    def exit(self):
        self._exit = True

    def run(self):
        while not self._exit:
            try:
                event = self.subscriber._ws.recv()
            except:
                break
            print 'Putting event into Q...'
            print 'Event:', event
            self.subscriber._event_q.put(event)


class Subscriber(threading.Thread):
    def __init__(self, apic):
        threading.Thread.__init__(self)
        self._apic = apic
        self._subscriptions = {}
        self._ws = None
        self._ws_url = None
        self._refresh_time = 15
        self._event_q = Queue()
        self._events = {}

    def _send_subscription(self, url):
        print 'Sending subscription:', url
        resp = self._apic.get(url)
        subscription_id = json.loads(resp.text)['subscriptionId']
        print 'Subscription id returned :', subscription_id
        self._subscriptions[url] = subscription_id
        return resp

    def refresh_subscriptions(self):
        print 'refresh_subscriptions called'
        for subscription in self._subscriptions:
            subscription_id = self._subscriptions[subscription]
            refresh_url = '/api/subscriptionRefresh.json?id=' + subscription_id
            resp = self._apic.get(refresh_url)
            print 'Refresh being sent...'
            print resp, resp.text

    def _open_web_socket(self):
        sslopt = {}
        sslopt['cert_reqs'] = ssl.CERT_NONE
        self._ws_url = 'wss://%s/socket%s' % (self._apic.ipaddr,
                                              self._apic.token)
        kwargs = {}
        if self._ws is not None:
            if self._ws.connected:
                print 'Closing old websocket...'
                self._ws.close()
                self.event_handler_thread.exit()
        print 'Opening websocket....'
        self._ws = create_connection(self._ws_url, sslopt=sslopt, **kwargs)
        self.event_handler_thread = EventHandler(self)
        self.event_handler_thread.daemon = True
        self.event_handler_thread.start()

    def _resubscribe(self):
        print 'Resubscribing...'
        self._process_event_q()
        urls = []
        for url in self._subscriptions:
            urls.append(url)
        self._subscriptions = {}
        for url in urls:
            self.subscribe(url)

    def _process_event_q(self):
        print 'processing event q'
        while not self._event_q.empty():
            event = json.loads(self._event_q.get())
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

        # Dump the events
        for k in self._events:
            print 'EVENT URL:', k
            for i in self._events[k]:
                print 'EVENT:', i

    def subscribe(self, url):
        # Check if already subscribed.  If so, skip
        if url in self._subscriptions:
            return

        if self._ws is not None:
            if not self._ws.connected:
                self._open_web_socket()

        return self._send_subscription(url)

    def unsubscribe(self, url):
        if url not in self._subscriptions:
            return
        del self._subscriptions[url]
        if not self._subscriptions:
            self._ws.close()

    def run(self):
        while True:
            # Sleep for some interval (60sec) and send subscription list
            time.sleep(self._refresh_time)
            print 'Timer expired.  Sending subscriptions'
            self.refresh_subscriptions()


class Session(object):
    """
       Session class
       This class is responsible for all communication with the APIC.
    """
    def __init__(self, url, uid, pwd, verify_ssl=False):
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
        self.subscription_thread = Subscriber(self)
        self.subscription_thread.daemon = True
        self.subscription_thread.start()

    def _send_login(self):
        print 'Sending login'
        login_url = self.api + '/api/aaaLogin.json'
        name_pwd = {'aaaUser': {'attributes': {'name': self.uid,
                                               'pwd': self.pwd}}}
        jcred = json.dumps(name_pwd)
        self.session = requests.Session()
        ret = self.session.post(login_url, data=jcred, verify=self.verify_ssl)
        ret_data = json.loads(ret.text)['imdata'][0]
        timeout = ret_data['aaaLogin']['attributes']['refreshTimeoutSeconds']
        self.token = str(ret_data['aaaLogin']['attributes']['token'])
        self.subscription_thread._open_web_socket()
        timeout = int(timeout)
        if (timeout - TIMEOUT_GRACE_SECONDS) > 0:
            timeout = timeout - TIMEOUT_GRACE_SECONDS
        self.login_thread._login_timeout = timeout
        self.login_thread._login_timeout = 30
        return ret

    def login(self):
        """
        Initiate login to the APIC.  Opens a communication session with the\
        APIC using the python requests library.

        :returns: Response class instance from the requests library.\
        response.ok is True if login is successful.
        """
        logging.info('Initializing connection to the APIC')
        resp = self._send_login()
        self.login_thread.daemon = True
        self.login_thread.start()
        return resp

    def subscribe(self, url):
        self.subscription_thread.subscribe(url)

    def unsubscribe(self, url):
        self.subscription_thread.unsubscribe(url)

    def has_event(self, url):
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
        post_url = self.api + url
        logging.debug('Posting url: %s data: %s', post_url, data)
        resp = self.session.post(post_url, data=json.dumps(data))
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
        resp = self.session.get(get_url)
        logging.debug(resp)
        logging.debug(resp.text)
        return resp
