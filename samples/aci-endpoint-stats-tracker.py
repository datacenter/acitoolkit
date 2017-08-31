#!/usr/bin/env python
################################################################################
#                 _    ____ ___   _____           _ _    _ _                   #
#                / \  / ___|_ _| |_   _|__   ___ | | | _(_) |_                 #
#               / _ \| |    | |    | |/ _ \ / _ \| | |/ / | __|                #
#              / ___ \ |___ | |    | | (_) | (_) | |   <| | |_                 #
#        ____ /_/   \_\____|___|___|_|\___/ \___/|_|_|\_\_|\__|                #
#       / ___|___   __| | ___  / ___|  __ _ _ __ ___  _ __ | | ___  ___        #
#      | |   / _ \ / _` |/ _ \ \___ \ / _` | '_ ` _ \| '_ \| |/ _ \/ __|       #
#      | |__| (_) | (_| |  __/  ___) | (_| | | | | | | |_) | |  __/\__ \       #
#       \____\___/ \__,_|\___| |____/ \__,_|_| |_| |_| .__/|_|\___||___/       #
#                                                    |_|                       #
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
from acitoolkit import Credentials, Session, InterfaceStats
import mysql.connector

valid_tables = []


def convert_timestamp_to_mysql(timestamp):
    """
    Convert timestamp to the format used in MySQL
    :param timestamp: String containing ACI timestamp
    :return: String containing MySQL timestamp
    """
    (mysql_timestamp, remaining) = timestamp.split('T')
    mysql_timestamp += ' '
    mysql_timestamp = mysql_timestamp + remaining.split('+')[0].split('.')[0]
    return mysql_timestamp


def create_table(c, cnx, table_name, counter_list):
    """
    Create the table in the MySQL database
    :param c:
    :param cnx:
    :param table_name: String containing the table name
    :param counter_list: List of counter names
    :return: None
    """
    command_str = u'CREATE TABLE IF NOT EXISTS {0:s} (interface CHAR(16) NOT NULL'.format(table_name)
    for column_name in counter_list:
        if column_name in ['intervalStart', 'intervalEnd']:
            command_str += ', ' + column_name.lower() + ' TIMESTAMP'
        elif 'rate' in column_name.lower():
            command_str += ', ' + column_name.lower() + ' FLOAT UNSIGNED'
        elif 'cum' in column_name.lower():
            command_str += ', ' + column_name.lower() + ' BIGINT UNSIGNED'
        elif 'bytes' in column_name.lower():
            command_str += ', ' + column_name.lower() + ' BIGINT UNSIGNED'
        else:
            command_str += ', ' + column_name.lower() + ' INT UNSIGNED'
    command_str += ');'

    c.execute(command_str)
    cnx.commit()
    valid_tables.append(table_name)


def insert_stats_row(c, cnx, table, interface_name, stats):
    """this will insert a row of stats in the specified table
    """
    column_names = list(stats.keys())

    if table not in valid_tables:
        create_table(c, cnx, table, column_names)

    command_str = 'INSERT INTO {0:s} ({1:s}'.format(table, 'interface')

    for column in column_names:
        command_str += ', %s' % (column.lower())

    command_str += u") VALUES ('{0:s}'".format(interface_name)

    for column in column_names:
        if column in ['intervalStart', 'intervalEnd']:
            command_str += ", '%s'" % (convert_timestamp_to_mysql(stats[column]))
        else:
            command_str += ", %s" % (stats[column])

    command_str += ')'
    c.execute(command_str)
    cnx.commit()


def interval_end_exists(c, table, interface_name, interval_end):
    sql_interval_end = convert_timestamp_to_mysql(interval_end)
    c.execute("SELECT interface, intervalend FROM %s where intervalend='%s' and interface='%s';" % (
        table, sql_interval_end, interface_name))
    rows = c.fetchall()

    if len(rows) > 0:
        return True
    else:
        return False


def main():
    """
    Main execution routine
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Application that logs on to the APIC and tracks'
                   ' all of the Endpoint stats in a MySQL database.')
    creds = Credentials(qualifier=('apic', 'mysql'),
                        description=description)
    args = creds.get()

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Create the MySQL database
    cnx = mysql.connector.connect(user=args.mysqllogin, password=args.mysqlpassword,
                                  host=args.mysqlip)
    c = cnx.cursor()
    c.execute('CREATE DATABASE IF NOT EXISTS acitoolkit_interface_stats;')
    cnx.commit()
    c.execute('USE acitoolkit_interface_stats;')

    all_stats = InterfaceStats.get_all_ports(session, 1)
    for intf in all_stats:
        stats = all_stats[intf]
        for stats_family in stats:
            if '5min' in stats[stats_family]:
                for epoch in stats[stats_family]['5min']:
                    if epoch != 0:
                        ss = stats[stats_family]['5min'][epoch]
                        if stats_family not in valid_tables:
                            create_table(c, cnx, stats_family, list(ss.keys()))
                        if not interval_end_exists(c, stats_family, intf, ss['intervalEnd']):
                            insert_stats_row(c, cnx, stats_family, intf, ss)

if __name__ == '__main__':
    main()
