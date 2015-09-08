#!/usr/bin/env python
################################################################################
#                 _    ____ ___   _____           _ _    _ _                   #
#                / \  / ___|_ _| |_   _|__   ___ | | | _(_) |_                 #
#               / _ \| |    | |    | |/ _ \ / _ \| | |/ / | __|                #
#              / ___ \ |___ | |    | | (_) | (_) | |   <| | |_                 #
#        ____ /_/   \_\____|___|___|_|\___/ \___/|_|_|\_\_|\__|                #
#       / ___|___   __| | ___  / ___|  __ _ _ __ ___  _ __ | | ___  ___        #
#      | |   / _ \ / _` |/ _ \ \___ \ / _` | '_ ` _ \| '_ \| |/ _ \/ __|       #
#      | |__| (_) | (_| |  __/  ___) | (_| | | | | | | |_) | |  __/\__ \       #
#       \____\___/ \__,_|\___| |____/ \__,_|_| |_| |_| .__/|_|\___||___/       #
#                                                    |_|                       #
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
Simple application using event subscription for the Tenant class.
When run, this application will log into the APIC and subscribe to
events on the Tenant class.  If a new tenant is created, the event
will be printed on the screen.  Likewise, if an existing tenant is
deleted.
"""
import sys

import acitoolkit as aci


def main():
    """
    Main subscribe tenants routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application using event subscription for the'
                   'Tenant class. When run, this application will log '
                   'into the APIC and subscribe to events on the Tenant '
                   'class.  If a new tenant is created, the event will be'
                   'printed on the screen. Likewise, if an existing tenant'
                   'is deleted.')
    creds = aci.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = aci.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    aci.Tenant.subscribe(session)

    while True:
        if aci.Tenant.has_events(session):
            tenant = aci.Tenant.get_event(session)
            if tenant.is_deleted():
                print('Tenant', tenant.name, 'has been deleted.')
            else:
                print('Tenant', tenant.name, 'has been created or modified.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
