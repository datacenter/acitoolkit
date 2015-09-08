from collections import namedtuple
import datetime
import json
import logging
import threading
import sqlite3
import sys

from requests.packages.urllib3 import disable_warnings
from flask import request
from werkzeug.contrib.atom import AtomFeed
from flask import Flask, render_template
from acitoolkit import (
    AppProfile, BridgeDomain, Context, Contract, Credentials, Endpoint, EPG,
    Session, Tenant
)


disable_warnings()
app = Flask(__name__)
logger = logging.getLogger('feed')
feed = cursor = None


def _get_db():
    """Get a handle to the SQLite3 datbase specified in the Configuration file"""
    conn = sqlite3.connect(feed.cfg['events_db'], detect_types=sqlite3.PARSE_DECLTYPES)
    return conn


def _get_query_filters(flask_request, limiter):
    """ Take a HTTP request and limiter keyword (i.e. day, week, etc..) and build
        a 3 item tuple that is used in the SELECT query. Missing values are filled
        in via a lookup to the configuration dictionary.
    """

    maxage, maxcount = _get_request_args(flask_request.args)
    timestamp_limit = datetime.datetime(1970, 1, 1, 0, 0, 0, 0)

    if limiter:
        limiter = limiter.lower()

    if limiter not in ['day', 'week', 'month', 'year', 'custom', None]:
        raise ValueError('Did not parse a legible limiter')

    if limiter:
        if limiter == 'day':
            timestamp_limit = datetime.datetime.now() - datetime.timedelta(days=1)
        elif limiter == 'week':
            timestamp_limit = datetime.datetime.now() - datetime.timedelta(weeks=1)
        elif limiter == 'month':
            timestamp_limit = datetime.datetime.now() - datetime.timedelta(weeks=4)
        elif limiter == 'year':
            timestamp_limit = datetime.datetime.now() - datetime.timedelta(weeks=52)
        else:
            timestamp_limit = datetime.datetime.now() - datetime.timedelta(days=maxage)

    return timestamp_limit, maxage, maxcount


def _produce_feed(atom_feed, events):
    """Populate the atom_feed object with a list of ACI events"""
    for event in events:
        cls, name, timestamp, json_dump, url = event

        atom_feed.add(cls, content=json_dump,
                      content_type='text',
                      author=name,
                      id=name,
                      updated=timestamp)


def _get_request_args(args):
    """
        Build a tuple of the maximum age an event can be plus the maximum amount
        of records to return in the SQL query.

        If no argument is provided, or the value is uncastable to an int the
        respective default value or 360 and 1000 will be returned.
    """
    try:
        maxage = int(args.get('maxage', 360))
    except ValueError:
        maxage = 360

    try:
        maxcount = int(args.get('maxcount', 1000))
    except ValueError:
        maxcount = 1000

    return maxage, maxcount


class EventMonitor(threading.Thread):
    """
        EventMonitor subscribes to Managed Object Classes on
        the APIC.

        Whenever an update is received a copy of the object
        plus supporting metadata is inserted into the DB
    """

    def __init__(self, url, login, password):
        super(EventMonitor, self).__init__()
        self.url = url
        self.login = login
        self.password = password
        self.daemon = True

    def run(self):
        """
            Spin a seperate thread off to sit in the background
            monitoring APIC MOs. The heavy lifting is done via
            the ACI Toolkit that implements a Websocket connection
            to listen for events pushed by the APIC.
        """
        evnt_logger = logging.getLogger('monitor')
        stdout = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stdout.setFormatter(formatter)
        evnt_logger.addHandler(stdout)
        evnt_logger.info('Starting Thread')
        evnt_logger.info('Getting DB Connection')
        try:
            conn = _get_db()
        except sqlite3.Error as e:
            evnt_logger.critical('Could not get handle to DB: %s', e.message)
            sys.exit(1)

        # Create table
        evnt_cursor = conn.cursor()
        try:
            evnt_cursor.execute(
                '''CREATE TABLE IF NOT EXISTS events (cls TEXT, name TEXT, timestamp timestamp, json TEXT, url TEXT)''')
            evnt_cursor.execute(
                '''CREATE INDEX IF NOT EXISTS datetime_index ON events (timestamp DESC)''')
            conn.commit()
        except sqlite3.OperationalError:
            evnt_logger.info('No need to create Table')

        # Login to APIC
        session = Session(self.url, self.login, self.password)
        resp = session.login()
        if not resp.ok:
            evnt_logger.critical('Could not login to APIC')
            return

        selected_classes = feed.selected_classes

        for cls in selected_classes:
            evnt_logger.info('Subscribing to %s', cls.__name__)
            cls.subscribe(session)
            evnt_logger.info('Subscribed to %s', cls.__name__)

        TableRow = namedtuple('TableRow', ('cls', 'name', 'timestamp', 'json', 'url'))
        while True:
            try:
                for cls in selected_classes:
                    if cls.has_events(session):
                        event_object = cls.get_event(session)

                        row = TableRow(
                            cls=event_object.__class__.__name__,
                            name=event_object.__str__(),
                            timestamp=datetime.datetime.now(),
                            json=json.dumps(event_object.get_json()),
                            url='Not Implemented')

                        evnt_cursor.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?)', row)
                        conn.commit()
                        evnt_logger.info('[%s] Update to %s', event_object.__class__.__name__, event_object)

            except KeyboardInterrupt:
                evnt_logger.info('Closing Down')
                return


@app.route('/events/recent/')
@app.route('/events/recent/<string:limiter>/')
def events_recent(limiter=None):
    """ Return an Atom Feed of _all_ classes currently subscribed to
    """
    logger.info('Rendering feed ALL with limiter %s and args %s', limiter, request.args)
    try:
        timestamp_limit, maxage, maxcount = _get_query_filters(request, limiter)
    except ValueError:
        return 'Did not provide a valid limiter', 404

    atom_feed = AtomFeed('Recent ACI events',
                         feed_url=request.url,
                         url=request.url_root,
                         generator=('ACI Toolkit', request.url_root, '1.0'))

    events = cursor.execute("SELECT * FROM events WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                            (timestamp_limit, maxcount))

    _produce_feed(atom_feed, events)

    return atom_feed.get_response()


@app.route('/events/class/<string:cls>/')
@app.route('/events/class/<string:cls>/<string:limiter>/')
def events_for_class(cls, limiter=None):
    """ Return an Atom Feed of the class specified in the URL param <cls>
    """
    logger.info('Rendering feed %s with limiter %s and args %s', cls, limiter, request.args)
    try:
        timestamp_limit, maxage, maxcount = _get_query_filters(request, limiter)
    except ValueError:
        return 'Did not provide a valid limiter', 404

    atom_feed = AtomFeed('ACI events for class {}'.format(cls),
                         generator=('ACI Toolkit', request.url_root, '1.0'),
                         feed_url=request.url,
                         url=request.url_root)

    timestamp_limit = datetime.datetime.now() - datetime.timedelta(days=maxage)
    events = cursor.execute("SELECT * FROM events WHERE cls = ? AND timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                            (cls, timestamp_limit, maxcount))

    _produce_feed(atom_feed, events)

    return atom_feed.get_response()


@app.route('/config/', methods=['POST', 'GET'])
def config():
    """ Simple GUI view to update the underlying configruation JSON dictionary
    """
    config_saved = False

    if request.method == 'POST':
        form = request.form
        config = {
            'log_file': form.get('log_file', feed.cfg['log_file']),
            'events_db': form.get('events_db', feed.cfg['events_db']),
            'classes': form.getlist('cls')
        }

        with open('config.json', 'w') as config_file:
            json.dump(config, config_file)
            feed.cfg.update(config)
            config_saved = True
        logger.info('Updated Config')
        logger.info(config)

    return render_template('config.html', selected_classes=feed.cfg['classes'],
                           eligible_classes=feed.eligible_classes_names, cfg=feed.cfg,
                           config_saved=config_saved)


@app.route('/')
def feeds():
    """
        List feeds available to the user
    """
    return render_template('feeds.html', selected_classes=feed.cfg['classes'])


class FeedCfg(object):
    """
        FeedCfg attempts to import the file 'config.json' if it is present.

        If not it will build a default configuration based on the values present
        in default_config

        If 'config.json' is present but does not parse correctly the script will
        raise a critical
    """

    def _import_cfg(self):

        default_config = {
            'log_file': 'feed.log',
            'events_db': 'events.db',
            'classes': ['Tenant']
        }

        try:
            with open('config.json', 'r') as config_file:
                try:
                    cfg = json.load(config_file)
                    default_config.update(cfg)
                except ValueError:
                    logger.critical('Could not load configuration file')
        except IOError:
            with open('config.json', 'w') as config_file:
                logger.info('Creating configuration file on first run')
                cfg = default_config
                json.dump(cfg, config_file)

        return default_config

    def _get_selected_classes(self):
        """
            Convert the string based representations of classes that are
            stored in the config.json file into the relveant Python
            objects that have been imported into the global namespace

            This avoids needing to use eval() on the string version of the
            class name (which could be dangerous)
        """
        selected_classes = []
        for cls in self.cfg['classes']:
            if cls in self.eligible_classes_names:
                selected_classes.append(globals()[cls])
        return selected_classes

    def __init__(self):
        """Eligible Classes defines the classes that can be subscribed to in EventFeeds"""
        self.cfg = self._import_cfg()
        self.eligible_classes = [
            Tenant,
            AppProfile,
            EPG,
            Endpoint,
            Contract,
            BridgeDomain,
            Context
        ]
        self.eligible_classes_names = [cls.__name__ for cls in self.eligible_classes]
        self.selected_classes = self._get_selected_classes()


def main():
    """
        Use the Credentials class of ACI toolkit to get the needed args to run the
        app.

        Set up an instance of FeedCfg and EventMonitor with provided args.

        Start the the EventMonitor thread as a daemon and then start the Flask server.
    """
    global feed, cursor, logger

    # Grab APIC credentials and ip/port for Flask
    creds = Credentials(qualifier=('apic', 'server'),
                        description='ACI Toolkit')
    args = creds.get()

    # Get EventFeeds configuration from disk and instantiate worker thread
    feed = FeedCfg()
    event_monitor = EventMonitor(args.url, args.login, args.password)

    # Set up file and stdout logging
    msg_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(filename=feed.cfg['log_file'], level=logging.INFO, format=msg_format)
    stdout = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(msg_format)
    stdout.setFormatter(formatter)
    logger.addHandler(stdout)

    logger.info('Getting DB Connection')
    try:
        conn = _get_db()
        cursor = conn.cursor()
    except sqlite3.Error as e:
        logger.critical('Could not get handle to DB: %s', e.message)

    # Start worker thread
    event_monitor.start()

    # Start Flask server
    app.run(host=args.ip, port=int(args.port), debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
