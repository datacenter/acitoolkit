from flask import Flask, request, abort, make_response, jsonify
from inheritance import execute_tool, get_arg_parser
import json
import logging
from flask.ext.httpauth import HTTPBasicAuth

DEFAULT_PORT = '5000'
DEFAULT_IPADDRESS = '127.0.0.1'

auth = HTTPBasicAuth()

parser = get_arg_parser()
parser.add_argument('--ip',
                    default=DEFAULT_IPADDRESS,
                    help='IP address to listen on.')
parser.add_argument('--port',
                    default=DEFAULT_PORT,
                    help='Port number to listen on.')

args = parser.parse_args()
app = Flask(__name__)
tool = execute_tool(args)

@auth.get_password
def get_password(username):
    if username == 'admin':
        return 'acitoolkit'
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)


@app.route('/config', methods=['GET'])
@auth.login_required
def get_config():
    return json.dumps(tool.get_config(), indent=4, separators=(',', ':'))


@app.route('/config', methods=['POST', 'PUT'])
@auth.login_required
def set_config():
    logging.debug('PUT /config request received %s', request.data)
    if not request.json:
        logging.error('Request is not proper json: %s %s %s %s', request, dir(request), request.data, request.content_type)
        abort(400)
    resp = tool.add_config(request.json)
    if resp != 'OK':
        logging.error('Response is not ok')
        abort(400)
    # tool.reload_config()
    return json.dumps({'Status': 'OK'}, indent=4, separators=(',', ':'))

if __name__ == '__main__':
    app.run(debug=False, host=args.ip, port=int(args.port))
