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
from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms import TextAreaField, SelectField
from wtforms.validators import IPAddress

__author__ = 'edsall'


class FeedbackForm(Form):
    """
    Form data for feedback
    """

    def generate_csrf_token(self, csrf_context):
        """

        :param csrf_context:
        """
        pass

    category = SelectField('', choices=[('bug', 'Bug'),
                                        ('enhancement', 'Enhancement Request'),
                                        ('question', 'General Question'),
                                        ('comment', 'General Comment')])
    comment = TextAreaField('Comment')
    submit = SubmitField('Submit')


class CredentialsForm(Form):
    """
    class to hold the form definition for the credentials
    """
    ipaddr = StringField('APIC IP Address:',
                         validators=[IPAddress()])
    secure = BooleanField('Use secure connection', validators=[])
    username = StringField('APIC Username:', validators=[])
    password = PasswordField('APIC Password:', validators=[])
    submit = SubmitField('Save')


class ResetForm(Form):
    """
    Reset form
    """
    reset = SubmitField('Reset')



