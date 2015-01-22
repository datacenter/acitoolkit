#!/usr/bin/env python
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
"""
Simple application that logs on to the APIC and displays all
of the Endpoints.
"""
import sys
import acitoolkit.acitoolkit as ACI
import mysql.connector

def convert_timestamp_to_mysql(timestamp):
    (ts, remaining) = timestamp.split('T')
    ts = ts + ' '
    ts = ts + remaining.split('+')[0].split('.')[0]
    return ts
    
# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = ('Application that logs on to the APIC and tracks'
               ' all of the Endpoints in a MySQL database.')
creds = ACI.Credentials(qualifier=('apic', 'mysql'),
                        description=description)
args = creds.get()

# Login to APIC
session = ACI.Session(args.url, args.login, args.password)
resp = session.login()
if not resp.ok:
    print '%% Could not login to APIC'
    sys.exit(0)

# Create the MySQL database
cnx = mysql.connector.connect(user=args.mysqllogin, password=args.mysqlpassword,
                              host=args.mysqlip)
c = cnx.cursor()
c.execute('CREATE DATABASE IF NOT EXISTS acitoolkit;')
cnx.commit()
c.execute('USE acitoolkit;')
c.execute('''CREATE TABLE IF NOT EXISTS endpoints (
                mac       CHAR(18) NOT NULL,
                ip        CHAR(16),
                tenant    CHAR(100) NOT NULL,
                app       CHAR(100) NOT NULL,
                epg       CHAR(100) NOT NULL,
                interface CHAR(100) NOT NULL,
                timestart TIMESTAMP NOT NULL,
                timestop  TIMESTAMP);''')
cnx.commit()

# Download all of the Endpoints and store in the database
endpoints = ACI.Endpoint.get(session)
for ep in endpoints:
    epg = ep.get_parent()
    app_profile = epg.get_parent()
    tenant = app_profile.get_parent()
    c.execute("""INSERT INTO endpoints (mac, ip, tenant, app, epg, interface, timestart)
                 VALUES ('%s', '%s', '%s', '%s',
                 '%s', '%s', '%s')""" % (ep.mac, ep.ip,
                                         tenant.name, app_profile.name,
                                         epg.name, ep.if_name,
                                         convert_timestamp_to_mysql(ep.timestamp)))
    cnx.commit()

# Subscribe to live updates and update the database
ACI.Endpoint.subscribe(session)
while True:
    if ACI.Endpoint.has_events(session):
        ep = ACI.Endpoint.get_event(session)
        epg = ep.get_parent()
        app_profile = epg.get_parent()
        tenant = app_profile.get_parent()
        if ep.is_deleted():
            ep.if_name = None
            update_cmd = """UPDATE endpoints SET timestop='%s'
                            WHERE mac='%s' AND tenant='%s' AND
                            timestop='0000-00-00 00:00:00'""" % (convert_timestamp_to_mysql(ep.timestamp),
                                                                 ep.mac,
                                                                 tenant.name)
            c.execute(update_cmd)
        else:
            insert_cmd = """INSERT INTO endpoints (mac, ip, tenant, app, epg, interface, timestart)
                            VALUES ('%s', '%s', '%s', '%s',
                                    '%s', '%s', '%s')""" % (ep.mac, ep.ip,
                                                            tenant.name, app_profile.name,
                                                            epg.name, ep.if_name,
                                                            convert_timestamp_to_mysql(ep.timestamp))
            c.execute(insert_cmd)
        cnx.commit()
