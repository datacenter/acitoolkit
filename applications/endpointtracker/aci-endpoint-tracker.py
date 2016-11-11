#!/usr/bin/env python
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
Simple application that logs on to the APIC and displays all
of the Endpoints.
"""
import sys
import acitoolkit.acitoolkit as aci
import warnings
import re
import os
import logging
import time
from daemon import Daemon

try:
    import mysql.connector as mysql
except ImportError:
    import pymysql as mysql


def touch(fname, times=None):
    """ Touch file """
    with open(fname, 'a'):
        os.utime(fname, times)


def convert_timestamp_to_mysql(timestamp):
    """
    Convert timestamp to correct format for MySQL

    :param timestamp: string containing timestamp in APIC format
    :return: string containing timestamp in MySQL format
    """
    (resp_ts, remaining) = timestamp.split('T')
    resp_ts += ' '
    resp_ts = resp_ts + remaining.split('+')[0].split('.')[0]
    return resp_ts


def connect_mysql(args):
    """
    Connect to the MySQL database
    :param args: command line arguments
    :return: tuple of c, cnx
    """
    # Create the MySQL database
    cnx = mysql.connect(user=args.mysqllogin,
                        password=args.mysqlpassword,
                        host=args.mysqlip)
    if args.daemon:
        logging.info("Connecting to mysql database")
    c = cnx.cursor()

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore')
        c.execute('CREATE DATABASE IF NOT EXISTS endpointtracker;')
        cnx.commit()
    c.execute('USE endpointtracker;')
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore')
        c.execute('''CREATE TABLE IF NOT EXISTS endpoints (
                         mac       CHAR(18) NOT NULL,
                         ip        CHAR(16),
                         tenant    CHAR(100) NOT NULL,
                         app       CHAR(100) NOT NULL,
                         epg       CHAR(100) NOT NULL,
                         interface CHAR(100) NOT NULL,
                         timestart TIMESTAMP NOT NULL,
                         timestop  TIMESTAMP NULL);''')
        cnx.commit()

    return c, cnx


def tracker(args):
    """
    Main Endpoint tracker
    :param args: command line arguments
    :return: None
    """
    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        sys.exit(0)

    c, cnx = connect_mysql(args)

    # Download all of the Endpoints and store in the database
    endpoints = aci.Endpoint.get(session)
    for ep in endpoints:
        try:
            epg = ep.get_parent()
        except AttributeError:
            continue
        app_profile = epg.get_parent()
        tenant = app_profile.get_parent()
        if ep.if_dn:
            for dn in ep.if_dn:
                match = re.match('protpaths-(\d+)-(\d+)', dn.split('/')[2])
                if match:
                    if match.group(1) and match.group(2):
                        int_name = "Nodes: " + match.group(1) + "-" + match.group(2) + " " + ep.if_name
        else:
            int_name = ep.if_name

        try:
            data = (ep.mac, ep.ip, tenant.name, app_profile.name, epg.name,
                    ep.if_name, convert_timestamp_to_mysql(ep.timestamp))
        except ValueError, e:
            if args.daemon:
                logging.info(e)
            continue

        ep_exists = c.execute("""SELECT * FROM endpoints
                                 WHERE mac="%s"
                                 AND
                                 timestop is null;""" % ep.mac)
        c.fetchall()
        if not ep_exists:
            c.execute("""INSERT INTO endpoints (mac, ip, tenant,
                         app, epg, interface, timestart)
                         VALUES ('%s', '%s', '%s', '%s',
                         '%s', '%s', '%s')""" % data)
            cnx.commit()

    # Subscribe to live updates and update the database
    sys.stdout.write("Starting subscribe to apic events")
    aci.Endpoint.subscribe(session)
    while True:
        if aci.Endpoint.has_events(session):
            ep = aci.Endpoint.get_event(session)
            try:
                epg = ep.get_parent()
            except AttributeError:
                continue
            app_profile = epg.get_parent()
            tenant = app_profile.get_parent()
            if ep.is_deleted():
                ep.if_name = None
                data = (convert_timestamp_to_mysql(ep.timestamp),
                        ep.mac,
                        tenant.name)
                update_cmd = """UPDATE endpoints SET timestop='%s',
                                timestart=timestart
                                WHERE mac='%s' AND tenant='%s' AND
                                timestop is null""" % data
                c.execute(update_cmd)
            else:
                if ep.if_dn:
                    for dn in ep.if_dn:
                        match = re.match('protpaths-(\d+)-(\d+)', dn.split('/')[2])
                        if match:
                            if match.group(1) and match.group(2):
                                int_name = "Nodes: " + match.group(1) + "-" + match.group(2) + " " + ep.if_name
                                pass
                else:
                    int_name = ep.if_name

                data = (ep.mac, ep.ip, tenant.name, app_profile.name, epg.name,
                        int_name, convert_timestamp_to_mysql(ep.timestamp))
                insert_data = "'%s', '%s', '%s', '%s', '%s', '%s', '%s'" % data
                query_data = ("mac='%s', ip='%s', tenant='%s', "
                              "app='%s', epg='%s', interface='%s', "
                              "timestart='%s'" % data).replace(',', ' AND')
                select_cmd = """SELECT COUNT(*) FROM endpoints
                                WHERE %s""" % query_data
                c.execute(select_cmd)
                for count in c:
                    if not count[0]:
                        insert_cmd = """INSERT INTO endpoints (mac, ip,
                                        tenant, app, epg, interface,
                                        timestart)
                                        VALUES (%s)""" % insert_data
                        c.execute(insert_cmd)
            cnx.commit()
        # Sleep or else the endpointtracker will take 100% cpu
        time.sleep(0.1)


class Daemonize(Daemon):
    """
    Daemonize the endpointtracker
    Creates a daemon and then runs the tracker function
    """
    def __init__(self,
                 args,
                 pidfile,
                 stdin='/var/log/endpointtracker.log',
                 stdout='/var/log/endpointtracker.log',
                 stderr='/var/log/endpointtracker.log'
                 ):
        self.args = args
        if not os.path.isfile(stdout):
            touch(stdout)

        super(Daemonize, self).__init__(pidfile, stdin, stdout, stderr)

    def run(self):
        """If --daemon is set we run the tracker function
        """
        logging.basicConfig(filename='/var/log/endpointtracker.log',
                            level=logging.INFO,
                            format=('%(asctime)s %(message)s'))
        logging.info('Starting endpointtracker')
        while True:
            try:
                tracker(self.args)
            except mysql.err.OperationalError:
                logging.info("Lost connection to database, reconnecting in 10")
                time.sleep(10)


def main():
    """
    Main Endpoint Tracker routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Application that logs on to the APIC and tracks'
                   ' all of the Endpoints in a MySQL database.')
    creds = aci.Credentials(qualifier=('apic', 'mysql', 'daemon'),
                            description=description)
    args = creds.get()

    if args.daemon or args.kill or args.restart:
        args.daemon = True
        pid = '/var/run/endpointtracker.pid'
        daemon = Daemonize(args, pid)

    if args.kill:
        daemon.stop()
    elif args.restart:
        daemon.restart()
    elif args.daemon:
        daemon.start()
    else:
        tracker(args)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
