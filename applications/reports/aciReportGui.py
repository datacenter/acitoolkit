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
Reports: ACI Toolkit report GUI.
"""
from flask import Flask, session, redirect, url_for
from flask import flash
from flask.ext import admin
from flask.ext.admin import BaseView, AdminIndexView, expose
from flask.ext.admin.actions import action
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.model.template import macro
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, CsrfProtect
from wtforms import SubmitField
from wtforms import SelectField
from acitoolkit.acitoolkitlib import Credentials
from requests import Timeout, ConnectionError
# Create application
from Forms import FeedbackForm, CredentialsForm, ResetForm
from aciReportDB import ReportDB, LoginError

app = Flask(__name__, static_folder='static')

# todo: need to validate the secrete key
app.config['SECRET_KEY'] = 'Dnit7qz7mfcP0YuelDrF8vLFvk0snhwP'
app.config['CSRF_ENABLED'] = True
CsrfProtect(app)

bootstrap = Bootstrap(app)

# Create the ACI Config Database
rdb = ReportDB()


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


class SelectSwitchForm(Form):
    """
    Base form for showing the select switch form.  List of switches and list of reports.
    """
    category = SelectField('Switch', choices=[], validators=[])
    detail = SelectField('Report Type', choices=[])
    submit = SubmitField('Select')


class SelectTenantForm(Form):
    """
    Base form for showing the select tenant form.
    """
    category = SelectField('Tenant', choices=[], validators=[])
    detail = SelectField('Report Type', choices=[])
    submit = SubmitField('Select')


class SelectTenantView(BaseView):
    """
    The actual select tenant page generator.
    """
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        """
        Allow user to select which report to show.

        :return:
        """
        form = SelectTenantForm()

        try:
            form.category.choices = rdb.get_tenants()
            form.detail.choices = rdb.get_tenant_reports()
        except Timeout:
            flash('Connection timeout when trying to reach the APIC', 'error')
            return redirect(url_for('switchreportadmin.index_view'))
        except LoginError:
            flash('Unable to login to the APIC', 'error')
            return redirect(url_for('credentialsview.index'))
        except ConnectionError:
            flash('Connection failure.  Perhaps \'secure\' setting is wrong')
            return redirect(url_for('credentialsview.index'))

        prompt = 'Select which switch you want to see the report for.'
        if form.validate_on_submit() and form.submit.data:

            # report = DynamicTableForm()
            try:
                report = rdb.get_tenant_table(form.data['category'], form.data['detail'])
            except Timeout:
                flash('Connection timeout when trying to reach the APIC', 'error')
                return redirect(url_for('switchreportadmin.index_view'))
            except LoginError:
                flash('Unable to login to the APIC', 'error')
                return redirect(url_for('credentialsview.index'))
            except ConnectionError:
                flash('Connection failure.  Perhaps \'secure\' setting is wrong')
                return redirect(url_for('credentialsview.index'))
            if not report:
                report = 'empty'
            return self.render('select_switch.html', prompt=prompt, form=form, report=report)

        return self.render('select_switch.html', prompt=prompt, form=form)


class SelectSwitchView(BaseView):
    """
    The actual select switch page generator.
    """
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        """
        Allow user to select which report to show.

        :return:
        """
        form = SelectSwitchForm()

        try:
            form.category.choices = rdb.get_switches()
            report = rdb.get_switch_summary()
        except Timeout:
            flash('Connection timeout when trying to reach the APIC', 'error')
            return redirect(url_for('switchreportadmin.index_view'))
        except LoginError:
            flash('Unable to login to the APIC', 'error')
            return redirect(url_for('credentialsview.index'))
        except ConnectionError:
            flash('Connection failure.  Perhaps \'secure\' setting is wrong')
            return redirect(url_for('credentialsview.index'))

        form.detail.choices = rdb.get_switch_reports()

        if form.validate_on_submit() and form.submit.data:

            # report = DynamicTableForm()
            try:
                report = rdb.get_switch_table(form.data['category'], form.data['detail'])
            except Timeout:
                flash('Connection timeout when trying to reach the APIC', 'error')
                return redirect(url_for('switchreportadmin.index_view'))
            except LoginError:
                flash('Unable to login to the APIC', 'error')
                return redirect(url_for('credentialsview.index'))
            except ConnectionError:
                flash('Connection failure.  Perhaps \'secure\' setting is wrong')
                return redirect(url_for('credentialsview.index'))

        prompt = 'Select which switch you want to see the report for.'
        return self.render('select_switch.html', prompt=prompt, form=form, report=report)


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
        apic_args = APICArgs(session.get('ipaddr'), session.get('username'), session.get('secure'), session.get('password'))
        rdb.set_login_credentials(apic_args)
        if form.validate_on_submit() and form.submit.data:
            old_ipaddr = session.get('ipaddr')
            old_username = session.get('username')
            old_secure = session.get('secure')
            old_password = session.get('password')
            if ((old_ipaddr is not None and old_ipaddr != form.ipaddr.data) or
                 (old_username is not None and old_username != form.username.data) or
                 (old_secure is not None and old_secure != form.secure.data) or
                 (old_password is not None and old_password != form.password.data)):
                flash('APIC Credentials have been updated')
            session['ipaddr'] = form.ipaddr.data
            session['secure'] = form.secure.data
            session['username'] = form.username.data
            session['password'] = form.password.data
            apic_args = APICArgs(session['ipaddr'], session['username'], session['secure'], session['password'])
            rdb.set_login_credentials(apic_args)
            return redirect(url_for('credentialsview.index'))
        elif reset_form.reset.data:
            session['ipaddr'] = None
            session['secure'] = None
            session['username'] = None
            session['password'] = None
            apic_args = APICArgs(session['ipaddr'], session['username'], session['secure'], session['password'])
            rdb.set_login_credentials(apic_args)
            return redirect(url_for('credentialsview.index'))
        return self.render('credentials.html', form=form,
                           reset_form=reset_form,
                           ipaddr=session.get('ipaddr'),
                           username=session.get('username'),
                           security=session.get('secure', 'False'))


# Customized admin interface
class CustomView(ModelView):
    """
    Custom view placeholder class
    """
    list_template = 'list.html'


class ReportView(CustomView):
    """
    Report view.
    """
    can_create = False
    can_edit = False
    column_searchable_list = ('version', 'filename')
    column_filters = ('version', 'filename', 'latest')
    column_formatters = dict(changes=macro('render_changes'))

    @action('rollback', 'Rollback',
            'Are you sure you want to rollback the configuration ?')
    def rollback(self):
        """
        This is not used.
        :return:
        """
        if session.get('ipaddr') is None:
            flash('APIC Credentials have not been entered', 'error')
            return redirect(url_for('snapshotsadmin.index_view'))
        return redirect(url_for('snapshotsadmin.index_view'))

    @action('view', 'View')
    def view(*args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        return redirect(url_for('fileview.index'))

# Create admin with custom base template
homepage_view = AdminIndexView(name='Home', template='admin/index.html',
                               url='/')
admin = admin.Admin(app,
                    name='ReportView',
                    index_view=homepage_view,
                    base_template='layout.html')

# Add views
admin.add_view(CredentialsView(name='Credentials'))
admin.add_view(About(name='About'))
admin.add_view(Feedback(name='Feedback'))
admin.add_view(SelectSwitchView(name='Switch Reports'))
admin.add_view(SelectTenantView(name='Tenant Reports'))

if __name__ == '__main__':
    description = 'ACI Report Viewer Tool.'
    creds = Credentials('server', description)
    args = creds.get()

    # Start app
    app.run(debug=True, host=args.ip, port=int(args.port))
