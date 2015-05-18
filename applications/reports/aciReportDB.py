__author__ = 'edsall'
import acitoolkit.acitoolkit as ACI
import acitoolkit.aciphysobject as ACI_PHYS
import acitoolkit.aciConcreteLib as ACI_CON


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
            self.all_switches = ACI_PHYS.Node.get(self.session)

            for switch in self.all_switches:
                if switch.role != 'controller':
                    switch_id = switch.node
                    self.switches[switch_id] = switch

        for switch_id in self.switches:
            switch_name = self.switches[switch_id].name
            s_tuple = (switch_id, '{0:>3} : {1}'.format(switch_id, switch_name))
            result.append(s_tuple)
        return sorted(result, key=lambda x: x[0])

    def get_switch_summary(self):
        """

        :return:
        """
        tables = ACI_PHYS.Node.get_table(self.all_switches)
        return tables

    def get_reports(self):


        return [('basic', 'Basic'),
                ('supervisorcard', 'Supervisor Card'),
                ('linecard', 'Linecard'),
                ('powersupply', 'Power Supply'),
                ('fantray', 'Fan Tray'),
                ('overlay', 'Overlay'),
                ('context', 'Context'),
                ('bridgedomain', 'Bridge (L2) Domain'),
                ('endpoint', 'Endpoint'),
                ('svi','SVI (Router Interface)'),
                ('accessrule', 'Access Rule'),
                ('arp', 'ARP'),
                ('portchannel', 'Port Channel (incl. VPC)')]

    def build_switch(self, switch_id=None):
        """
        Will build the pivot table data structure for a switch
        :param switch_id:
        """
        result = {}
        switch = self.switches[switch_id]
        switch.populate_children(deep=True, include_concrete=True)
        result['basic'] = switch.get_table([switch])

        children_modules = switch.get_children(ACI_PHYS.Linecard)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['linecard'] = tables

        children_modules = switch.get_children(ACI_PHYS.Supervisorcard)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['supervisorcard'] = tables

        children_modules = switch.get_children(ACI_PHYS.Fantray)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['fantray'] = tables

        children_modules = switch.get_children(ACI_PHYS.Powersupply)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['powersupply'] = tables

        children_modules = switch.get_children(ACI_CON.ConcreteArp)
        if children_modules:
            tables = children_modules[0].get_table(children_modules)
        else:
            tables = []
        result['arp'] = tables

        result['endpoint'] = self.load_table(switch, ACI_CON.ConcreteEp)
        result['context'] = self.load_table(switch, ACI_CON.ConcreteContext)
        result['bridgedomain'] = self.load_table(switch, ACI_CON.ConcreteBD)
        result['svi'] = self.load_table(switch, ACI_CON.ConcreteSVI)
        result['accessrule'] = self.load_table(switch, ACI_CON.ConcreteAccCtrlRule)
        result['accessrule'].extend(self.load_table(switch, ACI_CON.ConcreteFilter))
        result['portchannel'] = self.load_table(switch, ACI_CON.ConcretePortChannel)
        result['portchannel'].extend(self.load_table(switch, ACI_CON.ConcreteVpc))
        result['overlay'] = self.load_table(switch, ACI_CON.ConcreteOverlay)

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

    def get_table(self, switch_id, report_id):
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

