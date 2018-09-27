###############################################################################
#                                  _    ____ ___                              #
#                                 / \  / ___|_ _|                             #
#                                / _ \| |    | |                              #
#                               / ___ \ |___ | |                              #
#                         _____/_/   \_\____|___|_ _                          #
#                        |_   _|__   ___ | | | _(_) |_                        #
#                          | |/ _ \ / _ \| | |/ / | __|                       #
#                          | | (_) | (_) | |   <| | |_                        #
#                          |_|\___/ \___/|_|_|\_\_|\__|                       #
#                                                                             #
###############################################################################
#                                                                             #
# Copyright (c) 2015 Cisco Systems                                            #
# All Rights Reserved.                                                        #
#                                                                             #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may  #
#    not use this file except in compliance with the License. You may obtain  #
#    a copy of the License at                                                 #
#                                                                             #
#        http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                             #
#    Unless required by applicable law or agreed to in writing, software      #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT#
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the #
#    License for the specific language governing permissions and limitations  #
#    under the License.                                                       #
#                                                                             #
###############################################################################
"""  Main ACI Toolkit module
     This is the main module that comprises the ACI Toolkit.
"""
from collections import Sequence
import logging
from operator import attrgetter, itemgetter
import re
import sys
import copy

from requests.compat import urlencode
from requests.exceptions import ConnectionError

from .acibaseobject import BaseACIObject, BaseInterface, _Tag
from .aciphysobject import Interface, Fabric
from .acisession import Session
from .aciTable import Table
from .acicounters import InterfaceStats
from .acitoolkitlib import Credentials


class Tenant(BaseACIObject):
    """
    The Tenant class is used to represent the tenants within the acitoolkit
    object model.  In the APIC model, this class is roughly equivalent to
    the fvTenant class.
    """

    def __init__(self, name, parent=None):
        """
        :param name: String containing the Tenant name
        :param parent: None or An instance of Fabric class representing the Pod
                       which contains this Tenant.
        """
        if parent is not None and not isinstance(parent, Fabric) and not isinstance(parent, LogicalModel):
            raise TypeError('Parent must be None or an instance of Fabric class. Parent given as %s' % type(parent))
        super(Tenant, self).__init__(name, parent)

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvTenant']

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return LogicalModel

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-{}.json?subscription=yes'.format(self.name)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/tn-', '/']

    def get_json(self):
        """
        Returns json representation of the fvTenant object

        :returns: A json dictionary of fvTenant
        """
        attr = self._generate_attributes()
        return super(Tenant, self).get_json(self._get_apic_classes()[0],
                                            attributes=attr)

    def push_to_apic(self, session):
        """
        Push the appropriate configuration to the APIC for this Tenant.
        All of the subobject configuration will also be pushed.

        :param session: the instance of Session used for APIC communication
        :returns: Requests Response code
        """
        resp = session.push_to_apic(self.get_url(),
                                    self.get_json())
        return resp

    def _get_url_extension(self):

        rn = self._get_name_dn_delimiters()[0] + self.name
        return rn

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'fvAp': AppProfile,
                'fvBD': BridgeDomain,
                'vzCPIf': ContractInterface,
                'fvCtx': Context,
                'vzBrCP': Contract,
                'vzFilter': Filter,
                'vzTaboo': Taboo,
                'l3extOut': OutsideL3}

    @classmethod
    def get_deep(cls, session, names=(), limit_to=(), subtree='full', config_only=False, parent=None):
        """
        Get the Tenant objects and all of the children objects.

        :param session: the instance of Session used for APIC communication
        :param names: list of strings containing the tenant names. If no list is given, all tenants will be collected.
                      It should be noted that if relations extend across tenants, the relation will only be
                      populated if the tenants are included in this list.
        :param limit_to: list of strings containing the APIC classes to limit the collection to i.e. ['fvTenant',
                         'fvBD']. If no list is given, all classes will be collected.
        :param subtree: String containing the rsp-subtree option. Default is 'full'.
        :param config_only: Boolean containing whether to collect only configurable parameters
        :param parent: The parent instance to assign to the tenant objects. If None, a Fabric instance will be created.
        :returns: Requests Response code
        """
        resp = []
        if isinstance(names, str) or \
                not isinstance(names, Sequence) or \
                not all(isinstance(name, str) for name in names):
            raise TypeError('names should be a Sequence of strings')
        names = list(names) or [tenant.name for tenant in Tenant.get(session)]
        if isinstance(limit_to, str) or \
                not isinstance(limit_to, Sequence) or \
                not all(isinstance(class_name, str) for class_name in limit_to):
            raise TypeError('limit_to should be a Sequence of strings')
        limit_to = list(limit_to)
        if 'common' in names:
            # If tenant common is part of the list, put it at the front so we populate that first
            names.remove('common')
            names.insert(0, 'common')
        params = {'query-target': 'self', 'rsp-subtree': subtree}
        if len(limit_to):
            params['rsp-subtree-class'] = ','.join(limit_to)
        if config_only:
            params['rsp-prop-include'] = 'config-only'
        query = urlencode(params)
        objs = []
        full_data = []
        if parent is None:
            parent = Fabric()
        for name in names:
            query_url = '/api/mo/uni/tn-{}.json?{}'.format(name, query)
            ret = session.get(query_url)

            # the following works around a bug encountered in the json returned from the APIC
            # Python3 throws an error 'TypeError: 'str' does not support the buffer interface'
            # This error gets catched and the replace is done with byte code in a Python3 compatible way
            try:
                ret._content = ret._content.replace("\\\'", "'")
            except TypeError:
                ret._content = ret._content.replace(b"\\\'", b"'")

            data = ret.json()['imdata']
            if len(data):
                full_data.append(data[0])
                obj = super(Tenant, cls).get_deep(full_data=data,
                                                  working_data=data,
                                                  parent=parent,
                                                  limit_to=limit_to,
                                                  subtree=subtree,
                                                  config_only=config_only)
                if obj is not None:
                    objs.append(obj)
                    resp.append(obj)
                else:
                    print(name, 'resulted in a null object')
        obj_dict = build_object_dictionary(objs)
        for obj in objs:
            obj._extract_relationships(full_data, obj_dict)
        return resp

    @classmethod
    def get(cls, session, parent=None):
        """
        Gets all of the tenants from the APIC.

        :param parent: Parent object of the Tenant
        :param session: the instance of Session used for APIC communication
        :returns: a list of Tenant objects
        """
        tenants = BaseACIObject.get(session, cls, cls._get_apic_classes()[0])

        if parent:
            if isinstance(parent, LogicalModel):
                for tenant in tenants:
                    parent.add_child(tenant)
        return tenants

    @classmethod
    def exists(cls, session, tenant):
        """
        Check if a tenant exists on the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant to check if exists on the APIC
        :returns: True or False
        """
        apic_tenants = cls.get(session)
        return any(apic_tenant == tenant for apic_tenant in apic_tenants)

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

    @staticmethod
    def get_table(tenants, title=''):
        """
        Will create table of switch context information

        :param title:
        :param tenants:
        """

        headers = ['Tenant', 'Description']
        data = []
        for tenant in sorted(tenants):
            data.append([
                tenant.name,
                tenant.descr])

        data = sorted(data)
        table = Table(data, headers, title=title + 'Tenant')
        return [table, ]


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
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvAp']

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'fvAEPg': EPG, }

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/ap-', '/']

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/ap-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    @classmethod
    def _get_name_from_dn(cls, dn):
        if '/LDevInst-' in dn or '/lDev-' in dn:
            return 'ServiceGraph'
        elif '/ap-' not in dn:
            return None
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


    @staticmethod
    def get_table(app_profiles, title=''):
        """
        Will create table of app_profile information for a given tenant

        :param title:
        :param app_profiles:
        """
        result = []
        headers = ['Tenant', 'App Profile', 'Description',
                   'EPGs']

        by_name = attrgetter('name')
        for app_profile in sorted(app_profiles, key=by_name):
            data = []
            for epg in sorted(app_profile.get_children(EPG), key=by_name):
                data.append([
                    app_profile.get_parent().name,
                    app_profile.name,
                    app_profile.descr,
                    epg.name,
                ])
            result.append(Table(data, headers, title=title + 'Application Profile: {0}'.format(app_profile.name)))
        return result


class L2Interface(BaseACIObject):
    """ The L2Interface class creates an logical L2 interface that can be\
        attached to a physical interface. This interface defines the L2\
        encapsulation i.e. VLAN, VXLAN, or NVGRE
    """

    def __init__(self, name, encap_type, encap_id, encap_mode=None):
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
        self.encap_mode = encap_mode

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

    @staticmethod
    def parse_encap(encap):
        """
        Parses the encap_type and encap_id from a json encap string
        Examples: vlan-515 / vxlan-5000

        :param encap: String containing the json encap format
        :returns: encap_type, encap_id
        """
        encap_type, encap_id = encap.split('-')

        return encap_type, encap_id


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

    def get_all_provided(self, deleted=False):
        """
        Get all of the Contracts provided by this EPG

        :param deleted: Boolean indicating whether to get Contracts that are provided
                        or that the provided was marked as deleted
        :returns: List of Contract objects that are provided by the EPG.
        """
        if deleted:
            return self._get_all_detached_relation(Contract, 'provided')
        else:
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

    def get_all_consumed(self, deleted=False):
        """
        Get all of the Contracts consumed by this EPG

        :param deleted: Boolean indicating whether to get Contracts that are consumed
                        or that the consumed was marked as deleted
        :returns: List of Contract objects that are consumed by the EPG.
        """
        if deleted:
            return self._get_all_detached_relation(Contract, 'consumed')
        else:
            return self._get_all_relation(Contract, 'consumed')

    def consume_cif(self, contract_interface):
        """
        Make this EPG consume a ContractInterface

        :param contract_interface: ContractInterface class instance to be consumed by this EPG.
        :returns: True
        """

        if self.does_consume_cif(contract_interface):
            return True
        self._add_relation(contract_interface, 'consumed')
        return True

    def does_consume_cif(self, contract_interface):
        """
        Check if this EPG consumes a specific Contract

        :param contract_interface:
        :returns: True or False.  True if the EPG does consume the ContractInterface.
        """
        return self._has_relation(contract_interface, 'consumed')

    def dont_consume_cif(self, contract_interface):
        """
        Make this EPG not consume a ContractInterface.  It does not check to see
        if the ContractInterface was already consumed

        :param contract_interface:
        :returns: True
        """
        self._remove_relation(contract_interface, 'consumed')
        return True

    def get_all_consumed_cif(self, deleted=False):
        """
        Get all of the ContractInterfaces consumed by this EPG

        :param deleted: Boolean indicating whether to get ContractInterfaces that
                        are consumed or that the consumed was marked as deleted
        :returns: List of ContractInterface objects that are consumed by the EPG.
        """
        if deleted:
            return self._get_all_detached_relation(ContractInterface, 'consumed')
        else:
            return self._get_all_relation(ContractInterface, 'consumed')

    def protect(self, taboo):
        """
        Make this EPG protected by a Taboo

        :param taboo: Instance of Taboo class to protect this EPG.
        :returns: True
        """
        if self.does_protect(taboo):
            return True
        self._add_relation(taboo, 'protected')
        return True

    def does_protect(self, taboo):
        """
        Check if this EPG is protected by a specific Taboo.

        :param taboo: Instance of Taboo class to check if it protects
                         this EPG.
        :returns: True or False.  True if the EPG is protected by the Taboo.
        """
        return self._has_relation(taboo, 'protected')

    def dont_protect(self, taboo):
        """
        Make this EPG not protected by a Taboo

        :param taboo: Instance of Taboo class to no longer protect\
                         this EPG.
        :returns: True
        """
        self._remove_relation(taboo, 'protected')

    def get_all_protected(self, deleted=False):
        """
        Get all of the Taboos protecting this EPG

        :param deleted: Boolean indicating whether to get Taboos that are protected
                        or that the protected was marked as deleted

        :returns: List of Taboo objects that are protecting the EPG.
        """
        if deleted:
            return self._get_all_detached_relation(Taboo, 'protected')
        else:
            return self._get_all_relation(Taboo, 'protected')

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
            text = {'fvRsProv': {'attributes': {'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract in self.get_all_consumed():
            text = {'fvRsCons': {'attributes': {'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract_interface in self.get_all_consumed_cif():
            text = {'fvRsConsIf': {'attributes': {'tnVzCPIfName': contract_interface.name}}}
            children.append(text)
        for taboo in self.get_all_protected():
            text = {'fvRsProtBy': {'attributes': {'tnVzTabooName': taboo.name}}}
            children.append(text)
        for contract in self.get_all_provided(deleted=True):
            text = {'fvRsProv': {'attributes': {'status': 'deleted', 'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract in self.get_all_consumed(deleted=True):
            text = {'fvRsCons': {'attributes': {'status': 'deleted', 'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract_interface in self.get_all_consumed_cif(deleted=True):
            text = {'fvRsConsIf': {'attributes': {'status': 'deleted', 'tnVzCPIfName': contract_interface.name}}}
            children.append(text)
        for taboo in self.get_all_protected(deleted=True):
            text = {'fvRsProtBy': {'attributes': {'status': 'deleted', 'tnVzTabooName': taboo.name}}}
            children.append(text)
        return children

    @classmethod
    def get(cls, session, parent=None, tenant=None):
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


class AttributeCriterion(BaseACIObject):
    """ AttributeCriterion : roughly equivalent to fvCrtrn """

    def __init__(self, name, parent=None):
        """
        Initializes the AttributeCriterion with a name and optionally an EPG parent

        :param name: String containing the AttributeCriterion name
        :param parent: Instance of the EPG class representing where this AttributeCriterion is defined
        :return: Instance of AttributeCriterion class
        """
        if parent:
            if not isinstance(parent, EPG):
                raise TypeError('Parent must be instance of EPG')
            parent.is_attributed_based = True
        super(AttributeCriterion, self).__init__(name, parent)
        self._match = 'any'
        self._ip_addresses = []

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return EPG

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/ap-%s/epg-%s/crtrn.json?subscription=yes' % (
            self._parent._parent._parent.name, self._parent._parent.name, self._parent.name)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/crtrn', '/']

    @property
    def match(self):
        """
        Return the match property
        :return: String containing the match property. Possible values are 'any' or 'all'
        """
        return self._match

    @match.setter
    def match(self, x):
        """
        Set the match property
        :param x: String containing the match property. Possible values are 'any' or 'all'
        :return: None
        """
        assert x in ['any', 'all']
        self._match = x

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvCrtrn']

    def _generate_attributes(self):
        attr = super(AttributeCriterion, self)._generate_attributes()
        attr['match'] = self.match
        return attr

    def add_ip_address(self, ip_addr):
        """
        Add an IP address as an attribute

        :param ip_addr: String containing the IP address
        :return: None
        """
        if ip_addr not in self._ip_addresses:
            self._ip_addresses.append(ip_addr)

    def get_ip_addresses(self):
        """
        return the list of IP addresses
        """
        return self._ip_addresses

    @classmethod
    def get_deep(cls, full_data, working_data, parent=None, limit_to=(), subtree='full', config_only=False):
        attr_crtrn_data = working_data[0]['fvCrtrn']
        attr_ctrn = AttributeCriterion(str(attr_crtrn_data['attributes']['name']), parent)
        attr_ctrn._populate_from_attributes(attr_crtrn_data['attributes'])
        for child in attr_crtrn_data.get('children', ()):
            if 'fvIpAttr' in child:
                attr_ctrn.add_ip_address(str(child['fvIpAttr']['attributes']['ip']))

    def get_json(self):
        """
        Returns JSON representation of the AttributeCriterion
        :return:
        """
        attr = self._generate_attributes()
        children = []
        for ip_address in self._ip_addresses:
            child = {'fvIpAttr': {'attributes': {'name': ip_address.split('/')[0],
                                                 'ip': ip_address},
                                  'children': []}}
            children.append(child)
        return super(AttributeCriterion, self).get_json(self._get_apic_classes()[0],
                                                        attributes=attr,
                                                        children=children)


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
        if parent:
            if not isinstance(parent, AppProfile):
                raise TypeError('Parent must be instance of AppProfile')
        super(EPG, self).__init__(epg_name, parent)
        self._leaf_bindings = []
        self.match_type = None
        self.class_id = None
        self.scope = None
        self._deployment_immediacy = None
        self._intra_epg_isolation = False
        self._dom_deployment_immediacy = None
        self._dom_resolution_immediacy = None
        self._is_attribute_based = False
        self._base_epg = None

    def _generate_attributes(self):
        attributes = super(EPG, self)._generate_attributes()
        if self._is_attribute_based:
            attributes['isAttrBasedEPg'] = 'yes'
        if self._intra_epg_isolation:
            attributes['pcEnfPref'] = 'enforced'
        return attributes

    @property
    def is_attributed_based(self):
        """
        Get whether the EPG is attribute based
        :return: True if attribute based. False otherwise.
        """
        return self._is_attribute_based

    @is_attributed_based.setter
    def is_attributed_based(self, x):
        """
        Set the attribute_based flag.  Indicates that the EPG is attribute based.
        :param x: String containing 'true' or 'yes' indicates that the EPG is attribute based.
        :return: None
        """
        if isinstance(x, str):
            if x.lower() in ['true', 'yes']:
                self._is_attribute_based = True
            else:
                self._is_attribute_based = False
        self._is_attribute_based = x

    def set_base_epg(self, epg):
        """
        Sets the Base EPG.  Used by Attribute-based EPGs to indicate that the BridgeDomain, NodeAttach, and
        PathAttach relations should be copied from the base EPG when generating JSON.

        :param epg: EPG class instance of the Base EPG
        :return: None
        """
        self._base_epg = epg

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvAEPg']

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'fvCEp': Endpoint,
                'fvStCEp': Endpoint,
                'fvCrtrn': AttributeCriterion}

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return AppProfile

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/ap-%s/epg-%s.json?subscription=yes' % (
            self._parent._parent.name, self._parent.name, self.name)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/epg-', '/']

    @classmethod
    def _get_name_from_dn(cls, dn):
        if '/LDevInst-' in dn or '/lDev-' in dn:
            return 'ServiceGraph'
        elif '/epg-' not in dn:
            return None
        return dn.split('/epg-')[1].split('/')[0]

    def _populate_from_attributes(self, attributes):
        """
        Sets the attributes when creating objects from the APIC.
        Called from the base object when calling the classmethod get()
        """
        super(EPG, self)._populate_from_attributes(attributes)
        if 'matchT' in attributes:
            self.match_type = str(attributes.get('matchT'))
        if 'pcTag' in attributes:
            self.class_id = str(attributes.get('pcTag'))
        if 'scope' in attributes:
            self.scope = str(attributes.get('scope'))
        if 'name' in attributes:
            self.name = str(attributes.get('name'))
        elif self.dn != '':
            self.name = self._get_name_from_dn(self.dn)
        if str(attributes.get('isAttrBasedEPg')).lower() in ['true', 'yes']:
            self._is_attribute_based = True
        else:
            self._is_attribute_based = False
        if attributes.get('pcEnfPref') == 'enforced':
            self._intra_epg_isolation = True
        else:
            self._intra_epg_isolation = False

    # Infrastructure Domain references
    def add_infradomain(self, infradomain):
        """
        Add Infrastructure Domain to the EPG

        :param infradomain:  Instance of InfraDomain class.
        """
        if not isinstance(infradomain, EPGDomain):
            raise TypeError('add_infradomain not called with InfraDomain')
        self.populate_children(True)
        if self.has_child(infradomain):
            return
        self.add_child(infradomain)
        infradomain._add_relation(self)

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

    def set_deployment_immediacy(self, immediacy):
        """
        Set the deployment immediacy of the EPG

        :param immediacy: String containing either "immediate" or "lazy"
        """
        self._deployment_immediacy = immediacy

    def set_intra_epg_isolation(self, isolation):
        """
        Set the intra-EPG isolation of the EPG

        :param isolation: String containing either "unenforced" or "enforced"
        """
        self._intra_epg_isolation = isolation

    def set_dom_deployment_immediacy(self, immediacy):
        """
        Set the deployment immediacy for PhysDomain of the EPG

        :param immediacy: String containing either "immediate" or "lazy"
        """
        self._dom_deployment_immediacy = immediacy

    def set_dom_resolution_immediacy(self, immediacy):
        """
        Set the resolution immediacy for PhysDomain of the EPG

        :param immediacy: String containing either "immediate" or "lazy"
        """
        self._dom_resolution_immediacy = immediacy

    def _get_all_contracts(self, contract_type, deleted=False, include_any_epg=False):
        """
        Internal common function to get all of the Contracts/Taboos used by this EPG

        :param contract_type: String containing the contract type. Valid values are:
                              'provided', 'consumed'
        :param deleted: Boolean indicating whether to get Contracts that are provided
                        or that the provided was marked as deleted
        :param include_any_epg: Boolean indicating whether to include Contracts that
                                are provided due to inheritance from an AnyEPG within
                                the same Context providing it.
        :returns: List of Contract objects that are provided by the EPG.
        """
        if contract_type not in ['provided', 'consumed']:
            raise ValueError
        resp = []
        if include_any_epg:
            # Check if the tenant context has an AnyEPG
            any_epgs = []
            if self.has_bd() and self.get_bd().has_context():
                any_epgs += self.get_bd().get_context().get_children(only_class=AnyEPG)
            else:
                # Look for AnyEPG in the tenant common Context
                try:
                    my_fabric = self.get_parent().get_parent().get_parent()
                    tenants = my_fabric.get_children(only_class=Tenant)
                    for tenant in tenants:
                        if tenant.name == 'common':
                            common_contexts = tenant.get_children(only_class=Context)
                            for context in common_contexts:
                                if context.name == 'default':
                                    any_epgs += context.get_children(only_class=AnyEPG)
                except AttributeError:
                    # Couldn't find tenant common
                    pass
            for any_epg in any_epgs:
                if contract_type == 'provided':
                    resp += any_epg.get_all_provided(deleted=deleted)
                else:
                    resp += any_epg.get_all_consumed(deleted=deleted)
        if contract_type == 'provided':
            resp += super(EPG, self).get_all_provided(deleted=deleted)
        else:
            resp += super(EPG, self).get_all_consumed(deleted=deleted)
        return resp

    def get_all_provided(self, deleted=False, include_any_epg=False):
        """
        Get all of the Contracts provided by this EPG

        :param deleted: Boolean indicating whether to get Contracts that are provided
                        or that the provided was marked as deleted
        :param include_any_epg: Boolean indicating whether to include Contracts that
                                are provided due to inheritance from an AnyEPG within
                                the same Context that this EPG is in.
        :returns: List of Contract objects that are provided by the EPG.
        """
        return self._get_all_contracts(contract_type='provided',
                                       deleted=deleted,
                                       include_any_epg=include_any_epg)

    def get_all_consumed(self, deleted=False, include_any_epg=False):
        """
        Get all of the Contracts consumed by this EPG

        :param deleted: Boolean indicating whether to get Contracts that are consumed
                        or that the consumed was marked as deleted
        :param include_any_epg: Boolean indicating whether to include Contracts that
                                are consumed due to inheritance from an AnyEPG within
                                the same Context that this EPG is in.
        :returns: List of Contract objects that are consumed by the EPG.
        """
        return self._get_all_contracts(contract_type='consumed',
                                       deleted=deleted,
                                       include_any_epg=include_any_epg)

    def _extract_relationships(self, data, obj_dict):
        app_profile = self.get_parent()
        tenant = app_profile.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                tenant_children = tenant_data['fvTenant']['children']
        epg_children = None
        for app in tenant_children:
            if 'fvAp' in app:
                if app['fvAp']['attributes']['name'] == app_profile.name:
                    for epg in app['fvAp']['children']:
                        if 'fvAEPg' in epg:
                            epg_name = epg['fvAEPg']['attributes']['name']
                            if epg_name == self.name:
                                epg_children = epg['fvAEPg']['children']
        for child in epg_children:
            if 'fvRsBd' in child:
                bd_name = child['fvRsBd']['attributes']['tnFvBDName']
                # bd_search = Search()
                # bd_search.name = bd_name
                # objs = tenant.find(bd_search)
                if BridgeDomain in obj_dict:
                    objs = obj_dict[BridgeDomain]
                    found = False
                    for bd in objs:
                        # if isinstance(bd, BridgeDomain):
                        if bd.name == bd_name and bd.get_parent() == tenant:
                            self.add_bd(bd)
                            found = True
                    if not found:
                        for bd in objs:
                            if bd.name == bd_name and bd.get_parent().name == 'common':
                                self.add_bd(bd)

            elif 'fvRsPathAtt' in child:
                int_attributes = child['fvRsPathAtt']['attributes']
                int_dn = int_attributes['tDn']
                if Interface.is_dn_vpc(int_dn):
                    inter = PortChannel.create_from_dn(int_dn)
                else:
                    int_type, pod, node, module, port = Interface.parse_dn(int_dn)
                    inter = Interface(int_type, pod, node, module, port)
                encap = int_attributes['encap']
                encap_type, encap_id = L2Interface.parse_encap(encap)
                encap_mode = int_attributes['mode']
                if Interface.is_dn_vpc(int_dn):
                    l2int = L2Interface('l2_int_{}-{}_on_{}'.format(encap_type, encap_id, inter.name),
                                        encap_type,
                                        encap_id,
                                        encap_mode)
                else:
                    l2int = L2Interface('l2_int_{}-{}_on_{}{}/{}/{}/{}'.format(encap_type, encap_id, int_type,
                                                                               pod, node, module, port),
                                        encap_type,
                                        encap_id,
                                        encap_mode)
                l2int.attach(inter)
                self.attach(l2int)
            elif 'fvRsProv' in child:
                contract_name = child['fvRsProv']['attributes']['tnVzBrCPName']
                # contract_search = Search()
                # contract_search.name = contract_name
                # objs = tenant.find(contract_search)
                # if len(objs):
                #     for contract in objs:
                #         if isinstance(contract, Contract):
                # else:
                #     # Need to check tenant common (if available)
                #     fabric = tenant.get_parent()
                #     if fabric is not None:
                #         tenant_search = Search()
                #         tenant_search.name = 'common'
                #         tenant_common = fabric.find(tenant_search)
                #         if len(tenant_common):
                #             objs = tenant_common[0].find(contract_search)
                #             if len(objs):
                #                 for contract in objs:
                #                     if isinstance(contract, Contract):
                #                         self.provide(contract)

                if Contract in obj_dict:
                    objs = obj_dict[Contract]
                else:
                    objs = []
                if len(objs):
                    found = False
                    for contract in objs:
                        if contract.name == contract_name and contract.get_parent() == tenant:
                            self.provide(contract)
                            found = True
                    if not found:
                        for contract in objs:
                            if contract.name == contract_name and contract.get_parent().name == 'common':
                                self.provide(contract)
            elif 'fvRsCons' in child:
                contract_name = child['fvRsCons']['attributes']['tnVzBrCPName']
                # contract_search = Search()
                # contract_search.name = contract_name
                # objs = tenant.find(contract_search)
                # if len(objs):
                #     for contract in objs:
                #         if isinstance(contract, Contract):
                #             self.consume(contract)
                # else:
                # Need to check tenant common (if available)
                # fabric = tenant.get_parent()
                # if fabric is not None:
                #     tenant_search = Search()
                #     tenant_search.name = 'common'
                #     tenant_common = fabric.find(tenant_search)
                #     if len(tenant_common):
                #         objs = tenant_common[0].find(contract_search)
                #         if len(objs):
                #             for contract in objs:
                #                 if isinstance(contract, Contract):
                #                     self.consume(contract)
                if Contract in obj_dict:
                    objs = obj_dict[Contract]

                    if len(objs):
                        found = False
                        for contract in objs:
                            if contract.name == contract_name and contract.get_parent() == tenant:
                                self.consume(contract)
                                found = True
                        if not found:
                            for contract in objs:
                                if contract.name == contract_name and contract.get_parent().name == 'common':
                                    self.consume(contract)

            elif 'fvRsDomAtt' in child:
                dom_attributes = child['fvRsDomAtt']['attributes']
                dom = EPGDomain(dom_attributes['tDn'], self)
                dom.tDn = dom_attributes['tDn']
                self._dom_deployment_immediacy = dom_attributes['instrImedcy']
                self._dom_resolution_immediacy = dom_attributes['resImedcy']
            elif 'fvRsConsIf' in child:
                contract_if_name = child['fvRsConsIf']['attributes']['tnVzCPIfName']
                if ContractInterface in obj_dict:
                    objs = obj_dict[ContractInterface]

                    if len(objs):
                        found = False
                        for contract_if in objs:
                            if contract_if.name == contract_if_name and contract_if.get_parent() == tenant:
                                self.consume_cif(contract_if)
                                found = True
                        if not found:
                            for contract_if in objs:
                                if contract_if.name == contract_if_name and contract_if.get_parent().name == 'common':
                                    self.consume_cif(contract_if)

        super(EPG, self)._extract_relationships(data, obj_dict)

    def add_static_leaf_binding(self, leaf_id, encap_type, encap_id, encap_mode="regular", immediacy="lazy", pod=1):
        """
        Adds a static leaf binding to this EPG.

        :param leaf_id: Integer containing the node ID (e.g. 101)
        :param encap_type: String containing the encapsulation type.\
        Valid values are 'vlan', 'vxlan', or 'nvgre'.
        :param encap_id: String containing the encapsulation specific\
        identifier representing the virtual L2 network (i.e. for VXLAN,\
        this is the numeric value of the VNID).

        :param encap_mode: String containing the encapsulation mode. Use
        "regular" for normal dot1q tagged traffic, "untagged" for traffic
        reaching the leaf without any dot1q tags, and "native" for
        traffic tagged with a 802.1P tag.

        :param immediacy: String containing either "immediate" or "lazy"
        :param pod: Integer containing the ACI Pod where the supplied leaf is located.
        """
        if immediacy not in ('immediate', 'lazy'):
            raise ValueError("Immediacy must be one of 'immediate' or 'lazy'")
        if encap_type not in ('vlan', 'vxlan', 'nvgre'):
            raise ValueError("Encap type must be one of 'vlan', 'vxlan', or 'nvgre'")
        if encap_mode not in ('regular', 'untagged', 'native'):
            raise ValueError("Encap mode must be one of 'regular', 'untagged', or 'native'")
        text = {
            'fvRsNodeAtt': {
                'attributes': {
                    'encap': "%s-%s" % (encap_type, str(encap_id)),
                    'instrImedcy': immediacy,
                    'mode': encap_mode,
                    'tDn': 'topology/pod-%s/node-%s' % (str(pod), str(leaf_id))
                }
            }
        }
        self._leaf_bindings.append(text)

    @staticmethod
    def get_from_json(self, data, parent=None):
        """
        returns a Tenant object from a json
        """
        for child in data['fvAEPg']['children']:
            if 'fvRsCons' in child:
                contract_name = child['fvRsCons']['attributes']['tnVzBrCPName']
                contract = Contract(contract_name)
                self.consume(contract)
            elif 'fvRsProv' in child:
                contract_name = child['fvRsProv']['attributes']['tnVzBrCPName']
                contract = Contract(contract_name)
                self.provide(contract)
            elif 'fvRsPathAtt' in child:
                vlan = child['fvRsPathAtt']['attributes']['encap']
                vlan_intf = L2Interface(name='',
                                        encap_type=vlan.split('-')[0],
                                        encap_id=vlan.split('-')[1])
                self.attach(vlan_intf)
            elif 'fvRsBd' in child:
                bd_name = child['fvRsBd']['attributes']['tnFvBDName']
                if isinstance(parent._parent, Tenant):
                    bds = parent._parent.get_children(BridgeDomain)
                    bd_exist = False
                    for bd in bds:
                        if bd.name == bd_name:
                            self.add_bd(bd)
                            bd_exist = True
                    if not bd_exist:
                        bd = BridgeDomain(bd_name, parent=parent._parent)
                        self.add_bd(bd)
        return super(EPG, self).get_from_json(self, data, parent=parent)

    # Output
    def get_json(self):
        """
        Returns json representation of the EPG

        :returns: json dictionary of the EPG
        """
        children = super(EPG, self)._get_common_json()
        if self.has_bd() or (self._base_epg is not None and self._base_epg.has_bd()):
            if self.has_bd():
                bd_name = self.get_bd().name
            else:
                bd_name = self._base_epg.get_bd().name
            text = {'fvRsBd': {'attributes': {'tnFvBDName': bd_name}}}
            children.append(text)
        # Static leaf bindings
        for leaf_binding in self._leaf_bindings:
            children.append(leaf_binding)
        if self._base_epg is not None:
            for leaf_binding in self._base_epg._leaf_bindings:
                no_encap_leaf_binding = copy.deepcopy(leaf_binding)
                if 'encap' in no_encap_leaf_binding['fvRsNodeAtt']['attributes']:
                    del no_encap_leaf_binding['fvRsNodeAtt']['attributes']['encap']
                no_encap_leaf_binding['fvRsNodeAtt']['attributes']['instrImedcy'] = 'immediate'
                children.append(no_encap_leaf_binding)

        is_interfaces = False
        for interface in self.get_interfaces():
            is_interfaces = True
            encap_text = '%s-%s' % (interface.encap_type,
                                    interface.encap_id)
            text = {'fvRsPathAtt': {'attributes': {'encap': encap_text,
                                                   'tDn': interface._get_path()}}}
            if interface.encap_mode:
                text['fvRsPathAtt']['attributes']['mode'] = interface.encap_mode
            if self._deployment_immediacy:
                text['fvRsPathAtt']['attributes']['instrImedcy'] = self._deployment_immediacy
            children.append(text)

            for ep in interface.get_all_attachments(Endpoint):
                ep_children = []
                for child in self.get_children():
                    ep_children.append({'fvStIp': {'attributes': {'addr': child.ip}, 'children': []}})
                path = interface._get_path()
                ep_children.append({'fvRsStCEpToPathEp': {'attributes': {'tDn': path},
                                                          'children': []}})
                text = {'fvStCEp': {'attributes': {'ip': ep.ip,
                                                   'mac': ep.mac,
                                                   'name': ep.name,
                                                   'encap': encap_text,
                                                   'type': 'silent-host'},
                                    'children': ep_children}}
                if ep.is_deleted():
                    text['fvStCEp']['attributes']['status'] = 'deleted'
                children.append(text)
        if is_interfaces:
            # Only add the all-vlans physical domain if nobody has
            # attached any other domain
            if len(self.get_children(only_class=EPGDomain)) == 0:
                text = {'fvRsDomAtt': {'attributes': {'tDn': 'uni/phys-allvlans'}}}
                children.append(text)

        vmm_domains = self.get_all_attached(VmmDomain)
        if self._base_epg is not None:
            vmm_domains += self._base_epg.get_all_attached(VmmDomain)
        for vmm in vmm_domains:
            text = {'fvRsDomAtt': {'attributes': {'tDn': vmm._get_path(),
                                                  'resImedcy': 'immediate'}}}

            if self._deployment_immediacy:
                text['fvRsDomAtt']['attributes']['instrImedcy'] = self._deployment_immediacy

            children.append(text)
        for interface in self.get_interfaces('detached'):
            text = {'fvRsPathAtt': {'attributes': {'encap': '%s-%s' % (interface.encap_type,
                                                                       interface.encap_id),
                                                   'status': 'deleted',
                                                   'tDn': interface._get_path()}}}
            children.append(text)
        attr = self._generate_attributes()
        return super(EPG, self).get_json(self._get_apic_classes()[0],
                                         attributes=attr,
                                         children=children)

    @staticmethod
    def get_table(epgs, title=''):
        """
        Will create table of EPG information for a given tenant

        :param epgs:
        :param title:
        """

        headers = ['Tenant', 'App Profile', 'EPG',
                   'Context', 'Bridge Domain',
                   'Provides', 'Consumes', 'Scope',
                   'Class ID', 'Match Type',
                   'Deployment Immed.']

        data = []
        for epg in sorted(epgs, key=attrgetter('name')):
            context = 'None'
            bd = 'None'
            if epg.has_bd():
                bd = epg.get_bd().name
                if epg.get_bd().has_context():
                    context = epg.get_bd().get_context().name
            consumes = epg.get_all_consumed()
            provides = epg.get_all_provided()

            index_max = max(len(consumes), len(provides), 1)
            for index in range(index_max):
                if index < len(consumes):
                    consume = consumes[index]
                else:
                    consume = ''

                if index < len(provides):
                    provide = provides[index]
                else:
                    provide = ''

                data.append([
                    epg.get_parent().get_parent().name,
                    epg.get_parent().name,
                    epg.name,
                    context,
                    bd,
                    provide,
                    consume,
                    epg.scope,
                    epg.class_id,
                    epg.match_type,
                    epg._deployment_immediacy,
                ])
        data = sorted(data)
        table = Table(data, headers, title=title + 'EPGs')
        return [table, ]


class OutsideEPG(CommonEPG):
    """
    OutsideEPG class, roughly equivalent to l3ext:InstP
    """
    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return OutsideL3

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['l3extInstP']

    def get_json(self):
        """
        Returns json representation of the EPG

        :returns: json dictionary of the EPG
        """
        children = super(OutsideEPG, self)._get_common_json()
        attr = self._generate_attributes()
        return super(OutsideEPG, self).get_json(self._get_apic_classes()[0],
                                                attributes=attr,
                                                children=children)

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'l3extSubnet': OutsideNetwork, }

    def _extract_relationships(self, data, obj_dict, epg_type='l3'):
        l3out = self.get_parent()
        tenant = l3out.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                tenant_children = tenant_data['fvTenant']['children']
        epg_children = []
        l3ext_out = epg_type + 'extOut'
        l3ext_instp = epg_type + 'extInstP'
        for l3out_child in tenant_children:
            if l3ext_out in l3out_child:
                if l3out_child[l3ext_out]['attributes']['name'] == l3out.name:
                    for l3epg in l3out_child[l3ext_out]['children']:
                        if l3ext_instp in l3epg:
                            if l3epg[l3ext_instp]['attributes']['name'] == self.name:
                                epg_children = l3epg[l3ext_instp]['children']
        for child in epg_children:
            if 'fvRsProv' in child:
                contract_name = child['fvRsProv']['attributes']['tnVzBrCPName']
                if Contract in obj_dict:
                    objs = obj_dict[Contract]

                    if len(objs):
                        found = False
                        for contract in objs:
                            if contract.name == contract_name and contract.get_parent() == tenant:
                                self.provide(contract)
                                found = True
                        if not found:
                            for contract in objs:
                                if contract.name == contract_name and contract.get_parent().name == 'common':
                                    self.provide(contract)

            elif 'fvRsCons' in child:
                contract_name = child['fvRsCons']['attributes']['tnVzBrCPName']
                if Contract in obj_dict:
                    objs = obj_dict[Contract]
                    if len(objs):
                        found = False
                        for contract in objs:
                            if contract.name == contract_name and contract.get_parent() == tenant:
                                self.consume(contract)
                                found = True
                        if not found:
                            for contract in objs:
                                if contract.name == contract_name and contract.get_parent().name == 'common':
                                    self.consume(contract)
            elif 'fvRsConsIf' in child:
                contract_if_name = child['fvRsConsIf']['attributes']['tnVzCPIfName']
                if ContractInterface in obj_dict:
                    objs = obj_dict[ContractInterface]

                    if len(objs):
                        found = False
                        for contract_if in objs:
                            if contract_if.name == contract_if_name and contract_if.get_parent() == tenant:
                                self.consume_cif(contract_if)
                                found = True
                        if not found:
                            for contract_if in objs:
                                if contract_if.name == contract_if_name and contract_if.get_parent().name == 'common':
                                    self.consume_cif(contract_if)

        super(OutsideEPG, self)._extract_relationships(data, obj_dict)

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/out-%s/instP-%s.json?subscription=yes' % (
            self._parent._parent.name, self._parent.name, self.name)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/instP-', '/']


class AnyEPG(CommonEPG):
    """
    AnyEPG class, roughly equivalent to vz:Any
    """
    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Context

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['vzAny']

    def get_json(self):
        """
        Returns json representation of the EPG

        :returns: json dictionary of the EPG
        """
        children = self._get_common_json()
        attr = self._generate_attributes()
        return super(AnyEPG, self).get_json(self._get_apic_classes()[0],
                                            attributes=attr,
                                            children=children)

    def _extract_relationships(self, data, obj_dict):
        context = self.get_parent()
        tenant = context.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                tenant_children = tenant_data['fvTenant']['children']
        epg_children = []
        for ctx in tenant_children:
            if 'fvCtx' in ctx:
                if ctx['fvCtx']['attributes']['name'] == context.name:
                    for ctx_child in ctx['fvCtx']['children']:
                        if 'vzAny' in ctx_child:
                            if 'children' in ctx_child['vzAny']:
                                epg_children = ctx_child['vzAny']['children']
                    break
        for child in epg_children:
            if 'vzRsAnyToProv' in child:
                contract_name = child['vzRsAnyToProv']['attributes']['tnVzBrCPName']

                if Contract in obj_dict:
                    objs = obj_dict[Contract]
                else:
                    objs = []
                if len(objs):
                    found = False
                    for contract in objs:
                        if contract.name == contract_name and contract.get_parent() == tenant:
                            self.provide(contract)
                            found = True
                    if not found:
                        for contract in objs:
                            if contract.name == contract_name and contract.get_parent().name == 'common':
                                self.provide(contract)
            elif 'vzRsAnyToCons' in child:
                contract_name = child['vzRsAnyToCons']['attributes']['tnVzBrCPName']
                if Contract in obj_dict:
                    objs = obj_dict[Contract]

                    if len(objs):
                        found = False
                        for contract in objs:
                            if contract.name == contract_name and contract.get_parent() == tenant:
                                self.consume(contract)
                                found = True
                        if not found:
                            for contract in objs:
                                if contract.name == contract_name and contract.get_parent().name == 'common':
                                    self.consume(contract)

            elif 'vzRsAnyToConsIf' in child:
                contract_if_name = child['vzRsAnyToConsIf']['attributes']['tnVzCPIfName']
                if ContractInterface in obj_dict:
                    objs = obj_dict[ContractInterface]

                    if len(objs):
                        found = False
                        for contract_if in objs:
                            if contract_if.name == contract_if_name and contract_if.get_parent() == tenant:
                                self.consume_cif(contract_if)
                                found = True
                        if not found:
                            for contract_if in objs:
                                if contract_if.name == contract_if_name and contract_if.get_parent().name == 'common':
                                    self.consume_cif(contract_if)

        super(AnyEPG, self)._extract_relationships(data, obj_dict)

    def _get_common_json(self):
        """Internal routine to generate JSON common to EPGs and Outside EPGs"""
        children = []
        for contract in self.get_all_provided():
            text = {'vzRsAnyToProv': {'attributes': {'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract in self.get_all_consumed():
            text = {'vzRsAnyToCons': {'attributes': {'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract_interface in self.get_all_consumed_cif():
            text = {'vzRsAnyToConsIf': {'attributes': {'tnVzCPIfName': contract_interface.name}}}
            children.append(text)
        for contract in self.get_all_provided(deleted=True):
            text = {'vzRsAnyToProv': {'attributes': {'status': 'deleted', 'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract in self.get_all_consumed(deleted=True):
            text = {'vzRsAnyToCons': {'attributes': {'status': 'deleted', 'tnVzBrCPName': contract.name}}}
            children.append(text)
        for contract_interface in self.get_all_consumed_cif(deleted=True):
            text = {'vzRsAnyToConsIf': {'attributes': {'status': 'deleted', 'tnVzCPIfName': contract_interface.name}}}
            children.append(text)
        return children

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/ctx-%s/any.json?subscription=yes' % (self._parent._parent.name, self._parent.name)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/any', '/']


class OutsideL2EPG(CommonEPG):
    """
    OutsideL2EPG class, roughly equivalent to l2ext:InstP
    """
    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['l2extInstP']

    def get_json(self):
        """
        Returns json representation of the EPG

        :returns: json dictionary of the EPG
        """
        children = super(OutsideL2EPG, self)._get_common_json()
        attr = self._generate_attributes()
        return super(OutsideL2EPG, self).get_json(self._get_apic_classes()[0],
                                                  attributes=attr,
                                                  children=children)

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return OutsideL2

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/instP-', '/']

    def _extract_relationships(self, data, obj_dict):
        super(OutsideL2EPG, self)._extract_relationships(data, obj_dict, epg_type='l2')


class OutsideL3(BaseACIObject):
    """Represents the L3Out for external connectivity
    """

    def __init__(self, l3out_name, parent=None):
        """
        :param l3out_name: String containing the name of this OutsideL3
        :param parent: Instance of the Tenant class representing\
                       the tenant owning this OutsideL3.
        """
        self.context_name = None
        self.networks = []

        if not isinstance(parent, Tenant):
            raise TypeError('Parent is not set to Tenant')
        super(OutsideL3, self).__init__(l3out_name, parent)

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

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
                        OutsideL3.
        """
        assert isinstance(context, Context)
        if self.has_context():
            self.remove_context()
        self.context_name = context.name
        self._add_relation(context)

    def get_context(self):
        """
        Return the assigned context

        :returns: Instance of Context class that this OutsideL3 is assigned.
                  If no Context is assigned, None is returned.
        """
        return self._get_any_relation(Context)

    def remove_context(self):
        """
        Remove the context from the EPG

        """
        self._remove_all_relation(Context)

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary
        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'l3extInstP': OutsideEPG}

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['l3extOut']

    def _extract_relationships(self, data, obj_dict):
        tenant = self.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                tenant_children = tenant_data['fvTenant']['children']
        for child in tenant_children:
            if 'l3extOut' in child:
                outside_l3_name = child['l3extOut']['attributes']['name']
                if outside_l3_name == self.name:
                    outside_children = child['l3extOut']['children']
                    for outside_child in outside_children:
                        if 'l3extRsEctx' in outside_child:
                            context_name = outside_child['l3extRsEctx']['attributes']['tnFvCtxName']
                            # tenant = self.get_parent()
                            # context_search = Search()
                            # context_search.name = context_name
                            # objs = tenant.find(context_search)
                            # for context in objs:
                            #     if isinstance(context, Context):
                            #         self.add_context(context)

                            if Context in obj_dict:
                                all_contexts = obj_dict[Context]
                                if len(all_contexts):
                                    for context in all_contexts:
                                        if context.name == context_name and context.get_parent() == tenant:
                                            self.add_context(context)
                    break
        super(OutsideL3, self)._extract_relationships(data, obj_dict)

    # L3 External Domain
    def add_l3extdom(self, extdom):
        """
        Set the L3ExternalDomain for this BD

        :param extdom:
        """
        if not isinstance(extdom, L3ExtDomain):
            raise TypeError('add_extdom not called with L3ExtDom')
        self._add_relation(extdom)

    def has_l3extdom(self):
        """
        :return: Boolean indicating presence of L3 External Domain Attachment
        """
        return len(self._get_all_relation(L3ExtDomain)) > 0

    def get_json(self):
        """
        Returns json representation of OutsideL3

        :returns: json dictionary of OutsideL3
        """
        children = []
        if self.context_name is not None:
            context = {'l3extRsEctx': {'attributes': {'tnFvCtxName':
                                                      self.context_name}}}
            children.append(context)

        # Attach L3 External Domains if present
        if self.has_l3extdom():
            domain = {"l3extRsL3DomAtt":
                      {"attributes":
                       {"tDn": "uni/l3dom-{}".format(self._get_any_relation(L3ExtDomain))}}}
            children.append(domain)

        for interface in self.get_interfaces():
            if hasattr(interface, 'is_ospf'):
                ospf_if = interface

                text = {'ospfExtP': {'attributes': {'areaId': ospf_if.area_id,
                                                    'areaType': ospf_if.area_type},
                                     'children': []}}
                children.append(text)

            elif hasattr(interface, 'is_bgp'):
                # bgp_if = interface
                text = {"bgpExtP": {"attributes": {}}}
                children.append(text)

        for interface in self.get_interfaces():
            text = interface.get_json()
            children.append(text)
        attr = self._generate_attributes()
        return super(OutsideL3, self).get_json('l3extOut',
                                               attributes=attr,
                                               children=children)

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/out-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/out-', '/']


class OutsideL2(BaseACIObject):
    """Represents the L2Out for external connectivity
    """

    def __init__(self, l2out_name, parent=None):
        """
        :param l2out_name: String containing the name of this OutsideL2
        :param parent: Instance of the Tenant class representing\
                       the tenant owning this OutsideL2.
        """
        self.bd_name = None
        self.networks = []

        if not isinstance(parent, Tenant):
            raise TypeError('Parent is not set to Tenant')
        super(OutsideL2, self).__init__(l2out_name, parent)

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/l2out-', '/']

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary
        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'l2extInstP': OutsideL2EPG}

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['l2extOut']

    def has_bd(self):
        """
        Check if the BridgeDomain has been assigned

        :returns: True or False. True if a BridgeDomain has been assigned to this
                  L2Interface.
        """
        return self._has_any_relation(BridgeDomain)

    def add_bd(self, bd):
        """
        Add BridgeDomain to the EPG

        :param bd: Instance of BridgeDomain class to assign to this OutsideL2.
        """
        assert isinstance(bd, BridgeDomain)
        if self.has_bd():
            self.remove_bd()
        self.bd_name = bd.name
        self._add_relation(bd)

    def remove_bd(self):
        """
        Remove the BridgeDomain from the EPG
        """
        self._remove_all_relation(BridgeDomain)

    def _extract_relationships(self, data, obj_dict):
        tenant_children = None
        tenant = self.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                tenant_children = tenant_data['fvTenant']['children']
        if tenant_children is not None:
            for child in tenant_children:
                if 'l2extOut' in child:
                    outside_l2_name = child['l2extOut']['attributes']['name']
                    if outside_l2_name == self.name:
                        outside_children = child['l2extOut']['children']
                        for outside_child in outside_children:
                            if 'l2extRsEBd' in outside_child:
                                bd_name = outside_child['l2extRsEBd']['attributes']['tnFvBDName']
                                tenant = self.get_parent()
                                # bd_search = Search()
                                # bd_search.name = bd_name
                                # objs = tenant.find(bd_search)
                                # for bd in objs:
                                #     if isinstance(bd, BridgeDomain):
                                #         self.add_bd(bd)

                                if BridgeDomain in obj_dict:
                                    all_bds = obj_dict[BridgeDomain]
                                    if len(all_bds):
                                        for bd in all_bds:
                                            if bd.name == bd_name and bd.get_parent() == tenant:
                                                self.add_bd(bd)
                        break
        super(OutsideL2, self)._extract_relationships(data, obj_dict)

    # L2 External Domain
    def add_l2extdom(self, extdom):
        """
        Set the L2ExternalDomain for this BD

        :param extdom:
        """
        if not isinstance(extdom, L2ExtDomain):
            raise TypeError('add_extdom not called with L2ExtDom')
        self._add_relation(extdom)

    def has_l2extdom(self):
        """
        :return: Boolean indicating presence of L2 External Domain Attachment
        """
        return len(self._get_all_relation(L2ExtDomain)) > 0

    def get_json(self):
        """
        Returns json representation of OutsideL2

        :returns: json dictionary of OutsideL2
        """
        children = []
        if self.bd_name is not None:
            bd = {'l2extRsEctx': {'attributes': {'tnFvBDName':
                                                 self.bd_name}}}
            children.append(bd)

        # Attach L2 External Domains if present
        if self.has_l2extdom():
            domain = {"l2extRsL2DomAtt":
                      {"attributes":
                       {"tDn": "uni/l2dom-{}".format(self._get_any_relation(L2ExtDomain))}}}
            children.append(domain)

        for interface in self.get_interfaces():
            text = interface.get_json()
            children.append(text)
        attr = self._generate_attributes()
        return super(OutsideL2, self).get_json('l2extOut',
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
        self._mtu = 'inherit'
        self.networks = []

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

    def get_mtu(self):
        """
        Get the MTU of this interface

        :returns: MTU of the interface
        """
        return self._mtu

    def set_mtu(self, mtu):
        """
        Set the L3 MTU of this interface

        :param mtu: String containing MTU

        """
        self._mtu = mtu

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
        assert isinstance(context, Context)
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
        if self.get_addr() is None:
            return None
        text = {'l3extRsPathL3OutAtt': {'attributes': {'encap': '%s-%s' % (self.get_interfaces()[0].encap_type,
                                                                           self.get_interfaces()[0].encap_id),
                                                       'ifInstT': self.get_l3if_type(),
                                                       'addr': self.get_addr(),
                                                       'mtu': self.get_mtu(),
                                                       'tDn': self.get_interfaces()[0]._get_path()},
                                        'children': []}}
        return text

    def get_attributes(self, name=None):
        result = super(L3Interface, self).get_attributes(name)
        result['addr'] = self.get_addr()
        result['mtu'] = self.get_mtu()
        return result


class OSPFInterfacePolicy(BaseACIObject):
    """
    Represents the interface settings of an OSPF interface
    """

    def __init__(self, name, parent=None):
        """
        param name: String containing the name of this OSPF interface policy
        param parent: Instance of the Tenant class representing the tenant\
                      owning this OSPF interface policy
        """

        self.name = name
        self.parent = parent

        # Initialize default values
        self.network_type = 'bcast'
        self.cost = None
        self.priority = None
        self.hello_interval = None
        self.dead_interval = None
        self.retrans_interval = None
        self.transmit_delay = None

        if not isinstance(parent, Tenant):
            raise TypeError('Parent is not set to Tenant')
        super(OSPFInterfacePolicy, self).__init__(name, parent)

    def _generate_attributes(self):
        """Gets the attributes used in generating the JSON for the object
        """
        attributes = dict()
        attributes['name'] = self.name
        if self.descr:
            attributes['descr'] = self.descr
        if self.network_type:
            attributes['nwT'] = self.network_type
        if self.cost:
            attributes['cost'] = self.cost
        if self.priority:
            attributes['priority'] = self.priority
        if self.hello_interval:
            attributes['helloIntvl'] = self.hello_interval
        if self.dead_interval:
            attributes['deadIntvl'] = self.dead_interval
        if self.retrans_interval:
            attributes['rexmitIntvl'] = self.retrans_interval
        if self.transmit_delay:
            attributes['xmitDelay'] = self.transmit_delay
        return attributes

    def get_nw_type(self):
        """
        Get the nw-type of this interface ospf policy
        :returns: string of the network type for this policy
        """
        return self.network_type

    def set_nw_type(self, network_type):
        """
        sets the L3 nw_type with some validation

        :param network_type: string of bcast or p2p

        """
        valid_types = ['bcast', 'p2p']
        if network_type not in valid_types:
            raise ValueError('Invalid Network Type - %s' % network_type)
        else:
            self.network_type = network_type

    def get_json(self):
        """
        Returns json representation of OSPFRouter

        :returns: json dictionary of OSPFIRouter
        """
        attr = self._generate_attributes()
        text = {"ospfIfPol": {"attributes": attr}}
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
        self._pod = '1'

    def set_router_id(self, rid):
        """
        Sets the router id of the object

        :param rid: String containing the router id

        """
        self._router_id = rid

    def get_router_id(self):
        """
        :returns string containing the Router ID
        """
        return self._router_id

    def set_node_id(self, node):
        """
        Sets the router id of the object

        :param node: String containing the node id

        """
        self._node = node

    def get_node_id(self):
        """
        :returns string containing the Node ID
        """
        return self._node

    def get_json(self):
        """
        Returns json representation of OSPFRouter

        :returns: json dictionary of OSPFIRouter
        """
        dn_name = "topology/pod-%s/node-%s" % (self._pod, self._node)
        text = {"l3extRsNodeL3OutAtt": {"attributes": {"rtrId": self._router_id,
                                                       "tDn": dn_name}}}
        return text


class OSPFInterface(BaseACIObject):
    """
    Creates an OSPF router interface that can be attached to a L3 interface.
    This interface defines the OSPF area, authentication, etc.
    """

    def __init__(self, name, router=None, area_id=None):
        """
        :param name:  String containing the name of this OSPFInterface object.
        :param area_id: String containing the OSPF area id of this interface.\
                        Default is None.
        """
        super(OSPFInterface, self).__init__(name)
        self.area_id = area_id
        self.router = router
        self.int_policy_name = None
        self.auth_key = None
        self.auth_type = None
        self.auth_keyid = None
        self.networks = []
        self.area_type = 'nssa'

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

    def set_area_type(self, area_type):
        """
        Set the area_type for this OSPFInterface

        :param area_type: AreaType to use for this OSPFInterface
        """
        valid_area_types = ('nssa', 'stub', 'regular')
        if area_type not in valid_area_types:
            raise ValueError('area_type must be of: %s, %s or %s' % valid_area_types)
        self.area_type = area_type

    def get_json(self):
        """
        Returns json representation of OSPFInterface
        :returns: json dictionary of OSPFInterface
        """
        children = []
        if self.int_policy_name:
            policy = {'ospfRsIfPol': {'attributes': {'tnOspfIfPolName': self.int_policy_name}}}
            children.append(policy)

        text = {'ospfIfP': {'attributes': {'name': self.name},
                            'children': children}}
        if self.auth_key:
            text['ospfIfP']['attributes']['authKey'] = self.auth_key
            text['ospfIfP']['attributes']['authKeyId'] = self.auth_keyid
            text['ospfIfP']['attributes']['authType'] = self.auth_type

        text = [text, self.get_interfaces()[0].get_json()]
        text = {'l3extLIfP': {'attributes': {'name': self.name},
                              'children': text}, }
        text = {'l3extLNodeP': {'attributes': {'name': self.name},
                                'children': [text, self.router.get_json()]}}
        return text


class BGPSession(BaseACIObject):
    """
    Creates an BGP router interface that can be attached to a L3 interface.
    This interface defines the BGP AS, authentication, etc.
    """

    def __init__(self, name, router_id=None, peer_ip=None, node_id=None):
        """
        :param name:  String containing the name of this BGPSession object.
        :param router_id: String containing the IPv4 router-id
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
        :returns: True if this interface is an BGP interface.  In the case\
                  of BGPSession instances, this is always True.
        """
        return True

    def get_json(self):
        """
        Returns json representation of BGPSession

        :returns: json dictionary of BGP Session
        """

        # bgpextp = {'bgpExtP': {'attributes': {}}}
        bgpPeerP = {'bgpPeerP': {'attributes': {'addr': self.peer_ip,
                                                'ctrl': self.options,
                                                'descr': '',
                                                'name': '', }}}

        RsNode = {"l3extRsNodeL3OutAtt": {"attributes": {"rtrId": self.router_id,
                                                         "tDn": "topology/pod-1/node-%s" % self.node_id}}},
        text = [self.get_interfaces()[0].get_json()]
        text = {'l3extLIfP': {'attributes': {'name': self.name},
                              'children': text}}

        text = {'l3extLNodeP': {'attributes': {'name': self.name},
                                'children': [RsNode, bgpPeerP, text]}}

        return text


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
        self.unknown_mac_unicast = 'proxy'
        self.unknown_multicast = 'flood'
        self.arp_flood = 'no'
        self.unicast_route = 'yes'
        self.multidestination = 'bd-flood'
        self.mac = None

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvBD']

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'fvSubnet': Subnet, }

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/BD-', '/']

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/BD-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    def set_unknown_mac_unicast(self, unicast):
        """
        Set the unknown mac unicast for this BD

        :param unicast: Unicast to assign this BridgeDomain
        """
        valid_unicast = ('proxy', 'flood')
        if unicast not in valid_unicast:
            raise ValueError('unknown MAC unicast must be of: %s or %s' % valid_unicast)
        self.unknown_mac_unicast = unicast

    def get_unknown_mac_unicast(self):
        """
        Gets the unknown mac unicast for this BD

        :returns: unknown mac unicast of the BridgeDomain
        """
        return self.unknown_mac_unicast

    def set_mac(self, mac):
        """
        Set the mac address for the BD

        :param mac: string mac address (XX:XX:XX:XX:XX:XX)
        """

        self.mac = mac

    def get_mac(self):
        """
        Get the mac address for the BD

        :returns: string containing the mac address of the BD (e.g. 00:22:BD:F8:19:FF)
        """

        return self.mac

    def set_unknown_multicast(self, multicast):
        """
        Set the unknown multicast for this BD

        :param multicast: Multicast to assign this BridgeDomain
        """
        valid_multicast = ('flood', 'opt-flood')
        if multicast not in valid_multicast:
            raise ValueError('unknown multicast must be of: %s or %s' % valid_multicast)
        self.unknown_multicast = multicast

    def get_unknown_multicast(self):
        """
        Gets the unknown multicast for this BD

        :returns: unknown multicast of the BridgeDomain
        """
        return self.unknown_multicast

    def set_arp_flood(self, arp_value):
        """
        Set the ARP flood for this BD

        :param arp_value: arp to assign this BridgeDomain
        """
        valid_arp_flood = ('yes', 'no')
        if arp_value not in valid_arp_flood:
            raise ValueError('arp flood must be of: %s or %s' % valid_arp_flood)
        self.arp_flood = arp_value

    def is_arp_flood(self):
        """
        Check if ARP flooding is enabled
        """
        return self.arp_flood == 'yes'

    def get_arp_flood(self):
        """
        Get the ARP flooding policy for this BD

        :returns: a string containing the ARP flooding policy of the BridgeDomain
        """
        return self.arp_flood

    def set_unicast_route(self, route):
        """
        Set the unicast route for this BD

        :param route: route to assign this BridgeDomain
        """
        valid_unicast_route = ('yes', 'no')
        if route not in valid_unicast_route:
            raise ValueError('unicast route must be of: %s or %s' % valid_unicast_route)
        self.unicast_route = route

    def is_unicast_route(self):
        """
        Check if unicast routing is enabled
        """
        return self.unicast_route == 'yes'

    def get_unicast_route(self):
        """
        Get the Unicast Routing policy for this BD

        :returns: a string containing the unicast routing policy of the BridgeDomain
        """
        return self.unicast_route

    def set_multidestination(self, multidestination):
        """
        Set the multidestination flood policy for this BD

        :param multidestination: policy to assign this BridgeDomain
        """
        valid_multidestination = ('drop', 'bd-flood', 'encap-flood')
        if multidestination not in valid_multidestination:
            raise ValueError('multidestination must be of: %s, %s or %s' % valid_multidestination)
        self.multidestination = multidestination

    @staticmethod
    def get_from_json(self, data, parent=None):
        """
        returns a Tenant object from a json
        """
        for child in data['fvBD']['children']:
            if 'fvRsCtx' in child:
                context_name = child['fvRsCtx']['attributes']['tnFvCtxName']
                context = Context(context_name, parent=parent)
                self.add_context(context)
            elif 'fvRsBDToOut' in child:
                outside_l3_name = child['fvRsBDToOut']['attributes']['tnL3extOutName']
                outside_l3 = OutsideL3(outside_l3_name, parent=parent)
                self.add_l3out(outside_l3)
        return super(BridgeDomain, self).get_from_json(self, data, parent=parent)

    def get_json(self):
        """
        Returns json representation of the bridge domain

        :returns: json dictionary of bridge domain
        """
        children = []
        if self.has_context():
            text = {'fvRsCtx': {'attributes': {'tnFvCtxName': self.get_context().name}}}
            children.append(text)
        if self.has_l3out():
            for l3out in self.get_l3out():
                fvRsBDToOut = {"fvRsBDToOut": {"attributes": {"tnL3extOutName": l3out.name}}}
                children.append(fvRsBDToOut)
        attr = self._generate_attributes()
        attr['unkMacUcastAct'] = self.unknown_mac_unicast
        attr['unkMcastAct'] = self.unknown_multicast
        attr['arpFlood'] = self.arp_flood
        attr['unicastRoute'] = self.unicast_route
        attr['multiDstPktAct'] = self.multidestination
        if self.mac:
            attr['mac'] = self.mac
        return super(BridgeDomain, self).get_json(self._get_apic_classes()[0],
                                                  attributes=attr,
                                                  children=children)

    def _extract_relationships(self, data, obj_dict):
        tenant = self.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                tenant_children = tenant_data['fvTenant']['children']
        for child in tenant_children:
            if 'fvBD' in child:
                bd_name = child['fvBD']['attributes']['name']
                if bd_name == self.name:
                    bd_children = child['fvBD']['children']
                    for bd_child in bd_children:
                        if 'fvRsCtx' in bd_child:
                            context_name = bd_child['fvRsCtx']['attributes']['tRn'].partition('ctx-')[2]
                            # tenant = self.get_parent()
                            # context_search = Search()
                            # context_search.name = context_name
                            # objs = tenant.find(context_search)
                            # for context in objs:
                            #     if isinstance(context, Context):
                            #         self.add_context(context)

                            if Context in obj_dict:
                                all_contexts = obj_dict[Context]
                                context_found = False
                                if len(all_contexts):
                                    for context in all_contexts:
                                        if context.name == context_name and context.get_parent() == tenant:
                                            self.add_context(context)
                                            context_found = True
                                    if not context_found:
                                        for context in all_contexts:
                                            if context.name == context_name and context.get_parent().name == 'common':
                                                self.add_context(context)
                                                context_found = True
                        elif 'fvRsBDToOut' in bd_child:
                            l3_out_name = bd_child['fvRsBDToOut']['attributes']['tnL3extOutName']
                            # tenant = self.get_parent()
                            # l3_out_search = Search()
                            # l3_out_search.name = l3_out_name
                            # objs = tenant.find(l3_out_search)
                            # for l3_out in objs:
                            #     if isinstance(l3_out, OutsideL3):
                            #         self.add_l3out(l3_out)

                            if OutsideL3 in obj_dict:
                                all_l3out = obj_dict[OutsideL3]
                                if len(all_l3out):
                                    for l3_out in all_l3out:
                                        if l3_out.name == l3_out_name and l3_out.get_parent() == tenant:
                                            self.add_l3out(l3_out)
                    break
        super(BridgeDomain, self)._extract_relationships(data, obj_dict)

    # Context references
    def add_context(self, context):
        """
        Set the Context for this BD

        :param context: Context to assign this BridgeDomain
        """
        assert isinstance(context, Context)
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

    # L3 Outs
    def add_l3out(self, l3out):
        """
        Set the L3Out for this BD

        :param l3out: OutsideL3 to assign this BridgeDomain

        """
        if not isinstance(l3out, OutsideL3):
            raise TypeError('add_l3out not called with OutsideL3')
        self._add_relation(l3out)

    def has_l3out(self):
        """
        Check if this BD has an OutsideL3
        :return: True if the BD has an OutsideL3 configured. False, otherwise.
        """
        return len(self._get_all_relation(OutsideL3)) > 0

    def get_l3out(self):
        """
        :returns: List of OutsideL3 objects
        """
        return self._get_all_relation(OutsideL3)

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

        :param subnet:
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

    def _populate_from_attributes(self, attributes):
        """
        Populates various attributes
        :param attributes:
        :return:
        """
        super(BridgeDomain, self)._populate_from_attributes(attributes)
        self.class_id = attributes.get('pcTag')
        self.scope = attributes.get('scope')
        self.vnid = attributes.get('seg')
        self.mtu = attributes.get('mtu')
        self.mac = attributes.get('mac')
        self.arp_flood = attributes.get('arpFlood')
        self.unicast_route = attributes.get('unicastRoute')
        self.unknown_mac_unicast = attributes.get('unkMacUcastAct')
        self.unknown_multicast = attributes.get('unkMcastAct')
        self.multidestination = attributes.get('multiDstPktAct')
        self.modified_time = attributes.get('modTs')

    @staticmethod
    def get_table(bridge_domains, title=''):
        """
        Will create table of context information

        :param title:
        :param bridge_domains:
        """

        headers = ['Tenant',
                   'Context',
                   'Bridge Domain',
                   'Subnets',
                   'MAC',
                   'Route',
                   'Unknown UCST',
                   'Unknown MCST',
                   'VNID',
                   'Scope',
                   'Class ID',
                   'MTU',
                   ]
        data = []
        for bridge_domain in sorted(bridge_domains):
            context = 'Unset'
            if bridge_domain.has_context():
                context = bridge_domain.get_context().name

            subnets = bridge_domain.get_subnets()
            subnet_str = []
            for subnet in subnets:
                subnet_str.append(subnet.get_addr())

            data.append([
                bridge_domain.get_parent().name,
                context,
                bridge_domain.name,
                ', '.join(subnet_str),
                bridge_domain.mac,
                bridge_domain.unicast_route,
                bridge_domain.unknown_mac_unicast,
                bridge_domain.unknown_multicast,
                bridge_domain.vnid,
                bridge_domain.scope,
                bridge_domain.class_id,
                bridge_domain.mtu
            ])

        data = sorted(data)
        table = Table(data, headers, title=title + 'Bridge Domains')
        return [table, ]


class BaseSubnet(BaseACIObject):
    """
    Base class for Subnet and OutsideNetwork
    """

    def __init__(self, name, parent=None, address=None):
        """
        :param name: String containing the name of this instance.
        :param parent: An instance of the parent class.
        :param address: String containing the IP address. Can optionally be set later.
        """
        self._addr = address
        super(BaseSubnet, self).__init__(name, parent)
        self._scope = None

    @property
    def ip(self):
        """
        IP address of the subnet in the form of Address/mask e.g. 10.1.1.1/16

        :return: String containing the IP address
        """
        return self.get_addr()

    @ip.setter
    def ip(self, x):
        """
        Set the IP address of the subnet
        :param x: String containing the IP address of the subnet
        :return: None
        """
        self.set_addr(x)

    def get_addr(self):
        """
        Get the subnet address

        :returns: The subnet address as a string in the form of <ipaddr>/<mask>
        """
        return self._addr

    def set_addr(self, addr):
        """
        Set the subnet address

        :param addr: The subnet default gateway address as a string in the form\
                     of <ipaddr>/<mask>
        """
        if addr is None:
            raise TypeError('Address can not be set to None')
        self._addr = addr

    def get_scope(self):
        """
        Get the subnet scope

        :returns: The subnet scope as a string
        """
        return self._scope

    def set_scope(self, scope):
        """
        Set the subnet scope

        :param scope: String containing the subnet scope
        :return: None
        """
        raise NotImplementedError

    def _populate_from_attributes(self, attributes):
        """
        Sets the attributes when creating objects from the APIC.
        Called from the base object when calling the classmethod get()
        """
        super(BaseSubnet, self)._populate_from_attributes(attributes)
        if 'ip' in attributes:
            self.set_addr(str(attributes.get('ip')))
        if 'scope' in attributes:
            self.set_scope(str(attributes.get('scope')))

    @property
    def addr(self):
        """
        Subnet address

        :return: String containing the subnet default gateway IP address and mask e.g. "1.2.3.4/24"
        """
        return self._addr

    @addr.setter
    def addr(self, subnet_address):
        """
        Subnet address

        :param subnet_address: String containing the subnet default gateway IP address and mask e.g. "1.2.3.4/24"
        """
        self.set_addr(subnet_address)

    def get_attributes(self, name=None):

        result = super(BaseSubnet, self).get_attributes(name)
        if self.get_addr() is not None:
            result['addr'] = self.get_addr()
        if self.get_scope() is not None:
            result['scope'] = self.get_scope()
        return result

    def __eq__(self, other):
        # Neither object has "addr" attribute - use the parent class
        if not hasattr(self, 'addr') and not hasattr(other, 'addr'):
            return super(Subnet, self).__eq__(other)

        if not hasattr(self, 'addr') or not hasattr(other, 'addr'):
            return False

        return super(BaseSubnet, self).__eq__(other) and self._addr == other._addr

    def __hash__(self):
        return BaseACIObject.__hash__(self)


class Subnet(BaseSubnet):
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

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return BridgeDomain

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvSubnet']

    def set_scope(self, scope):
        """
        Set the subnet scope

        :param scope: The scope of the subnet. Use "public" when the subnet
        needs to be advertised externally, "private" when no external routing
        for the subnet is required (only internal), and "shared" when a route
        for the subnet needs to be leaked to a different VRF within the fabric.
        Note that "public" and "private" are mutually exclusive, but "shared"
        can be appended to any of them ("e.g. set_scope("public,shared")).
        """
        valid_scopes = ["public", "private", "shared", "public,shared",
                        "private,shared", "shared,public", "shared,private"]
        if scope is None:
            raise TypeError('Scope can not be set to None')
        elif len(scope) == 0:
            self._scope = "private"
        elif scope.lower() not in valid_scopes:
            raise ValueError('Invalid value for scope. It must be one of "%s".'
                             % '", "'.join(valid_scopes[:5]))
        self._scope = scope.lower()

    def get_json(self):
        """
        Returns json representation of the subnet

        :returns: json dictionary of subnet
        """
        attributes = self._generate_attributes()
        if self.get_addr() is None:
            raise ValueError('Subnet address is not set')
        attributes['ip'] = self.get_addr()
        if self.get_scope() is not None:
            attributes['scope'] = self.get_scope()
        return super(Subnet, self).get_json('fvSubnet', attributes=attributes)

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

    def get_attributes(self, name=None):

        result = super(Subnet, self).get_attributes(name)
        result['addr'] = self.get_addr()
        result['scope'] = self.get_scope()
        return result

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/BD-%s/subnet-[%s].json?subscription=yes' % (
            self._parent._parent.name, self._parent.name, self.ip)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/subnet-[', '/']

    @classmethod
    def get_event(cls, session):
        """
        Gets the event that is pending for this class.  Events are
        returned in the form of objects.  Objects that have been deleted
        are marked as such.

        :param session:  the instance of Session used for APIC communication
        """
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
            if "/BD-" not in cls._get_parent_dn(dn):
                return
            parent = cls._get_parent_from_dn(cls._get_parent_dn(dn))
            if status == 'created':
                name = str(attributes['name'])
            else:
                name = cls._get_name_from_dn(dn)
            obj = cls(name, parent=parent)
            obj._populate_from_attributes(attributes)
            if status == 'deleted':
                obj.mark_as_deleted()
            return obj


class OutsideNetwork(BaseSubnet):
    """
    OutsideNetwork class, roughly equivalent to l3extSubnet in the APIC model
    """

    def __init__(self, name, parent, address=None):
        """
        :param name: String containing the OutsideNetwork name
        :param parent: An instance of OutsideEPG class
        :param address: String containing the IP address of the OutsideNetwork. e.g. '1.2.3.0/24'
        """
        if address:
            self.addr = address
        super(OutsideNetwork, self).__init__(name, parent, address=address)

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return OutsideEPG

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/extsubnet-[', '/']

    def _generate_attributes(self):
        attributes = super(OutsideNetwork, self)._generate_attributes()
        if self.get_addr() is None:
            raise ValueError('OutsideNetwork ip is not set')
        attributes['ip'] = self.get_addr()
        if self._scope:
            attributes['scope'] = self._scope
        return attributes

    def set_scope(self, scope):
        """
        Set the subnet scope

        :param scope: String containing the scope
        """
        valid_scopes = ["import-rtctrl", "export-rtctrl", "import-security", "shared-security",
                        "shared-rtctrl"]
        if scope is None:
            raise TypeError('Scope can not be set to None')
        scope = scope.replace(' ', '')
        for sub_scope in scope.lower().split(','):
            if sub_scope not in valid_scopes:
                raise ValueError('Invalid value for scope. It must be one of "%s".'
                                 % '", "'.join(valid_scopes))
        self._scope = scope.lower()

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['l3extSubnet']

    def get_json(self):
        """
        Returns json representation of the OutsideNetwork object.

        :returns: json dictionary of OutsideNetwork
        """
        attr = self._generate_attributes()
        return super(OutsideNetwork, self).get_json(self._get_apic_classes()[0],
                                                    attributes=attr)


class Context(BaseACIObject):
    """ Context :  roughly equivalent to fvCtx """

    def __init__(self, context_name, parent=None):
        """
        :param context_name: String containing the Context name
        :param parent: An instance of Tenant class representing the Tenant\
                       which contains this Context.

        """
        super(Context, self).__init__(context_name, parent)
        self.allow_all = False

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvCtx']

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'vzAny': AnyEPG}

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/ctx-', '/']

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/ctx-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    @staticmethod
    def _get_tenant_from_dn(dn):
        """
        Get the tenant name from the DN

        :param dn: String containing the DN
        :return: string containing the tenant name
        """
        return dn.split('/tn-')[1].split('/')[0]

    def _populate_from_attributes(self, attributes):
        """
        Sets the attributes when creating objects from the APIC.
        Called from the base object when calling the classmethod get()
        """
        super(Context, self)._populate_from_attributes(attributes)
        dn = attributes.get('dn')
        if 'knwMcastAct' in attributes:
            self.known_mcast = str(attributes.get('knwMcastAct'))
        if 'modTs' in attributes:
            self.modified_time = str(attributes.get('modTs'))
        if 'name' in attributes:
            self.name = str(attributes.get('name'))
        elif self.dn != '':
            self.name = self._get_name_from_dn(self.dn)
        if 'pcTag' in attributes:
            self.class_id = str(attributes.get('pcTag'))
        if 'scope' in attributes:
            self.scope = str(attributes.get('scope'))
        if 'seg' in attributes:
            self.vnid = str(attributes.get('seg'))
        if dn is not None:
            self.tenant = str(self._get_tenant_from_dn(dn))
        else:
            self.tenant = None
        if attributes.get('pcEnfPref') == 'unenforced':
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
        self.allow_all = value

    def get_allow_all(self):
        """
        Returns the allow_all value from this Context. When set, contracts\
        will not be enforced in this context.

        :returns:  True or False.
        """
        return self.allow_all

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
    def get(cls, session, tenant=None):
        """
        Gets all of the Contexts from the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant used to limit the Contexts\
                       retreived from the APIC
        :returns: List of Context objects
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 tenant, tenant)

    @staticmethod
    def get_table(contexts, title=''):
        """
        Will create table of context information

        :param title:
        :param contexts:
        """

        headers = ['Tenant',
                   'Context',
                   'VNID', 'Scope', 'Class ID',
                   'Allow All',
                   'Known MCST', 'Modified Time',
                   ]
        data = []
        for context in sorted(contexts):
            data.append([
                context.get_parent().name,
                context.name,
                context.vnid,
                context.scope,
                context.class_id,
                context.allow_all,
                context.known_mcast,
                context.modified_time
            ])

        data = sorted(data)
        table = Table(data, headers, title=title + 'Context')
        return [table, ]


class ContractInterface(BaseACIObject):
    """ ContractInterface :  roughly equivalent to vzCPIf """

    def __init__(self, contractif_name, parent=None):
        """
        :param contractif_name: String containing the ContractInterface name
        :param parent: An instance of Tenant class representing the Tenant\
                       which contains this ContractInterface.

        """
        super(ContractInterface, self).__init__(contractif_name, parent)
        self.allow_all = False

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['vzCPIf']

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

    def _extract_relationships(self, data, obj_dict):
        consumer_tenant = self.get_parent()

        # Find the ContractInterface
        imported_contract_dn = None
        consumer_tenant_data = None
        contract_if_children_data = None
        for item in data:
            if 'fvTenant' in item:
                if item['fvTenant']['attributes']['name'] == consumer_tenant.name:
                    consumer_tenant_data = item
        if consumer_tenant_data is None:
            return
        children = consumer_tenant_data['fvTenant']['children']
        for child in children:
            if 'vzCPIf' in child and child['vzCPIf']['attributes']['name'] == self.name:
                if 'children' in child['vzCPIf']:
                    contract_if_children_data = child['vzCPIf']['children']
                break
        if contract_if_children_data is None:
            return

        # Find the import contract relation
        for child in contract_if_children_data:
            if 'vzRsIf' in child:
                imported_contract_dn = child['vzRsIf']['attributes']['tDn']
        if imported_contract_dn is None:
            return

        # Look if there is already a Tenant
        imported_tenant_name = imported_contract_dn.partition('/tn-')[-1].partition('/')[0]
        imported_contract_name = imported_contract_dn.partition('/brc-')[-1].partition('/')[0]
        provider_tenant = None
        if consumer_tenant.has_parent():
            for child in consumer_tenant.get_parent().get_children():
                if isinstance(child, Tenant) and child.name == imported_tenant_name:
                    provider_tenant = child
                    break

        # Find the contract
        if provider_tenant is not None:
            for contract in provider_tenant.get_children(only_class=Contract):
                if contract.name == imported_contract_name:
                    self.import_contract(contract)

        super(ContractInterface, self)._extract_relationships(data, obj_dict)

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/cif-', '/']

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/cif-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    @staticmethod
    def _get_tenant_from_dn(dn):
        """
        Get the tenant name from the DN

        :param dn: String containing the DN
        :return: string containing the tenant name
        """
        return dn.split('/tn-')[1].split('/')[0]

    def _populate_from_attributes(self, attributes):
        """
        Sets the attributes when creating objects from the APIC.
        Called from the base object when calling the classmethod get()
        """
        super(ContractInterface, self)._populate_from_attributes(attributes)
        dn = attributes.get('dn')
        if dn is not None:
            self.tenant = self._get_tenant_from_dn(dn)
        else:
            self.tenant = None
        self.modified_time = attributes.get('modTs')
        self.name = attributes.get('name')
        if self.name is None and self.dn != '':
            self.name = self._get_name_from_dn(self.dn)

    def import_contract(self, contract):
        """
        Set the Contract that is imported by this ContractInterface

        :param contract: Instance of Contract
        :return: None
        """
        if self.does_import_contract(contract):
            return
        if self.has_import_contract():
            old_contracts = self._get_all_relation(Contract, 'imported')
            for old_contract in old_contracts:
                self._remove_relation(old_contract, 'imported')
        self._add_relation(contract, 'imported')

    def does_import_contract(self, contract):
        """
        Check if this ContractInterface imports a specific Contract.

        :param contract: Instance of Contract class to check if it is\
                         imported by this ContractInterface.
        :returns: True or False.  True if the ContractInterface does import the Contract.
        """
        return self._has_relation(contract, 'imported')

    def has_import_contract(self):
        """
        Check if the ContractInterface has any imported Contract
        :return: True or False. True if the ContractInterface does import a Contract.
        """
        return len(self._get_all_relation(Contract, 'imported')) > 0

    def get_import_contract(self, deleted=False):
        """
        Get the specific Contract that this ContractInterface is importing.

        :param contract: Instance of Contract class that is
                         imported by this ContractInterface.
        :returns: Contract class instance or None if not importing a contract
        """
        if not self.has_import_contract():
            return None
        if deleted:
            return self._get_all_detached_relation(Contract, 'imported')[0]
        else:
            return self._get_all_relation(Contract, 'imported')[0]

    def _generate_children(self):
        """
        Internal function to generate the children. Called from get_json()
        :return: List of JSON disctionaries containing the children of this object
        """
        children = []
        for contract in self._get_all_relation(Contract, 'imported'):
            text = {'vzRsIf': {'attributes': {'tDn': 'uni/tn-%s/brc-%s' % (contract.get_parent().name,
                                                                           contract.name)}}}
            children.append(text)
        return children

    def get_json(self):
        """
        Returns json representation of vzCPIf object

        :returns: json dictionary of vzCPIf object
        """
        attributes = self._generate_attributes()
        children = self._generate_children()
        return super(ContractInterface, self).get_json(self._get_apic_classes()[0],
                                                       attributes=attributes,
                                                       children=children)

    @classmethod
    def get(cls, session, tenant=None):
        """
        Gets all of the ContractInterfaces from the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant used to limit the ContractInterfaces\
                       retrieved from the APIC
        :returns: List of ContractInterface objects
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 tenant, tenant)


class BaseContract(BaseACIObject):
    """ BaseContract :  Base class for Contracts and Taboos """

    def __init__(self, contract_name, parent=None):
        super(BaseContract, self).__init__(contract_name, parent)
        self._scope = 'context'

    def _populate_from_attributes(self, attributes):
        super(BaseContract, self)._populate_from_attributes(attributes)
        if 'scope' in attributes:
            self.set_scope(str(attributes['scope']))

    @staticmethod
    def _get_contract_code():
        """
        Returns the APIC class name for this contract.
        Meant to be overridden by inheriting classes.
        """
        raise NotImplementedError

    @staticmethod
    def _get_subject_code():
        """
        Get the subject code

        :return: None
        """
        raise NotImplementedError

    @staticmethod
    def _get_subject_relation_code():
        """
        Get the subject relation code

        :return: None
        """
        raise NotImplementedError

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return [cls._get_contract_code()]

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

    @classmethod
    def mask_class_from_graphs(cls):
        # Returns True if called for BaseContract
        return cls.__name__ == 'BaseContract'

    def set_scope(self, scope):
        """
        Set the scope of this contract.
        Valid values are 'context', 'global', 'tenant', and 'application-profile'

        :param scope: String containing one of the following 'context', 'global',
                      'tenant', or 'application-profile'
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
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {}

    def get_json(self):
        """
        Returns json representation of the contract

        :returns: json dictionary of the contract
        """
        resp_json = []
        attributes = self._generate_attributes()

        contract_code = self._get_contract_code()
        contract = super(BaseContract, self).get_json(contract_code,
                                                      attributes=attributes,
                                                      get_children=False)
        # Create a subject for every entry with a relation to the filter
        subjects = []
        for entry in self.get_children():
            if isinstance(entry, ContractSubject):
                subject = entry.get_json()
                subjects.append(subject)
        contract[self._get_contract_code()]['children'] = subjects
        resp_json.append(contract)
        return resp_json

    def get_attributes(self, name=None):

        result = super(BaseContract, self).get_attributes(name)
        result['scope'] = self.get_scope()
        return result

    def get_all_filter_entries(self, direction='bidirectional-only'):
        """
        Get all of the filter entries contained within this Contract/Taboo

        :param direction: String containing the type of filter entries to gather
                          Valid values are 'bidirectional-only', 'input-only', 'output-only', 'all'
                          Default is 'bidirectional-only'
        :return: List of FilterEntry instances
        """
        assert direction in ['bidirectional-only', 'all', 'input-only', 'output-only']
        entries = []
        if direction == 'bidirectional-only' or direction == 'all':
            for entry in self.get_children(only_class=FilterEntry):
                entries.append(entry)
        for subject in self.get_children(only_class=ContractSubject):
            if direction == 'bidirectional-only' or direction == 'all':
                for subj_filter in subject.get_children(only_class=Filter):
                    for entry in subj_filter.get_children(only_class=FilterEntry):
                        entries.append(entry)
                for subj_filter in subject.get_filters():
                    for entry in subj_filter.get_children(only_class=FilterEntry):
                        entries.append(entry)
            if direction == 'input-only' or direction == 'all':
                for input_terminal in subject.get_children(only_class=InputTerminal):
                    for subj_filter in input_terminal.get_filters():
                        for entry in subj_filter.get_children(only_class=FilterEntry):
                            entries.append(entry)
            if direction == 'output-only' or direction == 'all':
                for output_terminal in subject.get_children(only_class=OutputTerminal):
                    for subj_filter in output_terminal.get_filters():
                        for entry in subj_filter.get_children(only_class=FilterEntry):
                            entries.append(entry)
        return entries


class Contract(BaseContract):
    """ Contract :  Class for Contracts """

    def __init__(self, contract_name, parent=None):
        super(Contract, self).__init__(contract_name, parent)

    @staticmethod
    def _get_contract_code():
        """
        Returns the APIC class name for this type of contract.

        :returns: String containing APIC class name for this type of contract.
        """
        return 'vzBrCP'

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/brc-', '/']

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/brc-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    @classmethod
    def _get_name_from_dn(cls, dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name or None if not present
        """
        if '/brc-' in dn:
            name = dn.split('/brc-')[1].split('/')[0]
        elif '/oobbrc-' in dn:
            name = dn.split('/oobbrc-')[1].split('/')[0]
        else:
            name = None
        return name

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Tenant

    def _generate_attributes(self):
        attributes = super(Contract, self)._generate_attributes()
        attributes['scope'] = self.get_scope()
        return attributes

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary
        These are the children objects

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'vzSubj': ContractSubject, }

    # @classmethod
    # def get_deep(cls, full_data, working_data, parent=None, limit_to=(), subtree='full', config_only=False):
    #     contract_data = working_data[0]['vzBrCP']
    #     contract = Contract(str(contract_data['attributes']['name']),
    #                         parent)
    #     contract._populate_from_attributes(contract_data['attributes'])
    #     for child in contract_data.get('children', ()):
    #         if 'vzSubj' in child:
    #             # subject = child['vzSubj']
    #             subj = ContractSubject(child['vzSubj']['attributes']['name'], contract)
    #             subj._populate_from_attributes(child['vzSubj']['attributes'])

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Contracts from the APIC for a particular tenant.

        :param tenant:
        :param session:
        """
        return BaseACIObject.get(session, cls, cls._get_contract_code(),
                                 tenant, tenant)

    @staticmethod
    def get_table(contracts, title=''):
        """
        Will create of each contract

        :param title:
        :param contracts:
        """
        result = []
        headers = ['Tenant', 'Contract', 'Scope', 'Filter']
        for contract in sorted(contracts, key=attrgetter('name')):
            data = []
            for filter in contract.get_children(FilterEntry):
                data.append([
                    contract.get_parent().name,
                    contract.name,
                    contract.get_scope(),
                    filter.name,
                ])
            for subject in contract.get_children(ContractSubject):
                for subj_filter in subject.get_filters():
                    subj_filt_entries = subj_filter.get_children(only_class=FilterEntry)
                    for subj_filt_entry in subj_filt_entries:
                        entry = [
                            contract.get_parent().name,
                            contract.name,
                            contract.get_scope(),
                            subj_filt_entry.name,
                        ]
                        if entry not in data:
                            data.append(entry)
            result.append(Table(data, headers, title=title + 'Contract:{0}'.format(contract.name)))
        return result

    def _get_all_epgs(self, relation_type, deleted=False):
        """
        Internal function used by get_all_providing_epgs and get_all_consuming_epgs

        :param relation_type: String containing either 'provided' or 'consumed'
        :param deleted: Boolean indicating whether to get EPGs that are providing/consuming
                        or that the providing/consuming relationship was marked as deleted
        :return: List of EPG instances
        """
        assert relation_type in ['provided', 'consumed']
        resp = []
        if deleted:
            status = 'detached'
        else:
            status = 'attached'
        for epg_class in [EPG, AnyEPG, OutsideEPG]:
            for epg in self.get_all_attachments(epg_class, status=status, relation_type=relation_type):
                resp.append(epg)
        return resp

    def get_all_providing_epgs(self, deleted=False):
        """
        Get all of the EPGs providing this contract

        :param deleted: Boolean indicating whether to get EPGs that are providing
                        or that the providing relationship was marked as deleted
        :return: List of EPG instances
        """
        return self._get_all_epgs('provided', deleted)

    def get_all_consuming_epgs(self, deleted=False):
        """
        Get all of the EPGs consuming this contract

        :param deleted: Boolean indicating whether to get EPGs that are consuming
                        or that the consuming relationship was marked as deleted
        :return: List of EPG instances
        """
        return self._get_all_epgs('consumed', deleted)


class ContractSubject(BaseACIObject):
    """ ContractSubject : roughly equivalent to vzSubj """

    def __init__(self, subject_name, parent=None):
        super(ContractSubject, self).__init__(subject_name, parent)

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['vzSubj']

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary
        These are the children objects
        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'vzInTerm': InputTerminal,
                'vzOutTerm': OutputTerminal}

    def _extract_relationships(self, data, obj_dict):
        """
        Extracts and rebuild the relationships between the ContractSubject
        and Filter objects.
        """
        contract = self.get_parent()
        tenant = contract.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                contract_data = tenant_data['fvTenant']['children']
        if len(contract_data):
            for child in contract_data:
                if 'vzBrCP' in child and 'children' in child['vzBrCP'] and \
                                child['vzBrCP']['attributes']['name'] == contract.name:
                    for subj in child['vzBrCP']['children']:
                        try:
                            if subj['vzSubj']['attributes']['name'] == self.name:
                                for filt in subj['vzSubj']['children']:
                                    if 'vzRsSubjFiltAtt' in filt:
                                        filt_name = filt['vzRsSubjFiltAtt']['attributes']['tnVzFilterName']
                                        if Filter in obj_dict:
                                            all_filters = obj_dict[Filter]
                                            if len(all_filters):
                                                found = False
                                                for specific_filter in all_filters:
                                                    if specific_filter.name == filt_name and \
                                                            specific_filter.get_parent() == tenant:
                                                        self.add_filter(specific_filter)
                                                        found = True
                                                if not found:
                                                    for specific_filter in all_filters:
                                                        if specific_filter.name == filt_name and \
                                                                specific_filter.get_parent().name == 'common':
                                                            self.add_filter(specific_filter)
                        except KeyError:
                            pass

        super(ContractSubject, self)._extract_relationships(data, obj_dict)

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return [Contract, Taboo]

    @staticmethod
    def get_from_json(self, data, parent=None):
        """
        returns a Tenant object from a json
        """
        if 'vzSubj' in data:
            for child in data['vzSubj']['children']:
                if 'vzRsSubjFiltAtt' in child:
                    filter_name = child['vzRsSubjFiltAtt']['attributes']['tnVzFilterName']
                    filter_obj = Filter(filter_name)
                    self._add_relation(filter_obj)
        elif 'vzTSubj' in data:
            for child in data['vzTSubj']['children']:
                if 'vzRsDenyRule' in child:
                    filter_name = child['vzRsDenyRule']['attributes']['tnVzFilterName']
                    filter_obj = Filter(filter_name)
                    self._add_relation(filter_obj)
        return super(ContractSubject, self).get_from_json(self, data, parent=parent)

    def get_json(self):
        """
        Returns json representation of the ContractSubject or TabooContractSubject

        :returns: json dictionary of the ContractSubject or TabooContractSubject
        """
        subject = 'vzSubj'
        subjectFilter = 'vzRsSubjFiltAtt'
        if isinstance(self._parent, Taboo):
            subject = Taboo._get_subject_code()
            subjectFilter = Taboo._get_subject_relation_code()
        attr = self._generate_attributes()
        resp_json = super(ContractSubject, self).get_json(subject,
                                                          attributes=attr,
                                                          get_children=False)
        filters = []
        for entry in self.get_filters():
            filt = {subjectFilter: {'attributes': {'tnVzFilterName': entry.name}}}
            filters.append(filt)

        for entry in self.get_filters(deleted=True):
            filt = {'vzRsSubjFiltAtt': {'attributes': {'status': 'deleted', 'tnVzFilterName': entry.name}}}
            filters.append(filt)
        resp_json[subject]['children'] = filters

        terminals = []
        for entry in self.get_children():
            if isinstance(entry, BaseTerminal):
                terminal = entry.get_json()
                terminals.append(terminal)
        resp_json[subject]['children'].extend(terminals)

        return resp_json

    def add_filter(self, filter_obj):
        """
        Add Filter to the ContractSubject, roughly equivalent to vzRsSubjFiltAtt

        :param filter_obj:   Instance of Filter class. Represents\
                             a Filter that is added to the ContractSubject.\
                             Multiple Filter can be assigned to a single\
                             ContractSubject.
        """
        if not isinstance(filter_obj, Filter):
            raise TypeError('add_filter not called with Filter')
        self._add_relation(filter_obj)

    def get_filters(self, deleted=False):
        """
        Get all of the filters that are attached to this ContractSubject.

        :returns: List of Filter objects
        """
        resp = []
        for relation in self._relations:
            if deleted:
                if relation.status == 'detached':
                    if isinstance(relation.item, Filter):
                        resp.append(relation.item)
            else:
                if relation.status == 'attached':
                    if isinstance(relation.item, Filter):
                        resp.append(relation.item)
        return resp

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/brc-%s/subj-%s.json?subscription=yes' % (
            self._parent._parent.name, self._parent.name, self.name)
        return [url]

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/subj-', '/']


class Filter(BaseACIObject):
    """ Filter : roughly equivalent to vzFilter """

    def __init__(self, filter_name, parent=None):
        # Backward compatibility, allows the use of Filters that are attached to
        # ContractSubject instead of Tenants
        contract_subject_parent = None
        if isinstance(parent, ContractSubject):
            logging.warning('The parent of a Filter should be a Tenant Object!')
            contract_subject_parent = parent
            parent = parent.get_parent().get_parent()
        super(Filter, self).__init__(filter_name, parent)
        if contract_subject_parent:
            contract_subject_parent.add_filter(self)

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['vzFilter']

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return [ContractSubject, Tenant]

    @classmethod
    def get(cls, session, tenant):
        """Gets all of the Filters for the current tenant from the APIC.

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant used to limit the Filters\
                       retreived from the APIC
        :returns: List of Filter objects
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 parent=tenant, tenant=tenant)

    @classmethod
    def get_by_name_and_tenant(cls, session, tenant, filter_name):
        """
        Returns the Filter Object with name == filter_name and tenant == tenant

        :param session: the instance of Session used for APIC communication
        :param tenant: the instance of Tenant used to limit the search scope
        :param filter_name: the searched Filter Object
        :returns: a single Filter Object

        """
        return [filt for filt in cls.get(session, tenant) if filt.name == filter_name][0]

    @classmethod
    def get_deep(cls, full_data, working_data, parent=None, limit_to=(), subtree='full', config_only=False):
        filter_data = working_data[0]['vzFilter']
        filt = Filter(str(filter_data['attributes']['name']), parent)
        filt._populate_from_attributes(filter_data['attributes'])
        for child in filter_data.get('children', ()):
            if 'vzEntry' in child:
                FilterEntry.create_from_apic_json(child, filt)

    @staticmethod
    def get_from_json(self, data, parent=None):
        """
        returns a Tenant object from a json
        """
        for child in data['vzFilter']['children']:
            if 'vzEntry' in child:
                filterentry_name = child['vzEntry']['attributes']['name']
                filterentry = FilterEntry(filterentry_name, parent=self)
                filterentry._populate_from_attributes(child['vzEntry']['attributes'])
        return super(Filter, self).get_from_json(self, data, parent=parent)

    def get_json(self):
        """
        Returns json representation of the Filter

        :returns: json dictionary of the Filter
        """
        attr = {'name': self.name}
        resp_json = super(Filter, self).get_json('vzFilter',
                                                 attributes=attr)
        filter_entries = []
        for entry in self.get_children():
            filter_entries.append(entry.get_json())
        resp_json['vzFilter']['children'] = filter_entries
        return resp_json

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/flt-', '/']

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/flt-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    def has_entry(self, applyToFrag, arpOpc, dFromPort, dToPort, etherT, prot, sFromPort, sToPort,
                  tcpRules, stateful, icmpv4T='not-given', icmpv6T='not-given'):
        """
        Returns whether or not the Filter has a FilterEntry. All fields are compared except name.

        :returns: True if the Filter has a matching FilterEntry. False otherwise
        """
        for entry in self.get_children(only_class=FilterEntry):
            if entry.applyToFrag == applyToFrag and entry.etherT == etherT and entry.arpOpc == arpOpc and\
                    entry.dFromPort == dFromPort and entry.sFromPort == sFromPort and \
                    entry.dToPort == dToPort and entry.sToPort == sToPort and entry.prot == prot and\
                    entry.tcpRules == tcpRules and entry.stateful == stateful:
                if icmpv6T == 'not-given' and icmpv4T == 'not-given':
                    return True
                elif icmpv6T == 'not-given':
                    if entry.icmpv4T == icmpv4T:
                        return True
                elif icmpv4T == 'not-given':
                    if entry.icmpv6T == icmpv6T:
                        return True
                else:
                    if entry.icmpv4T == icmpv4T and entry.icmpv6T == icmpv6T:
                        return True
        return False


class Taboo(BaseContract):
    """ Taboo :  Class for Taboos """

    def __init__(self, contract_name, parent=None):
        super(Taboo, self).__init__(contract_name, parent)

    @staticmethod
    def _get_contract_code():
        """
        Returns the APIC class name for this type of contract.

        :returns: String containing APIC class name for this type of contract.
        """
        return 'vzTaboo'

    @staticmethod
    def _get_subject_code():
        return 'vzTSubj'

    @staticmethod
    def _get_subject_relation_code():
        return 'vzRsDenyRule'

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/taboo-', '/']

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/taboo-%s.json?subscription=yes' % (self._parent.name, self.name)
        return [url]

    @staticmethod
    def get_table(taboos, title=''):
        """
        Will create table of taboo information for a given tenant

        :param title:
        :param taboos:
        """

        result = []
        headers = ['Tenant', 'Taboo', 'Scope']
        data = []
        for taboo in sorted(taboos, key=attrgetter('name')):
            data.append([
                taboo.get_parent().name,
                taboo.name,
                taboo.get_scope(),
            ])

            result.append(Table(data, headers, title=title + 'Taboo:{0}'.format(taboo.name)))
        return result

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary
        These are the children objects

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {'vzTSubj': ContractSubject, }


class FilterEntry(BaseACIObject):
    """ FilterEntry :  roughly equivalent to vzEntry """

    def __init__(self, name, parent, applyToFrag='0', arpOpc='0',
                 dFromPort='0', dToPort='0', etherT='0', prot='0',
                 sFromPort='0', sToPort='0', tcpRules='0', stateful='0',
                 icmpv4T='not-given', icmpv6T='not-given'):
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
        :param stateful: True or False.  True indicates that this\
                         FilterEntry should monitor the TCP ACK bit.
        :param icmpv4T: String containing the ICMPv4 type.
        :param icmpv6T: String containing the ICMPv6 type.
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
        self.stateful = stateful
        self.icmpv4T = icmpv4T
        self.icmpv6T = icmpv6T
        # Backward compatibility for old calls that reference a Contract instead
        # of a Filter Object
        if isinstance(parent, Contract):
            contract_subject_name = parent.name + "_Subject"
            # Look for an existing ContractSubject
            found = False
            for child in parent.get_children():
                if isinstance(child, ContractSubject) and child.name == contract_subject_name:
                    contract_subject = child
                    found = True
                    break
            if not found:
                # Create the ContractSubject if not existing
                contract_subject = ContractSubject(parent.name + "_Subject", parent)
            filt = Filter(name + "_Filter", parent.get_parent())
            contract_subject.add_filter(filt)
            parent = filt
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
        attributes['stateful'] = self.stateful
        if self.icmpv4T != 'not-given':
            attributes['icmpv4T'] = self.icmpv4T
        if self.icmpv6T != 'not-given':
            attributes['icmpv6T'] = self.icmpv6T
        return attributes

    def _populate_from_attributes(self, attributes):
        super(FilterEntry, self)._populate_from_attributes(attributes)
        self.applyToFrag = str(attributes['applyToFrag'])
        self.arpOpc = str(attributes['arpOpc'])
        self.dFromPort = str(attributes['dFromPort'])
        self.dToPort = str(attributes['dToPort'])
        self.etherT = str(attributes['etherT'])
        self.prot = str(attributes['prot'])
        self.sFromPort = str(attributes['sFromPort'])
        self.sToPort = str(attributes['sToPort'])
        self.tcpRules = str(attributes['tcpRules'])
        self.stateful = str(attributes['stateful'])
        if 'icmpv4T' in attributes:
            self.icmpv4T = str(attributes['icmpv4T'])
        else:
            self.icmpv4T = 'not-given'
        if 'icmpv6T' in attributes:
            self.icmpv6T = str(attributes['icmpv6T'])
        else:
            self.icmpv6T = 'not-given'

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return [Contract, Filter, Taboo]

    def get_json(self):
        """
        Returns json representation of the FilterEntry

        :returns: json dictionary of the FilterEntry
        """
        attr = self._generate_attributes()
        text = super(FilterEntry, self).get_json('vzEntry',
                                                 attributes=attr)
        # filter_name = self.get_parent().name + self.name
        # text = {'vzFilter': {'attributes': {'name': filter_name},
        #                      'children': [text]}}
        return text

    @classmethod
    def get(cls, session, parent, tenant):
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
                tenant_url = parent._get_url_extension()
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
            if dn.split('/')[2][4:] == parent.name and \
               dn.split('/')[4][len('rssubjFiltAtt-'):] == dn.split('/')[3][5:] and \
               dn.split('/')[3][5:] == tDn.split('/')[2][4:] and tDn.split('/')[2][4:] == tRn[4:]:
                filter_name = str(object_data[apic_class]['attributes']['tRn'][4:])
                contract_name = filter_name[:len(parent.name)]
                entry_name = filter_name[len(parent.name):]
                if contract_name == parent.name and entry_name != '':
                    query_url = ('/api/mo/uni%s/flt-%s.json?query-target=subtree&'
                                 'target-subtree-class=vzEntry&'
                                 'query-target-filter=eq(vzEntry.name,"%s")' % (tenant_url, filter_name, entry_name))
                    ret = session.get(query_url)
                    filter_data = ret.json()['imdata']
                    if len(filter_data) == 0:
                        continue
                    logging.debug('response returned %s', filter_data)
                    resp = []
                    obj = cls(entry_name, parent)
                    attribute_data = filter_data[0]['vzEntry']['attributes']
                    obj._populate_from_attributes(attribute_data)
                    resp.append(obj)
        return resp

    @classmethod
    def create_from_apic_json(cls, data, parent):
        """
        create from the apic json

        :param data: json dictionary
        :param parent: parent object
        :return: object created from json dictionary
        """
        attributes = data['vzEntry']['attributes']
        if 'name' in attributes:
            name = str(attributes.get('name'))
        elif 'dn' in attributes:
            name = cls._get_name_from_dn(str(attributes.get('dn')))
        else:
            raise ValueError('Name not found in attributes')
        entry = cls(name=name,
                    parent=parent)
        entry._populate_from_attributes(attributes)
        return entry

    @staticmethod
    def get_table(filters, title=''):
        """
        Will create table of filter information for a given tenant

        :param title:
        :param filters:
        """

        headers = ['Filter', 'EtherType',
                   'Protocol', 'Arp Opcode', 'L4 DPort', 'L4 SPort', 'TCP Flags', 'Apply to Fragment']

        data = []
        for filter in sorted(filters, key=attrgetter('name')):
            data.append([
                filter.name,
                filter.etherT,
                filter.prot,
                filter.arpOpc,
                FilterEntry._get_port(filter.dFromPort, filter.dToPort),
                FilterEntry._get_port(filter.sFromPort, filter.sToPort),
                filter.tcpRules,
                filter.stateful,
                filter.applyToFrag,
            ])
        data = sorted(data)
        table = Table(data, headers, title=title + 'Filters')
        return [table, ]

    @staticmethod
    def _get_port(from_port, to_port):
        """
        will build a string that is a port range or a port number
        depending upon the from_port and to_port value
        """
        if from_port == to_port:
            return str(from_port)
        return '{0}-{1}'.format(str(from_port), str(to_port))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            key_attrs = attrgetter(
                'applyToFrag', 'arpOpc', 'dFromPort', 'dToPort', 'etherT',
                'prot', 'sFromPort', 'sToPort', 'tcpRules', 'stateful')
            return key_attrs(self) == key_attrs(other)
        return NotImplemented

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/flt-%s/e-%s.json?subscription=yes' % (self._parent.name, self._parent.name, self.name)
        return [url]

    def __hash__(self):
        return hash((self.applyToFrag,
                     self.arpOpc,
                     self.dFromPort,
                     self.dToPort,
                     self.etherT,
                     self.prot,
                     self.sFromPort,
                     self.sToPort,
                     self.tcpRules,
                     self.stateful))

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/e-', '/']

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by the acitoolkit class.
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: list of strings containing APIC class names
        """
        return []


class BaseTerminal(BaseACIObject):
    """
    Base class for Input terminal and output terminal
    """

    def __init__(self, terminal_name, parent=None):
        super(BaseTerminal, self).__init__(terminal_name, parent)

    @classmethod
    def mask_class_from_graphs(cls):
        # Returns True if called for BaseTerminal
        return cls.__name__ == 'BaseTerminal'

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return ContractSubject

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return [cls._get_terminal_code()]

    def get_json(self):
        """
        Returns json representation of the Terminal Object

        :returns: json dictionary of the ContractSubject
        """
        attr = self._generate_attributes()
        apic_object_type = self._get_terminal_code()
        resp_json = super(BaseTerminal, self).get_json(apic_object_type,
                                                       attributes=attr,
                                                       get_children=False)
        filters = []
        for entry in self.get_filters():
            filt = {'vzRsFiltAtt': {'attributes': {'tnVzFilterName': entry.name}}}
            filters.append(filt)
        resp_json[apic_object_type]['children'] = filters
        return resp_json

    def _extract_relationships(self, data, obj_dict):
        """
        Extracts and rebuild the relationships between the ContractSubject
        and Filter objects.
        """
        contract_subject = self.get_parent()
        contract = contract_subject.get_parent()
        tenant = contract.get_parent()
        for tenant_data in data:
            if 'fvTenant' in tenant_data and tenant_data['fvTenant']['attributes']['name'] == tenant.name:
                contract_data = tenant_data['fvTenant']['children']
        if len(contract_data):
            for child in contract_data:
                if 'vzBrCP' in child and 'children' in child['vzBrCP'] and \
                        child['vzBrCP']['attributes']['name'] == contract.name:
                    for subj in child['vzBrCP']['children']:
                        if 'vzSubj' in subj and \
                                subj['vzSubj']['attributes']['name'] == contract_subject.name and \
                                'children' in subj['vzSubj']:
                            for subj_child in subj['vzSubj']['children']:
                                try:
                                    if 'vzInTerm' in subj_child or 'vzOutTerm' in subj_child:
                                        for filt in subj_child[self._get_terminal_code()]['children']:
                                            if 'vzRsFiltAtt' in filt:

                                                filt_name = filt['vzRsFiltAtt']['attributes']['tnVzFilterName']
                                                if Filter in obj_dict:
                                                    all_filters = obj_dict[Filter]
                                                    if len(all_filters):
                                                        found = False
                                                        for specific_filter in all_filters:
                                                            if specific_filter.name == filt_name and \
                                                                    specific_filter.get_parent() == tenant:
                                                                self.add_filter(specific_filter)
                                                                found = True
                                                        if not found:
                                                            for specific_filter in all_filters:
                                                                if specific_filter.name == filt_name and \
                                                                        specific_filter.get_parent().name == 'common':
                                                                    self.add_filter(specific_filter)
                                except KeyError:
                                    pass

        super(BaseTerminal, self)._extract_relationships(data, obj_dict)

    def add_filter(self, filter_obj):
        """
        Add Filter to the Terminal, roughly equivalent to vzRsFiltAtt

        :param filter_obj:   Instance of Filter class. Represents\
                             a Filter that is added to the Terminal.\
                             Multiple Filters can be assigned to a single\
                             Terminal.
        """
        if not isinstance(filter_obj, Filter):
            raise TypeError('add_filter not called with Filter')
        self._add_relation(filter_obj)

    def get_filters(self):
        """
        Get all of the filters that are attached to this Terminal.

        :returns: List of Filter objects
        """
        resp = []
        for relation in self._relations:
            if isinstance(relation.item, Filter):
                resp.append(relation.item)
        return resp

    @staticmethod
    def _get_terminal_code():
        """
        Abstract method that should be over ridden

        :returns: String containing APIC class name for this type of terminal.
        """
        assert NotImplemented('This method needs to be implemented')


class InputTerminal(BaseTerminal):
    """
    Input terminal for a graph.  It is input with respect to the
    provider
    """
    @staticmethod
    def _get_terminal_code():
        """
        Returns the APIC class name for this type of terminal.

        :returns: String containing APIC class name for this type of terminal.
        """
        return 'vzInTerm'

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/intmnl', '/']

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return ContractSubject


class OutputTerminal(BaseTerminal):
    """
    Input terminal for a graph.  It is input with respect to the
    provider
    """
    @staticmethod
    def _get_terminal_code():
        """
        Returns the APIC class name for this type of terminal.

        :returns: String containing APIC class name for this type of terminal.
        """
        return 'vzOutTerm'

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/outtmnl', '/']

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return ContractSubject


class TunnelInterface(object):
    """This class describes a tunnel interface"""

    def __init__(self, if_type, pod, node, tunnel):
        self.interface_type = str(if_type)
        self.pod = str(pod)
        self.node = str(node)
        self.tunnel = tunnel
        self.if_name = self.interface_type + ' ' + self.pod + '/'
        self.if_name += self.node + '/' + self.tunnel


class FexInterface(BaseACIObject):
    """This class describes a physical interface on a FEX device"""

    def __init__(self, if_type, pod, node, fex, module, port):
        if_name = str(if_type) + ' ' + str(pod) + '/'
        if_name += str(node) + '/' + str(fex) + '/'
        if_name += str(module) + '/' + str(port)
        super(FexInterface, self).__init__(if_name)
        self.interface_type = str(if_type)
        self.pod = str(pod)
        self.node = str(node)
        self.fex = str(fex)
        self.module = str(module)
        self.port = str(port)
        self._session = None
        self.if_name = if_name
        self.attributes = {'if_name': self.if_name}
        if self.attributes.get('dn') is None:
            self.attributes['dn'] = self._get_path()
        self.stats = InterfaceStats(self, self.attributes.get('dn'))

    @classmethod
    def parse_dn(cls, dn):
        """
        Parse the pod, node, interface name from the dn
        :param dn: String containing the interface DN
        :return: Tuple consisting of if_type, pod, node, fex, module, port
        """
        if '/phys-' in dn:
            pod = dn.split('/pod-')[1].split('/')[0]
            node = dn.split('/node-')[1].split('/')[0]
            if_name = dn.split('/phys-[')[1]
            if_type = if_name[:3]
            if_name = if_name.split(']')[0]
            fex, module, port = if_name[3:].split('/')
            return if_type, pod, node, fex, module, port

    @classmethod
    def is_dn_a_fex_interface(cls, dn):
        # topology/pod-1/node-101/sys/phys-[eth101/1/1]
        if '/phys-[' in dn:
            if len(dn.split('/phys-[')[1].split(']')[0].split('/')) == 3:
                return True
        return False

    def _get_path(self):
        """Get the path of this interface used when communicating with
           the APIC object model.
        """
        return 'topology/pod-%s/paths-%s/extpaths-%s/pathep-[eth%s/%s]' % (self.pod,
                                                                           self.node,
                                                                           self.fex,
                                                                           self.module,
                                                                           self.port)


def _interface_from_dn(dn):
    """
    Creates the appropriate interface object based on the dn
    The classes along with an example DN are shown below
    Interface: topology/pod-1/paths-102/pathep-[eth1/12]
    FexInterface: topology/pod-1/paths-103/extpaths-105/pathep-[eth1/12]
    TunnelInterface:
    BladeSwitchInterface:
    """
    interface_pattern = r'''(?x)
        topology/pod-(?P<pod>\d+)/paths-(?P<node>\d+)/
        (?:extpaths-(?P<fex>\d+)/)? # optional fex path fragment
        pathep-
        \[
        (?: # physical interface or tunnel
            (?P<if_type>[A-Za-z]{3})(?P<module>\d+)/(?P<port>\d+)
        |
            tunnel(?P<tunnel>\w+)
        )
        \]
    '''
    match = re.match(interface_pattern, dn)
    if not match:
        # Look for Fex interfaces encoded as topology/pod-1/node-101/sys/phys-[eth101/1/1]
        if FexInterface.is_dn_a_fex_interface(dn):
            return FexInterface(*FexInterface.parse_dn(dn))
        return Interface(*Interface.parse_dn(dn))
    elif match.group('fex') is not None:
        args = match.group('if_type', 'pod', 'node', 'fex', 'module', 'port')
        return FexInterface(*args)
    elif match.group('tunnel') is not None:
        args = match.group('pod', 'node', 'tunnel')
        return TunnelInterface('tunnel', *args)
    else:
        return Interface(*Interface.parse_dn(dn))


class PortChannel(BaseInterface):
    """
    This class defines a port channel interface.
    """

    def __init__(self, name):
        super(PortChannel, self).__init__(name)
        self._interfaces = []
        self._nodes = []
        self._pod = '1'

    @classmethod
    def create_from_dn(cls, dn):
        """
        Create a PortChannel instance based on the specified DN

        :param dn: String containing the DN
        :return: Instance of PortChannel class
        """
        pod = dn.partition('/pod-')[-1].partition('/')[0]
        nodes = dn.partition('/protpaths-')[-1].partition('/')[0].split('-')
        name = dn.partition('/pathep-[')[-1].partition(']')[0]
        port_channel = cls(name)
        port_channel._nodes = nodes
        port_channel._pod = pod
        return port_channel

    def attach(self, interface):
        """Attach an interface to this PortChannel

        :param interface:
        """
        if interface not in self._interfaces:
            self._interfaces.append(interface)
        self._update_nodes()

    def detach(self, interface):
        """Detach an interface from this PortChannel

        :param interface:
        """
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
        # assert len(self._interfaces)
        if self.is_vpc():
            (node1, node2) = self._get_nodes()
            # Make sure the order of the nodes is the right one (lowest numbered
            # first)
            if int(node1) > int(node2):
                node1, node2 = node2, node1
            path = 'topology/pod-%s/protpaths-%s-%s/pathep-[%s]' % (self._pod,
                                                                    node1,
                                                                    node2,
                                                                    self.name)
        else:
            node = self._interfaces[0].node
            path = 'topology/pod-%s/paths-%s/pathep-%s' % (self._pod,
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
        infra = {'infraInfra': {'attributes': {}, 'children': []}}
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
        accbndlgrp = {'infraAccBndlGrp': {'attributes': {'name': self.name, 'lagT': pc_mode},
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
        fabric_group = {'fabricExplicitGEp': {'attributes': {'name': 'vpc' + unique_id, 'id': unique_id},
                                              'children': fabric_nodes}}
        fabric_prot_pol = {'fabricProtPol': {'attributes': {'name': 'vpc' + unique_id},
                                             'children': [fabric_group]}}
        return fabric_prot_pol, infra

    @staticmethod
    def get(session):
        """Gets all of the port channel interfaces from the APIC

        :param session:
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
    """
    Endpoint class
    """

    def __init__(self, name, parent):
        if not isinstance(parent, EPG):
            raise TypeError('Parent must be of EPG class')
        super(Endpoint, self).__init__(name, parent=parent)
        self.mac = None
        self.ip = None
        self.encap = None
        self.if_name = None
        self.if_dn = []
        self.secondary_ip = []

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvCEp', 'fvStCEp']

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary

        :returns: dict of APIC class names to acitoolkit classes
        """
        return {}

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return EPG

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/tn-%s/ap-%s/epg-%s/cep-%s.json?subscription=yes' % (
            self._parent._parent._parent.name, self._parent._parent.name, self._parent.name, self.name)
        return [url]

    @staticmethod
    def _get_parent_dn(dn):
        """
        Get the parent DN

        :param dn: string containing the distinguished name URL
        :return: None
        """
        if '/stcep-' in dn:
            return dn.split('/stcep-')[0]
        else:
            return dn.split('/cep-')[0]

    @classmethod
    def _get_name_from_dn(cls, dn):
        if '/stcep-' in dn:
            name = dn.split('/stcep-')[1].split('-type-')[0]
        elif '/cep-' in dn:
            name = dn.split('/cep-')[1]
        else:
            name = None
        return name

    def get_json(self):
        return None

    def _populate_from_attributes(self, attributes):
        if 'mac' not in attributes:
            return
        super(Endpoint, self)._populate_from_attributes(attributes)
        if 'mac' in attributes:
            self.mac = str(attributes.get('mac'))
        if 'ip' in attributes:
            self.ip = str(attributes.get('ip'))
        if 'encap' in attributes:
            self.encap = str(attributes.get('encap'))
        if 'lcC' in attributes:
            life_cycle = str(attributes.get('lcC'))
        if life_cycle is not '':
            self.life_cycle = life_cycle
        if 'type' in attributes:
            self.type = str(attributes.get('type'))

    def _populate_interface_info(self, working_data):
        """
        Populate the interface information for the Endpoint

        :param working_data: JSON dictionary containing the working data
        :return: None
        """
        for item in working_data[0]:
            if 'children' in working_data[0][item]:
                children = working_data[0][item]['children']
                for child in children:
                    for child_item in child:
                        if child_item in ['fvRsCEpToPathEp', 'fvRsStCEpToPathEp']:
                            if child[child_item]['attributes']['state'] != 'formed':
                                continue
                            if_dn = str(child[child_item]['attributes']['tDn'])
                            if 'protpaths' in if_dn:
                                regex = re.search(r'pathep-\[(.+)\]$', if_dn)
                                if regex is not None:
                                    self.if_name = regex.group(1)
                                else:
                                    self.if_name = if_dn
                            elif 'tunnel' in if_dn:
                                self.if_name = if_dn
                            elif 'pathgrp' in if_dn:
                                self.if_name = if_dn
                            else:
                                name = if_dn.split('/')
                                pod = str(name[1].split('-')[1])
                                node = str(name[2].split('-')[1])
                                port_result = re.search(r'pathep-\[eth(.+)\]$', if_dn)
                                if port_result is None:
                                    self.if_name = self.if_dn
                                else:
                                    port = port_result.group(1)
                                    self.if_name = 'eth {0}/{1}/{2}'.format(pod, node, port)

                        if child_item == 'fvIp' or child_item == 'fvStIp':
                            ip_address = str(child[child_item]['attributes']['addr'])
                            self.secondary_ip.append(ip_address)

    @classmethod
    def get_deep(cls, full_data, working_data, parent=None, limit_to=(), subtree='full', config_only=False):
        """
        Gets all instances of this class from the APIC and gets all of the
        children as well.

        :param full_data:
        :param working_data:
        :param parent:
        :param limit_to:
        :param subtree:
        :param config_only:
        """
        obj = None
        for item in working_data:
            for key in item:

                # if an endpoint is static then a dynamic one is also created
                # the following will prevent the dynamic one from being added
                if item[key]['attributes']['lcC'] == 'static' and key == 'fvCEp':
                    continue

                if key in cls._get_apic_classes():
                    attribute_data = item[key]['attributes']
                    name = str(attribute_data['name'])
                    if name == '':
                        name = attribute_data['mac']
                    obj = cls(name, parent)
                    if key == 'fvStCEp':
                        obj.life_cycle = 'static'
                    obj._populate_from_attributes(attribute_data)
                    obj._populate_interface_info(working_data)
                    if 'children' in item[key]:
                        for child in item[key]['children']:
                            for apic_class in child:
                                class_map = cls._get_toolkit_to_apic_classmap()
                                if apic_class not in class_map:
                                    if apic_class == 'tagInst':
                                        obj._tags.append(Tag(str(child[apic_class]['attributes']['name'])))
                                    continue
                                else:
                                    class_map[apic_class].get_deep(full_data=full_data,
                                                                   working_data=[child],
                                                                   parent=obj,
                                                                   limit_to=limit_to,
                                                                   subtree=subtree,
                                                                   config_only=config_only)
        return obj

    @classmethod
    def get_event(cls, session, with_relations=True):
        urls = cls._get_subscription_urls()
        for url in urls:
            if not session.has_events(url):
                continue
            event = session.get_event(url)
            for class_name in cls._get_apic_classes():
                if class_name in event['imdata'][0]:
                    break
            attributes = event['imdata'][0][class_name]['attributes']
            if 'status' in attributes:
                status = str(attributes.get('status'))
            if 'dn' in attributes:
                dn = str(attributes.get('dn'))
            parent = cls._get_parent_from_dn(cls._get_parent_dn(dn))
            if status == 'created' and 'mac' in attributes:
                name = str(attributes.get('mac'))
            else:
                name = cls._get_name_from_dn(dn)
            obj = cls(name, parent=parent)
            obj._populate_from_attributes(attributes)
            if 'modTs' in attributes:
                obj.timestamp = str(attributes.get('modTs'))
            if obj.mac is None:
                obj.mac = name
            try:
                if status == 'deleted':
                    obj.mark_as_deleted()
                elif with_relations:
                    objs = cls.get(session, name)
                    if len(objs):
                        obj = objs[0]
                    else:
                        # Endpoint was deleted before we could process the create
                        # return what we what we can from the event
                        pass
                return obj
            except IndexError:
                continue

    @staticmethod
    def _get(session, endpoint_name, interfaces, endpoints,
             apic_endpoint_class, endpoint_path):
        """
        Internal function to get all of the Endpoints

        :param session: Session object to connect to the APIC
        :param endpoint_name: string containing the name of the endpoint
        :param interfaces: list of interfaces
        :param endpoints: list of endpoints
        :param apic_endpoint_class: class of endpoint
        :param endpoint_path: interface of the endpoint
        :return: list of Endpoints
        """
        # Get all of the Endpoints
        if endpoint_name is None:
            endpoint_query_url = ('/api/node/class/%s.json?query-target=self'
                                  '&rsp-subtree=full' % apic_endpoint_class)
        else:
            endpoint_query_url = ('/api/node/class/%s.json?query-target=self'
                                  '&query-target-filter=eq(%s.mac,"%s")'
                                  '&rsp-subtree=full' % (apic_endpoint_class,
                                                         apic_endpoint_class,
                                                         endpoint_name))
        ret = session.get(endpoint_query_url)
        ep_data = ret.json()['imdata']
        for ep in ep_data:
            if ep[apic_endpoint_class]['attributes']['lcC'] == 'static':
                continue
            if 'children' in ep[apic_endpoint_class]:
                children = ep[apic_endpoint_class]['children']
            else:
                children = []
            ep = ep[apic_endpoint_class]['attributes']
            tenant = Tenant(str(ep['dn']).split('/')[1][3:])
            if '/LDevInst-' in str(ep['dn']):
                unknown = '?' * 10
                app_profile = AppProfile(unknown, tenant)
                epg = EPG(unknown, app_profile)
            else:
                app_profile = AppProfile(str(ep['dn']).split('/')[2][3:],
                                         tenant)
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
                                endpoint.if_name = _interface_from_dn(interface_dn).if_name
                            else:
                                endpoint.if_name = interface['name']
                                endpoint.if_dn.append(interface_dn)
                    # endpoint_query_url = '/api/mo/' + endpoint.if_name + '.json'
                    # ret = session.get(endpoint_query_url)
            endpoints.append(endpoint)
        return endpoints

    @staticmethod
    def get(session, endpoint_name=None):
        """Gets all of the endpoints connected to the fabric from the APIC

        :param endpoint_name:
        :param session: Session instance used to communicate with the APIC. Assumed to be logged in
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        # Get all of the interfaces
        interface_query_url = ('/api/node/class/fabricPathEp.json?'
                               'query-target=self')
        ret = session.get(interface_query_url)
        interfaces = ret.json()['imdata']

        endpoints = []
        endpoints = Endpoint._get(session, endpoint_name, interfaces,
                                  endpoints, 'fvCEp', 'fvRsCEpToPathEp')
        endpoints = Endpoint._get(session, endpoint_name, interfaces,
                                  endpoints, 'fvStCEp', 'fvRsStCEpToPathEp')

        return endpoints

    @classmethod
    def get_all_by_epg(cls, session, tenant_name, app_name, epg_name, with_interface_attachments=True):
        """
        Get all of the Endpoints for a specified EPG

        :param session: Session instance used to communicate with the APIC. Assumed to be logged in
        :param tenant_name: String containing the tenant name
        :param app_name: String containing the app name
        :param epg_name: String containing the epg name
        :param with_interface_attachments: Boolean indicating whether interfaces should be attached or not.
                                           True is default.
        :return: List of Endpoint instances
        """
        if with_interface_attachments:
            raise NotImplementedError
        query_url = ('/api/mo/uni/tn-%s/ap-%s/epg-%s.json?'
                     'rsp-subtree=children&'
                     'rsp-subtree-class=fvCEp,fvStCEp' % (tenant_name, app_name, epg_name))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        endpoints = []
        if len(data) == 0:
            return endpoints
        assert len(data) == 1
        assert 'fvAEPg' in data[0]
        if 'children' not in data[0]['fvAEPg']:
            return endpoints
        endpoints_data = data[0]['fvAEPg']['children']
        if len(endpoints_data) == 0:
            return endpoints
        tenant = Tenant(tenant_name)
        app = AppProfile(app_name, tenant)
        epg = EPG(epg_name, app)
        for ep_data in endpoints_data:
            if 'fvStCEp' in ep_data:
                mac = ep_data['fvStCEp']['attributes']['mac']
                ip = ep_data['fvStCEp']['attributes']['ip']
            else:
                mac = ep_data['fvCEp']['attributes']['mac']
                ip = ep_data['fvCEp']['attributes']['ip']
            ep = cls(str(mac), epg)
            ep.mac = mac
            ep.ip = ip
            endpoints.append(ep)
        return endpoints

    @staticmethod
    def get_table(endpoints, title=''):
        """
        Will create table of taboo information for a given tenant

        :param title:
        :param endpoints:
        """

        result = []
        headers = ['Tenant', 'Context', 'Bridge Domain', 'App Profile', 'EPG', 'Name', 'MAC', 'IP', 'Interface',
                   'Encap']
        data = []
        for endpoint in sorted(endpoints, key=attrgetter('name')):
            epg = endpoint.get_parent()
            bd = 'Not Set'
            context = 'Not Set'
            if epg.has_bd():
                bd = epg.get_bd().name
                if epg.get_bd().has_context():
                    context = epg.get_bd().get_context().name

            data.append([
                endpoint.get_parent().get_parent().get_parent().name,
                context,
                bd,
                endpoint.get_parent().get_parent().name,
                endpoint.get_parent().name,
                endpoint.name,
                endpoint.mac,
                endpoint.ip,
                endpoint.if_name,
                endpoint.encap
            ])
        data = sorted(data, key=itemgetter(1, 2, 3, 4))
        result.append(Table(data, headers, title=title + 'Endpoints'))
        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        results = super(Endpoint, self)._define_searchables()

        results[0].add_term('ipv4', str(self.ip))
        for secondary_ip in self.secondary_ip:
            results[0].add_term('secondary_ip', secondary_ip)
            results[0].add_term('ipv4', secondary_ip)
        return results


class IPEndpoint(BaseACIObject):
    """
    Endpoint class
    """

    def __init__(self, name, parent):
        # if not isinstance(parent, EPG):
        #     raise TypeError('Parent must be of EPG class')
        super(IPEndpoint, self).__init__(name, parent=parent)
        self.ip = None
        self.mac = None

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvIp', 'fvStIp']

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return EPG

    @classmethod
    def _get_parent_from_dn(cls, dn):
        """
        Derive the parent object using a dn

        :param dn: String containing a distinguished name of an object
        """
        if '/l2out-' in dn and '/instP-' in dn:
            parent_name = OutsideL2EPG._get_name_from_dn(dn)
            parent_dn = cls._get_parent_dn(dn)
            parent_obj = OutsideL2EPG(parent_name,
                                      OutsideL2EPG._get_parent_from_dn(parent_dn))
            return parent_obj
        return super(IPEndpoint, cls)._get_parent_from_dn(dn)

    @staticmethod
    def _get_name_dn_delimiters():
        return ['/ip-[', ']']

    def get_json(self):
        return None

    def _populate_from_attributes(self, attributes):
        super(IPEndpoint, self)._populate_from_attributes(attributes)
        if 'addr' in attributes:
            self.ip = str(attributes.get('addr'))

    @staticmethod
    def _get_mac_from_dn(dn):
        """
        Extract the MAC address from the dn

        :param dn: string containing the distinguished name URL
        :return: String containing the MAC address or None if not found
        """
        # Handle static IP addresses
        if '/stcep-' in dn:
            return str(dn.split('/stcep-')[1].partition('-type-')[0])
        # Handle dynamic IP addresses
        if '/cep-' in dn:
            return str(dn.split('/cep-')[1].partition('/')[0])
        if '/epdef-' in dn:
            return str(dn.split('/cep-')[1].partition('/')[0])
        return None

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
            if 'status' in attributes:
                status = str(attributes.get('status'))
            if 'dn' in attributes:
                dn = str(attributes.get('dn'))
            parent = cls._get_parent_from_dn(cls._get_parent_dn(dn))
            name = cls._get_name_from_dn(dn)
            obj = cls(name, parent=parent)
            obj._populate_from_attributes(attributes)
            obj.mac = obj._get_mac_from_dn(dn)
            if status == 'deleted':
                obj.mark_as_deleted()
            return obj

    @staticmethod
    def _get(session, endpoints, apic_endpoint_class):
        """
        Internal function to get all of the IPEndpoints

        :param session: Session object to connect to the APIC
        :param endpoints: list of endpoints
        :param apic_endpoint_class: class of endpoint
        :return: list of Endpoints
        """
        # Get all of the Endpoints
        endpoint_query_url = ('/api/node/class/%s.json?query-target=self'
                              '&rsp-subtree=full' % apic_endpoint_class)
        ret = session.get(endpoint_query_url)
        if not ret.ok:
            raise ConnectionError
        ep_data = ret.json()['imdata']
        for ep in ep_data:
            ep = ep[apic_endpoint_class]['attributes']
            ep_dn = str(ep['dn'])
            ep_addr = str(ep['addr'])
            if not all(x in ep_dn for x in ['/tn-', 'ap-', 'epg-']):
                continue
            tenant = Tenant(ep_dn.split('/')[1][3:])
            app_profile = AppProfile(ep_dn.split('/')[2][3:],
                                     tenant)
            epg = EPG(ep_dn.split('/')[3][4:], app_profile)
            endpoint = IPEndpoint(ep_addr, parent=epg)
            endpoint.ip = ep_addr
            endpoint.mac = IPEndpoint._get_mac_from_dn(ep_dn)
            endpoints.append(endpoint)
        return endpoints

    @staticmethod
    def get(session):
        """Gets all of the IP endpoints connected to the fabric from the APIC

        :param session: Session instance assumed to be logged into the APIC
        :return: List of IPEndpoint instances
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        endpoints = []
        endpoints = IPEndpoint._get(session, endpoints, 'fvIp')
        endpoints = IPEndpoint._get(session, endpoints, 'fvStIp')

        return endpoints

    @classmethod
    def get_all_by_epg(cls, session, tenant_name, app_name, epg_name):
        """
        Get all of the IP Endpoints for the specified EPG

        :param session: Session instance assumed to be logged into the APIC
        :param tenant_name: String containing the Tenant name that holds the EPG
        :param app_name: String containing the AppProfile name that holds the EPG
        :param epg_name: String containing the EPG name
        :return: List of IPEndpoint instances
        """
        query_url = ('/api/mo/uni/tn-%s/ap-%s/epg-%s.json?'
                     'query-target=subtree&'
                     'target-subtree-class=fvIp,fvStIp' % (tenant_name, app_name, epg_name))
        ret = session.get(query_url)
        endpoints = []
        if ret.ok:
            ep_data = ret.json()['imdata']
            if len(ep_data) == 0:
                return endpoints
            for ep in ep_data:
                if 'fvStIp' in ep:
                    attr = ep['fvStIp']['attributes']
                elif 'fvIp' in ep:
                    attr = ep['fvIp']['attributes']
                else:
                    logging.error('Could not get EPG endpoints from the APIC %s', ep)
                    break
                ep_dn = str(attr['dn'])
                ep_addr = str(attr['addr'])
                if not all(x in ep_dn for x in ['/tn-', 'ap-', 'epg-']):
                    continue
                tenant = Tenant(ep_dn.split('/')[1][3:])
                app_profile = AppProfile(ep_dn.split('/')[2][3:],
                                         tenant)
                epg = EPG(ep_dn.split('/')[3][4:], app_profile)
                endpoint = IPEndpoint(ep_addr, parent=epg)
                endpoint.ip = ep_addr
                endpoint.mac = IPEndpoint._get_mac_from_dn(ep_dn)
                endpoints.append(endpoint)
        else:
            raise ConnectionError
        return endpoints


class PhysDomain(BaseACIObject):
    """
    Physical Network domain
    """

    def __init__(self, name, parent=None):
        """
        :param name: String containing the PhysDomain name
        :param parent: An instance of DomP class representing
        """
        self.dn = None
        self.lcOwn = None
        self.childAction = None
        self.name = name
        super(PhysDomain, self).__init__(name, parent)

    def add_network(self, network_pool):
        """
        associate network pool to the physical domain
        :param network_pool: vlan or vxlan pool
        """
        if not isinstance(network_pool, NetworkPool):
            raise TypeError('add_network not called with NetworkPool')
        self._remove_all_relation(network_pool)
        self._add_relation(network_pool)

    def remove_network(self):
        """
        removes the associated vlan or vxlan from the physical domain
        :return:
        """
        self._remove_all_relation(NetworkPool)

    def get_network(self):
        """
        Get the network pool for this domain

        :returns: Instance of NetworkPool class associated to this Domain.
        """
        return self._get_any_relation(NetworkPool)

    def has_network(self):
        """
        Check if the network pool has been set for this physical domain

        :returns: True or False. True if this network pool is assigned to the\
                  domain.
        """
        return self._has_any_relation(NetworkPool)

    def get_json(self):
        """
        Returns json representation of the physDomP object

        :returns: A json dictionary of physical domain
        """
        attr = self._generate_attributes()
        children = []
        if self.has_network():
            network_pool = self.get_network()
            infraNsDn = 'uni/infra/%sns-[%s]-%s' % (network_pool.encap_type,
                                                    network_pool.name,
                                                    network_pool.mode)
            if network_pool.encap_type == 'vlan':
                infraNsType = 'infraRsVlanNs'
            elif network_pool.encap_type == 'vxlan':
                infraNsType = 'infraRsVxlanNs'

            infraRsNs = {infraNsType: {'attributes': {'tDn': infraNsDn}}}
            children.append(infraRsNs)
        return super(PhysDomain, self).get_json(self._get_apic_classes()[0],
                                                attributes=attr,
                                                children=children)

    def _generate_attributes(self):
        """
        Gets the attributes used in generating the JSON for the object
        """
        attributes = dict()
        if self.name:
            attributes['name'] = self.name
        if self.dn:
            attributes['dn'] = self.dn
        if self.lcOwn:
            attributes['lcOwn'] = self.lcOwn
        if self.childAction:
            attributes['childAction'] = self.childAction
        return attributes

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['physDomP']

    def get_parent(self):
        """
        :returns: Parent of this object.
        """
        return self._parent


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

    def push_to_apic(self, session):
        """
        Push the appropriate configuration to the APIC for this Phys Domain.
        All of the subobject configuration will also be pushed.

        :param session: the instance of Session used for APIC communication
        :returns: Requests Response code
        """
        resp = session.push_to_apic(self.get_url(),
                                    self.get_json())
        return resp

    @classmethod
    def get(cls, session):
        """
        Gets all of the Physical Domains from the APIC

        :param session: the instance of Session used for APIC communication
        :returns: List of PhysDomain objects

        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree&'
                      'target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']

        logging.debug('response returned %s', data)
        resp = []
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']
            obj.get_network_from_apic(session)
            resp.append(obj)
        return resp

    def get_network_from_apic(self, session):
        """
        get network from apic
        :param session:
        """
        apic_classes = {'infraRsVlanNs': 'vlan', 'infraRsVxlanNs': 'vxlan'}
        for ac in apic_classes:
            query_url = ('/api/mo/uni/phys-' + self.name + '.json?query-target=subtree&target-subtree-class=' + ac)
            ret = session.get(query_url)
            if int(ret.json()['totalCount']) == 0:
                continue
            data_pool = ret.json()['imdata']
            data_pool = data_pool[0]
            if ac in data_pool:
                tDn = data_pool[ac]['attributes']['tDn']
                mode = tDn.split("-")[-1]
                name_pool = tDn.split("-[")[1].split("]-")[0]
                network = NetworkPool(name_pool, apic_classes[ac], mode)
                self.add_network(network)

    @classmethod
    def get_by_name(cls, session, infra_name):
        """
        Gets all of the Physical Domains from the APIC

        :param infra_name:
        :param session: the instance of Session used for APIC communication
        :returns: List of PhysDomain objects
        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree&'
                      'target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']
            if name == infra_name:
                return obj
        return None


class VmmDomain(BaseACIObject):
    """
    VMMDomain class
    """

    def __init__(self, name, parent):
        """
        :param name: String containing the VMM Domain name
        :param parent: An instance of DomP class
        """
        self.dn = None
        self.lcOwn = None
        self.childAction = None
        self.name = name
        super(VmmDomain, self).__init__(name, parent)

    def get_json(self):
        """
        Returns json representation of the vmmDomP object

        :returns: A json dictionary of vmmDomP
        """
        attr = self._generate_attributes()
        return super(VmmDomain, self).get_json(self._get_apic_classes()[0],
                                               attributes=attr)

    def _get_path(self):
        """
        Get the URL of the VMM

        :return: string containing URL
        """
        return self.dn

    def _generate_attributes(self):
        """
        Gets the attributes used in generating the JSON for the object
        """
        attributes = dict()
        if self.name:
            attributes['name'] = self.name
        if self.dn:
            attributes['dn'] = self.dn
        if self.lcOwn:
            attributes['lcOwn'] = self.lcOwn
        if self.childAction:
            attributes['childAction'] = self.childAction
        return attributes

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['vmmDomP']

    def get_parent(self):
        """
        :returns: Parent of this object.
        """
        return self._parent

    @classmethod
    def get(cls, session):
        """
        Gets all of the VMM Domains from the APIC

        :param session: the instance of Session used for APIC communication
        :returns: List of VMM Domain objects
        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree&'
                      'target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)
        resp = []
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']
            resp.append(obj)
        return resp

    @classmethod
    def get_by_name(cls, session, infra_name):
        """
        Gets all of the VMM Domains from the APIC

        :param infra_name:
        :param session: the instance of Session used for APIC communication
        :returns: List of VMM Domain objects

        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree&'
                      'target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)

        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']

            if name == infra_name:
                return obj
        return None


class L2ExtDomain(BaseACIObject):
    """
    L2ExtDomain class
    """

    def __init__(self, name, parent):
        """
        :param name: String containing the L2ExtDomain name
        :param parent: An instance of DomP class representing
        """
        self.dn = None
        self.lcOwn = None
        self.childAction = None
        self.name = name
        super(L2ExtDomain, self).__init__(name, parent)

    def get_json(self):
        """
        Returns json representation of the l2extDomP object

        :returns: A json dictionary of fvTenant
        """
        attr = self._generate_attributes()
        return super(L2ExtDomain, self).get_json(self._get_apic_classes()[0],
                                                 attributes=attr)

    def _generate_attributes(self):
        """
        Gets the attributes used in generating the JSON for the object
        """
        attributes = dict()
        if self.name:
            attributes['name'] = self.name
        if self.dn:
            attributes['dn'] = self.dn
        if self.lcOwn:
            attributes['lcOwn'] = self.lcOwn
        if self.childAction:
            attributes['childAction'] = self.childAction
        return attributes

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['l2extDomP']

    def get_parent(self):
        """
        :returns: Parent of this object.
        """
        return self._parent

    @classmethod
    def get(cls, session):
        """
        Gets all of the L2Ext Domains from the APIC

        :param session: the instance of Session used for APIC communication
        :returns: List of L2ExtDomain objects

        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree&'
                      'target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)
        resp = []
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']
            resp.append(obj)
        return resp

    @classmethod
    def get_by_name(cls, session, infra_name):
        """
        Gets all of the Physical Domainss from the APIC

        :param infra_name:
        :param session: the instance of Session used for APIC communication
        :returns: List of L2ExtDomain objects

        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree&'
                      'target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)

        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']

            if name == infra_name:
                return obj
        return None


class L3ExtDomain(BaseACIObject):
    """
    L3ExtDomain class
    """

    def __init__(self, name, parent):
        """
        :param name: String containing the name of the external routed domain
        :param parent: An instance of DomP class
        """
        self.dn = None
        self.lcOwn = None
        self.childAction = None
        self.name = name
        super(L3ExtDomain, self).__init__(name, parent)

    def get_json(self):
        """
        Returns json representation of the fvTenant object

        :returns: A json dictionary of fvTenant
        """
        attr = self._generate_attributes()
        return super(L3ExtDomain, self).get_json(self._get_apic_classes()[0],
                                                 attributes=attr)

    def _generate_attributes(self):
        """
        Gets the attributes used in generating the JSON for the object
        """
        attributes = dict()
        if self.name:
            attributes['name'] = self.name
        if self.dn:
            attributes['dn'] = self.dn
        if self.lcOwn:
            attributes['lcOwn'] = self.lcOwn
        if self.childAction:
            attributes['childAction'] = self.childAction
        return attributes

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['l3extDomP']

    def get_parent(self):
        """
        :returns: Parent of this object.
        """
        return self._parent

    @classmethod
    def get(cls, session):
        """
        Gets all of the Physical Domains from the APIC

        :param session: the instance of Session used for APIC communication
        :returns: List of L3Ext Domain objects

        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree'
                      '&target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)
        resp = []
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']

            resp.append(obj)
        return resp

    @classmethod
    def get_by_name(cls, session, infra_name):
        """
        Gets all of the L3Ext Domains from the APIC

        :param infra_name:
        :param session: the instance of Session used for APIC communication
        :returns: List of L3Ext Domain objects

        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target=subtree&'
                      'target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)

        for object_data in data:
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.childAction = object_data[apic_class]['attributes']['childAction']

            if name == infra_name:
                return obj
        return None


class EPGDomain(BaseACIObject):
    """
    EPGDomain class
    """

    def __init__(self, name, parent):
        """
        :param name: String containing the name of a source relation to an
                     infrastructure domain profile associated with application
                     endpoint groups. The domain profile can be either a VMM
                     domain profile or a physical domain profile.
        :param parent: An instance of EPG class representing the EPG\
                       which contains this Domain Profile.
        """
        self.dn = None
        self.lcOwn = None
        self.tDn = None
        self.rType = None
        self.stateQual = None
        self.tCl = None
        self.triggerSt = None
        self.status = None
        self.state = None
        self.forceResolve = None
        self.instrImedcy = None
        self.monPolDn = None
        self.modTs = None
        self.uid = None
        self.tType = None
        self.resImedcy = None
        self.childAction = None
        self.domain_name = None
        self.domain_type = None
        self.tenant_name = None
        self.app_name = None
        self.epg_name = None

        super(EPGDomain, self).__init__(name, parent)

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['fvRsDomAtt']

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return None

    def get_json(self):
        """
        Returns json representation of the fvTenant object

        :returns: A json dictionary of fvTenant
        """
        attr = self._generate_attributes()
        for relation in self._relations:
            if isinstance(relation.item, EPG):
                if relation.item._dom_deployment_immediacy:
                    attr['instrImedcy'] = relation.item._dom_deployment_immediacy
                if relation.item._dom_resolution_immediacy:
                    attr['resImedcy'] = relation.item._dom_resolution_immediacy
        return super(EPGDomain, self).get_json(self._get_apic_classes()[0],
                                               attributes=attr)

    def _generate_attributes(self):
        """
        Gets the attributes used in generating the JSON for the object
        """

        attributes = dict()
        if self.dn:
            attributes['dn'] = self.dn
        # if self.lcOwn:
        #    attributes['lcOwn'] = self.lcOwn
        if self.tDn:
            attributes['tDn'] = self.tDn
        if self.rType:
            attributes['rType'] = self.rType
        if self.stateQual:
            attributes['stateQual'] = self.stateQual
        if self.tCl:
            attributes['tCl'] = self.tCl
        if self.triggerSt:
            attributes['triggerSt'] = self.triggerSt
        if self.status:
            attributes['status'] = self.status
        if self.state:
            attributes['state'] = self.state
        if self.forceResolve:
            attributes['forceResolve'] = self.forceResolve
        if self.instrImedcy:
            attributes['instrImedcy'] = self.instrImedcy
        if self.monPolDn:
            attributes['monPolDn'] = self.monPolDn
        if self.modTs:
            attributes['modTs'] = self.modTs
        if self.uid:
            attributes['uid'] = self.uid
        if self.tType:
            attributes['tType'] = self.tType
        if self.resImedcy:
            attributes['resImedcy'] = self.resImedcy
        if self.childAction:
            attributes['childAction'] = self.childAction

        return attributes

    def get_parent(self):
        """
        :returns: Parent of this object.
        """
        return self._parent

    @classmethod
    def get_by_name(cls, session, infra_name):
        """
        Gets all of the Physical Domains from the APIC

        :param infra_name:
        :param session: the instance of Session used for APIC communication
        :returns: List of Switch Profile objects

        """

        domain = PhysDomain.get_by_name(session, infra_name)

        if domain is None:
            domain = VmmDomain.get_by_name(session, infra_name)
            if domain is None:
                domain = L2ExtDomain.get_by_name(session, infra_name)
                if domain is None:
                    domain = L3ExtDomain.get_by_name(session, infra_name)
                    if domain is None:
                        return None

        toolkit_class = cls
        parent = None
        obj = toolkit_class(domain.name, parent)
        # apic_class = cls._get_apic_classes()[0]

        obj.tDn = domain.dn
        obj.lcOwn = domain.lcOwn
        obj.name = domain.name

        return obj

    @classmethod
    def get(cls, session):
        """
        Gets all of the Physical Domains from the APIC

        :param session: the instance of Session used for APIC communication
        :returns: List of Switch Profile objects

        """
        toolkit_class = cls
        apic_class = cls._get_apic_classes()[0]
        parent = None
        logging.debug('%s.get called', cls.__name__)
        query_url = (('/api/mo/uni.json?query-target='
                      'subtree&target-subtree-class=') + str(apic_class))
        ret = session.get(query_url)
        data = ret.json()['imdata']
        logging.debug('response returned %s', data)
        resp = []
        for object_data in data:
            name = str(object_data[apic_class]['attributes']['uid'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            obj.domain_name = object_data[apic_class]['attributes']['tDn'].split('/')[1].split('-')[1]
            obj.domain_type = object_data[apic_class]['attributes']['tDn'].split('/')[1].split('-')[0]
            obj.tenant_name = object_data[apic_class]['attributes']['dn'].split('/')[1].split('-')[1]
            obj.app_name = object_data[apic_class]['attributes']['dn'].split('/')[2].split('-')[1]
            obj.epg_name = object_data[apic_class]['attributes']['dn'].split('/')[3].split('-')[1]
            obj.dn = object_data[apic_class]['attributes']['dn']
            obj.lcOwn = object_data[apic_class]['attributes']['lcOwn']
            obj.tDn = object_data[apic_class]['attributes']['tDn']
            obj.rType = object_data[apic_class]['attributes']['rType']
            obj.tCI = object_data[apic_class]['attributes']['tCl']
            obj.triggerSt = object_data[apic_class]['attributes']['triggerSt']
            obj.status = object_data[apic_class]['attributes']['status']
            obj.state = object_data[apic_class]['attributes']['state']
            obj.forceResolve = object_data[apic_class]['attributes']['forceResolve']
            obj.instrImedcy = object_data[apic_class]['attributes']['instrImedcy']
            obj.monPolDn = object_data[apic_class]['attributes']['monPolDn']
            obj.modTs = object_data[apic_class]['attributes']['modTs']
            obj.uid = object_data[apic_class]['attributes']['uid']
            obj.tType = object_data[apic_class]['attributes']['tType']
            obj.resImedcy = object_data[apic_class]['attributes']['resImedcy']
            obj.childAction = object_data[apic_class]['attributes']['childAction']

            resp.append(obj)
        return resp

    def _get_instance_subscription_urls(self):
        url = '/api/mo/uni/phys-allvlans.json?subscription=yes'
        return [url]


class NetworkPool(BaseACIObject):
    """This class defines a pool of network ids
    """

    def __init__(self, name, encap_type, mode, start_id=None, end_id=None):
        super(NetworkPool, self).__init__(name)
        valid_encap_types = ['vlan', 'vxlan']
        if encap_type not in valid_encap_types:
            raise ValueError('Encap type specified is not a valid encap type')
        self.encap_type = encap_type
        self.start_id = start_id
        self.end_id = end_id
        valid_modes = ['static', 'dynamic', 'UOL_VXLAN']
        if mode not in valid_modes:
            raise ValueError('Mode specified is not a valid mode')
        self.mode = mode

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
        return '/api/mo/uni/infra.' + fmt

    def get_json(self):
        from_id = self.encap_type + '-' + self.start_id
        to_id = self.encap_type + '-' + self.end_id
        fvnsEncapBlk = {'fvnsEncapBlk': {'attributes': {'name': 'encap',
                                                        'from': from_id,
                                                        'to': to_id},
                                         'children': []}}
        pool_attributes = {'name': self.name}
        if self.encap_type == 'vlan':
            fvnsEncapInstP_string = 'fvnsVlanInstP'
            pool_attributes['allocMode'] = self.mode
        elif self.encap_type == 'vxlan':
            fvnsEncapInstP_string = 'fvnsVxlanInstP'
        fvnsEncapInstP = {fvnsEncapInstP_string: {'attributes': pool_attributes,
                                                  'children': [fvnsEncapBlk]}}
        if self.is_deleted():
            fvnsEncapInstP[fvnsEncapInstP_string]['attributes']['status'] = 'deleted'
        infra = {'infraInfra': {'attributes': {},
                                'children': [fvnsEncapInstP]}}
        return infra

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by the acitoolkit class.
        :returns: list of strings containing APIC class names
        """
        return ['fvnsVlanInstP', 'fvnsVxlanInstP']

    @classmethod
    def get(cls, session):
        """
        :param session: apic session
        :returns: list of network pools
        """
        toolkit_class = cls
        apic_classes = cls._get_apic_classes()

        logging.debug('%s.get called', cls.__name__)
        resp = []
        for ac in apic_classes:
            query_url = (('/api/mo/uni.json?query-target=subtree&'
                          'target-subtree-class=') + str(ac))
            ret = session.get(query_url)
            data = ret.json()['imdata']

            for object_data in data:
                if ac in object_data:
                    name = str(object_data[ac]['attributes']['name'])
                    dn = object_data[ac]['attributes']['dn']
                    encap_type = "vlan"
                    if ac == 'fvnsVxlanInstP':
                        encap_type = "vxlan"
                    mode = dn.split("-")[-1]
                    try:
                        obj = toolkit_class(name,encap_type,mode)
                    except ValueError:
                        pass
                    resp.append(obj)

        return resp


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
        """
        Get the URL of the VMM

        :return: string containing URL
        """
        return 'uni/vmmp-%s/dom-%s' % (self.vswitch_info.vendor,
                                       self.vswitch_info.vswitch_name)

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
        infraNsDn = 'uni/infra/%sns-[%s]-%s' % (self.network_pool.encap_type,
                                                self.network_pool.name,
                                                self.network_pool.mode)

        vmmDomP = {'vmmDomP': {'attributes': {'name': self.vswitch_info.vswitch_name},
                               'children': [vmmUsrAccP, vmmCtrlrP]}}
        if self.network_pool.encap_type == 'vlan':
            infraNsType = 'infraRsVlanNs'
        elif self.network_pool.encap_type == 'vxlan':
            infraNsType = 'infraRsVxlanNs'
        infraRsNs = {infraNsType: {'attributes': {'tDn': infraNsDn},
                                   'children': []}}
        if self.network_pool.encap_type == 'vlan':
            vmmDomP['vmmDomP']['children'].append(infraRsNs)
        else:
            vmmCtrlrP['vmmCtrlrP']['children'].append(infraRsNs)
        vmmProvP = {'vmmProvP': {'attributes': {'vendor': self.vswitch_info.vendor},
                                 'children': [vmmDomP]}}

        return vmmProvP

    @classmethod
    def get(cls, session):
        query_url = '/api/node/class/vmmDomP.json?query-target=subtree&rsp-subtree=full'
        ret = session.get(query_url)
        data = ret.json()['imdata']
        new_vmms = []
        for item in data:
            if 'vmmDomP' in item:
                dn = item['vmmDomP']['attributes'].get('dn')
                vendor = dn.rpartition('/vmmp-')[-1].partition('/')[0]
                dvs_name = item['vmmDomP']['attributes'].get('name')
                if 'children' in item['vmmDomP']:
                    for vmm in item['vmmDomP']['children']:
                        if 'vmmCtrlrP' in vmm:
                            # vmm_name = vmm['vmmCtrlrP']['attributes']['name']
                            vmm_ip = vmm['vmmCtrlrP']['attributes'].get('hostOrIp')
                            datacenter_name = vmm['vmmCtrlrP']['attributes'].get('rootContName')
                            vswitch_info = VMMvSwitchInfo(vendor, datacenter_name, dvs_name)
                            new_vmm = VMM(dvs_name, vmm_ip, None, vswitch_info, None)
                            # TODO: need to fill in NetworkPool if possible
                            new_vmms.append(new_vmm)
        return new_vmms


class Search(BaseACIObject):
    """This is an empty class used to create a search object for use with
       the "find" method.

       Attaching attributes to this class and then invoking find will return
       all objects with matching attributes in the object hierarchy at and
       below where the find is invoked.
    """

    def __init__(self):
        pass


class BaseMonitorClass(object):
    """ Base class for monitoring policies.  These are methods that can be
        used on all monitoring objects.
    """

    def set_name(self, name):
        """
        Sets the name of the MonitorStats.

       :param name: String to use as the name
        """
        self.name = str(name)
        self.modified = True

    def set_description(self, description):
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

        :param coll_obj:  A collection policy object of type CollectionPolicy
        """
        self.collection_policy[coll_obj.granularity] = coll_obj
        self.modified = True

    def remove_collection_policy(self, collection):
        """
        Remove a collection_policy object.  The object to remove is identified
        by its granularity, e.g. '5min', '15min', etc.  This string can be
        found in the 'CollectionPolicy.granularity' attribute of the object.

        :param collection: CollectionPolicy to remove.
        """
        if collection not in CollectionPolicy.granularityEnum:
            raise TypeError(('CollectionPolicy must be identified by its'
                             'granularity'))

        if collection in self.collection_policy:
            self.collection_policy.remove(collection)
            self.modified = True


class MonitorPolicy(BaseMonitorClass):
    """
    This class is the top-most container for a monitoring policy that controls
    how statistics are gathered. It has immediate children, CollectionPolicy
    objects, that control the default behavior for any network element that
    uses this monitoring policy.  It may optionally have MonitorTarget objects
    as children that are used to override the default behavior for a particular
    target class such as Interfaces.  There can be further granularity of
    control through children of the MonitorTarget sub-objects.

    Children of the MonitorPolicy will be CollectionPolicy objects that define
    the collection policy plus optional MonitorTarget objects that allow finer
    grained control over specific target APIC objects such as 'l1PhysIf' (layer
    1 physical interface).

    The CollectionPolicy children are contained in a dictionary called
    "collection_policy" that is indexed by the granulariy of the
    CollectionPolicy, e.g. '5min', '15min', etc.

    The MonitorTarget children are contained in a dictionary called
    "monitor_target" that is indexed by the name of the target object,
    e.g. 'l1PhysIf'.

    To make a policy take effect for a particular port, for example, you must
    attach that monitoring policy to the port.

    Note that the name of the MonitorPolicy is used to construct the dn of the
    object in the APIC.  As a result, the name cannot be changed.  If you read
    a policy from the APIC, change the name, and write it back, it will create
    a new policy with the new name and leave the old, original policy, in place
    with its original name.

    A description may be optionally added to the policy.
    """

    def __init__(self, policyType, name):
        """
        The MonitorPolicy is initialized with simply a policy type and a name.
        There are two policy types: 'fabric' and 'access'.  The 'fabric'
        monitoring policies can be applied to certain MonitorTarget types and
        'access' monitoring policies can be applied to other MonitorTarget
        types. Initially however, both policies can have l1PhysIf as targets.

        A name must be specified because it is used to build the distinguising
        name (dn) along with the policyType in the APIC.  The dn for "fabric"
        policies will be /uni/fabric/monfabric-[name] and for "access" policies
        it will be /uni/infra/moninfra-[name] in the APIC.

        :param policyType:  String specifying whether this is a fabric or\
                            access policy
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

        # assume that it has not been written to APIC.  This is cleared if the
        # policy is just loaded from APIC or the policy is written to the APIC.
        self.modified = True

    @classmethod
    def get(cls, session):
        """
        get() will get all of the monitor policies from the APIC and return
        them as a list.  It will get both fabric and access (infra) policies
        including default policies.

       :param session: the instance of Session used for APIC communication
       :returns: List of MonitorPolicy objects
        """
        result = []
        aciObjects = cls._getClass(session, 'monInfraPol')
        for data in aciObjects:
            name = str(data['monInfraPol']['attributes']['name'])
            policyObject = MonitorPolicy('access', name)
            policyObject.set_description(data['monInfraPol']['attributes']['descr'])
            cls._getPolicy(policyObject, session,
                           data['monInfraPol']['attributes']['dn'])
            result.append(policyObject)

        aciObjects = cls._getClass(session, 'monFabricPol')
        for data in aciObjects:
            name = str(data['monFabricPol']['attributes']['name'])
            policyObject = MonitorPolicy('fabric', name)
            policyObject.set_description(data['monFabricPol']['attributes']['descr'])
            cls._getPolicy(policyObject, session,
                           data['monFabricPol']['attributes']['dn'])
            result.append(policyObject)
        return result

    @staticmethod
    def _getClass(session, aciClass):
        """
        Get the class from the APIC

        :param session: Session object instance
        :param aciClass: string containing classname
        :return: JSON dictionary containing class instances
        """
        prefix = '/api/node/class/'
        suffix = '.json?query-target=self'
        class_query_url = prefix + aciClass + suffix
        ret = session.get(class_query_url)
        data = ret.json()['imdata']
        return data

    @classmethod
    def _getPolicy(cls, policyObject, session, dn):
        """
        Get the policy

        :param policyObject: policyObject
        :param session: Session class instance
        :param dn: string containing the distinguished name
        :return: None
        """
        children = cls._getChildren(session, dn)
        for child in children:
            if child[0] == 'statsHierColl':
                granularity = str(child[1]['attributes']['granularity'])
                adminState = str(child[1]['attributes']['adminState'])
                retention = str(child[1]['attributes']['histRet'])
                collPolicy = CollectionPolicy(policyObject, granularity,
                                              retention, adminState)
                collPolicy.set_name(child[1]['attributes']['name'])
                collPolicy.set_description(child[1]['attributes']['descr'])

            if child[0] in ['monFabricTarget', 'monInfraTarget']:
                scope = str(child[1]['attributes']['scope'])

                # initially only l1PhysIf is supported as a target
                if scope == 'l1PhysIf':
                    target = MonitorTarget(policyObject, scope)
                    target.set_name(str(child[1]['attributes']['name']))
                    target.set_description(str(child[1]['attributes']['descr']))
                    dn = child[1]['attributes']['dn']
                    targetChildren = cls._getChildren(session, dn)
                    for targetChild in targetChildren:
                        if targetChild[0] == 'statsReportable':
                            scope = str(targetChild[1]['attributes']['scope'])
                            scope = MonitorStats.statsDictionary[scope]
                            statFamily = MonitorStats(target, scope)
                            child_attr = targetChild[1]['attributes']
                            statFamily.set_name(str(child_attr['name']))
                            statFamily.set_description(str(child_attr['name']))
                            dn = targetChild[1]['attributes']['dn']
                            statChildren = cls._getChildren(session, dn)
                            for statChild in statChildren:
                                if statChild[0] == 'statsColl':
                                    child_stats = statChild[1]['attributes']
                                    granularity = str(child_stats['granularity'])
                                    adminState = str(child_stats['adminState'])
                                    retention = str(child_stats['histRet'])
                                    collPolicy = CollectionPolicy(statFamily,
                                                                  granularity,
                                                                  retention,
                                                                  adminState)
                                    collPolicy.set_name(child_stats['name'])
                                    collPolicy.set_description(child_stats['descr'])
                        if targetChild[0] == 'statsHierColl':
                            child_attr = targetChild[1]['attributes']
                            granularity = str(child_attr['granularity'])
                            adminState = str(child_attr['adminState'])
                            retention = str(child_attr['histRet'])
                            collPolicy = CollectionPolicy(target,
                                                          granularity,
                                                          retention,
                                                          adminState)
                            collPolicy.set_name(child_attr['name'])
                            collPolicy.set_description(child_attr['descr'])

    @classmethod
    def _getChildren(cls, session, dn):
        """
        Get the children

        :param session: Session instance object
        :param dn: string containing the distinguished name
        :return: json dictionary containing the children objects
        """
        result = []
        mo_query_url = '/api/mo/' + dn + '.json?query-target=children'
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
        return self.policyType + ':' + self.name

    def flat(self, target='l1PhysIf'):
        """
        This method will return a data structure that is a flattened version
        of the monitor policy. The flattened version is one that walks through
        the heirarchy of the policy and determines the administrative state and
        retention policy for each granularity of each statistics family.
        This is done for the target specified, i.e. 'l1PhysIf'

        For example, if 'foo' is a MonitorPolicy object, then
        flatPol = foo.flat('l1PhysIf') will return a dictionary that looks like
        the following:

        adminState = flatPol['counter_family']['granularity'].adminState
        retention = flatPol['counter_family']['granularity'].retention

        The dictionary will have all of the counter families for all of the
        granularities and the value returned is the administrative state and
        retention value that is the final result of resolving the policy
        hierarchy.

        :param target:  APIC target object.  This will default to 'l1PhysIf'
        :returns: Dictionary of statistic administrative state and retentions
                  indexed by counter family and granularity.
        """

        class Policy(object):
            """
            Policy class
            """

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

        target_stats = targetPolicy.monitor_stats
        for statFamily in target_stats:
            collection_pol = target_stats[statFamily].collection_policy
            for granularity in collection_pol:
                retention = collection_pol[granularity].retention
                adminState = collection_pol[granularity].adminState

                if adminState != 'inherited':
                    result[statFamily][granularity].adminState = adminState
                if retention != 'inherited':
                    result[statFamily][granularity].retention = retention

        # if the lesser granularity is disabled, then the larger granularity
        # is as well
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
    This class is a child of a MonitorPolicy object. It is used to specify a
    scope for appling a monitoring policy.  An example scope would be the
    Interface class, meaning that the monitoring policies specified here will
    apply to all Interface clas objects (l1PhysIf in the APIC) that use the
    parent MonitoringPolicy as their monitoring policy.

    Children of the MonitorTarget will be CollectionPolicy objects that define
    the collection policy for the specified target plus optional MonitorStats
    objects that allow finer grained control over specific families of
    statistics such as ingress packets, ingrPkts.

    The CollectionPolicy children are contained in a dictionary called
    "collection_policy" that is indexed by the granularity of the
    CollectionPolicy, e.g. '5min', '15min', etc.

    The MonitorStats children are contained in a dictionary called
    "monitor_stats" that is indexed by the name of the statistics family,
    e.g. 'ingrBytes', 'ingrPkts', etc.
    """

    def __init__(self, parent, target):
        """
        The MonitorTarget object is initialized with a parent of type
        MonitorPolicy, and a target string. Initially, this toolkit only
        supports a target of type 'l1PhysIf'.  The 'l1PhyIf' target is a layer
        1 physical interface or "port".  The MonitorTarget will narrow the
        scope of the policy specified by the children of the MonitorTarget to
        be only the target class.

       :param parent:  Parent object that this monitor target is a child.
                       It must be of type MonitorPolicy
       :param target:  String specifying the target class for the Monitor
                       policy.
        """
        targetEnum = ['l1PhysIf']
        if not type(parent) in [MonitorPolicy]:
            raise TypeError(('Parent of MonitorTarget must be one of type'
                             ' MonitorPolicy'))
        if target not in targetEnum:
            raise ValueError('target must be one of:', targetEnum)

        self._parent = parent
        self.scope = target
        self.descr = ''
        self.name = ''
        self._parent.add_target(self)
        self.collection_policy = {}
        self.monitor_stats = {}
        # assume that it has not been written to APIC.
        # This is cleared if the policy is just loaded from APIC
        # or the policy is written to the APIC.
        self.modified = True

    def __str__(self):
        return self.scope


class MonitorStats(BaseMonitorClass):
    """
    This class is a child of a MonitorTarget object.  It is used to specify
    a scope for applying a monitoring policy that is more fine grained than
    the MonitorTarget.  Specifically, the MonitorStats object specifies a
    statistics family such as "ingress packets" or "egress bytes".
    """
    statsDictionary = {'eqptEgrBytes': 'egrBytes',
                       'eqptEgrPkts': 'egrPkts',
                       'eqptEgrTotal': 'egrTotal',
                       'eqptEgrDropPkts': 'egrDropPkts',
                       'eqptIngrBytes': 'ingrBytes',
                       'eqptIngrPkts': 'ingrPkts',
                       'eqptIngrTotal': 'ingrTotal',
                       'eqptIngrDropPkts': 'ingrDropPkts',
                       'eqptIngrUnkBytes': 'ingrUnkBytes',
                       'eqptIngrUnkPkts': 'ingrUnkPkts',
                       'eqptIngrStorm': 'ingrStorm'}

    statsFamilyEnum = ['egrBytes', 'egrPkts', 'egrTotal', 'egrDropPkts',
                       'ingrBytes', 'ingrPkts', 'ingrTotal', 'ingrDropPkts',
                       'ingrUnkBytes', 'ingrUnkPkts', 'ingrStorm']

    def __init__(self, parent, statsFamily):
        """
        The MonitorStats object must always be initialized with a parent object
        of type MonitorTarget. It sets the scope of its children collection
        policies (CollectionPolicy) to a particular statistics family.

        The MonitorStats object contains a dictionary of collection policies
        called collection_policy.  This is a dictionary of children
        CollectionPolicy objects indexed by their granularity, e.g. '5min',
        '15min', etc.

       :param parent: Parent object that this monitor stats object should be\
                      applied to. This must be an object of type MonitorTarget.
       :param statsFamily: String specifying the statistics family that the\
                           children collection policies should be applied to.\
                           Possible values are:['egrBytes', 'egrPkts',\
                           'egrTotal', 'egrDropPkts', 'ingrBytes', 'ingrPkts',\
                           'ingrTotal', 'ingrDropPkts', 'ingrUnkBytes',\
                           'ingrUnkPkts', 'ingrStorm']
        """
        if not type(parent) in [MonitorTarget]:
            raise TypeError(('Parent of MonitorStats must be one of type '
                             'MonitorTarget'))
        if statsFamily not in MonitorStats.statsFamilyEnum:
            raise ValueError('statsFamily must be one of:', MonitorStats.statsFamilyEnum)

        self._parent = parent
        self.scope = statsFamily
        self.descr = ''
        self.name = ''
        self._parent.add_stats(self)
        self.collection_policy = {}
        # assume that it has not been written to APIC.  This is cleared if
        # the policy is just loaded from APIC or the policy is written to
        # the APIC.
        self.modified = True

    def __str__(self):
        return self.scope


class CollectionPolicy(BaseMonitorClass):
    """
    This class is a child of a MonitorPolicy object, MonitorTarget object or
    a MonitorStats object.  It is where the statistics collection policy is
    actually specified.  It applies to all of the statistics that are at the
    scope level of the parent object,
    i.e. all, specific to a target, or specific to a statistics family.  What
    is specified in the CollectionPolicy is the time granularity of the
    collection and how much history to retain.  For example, the granularity
    might be 5 minutes (5min) or 1 hour (1h).  How much history to retain is
    similarly specified.  For example you might specify that it be kept for
    10 days (10d) or 2 years (2year).

    If the CollectionPolicy is a child of a MonitorStats object, it can
    optionally have children that specify the policy for raising threshold
    alarms on the fields in the stats family specified in the MonitorStats
    object.  This has yet to be implemented.

    This object is roughly the same as the statsColl and statsHierColl objects
    in the APIC.
    """
    # this must be in order from small to large
    granularityEnum = ['5min', '15min', '1h', '1d',
                       '1w', '1mo', '1qtr', '1year']
    retentionEnum = ['none', 'inherited', '5min', '15min', '1h', '1d',
                     '1w', '10d', '1mo', '1qtr', '1year', '2year', '3year']

    def __init__(self, parent, granularity, retention, adminState='enabled'):
        """
        The CollectionPolicy must always be initialized with a parent object of
        type MonitorPolicy, MonitorTarget or MonitorStats. The granularity must
        also be specifically specified.  The retention period can be specified,
        set to "none", or set to "inherited".
        Note that the "none" value is a string, not the Python None.  When the
        retention period is set to "none" there will be no historical stats
        kept. However, assuming collection is enabled, stats will be kept for
        the current time period.

        If the retention period is set to "inherited", the value will be
        inherited from the less specific policy directly above this one. The
        same applies to the adminState value.  It can be 'disabled', 'enabled',
        or 'inherited'.  If 'disabled', the current scope of counters are not
        gathered.  If enabled, they are gathered.  If 'inherited', it will be
        according to the next higher scope.

        Having the 'inherited' option on the retention and administrative
        status allows these items independently controlled at the current
        stats granularity.  For example, you can specify that ingress unknown
        packets are gathered every 15 minutes by setting adding a collection
        policy that specifies a 15 minutes granularity and an adminState of
        'enabled' under a MonitorStats object that sets the scope to be ingress
        unknown packets.  This might override a higher level policy that
        disabled collection at a 15 minute interval.   However, you can set the
        retention in that same object to be "inherited" so that this specific
        policy does not change the retention behavior from that of the higher,
        less specific, policy.

        When the CollectionPolicy is a child at the top level, i.e. of the
        MonitorPolicy, the 'inherited' option is not allowed because there
        is no higher level policy to inherit from.  If this were to happen,
        'inherited' will be treated as 'enabled'.

       :param parent: Parent object that this collection policy should be
                      applied to. This must be an object of type MonitorStats,
                      MonitorTarget, or MonitorPolicy.
       :param granularity:  String specifying the time collection interval or
                            granularity of this policy.  Possible values are:
                            ['5min', '15min', '1h', '1d', '1w', '1mo', '1qtr',
                            '1year'].
       :param retention: String specifying how much history to retain the
                         collected statistics for.  The retention will be for
                         time units of the granularity specified.  Possible
                         values are ['none', 'inherited', '5min', '15min',
                         '1h', '1d', '1w', '10d', '1mo', '1qtr', '1year',
                         '2year', '3year'].
       :param adminState:  Administrative status.  String to specify whether
                           stats should be collected at the specified
                           granularity.  Possible values are ['enabled',
                           'disabled', 'inherited'].  The default if not
                           specified is 'enabled'.
        """
        adminStateEnum = ['enabled', 'disabled', 'inherited']

        if type(parent) not in [MonitorStats, MonitorTarget, MonitorPolicy]:
            raise TypeError(('Parent of collection policy must be one of '
                             'MonitorStats, MonitorTarget, or MonitorPolicy'))
        if granularity not in CollectionPolicy.granularityEnum:
            raise ValueError('granularity must be one of:',
                             CollectionPolicy.granularityEnum)
        if retention not in CollectionPolicy.retentionEnum:
            raise ValueError('retention must be one of:',
                             CollectionPolicy.retentionEnum)
        if adminState not in adminStateEnum:
            raise ValueError('adminState must be one of:',
                             CollectionPolicy.adminStateEnum)

        self._parent = parent
        self.granularity = granularity

        self.retention = retention
        self.adminState = adminState
        self._children = []

        self._parent.add_collection_policy(self)
        # assume that it has not been written to APIC.  This is cleared if
        # the policy is just loaded from APIC or the policy is written to
        # the APIC.
        self.modified = True

    def __str__(self):
        return self.granularity

    def setAdminState(self, adminState):
        """
        Sets the administrative status.

        :param adminState:  Administrative status.  String to specify whether
                            stats should be collected at the specified
                            granularity.  Possible values are ['enabled',
                            'disabled', 'inherited'].  The default if not
                            specified is 'enabled'.
        """
        if self.adminState != adminState:
            self.modified = True

        self.adminState = adminState

    def setRetention(self, retention):
        """
        Sets the retention period.

       :param retention: String specifying how much history to retain the
                         collected statistics for.  The retention will be for
                         time units of the granularity specified.  Possible
                         values are ['none', 'inherited', '5min', '15min',
                         '1h', '1d', '1w', '10d', '1mo', '1qtr', '1year',
                         '2year', '3year'].
        """
        if self.retention != retention:
            self.modified = True

        self.retention = retention


class Tag(_Tag):
    """
    Tag class.
    """
    @classmethod
    def get(cls, session, parent=None, tenant=None):
        """Gets all of the Tags from the APIC.

        :param session: the instance of Session used for APIC communication
        :param parent: Instance of the possible Tag parent classes used to limit the Tags\
                       retreived from the APIC.
        :param tenant: Instance of Tenant class used to limit the Tags\
                       retreived from the APIC.
        :returns: List of Tag instances
        """
        return BaseACIObject.get(session, cls, cls._get_apic_classes()[0],
                                 parent=parent, tenant=tenant,query_target_type='children')
    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return [EPG, Contract, Tenant, OutsideEPG, OutsideL2, OutsideL3, BridgeDomain, Context, Filter]


class LogicalModel(BaseACIObject):
    """
    This is the root class for the logical part of the network.  Its corollary is the PhysicalModel class.
    It is a container that can hold all of logical model instances such as Tenants.

    From this class, you can populate all of the children classes.
    """

    def __init__(self, session=None, parent=None):
        """
        Initialization method that sets up the Fabric.
        :return:
        """
        if session:
            assert isinstance(session, Session)

        # if parent:
        #     assert isinstance(parent, Fabric)

        super(LogicalModel, self).__init__(name='', parent=parent)

        self._session = session
        self.dn = 'logical'

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Fabric

    @classmethod
    def _get_name_from_dn(cls, dn):
        """
        Parse the name out of a dn string.
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing name
        """
        return None

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return None

    @classmethod
    def get(cls, session=None, parent=None):
        """
        Method to get all of the LogicalModels.  It will get one and return it in a list.

        :param session:
        :param parent:
        :return: list of LogicalModel
        """
        logical_model = LogicalModel(session=session, parent=parent)
        return [logical_model]

    @staticmethod
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return [Tenant]

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by the acitoolkit class.
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: list of strings containing APIC class names
        """
        return []

    def populate_children(self, deep=False, include_concrete=False):
        """
        Populates all of the children and then calls populate_children\
        of those children if deep is True.  This method should be\
        overridden by any object that does have children.

        If include_concrete is True, then if the object has concrete objects
        below it, i.e. is a switch, then also populate those conrete object.

        :param include_concrete: True or False. Default is False
        :param deep: True or False.  Default is False.
        """
        for child_class in self._get_children_classes():
            if deep:
                child_class.get_deep(self._session, parent=self)
            else:
                child_class.get(self._session, self)

        return self._children

    def _define_searchables(self):
        """
        Create all of the searchable terms

        """
        results = super(LogicalModel, self)._define_searchables()
        results[0].add_term('model', 'logical')

        return results


def build_object_dictionary(objs):
    """
    Will build a dictionary indexed by object class that contains all the objects of that class

    :param objs:
    :return:
    """
    result = {}
    for obj in objs:
        obj_class = obj.__class__
        if obj_class not in result:
            result[obj_class] = set()

        result[obj_class].add(obj)
        children = obj.get_children()
        children_result = build_object_dictionary(children)
        for child_class in children_result:
            if child_class not in result:
                result[child_class] = set()
            result[child_class] = result[child_class] | children_result[child_class]
    return result
