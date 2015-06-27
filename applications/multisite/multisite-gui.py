import os
import os.path as op

from flask import Flask, render_template, session, redirect, url_for, render_template_string
from flask.ext.admin import Admin, AdminIndexView
from wtforms import PasswordField
from wtforms.validators import Required, IPAddress
from multisite import MultisiteCollector, SiteLoginCredentials, Site, ContractDB, ContractDBEntry
from flask import flash, send_from_directory, request
from flask.ext.sqlalchemy import SQLAlchemy
from requests import Timeout
#from flask.ext import admin
from flask.ext.admin import BaseView, AdminIndexView, expose
from flask.ext.admin.actions import action
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.model.template import macro
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, CsrfProtect
from wtforms import StringField, SubmitField, PasswordField, BooleanField, Field
from wtforms import RadioField, IntegerField, TextAreaField, SelectField, SelectMultipleField
from wtforms.fields.html5 import DateField, DateTimeField
from wtforms.validators import Required, IPAddress, NumberRange
from wtforms.validators import ValidationError, Optional
from wtforms.widgets import TextInput
from wtforms import widgets
from acitoolkit.acitoolkit import Credentials
#from flask_wtf.csrf import CsrfProtect
import sys

LAB_TEST_MODE = False

# Create application
app = Flask(__name__, static_folder='static')

# Create dummy secret key so we can use sessions
app.config['SECRET_KEY'] = '123456790'
app.config['CSRF_ENABLED'] = True
CsrfProtect(app)

bootstrap = Bootstrap(app)

# Create in-memory database
db_filename = os.environ.get('MULTISITE_DATABASE_FILE')
if db_filename is None:
    app.config['DATABASE_FILE'] = 'multisite_db.sqlite'
else:
    app.config['DATABASE_FILE'] = db_filename
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app=app)

# Create directory for file fields to use
file_path = op.join(op.dirname(__file__), 'files')
try:
    os.mkdir(file_path)
except OSError:
    pass

collector = MultisiteCollector()


def shutdown_server():
    """
    Shutdown the server
    """
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def lab_mode_only(original_function):
    """
    Decorator to enable lab only functionality
    """
    def new_function():
        if not LAB_TEST_MODE:
            return 'Function only available in lab testing mode'
        return original_function()
    return new_function

@app.route('/shutdown', methods=['POST', 'GET'])
@lab_mode_only
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


class SiteCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.Unicode(64))
    ip_address = db.Column(db.Unicode(64))
    user_name = db.Column(db.Unicode(64))
    password = db.Column(db.Unicode(64))
    use_https = db.Column(db.Boolean())
    local = db.Column(db.Boolean())


class CustomView(ModelView):
    list_template = 'list.html'

    def get_create_button_text(self):
        return 'Create'


class SiteCredentialsView(CustomView):
    form_base_class = Form

    def verify_unique_sitename(form, field):
        if not collector.verify_legal_characters(field):
            raise ValidationError('Site name characters must be belong to the following set of characters: a-zA-Z0-9=!#$%()*,-.:;@ _{|}~?&+')
        #if not collector.verify_unique_sitename(field):
        #    raise ValidationError('Site name must be unique')

    def verify_unique_ipaddress(form, field):
        pass
        #if not collector.verify_unique_ipaddress(field):
        #    raise ValidationError('IP address must be unique')

    can_create = True
    can_edit = True
    column_searchable_list = ('site_name', 'ip_address')
    column_labels = dict(ip_address='IP Address',
                         use_https='Use HTTPS')
    column_filters = ('site_name', 'ip_address', 'local')
    #column_editable_list = ('site_name')
    form_overrides = dict(password=PasswordField)
    form_args = dict(site_name=dict(validators=[Required(), verify_unique_sitename]),
                     user_name=dict(validators=[Required()]),
                     password=dict(validators=[Required()]),
                     ip_address=dict(validators=[Required(), IPAddress(), verify_unique_ipaddress]))
    column_exclude_list = ('password')

    def after_model_change(self, form, model, is_created):
        creds = SiteLoginCredentials(model.ip_address, model.user_name, model.password,
                                     model.use_https)
        collector.add_site(model.site_name, creds, model.local)
        update_db(model)
        collector.print_sites()

    def on_model_delete(self, model):
        collector.delete_site(model.site_name)
        collector.print_sites()
        # TODO: On model delete, for local remove all contracts.
        # TODO: For remote remove the remote from the site list and check back in if not empty
        # TODO: If empty, delete the entry

        if model.local:
            local_contracts = SiteContracts.query.filter_by(export_state='local')
            for local_contract in local_contracts:
                db.session.delete(local_contract)
            db.session.commit()

    def get_title(self):
        return 'Site Credentials'


class SiteContracts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_name = db.Column(db.Unicode(64))
    contract_name = db.Column(db.Unicode(64))
    export_state = db.Column(db.Unicode(64))
    remote_sites = db.Column(db.Unicode(256))

class ExportForm(Form):
    sites = SelectMultipleField('Remote Sites',
                                choices=[])
    submit = SubmitField('Save Export Settings')

class ExportView(BaseView):
    def is_visible(self):
        return False

    @expose('/', methods=['GET', 'POST'])
    def index(self):
        contract_ids = session.get('export_contracts')
        default_sites = []
        contract_data = []
        for contract_id in contract_ids:
            contract = SiteContracts.query.get(contract_id)
            contract_data.append((contract.contract_name, contract.tenant_name))
            selected_sites = contract.remote_sites.split('.')
            for selected_site in selected_sites:
                if selected_site not in default_sites:
                    default_sites.append(selected_site)
        remote_sites = collector.get_sites(remote_only=True)
        site_choices = []
        for remote_site in remote_sites:
            site_choices.append((remote_site.name, remote_site.name))
        MyExportForm = type('MyExportForm',
                            (ExportForm,),
                            {'sites': SelectMultipleField('Please select remote export sites',
                                                          default=default_sites,
                                                          choices=site_choices,
                                                          option_widget=widgets.CheckboxInput(),
                                                          widget=widgets.ListWidget(prefix_label=False)),
                             'submit': SubmitField('Save Export Settings')})
        form = MyExportForm()

        if form.validate_on_submit() and form.submit.data:
            for contract in contract_data:
                (contract_name, tenant_name) = contract

                # Get rid of the old contract entry in the GUI database
                old_db_entries= SiteContracts.query.filter_by(contract_name=contract_name,
                                                              tenant_name=tenant_name)
                for old_db_entry in old_db_entries:
                    db.session.delete(old_db_entry)
                db.session.commit()

                # Export the contract
                local_site = collector.get_local_site()
                problem_sites = local_site.export_contract(contract_name, tenant_name, form.sites.data)
                for problem_site in problem_sites:
                    flash('Could not export contract %s to site %s' % (contract_name, problem_site), 'error')

                # Store the new entries in the GUI database
                contract_entry = local_site.get_contract(tenant_name, contract_name)
                assert contract_entry is not None
                new_entry = SiteContracts()
                new_entry.tenant_name = contract_entry.tenant_name
                new_entry.contract_name = contract_entry.contract_name
                new_entry.export_state = contract_entry.export_state
                new_entry.remote_sites = contract_entry.get_remote_sites_as_string()
                db.session.add(new_entry)
                db.session.commit()
            return redirect(url_for('sitecontractsview.index_view'))

        #return render_template_string('<form>{{ form.sites')
        return self.render('exportview.html', form=form)

    def get_title(self):
        return 'Export Contracts'


class SiteContractsView(CustomView):
    can_create = False
    can_edit = False
    can_delete = False
    column_searchable_list = ('tenant_name', 'contract_name', 'export_state', 'remote_sites')
    column_filters = ('tenant_name', 'contract_name', 'export_state', 'remote_sites')

    def get_title(self):
        return 'Site Contracts'

    def get_create_button_text(self):
        return 'Export'

    def get_list(self, page, sort_column, sort_desc, search, filters, execute=True):
        update_contract_db()
        return super(SiteContractsView, self).get_list(page, sort_column, sort_desc, search, filters, execute)

    @action('export', 'Change Export Settings')
    def export(*args, **kwargs):
        if len(args[1]):
            for contract_id in args[1]:
                contract = SiteContracts.query.get(contract_id)
                if contract.export_state == 'imported':
                    flash('Cannot export an imported contract')
                    return
            session['export_contracts'] = args[1]
            return redirect(url_for('exportview.index'))
        else:
            flash('Please select at least one contract to export')


class SiteEpgs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_name = db.Column(db.Unicode(64))
    app_name = db.Column(db.Unicode(64))
    epg_name = db.Column(db.Unicode(64))
    contract_name = db.Column(db.Unicode(64))


class SiteEpgsView(CustomView):
    can_create = False
    can_edit = False
    can_delete = False
    column_searchable_list = ('tenant_name', 'app_name', 'epg_name', 'contract_name')
    column_filters = ('tenant_name', 'app_name', 'epg_name', 'contract_name')

    def get_title(self):
        return 'Site Exported/Imported EPGs'

    def get_list(self, page, sort_column, sort_desc, search, filters, execute=True):
        update_epg_db()
        return super(SiteEpgsView, self).get_list(page, sort_column, sort_desc, search, filters, execute)


class FeedbackForm(Form):
    category = SelectField('', choices=[('bug', 'Bug'),
                                        ('enhancement', 'Enhancement Request'),
                                        ('question', 'General Question'),
                                        ('comment', 'General Comment')])
    comment = TextAreaField('Comment', validators=[Required()])
    submit = SubmitField('Submit')


class Feedback(BaseView):
    @expose('/')
    def index(self):
        form = FeedbackForm()
        return self.render('feedback.html', form=form)


class About(BaseView):
    @expose('/')
    def index(self):
        return self.render('about.html')


# Create admin with custom base template
homepage_view = AdminIndexView(name='Home', template='admin/index.html',
                               url='/')
admin = Admin(app, name='ACI Multisite',
              index_view=homepage_view,
              base_template='layout.html')


# Add views
admin.add_view(SiteCredentialsView(SiteCredentials, db.session, name='Site Credentials'))
admin.add_view(SiteContractsView(SiteContracts, db.session, name='Site Contracts',
                                 endpoint='sitecontractsview'))
admin.add_view(SiteEpgsView(SiteEpgs, db.session, name='EPGs',
                                 endpoint='siteepgsview'))
admin.add_view(ExportView(name='Export Contracts'))
admin.add_view(About(name='About'))
admin.add_view(Feedback(name='Feedback'))


def build_db():
    """
    Populate the Database with the table.
    """
    db.drop_all()
    db.create_all()
    db.session.commit()
    return

def update_contract_db():
    local_site = collector.get_local_site()
    if local_site is None:
        flash('No local site credentials configured')
        return
    contract_db = local_site.get_contracts()
    SiteContracts.query.delete()
    db.session.commit()
    for contract in contract_db:
        dbcontract = SiteContracts()
        dbcontract.tenant_name = contract.tenant_name
        dbcontract.contract_name = contract.contract_name
        dbcontract.export_state = contract.export_state
        dbcontract.remote_sites = contract.get_remote_sites_as_string()
        db.session.add(dbcontract)
    db.session.commit()

def update_epg_db():
    local_site = collector.get_local_site()
    if local_site is None:
        flash('No local site credentials configured')
        return
    epg_db = local_site.get_epgs()
    SiteEpgs.query.delete()
    db.session.commit()
    for epg in epg_db:
        dbepg = SiteEpgs()
        dbepg.tenant_name = epg.tenant_name
        dbepg.app_name = epg.app_name
        dbepg.epg_name = epg.epg_name
        dbepg.contract_name = epg.contract_name
        db.session.add(dbepg)
    db.session.commit()

def update_db(site):
    if not site.local:
        return
    local_site = collector.get_site(site.site_name)
    if local_site is None:
        return

    # TODO initialize the info from APIC but should learn to rely on Monitor and use a callback to update GUI db
    local_site.initialize_from_apic()

    #local_site.register_for_callbacks('contracts', update_contract_db)
    update_contract_db()
    #local_site.register_for_callbacks('epgs', update_epg_db)
    update_epg_db()


def dbfile_exists():
    app_dir = op.realpath(os.path.dirname(__file__))
    database_path = op.join(app_dir, app.config['DATABASE_FILE'])
    if os.path.exists(database_path):
        return True

if __name__ == '__main__':
    description = ('ACI Multisite tool.')
    creds = Credentials('server', description)
    args = creds.get()
    LAB_TEST_MODE = args.test

    if dbfile_exists():
        # Discard contract table as we will repopulate from APIC since it may be stale
        SiteContracts.query.delete()
        db.session.commit()
        SiteEpgs.query.delete()
        db.session.commit()

        # Initialize the collector if database file already exists at initial run
        sites = SiteCredentials.query.all()
        for site in sites:
            creds = SiteLoginCredentials(site.ip_address, site.user_name, site.password,
                                         site.use_https)
            collector.add_site(site.site_name, creds, site.local)
        for site in sites:
            update_db(site)
    else:
        build_db()

    # Start app
    app.run(debug=False, use_reloader=False, host=args.ip, port=int(args.port))
