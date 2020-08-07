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
Forms for report GUI
"""
from flask_wtf import Form
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms import TextAreaField, SelectField
from wtforms.validators import DataRequired, IPAddress, ValidationError
from wtforms.compat import string_types, text_type
import re
import ipaddress

__author__ = 'edsall'

class CustomValidation(object):
    """
    Custom validation class for checking APIC input. Validates IPv4 or IPv6 addresses
    If not an IP, uses a regex to invalidate symbols from FQDN
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        value = field.data
        valid = False
        fqdn_re = re.compile('(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
        try:
            apic_input = ipaddress.ip_address(value)
            if apic_input.version == 4:
                valid = True
            elif apic_input.version == 6:
                    valid = True
        except ValueError:
            if fqdn_re.search(value):
                valid = True
            else:
                valid = False

        if not valid:
            message = self.message
            if message is None:
                message = field.gettext('Invalid IP or FQDN.')
            raise ValidationError(message)

class FeedbackForm(Form):
    """
    Form data for feedback
    """
    category = SelectField('', choices=[('bug', 'Bug'),
                                        ('enhancement', 'Enhancement Request'),
                                        ('question', 'General Question'),
                                        ('comment', 'General Comment')])
    comment = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Submit')


class CredentialsForm(Form):
    """
    class to hold the form definition for the credentials
    """
    ipaddr = StringField('APIC IP Address/FQDN:',
                         validators=[DataRequired(), CustomValidation()])
    secure = BooleanField('Use secure connection', validators=[])
    username = StringField('APIC Username:', validators=[DataRequired()])
    password = PasswordField('APIC Password:', validators=[DataRequired()])
    submit = SubmitField('Save')


class ResetForm(Form):
    """
    Reset form
    """
    reset = SubmitField('Reset')
