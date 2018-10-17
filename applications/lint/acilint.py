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
from acitoolkit.acitoolkit import Tenant, AppProfile, Context, EPG, BridgeDomain
from acitoolkit.acitoolkit import OutsideL3, OutsideEPG, OutsideNetwork
from acitoolkit.acitoolkit import Contract, ContractSubject, InputTerminal
from acitoolkit.acitoolkit import OutputTerminal, Filter, FilterEntry
from acitoolkit.acitoolkit import Credentials, Session
from acitoolkit.acifakeapic import FakeSession
import argparse
import ipaddress


class Checker(object):
    """
    Checker class contains a series of lint checks that are executed against the
    provided configuration.
    """
    def __init__(self, session, output, fh=None):
        print('Getting configuration from APIC....')
        self.tenants = Tenant.get_deep(session)
        self.output = output
        self.file = fh
        print('Processing configuration....')

    def output_handler(self, msg):
        """
        Print(the supplied string in a format appropriate to the output medium.)

        :param msg: The message to be printed.
        """
        if self.output == 'console':
            print(msg)
        elif self.output == 'html':

            color_map = {'Error': '#FF8C00',
                         'Critical': '#FF0000',
                         'Warning': '#FFFF00'}

            sev = msg.split(':')[0].split(' ')[0]
            rule = msg.split(':')[0].split(' ')[1]
            descr = msg.split(': ')[1]
            self.file.write("""
            <tr>
            <td bgcolor="{0}">{1}</td>
            <td bgcolor="{0}">{2}</td>
            <td bgcolor="{0}">{3}</td>
            </tr>
            """.format(color_map[sev], sev, rule, descr))

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
                self.output_handler("Warning 001: Tenant '%s' has no Application "
                                    "Profile." % tenant.name)

    def warning_002(self):
        """
        W002: Tenant has no context
        """
        for tenant in self.tenants:
            if len(tenant.get_children(Context)) == 0:
                self.output_handler("Warning 002: Tenant '%s' has no Context." % tenant.name)

    def warning_003(self):
        """
        W003: AppProfile has no EPGs
        """
        for tenant in self.tenants:
            for app in tenant.get_children(AppProfile):
                if len(app.get_children(EPG)) == 0:
                    self.output_handler("Warning 003: AppProfile '%s' in Tenant '%s'"
                                        "has no EPGs." % (app.name, tenant.name))

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
                self.output_handler("Warning 004: Context '%s' in Tenant '%s' has no "
                                    "BridgeDomains." % (context, tenant.name))

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
                self.output_handler("Warning 005: BridgeDomain '%s' in Tenant '%s'"
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
                self.output_handler("Warning 006: Contract '%s' in Tenant '%s' is not"
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
                self.output_handler("Warning 007: Contract '%s' in Tenant '%s' is not"
                                    " consumed at all." % (contract, tenant.name))

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
                                    self.output_handler("Warning 008: EPG '%s' providing "
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
            if tenant.name not in provide_db:
                self.output_handler("Warning 010: No contract provided within"
                                    " this tenant '%s'" % tenant.name)
                continue  # don't repeat this message for each option below.
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
                        if contract.name not in provide_db[tenant.name]:
                            self.output_handler("Warning 010: Contract '%s' not provided "
                                                "within the same tenant "
                                                "'%s'" % (contract.name, tenant.name))
                        elif context.name not in provide_db[tenant.name][contract.name]:
                            self.output_handler("Warning 010: Contract '%s' not provided in context '%s' "
                                                "where it is being consumed for"
                                                " tenant '%s'" % (contract.name, context.name, tenant.name))

    @staticmethod
    def subj_matches_proto(filterlist, protocol):
        """
        This routine will return True/False if the list of filters has a filter
        that matches the specified protocol.

        :param filterlist: The list of filters to inspect.
        :param protocol: The protocol we are looking for.
        """
        for subjfilter in filterlist:
            for entry in subjfilter.get_children(FilterEntry):
                entryAttrs = entry.get_attributes()
                if entryAttrs['prot'] == protocol:
                    return True
        return False

    def warning_011(self):
        """
        W011: Contract has Bidirectional TCP Subjects.
        """
        for tenant in self.tenants:
            for contract in tenant.get_children(Contract):
                is_tcp_bidi = 0
                for subject in contract.get_children(ContractSubject):
                    if self.subj_matches_proto(subject.get_filters(), 'tcp'):
                        is_tcp_bidi = 3
                        break

                    in_terminal = subject.get_children(InputTerminal)
                    out_terminal = subject.get_children(OutputTerminal)
                    if in_terminal:
                        in_filterlist = in_terminal[0].get_filters()
                    else:
                        in_filterlist = ()
                    if out_terminal:
                        out_filterlist = out_terminal[0].get_filters()
                    else:
                        out_filterlist = ()

                    if in_filterlist:
                        if self.subj_matches_proto(in_filterlist, 'tcp'):
                            is_tcp_bidi = 1
                    if out_filterlist:
                        if self.subj_matches_proto(out_filterlist, 'tcp'):
                            is_tcp_bidi += 1
                    # Otherwise, either there are no terminals so it's a permit
                    # everything which doesn't count.

                    if is_tcp_bidi:
                        break

                if is_tcp_bidi == 3:
                    self.output_handler("Warning 011: In tenant '%s' contract "
                                        "'%s' is a Bidirectional TCP contract."
                                        % (tenant.name, contract.name))
                elif is_tcp_bidi == 2:
                    self.output_handler("Warning 011: In tenant '%s' contract "
                                        "'%s' is an explictly "
                                        "Bidirectional TCP contract."
                                        % (tenant.name, contract.name))

    def warning_012(self):
        """
        W012: Contract has Bidirectional UDP Subjects.
        """
        for tenant in self.tenants:
            for contract in tenant.get_children(Contract):
                is_udp_bidi = 0
                for subject in contract.get_children(ContractSubject):
                    if self.subj_matches_proto(subject.get_filters(), 'udp'):
                        is_udp_bidi = 3
                        break

                    in_terminal = subject.get_children(InputTerminal)
                    out_terminal = subject.get_children(OutputTerminal)
                    if in_terminal:
                        in_filterlist = in_terminal[0].get_filters()
                    else:
                        in_filterlist = ()
                    if out_terminal:
                        out_filterlist = out_terminal[0].get_filters()
                    else:
                        out_filterlist = ()

                    if in_filterlist:
                        if self.subj_matches_proto(in_filterlist, 'udp'):
                            is_udp_bidi = 1
                    if out_filterlist:
                        if self.subj_matches_proto(out_filterlist, 'udp'):
                            is_udp_bidi += 1
                    # Otherwise, either there are no terminals so it's a permit
                    # everything which doesn't count.

                    if is_udp_bidi:
                        break

                if is_udp_bidi == 3:
                    self.output_handler("Warning 012: In tenant '%s' contract "
                                        "'%s' is a Bidirectional UDP contract."
                                        % (tenant.name, contract.name))
                elif is_udp_bidi == 2:
                    self.output_handler("Warning 012: In tenant '%s' contract "
                                        "'%s' is an explictly "
                                        "Bidirectional UDP contract."
                                        % (tenant.name, contract.name))

    def warning_013(self):
        """
        W013: Contract has no Subjects.
        """
        for tenant in self.tenants:
            for contract in tenant.get_children(Contract):
                if len(contract.get_children(ContractSubject)) == 0:
                    self.output_handler("Warning 013: In tenant '%s' contract "
                                        "'%s' has no Subjects."
                                        % (tenant.name, contract.name))

    def warning_014(self):
        """
        W014: Contract has Subjects with no Filters.
        """
        for tenant in self.tenants:
            for contract in tenant.get_children(Contract):
                missing_filter = False
                for subject in contract.get_children(ContractSubject):
                    if len(subject.get_filters()) == 0:
                        # No directly attached filters...
                        for terminal in subject.get_children(InputTerminal):
                            if len(terminal.get_filters()) == 0:
                                for out_terminal in subject.get_children(OutputTerminal):
                                    if len(out_terminal.get_filters()) == 0:
                                        missing_filter = True
                    if missing_filter:
                        self.output_handler("Warning 014: In tenant '%s' contract "
                                        "'%s' subject '%s' has no Filters." % (
                                        tenant.name, contract.name, subject.name))

    def error_001(self):
        """
        E001: BridgeDomain has no Context
        """
        for tenant in self.tenants:
            for bd in tenant.get_children(BridgeDomain):
                if not bd.has_context():
                    self.output_handler("Error 001: BridgeDomain '%s' in tenant '%s' "
                                        "has no Context assigned." % (bd.name, tenant.name))

    def error_002(self):
        """
        E002: EPG has no BD assigned.
        """
        for tenant in self.tenants:
            for app in tenant.get_children(AppProfile):
                for epg in app.get_children(EPG):
                    if not epg.has_bd():
                        self.output_handler("Error 002: EPG '%s' in Tenant '%s', "
                                            "AppProfile '%s' has no BridgeDomain "
                                            "assigned." % (epg.name, tenant.name,
                                                           app.name))

    def error_004(self):
        # E004: EPG not assigned to an interface or VMM domain
        pass

    def error_005(self):
        """
        E005: Overlapping subnets are defined in a single context.
        Note: Only subnets inside the fabric are inspected.
        """
        for tenant in self.tenants:
            context_info = {}
            for bd in tenant.get_children(BridgeDomain):
                current_context = bd.get_context()
                if not current_context:
                    # BridgeDomain has no Context so ignore it.
                    continue
                if current_context not in context_info:
                    context_info[current_context] = {'v4list': [],
                                                     'v6list': []}
                for subnet in bd.get_subnets():
                    ip_subnet = ipaddress.ip_network(unicode(subnet.addr),
                                                     strict=False)
                    index = 0
                    index_to_insert = 0
                    if ip_subnet.version == 4:
                        address_list = context_info[current_context]['v4list']
                    else:
                        address_list = context_info[current_context]['v6list']

                    while index < len(address_list):
                        if ip_subnet == address_list[index]['addr']:
                            index_to_insert = index
                            if bd.name != address_list[index]['bd']:
                                # Because sometimes they are equal...
                                self.output_handler(
                                    "Error 005: In tenant/context '{}/{}': "
                                    "subnet {} in BridgeDomain '{}' "
                                    "duplicated by subnet {} in BridgeDomain "
                                    "'{}'".format(tenant.name,
                                                  current_context,
                                                  ip_subnet.with_prefixlen,
                                                  bd.name,
                                                  address_list[index][
                                                      'addr'].with_prefixlen,
                                                  address_list[index]['bd']))
                        elif ip_subnet < address_list[index]['addr']:
                            index_to_insert = index + 1
                            if ip_subnet.overlaps(address_list[index]['addr']):
                                self.output_handler(
                                    "Error 005: In tenant/context '{}/{}': "
                                    "subnet {} in BridgeDomain '{}' "
                                    "contains subnet {} in BridgeDomain "
                                    "'{}'".format(tenant.name,
                                                  current_context,
                                                  ip_subnet.with_prefixlen,
                                                  bd.name,
                                                  address_list[index - 1][
                                                      'addr'].with_prefixlen,
                                                  address_list[index - 1]['bd']))
                            else:
                                break
                        elif address_list[index]['addr'].overlaps(ip_subnet):
                            index_to_insert = index
                            self.output_handler("Error 005: In tenant/context "
                                                "'{}/{}': subnet {} in "
                                                "BridgeDomain '{}' contains "
                                                "subnet {} in BridgeDomain "
                                                "'{}'".format(tenant.name,
                                                              current_context,
                                                              address_list[index][
                                                                  'addr'].with_prefixlen,
                                                              address_list[index]['bd'],
                                                              ip_subnet.with_prefixlen,
                                                              bd.name))
                            break
                        index += 1
                    if index_to_insert:
                        address_list.insert(index_to_insert, {'addr': ip_subnet,
                                                              'bd': bd.name})
                    else:
                        address_list.insert(index, {'addr': ip_subnet,
                                                    'bd': bd.name})

    def error_006(self):
        """
        E006: Check for duplicated subnets in ExternalNetworks.

        Check to ensure that the same subnet is not defined in two separate
        ExternalNetworks or between an ExternalNetwork and a BD within a
        single VRF. Overlapping but not the equal subnets are not a problem.
        """
        for tenant in self.tenants:
            context_set = {}
            for l3out in tenant.get_children(OutsideL3):
                current_ctxt = l3out.get_context()
                if not current_ctxt:
                    # OutsideL3 Network has no Context so ignore it.
                    continue
                if current_ctxt.name not in context_set:
                    context_set[current_ctxt.name] = {}
                current_subnets = context_set[current_ctxt.name]

                for extnet in l3out.get_children(OutsideEPG):
                    for subnet in extnet.get_children(OutsideNetwork):
                        if subnet.addr in current_subnets:
                            current_subnets[subnet.addr].append(
                                "{}/{}/{}/{}".format(tenant.name,
                                                     current_ctxt.name,
                                                     l3out.name,
                                                     extnet.name))
                        else:
                            current_subnets[subnet.addr] = [
                                "{}/{}/{}/{}".format(tenant.name,
                                                     current_ctxt.name,
                                                     l3out.name,
                                                     extnet.name)]
            for current_ctxt in context_set:
                for subnet in context_set[current_ctxt]:
                    if 1 < len(context_set[current_ctxt][subnet]):
                        for subnet_info in context_set[current_ctxt][subnet]:
                            self.output_handler(
                                "Error 006: In Tenant/Context/L3Out/ExtEPG "
                                "'{}' found duplicate subnet {}.".format(
                                    subnet_info, subnet))

            for bd in tenant.get_children(BridgeDomain):
                bd_ctxt = bd.get_context()
                if not bd_ctxt:
                    # BridgeDomain has no Context so ignore it.
                    continue
                if bd_ctxt.name not in context_set:
                    # BridgeDomain Context has no associated ExternalNetworks so ignore it.
                    continue
                for subnet in bd.get_subnets():
                    ip_subnet = ipaddress.ip_network(str(subnet.addr),
                                                     strict=False)
                    ip_subnet_str = ip_subnet.network_address
                    if ip_subnet_str in context_set[bd_ctxt.name]:
                        for subnet_info in context_set[bd_ctxt.name][ip_subnet_str]:
                            self.output_handler(
                                "Error 006: Subnet {0:s} in "
                                "Tenant/Context/BridgeDomain '{}/{}/{}' "
                                "conflicts with subnet {} in "
                                "Tenant/Context/L3Out/ExtEPG '{}'.".format(
                                    ip_subnet.with_prefixlen, tenant.name,
                                    bd_ctxt.name, bd.name, ip_subnet_str,
                                    subnet_info))

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
                        self.output_handler("Critical 001: EPG '%s' in tenant '%s' "
                                            "app '%s' is not assigned security "
                                            "clearance" % (epg.name, tenant.name, app.name))
                    if epg.has_tag('secure'):
                        if epg.has_tag('nonsecure'):
                            self.output_handler("Critical 001: EPG '%s' in tenant '%s' "
                                                "app '%s' is assigned secure and nonsecure security "
                                                "clearance" % (epg.name, tenant.name, app.name))
                            # Squirrel away the Secure EPGs
                        secure_epgs.append(epg)
                    else:
                        nonsecure_epgs.append(epg)

                # Verify that the secure EPGs are only providing/consuming from
                # secure EPGs
                for secure_epg in secure_epgs:
                    for contract in secure_epg.get_all_provided():
                        for nonsecure_epg in nonsecure_epgs:
                            if nonsecure_epg.does_consume(contract):
                                self.output_handler("Critical 001: Nonsecure EPG '%s' in tenant '%s' "
                                                    "is consuming secure contract from 'EPG' %s" % (nonsecure_epg.name,
                                                                                                    tenant.name,
                                                                                                    secure_epg.name))
                    for contract in secure_epg.get_all_consumed():
                        for nonsecure_epg in nonsecure_epgs:
                            if nonsecure_epg.does_provide(contract):
                                self.output_handler("Critical 001: Nonsecure EPG '%s' in tenant '%s' "
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
    creds.add_argument('-o', '--output', required=False, default='console')
    args = creds.get()
    if args.generateconfigfile:
        print('Generating configuration file....')
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
            print('%% Could not login to APIC')
            sys.exit(0)

    html = None
    if args.output == 'html':
        print('Creating file lint.html')
        html = open('lint.html', 'w')
        html.write("""
        <table border="2" style="width:100%">
        <tr>
        <th>Severity</th>
        <th>Rule</th>
        <th>Description</th>
        </tr>
        """)

    checker = Checker(session, args.output, html)
    checker.execute(methods)

if __name__ == "__main__":
    acilint()
