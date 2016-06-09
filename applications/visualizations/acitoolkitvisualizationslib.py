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
try:
    import mysql.connector as mysql
except ImportError:
    import pymysql as mysql
import json


def regenerate_pie_data(MYSQL_USERID, MYSQL_PASSWORD, MYSQL_IP):
    cnx = mysql.connect(user=MYSQL_USERID, password=MYSQL_PASSWORD,
                        host=MYSQL_IP)
    c = cnx.cursor()
    c.execute('USE endpointtracker;')
    c.execute("SELECT DISTINCT(tenant) FROM endpoints;")

    tenants = []
    for (tenant) in c:
        tenants.append(tenant[0])

    data = []
    data.append('tenant,endpoints')
    for tenant in tenants:
        line = ''
        c.execute("SELECT COUNT(*) FROM endpoints WHERE tenant='%s';" % tenant)
        for count in c:
            line = tenant + ',' + str(count[0])
        data.append(line)

    f = open('static/endpoint_tracker_pie.csv', 'w')
    for line in data:
        f.write(line + '\n')
    f.close()


def regenerate_radial_data(MYSQL_USERID, MYSQL_PASSWORD, MYSQL_IP):
    def get_json_from_data(item, children):
        children_json = []
        for child in children:
            children_json.append(get_json_from_data(child, children[child]))
        resp = {'name': item, 'children': children_json}
        return resp

    def get_data_from_db():
        cnx = mysql.connect(user=MYSQL_USERID,
                            password=MYSQL_PASSWORD,
                            host=MYSQL_IP)
        c = cnx.cursor()
        c.execute('USE endpointtracker;')
        c.execute("SELECT DISTINCT(tenant) FROM endpoints;")

        tenants = {}
        for (tenant) in c:
            tenants[str(tenant[0])] = {}

        for tenant in tenants:
            c.execute("""SELECT DISTINCT(app) FROM endpoints
                         WHERE tenant='%s';""" % tenant)
            for (app) in c:
                tenants[tenant][str(app[0])] = {}

        for tenant in tenants:
            for app in tenants[tenant]:
                c.execute("""SELECT DISTINCT(epg) FROM endpoints
                             WHERE tenant='%s' AND app='%s';""" % (tenant,
                                                                   app))
                for (epg) in c:
                    tenants[tenant][app][str(epg[0])] = {}

        for tenant in tenants:
            for app in tenants[tenant]:
                for epg in tenants[tenant][app]:
                    c.execute("""SELECT mac FROM endpoints
                                 WHERE tenant='%s' AND app='%s'
                                 AND epg = '%s';""" % (tenant, app, epg))
                    for (mac) in c:
                        tenants[tenant][app][epg][str(mac[0])] = {}
        return tenants

    tenants = get_data_from_db()
    data = []
    for tenant in tenants:
        data.append(get_json_from_data(tenant, tenants[tenant]))
    data = {'name': 'Root', 'children': data}

    f = open('static/endpoint_radial.json', 'w')
    data = json.dumps(data)
    f.write(data)
    f.close()


def regenerate_sunburst_data(MYSQL_USERID, MYSQL_PASSWORD, MYSQL_IP):
    cnx = mysql.connect(user=MYSQL_USERID, password=MYSQL_PASSWORD,
                        host=MYSQL_IP,
                        database='endpointtracker')
    c = cnx.cursor()
    c.execute('USE endpointtracker;')
    query = """select distinct mac,ip,tenant,app,epg from endpoints;"""
    c.execute(query)

    endpoints = {}
    for (mac, ip, tenant, app, epg) in c:
        if tenant not in endpoints:
            endpoints[tenant] = {}
        if app not in endpoints[tenant]:
            endpoints[tenant][app] = {}
        if epg not in endpoints[tenant][app]:
            endpoints[tenant][app][epg] = []
        if ip == '0.0.0.0':
            endpoints[tenant][app][epg].append(mac)
        else:
            endpoints[tenant][app][epg].append(ip)

    f = open('static/sunburst.json', 'w')
    f.write('{"name": "root", "children":[')
    num_tenants = len(endpoints)
    for tenant in endpoints:
        num_tenants = num_tenants - 1
        f.write('{"name": "%s", "children":[' % tenant)
        num_apps = len(endpoints[tenant])
        for app in endpoints[tenant]:
            num_apps = num_apps - 1
            f.write('{"name": "%s", "children":[' % app)
            num_epgs = len(endpoints[tenant][app])
            for epg in endpoints[tenant][app]:
                num_epgs = num_epgs - 1
                f.write('{"name": "%s", "children":[' % epg)
                num_macs = len(endpoints[tenant][app][epg])
                for mac in endpoints[tenant][app][epg]:
                    num_macs = num_macs - 1
                    f.write('{"name": "%s", "size": 3000}' % mac)
                    if num_macs != 0:
                        f.write(',')
                f.write(']}')
                if num_epgs != 0:
                    f.write(',')
            f.write(']}')
            if num_apps != 0:
                f.write(',')
        f.write(']}')
        if num_tenants != 0:
            f.write(',')
    f.write(']}')


def regenerate_endpoint_epg_tree(MYSQL_USERID, MYSQL_PASSWORD, MYSQL_IP):
    def get_json_from_data(item, children):
        children_json = []
        for child in children:
            children_json.append(get_json_from_data(child, children[child]))
        return {'name': item, 'children': children_json}

    def get_data_from_db():
        cnx = mysql.connect(user=MYSQL_USERID,
                            password=MYSQL_PASSWORD,
                            host=MYSQL_IP)
        c = cnx.cursor()
        c.execute('USE endpointtracker;')
        c.execute("SELECT DISTINCT(tenant) FROM endpoints;")

        tenants = {}
        for (tenant) in c:
            tenants[str(tenant[0])] = {}

        for tenant in tenants:
            c.execute("""SELECT DISTINCT(app) FROM endpoints
                         WHERE tenant='%s';""" % tenant)
            for (app) in c:
                tenants[tenant][str(app[0])] = {}

        for tenant in tenants:
            for app in tenants[tenant]:
                c.execute("""SELECT DISTINCT(epg) FROM endpoints
                             WHERE tenant='%s' AND app='%s';""" % (tenant,
                                                                   app))
                for (epg) in c:
                    tenants[tenant][app][str(epg[0])] = {}

        for tenant in tenants:
            for app in tenants[tenant]:
                for epg in tenants[tenant][app]:
                    c.execute("""SELECT mac FROM endpoints WHERE tenant='%s' AND
                                 app='%s' AND epg = '%s';""" % (tenant,
                                                                app,
                                                                epg))
                    for (mac) in c:
                        tenants[tenant][app][epg][str(mac[0])] = {}
        return tenants

    tenants = get_data_from_db()
    data = []
    for tenant in tenants:
        data.append(get_json_from_data(tenant, tenants[tenant]))
    data = [{'name': 'Root', 'children': data}]
    return data
