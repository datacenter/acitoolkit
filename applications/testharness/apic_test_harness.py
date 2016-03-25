"""
APIC Test Harness - Provides a Fake APIC running within a Flask Web Server for test purposes.
Can inject errors and create scenarios that normally would be difficult to generate in a real system.
"""
from os import listdir, getpid
from acitoolkit import FakeSession
import argparse
import sys
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, request, abort, make_response, jsonify
from werkzeug.urls import iri_to_uri
import json

DEFAULT_PORT = '5000'
DEFAULT_IPADDRESS = '127.0.0.1'

parser = argparse.ArgumentParser(description='ACI APIC Test Harness Tool')
parser.add_argument('--directory', default=None, help='Directory containing the Snapshot files')
parser.add_argument('--maxlogfiles', type=int, default=10, help='Maximum number of log files (default is 10)')
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
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
log_file = 'apic_test_harness.%s.log' % str(getpid())
my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5 * 1024 * 1024,
                                 backupCount=args.maxlogfiles, encoding=None, delay=0)
my_handler.setLevel(level)
my_handler.setFormatter(log_formatter)
logging.getLogger().addHandler(my_handler)
logging.getLogger().setLevel(level)

# Set the directory to the location of the JSON files
directory = args.directory
filenames = [directory + file for file in listdir(directory)
             if file.endswith('.json')]

# Create the session
session = FakeSession(filenames)

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def handle_get(path):
    path = '/api' + iri_to_uri(request.url).partition('/api')[-1]
    if path == '/api':
        abort(400)
    logging.debug('Received %s', path)
    dump = session.get(path)
    logging.debug('From Fake APIC: %s', dump.json())
    response = json.dumps(dump.json(), indent=4, separators=(',', ':'))
    return response


@app.route('/', defaults={'path': ''}, methods=['POST', 'PUT'])
@app.route('/<path:path>', methods=['POST', 'PUT'])
def handle_post(path):
    logging.debug('request url: %s received: %s', path, request.data)
    if not request.data:
        logging.debug('Aborting due to no JSON in the POST')
        abort(400)
    resp = session.push_to_apic('/' + path, request.data)
    if not resp.ok:
        logging.debug('Aborting due to no Response coming back as not ok')
        abort(400)
    logging.debug('Response: %s', resp.json())
    return json.dumps(resp.json(), indent=4, separators=(',', ':'))


if __name__ == '__main__':
    app.run(debug=False, host=args.ip, port=int(args.port))
