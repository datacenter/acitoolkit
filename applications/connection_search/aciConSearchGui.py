################################################################################
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
Browser GUI for connection search.
"""
import datetime
import re
from copy import copy
from flask import Flask, session, redirect, url_for, jsonify
from flask import flash, request
from flask.ext import admin
from flask.ext.admin import BaseView, AdminIndexView, expose
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, CsrfProtect
from acitoolkit.acitoolkitlib import Credentials
from acitoolkit.acisession import Session, CredentialsError
from requests import Timeout, ConnectionError
# Create application
from Forms import FeedbackForm, CredentialsForm, ResetForm
from aciConSearch import FlowSpec, SearchDb, ProtocolFilter

# start the flask application and tell it the static folder is called 'static'
app = Flask(__name__, static_folder='static')

# todo: need to validate the secrete key
app.config['SECRET_KEY'] = 'Dnit7qz7mfcP0YuelDrF8vLFvk0snhwP'
app.config['CSRF_ENABLED'] = True
CsrfProtect(app)

bootstrap = Bootstrap(app)

# Create the ACI Search Database
sdb = SearchDb()


class APICArgs(object):
    """
    Class to hold the Arguments of the APIC
    """

    def __init__(self, ipaddr, username, secure, password):
        self.login = username
        self.password = password
        if ipaddr is not None:
            if secure is True:
                self.url = 'https://' + ipaddr
            else:
                self.url = 'http://' + ipaddr
        else:
            self.url = None
        self.modified = True  # flag to indicate that the credentials have changed


class Feedback(BaseView):
    """
    form to allow the user to provide feedback.
    """

    @expose('/')
    def index(self):
        """
        Get feedback

        :return:
        """
        form = FeedbackForm()
        return self.render('feedback.html', form=form)


class SearchBar(Form):
    """
    Base form for showing the select switch form.  List of switches and list of reports.
    """
    pass


class LoginError(Exception):
    """
    Exception for login errors.
    """
    pass


class BaseConnSearchView(BaseView):
    @staticmethod
    def load_db():
        """
        This will setup the session to the APIC and then load the db
        :return:
        """
        try:
            apic_args = APICArgs(session['ipaddr'], session['username'], session['secure'], session['password'])
        except KeyError:
            return False
            # return redirect(url_for('credentialsview.index'))

        # apic_session = Session(apic_args.url, apic_args.login, apic_args.password)
        # resp = apic_session.login()
        # if not resp.ok:
        #     raise LoginError
        # sdb.session = apic_session
        # sdb.build()
        try:
            apic_session = Session(apic_args.url, apic_args.login, apic_args.password)
            resp = apic_session.login()
            if not resp.ok:
                raise LoginError
            sdb.session = apic_session
            sdb.build()

        except Timeout:
            flash('Connection timeout when trying to reach the APIC', 'error')
            return False
            # return redirect(url_for('switchreportadmin.index_view'))
        except LoginError:
            flash('Unable to login to the APIC', 'error')
            return False
            # return redirect(url_for('credentialsview.index'))
        except ConnectionError:
            flash('Connection failure.  Perhaps \'secure\' setting is wrong')
            return False
            # return redirect(url_for('credentialsview.index'))
        except CredentialsError, e:
            flash('There is a problem with your APIC credentials:' + e.message)
            return False
            # return redirect(url_for('credentialsview.index'))
        return True
        #     flash('Login failure - perhaps credentials are incorrect')
        #     return redirect(url_for('credentialsview.index'))


class AciConnSearchView(BaseConnSearchView):
    """
    Search bar.
    """

    @expose('/')
    def index(self):
        """

        :return:
        """
        global sdb
        form = SearchBar()

        # load data from file if it has not been otherwise loaded
        if not sdb.initialized:
            return self.render('loading.html')

        return self.render('search_result.html', form=form)


class About(BaseView):
    """
    Displays the about information
    """

    @expose('/')
    def index(self):
        """
        Show about information

        :return:
        """
        return self.render('about.html')


class CredentialsView(BaseView):
    """
    Gets the APIC credentials from the user.
    """

    @expose('/', methods=['GET', 'POST'])
    def index(self):
        """
        Prompt user for APIC credentials

        :return:
        """
        form = CredentialsForm()
        reset_form = ResetForm()
        if session.get('ipaddr') is None:
            session['ipaddr'] = None
            session['secure'] = None
            session['username'] = None
            session['password'] = None

        if form.validate_on_submit() and form.submit.data:
            old_ipaddr = session.get('ipaddr')
            old_username = session.get('username')
            old_secure = session.get('secure')
            old_password = session.get('password')
            if ((old_ipaddr is not None and old_ipaddr != form.ipaddr.data) or
                    (old_username is not None and old_username != form.username.data) or
                    (old_secure is not None and old_secure != form.secure.data) or
                    (old_password is not None and old_password != form.password.data)):
                sdb.initialized = False
                flash('APIC Credentials have been updated')

            session['ipaddr'] = form.ipaddr.data
            session['secure'] = form.secure.data
            session['username'] = form.username.data
            session['password'] = form.password.data
            return redirect(url_for('credentialsview.index'))
        elif reset_form.reset.data:
            session['ipaddr'] = None
            session['secure'] = None
            session['username'] = None
            session['password'] = None
            sdb.initialized = False
            return redirect(url_for('credentialsview.index'))
        return self.render('credentials.html', form=form,
                           reset_form=reset_form,
                           ipaddr=session.get('ipaddr'),
                           username=session.get('username'),
                           security=session.get('secure', 'False'))


# Create admin with custom base template
homepage_view = AdminIndexView(name='Home', template='admin/index.html',
                               url='/')
admin = admin.Admin(app,
                    name='Search Tom View',
                    index_view=homepage_view,
                    base_template='layout.html')

# Add views
admin.add_view(CredentialsView(name='Credentials'))
admin.add_view(About(name='About', endpoint='about'))
admin.add_view(Feedback(name='Feedback'))
admin.add_view(AciConnSearchView(name='Search'))


# admin.add_view(ShowObjectView(name='Object View', endpoint='atk_object'))


def build_flow_spec(terms):
    flow_spec = FlowSpec()
    protocol_filter = ProtocolFilter()
    flow_spec.protocol_filter = [protocol_filter]

    fields = input_parser(terms)
    num_filters = 1
    if 'dport' in fields or 'sport' in fields:
        if 'tcpRules' not in fields and 'prot' not in fields:
            num_filters = 2

    for keyword in fields:
        value = fields[keyword]
        if keyword == 'tenant':
            flow_spec.tenant_name = value

        if keyword == 'context':
            flow_spec.context_name = value

        if keyword == 'contract':
            flow_spec.contract = value

        if keyword == 'dip':
            flow_spec.dip = value

        if keyword == 'sip':
            flow_spec.sip = value

        if keyword == 'arpOpc':
            protocol_filter.arpOpc = value

        if keyword == 'applyToFrag':
            protocol_filter.applyToFrag = value

        if keyword == 'etherT':
            protocol_filter.etherT = value

        if keyword == 'prot':
            protocol_filter.prot = value

        if keyword == 'dport':
            protocol_filter.dPort = value

        if keyword == 'sport':
            protocol_filter.sPort = value

        if keyword == 'tcpRules':
            protocol_filter.tcpRules = value

    if num_filters == 2:
        protocol_filter.prot = 'tcp'
        protocol_filter_2 = copy(protocol_filter)
        protocol_filter_2.prot = 'udp'
        flow_spec.protocol_filter.append(protocol_filter_2)

    return flow_spec


def input_parser(in_string):
    """
    Will parse the input string to pull out keyword value pairs
    :param in_string:
    :return:
    """
    keywords = ["tenant", "context", "contract", "sip", "dip", "dport", "sport",
                "prot", "etherT", "arpOpc", "applyToFrag", "tcpRules"]

    result = {}
    fields = re.split('[\s=]+', in_string)
    index = 0
    done = False
    while len(fields) > index and not done:

        if fields[index] in keywords:
            key = fields[index]
            index += 1
            value = ''
            if len(fields) > index:
                if key in ['sport', 'dport']:
                    while fields[index] not in keywords and not done:
                        value += fields[index]

                        if index == len(fields) - 1:
                            done = True
                        else:
                            index += 1
                else:
                    value += fields[index]
                    if index == len(fields) - 1:
                        done = True
                    else:
                        index += 1
            else:
                done = True
            result[key] = value
        else:
            if index == len(fields) - 1:
                done = True
            else:
                index += 1
    return result


def prep_results(s_results):
    """
    Will format the search results into a dictionary that can be serialized into JSON
    :param s_results:
    :return:
    """
    result = []
    for s_result in s_results:
        entry = {'src_tenant': s_result.src_tenant_name,
                 'src_app_profile': s_result.src_app_profile,
                 'src_app_profile_type': s_result.src_app_profile_type,
                 'sourceEpg': s_result.source_epg,
                 'src_epg_type': s_result.src_epg_type,
                 'sip': [],
                 'dip': [],
                 'dst_tenant': s_result.dst_tenant_name,
                 'dst_app_profile': s_result.dst_app_profile,
                 'dst_app_profile_type' : s_result.dst_app_profile_type,
                 'destEpg': s_result.dest_epg,
                 'dst_epg_type': s_result.dst_epg_type,
                 'contract_tenant': s_result.contract_tenant,
                 'contract': s_result.contract}
        for address in sorted(s_result.dip):
            entry['dip'].append(str(address))
        entry['sip'] = []
        for address in sorted(s_result.sip):
            entry['sip'].append(str(address))
        entry['filter'] = []
        for aci_filter in s_result.protocol_filter:
            entry['filter'].append(str(aci_filter))

        result.append(entry)
    return result


@app.route("/search/<search_terms>")
def search_result_page(search_terms='1/101/1/49'):
    """
    This will do the actual search and return the result
    :param search_terms:
    """
    terms = str(request.args['first'])
    print 'search terms', terms
    flow_spec = build_flow_spec(terms)
    t1 = datetime.datetime.now()
    #result = sorted(sdb.search(flow_spec))
    result = sdb.search(flow_spec)
    t2 = datetime.datetime.now()
    print "Search time:", t2 - t1
    return jsonify(result=prep_results(result))


@app.route("/load_data")
def load_data():
    if BaseConnSearchView.load_db():
        return jsonify(result='done')
    else:
        return jsonify(result='fail')

        # return redirect(url_for('credentialsview.index'))

        # return jsonify(result='done')


def initialize_db():
    sdb.build()


if __name__ == '__main__':
    description = 'ACI Connection Search Tool.'
    creds = Credentials('server', description)
    args = creds.get()

    # Start app
    # app.run(debug=True, host=args.ip, port=int(args.port))
    app.run(debug=True, use_reloader=False, host=args.ip, port=5001)
