#!/usr/bin/env python
################################################################################
#                        _    ____ ___   _     _       _                       #
#                       / \  / ___|_ _| | |   (_)_ __ | |_                     #
#                      / _ \| |    | |  | |   | | '_ \| __|                    #
#                     / ___ \ |___ | |  | |___| | | | | |_                     #
#                    /_/   \_\____|___| |_____|_|_| |_|\__|                    #
#                                                                              #
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
acilint - A static configuration analysis tool for examining ACI Fabric
          configuration for potential problems and unused configuration.
"""
import sys
from acitoolkit.acitoolkit import Tenant, AppProfile, Context, EPG, BridgeDomain, Contract
from acitoolkit.acitoolkit import Credentials, Session
from acitoolkit.acifakeapic import FakeSession
import argparse


class Checker(object):
    """
    Checker class contains a series of lint checks that are executed against the
    provided configuration.
    """
    def __init__(self, session):
        print 'Getting configuration from APIC....'
        self.tenants = Tenant.get_deep(session)
        print 'Processing configuration....'

    @staticmethod
    def ensure_tagged(objects, tags):
        """
        Checks that a set of objects are tagged with at least one tag
        from the set of tags.
        """
        for obj in objects:
            tagged = False
            for tag in tags:
                if obj.has_tag(tag):
                    tagged = True
            if not tagged:
                return False
        return True

    def warning_001(self):
        """
        W001: Tenant has no app profile
        """
        for tenant in self.tenants:
            if len(tenant.get_children(AppProfile)) == 0:
                print ("Warning 001: Tenant '%s' has no Application "
                       "Profile." % tenant.name)

    def warning_002(self):
        """
        W002: Tenant has no context
        """
        for tenant in self.tenants:
            if len(tenant.get_children(Context)) == 0:
                print "Warning 002: Tenant '%s' has no Context." % tenant.name

    def warning_003(self):
        """
        W003: AppProfile has no EPGs
        """
        for tenant in self.tenants:
            for app in tenant.get_children(AppProfile):
                if len(app.get_children(EPG)) == 0:
                    print ("Warning 003: AppProfile '%s' in Tenant '%s'"
                           " has no EPGs." % (app.name, tenant.name))

    def warning_004(self):
        """
        W004: Context has no BridgeDomain
        """
        for tenant in self.tenants:
            contexts = []
            for context in tenant.get_children(Context):
                contexts.append(context.name)
            for bd in tenant.get_children(BridgeDomain):
                if bd.has_context():
                    context = bd.get_context().name
                    if context in contexts:
                        contexts.remove(context)
            for context in contexts:
                print ("Warning 004: Context '%s' in Tenant '%s' has no "
                       "BridgeDomains." % (context, tenant.name))

    def error_001(self):
        """
        E001: BridgeDomain has no Context
        """
        for tenant in self.tenants:
            for bd in tenant.get_children(BridgeDomain):
                if not bd.has_context():
                    print ("Error 001: BridgeDomain '%s' in tenant '%s' "
                           "has no Context assigned." % (bd.name, tenant.name))

    def warning_005(self):
        """
        W005: BridgeDomain has no EPGs assigned
        """
        for tenant in self.tenants:
            bds = []
            for bd in tenant.get_children(BridgeDomain):
                bds.append(bd.name)
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    if epg.has_bd():
                        bd = epg.get_bd().name
                        if bd in bds:
                            bds.remove(bd)
            for bd in bds:
                print ("Warning 005: BridgeDomain '%s' in Tenant '%s'"
                       " has no EPGs." % (bd, tenant.name))

    def warning_006(self):
        """
        W006: Contract is not provided at all.
        """
        for tenant in self.tenants:
            contracts = []
            for contract in tenant.get_children(Contract):
                contracts.append(contract.name)
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    provided = epg.get_all_provided()
                    for contract in provided:
                        if contract.name in contracts:
                            contracts.remove(contract.name)
            for contract in contracts:
                print ("Warning 006: Contract '%s' in Tenant '%s' is not"
                       " provided at all." % (contract, tenant.name))

    def warning_007(self):
        """
        W007: Contract is not consumed at all.
        """
        for tenant in self.tenants:
            contracts = []
            for contract in tenant.get_children(Contract):
                contracts.append(contract.name)
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    consumed = epg.get_all_consumed()
                    for contract in consumed:
                        if contract.name in contracts:
                            contracts.remove(contract.name)
            for contract in contracts:
                print ("Warning 007: Contract '%s' in Tenant '%s' is not"
                       " consumed at all." % (contract, tenant.name))

    def error_002(self):
        """
        E002: EPG has no BD assigned.
        """
        for tenant in self.tenants:
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    if not epg.has_bd():
                        print ("Error 002: EPG '%s' in Tenant '%s', "
                               "AppProfile '%s' has no BridgeDomain "
                               "assigned." % (epg.name, tenant.name,
                                              app.name))

    def error_004(self):
        # E004: EPG not assigned to an interface or VMM domain
        pass

    def warning_008(self):
        """
        W008: EPG providing contracts but in a Context with no enforcement.
        """
        for tenant in self.tenants:
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    if len(epg.get_all_provided()):
                        if epg.has_bd():
                            bd = epg.get_bd()
                            if bd.has_context():
                                context = bd.get_context()
                                if context.get_allow_all():
                                    print ("Warning 008: EPG '%s' providing "
                                           "contracts in Tenant '%s', App"
                                           "Profile '%s' but Context '%s' "
                                           "is not enforcing." % (epg.name,
                                                                  tenant.name,
                                                                  app.name,
                                                                  context.name))

    def warning_010(self):
        """
        W010: EPG providing contract but consuming EPG is in a different
              context.
        """
        provide_db = {}
        for tenant in self.tenants:
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    if epg.has_bd():
                        bd = epg.get_bd()
                        if bd.has_context():
                            context = bd.get_context()
                        provided = epg.get_all_provided()
                        for contract in provided:
                            if tenant.name not in provide_db:
                                provide_db[tenant.name] = {}
                            if contract.name not in provide_db[tenant.name]:
                                provide_db[tenant.name][contract.name] = []
                            if context.name not in provide_db[tenant.name][contract.name]:
                                provide_db[tenant.name][contract.name].append(context.name)

        for tenant in self.tenants:
            epgs = []
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    epgs.append(epg)
            for epg in epgs:
                if epg.has_bd():
                    bd = epg.get_bd()
                    if bd.has_context():
                        context = bd.get_context()
                    consumed = epg.get_all_consumed()
                    for contract in consumed:
                        if tenant.name not in provide_db:
                            print ("Warning 010: No contract provided within"
                                   " this tenant '%s'" % tenant.name)
                        elif contract.name not in provide_db[tenant.name]:
                            print ("Warning 010: Contract not provided "
                                   "within the same tenant "
                                   "'%s'" % tenant.name)
                        elif context.name not in provide_db[tenant.name][contract.name]:
                            print ("Warning 010: Contract '%s' not provided in context '%s' "
                                   "where it is being consumed for"
                                   " tenant '%s'" % (contract.name, context.name, tenant.name))

    def critical_001(self):
        """
        This is an example of a compliance check where all EPGs are expected
        to be tagged with either 'secure' or 'nonsecure' and secure EPGs are
        not allowed to provide or consume contracts from nonsecure EPGs.
        """
        for tenant in self.tenants:
            # Look at all the EPGs and verify that they are all
            # assigned a security level
            secure_epgs = []
            nonsecure_epgs = []
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    if not self.ensure_tagged([epg], ('secure', 'nonsecure')):
                        print ("Critical 001: EPG '%s' in tenant '%s' "
                               "app '%s' is not assigned security "
                               "clearance" % (epg.name, tenant.name, app.name))
                    if epg.has_tag('secure'):
                        if epg.has_tag('nonsecure'):
                            print ("Critical 001: EPG '%s' in tenant '%s' "
                                   "app '%s' is assigned secure and nonsecure security "
                                   "clearance" % (epg.name, tenant.name, app.name))
                            # Squirrel away the Secure EPGs
                            secure_epgs.append(epg)
                        else:
                            nonsecure_epgs.append(epg)

                # Verify that the secure EPGs are only providing/consuming from
                # secure EPGs
                contracts = []
                for secure_epg in secure_epgs:
                    for contract in secure_epg.get_all_provided():
                        for nonsecure_epg in nonsecure_epgs:
                            if nonsecure_epg.does_consume(contract):
                                print ("Critical 001: Nonsecure EPG '%s' in tenant '%s' "
                                       "is consuming secure contract from 'EPG' %s" % (nonsecure_epg.name,
                                                                                       tenant.name,
                                                                                       secure_epg.name))
                    for contract in secure_epg.get_all_consumed():
                        for nonsecure_epg in nonsecure_epgs:
                            print 'consumed ', contract.name
                            if nonsecure_epg.does_provide(contract):
                                print ("Critical 001: Nonsecure EPG '%s' in tenant '%s' "
                                       "is providing contract to secure EPG '%s'" % (nonsecure_epg.name,
                                                                                     tenant.name,
                                                                                     secure_epg.name))

    def execute(self, methods):
        for method in methods:
            getattr(self, method)()


def acilint():
    """
    Main execution routine

    :return: None
    """
    description = ('acilint - A static configuration analysis tool. '
                   'Checks can be individually disabled by generating'
                   ' and editing a configuration file.  If no config '
                   'file is given, all checks will be run.')
    creds = Credentials('apic', description)
    creds.add_argument('-c', '--configfile', type=argparse.FileType('r'))
    creds.add_argument('-g', '--generateconfigfile',
                       type=argparse.FileType('w'))
    args = creds.get()

    if args.generateconfigfile:
        print 'Generating configuration file....'
        f = args.generateconfigfile
        f.write(('# acilint configuration file\n# Remove or comment out any '
                 'warnings or errors that you no longer wish to see\n'))
        methods = dir(Checker)
        for method in methods:
            if method.startswith(('warning_', 'critical_', 'error_')):
                f.write(method + '\n')
        f.close()
        sys.exit(0)

    methods = []
    if args.configfile:
        f = args.configfile
        for line in f:
            method = line.split('\n')[0]
            if method in dir(Checker) and method.startswith(('warning_', 'error_', 'critical_')):
                methods.append(method)
        f.close()
    else:
        for method in dir(Checker):
            if method.startswith(('warning_', 'error_', 'critical_')):
                methods.append(method)

    if args.snapshotfiles:
        session = FakeSession(filenames=args.snapshotfiles)
    else:
        # Login to APIC
        session = Session(args.url, args.login, args.password)
        resp = session.login()
        if not resp.ok:
            print '%% Could not login to APIC'
            sys.exit(0)

    checker = Checker(session)
    checker.execute(methods)

if __name__ == "__main__":
    acilint()
