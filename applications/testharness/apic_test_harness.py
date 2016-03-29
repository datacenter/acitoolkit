"""
APIC Test Harness - Provides a Fake APIC running within a Flask Web Server
for test purposes. Can inject errors and create scenarios that normally would
be difficult to generate in a real system.
"""
from os import listdir, getpid
from acitoolkit import FakeSession
import argparse
import sys
import logging
from logging.handlers import RotatingFileHandler
import ConfigParser
from flask import Flask, request, abort
from werkzeug.urls import iri_to_uri
import json
import random
import time

DEFAULT_PORT = '5000'
DEFAULT_IPADDRESS = '127.0.0.1'


class FailureHandler(object):
    """
    Class for creating emulated failure conditions
    """
    def __init__(self):
        self._config = None
        self._timeout_count = 0

    def _check_is_enabled(self, name):
        """
        Check if the specified element is set to enabled
        :param name: String containing the section to check
        :return: True if the specified element is set to enabled. False
                 otherwise
        """
        try:
            return self._config.get(name, 'Status') == 'enabled'
        except (ConfigParser.NoSectionError,
                ConfigParser.NoOptionError,
                AttributeError):
            return False

    def is_delay_enabled(self):
        """
        Check whether the DelayResponses is enabled
        :return: True if DelayResponses is enabled. False otherwise
        """
        return self._check_is_enabled('DelayResponses')

    def is_connection_failure_enabled(self):
        """
        Check whether the ConnectionFailures is enabled
        :return: True if ConnectionFailures is enabled. False otherwise
        """
        return self._check_is_enabled('ConnectionFailures')

    def enforce_delay(self):
        """
        Enforce the delay if deemed necessary.  The delay will be enforced
        if the request is randomly selected based on the PercentageOfRequests
        setting.  The delay will be in seconds based on the DelayInSeconds
        setting.
        :return: None
        """
        if not self.is_delay_enabled():
            return
        try:
            percentage = int(self._config.get('DelayResponses',
                                              'PercentageOfRequests'))
            delay_time = int(self._config.get('DelayResponses',
                                              'DelayInSeconds'))
        except ConfigParser.NoOptionError:
            return
        if percentage == 0:
            return
        if random.randint(1, 100) <= percentage:
            logging.warning('Delaying response by %s seconds...', delay_time)
            time.sleep(delay_time)

    def enforce_connection_failure(self):
        """
        Determines whether connection failure should be enforced. The connection
        failure will be enforced if the request is randomly selected based on
        the PercentageOfRequests setting.
        :return: True if the request should be failed. False otherwise
        """
        if not self.is_connection_failure_enabled():
            return False
        try:
            percentage = int(self._config.get('ConnectionFailures',
                                              'PercentageOfRequests'))
        except ConfigParser.NoOptionError:
            return False
        if percentage != 0 and random.randint(1, 100) <= percentage:
            logging.warning('Connection failure should be enforced...')
            return True
        return False

    def add_config(self, filename):
        """
        Add the configuration file
        :param filename: String containing the name of the configuration file
        """
        if filename is None:
            return
        self._config = ConfigParser.ConfigParser()
        self._config.read(filename)


parser = argparse.ArgumentParser(description='ACI APIC Test Harness Tool')
parser.add_argument('--directory', default=None,
                    help='Directory containing the Snapshot files')
parser.add_argument('--config', default=None,
                    help='Optional .ini file providing failure scenario configuration')
parser.add_argument('--maxlogfiles', type=int, default=10,
                    help='Maximum number of log files (default is 10)')
parser.add_argument('--debug', nargs='?',
                    choices=['verbose', 'warnings', 'critical'],
                    const='critical',
                    help='Enable debug messages.')
parser.add_argument('--ip',
                    default=DEFAULT_IPADDRESS,
                    help='IP address to listen on.')
parser.add_argument('--port',
                    default=DEFAULT_PORT,
                    help='Port number to listen on.')
args = parser.parse_args()

if args.directory is None:
    print '%% No snapshot directory given.'
    sys.exit(0)

if args.debug is not None:
    if args.debug == 'verbose':
        level = logging.DEBUG
    elif args.debug == 'warnings':
        level = logging.WARNING
    else:
        level = logging.CRITICAL
else:
    level = logging.CRITICAL
format_string = '%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s'
log_formatter = logging.Formatter(format_string)
log_file = 'apic_test_harness.%s.log' % str(getpid())
my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5 * 1024 * 1024,
                                 backupCount=args.maxlogfiles,
                                 encoding=None, delay=0)
my_handler.setLevel(level)
my_handler.setFormatter(log_formatter)
logging.getLogger().addHandler(my_handler)
logging.getLogger().setLevel(level)

# Set the directory to the location of the JSON files
directory = args.directory
filenames = [directory + filename for filename in listdir(directory)
             if filename.endswith('.json')]

# Create the session
session = FakeSession(filenames)

# Handle failure scenario configuration
failure_hdlr = FailureHandler()
failure_hdlr.add_config(args.config)

app = Flask(__name__)


@app.route('/', defaults={'path': ''}, methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def handle_get(path):
    """
    Handle the GET
    """
    path = '/api' + iri_to_uri(request.url).partition('/api')[-1]
    if path == '/api':
        abort(400)
    logging.debug('Received %s', path)
    dump = session.get(path)
    logging.debug('From Fake APIC: %s', dump.json())
    response = json.dumps(dump.json(), indent=4, separators=(',', ':'))
    failure_hdlr.enforce_delay()
    if failure_hdlr.enforce_connection_failure():
        abort(400)
    return response


@app.route('/', defaults={'path': ''}, methods=['POST', 'PUT'])
@app.route('/<path:path>', methods=['POST', 'PUT'])
def handle_post(path):
    """
    Handle the POST and PUT
    """
    logging.debug('request url: %s received: %s', path, request.data)
    if not request.data:
        logging.debug('Aborting due to no JSON in the POST')
        abort(400)
    resp = session.push_to_apic('/' + path, request.data)
    if not resp.ok:
        logging.debug('Aborting due to no Response coming back as not ok')
        abort(400)
    logging.debug('Response: %s', resp.json())
    failure_hdlr.enforce_delay()
    if failure_hdlr.enforce_connection_failure():
        abort(400)
    return json.dumps(resp.json(), indent=4, separators=(',', ':'))


if __name__ == '__main__':
    app.run(debug=False, host=args.ip, port=int(args.port))
