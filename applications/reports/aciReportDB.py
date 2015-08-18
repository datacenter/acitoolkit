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
This is the report generator for the aciReportGui application
"""
from acitoolkit.aciConcreteLib import ConcreteTunnel

__author__ = 'edsall'

from operator import itemgetter

import acitoolkit as ACI


class DisplayRecord(object):
    """
    This class holds all the information needed to display a report table
    """

    def __init__(self, tables, label, title=None):
        """
        Initializer
        """
        self.label = label
        if title is None:
            self.title = label
        else:
            self.title = title

        self.tables = tables
        self.children = []

    def add_child(self, child):
        """
        adds a child to the display record
        :param child:
        """
        self.children.append(child)

    def add_tables(self, tables):
        """
        Will add a list of tables to the tables list
        :param tables:
        """
        self.tables.extend(tables)


class LoginError(Exception):
    """
    Exception for login errors.
    """
    pass


class ReportDB(object):
    """
    This class holds all of the objects that a report can be generated for.
    """

    def __init__(self):
        """
        Initializer
        """
        self._session = None
        self.resp = None
        self.built_switches = {}
        self.built_tenants = {}
        self.args = None
        self.timeout = 2
        self.switches = {}
        self.all_switches = []

    def clear_switch_info(self):
        """
        This will clear out the switch info to force a reload of the switch information from the APIC.
        :return:
        """
        self.switches = {}
        self.built_switches = {}
        self._session = None

    def get_switches(self):

        """
        Method to load the basic switch information.  From this, a switch menu can be generated.

        :return:
        """
        result = []
        if not self.switches:
            self.all_switches = ACI.Node.get(self.session)

            for switch in self.all_switches:
                if switch.role != 'controller':
                    switch_id = switch.node
                    self.switches[switch_id] = switch

        for switch_id in self.switches:
            switch_name = self.switches[switch_id].name
            s_tuple = (switch_id, '{0:>3} : {1}'.format(switch_id, switch_name))
            result.append(s_tuple)
        return sorted(result, key=itemgetter(0))

    def get_tenants(self):
        """
        Return list of tenant names
        :return:
        """
        result = []
        tenants = ACI.Tenant.get(self.session)
        for tenant in tenants:
            result.append((tenant.name, tenant.name))
        return sorted(result, key=itemgetter(0))

    def get_switch_summary(self):
        """

        :return:
        """
        tables = ACI.Node.get_table(self.all_switches)
        return tables

    @staticmethod
    def get_switch_reports():
        """
        Gets a list of reports that can be generated for the switch. It is returned as tuples where
        the first item in the tuple is the key to the python dictionary where the report is stored and
        the second item is the text to display to the user.

        :return: list of tuples
        """
        return [('basic', 'Basic'),
                ('supervisorcard', 'Supervisor Card'),
                ('linecard', 'Linecard'),
                ('powersupply', 'Power Supply'),
                ('fantray', 'Fan Tray'),
                ('overlay', 'Overlay'),
                ('context', 'Context'),
                ('bridgedomain', 'Bridge (L2) Domain'),
                ('endpoint', 'Endpoint'),
                ('svi', 'SVI (Router Interface)'),
                ('accessrule', 'Access Rule'),
                ('arp', 'ARP'),
                ('portchannel', 'Port Channel (incl. VPC)')]

    @staticmethod
    def get_tenant_reports():

        """
        Gets a list of reports that can be generated for tenants. It is returned as tuples where
        the first item in the tuple is the key to the python dictionary where the report is stored and
        the second item is the text to display to the user.

        :return: list of tuples
        """
        return [('context', 'Context'),
                ('bridgedomain', 'Bridge Domain'),
                ('contract', 'Contract'),
                ('taboo', 'Taboo'),
                ('filter', 'Filter'),
                ('app_profile', 'Application Profile'),
                ('epg', 'Endpoint Group'),
                ('endpoint', 'Endpoint'),
                ]

    def build_switch(self, switch_id=None):
        """
        Will build the pivot table data structure for a switch
        :param switch_id:
        """
        result = {}
        switch = self.switches[switch_id]
        switch.populate_children(deep=True, include_concrete=True)
        result['basic'] = switch.get_table([switch])

        children_modules = switch.get_children(ACI.Linecard)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['linecard'] = tables

        children_modules = switch.get_children(ACI.Supervisorcard)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['supervisorcard'] = tables

        children_modules = switch.get_children(ACI.Fantray)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['fantray'] = tables

        children_modules = switch.get_children(ACI.Powersupply)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['powersupply'] = tables

        children_modules = switch.get_children(ACI.ConcreteArp)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['arp'] = tables

        result['endpoint'] = self.load_table(switch, ACI.ConcreteEp)
        result['context'] = self.load_table(switch, ACI.ConcreteContext)
        result['bridgedomain'] = self.load_table(switch, ACI.ConcreteBD)
        result['svi'] = self.load_table(switch, ACI.ConcreteSVI)
        result['accessrule'] = self.load_table(switch, ACI.ConcreteAccCtrlRule)
        result['accessrule'].extend(self.load_table(switch, ACI.ConcreteFilter))
        result['portchannel'] = self.load_table(switch, ACI.ConcretePortChannel)
        result['portchannel'].extend(self.load_table(switch, ACI.ConcreteVpc))
        overlays = switch.get_children(ACI.ConcreteOverlay)
        if overlays:
            result['overlay'] = ACI.ConcreteOverlay.get_table(overlays)
            tunnels = overlays[0].get_children(ConcreteTunnel)
            result['overlay'].extend(ConcreteTunnel.get_table(tunnels))

        return result

    def build_tenant(self, tenant_name=None):
        """
        Will build table data structure for a tenant
        :param tenant_name:
        """
        result = {}
        tenant = ACI.Tenant.get_deep(self.session, names=[str(tenant_name)])[0]
        child_name_object_map = {ACI.Context: 'context',
                                 ACI.BridgeDomain: 'bridgedomain',
                                 ACI.Contract: 'contract',
                                 ACI.Taboo: 'taboo',
                                 ACI.AppProfile: 'app_profile',
                                 }

        for tk_class in child_name_object_map:
            key = child_name_object_map[tk_class]
            objs = tenant.get_children(tk_class)
            result[key] = tk_class.get_table(objs)

        filters = []
        contracts = tenant.get_children(ACI.Contract)
        for contract in contracts:
            filter_entry = contract.get_children(ACI.FilterEntry)
            for filter in filter_entry:
                if filter not in filters:
                    filters.append(filter)
        result['filter'] = ACI.FilterEntry.get_table(filters)

        epgs = []
        app_profiles = tenant.get_children(ACI.AppProfile)
        for app_profile in app_profiles:
            epgs.extend(app_profile.get_children(ACI.EPG))
        result['epg'] = ACI.EPG.get_table(epgs)

        endpoints = []
        for epg in epgs:
            endpoints.extend(epg.get_children(ACI.Endpoint))

        result['endpoint'] = ACI.Endpoint.get_table(endpoints)

        return result

    @staticmethod
    def load_table(switch, aci_class):

        """

        :param switch:
        :param aci_class:
        :return:
        """
        children_modules = switch.get_children(aci_class)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        return tables

    @property
    def session(self):
        """
        session property will return an active session that has been logged in
        If a login had not previously occurred, it will proactively login first.
        :return: Session
        """
        if self._session is None:
            if self.args is not None:
                if self.args.login is not None:
                    self._session = ACI.Session(self.args.url, self.args.login, self.args.password)
                    resp = self.session.login(self.timeout)
                else:
                    raise LoginError
            else:
                raise LoginError
            if not resp.ok:
                raise LoginError
        return self._session

    def set_login_credentials(self, args, timeout=2):
        """
        Login to the APIC

        :param args: An instance containing the APIC credentials.  Expected to
                     have the following instance variables; url, login, and
                     password.
        :param timeout:  Optional integer argument that indicates the timeout
                         value in seconds to use for APIC communication.
                         Default value is 2.
        """
        self.args = args
        self.timeout = timeout
        self.clear_switch_info()

    def _get_from_apic(self, url):
        """
        Internal wrapper function for communicating with the APIC

        :returns: JSON dictionary of returned data
        """
        ret = self.session.get(url)
        data = ret.json()
        return data

    def get_switch_table(self, switch_id, report_id):
        """
        Will return a list of tables corresponding to the switch_id and report_id.

        :param switch_id:
        :param report_id:
        :return:
        """
        if switch_id not in self.built_switches:
            switch_record = self.build_switch(switch_id)
            self.built_switches[switch_id] = switch_record

        return self.built_switches[switch_id][report_id]

    def get_tenant_table(self, tenant_id, report_id):
        """
        Will cause the tenant info to be retrieved and then return the specified report

        :param tenant_id:
        :param report_id:
        :return:
        """

        if tenant_id not in self.built_tenants:
            tenant_record = self.build_tenant(tenant_id)
            self.built_tenants[tenant_id] = tenant_record
        return self.built_tenants[tenant_id][report_id]
