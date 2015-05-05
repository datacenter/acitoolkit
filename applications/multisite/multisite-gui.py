import os
import os.path as op

from flask import Flask, render_template, session, redirect, url_for, render_template_string
from flask.ext.admin import Admin, AdminIndexView
from wtforms import PasswordField
from wtforms.validators import Required, IPAddress
from multisite import MultisiteCollector, SiteLoginCredentials, Site
from flask import flash, send_from_directory, request
from flask.ext.sqlalchemy import SQLAlchemy
from requests import Timeout
from flask.ext import admin
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

# Create application
app = Flask(__name__, static_folder='static')

# Create dummy secret key so we can use sessions
app.config['SECRET_KEY'] = '123456790'
app.config['CSRF_ENABLED'] = True
CsrfProtect(app)

bootstrap = Bootstrap(app)

# Create in-memory database
app.config['DATABASE_FILE'] = 'multisite_db.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)

# Create directory for file fields to use
file_path = op.join(op.dirname(__file__), 'files')
try:
    os.mkdir(file_path)
except OSError:
    pass

collector = MultisiteCollector()


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
    can_create = True
    can_edit = True
    column_searchable_list = ('site_name', 'ip_address')
    column_labels = dict(ip_address='IP Address',
                         use_https='Use HTTPS')
    column_filters = ('site_name', 'ip_address', 'local')
    #column_editable_list = ('site_name')
    form_overrides = dict(password=PasswordField)
    form_args = dict(site_name=dict(validators=[Required()]),
                     user_name=dict(validators=[Required()]),
                     password=dict(validators=[Required()]),
                     ip_address=dict(validators=[Required(), IPAddress()]))
    column_exclude_list = ('password')

    def after_model_change(self, form, model, is_created):
        creds = SiteLoginCredentials(model.ip_address, model.user_name, model.password,
                                     model.use_https)
        collector.add_site(model.site_name, creds, model.local)
        update_contract_db(model)
        print '****MICHSMIT**** after_model_change:', model, type(model), is_created
        print model.site_name, model.ip_address, model.local
        collector.print_sites()

    def on_model_delete(self, model):
        print '****MICHSMIT**** on_model_delete', model.site_name, 'is being deleted'
        collector.delete_site(model.site_name)
        collector.print_sites()

    def get_num_sites(self):
        return collector.get_num_sites()

    def get_title(self):
        return 'Site credentials'


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
            print 'REMOTE SITES FOR', contract.contract_name, 'ARE', contract.remote_sites
            contract_data.append((contract.contract_name, contract.tenant_name))
            selected_sites = contract.remote_sites.split('.')
            for selected_site in selected_sites:
                if selected_site not in default_sites:
                    default_sites.append(selected_site)
        print 'DEFAULT SITES', default_sites
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
            collector.export_contracts(contract_data, form.sites.data)
            first = True
            remote_site_list = ''
            for site in form.sites.data:
                if first:
                    remote_site_list = site
                    first = False
                else:
                    remote_site_list += '.' + site

            for contract in contract_data:
                (contract_name, tenant_name) = contract
                old_db_entries= SiteContracts.query.filter_by(contract_name=contract_name,
                                                              tenant_name=tenant_name)
                for old_db_entry in old_db_entries:
                    db.session.delete(old_db_entry)
                new_entry = SiteContracts()
                (new_entry.tenant_name, new_entry.contract_name,
                 new_entry.export_state, new_entry.remote_sites) = (tenant_name, contract_name,
                                                                    'exported', remote_site_list)
                db.session.add(new_entry)
            db.session.commit()
            return redirect(url_for('sitecontractsview.index_view'))

        #return render_template_string('<form>{{ form.sites')
        return self.render('exportview.html', form=form)


class SiteContractsView(CustomView):
    can_create = False
    can_edit = False
    can_delete = False
    column_searchable_list = ('tenant_name', 'contract_name', 'export_state', 'remote_sites')
    column_filters = ('tenant_name', 'contract_name', 'export_state', 'remote_sites')

    def get_title(self):
        return 'Site contracts'

    def get_create_button_text(self):
        return 'Export'

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
admin.add_view(ExportView(name='Export Contracts'))


def build_db():
    """
    Populate the Database with the table.
    """
    db.drop_all()
    db.create_all()
    db.session.commit()
    return

def update_contract_db(site):
    if not site.local:
        return
    local_site = collector.get_site(site.site_name)
    contracts = local_site.get_contracts()
    for contract in contracts:
        dbcontract = SiteContracts()
        (dbcontract.tenant_name, dbcontract.contract_name,
         dbcontract.export_state, dbcontract.remote_sites) = contract
        db.session.add(dbcontract)
    db.session.commit()

def dbfile_exists():
    app_dir = op.realpath(os.path.dirname(__file__))
    database_path = op.join(app_dir, app.config['DATABASE_FILE'])
    if os.path.exists(database_path):
        return True

if __name__ == '__main__':
    if dbfile_exists():
        # Discard contract table as we will repopulate from APIC since it may be stale
        SiteContracts.query.delete()
        db.session.commit()

        # Initialize the collector if database file already exists at initial run
        sites = SiteCredentials.query.all()
        for site in sites:
            creds = SiteLoginCredentials(site.ip_address, site.user_name, site.password,
                                         site.use_https)
            collector.add_site(site.site_name, creds, site.local)
            update_contract_db(site)
    else:
        build_db()

    # Start app
    app.run(debug=True, use_reloader=False)