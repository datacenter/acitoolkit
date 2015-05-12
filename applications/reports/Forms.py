from wtforms import Form, StringField, BooleanField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import Required, IPAddress
from flask import Flask, render_template, session, redirect, url_for
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
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms import RadioField, IntegerField, TextAreaField, SelectField
from wtforms.fields.html5 import DateField, DateTimeField
from wtforms.validators import Required, IPAddress, NumberRange
from wtforms.validators import ValidationError, Optional
import difflib
from acitoolkit.acitoolkitlib import Credentials
import acitoolkit.acitoolkit as ACI
import acitoolkit.aciphysobject as ACI_PHYS

__author__ = 'edsall'



class FeedbackForm(Form):
    """
    Form data for feedback
    """
    category = SelectField('', choices=[('bug', 'Bug'),
                                        ('enhancement', 'Enhancement Request'),
                                        ('question', 'General Question'),
                                        ('comment', 'General Comment')])
    comment = TextAreaField('Comment', validators=[Required()])
    submit = SubmitField('Submit')


class CredentialsForm(Form):
    """
    class to hold the form definition for the credentials
    """
    ipaddr = StringField('APIC IP Address:',
                         validators=[Required(), IPAddress()])
    secure = BooleanField('Use secure connection', validators=[])
    username = StringField('APIC Username:', validators=[Required()])
    password = PasswordField('APIC Password:', validators=[Required()])
    submit = SubmitField('Save')

class ResetForm(Form):
    reset = SubmitField('Reset')



