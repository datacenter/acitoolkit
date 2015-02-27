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
This application will read all of the historical 5min interface stats in the
most recent interface, i.e. in the last 5 minutes, and put it into the
MySQL database specified at the command line.

This script should be run every 5 minutes, minus some seconds, e.g. 10, to compensate for
clock skews, in order to record all of the stats data.

Possible Enhancements:
 A possible enhancement is to check the timestamp of the most recent
 entry in the database before reading the stats.  If it is more than
 5+ minutes ago, then read enough of the historical stats to cover the
 gap.  For example, if the last record was 30minutes old, then read
 the most recent 6 periods of 5min data to bring the database up to
 date without any gaps.
"""
import sys
import acitoolkit.acitoolkit as ACI
from acicounters import InterfaceStats
import mysql.connector

def convert_timestamp_to_mysql(timestamp):
    (ts, remaining) = timestamp.split('T')
    ts = ts + ' '
    ts = ts + remaining.split('+')[0].split('.')[0]
    return ts
    
# Take login credentials from the command line if provided
# Otherwise, take them from your environment variables file ~/.profile
description = ('Application that logs on to the APIC and tracks'
               ' all of the Endpoint stats in a MySQL database.')
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
c.execute('CREATE DATABASE IF NOT EXISTS acitoolkit_interface_stats;')
cnx.commit()
c.execute('USE acitoolkit_interface_stats;')
validTables = []

def createTable(tableName, counterList) :
    commandStr = 'CREATE TABLE IF NOT EXISTS %s (interface CHAR(16) NOT NULL' % (tableName)
    for columnName in counterList :
        if columnName in ['intervalStart', 'intervalEnd'] :
            commandStr += ', '+columnName.lower() + ' TIMESTAMP'
        elif 'rate' in columnName.lower() :
            commandStr += ', '+columnName.lower() + ' FLOAT UNSIGNED'
        elif 'cum' in columnName.lower() :
            commandStr += ', '+columnName.lower() + ' BIGINT UNSIGNED'
        elif 'bytes' in columnName.lower() :
            commandStr += ', '+columnName.lower() + ' BIGINT UNSIGNED'
        else :
            commandStr += ', '+columnName.lower() + ' INT UNSIGNED'
    commandStr +=');'

    c.execute(commandStr)
    cnx.commit()
    validTables.append(tableName)

def insertStatsRow(table, interfaceName, stats) :
    """this will insert a row of stats in the specified table
    """
    columnNames = list(stats.keys())
    
    if table not in validTables :
        createTable(table, columnNames)
        
    commandStr = 'INSERT INTO %s (%s' % (table, 'interface')

    for column in columnNames :
        commandStr += ', %s' % (column.lower())
    
    commandStr += ") VALUES ('%s'" % (interfaceName)

    for column in columnNames :
        if column in ['intervalStart','intervalEnd'] :
            commandStr += ", '%s'" % (convert_timestamp_to_mysql(stats[column]))
        else :
            commandStr += ", %s" % (stats[column])

    commandStr += ')'
    c.execute(commandStr)
    cnx.commit()

def intervalEndExists(table, interfaceName, intervalEnd) :
    sql_intervalEnd = convert_timestamp_to_mysql(intervalEnd)
    c.execute("SELECT interface, intervalend FROM %s where intervalend='%s' and interface='%s';" % (table, sql_intervalEnd, interfaceName))
    rows = c.fetchall()

    if len(rows) > 0 :
        return True
    else :
        return False

all_stats = InterfaceStats.get_all_ports(session,1)
for intf in all_stats :
    stats = all_stats[intf]
    for statsFamily in stats :
        if '5min' in stats[statsFamily] :
            for epoch in stats[statsFamily]['5min'] :
                if epoch != 0 :
                    ss = stats[statsFamily]['5min'][epoch]
                    if not intervalEndExists(statsFamily, intf, ss['intervalEnd']) :
                        insertStatsRow(statsFamily, intf, ss)
    
