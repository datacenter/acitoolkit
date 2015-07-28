from flask import Flask, request, abort, make_response, jsonify
from intersite import execute_tool, parse_args
import json
from flask.ext.httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

collector = execute_tool(parse_args(), test_mode=True)
app = Flask(__name__)


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
    return json.dumps(collector.config.get_config(), indent=4, separators=(',', ':'))


@app.route('/config', methods=['POST', 'PUT'])
@auth.login_required
def set_config():
    if not request.json:
        abort(400)
    resp = collector.save_config(request.json)
    if resp != 'OK':
        abort(400)
    collector.reload_config()
    return json.dumps({'Status': 'OK'}, indent=4, separators=(',', ':'))

if __name__ == '__main__':
    app.run(debug=True)
