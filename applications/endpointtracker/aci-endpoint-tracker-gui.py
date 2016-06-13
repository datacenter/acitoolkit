################################################################################
#                                 _    ____ ___                                #
#                                / \  / ___|_ _|                               #
#                               / _ \| |    | |                                #
#                  _____       / ___ \ |___ | |  _       _                     #
#                 | ____|_ __ /_/_| \_\____|___|(_)_ __ | |_                   #
#                 |  _| | '_ \ / _` | '_ \ / _ \| | '_ \| __|                  #
#                 | |___| | | | (_| | |_) | (_) | | | | | |_                   #
#                 |_____|_|_|_|\__,_| .__/ \___/|_|_| |_|\__|                  #
#                     |_   _| __ __ |_|___| | _____ _ __                       #
#                       | || '__/ _` |/ __| |/ / _ \ '__|                      #
#                       | || | | (_| | (__|   <  __/ |                         #
#                       |_||_|  \__,_|\___|_|\_\___|_|                         #
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
"""
ACI Endpoint Tracker GUI
"""
import socket
from flask import Flask, render_template
try:
    import mysql.connector as mysql
except ImportError:
    import pymysql as mysql
from acitoolkit.acitoolkit import Credentials


def populate_data(mysql_ip, mysql_username, mysql_password):
    """
    Get the data from the MySQL database

    :param mysql_ip: String containing IP address of the MySQL server
    :param mysql_username: String containing username to login to the MySQL server
    :param mysql_password: String containing password to login to the MySQL server
    :return: String containing the data in HTML format
    """
    # Cache lookups to speed things up a bit.
    ipCache = {'0.0.0.0': ''}

    # Create the MySQL database
    cnx = mysql.connect(user=mysql_username, password=mysql_password,
                        host=mysql_ip,
                        database='endpointtracker')
    c = cnx.cursor()
    c.execute('USE endpointtracker;')
    c.execute('SELECT * FROM endpoints;')

    data = ''
    for (mac, ip, tenant, app, epg, interface, timestart, timestop) in c:
        if timestop is None:
            timestop = '0000-00-00 00:00:00'
        data = data + '<tr> <td>' + mac + '</td> '
        if ip not in ipCache:
            try:
                ipCache[ip] = ' [' + socket.gethostbyaddr(ip)[0] + ']'
            except socket.error as error:
                ipCache[ip] = ''
        data = data + '<td>' + ip + ipCache[ip] + '</td> '
        data = data + '<td>' + tenant + '</td> '
        data = data + '<td>' + app + '</td> '
        data = data + '<td>' + epg + '</td> '
        data = data + '<td>' + interface + '</td> '
        data = data + '<td>' + str(timestart) + '</td> '
        data = data + '<td>' + str(timestop) + '</td> '
        data = data + '</tr>'
    return data

app = Flask(__name__)


@app.route('/')
def display_table():
    """
    Display the main search page

    :return: HTML to be displayed
    """
    return render_template('main.html', data=populate_data(args.mysqlip,
                                                           args.mysqllogin,
                                                           args.mysqlpassword))


if __name__ == '__main__':
    description = ('Simple application that logs on to the APIC '
                   'and displays all of the Endpoints.')
    creds = Credentials(['mysql', 'server'], description)
    args = creds.get()

    app.run(debug=False, host=args.ip, port=int(args.port))
