"""
Visualization of Endpoint membership within an EPG.
Runs as a web service and connects to the APIC to get Endpoint data.
Bubbles represent the EPGs.
Colorization is done based on Tenant/App/EPG and bubble size represents
the number of Endpoints in the EPG.  Hovering over a bubble will show the
EPG name and number of Endpoints.
"""
import flask
import json
import sys
from acitoolkit import Credentials, Session, Endpoint

DEFAULT_PORT = '5000'
DEFAULT_IPADDRESS = '127.0.0.1'

flask_app = flask.Flask(__name__)


def get_data_from_apic(url, username, password):
    """
    Gets the Endpoint data from the APIC

    :param url: String containing the URL of the APIC
    :param username: String containing the username to login to the APIC
    :param password: String containing the password to login to the APIC
    :return: None
    """
    ep_db = {}

    # Login to the APIC
    print 'Logging in to APIC...'
    session = Session(url, username, password, subscription_enabled=False)
    resp = session.login()
    if not resp.ok:
        print 'Could not login to APIC'
        sys.exit(0)

    # Get the endpoint from the APIC
    print 'Getting endpoints from the APIC....'
    endpoints = Endpoint.get(session)

    # Loop through the endpoints and count them on a per EPG basis
    print 'Counting the endpoints....'
    for endpoint in endpoints:
        epg = endpoint.get_parent()
        app = epg.get_parent()
        tenant = app.get_parent()
        if tenant.name not in ep_db:
            ep_db[tenant.name] = {}
        if app.name not in ep_db[tenant.name]:
            ep_db[tenant.name][app.name] = {}
        if epg.name not in ep_db[tenant.name][app.name]:
            ep_db[tenant.name][app.name][epg.name] = 0
        ep_db[tenant.name][app.name][epg.name] += 1

    # Write the results to a JSON formatted dictionary
    print 'Translating results to JSON...'
    epgs = {'name': 'epgs',
            'children': []}
    for tenant in ep_db:
        tenant_json = {'name': tenant,
                       'children': []}
        for app in ep_db[tenant]:
            app_json = {'name': app,
                        'children': []}
            for epg in ep_db[tenant][app]:
                epg_json = {'name': epg,
                            'size': ep_db[tenant][app][epg]}
                app_json['children'].append(epg_json)
            tenant_json['children'].append(app_json)
        epgs['children'].append(tenant_json)

    # Write the formatted JSON to a file
    print 'Writing results to a file....'
    try:
        with open('static/epgs.json', 'w') as epg_file:
            epg_file.write(json.dumps(epgs))
    except IOError:
        print '%% Unable to open configuration file', 'static/epgs.json'
        sys.exit(0)
    except ValueError:
        print '%% File could not be decoded as JSON.'
        sys.exit(0)


@flask_app.route('/')
def index():
    """ Displays the index page accessible at '/'
    """
    return flask.render_template('bubble-tooltips.html')

if __name__ == '__main__':
    creds = Credentials(('apic', 'server'),
                        'Endpoints per EPG bubble chart visualization')
    args = creds.get()

    print 'Getting data from APIC....'
    get_data_from_apic(args.url, args.login, args.password)

    print 'Running server. Point your browser to http://%s:%s' % (args.ip,
                                                                  args.port)
    flask_app.run(debug=False, host=args.ip, port=int(args.port))
