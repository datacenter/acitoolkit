"""  This module contains the Session class that controls communication
     with the APIC.
"""
import logging
import json
import requests


class Session(object):
    """Session class
       This class contains the connectivity information for talking to the
       APIC.
    """
    def __init__(self, ipaddr, uid, pwd):
        self.ipaddr = ipaddr
        self.uid = uid
        self.pwd = pwd
        # self.api = 'http://%s:80/api/' % self.ip # 7580
        self.api = ipaddr
        self.session = None

    def login(self):
        """Login to the APIC"""
        logging.info('Initializing connection to the APIC')
        login_url = self.api + '/api/aaaLogin.json'
        name_pwd = {'aaaUser': {'attributes': {'name': self.uid,
                                               'pwd': self.pwd}}}
        jcred = json.dumps(name_pwd)
        self.session = requests.Session()
        ret = self.session.post(login_url, data=jcred)
        return ret

    def push_to_apic(self, url, data):
        """Push the object to the APIC"""
        post_url = self.api + url
        logging.debug('Posting url: %s data: %s', post_url, data)
        resp = self.session.post(post_url, data=json.dumps(data))
        logging.debug('Response: %s %s', resp, resp.text)
        return resp

    def get(self, url):
        """Perform a REST GET call to the APIC."""
        get_url = self.api + url
        logging.debug(get_url)
        resp = self.session.get(get_url)
        logging.debug(resp)
        logging.debug(resp.text)
        return resp
