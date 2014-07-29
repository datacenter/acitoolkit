"""  Main ACI Toolkit module
     This is the main module that comprises the ACI Toolkit
"""
from acibaseobject import BaseACIObject, BaseRelation
from acisession import Session
import json
import logging


class Tenant(BaseACIObject):
    """ Tenant :  roughly equivalent to fvTenant """
    def get_json(self):
        """ Returns json representation of the fvTenant object

        INPUT:
        RETURNS: json dictionary of fvTenant
        """
        return super(Tenant, self).get_json('fvTenant', attributes={})

    @classmethod
    def get(cls, session):
        """Gets all of the tenants from the APIC.

        INPUT: session
        RETURNS: List of Tenant objects
        """
        return BaseACIObject.get(session, cls, 'fvTenant')

    @classmethod
    def exists(cls, session, tenant):
        """Check if a tenant exists on the APIC.

        INPUT: session, tenant
        RETURNS: boolean
        """
        apic_tenants = cls.get(session)
        for apic_tenant in apic_tenants:
            if tenant == apic_tenant:
                return True
        return False

    @staticmethod
    def get_url(fmt='json'):
        """Get the URL used to push the configuration to the APIC
        if no fmt parameter is specified, the format will be 'json'
        otherwise it will return '/api/mo/uni.' with the fmt string appended.

        INPUT: optional fmt string
        RETURNS: URL string
        """
        return '/api/mo/uni.' + fmt


class AppProfile(BaseACIObject):
    """ AppProfile :  roughly equivalent to fvAp """
    def __init__(self, name, parent):
        if not isinstance(parent, Tenant):
            raise TypeError('Parent must be of Tenant class')
        super(AppProfile, self).__init__(name, parent)

    def get_json(self):
        """ Returns json representation of the fvAp object

        INPUT:
        RETURNS: json dictionary of fvAp
        """
        return super(AppProfile, self).get_json('fvAp', attributes={})

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Application Profiles from the APIC.

        INPUT: session, tenant
        RETURNS: List of AppProfile objects
        """
        return BaseACIObject.get(session, cls, 'fvAp', parent=tenant,
                                 tenant=tenant)

    def _get_url_extension(self):
        return '/ap-%s' % self.name


class L2Interface(BaseACIObject):
    """ Creates a L2 interface that can be attached to a physical interface.
        This interface defines the L2 encapsulation i.e. VLAN, VXLAN, or NVGRE
    """
    def __init__(self, name, encap_type, encap_id):
        super(L2Interface, self).__init__(name)
        if encap_type not in ('vlan', 'vxlan', 'nvgre'):
            raise ValueError("Encap type must be one of 'vlan',"
                             " 'vxlan', or 'nvgre'")
        self.encap_type = encap_type
        self.encap_id = encap_id

    def is_interface(self):
        return True

    def get_encap_type(self):
        """Get the encap_type of the L2 interface.
           Valid values are 'vlan', 'vxlan', and 'nvgre'
        """
        return self.encap_type

    def get_encap_id(self):
        """Get the encap_id of the L2 interface.
           The value is returned as a string and depends on the encap_type
           (i.e. VLAN VID, VXLAN VNID, or NVGRE VSID)
        """
        return self.encap_id

    def get_path(self):
        """Get the path of this interface used when communicating with
           the APIC object model.
        """
        for relation in self._relations:
            if relation.item.is_interface():
                return relation.item.get_path()


class CommonEPG(BaseACIObject):
    """ Base class for EPG and OutsideEPG.
        Not meant to be instantiated directly
    """
    def __init__(self, epg_name, parent=None):
        super(CommonEPG, self).__init__(epg_name, parent)

    # Contract references
    def provide(self, contract):
        """ Make this EPG provide a Contract

        INPUT: Contract
        RETURNS: True
        """
        if self.does_provide(contract):
            return True
        self._add_relation(contract, 'provided')
        return True

    def does_provide(self, contract):
        """ Check if this EPG provides a specific Contract.
        True if the EPG does provide the Contract

        INPUT: Contract
        RETURNS: boolean
        """
        return self._has_relation(contract, 'provided')

    def dont_provide(self, contract):
        """ Make this EPG not provide a Contract

        INPUT: Contract
        RETURNS: True
        """
        self._remove_relation(contract, 'provided')

    def get_all_provided(self):
        """Get all of the Contracts provided by this EPG

        INPUT:
        RETURNS: List of Contract objects
        """
        return self._get_all_relation(Contract, 'provided')

    def consume(self, contract):
        """ Make this EPG consume a Contract

        INPUT: Contract
        RETURNS: True
        """

        if self.does_consume(contract):
            return True
        self._add_relation(contract, 'consumed')
        return True

    def does_consume(self, contract):
        """ Check if this EPG consumes a specific Contract

        INPUT: Contract
        RETURNS: boolean
        """
        return self._has_relation(contract, 'consumed')

    def dont_consume(self, contract):
        """ Make this EPG not consume a Contract.  It does not check to see
        if the Contract was already consumed

        INPUT: Contract
        RETURNS: True
        """
        self._remove_relation(contract, 'consumed')
        return True

    def get_all_consumed(self):
        """Get all of the Contracts consumed by this EPG

        INPUT:
        RETURNS: List of Contract objects
        """
        return self._get_all_relation(Contract, 'consumed')

    def get_interfaces(self, status='attached'):
        """Get all of the interfaces that this EPG is attached
        The default is to get list of 'attached' interfaces.
        If 'status' is set to 'detached' it will return the list of
        detached Interface objects

        INPUT: [status] defaults to 'attached'
        RETURNS: List of Interface objects
        """

        resp = []
        for relation in self._relations:
            if relation.item.is_interface() and relation.status == status:
                resp.append(relation.item)
        return resp

    def _get_common_json(self):
        """Internal routine to generate JSON common to EPGs and Outside EPGs"""
        children = []
        for contract in self.get_all_provided():
            text = {'fvRsProv': {'attributes': {'tnVzBrCPName':
                                                contract.name}}}
            children.append(text)
        for contract in self.get_all_consumed():
            text = {'fvRsCons': {'attributes': {'tnVzBrCPName':
                                                contract.name}}}
            children.append(text)
        return children

    @classmethod
    def get(cls, session, parent, tenant):
        """Gets all of the EPGs from the APIC.

        INPUT: session, parent, Tenant
        RETURNS: List of CommonEPG
        """
        return BaseACIObject.get(session, cls, 'fvAEPg', parent, tenant)


class EPG(CommonEPG):
    """ EPG :  roughly equivalent to fvAEPg """
    def __init__(self, epg_name, parent=None):
        """Initializes the EPG with a name and, optionally,
           an AppProfile parent.
           If the parent is specified and is not an AppProfile,
           an error will occur.

        INPUT: string, [AppProfile]
        RETURNS:
        """
        if not isinstance(parent, AppProfile):
            raise TypeError('Parent must be instance of AppProfile')
        super(EPG, self).__init__(epg_name, parent)

    # Bridge Domain references
    def add_bd(self, bridgedomain):
        """ Add BridgeDomain to the EPG, roughly equivalent to fvRsBd

        INPUT: BridgeDomain
        RETURNS:
        """
        if not isinstance(bridgedomain, BridgeDomain):
            raise TypeError('add_bd not called with BridgeDomain')
        self._remove_all_relation(BridgeDomain)
        self._add_relation(bridgedomain)

    def remove_bd(self):
        """ Remove BridgeDomain from the EPG.
            Note that there should only be one BridgeDomain attached
            to the EPG.
        INPUT:
        RETURNS:
        """
        self._remove_all_relation(BridgeDomain)

    def get_bd(self):
        """ Return the assigned BridgeDomain.
            There should only be one item in the returned list.

        INPUT:
        RETURNS: List of BridgeDomain objects
        """

        return self._get_any_relation(BridgeDomain)

    def has_bd(self):
        """ Check if a BridgeDomain has been assigned to the EPG

        INPUT:
        RETURNS: boolean
        """
        return self._has_any_relation(BridgeDomain)

    # Output
    def get_json(self):
        """ Returns json representation of the EPG

        INPUT:
        RETURNS: json dictionary of the EPG
        """
        children = super(EPG, self)._get_common_json()
        if self.has_bd():
            text = {'fvRsBd': {'attributes': {'tnFvBDName':
                                              self.get_bd().name}}}
            children.append(text)
        for interface in self.get_interfaces():
            text = {'fvRsPathAtt': {'attributes':
                                    {'encap': '%s-%s' % (interface.encap_type,
                                                         interface.encap_id),
                                     'tDn': interface.get_path()}}}
            children.append(text)
        for interface in self.get_interfaces('detached'):
            text = {'fvRsPathAtt': {'attributes':
                                    {'encap': '%s-%s' % (interface.encap_type,
                                                         interface.encap_id),
                                     'status': 'deleted',
                                     'tDn': interface.get_path()}}}
            children.append(text)
        return super(EPG, self).get_json('fvAEPg',
                                         attributes={},
                                         children=children)


class OutsideEPG(CommonEPG):
    """Represents the EPG for external connectivity
    """
    def __init__(self, epg_name, parent=None):
        if not isinstance(parent, Tenant):
            raise TypeError('Parent is not set to Tenant')
        super(OutsideEPG, self).__init__(epg_name, parent)

    def get_json(self):
        """ Returns json representation of OutsideEPG

        INPUT:
        RETURNS: json dictionary of OutsideEPG
        """
        children = []
        for interface in self.get_interfaces():
            if interface.is_ospf():
                ospf_if = interface
                text = {'ospfExtP': {'attributes': {'areaId': ospf_if.area_id},
                                     'children': []}}
                children.append(text)
                text = {'l3extInstP': {'attributes': {'name': self.name},
                                       'children': []}}
                for network in ospf_if.networks:
                    subnet = {'l3extSubnet': {'attributes': {'ip': network},
                                              'children': []}}
                    contracts = super(OutsideEPG, self)._get_common_json()
                    text['l3extInstP']['children'].append(subnet)
                    for contract in contracts:
                        text['l3extInstP']['children'].append(contract)
                children.append(text)
        for interface in self.get_interfaces():
            text = interface.get_json()
            children.append(text)
        return super(OutsideEPG, self).get_json('l3extOut',
                                                attributes={},
                                                children=children)


class L3Interface(BaseACIObject):
    """ Creates a L3 interface that can be attached to a L2 interface.
        This interface defines the L3 address i.e. IPv4
    """
    def __init__(self, name):
        super(L3Interface, self).__init__(name)
        self._addr = None
        self._l3if_type = None

    def is_interface(self):
        """ Check if this is an interface object.

        INPUTS:
        RETURNS: True
        """

        return True

    def get_addr(self):
        """Get the L3 address assigned to this interface.
        The address is set via the L3Interface.set_addr() method

        INPUT:
        RETURNS: Address
        """
        return self._addr

    def set_addr(self, addr):
        """Set the L3 address assigned to this interface

        INPUT: L3 address
        RETURNS:
        """
        self._addr = addr

    def get_l3if_type(self):
        """Get the l3if_type of this L3 interface.
           Valid values are 'sub-interface', 'l3-port', and 'ext-svi'
        """
        return self._l3if_type

    def set_l3if_type(self, l3if_type):
        """Set the l3if_type of this L3 interface.
           Valid values are 'sub-interface', 'l3-port', and 'ext-svi'
        """
        if l3if_type not in ('sub-interface', 'l3-port', 'ext-svi'):
            raise ValueError("l3if_type is not one of 'sub-interface', "
                             "'l3-port', or 'ext-svi'")
        self._l3if_type = l3if_type

    # Context references
    def add_context(self, context):
        """ Add context to the EPG """
        if self.has_context():
            self.remove_context()
        self._add_relation(context)

    def remove_context(self):
        """ Remove context from the EPG """
        self._remove_all_relation(Context)

    def get_context(self):
        """ Return the assigned context """
        return self._get_any_relation(Context)

    def has_context(self):
        """ Check if the context has been assigned"""
        return self._has_any_relation(Context)

    def get_json(self):
        """ Returns json representation of L3Interface

        INPUT:
        RETURNS: json dictionary of L3Interface
        """
        text = {'l3extRsPathL3OutAtt':
                {'attributes':
                 {'encap': '%s-%s' % (self.get_interfaces()[0].encap_type,
                                      self.get_interfaces()[0].encap_id),
                  'ifInstT': self.get_l3if_type(),
                  'addr': self.get_addr(),
                  'tDn': self.get_interfaces()[0].get_path()},
                 'children': []}}
        return text


class OSPFInterface(BaseACIObject):
    """ Creates an OSPF router interface that can be attached to a L3 interface.
        This interface defines the OSPF area, authentication, etc.
    """
    def __init__(self, name, area_id=None):
        super(OSPFInterface, self).__init__(name)
        self.area_id = area_id
        self.auth_key = None
        self.auth_type = None
        self.auth_keyid = None
        self.networks = []

    def is_interface(self):
        return True

    @staticmethod
    def is_ospf():
        """Returns True if this interface is an OSPF interface"""
        return True

    def get_json(self):
        """ Returns json representation of OSPFInterface

        INPUT:
        RETURNS: json dictionary of OSPFInterface
        """
        text = {'ospfIfP': {'attributes': {'authKey': self.auth_key,
                                           'authKeyId': self.auth_keyid,
                                           'authType': self.auth_type,
                                           'name': self.name},
                            'children': []}}
        text = [text, self.get_interfaces()[0].get_json()]
        text = {'l3extLIfP': {'attributes': {'name': self.name},
                              'children': text}}
        text = {'l3extLNodeP': {'attributes': {'name': self.name},
                                'children': [text]}}
        return text


class OSPFRouter(BaseACIObject):
    """Represents the global settings of the OSPF Router
    """
    def __init__(self, name):
        super(OSPFRouter, self).__init__(name)
        self._router_id = None
        self._node = None


class BridgeDomain(BaseACIObject):
    """ BridgeDomain :  roughly equivalent to fvBD """
    def __init__(self, bd_name, parent=None):
        if parent is None or not isinstance(parent, Tenant):
            raise TypeError
        super(BridgeDomain, self).__init__(bd_name, parent)

    def get_json(self):
        """ Returns json representation of the bridge domain

        INPUT:
        RETURNS: json dictionary of bridge domain
        """

        children = []
        if self.has_context():
            text = {'fvRsCtx': {'attributes':
                                {'tnFvCtxName': self.get_context().name}}}
            children.append(text)
        return super(BridgeDomain, self).get_json('fvBD',
                                                  attributes={},
                                                  children=children)

    # Context references
    def add_context(self, context):
        """Set the Context for this BD """
        self._add_relation(context)

    def remove_context(self):
        """Remove the Context for this BD """
        self._remove_all_relation(Context)

    def get_context(self):
        """Get the Context for this BD """
        return self._get_any_relation(Context)

    def has_context(self):
        """Check if the Context has been set for this BD """
        return self._has_any_relation(Context)

    # Subnet
    def add_subnet(self, subnet):
        """Add a subnet to this BD"""
        if not isinstance(subnet, Subnet):
            raise TypeError('add_subnet requires a Subnet instance')
        if subnet.get_addr() is None:
            raise ValueError('Subnet address is not set')
        if subnet in self.get_subnets():
            return
        self.add_child(subnet)

    def remove_subnet(self, subnet):
        """Remove a subnet from this BD"""
        if not isinstance(subnet, Subnet):
            raise TypeError('remove_subnet requires a Subnet instance')
        self.remove_child(subnet)

    def get_subnets(self):
        """Get all of the subnets on this BD"""
        resp = []
        children = self.get_children()
        for child in children:
            if isinstance(child, Subnet):
                resp.append(child)
        return resp

    def has_subnet(self, subnet):
        """Check if the BD has this particular subnet"""
        if not isinstance(subnet, Subnet):
            raise TypeError('has_subnet requires a Subnet instance')
        if subnet.get_addr() is None:
            raise ValueError('Subnet address is not set')
        return self.has_child(subnet)

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Bridge Domains from the APIC.
        """
        return BaseACIObject.get(session, cls, 'fvBD', tenant, tenant)


class Subnet(BaseACIObject):
    """ Subnet :  roughly equivalent to fvSubnet """
    def __init__(self, subnet_name, parent=None):
        if not isinstance(parent, BridgeDomain):
            raise TypeError('Parent of Subnet class must be BridgeDomain')
        super(Subnet, self).__init__(subnet_name, parent)
        self._addr = None

    def get_addr(self):
        """Get the subnet address

        INPUT:
        RETURNS: The subnet address as a string in the form
                 of <ipaddr>/<mask>
        """
        return self._addr

    def set_addr(self, addr):
        """Set the subnet address

           INPUT: addr: The subnet address as a string in the form
                        of <ipaddr>/<mask>
        """
        if addr is None:
            raise TypeError('Address can not be set to None')
        self._addr = addr

    def get_json(self):
        """ Returns json representation of the subnet

        INPUT:
        RETURNS: json dictionary of subnet
        """
        attributes = {}
        if self.get_addr() is None:
            raise ValueError('Subnet address is not set')
        attributes['ip'] = self.get_addr()
        return super(Subnet, self).get_json('fvSubnet', attributes=attributes)

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Subnets from the APIC.
        """
        return BaseACIObject.get(session, cls, 'fvSubnet', tenant=tenant)


class Context(BaseACIObject):
    """ Context :  roughly equivalent to fvCtx """
    def __init__(self, context_name, parent=None):
        super(Context, self).__init__(context_name, parent)
        self._allow_all = False

    def set_allow_all(self, value=True):
        """Set the allow_all value.
           When set, contracts will not be enforced in this context.
        """
        self._allow_all = value

    def get_allow_all(self):
        """Get the allow_all value.
           When set, contracts will not be enforced in this context.
        """
        return self._allow_all

    def get_json(self):
        """ Returns json representation of fvCtx object

        INPUT:
        RETURNS: json dictionary of fvCtx object
        """
        attributes = {}
        if self.get_allow_all():
            attributes['pcEnfPref'] = 'unenforced'
        else:
            attributes['pcEnfPref'] = 'enforced'
        return super(Context, self).get_json('fvCtx', attributes=attributes)

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Contexts from the APIC.
        """
        return BaseACIObject.get(session, cls, 'fvCtx', tenant, tenant)


class BaseContract(BaseACIObject):
    """ BaseContract :  Base class for Contracts and Taboos """
    def __init__(self, contract_name, contract_type='vzBrCP', parent=None):
        super(BaseContract, self).__init__(contract_name, parent)
        self._scope = 'context'
        self._contract_type = contract_type

    def set_scope(self, scope):
        """Set the scope of this contract.
           Valid values are 'context', 'global', 'tenant', and
           'application-profile'
        """
        if scope not in ('context', 'global', 'tenant', 'application-profile'):
            raise ValueError
        self._scope = scope

    def get_scope(self):
        """Get the scope of this contract.
           Valid values are 'context', 'global', 'tenant', and
           'application-profile'
        """
        return self._scope

    def get_json(self):
        """ Returns json representation of the contract

        INPUT:
        RETURNS: json dictionary of the contract
        """
        resp_json = []
        if self._contract_type == 'vzBrCP':
            subj_code = 'vzSubj'
            subj_relation_code = 'vzRsSubjFiltAtt'
            attributes = {'scope': self.get_scope()}
        else:
            subj_code = 'vzTSubj'
            subj_relation_code = 'vzRsDenyRule'
            attributes = {}

        contract = super(BaseContract, self).get_json(self._contract_type,
                                                      attributes=attributes,
                                                      get_children=False)
        # Create a subject for every entry with a relation to the filter
        subjects = []
        for entry in self.get_children():
            subject_name = self.name + entry.name
            subject = {subj_code: {'attributes': {'name': subject_name}}}
            filt_name = subject_name
            filt = {subj_relation_code:
                    {'attributes': {'tnVzFilterName': filt_name}}}
            subject[subj_code]['children'] = [filt]
            subjects.append(subject)
        contract[self._contract_type]['children'] = subjects
        resp_json.append(contract)
        for entry in self.get_children():
            entry_json = entry.get_json()
            if entry_json is not None:
                resp_json.append(entry_json)
        return resp_json


class Contract(BaseContract):
    """ Contract :  Class for Contracts """
    def __init__(self, contract_name, parent=None):
        super(Contract, self).__init__(contract_name, 'vzBrCP', parent)


class Taboo(BaseContract):
    """ Taboo :  Class for Taboos """
    def __init__(self, contract_name, parent=None):
        super(Taboo, self).__init__(contract_name, 'vzTaboo', parent)


class FilterEntry(BaseACIObject):
    """ FilterEntry :  roughly equivalent to vzEntry """
    def __init__(self, name, applyToFrag, arpOpc, dFromPort, dToPort,
                 etherT, prot, sFromPort, sToPort, tcpRules, parent):
        self.applyToFrag = applyToFrag
        self.arpOpc = arpOpc
        self.dFromPort = dFromPort
        self.dToPort = dToPort
        self.etherT = etherT
        self.prot = prot
        self.sFromPort = sFromPort
        self.sToPort = sToPort
        self.tcpRules = tcpRules
        super(FilterEntry, self).__init__(name, parent)

    def get_json(self):
        """ Returns json representation of the FilterEntry

        INPUT:
        RETURNS: json dictionary of the FilterEntry
        """
        attributes = {'applyToFrag': self.applyToFrag,
                      'arpOpc': self.arpOpc,
                      'dFromPort': self.dFromPort,
                      'dToPort': self.dToPort,
                      'etherT': self.etherT,
                      'prot': self.prot,
                      'sFromPort': self.sFromPort,
                      'sToPort': self.sToPort,
                      'tcpRules': self.tcpRules}
        text = super(FilterEntry, self).get_json('vzEntry',
                                                 attributes=attributes)
        filter_name = self.get_parent().name + self.name
        text = {'vzFilter': {'attributes': {'name': filter_name},
                             'children': [text]}}
        return text


class Interface(BaseACIObject):
    """This class defines a physical interface.
    """
    def __init__(self, interface_type, pod, node, module, port, parent=None):
        self.interface_type = interface_type
        self.pod = pod
        self.node = node
        self.module = module
        self.port = port
        self.if_name = self.interface_type + ' ' + self.pod + '/'
        self.if_name += self.node + '/' + self.module + '/' + self.port
        super(Interface, self).__init__(self.if_name, None)
        self.porttype = ''
        self.adminstatus = ''
        self.speed = ''
        self.mtu = ''

    def is_interface(self):
        return True

    def get_json(self):
        """ Not implemented yet
        """
        pass

    def get_path(self):
        """Get the path of this interface used when communicating with
           the APIC object model.
        """
        return 'topology/pod-%s/paths-%s/pathep-[eth%s/%s]' % (self.pod,
                                                               self.node,
                                                               self.module,
                                                               self.port)

    @staticmethod
    def parse_name(name):
        """Parses a name that is of the form:
        <type> <pod>/<mod>/<port>
        """
        interface_type = name.split()[0]
        name = name.split()[1]
        (pod, node, module, port) = name.split('/')
        return interface_type, pod, node, module, port

    @staticmethod
    def parse_dn(dist_name):
        """Parses the pod, node, module, port from a
           distinguished name of the interface.
        """
        name = dist_name.split('/')
        pod = name[1].split('-')[1]
        node = name[2].split('-')[1]
        module = name[4].split('[')[1]
        interface_type = module[:3]
        module = module[3:]
        port = name[5].split(']')[0]
        return interface_type, pod, node, module, port

    @staticmethod
    def get(session):
        """Gets all of the physical interfaces from the APIC
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')
        interface_query_url = '/api/node/class/l1PhysIf.json?query-target=self'
        ret = session.get(interface_query_url)
        resp = []
        interface_data = ret.json()['imdata']
        for interface in interface_data:
            dist_name = str(interface['l1PhysIf']['attributes']['dn'])
            porttype = str(interface['l1PhysIf']['attributes']['portT'])
            adminstatus = str(interface['l1PhysIf']['attributes']['adminSt'])
            speed = str(interface['l1PhysIf']['attributes']['speed'])
            mtu = str(interface['l1PhysIf']['attributes']['mtu'])
            (interface_type, pod, node,
             module, port) = Interface.parse_dn(dist_name)
            interface_obj = Interface(interface_type, pod, node, module, port)
            interface_obj.porttype = porttype
            interface_obj.adminstatus = adminstatus
            interface_obj.speed = speed
            interface_obj.mtu = mtu
            resp.append(interface_obj)
        return resp

    def __str__(self):
        items = [self.if_name, '\t', self.porttype, '\t',
                 self.adminstatus, '\t', self.speed, '\t',
                 self.mtu]
        ret = ''.join(items)
        return ret


class PortChannel(BaseACIObject):
    """This class defines a port channel interface.
    """
    def __init__(self, name):
        super(PortChannel, self).__init__(name)
        self._interfaces = []
        self._nodes = []

    def attach(self, interface):
        """Attach an interface to this PortChannel"""
        if interface not in self._interfaces:
            self._interfaces.append(interface)
        self.update_nodes()

    def detach(self, interface):
        """Detach an interface from this PortChannel"""
        if interface in self._interfaces:
            self._interfaces.remove(interface)
        self.update_nodes()

    def update_nodes(self):
        """Updates the nodes that are participating in this PortChannel"""
        nodes = []
        for interface in self._interfaces:
            nodes.append(interface.node)
        self._nodes = set(nodes)

    def is_vpc(self):
        """Returns True if the PortChannel is a VPC"""
        return len(self._nodes) > 1

    def is_interface(self):
        """Returns True since a PortChannel is an interface"""
        return True

    def get_nodes(self):
        """ Returns a single node id or multiple node ids in the
            case that this is a VPC
        """
        return self._nodes

    def get_path(self):
        """Get the path of this interface used when communicating with
           the APIC object model.
        """
        assert len(self._interfaces)
        pod = self._interfaces[0].pod
        if self.is_vpc():
            (node1, node2) = self.get_nodes()
            path = 'topology/pod-%s/protpaths-%s-%s/pathep-[%s]' % (pod,
                                                                    node1,
                                                                    node2,
                                                                    self.name)
        else:
            node = self._interfaces[0].node
            path = 'topology/pod-%s/paths-%s/pathep-%s' % (pod,
                                                           node,
                                                           self.name)

        return path

    def get_json(self):
        """ Returns json representation of the PortChannel

        INPUT:
        RETURNS: json dictionary of the PortChannel
        """
        vpc = self.is_vpc()
        pc_mode = 'link'
        if vpc:
            pc_mode = 'node'
        infra = {'infraInfra': {'children': []}}
        # Add the node and port selectors
        for interface in self._interfaces:
            name = '%s-%s-%s-%s' % (interface.pod, interface.node,
                                    interface.module, interface.port)
            port_blk = {'name': name,
                        'fromCard': interface.module,
                        'toCard': interface.module,
                        'fromPort': interface.port,
                        'toPort': interface.port}
            port_blk = {'infraPortBlk': {'attributes': port_blk,
                                         'children': []}}
            pc_url = 'uni/infra/funcprof/accbundle-%s' % self.name
            accbasegrp = {'infraRsAccBaseGrp': {'attributes': {'tDn': pc_url},
                                                'children': []}}
            portselect = {'infraHPortS': {'attributes':
                                          {'name': name, 'type': 'range'},
                                          'children': [port_blk, accbasegrp]}}
            accport_selector = {'infraAccPortP': {'attributes': {'name': name},
                                                  'children': [portselect]}}
            node_blk = {'name': name,
                        'from_': interface.node, 'to_': interface.node}
            node_blk = {'infraNodeBlk': {'attributes':
                                         node_blk, 'children': []}}
            leaf_selector = {'infraLeafS': {'attributes':
                                            {'name': name, 'type': 'range'},
                                            'children': [node_blk]}}
            accport = {'infraRsAccPortP':
                       {'attributes': {'tDn':
                                       'uni/infra/accportprof-%s' % name},
                        'children': []}}
            node_profile = {'infraNodeP': {'attributes': {'name': name},
                                           'children': [leaf_selector,
                                                        accport]}}
            infra['infraInfra']['children'].append(node_profile)
            infra['infraInfra']['children'].append(accport_selector)
        # Add the actual port-channel
        accbndlgrp = {'infraAccBndlGrp':
                      {'attributes':
                       {'name': self.name, 'lagT': pc_mode},
                       'children': []}}
        infrafuncp = {'infraFuncP': {'attributes': {},
                                     'children': [accbndlgrp]}}
        infra['infraInfra']['children'].append(infrafuncp)

        if not vpc:
            return None, infra

        # VPC add Fabric Protocol Policy
        # Pick the lowest node as the unique id for the vpc group
        nodes = []
        for interface in self._interfaces:
            nodes.append(str(interface.node))
        unique_nodes = sorted(set(nodes))
        unique_id = unique_nodes[0]

        fabric_nodes = []
        for node in unique_nodes:
            fabric_node = {'fabricNodePEp': {'attributes': {'id': node}}}
            fabric_nodes.append(fabric_node)
        fabric_group = {'fabricExplicitGEp':
                        {'attributes':
                         {'name': 'vpc' + unique_id, 'id': unique_id},
                         'children': fabric_nodes}}
        fabric_prot_pol = {'fabricProtPol': {'attributes':
                                             {'name': 'vpc' + unique_id},
                                             'children': [fabric_group]}}

        return fabric_prot_pol, infra
