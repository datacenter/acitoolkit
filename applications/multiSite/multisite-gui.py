import os
import os.path as op

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin import Admin, AdminIndexView


# Create application
app = Flask(__name__, static_folder='static')

# Create dummy secrey key so we can use sessions
app.config['SECRET_KEY'] = '123456790'

# Create in-memory database
app.config['DATABASE_FILE'] = 'sample_db.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)

# Create directory for file fields to use
file_path = op.join(op.dirname(__file__), 'files')
try:
    os.mkdir(file_path)
except OSError:
    pass


class SiteCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.Unicode(64))
    ip_address = db.Column(db.Unicode(64))
    user_name = db.Column(db.Unicode(64))
    password = db.Column(db.Unicode(64))
    secure = db.Column(db.Boolean())
    local = db.Column(db.Boolean())

class CustomView(ModelView):
    list_template = 'list.html'

class SiteCredentialsView(CustomView):
    can_create = True
    can_edit = True
    column_searchable_list = ('site_name', 'ip_address')
    column_filters = ('site_name', 'ip_address', 'local')


# Create admin with custom base template
homepage_view = AdminIndexView(name='Home', template='admin/index.html',
                               url='/')
admin = Admin(app, name='ACI Multisite',
              index_view=homepage_view,
              base_template='layout.html')


# Add views
admin.add_view(SiteCredentialsView(SiteCredentials, db.session, name='Site Credentials'))


def build_sample_db():
    """
    Populate a small db with some example entries.
    """
    import random
    import string

    db.drop_all()
    db.create_all()

    # Add any here

    db.session.commit()
    return

if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = op.realpath(os.path.dirname(__file__))
    database_path = op.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()

    # Start app
    app.run(debug=True)