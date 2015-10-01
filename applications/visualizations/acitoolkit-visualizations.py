################################################################################
#                  _    ____ ___   _____           _ _    _ _                  #
#                 / \  / ___|_ _| |_   _|__   ___ | | | _(_) |_                #
#                / _ \| |    | |    | |/ _ \ / _ \| | |/ / | __|               #
#               / ___ \ |___ | |    | | (_) | (_) | |   <| | |_                #
#        __    /_/_  \_\____|___|   |_|\___/ \___/|_|_|\_\_|\__|               #
#        \ \   / (_)___ _   _  __ _| (_)______ _| |_(_) ___  _ __  ___         #
#         \ \ / /| / __| | | |/ _` | | |_  / _` | __| |/ _ \| '_ \/ __|        #
#          \ V / | \__ \ |_| | (_| | | |/ / (_| | |_| | (_) | | | \__ \        #
#           \_/  |_|___/\__,_|\__,_|_|_/___\__,_|\__|_|\___/|_| |_|___/        #
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
import flask
from acitoolkitvisualizationslib import *
from acitoolkit.acitoolkitlib import Credentials

description = 'Simple set of visualization examples.'
#creds = Credentials(('mysql'), description)
creds = Credentials(['mysql', 'server'], description)
args = creds.get()

app = flask.Flask(__name__)


@app.route('/')
def index():
    """ Displays the index page accessible at '/'
    """
    return flask.render_template('index.html')


@app.route('/pie')
def endpoint_tracker_pie():
    regenerate_pie_data(args.mysqllogin, args.mysqlpassword, args.mysqlip)
    return flask.render_template('endpoint-tracker-pie.html',
                                 filename='endpoint_tracker_pie.csv')


@app.route('/force')
def endpoint_location_force():
    return flask.render_template('endpoint-force.html')


@app.route('/hierarchical')
def endpoint_hierarchical():
    return flask.render_template('endpoint-hierarchical-edge-bundling.html')


@app.route('/radial')
def endpoint_radial():
    regenerate_radial_data(args.mysqllogin, args.mysqlpassword, args.mysqlip)
    return flask.render_template('endpoint-radial.html')


@app.route('/sunburst')
def endpoint_sunburst():
    regenerate_sunburst_data(args.mysqllogin, args.mysqlpassword, args.mysqlip)
    return flask.render_template('endpoint-sunburst.html')


@app.route('/tree')
def endpoint_epg_tree():
    data = regenerate_endpoint_epg_tree(args.mysqllogin, args.mysqlpassword,
                                        args.mysqlip)
    return flask.render_template('endpoint-tree.html', data=data)


if __name__ == '__main__':
    #app.run(debug=True)
    app.run(debug=False, host=args.ip, port=int(args.port))
