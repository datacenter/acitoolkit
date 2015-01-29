# Copyright (c) 2014 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
"""  Main ACI Toolkit module
     This is the main module that comprises the ACI Toolkit.
"""
from acibaseobject import BaseACIObject, BaseRelation
from acisession import Session
from acitoolkitlib import Credentials
# from aciphysobject import Linecard
import json
import logging
import re
import copy


class Tenant(BaseACIObject):
    """
    The Tenant class is used to represent the tenants within the acitoolkit
    object model.  In the APIC model, this class is roughly equivalent to
    the fvTenant class.
    """
    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append('fvTenant')
        return resp

    @staticmethod
    def _get_parent_class():
        return None

    def _get_instance_subscription_url(self):
        return '/api/mo/uni/tn-%s.json?subscription=yes' % self.name

    @staticmethod
    def _get_name_from_dn(dn):
        name = dn.split('uni/tn-')[1].split('/')[0]
        return name

    @staticmethod
    def _get_parent_dn(dn):
        return None

    def get_json(self):
        """
        Returns json representation of the fvTenant object

        :returns: A json dictionary of fvTenant
        """
        attr = self._generate_attributes()
        return super(Tenant, self).get_json(self._get_apic_classes()[0],
                                            attributes=attr)

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        return {
            'fvAp': AppProfile,
            'fvBD': BridgeDomain,
            'fvCtx': Context,
            'vzBrCP': Contract,
            'vzTaboo': Taboo,
            }

    @classmethod
    def get_deep(cls, session, names=[]):
        resp = []
        assert isinstance(names, list), ('names should be a list'
                                         ' of strings')

        # If no tenant names passed, get all tenant names from APIC
        if len(names) == 0:
            tenants = Tenant.get(session)
            for tenant in tenants:
                names.append(tenant.name)

        for name in names:
            query_url = ('/api/mo/uni/tn-%s.json?query-target=self&'
                         'rsp-subtree=full' % name)
            ret = session.get(query_url)
            data = ret.json()['imdata']
            obj = super(Tenant, cls).get_deep(full_data=data,
                                              working_data=data,
                                              parent=None)
            obj._extract_relationships(data)
            resp.append(obj)
        return resp

    @classmethod
    def get(cls, session):
        """
        Gets all of the tenants from the APIC.

        :param session: the instance of Session used for APIC communication
        :returns: a list of Tenant objects
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0])

    @classmethod
    def exists(cls, session, tenant):
        """
        Check if a tenant exists on the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant to check if exists on the APIC
        :returns: True or False
        """
        apic_tenants = cls.get(session)
        for apic_tenant in apic_tenants:
            if tenant == apic_tenant:
                return True
        return False

    @staticmethod
    def get_url(fmt='json'):
        """
        Get the URL used to push the configuration to the APIC
        if no format parameter is specified, the format will be 'json'
        otherwise it will return '/api/mo/uni.' with the format string
        appended.

        :param fmt: optional format string, default is 'json'
        :returns: URL string
        """
        return '/api/mo/uni.' + fmt


class AppProfile(BaseACIObject):
    """
    The AppProfile class is used to represent the Application Profiles within
    the acitoolkit object model.  In the APIC model, this class is roughly
    equivalent to the fvAp class.
    """
    def __init__(self, name, parent):
        """
        :param name: String containing the Application Profile name
        :param parent: An instance of Tenant class representing the Tenant\
                       which contains this Application Profile.
        """
        if not isinstance(parent, Tenant):
            raise TypeError('Parent must be of Tenant class')
        super(AppProfile, self).__init__(name, parent)

    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append('fvAp')
        return resp

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        return {
            'fvAEPg': EPG,
            }

    @staticmethod
    def _get_parent_class():
        return Tenant

    @staticmethod
    def _get_parent_dn(dn):
        return dn.split('/ap-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        if '/LDevInst-' in dn:
            return 'ServiceGraph'
        name = dn.split('/ap-')[1].split('/')[0]
        return name

    def get_json(self):
        """
        Returns json representation of the AppProfile object.

        :returns: json dictionary of fvAp
        """
        attr = self._generate_attributes()
        return super(AppProfile, self).get_json(self._get_apic_classes()[0],
                                                attributes=attr)

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Application Profiles from the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant used to limit the Application\
                       Profiles retreived from the APIC
        :returns: List of AppProfile objects
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 parent=tenant, tenant=tenant)

    def _get_url_extension(self):
        return '/ap-%s' % self.name


class L2Interface(BaseACIObject):
    """ The L2Interface class creates an logical L2 interface that can be\
        attached to a physical interface. This interface defines the L2\
        encapsulation i.e. VLAN, VXLAN, or NVGRE
    """
    def __init__(self, name, encap_type, encap_id):
        """
        :param name: String containing the L2Interface instance name
        :param encap_type: String containing the encapsulation type.\
        Valid values are 'VLAN', 'VXLAN', or 'NVGRE'.
        :param encap_id: String containing the encapsulation specific\
        identifier representing the virtual L2 network (i.e. for VXLAN,\
        this is the numeric value of the VNID).
        """
        super(L2Interface, self).__init__(name)
        if encap_type not in ('vlan', 'vxlan', 'nvgre'):
            raise ValueError("Encap type must be one of 'vlan',"
                             " 'vxlan', or 'nvgre'")
        self.encap_type = encap_type
        self.encap_id = encap_id

    def is_interface(self):
        """
        Returns whether this instance is considered an interface.

        :returns: True
        """
        return True

    def get_encap_type(self):
        """
        Get the encap_type of the L2 interface.
        Valid values are 'vlan', 'vxlan', and 'nvgre'

        :returns: String containing encap_type value.
        """
        return self.encap_type

    def get_encap_id(self):
        """
        Get the encap_id of the L2 interface.
        The value is returned as a string and depends on the encap_type
        (i.e. VLAN VID, VXLAN VNID, or NVGRE VSID)

        :returns: String containing encapsulation identifier value.
        """
        return self.encap_id

    def _get_path(self):
        """
        Get the path of this interface used when communicating with\
        the APIC object model.

        :returns: String containing the path
        """
        for relation in self._relations:
            if relation.item.is_interface():
                return relation.item._get_path()


class CommonEPG(BaseACIObject):
    """
    Base class for EPG and OutsideEPG.
    Not meant to be instantiated directly
    """
    def __init__(self, epg_name, parent=None):
        """
        :param epg_name: String containing the name of this EPG
        :param parent: Instance of the AppProfile class representing\
                       the Application Profile where this EPG is contained.
        """
        super(CommonEPG, self).__init__(epg_name, parent)

    # Contract references
    def provide(self, contract):
        """
        Make this EPG provide a Contract

        :param contract: Instance of Contract class to be provided by this EPG.
        :returns: True
        """
        if self.does_provide(contract):
            return True
        self._add_relation(contract, 'provided')
        return True

    def does_provide(self, contract):
        """
        Check if this EPG provides a specific Contract.

        :param contract: Instance of Contract class to check if it is\
                         provided by this EPG.
        :returns: True or False.  True if the EPG does provide the Contract.
        """
        return self._has_relation(contract, 'provided')

    def dont_provide(self, contract):
        """
        Make this EPG not provide a Contract

        :param contract: Instance of Contract class to be no longer provided\
                         by this EPG.
        :returns: True
        """
        self._remove_relation(contract, 'provided')

    def get_all_provided(self):
        """
        Get all of the Contracts provided by this EPG

        :returns: List of Contract objects that are provided by the EPG.
        """
        return self._get_all_relation(Contract, 'provided')

    def consume(self, contract):
        """
        Make this EPG consume a Contract

        :param contract: Contract class instance to be consumed by this EPG.
        :returns: True
        """

        if self.does_consume(contract):
            return True
        self._add_relation(contract, 'consumed')
        return True

    def does_consume(self, contract):
        """
        Check if this EPG consumes a specific Contract

        :param contract: Instance of Contract class to check if it is\
                         consumed by this EPG.
        :returns: True or False.  True if the EPG does consume the Contract.
        """
        return self._has_relation(contract, 'consumed')

    def dont_consume(self, contract):
        """
        Make this EPG not consume a Contract.  It does not check to see
        if the Contract was already consumed

        :param contract: Instance of Contract class to be no longer consumed\
                         by this EPG.
        :returns: True
        """
        self._remove_relation(contract, 'consumed')
        return True

    def get_all_consumed(self):
        """
        Get all of the Contracts consumed by this EPG

        :returns: List of Contract objects that are consumed by the EPG.
        """
        return self._get_all_relation(Contract, 'consumed')

    def get_interfaces(self, status='attached'):
        """
        Get all of the interfaces that this EPG is attached.
        The default is to get list of 'attached' interfaces.
        If 'status' is set to 'detached' it will return the list of
        detached Interface objects (Those EPGs which are no longer
        attached to an Interface, but the configuration is not yet
        pushed to the APIC.)

        :param status: 'attached' or 'detached'.  Defaults to 'attached'.
        :returns: List of Interface objects
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

        :param session: the instance of Session used for APIC communication
        :param parent: Instance of the AppProfile class used to limit the EPGs\
                       retreived from the APIC.
        :param tenant: Instance of Tenant class used to limit the EPGs\
                       retreived from the APIC.
        :returns: List of CommonEPG instances (or EPG instances if called\
                  from EPG class)
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 parent, tenant)


class EPG(CommonEPG):
    """ EPG :  roughly equivalent to fvAEPg """
    def __init__(self, epg_name, parent=None):
        """
        Initializes the EPG with a name and, optionally,
        an AppProfile parent.
        If the parent is specified and is not an AppProfile,
        an error will occur.

        :param epg_name: String containing the name of the EPG.
        :param parent: Instance of the AppProfile class representing\
                       the Application Profile where this EPG is contained.
        """
        if not isinstance(parent, AppProfile):
            raise TypeError('Parent must be instance of AppProfile')
        super(EPG, self).__init__(epg_name, parent)

    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append('fvAEPg')
        return resp

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        return {
            'fvCEp': Endpoint,
            'fvStCEp': Endpoint,
            }

    @staticmethod
    def _get_parent_class():
        return AppProfile

    @staticmethod
    def _get_parent_dn(dn):
        return dn.split('/epg-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        if '/LDevInst-' in dn:
            return 'ServiceGraph'
        return dn.split('/epg-')[1].split('/')[0]

    # Bridge Domain references
    def add_bd(self, bridgedomain):
        """
        Add BridgeDomain to the EPG, roughly equivalent to fvRsBd

        :param bridgedomain: Instance of BridgeDomain class.  Represents\
                             the BridgeDomain that this EPG will be assigned.\
                             An EPG can only be assigned to a single\
                             BridgeDomain.
        """
        if not isinstance(bridgedomain, BridgeDomain):
            raise TypeError('add_bd not called with BridgeDomain')
        self._remove_all_relation(BridgeDomain)
        self._add_relation(bridgedomain)

    def remove_bd(self):
        """
        Remove BridgeDomain from the EPG.
        Note that there should only be one BridgeDomain attached to the EPG.
        """
        self._remove_all_relation(BridgeDomain)

    def get_bd(self):
        """
        Return the assigned BridgeDomain.
        There should only be one item in the returned list.

        :returns: List of BridgeDomain objects
        """
        return self._get_any_relation(BridgeDomain)

    def has_bd(self):
        """
        Check if a BridgeDomain has been assigned to the EPG

        :returns: True or False.  True if the EPG has been assigned\
                  a BridgeDomain.
        """
        return self._has_any_relation(BridgeDomain)

    def _extract_relationships(self, data):
        app_profile = self.get_parent()
        tenant = app_profile.get_parent()
        tenant_children = data[0]['fvTenant']['children']
        epg_children = None
        for app in tenant_children:
            if 'fvAp' in app:
                if app['fvAp']['attributes']['name'] == app_profile.name:
                    for epg in app['fvAp']['children']:
                        if 'fvAEPg' in epg:
                            if epg['fvAEPg']['attributes']['name'] == self.name:
                                epg_children = epg['fvAEPg']['children']
        for child in epg_children:
            if 'fvRsBd' in child:
                bd_name = child['fvRsBd']['attributes']['tnFvBDName']
                bd_search = Search()
                bd_search.name = bd_name
                objs = tenant.find(bd_search)
                for bd in objs:
                    if isinstance(bd, BridgeDomain):
                        self.add_bd(bd)
            elif 'fvRsPathAtt' in child:
                pass
            elif 'fvRsProv' in child:
                contract_name = child['fvRsProv']['attributes']['tnVzBrCPName']
                contract_search = Search()
                contract_search.name = contract_name
                objs = tenant.find(contract_search)
                for contract in objs:
                    if isinstance(contract, Contract):
                        self.provide(contract)
            elif 'fvRsCons' in child:
                contract_name = child['fvRsCons']['attributes']['tnVzBrCPName']
                contract_search = Search()
                contract_search.name = contract_name
                objs = tenant.find(contract_search)
                for contract in objs:
                    if isinstance(contract, Contract):
                        self.consume(contract)
        super(EPG, self)._extract_relationships(data)

    # Output
    def get_json(self):
        """
        Returns json representation of the EPG

        :returns: json dictionary of the EPG
        """
        children = super(EPG, self)._get_common_json()
        if self.has_bd():
            text = {'fvRsBd': {'attributes': {'tnFvBDName':
                                              self.get_bd().name}}}
            children.append(text)
        is_interfaces = False
        for interface in self.get_interfaces():
            is_interfaces = True
            encap_text = '%s-%s' % (interface.encap_type,
                                    interface.encap_id)
            text = {'fvRsPathAtt': {'attributes':
                                    {'encap': encap_text,
                                     'tDn': interface._get_path()}}}
            children.append(text)

            for ep in interface.get_all_attachments(Endpoint):
                path = interface._get_path()
                text = {'fvStCEp': {'attributes':
                                    {'ip': ep.ip,
                                     'mac': ep.mac,
                                     'name': ep.name,
                                     'encap': encap_text,
                                     'type': 'silent-host'},
                                    'children': [{'fvRsStCEpToPathEp':
                                                  {'attributes':
                                                   {'tDn': path},
                                                   'children': []}}]}}
                if ep.is_deleted():
                    text['fvStCEp']['attributes']['status'] = 'deleted'
                children.append(text)
        if is_interfaces:
            text = {'fvRsDomAtt': {'attributes':
                                   {'tDn': 'uni/phys-allvlans'}}}
            children.append(text)

        is_vmms = False
        for vmm in self.get_all_attached(VMM):
            is_vmms = True
            text = {'fvRsDomAtt': {'attributes':
                                   {'tDn': vmm._get_path(),
                                    'resImedcy': 'immediate'}}}
            children.append(text)

        for interface in self.get_interfaces('detached'):
            text = {'fvRsPathAtt': {'attributes':
                                    {'encap': '%s-%s' % (interface.encap_type,
                                                         interface.encap_id),
                                     'status': 'deleted',
                                     'tDn': interface._get_path()}}}
            children.append(text)
        attr = self._generate_attributes()
        return super(EPG, self).get_json(self._get_apic_classes()[0],
                                         attributes=attr,
                                         children=children)


class OutsideEPG(CommonEPG):
    """Represents the EPG for external connectivity
    """
    def __init__(self, epg_name, parent=None):
        """
        :param epg_name: String containing the name of this OutsideEPG
        :param parent: Instance of the Tenant class representing\
                       the tenant owning this OutsideEPG.
        """
        self.context = None
        if not isinstance(parent, Tenant):
            raise TypeError('Parent is not set to Tenant')
        super(OutsideEPG, self).__init__(epg_name, parent)

    def has_context(self):
        """
        Check if the context has been assigned

        :returns: True or False. True if a Context has been assigned to this\
                  L3Interface.
        """
        return self._has_any_relation(Context)

    def add_context(self, context):
        """
        Add context to the EPG

        :param context: Instance of Context class to assign to this\
                        L3Interface.
        """
        if self.has_context():
            self.remove_context()
        self._add_relation(context)

    def get_json(self):
        """
        Returns json representation of OutsideEPG

        :returns: json dictionary of OutsideEPG
        """
        children = []
        context = {"l3extRsEctx":{"attributes":{"tnFvCtxName":"Ohio-Demo-ctx1"},"children":[]}}
        children.append(context)
        for interface in self.get_interfaces():

            if hasattr(interface, 'is_ospf'):
                ospf_if = interface

                text = {'ospfExtP': {'attributes': {'areaId': ospf_if.area_id},
                                     'children': []}
                        }
                children.append(text)

            elif hasattr(interface,'is_bgp'):
                bgp_if = interface
                text = {"bgpExtP":{"attributes":{}}}
                children.append(text)


            text = {'l3extInstP': {'attributes': {'name': self.name},
                                       'children': []}}
            for network in interface.networks:
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
        attr = self._generate_attributes()
        return super(OutsideEPG, self).get_json('l3extOut',
                                                attributes=attr,
                                                children=children)


class L3Interface(BaseACIObject):
    """
    Creates an L3 interface that can be attached to an L2 interface.
    This interface defines the L3 address i.e. IPv4
    """
    def __init__(self, name):
        """
        :param name:  String containing the name of this L3Interface object.
        """
        super(L3Interface, self).__init__(name)
        self._addr = None
        self._l3if_type = None

    def is_interface(self):
        """
        Check if this is an interface object.

        :returns: True
        """

        return True

    def get_addr(self):
        """
        Get the L3 address assigned to this interface.
        The address is set via the L3Interface.set_addr() method

        :returns: String containing the L3 address in dotted decimal notation.
        """
        return self._addr

    def set_addr(self, addr):
        """
        Set the L3 address assigned to this interface

        :param addr: String containing the L3 address in dotted decimal\
                     notation.
        """
        self._addr = addr

    def get_l3if_type(self):
        """
        Get the l3if_type of this L3 interface.

        :returns: L3 interface type. Valid values are 'sub-interface',\
                  'l3-port', and 'ext-svi'
        """
        return self._l3if_type

    def set_l3if_type(self, l3if_type):
        """
        Set the l3if_type of this L3 interface.

        :param l3if_type: L3 interface type. Valid values are 'sub-interface',\
                          'l3-port', and 'ext-svi'
        """
        if l3if_type not in ('sub-interface', 'l3-port', 'ext-svi'):
            raise ValueError("l3if_type is not one of 'sub-interface', "
                             "'l3-port', or 'ext-svi'")
        self._l3if_type = l3if_type

    # Context references
    def add_context(self, context):
        """
        Add context to the EPG

        :param context: Instance of Context class to assign to this\
                        L3Interface.
        """
        if self.has_context():
            self.remove_context()
        self._add_relation(context)

    def remove_context(self):
        """
        Remove context from the EPG
        """
        self._remove_all_relation(Context)

    def get_context(self):
        """
        Return the assigned context

        :returns: Instance of Context class that this L3Interface is assigned.\
                  If no Context is assigned, None is returned.
        """
        return self._get_any_relation(Context)

    def has_context(self):
        """
        Check if the context has been assigned

        :returns: True or False. True if a Context has been assigned to this\
                  L3Interface.
        """
        return self._has_any_relation(Context)

    def get_json(self):
        """
        Returns json representation of L3Interface

        :returns: json dictionary of L3Interface
        """
        text = {'l3extRsPathL3OutAtt':
                {'attributes':
                 {'encap': '%s-%s' % (self.get_interfaces()[0].encap_type,
                                      self.get_interfaces()[0].encap_id),
                  'ifInstT': self.get_l3if_type(),
                  'addr': self.get_addr(),
                  'tDn': self.get_interfaces()[0]._get_path()},
                 'children': []}}
        return text


class OSPFInterface(BaseACIObject):
    """
    Creates an OSPF router interface that can be attached to a L3 interface.
    This interface defines the OSPF area, authentication, etc.
    """
    def __init__(self, name, area_id=None):
        """
        :param name:  String containing the name of this OSPFInterface object.
        :param area_id: String containing the OSPF area id of this interface.\
                        Default is None.
        """
        super(OSPFInterface, self).__init__(name)
        self.area_id = area_id
        self.auth_key = None
        self.auth_type = None
        self.auth_keyid = None
        self.networks = []

    def is_interface(self):
        """
        Returns whether this instance is considered an interface.

        :returns: True
        """
        return True

    @staticmethod
    def is_ospf():
        """
        :returns: True if this interface is an OSPF interface.  In the case\
                  of OSPFInterface instances, this is always True.
        """
        return True

    def get_json(self):
        """
        Returns json representation of OSPFInterface

        :returns: json dictionary of OSPFInterface
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


class BGPSession(BaseACIObject):
    """
    Creates an BGP router interface that can be attached to a L3 interface.
    This interface defines the BGP AS, authentication, etc.
    """
    def __init__(self, name, router_id=None,peer_ip=None,node_id=None):
        """
        :param name:  String containing the name of this BGPSession object.
        :param router_id: String containint the IPv4 router-id
        :param peer_ip: String containing the IP address of the BGP peer\
                        Default is None.
        :param node_id: String Containing the node-id (e.g. '101')
        """
        super(BGPSession, self).__init__(name)
        self.peer_ip = peer_ip
        self.router_id = router_id
        self.node_id = node_id
        self.options = ''
        self.networks = []

    def is_interface(self):
        """
        Returns whether this instance is considered an interface.

        :returns: True
        """
        return True

    @staticmethod
    def is_bgp():
        """
        :returns: True if this interface is an OSPF interface.  In the case\
                  of BGPSession instances, this is always True.
        """
        return True

    def get_json(self):
        """
        Returns json representation of BGPSession

        :returns: json dictionary of OSPFInterface
        """

        bgpextp = {"bgpExtP": {"attributes": {}}}
        bgpPeerP = {'bgpPeerP': {
                                'attributes': {
                                    'addr': self.peer_ip,
                                    'ctrl': self.options,
                                    "descr": "",
                                    'name': "",
                                }}}

        RsNode = { "l3extRsNodeL3OutAtt": {
                                "attributes": {
                                    "rtrId": self.router_id,
                                    "tDn": "topology/pod-1/node-%s" % self.node_id
                                }
                            }
                        },
        text = [self.get_interfaces()[0].get_json()]
        text = {'l3extLIfP': {'attributes': {'name': self.name},
                              'children': text}}

        text = {'l3extLNodeP': {'attributes': {'name': self.name},
                                'children': [RsNode,bgpPeerP,text]}}

        return text




class OSPFRouter(BaseACIObject):
    """
    Represents the global settings of the OSPF Router
    """
    def __init__(self, name):
        """
        :param name:  String containing the name of this OSPFRouter object.
        """
        super(OSPFRouter, self).__init__(name)
        self._router_id = None
        self._node = None


class BridgeDomain(BaseACIObject):
    """
    BridgeDomain :  roughly equivalent to fvBD
    """
    def __init__(self, bd_name, parent=None):
        """
        :param bd_name:  String containing the name of this BridgeDomain\
                         object.
        :param parent: An instance of Tenant class representing the Tenant\
                       which contains this BridgeDomain.
        """
        if parent is None or not isinstance(parent, Tenant):
            raise TypeError
        super(BridgeDomain, self).__init__(bd_name, parent)

    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append('fvBD')
        return resp

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        return {
            'fvSubnet': Subnet,
            }

    @staticmethod
    def _get_parent_class():
        return Tenant

    @staticmethod
    def _get_parent_dn(dn):
        return dn.split('/BD-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        return dn.split('/BD-')[1].split('/')[0]

    def get_json(self):
        """
        Returns json representation of the bridge domain

        :returns: json dictionary of bridge domain
        """
        children = []
        if self.has_context():
            text = {'fvRsCtx': {'attributes':
                                {'tnFvCtxName': self.get_context().name}}}
            children.append(text)
        attr = self._generate_attributes()
        return super(BridgeDomain, self).get_json(self._get_apic_classes()[0],
                                                  attributes=attr,
                                                  children=children)

    def _extract_relationships(self, data):
        tenant_children = data[0]['fvTenant']['children']
        for child in tenant_children:
            if 'fvBD' in child:
                bd_name = child['fvBD']['attributes']['name']
                if bd_name == self.name:
                    bd_children = child['fvBD']['children']
                    for bd_child in bd_children:
                        if 'fvRsCtx' in bd_child:
                            context_name = bd_child['fvRsCtx']['attributes']['tnFvCtxName']
                            tenant = self.get_parent()
                            context_search = Search()
                            context_search.name = context_name
                            objs = tenant.find(context_search)
                            for context in objs:
                                if isinstance(context, Context):
                                    self.add_context(context)
                    break
        super(BridgeDomain, self)._extract_relationships(data)

    # Context references
    def add_context(self, context):
        """
        Set the Context for this BD

        :param context: Context to assign this BridgeDomain
        """
        self._add_relation(context)

    def remove_context(self):
        """
        Remove the assigned Context from this BD
        """
        self._remove_all_relation(Context)

    def get_context(self):
        """
        Get the Context for this BD

        :returns: Instance of Context class that this BridgeDomain is assigned.
        """
        return self._get_any_relation(Context)

    def has_context(self):
        """
        Check if the Context has been set for this BD

        :returns: True or False. True if this BridgeDomain is assigned to a\
                  Context.
        """
        return self._has_any_relation(Context)

    # Subnet
    def add_subnet(self, subnet):
        """
        Add a subnet to this BD.

        :param subnet: Instance of Subnet class to add to this BridgeDomain.
        """
        if not isinstance(subnet, Subnet):
            raise TypeError('add_subnet requires a Subnet instance')
        if subnet.get_addr() is None:
            raise ValueError('Subnet address is not set')
        if subnet in self.get_subnets():
            return
        self.add_child(subnet)

    def remove_subnet(self, subnet):
        """
        Remove a subnet from this BD

        :param subnet: Instance of Subnet class to remove from this\
                       BridgeDomain.
        """
        if not isinstance(subnet, Subnet):
            raise TypeError('remove_subnet requires a Subnet instance')
        self.remove_child(subnet)

    def get_subnets(self):
        """
        Get all of the subnets on this BD.

        :returns: List of Subnet instances assigned to this BridgeDomain.
        """
        resp = []
        children = self.get_children()
        for child in children:
            if isinstance(child, Subnet):
                resp.append(child)
        return resp

    def has_subnet(self, subnet):
        """
        Check if the BD has this particular subnet.

        :returns: True or False.  True if this BridgeDomain has this\
                  particular Subnet.
        """
        if not isinstance(subnet, Subnet):
            raise TypeError('has_subnet requires a Subnet instance')
        if subnet.get_addr() is None:
            raise ValueError('Subnet address is not set')
        return self.has_child(subnet)

    @classmethod
    def get(cls, session, tenant):
        """
        Gets all of the Bridge Domains from the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant used to limit the BridgeDomain\
                       instances retreived from the APIC
        :returns: List of BridgeDomain objects
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 tenant, tenant)

    def _get_url_extension(self):
        return '/BD-%s' % self.name


class Subnet(BaseACIObject):
    """ Subnet :  roughly equivalent to fvSubnet """
    def __init__(self, subnet_name, parent=None):
        """
        :param subnet_name: String containing the name of this Subnet instance.
        :param parent: An instance of BridgeDomain class representing the\
                       BridgeDomain which contains this Subnet.
        """
        if not isinstance(parent, BridgeDomain):
            raise TypeError('Parent of Subnet class must be BridgeDomain')
        super(Subnet, self).__init__(subnet_name, parent)
        self._addr = None

    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append('fvSubnet')
        return resp

    def get_addr(self):
        """
        Get the subnet address

        :returns: The subnet address as a string in the form of <ipaddr>/<mask>
        """
        return self._addr

    def set_addr(self, addr):
        """
        Set the subnet address

        :param addr: The subnet address as a string in the form\
                     of <ipaddr>/<mask>
        """
        if addr is None:
            raise TypeError('Address can not be set to None')
        self._addr = addr

    def get_json(self):
        """
        Returns json representation of the subnet

        :returns: json dictionary of subnet
        """
        attributes = self._generate_attributes()
        if self.get_addr() is None:
            raise ValueError('Subnet address is not set')
        attributes['ip'] = self.get_addr()
        return super(Subnet, self).get_json('fvSubnet', attributes=attributes)

    def _populate_from_attributes(self, attributes):
        """
        Sets the attributes when creating objects from the APIC.
        Called from the base object when calling the classmethod get()
        """
        self.set_addr(attributes['ip'])

    def _extract_attributes(self, attributes):
        self.set_addr(str(attributes['ip']))

    @classmethod
    def get(cls, session, bridgedomain, tenant):
        """
        Gets all of the Subnets from the APIC for a particular tenant and
        bridgedomain.

        :param session: the instance of Session used for APIC communication
        :param bridgedomain: the instance of BridgeDomain used to limit the\
                             Subnet instances retreived from the APIC
        :param tenant: the instance of Tenant used to limit the Subnet\
                       instances retreived from the APIC
        :returns: List of Subnet objects

        """
        return BaseACIObject.get(session, cls, 'fvSubnet',
                                 parent=bridgedomain, tenant=tenant)


class Context(BaseACIObject):
    """ Context :  roughly equivalent to fvCtx """
    def __init__(self, context_name, parent=None):
        """
        :param context_name: String containing the Context name
        :param parent: An instance of Tenant class representing the Tenant\
                       which contains this Context.

        """
        super(Context, self).__init__(context_name, parent)
        self._allow_all = False

    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append('fvCtx')
        return resp

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        return {}

    @staticmethod
    def _get_parent_class():
        return Tenant

    @staticmethod
    def _get_parent_dn(dn):
        return dn.split('/ctx-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        return dn.split('/ctx-')[1].split('/')[0]

    def _extract_attributes(self, attributes):
        if attributes['pcEnfPref'] == 'unenforced':
            allow_all = True
        else:
            allow_all = False
        self.set_allow_all(allow_all)

    def set_allow_all(self, value=True):
        """
        Set the allow_all value. When set, contracts will not be enforced\
        in this context.

        :param value: True or False.  Default is True.
        """
        self._allow_all = value

    def get_allow_all(self):
        """
        Returns the allow_all value from this Context. When set, contracts\
        will not be enforced in this context.

        :returns:  True or False.
        """
        return self._allow_all

    def get_json(self):
        """
        Returns json representation of fvCtx object

        :returns: json dictionary of fvCtx object
        """
        attributes = self._generate_attributes()
        if self.get_allow_all():
            attributes['pcEnfPref'] = 'unenforced'
        else:
            attributes['pcEnfPref'] = 'enforced'
        return super(Context, self).get_json(self._get_apic_classes()[0],
                                             attributes=attributes)

    @classmethod
    def get(cls, session, tenant):
        """
        Gets all of the Contexts from the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant used to limit the Contexts\
                       retreived from the APIC
        :returns: List of Context objects
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 tenant, tenant)


class BaseContract(BaseACIObject):
    """ BaseContract :  Base class for Contracts and Taboos """
    def __init__(self, contract_name, contract_type='vzBrCP', parent=None):
        super(BaseContract, self).__init__(contract_name, parent)
        self._scope = 'context'

    @staticmethod
    def _get_contract_code():
        raise NotImplementedError

    @staticmethod
    def _get_subject_code():
        raise NotImplementedError

    @staticmethod
    def _get_subject_relation_code():
        raise NotImplementedError

    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append(cls._get_contract_code())
        return resp

    @staticmethod
    def _get_parent_class():
        return Tenant

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

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        return {}

    def get_json(self):
        """
        Returns json representation of the contract

        :returns: json dictionary of the contract
        """
        resp_json = []
        subj_code = self._get_subject_code()
        subj_relation_code = self._get_subject_relation_code()
        attributes = self._generate_attributes()

        contract_code = self._get_contract_code()
        contract = super(BaseContract, self).get_json(contract_code,
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
        contract[self._get_contract_code()]['children'] = subjects
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

    @staticmethod
    def _get_contract_code():
        return 'vzBrCP'

    @staticmethod
    def _get_subject_code():
        return 'vzSubj'

    @staticmethod
    def _get_subject_relation_code():
        return 'vzRsSubjFiltAtt'

    @staticmethod
    def _get_parent_dn(dn):
        return dn.split('/brc-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        name = dn.split('/brc-')[1].split('/')[0]
        return name

    def _generate_attributes(self):
        attributes = super(Contract, self)._generate_attributes()
        attributes['scope'] = self.get_scope()
        return attributes

    @classmethod
    def get_deep(cls, full_data, working_data, parent=None):
        contract_data = working_data[0]['vzBrCP']
        contract = Contract(str(contract_data['attributes']['name']),
                            parent)
                            
        if 'children' not in contract_data:
            return
            
        for child in contract_data['children']:
            if 'vzSubj' in child:
                subject = child['vzSubj']
                for subj_child in subject['children']:
                    if 'vzRsSubjFiltAtt' in subj_child:
                        filter_attributes = subj_child['vzRsSubjFiltAtt']['attributes']
                        filter_name = filter_attributes['rn'].split('rssubjFiltAtt-')[1]
                        for filter in full_data[0]['fvTenant']['children']:
                            if 'vzFilter' in filter:
                                match_name = filter['vzFilter']['attributes']['name']
                                if match_name == filter_name:
                                    for entry in filter['vzFilter']['children']:
                                        if 'vzEntry' in entry:
                                            entry_obj = FilterEntry.create_from_apic_json(entry, contract)

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Contracts from the APIC for a particular tenant.
        """
        return BaseACIObject.get(session, cls, cls._get_contract_code(),
                                 tenant, tenant)


class Taboo(BaseContract):
    """ Taboo :  Class for Taboos """
    def __init__(self, contract_name, parent=None):
        super(Taboo, self).__init__(contract_name, self._get_contract_code(),
                                    parent)

    @staticmethod
    def _get_contract_code():
        return 'vzTaboo'

    @staticmethod
    def _get_subject_code():
        return 'vzTSubj'

    @staticmethod
    def _get_subject_relation_code():
        return 'vzRsDenyRule'

    @staticmethod
    def _get_parent_dn(dn):
        return dn.split('/taboo-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        name = dn.split('/taboo-')[1].split('/')[0]
        return name


class FilterEntry(BaseACIObject):
    """ FilterEntry :  roughly equivalent to vzEntry """
    def __init__(self, name, parent, applyToFrag='0', arpOpc='0',
                 dFromPort='0', dToPort='0', etherT='0', prot='0',
                 sFromPort='0', sToPort='0', tcpRules='0'):
        """
        :param name: String containing the name of this FilterEntry instance.
        :param applyToFrag: True or False.  True indicates that this\
                            FilterEntry should be applied to IP fragments.
        :param arpOpc: 'req' or 'reply'.  Indicates that this FilterEntry\
                       should be applied to ARP Requests or ARP replies.
        :param dFromPort: String containing the lower L4 destination port\
                          number of the L4 destination port number range.
        :param dToPort: String containing the upper L4 destination port\
                        number of the L4 destination port number range.
        :param etherT: String containing the EtherType of the frame to be\
                       matched by this FilterEntry.
        :param prot: String containing the L4 protocol number to be\
                     matched by this FilterEntry.
        :param sFromPort: String containing the lower L4 source port\
                          number of the L4 source port number range.
        :param sToPort: String containing the upper L4 source port\
                        number of the L4 source port number range.
        :param tcpRules: Bit mask consisting of the TCP flags to be matched\
                         by this FilterEntry.
        """
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

    def _generate_attributes(self):
        attributes = super(FilterEntry, self)._generate_attributes()
        attributes['applyToFrag'] = self.applyToFrag
        attributes['arpOpc'] = self.arpOpc
        attributes['dFromPort'] = self.dFromPort
        attributes['dToPort'] = self.dToPort
        attributes['etherT'] = self.etherT
        attributes['prot'] = self.prot
        attributes['sFromPort'] = self.sFromPort
        attributes['sToPort'] = self.sToPort
        attributes['tcpRules'] = self.tcpRules
        return attributes

    def _extract_attributes(self, attributes):
        self.applyToFrag = str(attributes['applyToFrag'])
        self.arpOpc = str(attributes['arpOpc'])
        self.dFromPort = str(attributes['dFromPort'])
        self.dToPort = str(attributes['dToPort'])
        self.etherT = str(attributes['etherT'])
        self.prot = str(attributes['prot'])
        self.sFromPort = str(attributes['sFromPort'])
        self.sToPort = str(attributes['sToPort'])
        self.tcpRules = str(attributes['tcpRules'])

    def get_json(self):
        """
        Returns json representation of the FilterEntry

        :returns: json dictionary of the FilterEntry
        """
        attr = self._generate_attributes()
        text = super(FilterEntry, self).get_json('vzEntry',
                                                 attributes=attr)
        filter_name = self.get_parent().name + self.name
        text = {'vzFilter': {'attributes': {'name': filter_name},
                             'children': [text]}}
        return text

    @classmethod
    def get(cls, session, parent=None, tenant=None):
        """
        To get all of acitoolkit style Filter Entries APIC class.

        :param session:  the instance of Session used for APIC communication
        :param parent:  Object to assign as the parent to the created objects.
        :param tenant:  Tenant object to assign the created objects.
        """

        apic_class = 'vzRsSubjFiltAtt'

        if isinstance(tenant, str):
            raise TypeError
        logging.debug('%s.get called', cls.__name__)
        if tenant is None:
            tenant_url = ''
        else:
            tenant_url = '/tn-%s' % tenant.name
            if parent is not None:
                tenant_url = tenant_url + parent._get_url_extension()
        query_url = ('/api/mo/uni%s.json?query-target=subtree&'
                     'target-subtree-class=%s' % (tenant_url, apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)
        resp = []
        for object_data in data:
            dn = object_data['vzRsSubjFiltAtt']['attributes']['dn']
            tDn = object_data['vzRsSubjFiltAtt']['attributes']['tDn']
            tRn = object_data['vzRsSubjFiltAtt']['attributes']['tRn']
            names = ()
            if dn.split('/')[2][4:] == parent.name and dn.split('/')[4][len(apic_class)-1:] == dn.split('/')[3][5:] and dn.split('/')[3][5:] == tDn.split('/')[2][4:] and tDn.split('/')[2][4:] == tRn[4:]:
                name = str(object_data[apic_class]['attributes']['tRn'][4:])
                if name[:len(parent.name)] == parent.name and name[len(parent.name):] != '':
                    obj = cls(name[len(parent.name):], parent)
                    attribute_data = object_data[apic_class]['attributes']
                    obj._populate_from_attributes(attribute_data)
                    resp.append(obj)
        return resp

    @classmethod
    def create_from_apic_json(cls, data, parent):
        attributes = data['vzEntry']['attributes']
        entry = cls(name=str(attributes['name']),
                    parent=parent)
        entry._extract_attributes(attributes)
        return entry

    @classmethod
    def get_deep(cls, session, parent=None, tenant=None):
        """
        To get all of acitoolkit style Filter Entries APIC class.

        :param session:  the instance of Session used for APIC communication
        :param parent:  Object to assign as the parent to the created objects.
        :param tenant:  Tenant object to assign the created objects.
        """

        apic_class = 'vzRsSubjFiltAtt'

        if isinstance(tenant, str):
            raise TypeError
        logging.debug('%s.get called', cls.__name__)
        if tenant is None:
            tenant_url = ''
        else:
            tenant_url = '/tn-%s' % tenant.name
            if parent is not None:
                tenant_url = tenant_url + parent._get_url_extension()
        query_url = ('/api/mo/uni%s.json?query-target=subtree&'
                     'target-subtree-class=%s' % (tenant_url, apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)
        resp = []
        for object_data in data:
            dn = object_data['vzRsSubjFiltAtt']['attributes']['dn']
            tDn = object_data['vzRsSubjFiltAtt']['attributes']['tDn']
            tRn = object_data['vzRsSubjFiltAtt']['attributes']['tRn']
            names = ()
            if dn.split('/')[2][4:] == parent.name and dn.split('/')[4][len(apic_class)-1:] == dn.split('/')[3][5:] and dn.split('/')[3][5:] == tDn.split('/')[2][4:] and tDn.split('/')[2][4:] == tRn[4:]:
                name = str(object_data[apic_class]['attributes']['tRn'][4:])
                if name[:len(parent.name)] == parent.name and name[len(parent.name):] != '':
                    obj = cls(name[len(parent.name):], parent)
                    attribute_data = object_data[apic_class]['attributes']
                    obj._populate_from_attributes(attribute_data)
                    resp.append(obj)
        return resp


class BaseInterface(BaseACIObject):
    """Abstract class used to provide base functionality to other Interface
       classes.
    """
    def _get_port_selector_json(self, port_type, port_name):
        """Returns the json used for selecting the specified interfaces
        """
        name = self._get_name_for_json()
        port_blk = {'name': name,
                    'fromCard': self.module,
                    'toCard': self.module,
                    'fromPort': self.port,
                    'toPort': self.port}
        port_blk = {'infraPortBlk': {'attributes': port_blk,
                                     'children': []}}
        pc_url = 'uni/infra/funcprof/%s-%s' % (port_type, port_name)
        accbasegrp = {'infraRsAccBaseGrp': {'attributes': {'tDn': pc_url},
                                            'children': []}}
        portselect = {'infraHPortS': {'attributes': {'name': name,
                                                     'type': 'range'},
                                      'children': [port_blk, accbasegrp]}}
        accport_selector = {'infraAccPortP': {'attributes': {'name': name},
                                              'children': [portselect]}}
        node_blk = {'name': name,
                    'from_': self.node, 'to_': self.node}
        node_blk = {'infraNodeBlk': {'attributes': node_blk, 'children': []}}
        leaf_selector = {'infraLeafS': {'attributes': {'name': name,
                                                       'type': 'range'},
                                        'children': [node_blk]}}
        accport = {'infraRsAccPortP':
                   {'attributes': {'tDn': 'uni/infra/accportprof-%s' % name},
                    'children': []}}
        node_profile = {'infraNodeP': {'attributes': {'name': name},
                                       'children': [leaf_selector,
                                                    accport]}}
        return node_profile, accport_selector

    def get_port_selector_json(self):
        return self._get_port_selector_json('accportgrp',
                                            self._get_name_for_json())

    def get_port_channel_selector_json(self, port_name):
        return self._get_port_selector_json('accbundle', port_name)


class Interface(BaseInterface):
    """This class defines a physical interface.
    """
    def __init__(self, interface_type, pod, node, module, port,
                 parent=None, session=None, attributes={}):

        self._session = session
        self.attributes = {}
        self.attributes = copy.deepcopy(attributes)
        self.interface_type = str(interface_type)
        self.pod = str(pod)
        self.node = str(node)
        self.module = str(module)
        self.port = str(port)
        self.attributes['interface_type'] = str(interface_type)
        self.attributes['pod'] = str(pod)
        self.attributes['node'] = str(node)
        self.attributes['module'] = str(module)
        self.attributes['port'] = str(port)

        self.if_name = self.interface_type + ' ' + self.pod + '/'
        self.if_name += self.node + '/' + self.module + '/' + self.port
        self.attributes['if_name'] = self.if_name
        super(Interface, self).__init__(self.if_name, None)
        self.porttype = ''
        self.adminstatus = ''    # up or down
        self.speed = '10G'       # 100M, 1G, 10G or 40G
        self.mtu = ''
        self._cdp_config = None
        self._lldp_config = None
        self.type = 'interface'
        self.attributes['type'] = 'interface'
        self.id = interface_type+module+'/'+port

        self._parent = parent
        if parent:
            self._parent.add_child(self)
        self.stats = InterfaceStats(self, self.attributes.get('dist_name'))

    def is_interface(self):
        """
        Returns whether this instance is considered an interface.

        :returns: True
        """
        return True

    def is_cdp_enabled(self):
        """
        Returns whether this interface has CDP configured as enabled.

        :returns: True or False
        """
        return self._cdp_config == 'enabled'

    def is_cdp_disabled(self):
        """
        Returns whether this interface has CDP configured as disabled.

        :returns: True or False
        """
        return self._cdp_config == 'disabled'

    def enable_cdp(self):
        """
        Enables CDP on this interface.
        """
        self._cdp_config = 'enabled'

    def disable_cdp(self):
        """
        Disables CDP on this interface.
        """
        self._cdp_config = 'disabled'

    def is_lldp_enabled(self):
        """
        Returns whether this interface has LLDP configured as enabled.

        :returns: True or False
        """
        return self._lldp_config == 'enabled'

    def is_lldp_disabled(self):
        """
        Returns whether this interface has LLDP configured as disabled.

        :returns: True or False
        """
        return self._lldp_config == 'disabled'

    def enable_lldp(self):
        """
        Enables LLDP on this interface.
        """
        self._lldp_config = 'enabled'

    def disable_lldp(self):
        """
        Disables LLDP on this interface.
        """
        self._lldp_config = 'disabled'

    def get_type(self):
        return self.type

    def get_serial(self):
        return None

    def get_url(self):
        phys_domain_url = '/api/mo/uni.json'
        fabric_url = '/api/mo/uni/fabric.json'
        infra_url = '/api/mo/uni.json'
        return phys_domain_url, fabric_url, infra_url

    def _get_name_for_json(self):
        return '%s-%s-%s-%s' % (self.pod, self.node,
                                self.module, self.port)

    def get_json(self):
        """ Get the json for an interface.  Returns a tuple since the json is
            required to be sent in 2 posts.
        """
        fabric = None
        # Physical Domain json
        vlan_ns_dn = 'uni/infra/vlanns-allvlans-static'
        vlan_ns_ref = {'infraRsVlanNs': {'attributes':
                                         {'tDn': vlan_ns_dn},
                                         'children': []}}
        phys_domain = {'physDomP': {'attributes': {'name': 'allvlans'},
                                    'children': [vlan_ns_ref]}}

        # Infra json
        infra = {'infraInfra': {'children': []}}
        node_profile, accport_selector = self.get_port_selector_json()
        infra['infraInfra']['children'].append(node_profile)
        infra['infraInfra']['children'].append(accport_selector)
        speed_name = 'speed%s' % self.speed
        hifpol_dn = 'uni/infra/hintfpol-%s' % speed_name
        speed = {'fabricHIfPol': {'attributes': {'autoNeg': 'on',
                                                 'dn': hifpol_dn,
                                                 'name': speed_name,
                                                 'speed': self.speed},
                                  'children': []}}
        infra['infraInfra']['children'].append(speed)
        name = self._get_name_for_json()
        accportgrp_dn = 'uni/infra/funcprof/accportgrp-%s' % name
        speed_attr = {'tnFabricHIfPolName': speed_name}
        speed_children = {'infraRsHIfPol': {'attributes': speed_attr,
                                            'children': []}}
        cdp_children = None
        if self._cdp_config is not None:
            cdp_data = {'tnCdpIfPolName': 'CDP_%s' % self._cdp_config}
            cdp_children = {'infraRsCdpIfPol': {'attributes': cdp_data}}
        lldp_children = None
        if self._lldp_config is not None:
            lldp_data = {'tnLldpIfPolName': 'LLDP_%s' % self._lldp_config}
            lldp_children = {'infraRsLldpIfPol': {'attributes': lldp_data}}
        att_ent_dn = 'uni/infra/attentp-allvlans'
        att_ent_p = {'infraRsAttEntP': {'attributes': {'tDn': att_ent_dn},
                                        'children': []}}
        speed_ref = {'infraAccPortGrp': {'attributes': {'dn': accportgrp_dn,
                                                        'name': name},
                                         'children': [speed_children,
                                                      att_ent_p]}}
        if cdp_children is not None:
            speed_ref['infraAccPortGrp']['children'].append(cdp_children)
        if lldp_children is not None:
            speed_ref['infraAccPortGrp']['children'].append(lldp_children)
        speed_ref = {'infraFuncP': {'attributes': {}, 'children': [speed_ref]}}
        infra['infraInfra']['children'].append(speed_ref)

        phys_dom_dn = 'uni/phys-allvlans'
        rs_dom_p = {'infraRsDomP': {'attributes': {'tDn': phys_dom_dn}}}
        infra_att_entity_p = {'infraAttEntityP': {'attributes':
                                                  {'name': 'allvlans'},
                                                  'children': [rs_dom_p]}}
        infra['infraInfra']['children'].append(infra_att_entity_p)

        if self._cdp_config is not None:
            cdp_if_pol = {'cdpIfPol': {'attributes': {'adminSt': self._cdp_config,
                                                      'name': 'CDP_%s' % self._cdp_config}}}
            infra['infraInfra']['children'].append(cdp_if_pol)

        if self._lldp_config is not None:
            lldp_if_pol = {'lldpIfPol': {'attributes': {'adminRxSt': self._lldp_config,
                                                        'adminTxSt': self._lldp_config,
                                                        'name': 'LLDP_%s' % self._lldp_config}}}
            infra['infraInfra']['children'].append(lldp_if_pol)

        if self.adminstatus != '':
            adminstatus_attributes = {}
            adminstatus_attributes['tDn'] = self._get_path()
            if self.adminstatus == 'up':
                admin_dn = 'uni/fabric/outofsvc/rsoosPath-['
                admin_dn = admin_dn + self._get_path() + ']'
                adminstatus_attributes['dn'] = admin_dn
                adminstatus_attributes['status'] = 'deleted'
            else:
                adminstatus_attributes['lc'] = 'blacklist'
            adminstatus_json = {'fabricRsOosPath':
                                {'attributes': adminstatus_attributes,
                                 'children': []}}
            fabric = {'fabricOOServicePol': {'children': [adminstatus_json]}}

        fvns_encap_blk = {'fvnsEncapBlk': {'attributes': {'name': 'encap',
                                                          'from': 'vlan-1',
                                                          'to': 'vlan-4092'}}}
        fvns_vlan_inst_p = {'fvnsVlanInstP': {'attributes':
                                              {'name': 'allvlans',
                                               'allocMode': 'static'},
                                              'children': [fvns_encap_blk]}}
        infra['infraInfra']['children'].append(fvns_vlan_inst_p)

        return phys_domain, fabric, infra

    def _get_path(self):
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
    def _parse_physical_dn(dn):
        """
        Handles DNs that look like the following:
        topology/pod-1/node-103/sys/phys-[eth1/12]
        """
        name = dn.split('/')
        pod = name[1].split('-')[1]
        node = name[2].split('-')[1]
        module = name[4].split('[')[1]
        interface_type = module[:3]
        module = module[3:]
        port = name[5].split(']')[0]

        return interface_type, pod, node, module, port

    @staticmethod
    def _parse_path_dn(dn):
        """
        Handles DNs that look like the following:
        topology/pod-1/paths-102/pathep-[eth1/12]
        """
        name = dn.split('/')
        pod = name[1].split('-')[1]
        node = name[2].split('-')[1]
        module = name[3].split('[')[1]
        interface_type = module[:3]
        module = module[3:]
        port = name[4].split(']')[0]

        return interface_type, pod, node, module, port

    @classmethod
    def parse_dn(cls, dn):
        """
        Parses the pod, node, module, port from a distinguished name
        of the interface.

        :param dn: String containing the interface distinguished name
        :returns: interface_type, pod, node, module, port
        """
        if 'sys' in dn.split('/'):
            return cls._parse_physical_dn(dn)
        else:
            return cls._parse_path_dn(dn)

    @staticmethod
    def _get_discoveryprot_policies(session, prot):
        """
        :param prot: String containing either 'cdp' or 'lldp'
        """
        prot_policies = {}
        if prot == 'cdp':
            prot_class = 'cdpIfPol'
        elif prot == 'lldp':
            prot_class = 'lldpIfPol'
        else:
            raise ValueError

        query_url = '/api/node/class/%s.json?query-target=self' % prot_class
        ret = session.get(query_url)
        prot_data = ret.json()['imdata']
        for policy in prot_data:
            attributes = policy['%s' % prot_class]['attributes']
            if prot == 'cdp':
                prot_policies[attributes['name']] = attributes['adminSt']
            else:
                prot_policies[attributes['name']] = attributes['adminTxSt']
        return prot_policies

    @staticmethod
    def _get_discoveryprot_relations(session, interfaces, prot, prot_policies):
        if prot == 'cdp':
            prot_relation_class = 'l1RsCdpIfPolCons'
            prot_relation_dn_class = '/cdpIfP-'
            prot_relation_dn = '/rscdpIfPolCons'
        elif prot == 'lldp':
            prot_relation_class = 'l1RsLldpIfPolCons'
            prot_relation_dn_class = '/lldpIfP-'
            prot_relation_dn = '/rslldpIfPolCons'
        else:
            raise ValueError

        query_url = ('/api/node/class/l1PhysIf.json?query-target=subtree&'
                     'target-subtree-class=%s' % prot_relation_class)
        ret = session.get(query_url)
        prot_data = ret.json()['imdata']
        for prot_relation in prot_data:
            attributes = prot_relation[prot_relation_class]['attributes']
            policy_name = attributes['tDn'].split(prot_relation_dn_class)[1]
            intf_dn = attributes['dn'].split(prot_relation_dn)[0]
            search_intf = Interface(*Interface._parse_physical_dn(intf_dn))
            for intf in interfaces:
                if intf == search_intf:
                    if prot_policies[policy_name] == 'enabled':
                        if prot == 'cdp':
                            intf.enable_cdp()
                        else:
                            intf.enable_lldp()
                    else:
                        if prot == 'cdp':
                            intf.disable_cdp()
                        else:
                            intf.disable_lldp()
                    break
        return interfaces

    @staticmethod
    def get(session, pod_parent=None, node=None, module=None, port=None):
        """
        Gets all of the physical interfaces from the APIC if no parent is specified.
        If a parent of type Linecard is specified, then only those interfaces on
        that linecard are returned and they are also added as children to that linecard.

        If the pod, node, module and port are specified, then only that specific
        interface is read.

        :param session: the instance of Session used for APIC communication
        :param pod_parent: Linecard instance to limit interfaces or pod number (optional)
        :param node: Node id string.  This specifies the switch to read. (optional)
        :param module: Module id string.  This specifies the module or slot of the port. (optional)
        :param port: Port number.  This is the port to read. (optional)

        :returns: list of Interface instances
        """

        if port:
            if not isinstance(module, str):
                raise ValueError('When specifying a specific port, the module must be identified by a string')
            if not isinstance(node, str):
                raise ValueError('When specifying a specific port, the node must be identified by a string')
            if not isinstance(pod_parent, str):
                raise ValueError('When specifying a specific port, the pod must be identified by a string')

        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        cdp_policies = Interface._get_discoveryprot_policies(session, 'cdp')
        lldp_policies = Interface._get_discoveryprot_policies(session, 'lldp')

        if port:
            dist_name = 'topology/pod-{0}/node-{1}/sys/phys-[eth{2}/{3}]'.format(pod_parent, node, module, port)
            interface_query_url = ('/api/mo/'+dist_name+'.json?query-target=self')
            eth_query_url = ('/api/mo/'+dist_name+'/phys.json?query-target=self')
        else:
            interface_query_url = ('/api/node/class/l1PhysIf.json?query-target='
                                   'self')
            eth_query_url = ('/api/node/class/ethpmPhysIf.json?query-target='
                             'self')

        ret = session.get(interface_query_url)
        resp = []
        interface_data = ret.json()['imdata']

        # also get information about the ethernet interface
        ethResp = session.get(eth_query_url)
        resp = []
        ethData = ethResp.json()['imdata']

        # re-index the ethernet port info so it can be referenced by dn
        ethDataDict = {}
        for object in ethData:

            ethDataDict[object['ethpmPhysIf']['attributes']['dn']] = object['ethpmPhysIf']['attributes']

        for interface in interface_data:
            attributes = {}
            dist_name = str(interface['l1PhysIf']['attributes']['dn'])
            attributes['dist_name'] = dist_name
            porttype = str(interface['l1PhysIf']['attributes']['portT'])
            attributes['porttype'] = porttype
            adminstatus = str(interface['l1PhysIf']['attributes']['adminSt'])
            attributes['adminstatus'] = adminstatus
            speed = str(interface['l1PhysIf']['attributes']['speed'])
            attributes['speed'] = speed
            mtu = str(interface['l1PhysIf']['attributes']['mtu'])
            attributes['mtu'] = mtu
            id = str(interface['l1PhysIf']['attributes']['id'])
            attributes['id'] = id
            attributes['monPolDn'] = str(interface['l1PhysIf']['attributes']['monPolDn'])
            attributes['name'] = str(interface['l1PhysIf']['attributes']['name'])
            attributes['descr'] = str(interface['l1PhysIf']['attributes']['descr'])
            (interface_type, pod, node,
             module, port) = Interface.parse_dn(dist_name)
            attributes['interface_type'] = interface_type
            attributes['pod'] = pod
            attributes['node'] = node
            attributes['module'] = module
            attributes['port'] = port
            attributes['operSt'] = ethDataDict[dist_name+'/phys']['operSt']
            interface_obj = Interface(interface_type, pod, node, module, port, parent=None, session=session, attributes=attributes)
            interface_obj.porttype = porttype
            interface_obj.adminstatus = adminstatus
            interface_obj.speed = speed
            interface_obj.mtu = mtu

            if not isinstance(pod_parent, str) and pod_parent:
                if interface_obj.pod == pod_parent.pod and interface_obj.node == pod_parent.node and interface_obj.module == pod_parent.slot:
                    resp.append(interface_obj)
            else:
                resp.append(interface_obj)

        resp = Interface._get_discoveryprot_relations(session, resp, 'cdp', cdp_policies)
        resp = Interface._get_discoveryprot_relations(session, resp, 'lldp', lldp_policies)
        return resp

    def __str__(self):
        items = [self.if_name, '\t', self.porttype, '\t',
                 self.adminstatus, '\t', self.speed, '\t',
                 self.mtu]
        ret = ''.join(items)
        return ret

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if (self.attributes['interface_type'] == other.attributes.get('interface_type') and
                self.attributes['pod'] == other.attributes.get('pod') and
                self.attributes['node'] == other.attributes.get('node') and
                self.attributes['module'] == other.attributes.get('module') and
                self.attributes['port'] == other.attributes.get('port')):

            return True
        return False


class InterfaceStats():
    """
    This class defines interface statistics.  It will provide methods to
    retrieve the stats.  The stats are returned as a dictionary with the
    following structure:

    stats= {<counterFamily>:{<granularity>:{<period>:{<counter>:value}}}}

    stats are gathered and summed up in time intervals or granularities. For each granularity there are a set of time periods
    identified by the <period> field.  The current stats are stored in period 0.  These stats are zeroed at the beginning of the
    time interval and are updated at a smaller time interval depending on the granularity.  Historical statistics have periods that are
    greater than 0.  The number of historical stats to keep is determined by the monitoring policy and may be specifc to a particular counter
    family.

    The counter families are as follows: 'egrTotal', 'egrBytes','egrPkts','egrDropPkts', 'ingrBytes','ingrPkts',
    'ingrTotal', 'ingrDropPkts', 'ingrUnkBytes','ingrUnkPkts', 'ingrStorm'.

    The granularities are: '5min', '15min', '1h', '1d', '1w', '1mo', '1qtr', and '1year'.

    For each counter family/granularity/period there are several counter values retained.  The best way to see a list of these
    counters is to print the keys of the dictionary.


    """
    def __init__(self, parent, interfaceDn):
        self._parent = parent
        self._interfaceDn = interfaceDn

    def get(self, session=None):
        """
        Retrieve the count dictionary.  This method will read in all the counters and return them as a dictionary.

        :param session: Session to use when accessing the APIC

        :returns:  Dictionary of counters. Format is {<counterFamily>:{<granularity>:{<period>:{<counter>:value}}}}
        """
        result = {}
        if not session:
            session = self._parent._session

        mo_query_url = '/api/mo/'+self._interfaceDn+'.json?query-target=self&rsp-subtree-include=stats'

        ret = session.get(mo_query_url)
        data = ret.json()['imdata']
        noCounts = False
        if data:
            if 'children' in data[0]['l1PhysIf']:
                children = data[0]['l1PhysIf']['children']
                for grandchildren in children:
                    for count in grandchildren:
                        counterAttr = grandchildren[count]['attributes']
                        if re.search('^C', counterAttr['rn']):
                            period = 0
                        else:
                            period = int(counterAttr['index'])+1

                        if 'EgrTotal' in count:
                            countName = 'egrTotal'
                        elif 'EgrBytes' in count:
                            countName = 'egrBytes'
                        elif 'EgrPkts' in count:
                            countName = 'egrPkts'
                        elif 'EgrDropPkts' in count:
                            countName = 'egrDropPkts'
                        elif 'IngrBytes' in count:
                            countName = 'ingrBytes'
                        elif 'IngrPkts' in count:
                            countName = 'ingrPkts'
                        elif 'IngrTotal' in count:
                            countName = 'ingrTotal'
                        elif 'IngrDropPkts' in count:
                            countName = 'ingrDropPkts'
                        elif 'IngrUnkBytes' in count:
                            countName = 'ingrUnkBytes'
                        elif 'IngrUnkPkts' in count:
                            countName = 'ingrUnkPkts'
                        elif 'IngrStorm' in count:
                            countName = 'ingrStorm'
                        else:
                            countName = count

                        granularity = re.search('(\d+\D+)$', count).group(1)

                        if countName not in result:
                            result[countName] = {}
                        if granularity not in result[countName]:
                            result[countName][granularity] = {}
                        if period not in result[countName][granularity]:
                            result[countName][granularity][period] = {}

                        if countName in ['egrTotal', 'ingrTotal']:
                            for attrName in ['bytesAvg', 'bytesCum', 'bytesMax', 'bytesMin', 'bytesPer',
                                             'pktsAvg', 'pktsCum', 'pktsMax', 'pktsMin', 'pktsPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['bytesRate', 'bytesRateAvg', 'bytesRateMax', 'bytesRateMin',
                                             'pktsRate', 'pktsRateAvg', 'pktsRateMax', 'pktsRateMin']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])

                        elif countName in ['egrBytes', 'ingrBytes']:
                            for attrName in ['floodAvg', 'floodCum', 'floodMax', 'floodMin', 'floodPer',
                                             'multicastAvg', 'multicastCum', 'multicastMax', 'multicastMin', 'multicastPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['floodRate',
                                             'multicastRate', 'multicastRateAvg', 'multicastRateMax', 'multicastRateMin']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])

                        elif countName in ['egrPkts', 'ingrPkts']:
                            for attrName in ['floodAvg', 'floodCum', 'floodMax', 'floodMin', 'floodPer',
                                             'multicastAvg', 'multicastCum', 'multicastMax', 'multicastMin', 'multicastPer',
                                             'unicastAvg', 'unicastCum', 'unicastMax', 'unicastMin', 'unicastPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['floodRate', 'multicastRate', 'unicastRate']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])

                        elif countName in ['egrDropPkts']:
                            for attrName in ['afdWredAvg', 'afdWredCum', 'afdWredMax', 'afdWredMin', 'afdWredPer',
                                             'bufferAvg', 'bufferCum', 'bufferMax', 'bufferMin', 'bufferPer',
                                             'errorAvg', 'errorCum', 'errorMax', 'errorMin', 'errorPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['afdWredRate',
                                             'bufferRate',
                                             'errorRate']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])
                        elif countName in ['ingrDropPkts']:
                            for attrName in ['bufferAvg', 'bufferCum', 'bufferMax', 'bufferMin', 'bufferPer',
                                             'errorAvg', 'errorCum', 'errorMax', 'errorMin', 'errorPer',
                                             'forwardingAvg', 'forwardingCum', 'forwardingMax', 'forwardingMin', 'forwardingPer',
                                             'lbAvg', 'lbCum', 'lbMax', 'lbMin', 'lbPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['bufferRate', 'errorRate', 'forwardingRate', 'lbRate']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])

                        elif countName in ['ingrUnkBytes']:
                            for attrName in ['unclassifiedAvg', 'unclassifiedCum', 'unclassifiedMax', 'unclassifiedMin', 'unclassifiedPer',
                                             'unicastAvg', 'unicastCum', 'unicastMax', 'unicastMin', 'unicastPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['unclassifiedRate', 'unicastRate']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])

                        elif countName in ['ingrUnkPkts']:
                            for attrName in ['unclassifiedAvg', 'unclassifiedCum', 'unclassifiedMax', 'unclassifiedMin', 'unclassifiedPer',
                                             'unicastAvg', 'unicastCum', 'unicastMax', 'unicastMin', 'unicastPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['unclassifiedRate', 'unicastRate']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])
                        elif countName in ['ingrStorm']:
                            for attrName in ['dropBytesAvg', 'dropBytesCum', 'dropBytesMax', 'dropBytesMin', 'dropBytesPer']:
                                result[countName][granularity][period][attrName] = int(counterAttr[attrName])
                            for attrName in ['dropBytesRate', 'dropBytesRateAvg', 'dropBytesRateMax', 'dropBytesRateMin']:
                                result[countName][granularity][period][attrName] = float(counterAttr[attrName])
                        else:
                            print 'Found unsupported counter', countName, granularity, period
                        result[countName][granularity][period]['intervalEnd'] = counterAttr.get('repIntvEnd')
                        result[countName][granularity][period]['intervalStart'] = counterAttr.get('repIntvStart')

            else:
                noCounts = True
        else:
            noCounts = True
        # store the result to be accessed by the retrieve method
        self.result = result
        return result

    def retrieve(self, countFamily, granularity, period, countName):
        """
        This will return the requested count from stats that were loaded with
        the previous get().  It will return 0 for counts that don't exist or None
        for time stamps that don't exist.

        Note that this method will not access the APIC, it will only work on data that was previously loaded with a get().

       :param countFamily: The counter family string.  Examples are 'egrTotal', 'ingrDropPkts, etc.
       :param granularity: String specifying the counter time granularity.  Possible values are: '5min', '15min',
                            '1h', '1d', '1w', '1mo', '1qtr', and '1year'
       :param period: Integer of time period to get the counter from.  Period 0 is the current period. Period 1 is the previous
                            time granularity.
       :param countName: Name of the actual counter.  Examples are 'unicastPer', 'unicastRate', etc.  Counter names are unique per counter family.

       :returns:  integer, float or None.  If the counter is not present, it will return 0.
        """

        # initialize result to a miss
        if countName in ['intervalEnd', 'intervalStart']:
            result = None

        elif countName in ['pktsRate', 'pktsRateAvg', 'pktsRateMax', 'pktsRateMin',
                           'bytesRate', 'bytesRateAvg', 'bytesRateMax', 'bytesRateMin',
                           'floodRate', 'unicastRate', 'unclassifiedRate'
                           'afdWredRate', 'bufferRate', 'errorRate',
                           'forwardingRate', 'lbRate',
                           'multicastRate', 'multicastRateAvg', 'multicastRateMax', 'multicastRateMin',
                           'dropBytesRate', 'dropBytesRateAvg', 'dropBytesRateMax', 'dropBytesRateMin']:
            result = 0.0
        else:
            result = 0

        # overwrite result if it exists
        if countFamily in self.result:
            if granularity in self.result[countFamily]:
                if period in self.result[countFamily][granularity]:
                    if countName in self.result[countFamily][granularity][period]:

                        # read value
                        result = self.result[countFamily][granularity][period][countName]

        return result


class PortChannel(BaseInterface):
    """
    This class defines a port channel interface.
    """
    def __init__(self, name):
        super(PortChannel, self).__init__(name)
        self._interfaces = []
        self._nodes = []

    def attach(self, interface):
        """Attach an interface to this PortChannel"""
        if interface not in self._interfaces:
            self._interfaces.append(interface)
        self._update_nodes()

    def detach(self, interface):
        """Detach an interface from this PortChannel"""
        if interface in self._interfaces:
            self._interfaces.remove(interface)
        self._update_nodes()

    def _update_nodes(self):
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

    def _get_nodes(self):
        """ Returns a single node id or multiple node ids in the
            case that this is a VPC
        """
        return self._nodes

    def _get_path(self):
        """Get the path of this interface used when communicating with
           the APIC object model.
        """
        assert len(self._interfaces)
        pod = self._interfaces[0].pod
        if self.is_vpc():
            (node1, node2) = self._get_nodes()
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

    @staticmethod
    def get_url(fmt='json'):
        """
        Get the URLs used to push the configuration to the APIC
        if no format parameter is specified, the format will be 'json'
        otherwise it will return '/api/mo/uni.' with the format string
        appended.
        :param fmt: optional format string, default is 'json'
        :returns: URL string
        """
        return ('/api/mo/uni/fabric.' + fmt,
                '/api/mo/uni.' + fmt)

    def get_json(self):
        """
        Returns json representation of the PortChannel

       :returns: json dictionary of the PortChannel
        """
        vpc = self.is_vpc()
        pc_mode = 'link'
        if vpc:
            pc_mode = 'node'
        infra = {'infraInfra': {'children': []}}
        # Add the node and port selectors
        for interface in self._interfaces:
            node_profile, accport_selector = interface.get_port_channel_selector_json(self.name)
            infra['infraInfra']['children'].append(node_profile)
            if self.is_deleted():
                for hports in accport_selector['infraAccPortP']['children']:
                    if 'infraHPortS' in hports:
                        for child in hports['infraHPortS']['children']:
                            if 'infraRsAccBaseGrp' in child:
                                child['infraRsAccBaseGrp']['attributes']['status'] = 'deleted'
            infra['infraInfra']['children'].append(accport_selector)
        # Add the actual port-channel
        accbndlgrp = {'infraAccBndlGrp':
                      {'attributes':
                       {'name': self.name, 'lagT': pc_mode},
                       'children': []}}
        if self.is_deleted():
            accbndlgrp['infraAccBndlGrp']['attributes']['status'] = 'deleted'
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

    @staticmethod
    def get(session):
        """Gets all of the port channel interfaces from the APIC
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')
        interface_query_url = ('/api/node/class/infraAccBndlGrp.json?'
                               'query-target=self')
        portchannels = []
        ret = session.get(interface_query_url)
        pc_data = ret.json()['imdata']
        for pc in pc_data:
            portchannel_name = str(pc['infraAccBndlGrp']['attributes']['name'])
            portchannel = PortChannel(portchannel_name)
            portchannels.append(portchannel)
        return portchannels


class Endpoint(BaseACIObject):
    def __init__(self, name, parent):
        if not isinstance(parent, EPG):
            raise TypeError('Parent must be of EPG class')
        super(Endpoint, self).__init__(name, parent=parent)
        self.mac = None
        self.ip = None
        self.encap = None

    @classmethod
    def _get_apic_classes(cls):
        resp = []
        resp.append('fvCEp')
        resp.append('fvStCEp')
        return resp

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        return {}

    @staticmethod
    def _get_parent_class():
        return EPG

    @staticmethod
    def _get_parent_dn(dn):
        if '/stcep-' in dn:
            return dn.split('/stcep-')[0]
        else:
            return dn.split('/cep-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        if '/stcep-' in dn:
            name = dn.split('/stcep-')[1].split('-type-')[0]
        else:
            name = dn.split('/cep-')[1]
        return name

    def get_json(self):
        return None

    def _populate_from_attributes(self, attributes):
        if 'mac' not in attributes:
            return
        self.mac = str(attributes['mac'])
        self.ip = str(attributes['ip'])
        self.encap = str(attributes['encap'])

    @classmethod
    def get_event(cls, session):
        urls = cls._get_subscription_urls()
        for url in urls:
            if not session.has_events(url):
                continue
            event = session.get_event(url)
            for class_name in cls._get_apic_classes():
                if class_name in event['imdata'][0]:
                    break
            attributes = event['imdata'][0][class_name]['attributes']
            status = str(attributes['status'])
            dn = str(attributes['dn'])
            parent = cls._get_parent_from_dn(cls._get_parent_dn(dn))
            if status == 'created':
                name = str(attributes['name'])
            else:
                name = cls._get_name_from_dn(dn)
            obj = cls(name, parent=parent)
            obj._populate_from_attributes(attributes)
            obj.timestamp = str(attributes['modTs'])
            if obj.mac is None:
                obj.mac = name
            if status == 'deleted':
                obj.mark_as_deleted()
            else:
                obj = cls.get(session, name)[0]
            return obj

    @staticmethod
    def _get(session, endpoint_name, interfaces, endpoints, apic_endpoint_class, endpoint_path):
        # Get all of the Endpoints
        if endpoint_name is None:
            endpoint_query_url = ('/api/node/class/%s.json?query-target=self'
                                  '&rsp-subtree=full' % apic_endpoint_class)
        else:
            endpoint_query_url = ('/api/node/class/%s.json?query-target=self'
                                  '&query-target-filter=eq(%s.name,"%s")'
                                  '&rsp-subtree=full' % (apic_endpoint_class,
                                                         apic_endpoint_class,
                                                         endpoint_name))
        ret = session.get(endpoint_query_url)
        ep_data = ret.json()['imdata']
        for ep in ep_data:
            if ep[apic_endpoint_class]['attributes']['lcC'] == 'static':
                continue
            children = ep[apic_endpoint_class]['children']
            ep = ep[apic_endpoint_class]['attributes']
            tenant = Tenant(str(ep['dn']).split('/')[1][3:])
            if '/LDevInst-' in str(ep['dn']):
                unknown = '?' * 10
                app_profile = AppProfile(unknown, tenant)
                epg = EPG(unknown, app_profile)
            else:
                app_profile = AppProfile(str(ep['dn']).split('/')[2][3:], tenant)
                epg = EPG(str(ep['dn']).split('/')[3][4:], app_profile)
            endpoint = Endpoint(str(ep['name']), parent=epg)
            endpoint.mac = str(ep['mac'])
            endpoint.ip = str(ep['ip'])
            endpoint.encap = str(ep['encap'])
            endpoint.timestamp = str(ep['modTs'])
            for child in children:
                if endpoint_path in child:
                    endpoint.if_name = str(child[endpoint_path]['attributes']['tDn'])
                    for interface in interfaces:
                        interface = interface['fabricPathEp']['attributes']
                        interface_dn = str(interface['dn'])
                        if endpoint.if_name == interface_dn:
                            if str(interface['lagT']) == 'not-aggregated':
                                endpoint.if_name = Interface(*Interface.parse_dn(interface_dn)).if_name
                            else:
                                endpoint.if_name = interface['name']
                    endpoint_query_url = '/api/mo/' + endpoint.if_name + '.json'
                    ret = session.get(endpoint_query_url)
            endpoints.append(endpoint)
        return endpoints

    @staticmethod
    def get(session, endpoint_name=None):
        """Gets all of the endpoints connected to the fabric from the APIC
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        # Get all of the interfaces
        interface_query_url = ('/api/node/class/fabricPathEp.json?'
                               'query-target=self')
        ret = session.get(interface_query_url)
        interfaces = ret.json()['imdata']

        endpoints = []
        endpoints = Endpoint._get(session, endpoint_name, interfaces, endpoints,
                                  'fvCEp', 'fvRsCEpToPathEp')
        endpoints = Endpoint._get(session, endpoint_name, interfaces, endpoints,
                                  'fvStCEp', 'fvRsStCEpToPathEp')

        return endpoints


class NetworkPool(BaseACIObject):
    """This class defines a pool of network ids
    """
    def __init__(self, name, encap_type, start_id, end_id, mode):
        super(NetworkPool, self).__init__(name)
        valid_encap_types = ['vlan', 'vxlan']
        if encap_type not in valid_encap_types:
            raise ValueError('Encap type specified is not a valid encap type')
        self.encap_type = encap_type
        self.start_id = start_id
        self.end_id = end_id
        valid_modes = ['static', 'dynamic']
        if mode not in valid_modes:
            raise ValueError('Mode specified is not a valid mode')
        self.mode = mode

    def get_json(self):
        from_id = self.encap_type + '-' + self.start_id
        to_id = self.encap_type + '-' + self.end_id
        fvnsEncapBlk = {'fvnsEncapBlk': {'attributes': {'name': 'encap',
                                                        'from': from_id,
                                                        'to': to_id},
                                         'children': []}}
        if self.encap_type == 'vlan':
            fvnsEncapInstP_string = 'fvnsVlanInstP'
        elif self.encap_type == 'vxlan':
            fvnsEncapInstP_string = 'fvnsVxlanInstP'
        fvnsEncapInstP = {fvnsEncapInstP_string:  {'attributes': {'name': self.name,
                                                                  'allocMode': self.mode},
                                                   'children': [fvnsEncapBlk]}}
        infra = {'infraInfra': {'attributes': {},
                                'children': [fvnsEncapInstP]}}
        return infra


class VMMCredentials(BaseACIObject):
    """This class defines the credentials used to login to a Virtual
       Machine Manager
    """
    def __init__(self, name, uid, pwd):
        super(VMMCredentials, self).__init__(name)
        self.uid = uid
        self.pwd = pwd

    def get_json(self):
        vmmUsrAccP = {'vmmUsrAccP': {'attributes': {'name': self.name,
                                                    'usr': self.uid,
                                                    'pwd': self.pwd},
                                     'children': []}}
        return vmmUsrAccP


class VMMvSwitchInfo(object):
    """This class contains the information necessary for creating the
       vSwitch on the Virtual Machine Manager
    """
    def __init__(self, vendor, container_name, vswitch_name):
        valid_vendors = ['VMware', 'Microsoft']
        if vendor not in valid_vendors:
            raise ValueError('Vendor specified is not in valid vendor list')
        self.vendor = vendor
        self.container_name = container_name
        self.vswitch_name = vswitch_name


class VMM(BaseACIObject):
    """This class defines an instance of connectivity to a
       Virtual Machine Manager (such as VMware vCenter)
    """
    def __init__(self, name, ipaddr, credentials, vswitch_info, network_pool):
        super(VMM, self).__init__(name)
        self.ipaddr = ipaddr
        self.credentials = credentials
        self.vswitch_info = vswitch_info
        self.network_pool = network_pool

    def _get_path(self):
        return 'uni/vmmp-%s/dom-%s' % (self.vswitch_info.vendor,
                                       self.vswitch_info.vswitch_name)

    def get_json(self):
        vmmUsrAccP = self.credentials.get_json()
        vmmUsrAccDn = 'uni/vmmp-%s/dom-%s/usracc-%s' % (self.vswitch_info.vendor,
                                                        self.vswitch_info.vswitch_name,
                                                        self.credentials.name)
        vmmRsAcc = {'vmmRsAcc': {'attributes': {'tDn': vmmUsrAccDn},
                                 'children': []}}
        vmmCtrlrP = {'vmmCtrlrP': {'attributes': {'name': self.name,
                                                  'hostOrIp': self.ipaddr,
                                                  'rootContName': self.vswitch_info.container_name},
                                   'children': [vmmRsAcc]}}
        infraNsDn = 'uni/infra/%sns-%s-%s' % (self.network_pool.encap_type,
                                              self.network_pool.name,
                                              self.network_pool.mode)

        if self.network_pool.encap_type == 'vlan':
            infraNsType = 'infraRsVlanNs'
        elif self.network_pool.encap_type == 'vxlan':
            infraNsType = 'infraRsVxlanNs'
        infraRsNs = {infraNsType: {'attributes': {'tDn': infraNsDn},
                                   'children': []}}
        vmmDomP = {'vmmDomP': {'attributes': {'name': self.vswitch_info.vswitch_name},
                               'children': [vmmUsrAccP, vmmCtrlrP, infraRsNs]}}
        vmmProvP = {'vmmProvP': {'attributes': {'vendor': self.vswitch_info.vendor},
                                 'children': [vmmDomP]}}

        return vmmProvP

    @classmethod
    def get(cls, session):
        query_url = '/api/node/class/vmmCtrlrP.json?query-target=subtree'
        ret = session.get(query_url)
        data = ret.json()['imdata']
        for item in data:
            for key in item:
                print key
        print data
        raise NotImplementedError


class Search(BaseACIObject):
    """This is an empty class used to create a search object for use with the "find" method.

    Attaching attributes to this class and then invoking find will return all objects with matching attributes
    in the object hierarchy at and below where the find is invoked.
    """
    def __init__(self):
        pass


class BaseMonitorClass(object):
    """ Base class for monitoring policies.  These are methods that can be used on all monitoring objects.
    """
    def setName(self, name):
        """
        Sets the name of the MonitorStats.

       :param name: String to use as the name
        """
        self.name = name
        self.modified = True

    def setDescription(self, description):
        """
        Sets the description of the MonitorStats.

       :param description: String to use as the description
        """
        self.description = description
        self.modified = True

    def isModified(self):
        """
        Returns True if this policy and any children have been modified or
        created and not been written to the APIC
        """
        for child in self._children:
            if child.isModified():
                return True

        return self.modified

    def get_parent(self):
        """
       :returns: parent object
        """
        return self._parent

    def add_stats(self, stat_obj):
        """
        Adds a stats family object.

        :param stat_obj: Statistics family object of type MonitorStats.
        """
        self.monitor_stats[stat_obj.scope] = stat_obj
        self.modified = True

    def remove_stats(self, stats_family):
        """
        Remove a stats family object.  The object to remove is identified by
        a string, e.g. 'ingrPkts', or 'egrTotal'.  This string can be found
        in the 'MonitorStats.scope' attribute of the object.

        :param stats_family: Statistics family string.
        """
        if not isinstance(stats_family, str):
            raise TypeError('MonitorStats must be identified by a string')

        if stats_family in self.monitor_stats:
            self.monitor_stats.remove(stats_family)
            self.modified = True

    def add_target(self, target_obj):
        """
        Add a target object.

        :param target_obj: target object of type MonitorTarget
        """
        self.monitor_target[target_obj.scope] = target_obj
        self.modified = True

    def remove_target(self, target):
        """
        Remove a target object.  The object to remove is identified by
        a string, e.g 'l1PhysIf'.  This string can be found
        in the 'MonitorTarget.scope' attribute of the object.

        :param target: target to remove.
        """
        if not isinstance(target, str):
            raise TypeError('MonitorTarget must be identified by a string')

        if target in self.monitor_target:
            self.monitor_target.remove(target)
            self.modified = True

    def add_collection_policy(self, coll_obj):
        """
        Add a collection policy.

        :param coll_obj :  A collection policy object of type CollectionPolicy
        """
        self.collection_policy[coll_obj.granularity] = coll_obj
        self.modified = True

    def remove_collection_policy(self, collection):
        """
        Remove a collection_policy object.  The object to remove is identified by
        its granularity, e.g. '5min', '15min', etc.  This string can be found
        in the 'CollectionPolicy.granularity' attribute of the object.

        :param collection: CollectionPolicy to remove.
        """
        if collection not in CollectionPolicy.granularityEnum:
            raise TypeError('CollectionPolicy must be identified by its granularity')

        if collection in self.collection_policy:
            self.collection_policy.remove(collection)
            self.modified = True


class MonitorPolicy(BaseMonitorClass):
    """
    This class is the top-most container for a monitoring policy that controlls how statistics are gathered.
    It has immediate children, CollectionPolicy objects, that control the default behavior for any network
    element that uses this monitoring policy.  It may optionally have MonitorTarget objects as children that
    are used to override the default behavior for a particular target class such as Interfaces.  There can be
    further granularity of control through children of the MonitorTarget sub-objects.

    Children of the MonitorPolicy will be CollectionPolicy objects that define
    the collection policy plus optional MonitorTarget objects that allow finer grained
    control over specific target APIC objects such as 'l1PhysIf' (layer 1 physical interface).

    The CollectionPolicy children are contained in a dictionary called "collection_policy" that is indexed
    by the granulariy of the CollectionPolicy, e.g. '5min', '15min', etc.

    The MonitorTarget children are contained in a dictionary called "monitor_target" that is indexed by the
    name of the target object, e.g. 'l1PhysIf'.

    To make a policy take effect for a particular port, for example, you must attach that monitoring policy to
    the port.

    Note that the name of the MonitorPolicy is used to construct the dn of the object in the APIC.  As a
    result, the name cannot be changed.  If you read a policy from the APIC, change the name, and write it
    back, it will create a new policy with the new name and leave the old, original policy, in place
    with its original name.

    A description may be optionally added to the policy.
    """
    def __init__(self, policyType, name):
        """
        The MonitorPolicy is initialized with simply a policy type and a name.  There are two policy types: 'fabric'
        and 'access'.  The 'fabric' monitoring policies can be applied to certain MonitorTarget types and 'access'
        monitoring policies can be applied to other MonitorTarget types. Initially however, both policies can
        have l1PhysIf as targets.

        A name must be specified because it is used to build the distinguising name (dn) along with the policyType in
        the APIC.  The dn for "fabric" policies will be /uni/fabric/monfabric-[name] and for "access" policies it
        will be /uni/infra/moninfra-[name] in the APIC.

        :param policyType:  String specifying whether this is a fabric or access policy
        :param name:        String specifying a name for the policy.
        """
        policyTypeEnum = ['fabric', 'access']

        if policyType not in policyTypeEnum:
            raise ValueError('Policy Type must be one of:', policyTypeEnum)

        self.name = name
        self.policyType = policyType
        self.descr = ''
        self.collection_policy = {}
        self.monitor_target = {}

        # assume that it has not been written to APIC.  This is cleared if the policy is just loaded from APIC
        # or the policy is written to the APIC.
        self.modified = True

    @classmethod
    def get(cls, session):
        """
        get() will get all of the monitor policies from the APIC and return them as a list.  It will get both
        fabric and access (infra) policies including default policies.

       :param session: the instance of Session used for APIC communication
       :returns: List of MonitorPolicy objects
        """
        result = []
        aciObjects = cls._getClass(session, 'monInfraPol')
        for data in aciObjects:
            name = data['monInfraPol']['attributes']['name']
            policyObject = MonitorPolicy('access', name)
            policyObject.setDescription(data['monInfraPol']['attributes']['descr'])
            cls._getPolicy(policyObject, session, data['monInfraPol']['attributes']['dn'])
            result.append(policyObject)

        aciObjects = cls._getClass(session, 'monFabricPol')
        for data in aciObjects:
            name = data['monFabricPol']['attributes']['name']
            policyObject = MonitorPolicy('fabric', name)
            policyObject.setDescription(data['monFabricPol']['attributes']['descr'])
            cls._getPolicy(policyObject, session, data['monFabricPol']['attributes']['dn'])
            result.append(policyObject)
        return result

    @staticmethod
    def _getClass(session, aciClass):
        class_query_url = '/api/node/class/'+aciClass+'.json?query-target=self'
        ret = session.get(class_query_url)
        data = ret.json()['imdata']
        return data

    @classmethod
    def _getPolicy(cls, policyObject, session, dn):
        children = cls._getChildren(session, dn)
        for child in children:
            if child[0] == 'statsHierColl':
                granularity = str(child[1]['attributes']['granularity'])
                adminState = str(child[1]['attributes']['adminState'])
                retention = str(child[1]['attributes']['histRet'])
                collPolicy = CollectionPolicy(policyObject, granularity, retention, adminState)
                collPolicy.setName(child[1]['attributes']['name'])
                collPolicy.setDescription(child[1]['attributes']['descr'])

            if child[0] in ['monFabricTarget', 'monInfraTarget']:
                scope = str(child[1]['attributes']['scope'])

                # initially only l1PhysIf is supported as a target
                if scope == 'l1PhysIf':
                    target = MonitorTarget(policyObject, scope)
                    target.setName(str(child[1]['attributes']['name']))
                    target.setDescription(str(child[1]['attributes']['descr']))
                    dn = child[1]['attributes']['dn']
                    targetChildren = cls._getChildren(session, dn)
                    for targetChild in targetChildren:
                        if targetChild[0] == 'statsReportable':
                            scope = str(targetChild[1]['attributes']['scope'])
                            scope = MonitorStats.statsDictionary[scope]
                            statFamily = MonitorStats(target, scope)
                            statFamily.setName(str(targetChild[1]['attributes']['name']))
                            statFamily.setDescription(str(targetChild[1]['attributes']['name']))
                            dn = targetChild[1]['attributes']['dn']
                            statChildren = cls._getChildren(session, dn)
                            for statChild in statChildren:
                                if statChild[0] == 'statsColl':
                                    granularity = str(statChild[1]['attributes']['granularity'])
                                    adminState = str(statChild[1]['attributes']['adminState'])
                                    retention = str(statChild[1]['attributes']['histRet'])
                                    collPolicy = CollectionPolicy(statFamily, granularity, retention, adminState)
                                    collPolicy.setName(statChild[1]['attributes']['name'])
                                    collPolicy.setDescription(statChild[1]['attributes']['descr'])
                        if targetChild[0] == 'statsHierColl':
                            granularity = str(targetChild[1]['attributes']['granularity'])
                            adminState = str(targetChild[1]['attributes']['adminState'])
                            retention = str(targetChild[1]['attributes']['histRet'])
                            collPolicy = CollectionPolicy(target, granularity, retention, adminState)
                            collPolicy.setName(targetChild[1]['attributes']['name'])
                            collPolicy.setDescription(targetChild[1]['attributes']['descr'])

    @classmethod
    def _getChildren(cls, session, dn):
        result = []
        mo_query_url = '/api/mo/'+dn+'.json?query-target=children'
        ret = session.get(mo_query_url)
        mo_data = ret.json()['imdata']
        for node in mo_data:
            for key in node:
                result.append((key, node[key]))
        return result

    def __str__(self):
        """
        Return print string.
        """
        return self.policyType+':'+self.name

    def flat(self, target='l1PhysIf'):
        """
        This method will return a data structure that is a flattened version of the monitor policy.
        The flattened version is one that walks through the heirarchy of the policy and determines
        the administrative state and retention policy for each granularity of each statistics family.
        This is done for the target specified, i.e. 'l1PhysIf'

        For example, if 'foo' is a MonitorPolicy object, then flatPol = foo.flat('l1PhysIf') will return a
        dictionary that looks like the following:

        adminState = flatPol['counter_family']['granularity'].adminState
        retention = flatPol['counter_family']['granularity'].retention

        The dictionary will have all of the counter families for all of the granularities and the value
        returned is the administrative state nad retention value that is the final result
        of resolving the policy heirarchy.

        :param target:  APIC target object.  This will default to 'l1PhysIf'
        :returns: Dictionary of statistic administrative state and retentions indexed by
                  counter family and granularity.
        """
        class Policy(object):
            def __init__(self):
                self.adminState = 'disabled'
                self.retention = 'none'

        result = {}

        # initialize data structure
        for statFamily in MonitorStats.statsFamilyEnum:
            result[statFamily] = {}
            for granularity in CollectionPolicy.granularityEnum:
                result[statFamily][granularity] = Policy()

        # walk through the policy heirarchy and over-ride each
        # policy with the more specific one

        for granularity in self.collection_policy:
            retention = self.collection_policy[granularity].retention
            adminState = self.collection_policy[granularity].adminState
            for statFamily in MonitorStats.statsFamilyEnum:
                result[statFamily][granularity].adminState = adminState
                result[statFamily][granularity].retention = retention

        # now go through monitor targets
        targetPolicy = self.monitor_target[target]
        for granularity in targetPolicy.collection_policy:
            retention = targetPolicy.collection_policy[granularity].retention
            adminState = targetPolicy.collection_policy[granularity].adminState
            for statFamily in MonitorStats.statsFamilyEnum:
                if adminState != 'inherited':
                    result[statFamily][granularity].adminState = adminState
                if retention != 'inherited':
                    result[statFamily][granularity].retention = retention

        for statFamily in targetPolicy.monitor_stats:
            for granularity in targetPolicy.monitor_stats[statFamily].collection_policy:
                retention = targetPolicy.monitor_stats[statFamily].collection_policy[granularity].retention
                adminState = targetPolicy.monitor_stats[statFamily].collection_policy[granularity].adminState

                if adminState != 'inherited':
                    result[statFamily][granularity].adminState = adminState
                if retention != 'inherited':
                    result[statFamily][granularity].retention = retention

        # if the lesser granularity is disabled, then the larger granularity is as well
        for statFamily in MonitorStats.statsFamilyEnum:
            disable_found = False
            for granularity in CollectionPolicy.granularityEnum:
                if result[statFamily][granularity].adminState == 'disabled':
                    disable_found = True
                if disable_found:
                    result[statFamily][granularity].adminState = 'disabled'
        return result


class MonitorTarget(BaseMonitorClass):
    """
    This class is a child of a MonitorPolicy object. It is used to specify a scope for appling a monitoring
    policy.  An example scope would be the Interface class, meaning that the monitoring policies specified
    here will apply to all Interface clas objects (l1PhysIf in the APIC) that use the parent MonitoringPolicy as
    their monitoring policy.

    Children of the MonitorTarget will be CollectionPolicy objects that define
    the collection policy for the specified target plus optional MonitorStats objects that allow finer grained
    control over specific families of statistics such as ingress packets, ingrPkts.

    The CollectionPolicy children are contained in a dictionary called "collection_policy" that is indexed
    by the granulariy of the CollectionPolicy, e.g. '5min', '15min', etc.

    The MonitorStats children are contained in a dictionary called "monitor_stats" that is indexed by the
    name of the statistics family, e.g. 'ingrBytes', 'ingrPkts', etc.
    """
    def __init__(self, parent, target):
        """
        The MonitorTarget object is initialized with a parent of type MonitorPoliy, and a target string.
        Initially, this toolkit only support a target of type 'l1PhysIf'.  The 'l1PhyIf' target is a layer
        1 physical interface or "port".  The MonitorTarget will narrow the scope of the policy specified by
        the children of the MonitorTarget to be only the target class.

       :param parent:  Parent object that his monitor target is a child of. It must be of type MonitorPolicy
       :param target:  String specifying the target class for the Monitor policy.
        """
        targetEnum = ['l1PhysIf']
        if not type(parent) in [MonitorPolicy]:
            raise TypeError('Parent of MonitorTarget must be one of type MonitorPolicy')
        if target not in targetEnum:
            raise ValueError('target must be one of:', targetEnum)

        self._parent = parent
        self.scope = target
        self.descr = ''
        self.name = ''
        self._parent.add_target(self)
        self.collection_policy = {}
        self.monitor_stats = {}
        # assume that it has not been written to APIC.  This is cleared if the policy is just loaded from APIC
        # or the policy is written to the APIC.
        self.modified = True

    def __str__(self):
        return self.scope


class MonitorStats(BaseMonitorClass):
    """
    This class is a child of a MonitorTarget object.  It is used to specify a scope for applying a monitoring policy
    that is more fine grained than the MonitorTarget.  Specifically, the MonitorStats object specifies a statistics
    family such as "ingress packets" or "egress bytes".
    """
    statsDictionary = {'eqptEgrBytes': 'egrBytes', 'eqptEgrPkts': 'egrPkts',
                       'eqptEgrTotal': 'egrTotal', 'eqptEgrDropPkts': 'egrDropPkts',
                       'eqptIngrBytes': 'ingrBytes', 'eqptIngrPkts': 'ingrPkts',
                       'eqptIngrTotal': 'ingrTotal', 'eqptIngrDropPkts': 'ingrDropPkts',
                       'eqptIngrUnkBytes': 'ingrUnkBytes', 'eqptIngrUnkPkts': 'ingrUnkPkts',
                       'eqptIngrStorm': 'ingrStorm'}

    statsFamilyEnum = ['egrBytes', 'egrPkts', 'egrTotal', 'egrDropPkts', 'ingrBytes', 'ingrPkts',
                       'ingrTotal', 'ingrDropPkts', 'ingrUnkBytes', 'ingrUnkPkts', 'ingrStorm']

    def __init__(self, parent, statsFamily):
        """
        The MonitorStats object must always be initialized with a parent object of type MonitorTarget.
        It sets the scope of its children collection policies (CollectionPolicy) to a particular statistics family.

        The MonitorStats object contains a dictionary of collection policies called collection_policy.  This
        is a dictionary of children CollectionPolicy objects indexed by their granularity, e.g. '5min', '15min',
        etc.

       :param parent: Parent object that this monitor stats object should be applied to.
                       This must be an object of type MonitorTarget.
       :param statsFamily: String specifying the statistics family that the children collection policies should
                       be applied to.  Possible values are:['egrBytes', 'egrPkts', 'egrTotal', 'egrDropPkts',
                       'ingrBytes', 'ingrPkts', 'ingrTotal', 'ingrDropPkts', 'ingrUnkBytes', 'ingrUnkPkts', 'ingrStorm']
        """
        if not type(parent) in [MonitorTarget]:
            raise TypeError('Parent of MonitorStats must be one of type MonitorTarget')
        if statsFamily not in MonitorStats.statsFamilyEnum:
            raise ValueError('statsFamily must be one of:', statsFamilyEnum)

        self._parent = parent
        self.scope = statsFamily
        self.descr = ''
        self.name = ''
        self._parent.add_stats(self)
        self.collection_policy = {}
        # assume that it has not been written to APIC.  This is cleared if the policy is just loaded from APIC
        # or the policy is written to the APIC.
        self.modified = True

    def __str__(self):
        return self.scope


class CollectionPolicy(BaseMonitorClass):
    """
    This class is a child of a MonitorPolicy object, MonitorTarget object or a MonitorStats object.  It is where the statistics collection
    policy is actually specified.  It applies to all of the statistics that are at the scope level of the parent object,
    i.e. all, specific to a target, or specific to a statistics family.  What is specified in the CollectionPolicy is the
    time granularity of the collection and how much history to retain.  For example, the granularity might be 5 minutes (5min)
    or 1 hour (1h).  How much history to retain is similarly specified.  For example you might specify that it be kept for 10 days (10d)
    or 2 years (2year).

    If the CollectionPolicy is a child of a MonitorStats object, it can optionally have children that specify the policy
    for raising threshold alarms on the fields in the stats family specified in the MonitorStats object.  This has yet to be
    implemented.

    This object is roughly the same as the statsColl and statsHierColl objects in the APIC.
    """
    granularityEnum = ['5min', '15min', '1h', '1d', '1w', '1mo', '1qtr', '1year']  # this must be in order from small to large
    retentionEnum = ['none', 'inherited', '5min', '15min', '1h', '1d',
                     '1w', '10d', '1mo', '1qtr', '1year', '2year', '3year']

    def __init__(self, parent, granularity, retention, adminState='enabled'):
        """
        The CollectionPolicy must always be initialized with a parent object of type MonitorPolicy, MonitorTarget or MonitorStats.
        The granularity must also be specifically specified.  The retention period can be specified, set to "none", or set to "inherited".
        Note that the "none" value is a string, not the Python None.  When the retention period is set to "none" there will be no
        historical stats kept.  However, assuming collection is enabled, stats will be kept for the current time period.

        If the retention period is set to "inherited", the value will be inherited from the less specific policy directly above this one.
        The same applies to the adminState value.  It can be 'disabled', 'enabled', or 'inherited'.  If 'disabled', the current scope of
        counters are not gathered.  If enabled, they are gathered.  If 'inherited', it will be according to the next higher scope.

        Having the 'inherited' option on the retention and administrative status allows these items independently controlled at the current
        stats granularity.  For example, you can specify that ingress unknown packets are gathered every 15 minutes by setting
        adding a collection policy that specifies a 15 minutes granularity and an adminState of 'enabled' under a MonitorStats object that
        sets the scope to be ingress unknown packets.  This might override a higher level policy that disabled collection at a 15 minute
        interval.   However, you can set the retention in that same object to be "inherited" so that this specific policy does not
        change the retention behavior from that of the higher, less specific, policy.

        When the CollectionPolicy is a child at the top level, i.e. of the MonitorPolicy, the 'inherited' option is not allowed
        because there is no higher level policy to inherit from.  If this were to happen, 'inherited' will be treated as
        'enabled'.

       :param parent: Parent object that this collection policy should be applied to.
                       This must be an object of type MonitorStats, MonitorTarget, or MonitorPolicy.
       :param granularity:  String specifying the time collection interval or granularity of this policy.  Possible values are:
                       ['5min', '15min', '1h', '1d', '1w', '1mo', '1qtr', '1year'].
       :param retention: String specifying how much history to retain the collected statistics for.  The retention will be for
                       time units of the granularity specified.  Possible values are ['none', 'inherited', '5min', '15min', '1h',
                       '1d', '1w', '10d', '1mo', '1qtr', '1year', '2year', '3year'].
       :param adminState:  Administrative status.  String to specify whether stats should be collected at the specified
                       granularity.  Possible values are ['enabled', 'disabled', 'inherited'].  The default if not
                       specified is 'enabled'.
        """
        adminStateEnum = ['enabled', 'disabled', 'inherited']

        if type(parent) not in [MonitorStats, MonitorTarget, MonitorPolicy]:
            raise TypeError('Parent of collection policy must be one of MonitorStats, MonitorTarget, or MonitorPolicy')
        if granularity not in CollectionPolicy.granularityEnum:
            raise ValueError('granularity must be one of:', granularityEnum)
        if retention not in CollectionPolicy.retentionEnum:
            raise ValueError('retention must be one of:', retentionEnum)
        if adminState not in adminStateEnum:
            raise ValueError('adminState must be one of:', adminStateEnum)

        self._parent = parent
        self.granularity = granularity

        self.retention = retention
        self.adminState = adminState
        self._children = []

        self._parent.add_collection_policy(self)
        # assume that it has not been written to APIC.  This is cleared if the policy is just loaded from APIC
        # or the policy is written to the APIC.
        self.modified = True

    def __str__(self):
        return self.granularity

    def setAdminState(self, adminState):
        """
        Sets the administrative status.

        :param adminState:  Administrative status.  String to specify whether stats should be collected at the specified
                       granularity.  Possible values are ['enabled', 'disabled', 'inherited'].  The default if not
                       specified is 'enabled'.
        """
        if self.adminState != adminState:
            self.modified = True

        self.adminState = adminState

    def setRetention(self, retention):
        """
        Sets the retention period.

       :param retention: String specifying how much history to retain the collected statistics for.  The retention will be for
                       time units of the granularity specified.  Possible values are ['none', 'inherited', '5min', '15min', '1h',
                       '1d', '1w', '10d', '1mo', '1qtr', '1year', '2year', '3year'].
        """

        if self.retention != retention:
            self.modified = True

        self.retention = retention
