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
import copy
import json
import logging
import ssl
import threading
import time
import socket

import requests
try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
except ImportError:
    pass
from six.moves.queue import Queue
from websocket import create_connection, WebSocketException
from requests.exceptions import ConnectionError

try:
    import urllib3
    urllib3.disable_warnings()
except (ImportError, AttributeError):
    pass
else:
    try:
        urllib3.disable_warnings()
    except AttributeError:
        pass


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

    def _check_callbacks(self):
        """
        Invoke the callback functions on a successful relogin
        if there was an error response

        :param resp: Instance of requests.Response
        """
        if self._apic.login_error:
            logging.info('Logged back into the APIC')
            self._apic.login_error = False
            self._apic.invoke_login_callbacks()

    def run(self):
        while not self._exit:
            time.sleep(self._login_timeout)
            try:
                resp = self._apic.refresh_login(timeout=120)
            except ConnectionError:
                logging.error('Could not refresh APIC login due to ConnectionError')
                self._login_timeout = 30
                self._apic.login_error = True
            except requests.exceptions.Timeout:
                logging.error('Could not refresh APIC login due to Timeout')
            else:
                if resp.ok:
                    self._check_callbacks()
                    continue
            try:
                resp = self._apic._send_login()
                self._apic.resubscribe()
                if resp.ok:
                    self._check_callbacks()
            except ConnectionError:
                logging.error('Could not relogin to APIC due to ConnectionError')
                self._apic.login_error = True


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
        self._refresh_time = 30
        self._event_q = Queue()
        self._events = {}
        self._exit = False
        self.event_handler_thread = None

    def exit(self):
        """
        Indicate that the thread should exit.
        """
        self._exit = True

    def _send_subscription(self, url, only_new=False):
        """
        Send the subscription for the specified URL.

        :param url: URL string to issue the subscription
        """
        try:
            resp = self._apic.get(url)
        except ConnectionError:
            self._subscriptions[url] = None
            logging.error('Could not send subscription to APIC for url %s', url)
            resp = requests.Response()
            resp.status_code = 404
            resp._content = '{"error": "Could not send subscription to APIC"}'
            return resp
        if not resp.ok:
            self._subscriptions[url] = None
            logging.error('Could not send subscription to APIC for url %s', url)
            resp = requests.Response()
            resp.status_code = 404
            resp._content = '{"error": "Could not send subscription to APIC"}'
            return resp
        resp_data = json.loads(resp.text)
        subscription_id = resp_data['subscriptionId']
        self._subscriptions[url] = subscription_id
        if not only_new:
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
        # Make a copy of the current subscriptions in case of changes
        # while we are refreshing
        current_subscriptions = {}
        for subscription in self._subscriptions:
            try:
                current_subscriptions[subscription] = self._subscriptions[subscription]
            except KeyError:
                logging.warning('Subscription removed while copying')

        # Refresh the subscriptions
        for subscription in current_subscriptions:
            if self._ws is not None:
                if not self._ws.connected:
                    logging.warning('Websocket not established on subscription refresh. Re-establishing websocket')
                    self._open_web_socket('https://' in subscription)
            try:
                subscription_id = self._subscriptions[subscription]
            except KeyError:
                logging.warning('Subscription has been removed while trying to refresh')
                continue
            if subscription_id is None:
                self._send_subscription(subscription)
                continue
            refresh_url = '/api/subscriptionRefresh.json?id=' + str(subscription_id)
            resp = self._apic.get(refresh_url)
            if not resp.ok:
                logging.warning('Could not refresh subscription: %s', refresh_url)
                # Try to resubscribe
                self._resubscribe()

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
        try:
            self._ws = create_connection(self._ws_url, sslopt=sslopt, **kwargs)
            if not self._ws.connected:
                logging.error('Unable to open websocket connection')
            self.event_handler_thread = EventHandler(self)
            self.event_handler_thread.daemon = True
            self.event_handler_thread.start()
        except WebSocketException:
            logging.error('Unable to open websocket connection due to WebSocketException')
        except socket.error:
            logging.error('Unable to open websocket connection due to Socket Error')

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
            self.subscribe(url, only_new=True)

    def _process_event_q(self):
        """
        Put the event into correct bucket based on URLs that have been
        subscribed.
        """
        if self._event_q.empty():
            return

        while not self._event_q.empty():
            event = self._event_q.get()
            orig_event = event
            try:
                event = json.loads(event)
            except ValueError:
                logging.error('Non-JSON event: %s', orig_event)
                continue
            # Find the URL for this event
            num_subscriptions = len(event['subscriptionId'])
            for i in range(0, num_subscriptions):
                url = None
                for k in self._subscriptions:
                    if self._subscriptions[k] == str(event['subscriptionId'][i]):
                        url = k
                        break
                if url not in self._events:
                    self._events[url] = []
                self._events[url].append(event)
                if num_subscriptions > 1:
                    event = copy.deepcopy(event)

    def subscribe(self, url, only_new=False):
        """
        Subscribe to a particular APIC URL.  Used internally by the
        Class and Instance subscriptions.

        :param url: URL string to send as a subscription
        """
        logging.info('Subscribing to url: %s', url)
        # Check if already subscribed.  If so, skip
        if url in self._subscriptions:
            return

        if self._ws is not None:
            if not self._ws.connected:
                self._open_web_socket('https://' in url)

        resp = self._send_subscription(url, only_new=only_new)
        return resp

    def is_subscribed(self, url):
        """
        Check if subscribed to a particular APIC URL.

        :param url: URL string to send as a subscription
        """
        return url in self._subscriptions

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
        logging.debug('Event received %s', event)
        return event

    def unsubscribe(self, url):
        """
        Unsubscribe from a particular APIC URL.  Used internally by the
        Class and Instance subscriptions.

        :param url: URL string to unsubscribe
        """
        logging.info('Unsubscribing from url: %s', url)
        if url not in self._subscriptions:
            return
        if '&subscription=yes' in url:
            unsubscribe_url = url.split('&subscription=yes')[0] + '&subscription=no'
        elif '?subscription=yes' in url:
            unsubscribe_url = url.split('?subscription=yes')[0] + '?subscription=no'
        else:
            raise ValueError('No subscription string in URL being unsubscribed')
        resp = self._apic.get(unsubscribe_url)
        if not resp.ok:
            logging.warning('Could not unsubscribe from url: %s', unsubscribe_url)
        # Chew up any outstanding events
        while self.has_events(url):
            self.get_event(url)
        del self._subscriptions[url]
        if not self._subscriptions:
            self._ws.close()

    def run(self):
        while not self._exit:
            # Sleep for some interval and send subscription list
            time.sleep(self._refresh_time)
            try:
                self.refresh_subscriptions()
            except ConnectionError:
                logging.error('Could not refresh subscriptions due to ConnectionError')


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
        self._relogin_callbacks = []
        self.login_error = False
        self._logged_in = False
        self._subscription_enabled = subscription_enabled
        if subscription_enabled:
            self.subscription_thread = Subscriber(self)
            self.subscription_thread.daemon = True
            self.subscription_thread.start()

    def __reduce__(self):
        """
        This will enable this class to be pickled by only saving api, uid and pwd when
        pickling.
        :return:
        """
        return self.__class__, (self.api, self.uid, self.pwd)

    def _send_login(self, timeout=None):
        """
        Send the actual login request to the APIC and open the web
        socket interface.
        """
        login_url = '/api/aaaLogin.json'
        name_pwd = {'aaaUser': {'attributes': {'name': self.uid,
                                               'pwd': self.pwd}}}
        if not self.verify_ssl:
            try:
                requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            except AttributeError:
                pass
        self.session = requests.Session()
        ret = self.push_to_apic(login_url, data=name_pwd, timeout=timeout)
        if not ret.ok:
            logging.error('Could not relogin to APIC. Aborting login thread.')
            self.login_thread.exit()
            self.subscription_thread.exit()
            return ret
        self._logged_in = True
        ret_data = json.loads(ret.text)['imdata'][0]
        timeout = ret_data['aaaLogin']['attributes']['refreshTimeoutSeconds']
        self.token = str(ret_data['aaaLogin']['attributes']['token'])
        if self._subscription_enabled:
            self.subscription_thread._open_web_socket('https://' in self.api)
        timeout = int(timeout)
        self.login_thread._login_timeout = timeout / 2
        return ret

    def login(self, timeout=None):
        """
        Initiate login to the APIC.  Opens a communication session with the\
        APIC using the python requests library.

        :returns: Response class instance from the requests library.\
        response.ok is True if login is successful.
        """
        logging.info('Initializing connection to the APIC')
        try:
            resp = self._send_login(timeout)
        except ConnectionError:
            logging.error('Could not relogin to APIC due to ConnectionError')
            resp = requests.Response()
            resp.status_code = 404
            resp._content = '{"error": "Could not relogin to APIC due to ConnectionError"}'
        self.login_thread.daemon = True
        self.login_thread.start()
        return resp

    def logged_in(self):
        """
        Returns whether the session is logged in to the APIC

        :return: True or False. True if the session is logged in to the APIC.
        """
        return self._logged_in and not self.login_error

    def refresh_login(self, timeout=None):
        """
        Refresh the login to the APIC

        :param timeout: Integer containing the number of seconds for connection timeout
        :return: Instance of requests.Response
        """
        refresh_url = '/api/aaaRefresh.json'
        resp = self.get(refresh_url, timeout=timeout)
        return resp

    def close(self):
        """
        Close the session
        """
        self.session.close()

    def subscribe(self, url, only_new=False):
        """
        Subscribe to events for a particular URL.  Used internally by the
        class and instance subscriptions.

        :param url:  URL string to issue subscription
        """
        if self._subscription_enabled:
            resp = self.subscription_thread.subscribe(url, only_new=only_new)
            return resp

    def is_subscribed(self, url):
        """
        Check if subscribed to events for a particular URL.

        :param url:  URL string to issue subscription
        """
        if not self._subscription_enabled:
            return False
        return self.subscription_thread.is_subscribed(url)

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

    def push_to_apic(self, url, data, timeout=None):
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

        resp = self.session.post(post_url, data=json.dumps(data, sort_keys=True), verify=self.verify_ssl, timeout=timeout)
        if resp.status_code == 403:
            logging.error(resp.text)
            logging.error('Trying to login again....')
            resp = self._send_login()
            self.resubscribe()
            logging.error('Trying post again...')
            logging.debug(post_url)
            resp = self.session.post(post_url, data=json.dumps(data, sort_keys=True), verify=self.verify_ssl, timeout=timeout)
        logging.debug('Response: %s %s', resp, resp.text)
        return resp

    def get(self, url, timeout=None):
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

        resp = self.session.get(get_url, timeout=timeout, verify=self.verify_ssl)
        if resp.status_code == 403:
            logging.error(resp.text)
            logging.error('Trying to login again....')
            resp = self._send_login()
            self.resubscribe()
            logging.error('Trying get again...')
            logging.debug(get_url)
            resp = self.session.get(get_url, timeout=timeout, verify=self.verify_ssl)
        logging.debug(resp)
        logging.debug(resp.text)
        return resp

    def register_login_callback(self, callback_fn):
        """
        Register a callback function that will be called when the session performs a
        successful relogin attempt after disconnecting from the APIC.

        :param callback_fn: function to be called
        """
        if callback_fn not in self._relogin_callbacks:
            self._relogin_callbacks.append(callback_fn)

    def deregister_login_callback(self, callback_fn):
        """
        Delete the registration of a callback function that was registered via the
        register_login_callback function.

        :param callback_fn: function to be deregistered
        """
        if callback_fn in self._relogin_callbacks:
            self._relogin_callbacks.remove(callback_fn)

    def invoke_login_callbacks(self):
        """
        Invoke registered callback functions when the session performs a
        successful relogin attempt after disconnecting from the APIC.
        """
        for callback_fn in self._relogin_callbacks:
            callback_fn(self)
