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
"""ACI Toolkit module for physical objects
"""

from acibaseobject import BaseACIObject
from acisession import Session
import acitoolkit as ACI
from acicounters import AtomicCountersOnGoing

import logging
import re
import copy


class BaseACIPhysObject(BaseACIObject):
    """Base class for physical objects
    """
    def _common_init(self, parent):
        """
        Common init used for all physical objects
        """
        self._deleted = False
        self._parent = parent
        self._children = []
        self._relations = []
        self._session = None
        if self._parent is not None:
            self._parent.add_child(self)

    def _delete_redundant_policy(self, infra, policy_type):
        """
        Removes redundant policies
        """
        policies = []
        for idx, child in enumerate(infra['infraInfra']['children']):
            if policy_type in child:
                policy_name = child[policy_type]['attributes']['name']
                if policy_name in policies:
                    del infra['infraInfra']['children'][idx]
                else:
                    policies.append(policy_name)
        return infra

    def _combine_json(self, data, other):
        """
        Combines the json
        """
        if len(data) == 0:
            return other
        if len(other) == 0:
            return data
        phys_domain, fabric, infra = data
        other_phys_domain, other_fabric, other_infra = other
        infra['infraInfra']['children'].extend(other_infra['infraInfra']
                                               ['children'])

        # Remove duplicate named policies
        for item in infra['infraInfra']['children']:
            for key in item:
                if 'name' in item[key]['attributes']:
                    self._delete_redundant_policy(infra, key)

        # Combine all of the infraFuncP items
        first_occur = None
        for idx, child in enumerate(infra['infraInfra']['children']):
            if 'infraFuncP' in child:
                if first_occur is None:
                    first_occur = idx
                else:
                    for other_child in child['infraFuncP']['children']:
                        infra['infraInfra']['children'][first_occur]\
                            ['infraFuncP']['children'].append(other_child)
                    del infra['infraInfra']['children'][idx]
        return(phys_domain, fabric, infra)

    def get_json(self):
        """Returns json representation of the object

        :returns: JSON of contained Interfaces
        """
        data = []
        for child in self.get_children():
            other = child.get_json()
            if other is not None:
                data = self._combine_json(data, other)
        if len(data) == 0:
            return None
        return data

    def get_url(self, fmt='json'):
        """Get the URL used to push the configuration to the APIC
        if no fmt parameter is specified, the format will be 'json'
        otherwise it will return '/api/mo/uni.' with the fmt string appended.

        :param fmt: optional fmt string
        :returns: Nothing - physical objects are not modifiable
        """
        pass

    def add_child(self, child_obj):
        """Add a child to the children list. All children must be unique so it
        will first delete the child if it already exists.

        :param child_obj: a child object to be added as a child to this object.
                          This will be put into the _children list.

        :returns: None
        """
        if self.has_child(child_obj):
            self.remove_child(child_obj)
        self._children.append(child_obj)

    def get_children(self, childType=None):
        """Returns the list of children.  If childType is provided, then
        it will return all of the children of the matching type.

        :param childType: This optional parameter will cause this method to\
                        return only those children\
                        that match the type of childType.  If this parameter\
                        is ommitted, then all of the children will be returned.

        :returns: list of children
        """
        if childType:
            children = []
            for child in self._children:
                if isinstance(child, childType):
                    children.append(child)
            return children
        else:
            return self._children

    @classmethod
    def exists(cls, session, phys_obj):
        """Check if an apic phys_obj exists on the APIC.
        Returns True if the phys_obj does exist.

        :param session: APIC session to use when accessing the APIC controller.
        :param phys_obj: The object that you are checking for.
        :returns: True if the phys_obj exists, False if it does not.
        """
        apic_nodes = cls.get(session)
        for apic_node in apic_nodes:
            if phys_obj == apic_node:
                return True
        return False

    def get_type(self):
        """Gets physical object type

        :returns: type string of the object.
        """
        return self.type

    def get_pod(self):
        """Gets pod_id
        :returns: id of pod
        """
        return self.pod

    def get_node(self):
        """Gets node id

        :returns: id of node
        """
        return self.node

    def get_name(self):
        """Gets name.

        :returns: Name string
        """
        return self.name

    def get_serial(self):
        """Gets serial number.

        :returns: serial number string
        """
        return None


class BaseACIPhysModule(BaseACIPhysObject):
    """BaseACIPhysModule: base class for modules  """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.

            :param pod: pod id of module
            :param node: node id of module
            :param slot: slot id of module
            :param parent: optional parent object
        """

        # check that parent is a node
        if parent:
            if not isinstance(parent, Node):
                raise TypeError('An instance of Node class is required')

        self.pod = str(pod)
        self.node = str(node)
        self.slot = str(slot)
        self.serial = None
        self.model = None
        self.dn = None
        self.descr = None
        self.bios = None
        self.firmware = None

        self._apic_class = None
        self.dn = None
        self._session = None

        logging.debug('Creating %s %s', self.__class__.__name__,
                      'pod-' + self.pod + '/node-' + self.node + '/slot-' + self.slot)
        self._common_init(parent)

    def get_slot(self):
        """Gets slot id

        :returns: slot id
        """
        return self.slot

    def __eq__(self, other):
        """ Two modules are considered equal if their class type is the same
        and pod, node, slot, type all match.
        """
        if type(self) is not type(other):
            return False
        return (self.pod == other.pod) and (self.node == other.node) and \
            (self.slot == other.slot) and (self.type == other.type)

    @staticmethod
    def _parse_dn(dn):
        """Parses the pod, node, and slot from a
           distinguished name of the node.

           :param dn: str - distinguished name

           :returns: pod, node, slot strings
        """
        name = dn.split('/')
        pod = str(name[1].split('-')[1])
        node = str(name[2].split('-')[1])
        slot = str(name[5].split('-')[1])
        return pod, node, slot

    @classmethod
    def get_obj(cls, session, apic_class, parent):
        """Gets all of the Nodes from the APIC.  This is called by the
        module specific get() methods.  The parameters passed include the
        APIC object class, apic_class, so that this will work for
        different kinds of modules.

        :param session: APIC session to use when retrieving the nodes
        :param apic_class: The object class in APIC to retrieve
        :param parent: The parent object of this object
        :returns: list of module objects derived from the specified apic_class

        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        interface_query_url = ('/api/node/class/' + apic_class + '.json?'
                               'query-target=self')
        cards = []
        ret = session.get(interface_query_url)
        card_data = ret.json()['imdata']
        for apic_obj in card_data:
            dist_name = str(apic_obj[apic_class]['attributes']['dn'])
            (pod, node_id, slot) = cls._parse_dn(dist_name)
            card = cls(pod, node_id, slot)
            card._session = session
            card._apic_class = apic_class
            card._populate_from_attributes(apic_obj[apic_class]['attributes'])
            card._more_populate_from_attributes(
                apic_obj[apic_class]['attributes'])
            (card.firmware, card.bios) = card._get_firmware(dist_name)
            card.dn = dist_name
            card.start_time = str(apic_obj[apic_class]['attributes']['modTs'])
            card.node = node_id
            card.pod = pod
            card.slot = slot
            card._parent = parent
            if parent:
                if card.node == parent.node:
                    if card._parent.has_child(card):
                        card._parent.remove_child(card)
                    card._parent.add_child(card)
                    cards.append(card)
            else:
                cards.append(card)
        return cards

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = str(attributes['ser'])
        self.model = str(attributes['model'])
        self.dn = str(attributes['dn'])
        self.descr = str(attributes['descr'])

    def _more_populate_from_attributes(self, attributes):
        """Fills in an object with the additional attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.type = str(attributes['type'])

    def _get_firmware(self, dist_name):
        """Gets the firmware and bios version for the module from the "running" object in APIC.

        :param dist_name: dn of module, a string

        :returns: firmware, bios
        """
        mo_query_url = '/api/mo/' + dist_name + '/running.json?query-target=self'
        ret = self._session.get(mo_query_url)
        node_data = ret.json()['imdata']
        if node_data:
            firmware = str(node_data[0]['firmwareCardRunning']['attributes']['version'])
            bios = str(node_data[0]['firmwareCardRunning']['attributes']['biosVer'])
        else:
            firmware = None
            bios = None
        return (firmware, bios)

    def get_serial(self):
        """Returns the serial number.
        :returns: serial number string
        """
        return self.serial


class Systemcontroller(BaseACIPhysModule):
    """ class of the motherboard of the APIC controller node   """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create the name
        of the Systemcontroller and set the type
        before calling the base class __init__ method.

        :param pod: pod id
        :param node: node id
        :param slot: slot id
        :param parent: optional parent object

        """
        self.name = 'SysC-' + '/'.join([pod, node, slot])
        self.type = 'systemctrlcard'
        super(Systemcontroller, self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the System controllers from the APIC.
        This information comes from
        the APIC 'eqptBoard' class.

        If parent is specified, it will only get system
        controllers that are children of the the parent.
        The system controlles will also be added as children
        to the parent Node.

        :param session: APIC session
        :param parent: parent Node

        :returns: list of Systemcontrollers
        """
        # need to add pod as parent
        return cls.get_obj(session, 'eqptBoard', parent)

    @staticmethod
    def _parse_dn(dn):
        """Parses the pod, node from a
           distinguished name of the node and fills in the slot to be '1'

           :param dn: dn of node

           :returns: pod, node, slot
        """
        name = dn.split('/')
        pod = str(name[1].split('-')[1])
        node = str(name[2].split('-')[1])
        slot = '1'
        return pod, node, slot

    def _get_firmware(self, dn):
        """Gets the firmware version of the System controller
        from the firmwareCtrlrRunning attribute of the
        ctrlrrunning object under the ctrlrfwstatuscont object.
        It will set the bios to None.

        :param dn: dn of node

        :returns: firmware, bios
        """
        name = dn.split('/')
        new_dist_name = '/'.join(name[0:4])

        mo_query_url = '/api/mo/' + new_dist_name + \
            '/ctrlrfwstatuscont/ctrlrrunning.json?query-target=self'
        ret = self._session.get(mo_query_url)
        node_data = ret.json()['imdata']

        if node_data:
            firmware = str(node_data[0]['firmwareCtrlrRunning']['attributes']['version'])
        else:
            firmware = None

        bios = None
        return (firmware, bios)

    def _more_populate_from_attributes(self, attributes):
        """Fills in the System controller with additional attributes.
        """
        self.type = str(attributes['type'])

        # I think this is a bug fix to the APIC controller.  The type should be set correctly.
        if self.type == 'unknown':
            self.type = 'systemctrlcard'


class Linecard(BaseACIPhysModule):
    """ class for a linecard of a switch   """
    def __init__(self, arg0=None, arg1=None, slot=None, parent=None):
        """Initialize the basic object.  It will create the
        name of the linecard and set the type
        before calling the base class __init__ method.
        If arg1 is an instance of a Node, then pod,
        and node are derived from the Node and the slot_id
        is from arg0.  If arg1 is not a Node, then arg0
        is the pod, arg1 is the node id, and slot is the slot_id

        In other words, this Linecard object can either be initialized by

          >>> lc = Linecard(slot_id, parent_switch)

        or

          >>> lc = Linecard(pod_id, node_id, slot_id)

        or

          >>> lc = Linecard(pod_id, node_id, slot_id, parent_switch)

        :param arg0: pod_id if arg1 is a node_id, slot_id if arg1 is of type Node
        :param arg1: node_id string or parent Node of type Node
        :param slot: slot_id if arg1 is node_id  Not required if arg1 is a Node
        :param parent: parent switch of type Node.  Not required if arg1 is used instead.

        :returns: None
        """
        if isinstance(arg1, Node):
            slot_id = arg0
            pod = arg1.pod
            node = arg1.node
            parent = arg1
        else:
            slot_id = slot
            pod = arg0
            node = arg1

        self.name = 'Lc-' + '/'.join([str(pod), str(node), str(slot_id)])
        self.type = 'linecard'
        super(Linecard, self).__init__(pod, node, slot_id, parent)

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the linecards from the APIC.  If parent is
        specified, it will only get linecards that are
        children of the the parent.  The linecards will also
        be added as children to the parent Node.

        The lincard object is derived mostly from the APIC 'eqptLC' class.

        :param session: APIC session
        :param parent: optional parent of class Node

        :returns: list of linecards
        """
        return cls.get_obj(session, 'eqptLC', parent)

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = str(attributes['ser'])
        self.model = str(attributes['model'])
        self.descr = str(attributes['descr'])
        self.num_ports = str(attributes['numP'])
        self.hardware_version = str(attributes['hwVer'])
        
    def populate_children(self, deep=False):
        """Populates all of the children of the linecard.  Children are the interfaces.
        If deep is set to true, it will also try to populate the children of the children.

        :param deep: boolean that when true will cause the entire sub-tree to be populated\
            when false, only the immediate children are populated

        :returns: None
        """

        # The following will add the interfaces to the linecard
        ACI.Interface.get(self._session, self)
        
        if deep:
            for child in self._children:
                child.populate_children(deep=True)

        return None


class Supervisorcard(BaseACIPhysModule):
    """Class representing the supervisor card of a switch
    """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.

            :param pod: pod id
            :param node: node id
            :param slot: slot id
            :param parent: optional parent object
        """
        self.name = 'SupC-' + '/'.join([pod, node, slot])
        self.type = 'supervisor'
        super(Supervisorcard, self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the supervisor cards from the APIC.
        If parent is specified, it will only get the
        supervisor card that is a child of the the parent Node.
        The supervisor will also be added as a child to the parent Node.

        The Supervisorcard object is derived mostly from the
        APIC 'eqptSupC' class.

        :param session: APIC session
        :param parent: optional parent switch of class Node

        :returns: list of linecards
        """
        return cls.get_obj(session, 'eqptSupC', parent)


class Fantray(BaseACIPhysModule):
    """Class for the fan tray of a node"""
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create
        the name of the fan tray and set the type
        before calling the base class __init__ method
        :param pod: pod id
        :param node: node id
        :param slot: slot id
        :param parent: optional parent object
        """
        self.name = 'Fan-' + '/'.join([pod, node, slot])
        self.type = 'fantray'
        self.status = None
        super(Fantray, self).__init__(pod, node, slot, parent)


    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the fantrays from the APIC.  If parent
        is specified, it will only get fantrays that are
        children of the the parent.  The fantrays will
        also be added as children to the parent Node.

        The fantray object is derived mostly from the APIC 'eqptFt' class.

        :param session: APIC session
        :param parent: optional parent switch of class Node

        :returns: list of fantrays
        """
        return cls.get_obj(session, 'eqptFt', parent)

    def _more_populate_from_attributes(self, attributes):
        """Fills in an object with additional attributes.
         """
        self.status = str(attributes['operSt'])

    @staticmethod
    def _get_firmware(dist_name):
        """ Returns None for firmware and bios revisions"""
        return (None, None)

    def populate_children(self, deep=False):
        """Populates all of the children of the fantray.
        Since the fantray has no children,
        this will return none.

        :param deep: boolean that when true will cause the
                     entire sub-tree to be populated
                     when false, only the immediate
                     children are populated

        :returns: None
        """
        return None


class Powersupply(BaseACIPhysModule):
    """ class for a power supply in a node   """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create
        the name of the powersupply and set the type
        before calling the base class __init__ method
        :param pod: pod id
        :param node: node id
        :param slot: slot id
        :param parent: optional parent object
        """
        self.name = 'PS-' + '/'.join([pod, node, slot])
        self.type = 'powersupply'
        self.status = None
        self.voltage_source = None
        self.fan_status = None
        super(Powersupply, self).__init__(pod, node, slot, parent)


    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the power supplies from the APIC.
        If parent is specified, it will only get power supplies that are
        children of the the parent.  The power supplies
        will also be added as children to the parent Node.

        The Powersupply object is derived mostly from the APIC 'eqptPsu' class.

        :param session: APIC session
        :param parent: optional parent switch of class Node

        :returns: list of powersupplies
        """
        return cls.get_obj(session, 'eqptPsu', parent)

    def _more_populate_from_attributes(self, attributes):
        """Fills in an object with additional desired attributes.
        """
        self.status = str(attributes['operSt'])
        self.fan_status = str(attributes['fanOpSt'])
        self.voltage_source = str(attributes['vSrc'])

    @staticmethod
    def _get_firmware(dist_name):
        """ The power supplies do not have a readable firmware or bios revision so
        this will return None for firmware and bios revisions"""

        return (None, None)

    def populate_children(self, deep=False):
        """Populates all of the children of the power supply.
        Since the power supply has no children,
        this will return none.

        :param deep: boolean that when true will cause the
                     entire sub-tree to be populated
                     when false, only the immediate
                     children are populated

        :returns: None
        """
        return None


class Pod(BaseACIPhysObject):
    """ Pod :  roughly equivalent to fabricPod """
    def __init__(self, pod_id, attributes=None, parent=None):
        """ Initialize the basic object.  It will
        create the name of the pod and set the type
        before calling the base class __init__ method.
        Typically the pod_id will be 1.

        :param pod_id: pod id string
        :param attributes:
        :param parent: optional parent object
        """
        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")

        if attributes :
            if not isinstance(attributes, dict):
                raise TypeError("Attributes must be a dictionary")

        if attributes:
            self.attributes = copy.deepcopy(attributes)
        else:
            self.attributes = {}
        self.pod = str(pod_id)
        self.type = 'pod'
        self.name = 'pod-' + str(self.pod)
        self._session = None
        logging.debug('Creating %s %s', self.__class__.__name__, self.pod)
        self._common_init(parent)

        # add atomic counters
        if 'dist_name' in self.attributes:
            self.atomic = AtomicCountersOnGoing(self, self.attributes['dist_name'])

    @staticmethod
    def get(session):
        """Gets all of the Pods from the APIC.  Generally there will be only one.

        :param session: APIC session
        :returns: list of Pods.  Note that this will be a
                  list even though there typically
                  will only be one item in the list.
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')
        class_query_url = ('/api/node/class/fabricPod.json?'
                           'query-target=self')
        pods = []
        ret = session.get(class_query_url)
        pod_data = ret.json()['imdata']
        for apic_pod in pod_data:
            attributes = {}
            attributes['dist_name'] = str(apic_pod['fabricPod']['attributes']['dn'])
            attributes['pod_id'] = str(apic_pod['fabricPod']['attributes']['id'])
            pod = Pod(attributes['pod_id'], attributes=attributes)
            pod._session = session
            pods.append(pod)
        return pods

    def populate_children(self, deep=False):
        """ This will cause all of children of the pod to be gotten from the APIC and
        populated as children of the pod.

        If deep is set to True, it will populate the entire tree.

        This method returns nothing.

        :param deep: boolean that when true will cause the
                     entire sub-tree to be populated
                     when false, only the immediate
                     children are populated

        :returns: None
        """
        nodes = Node.get(self._session, self)
        for node in nodes:
            self.add_child(node)
        links = Link.get(self._session, self)
        for link in links:
            self.add_child(link)
        if deep:
            for child in self._children:
                child.populate_children(deep=True)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.pod == other.pod

    def __str__(self):
        return 'pod-' + str(self.pod)


class Node(BaseACIPhysObject):
    """Node :  roughly equivalent to fabricNode """
    def __init__(self, pod=None, node=None, name=None, role=None, parent=None):
        """
        :param pod: String representation of the pod number
        :param node: String representation of the node number
        :param name: Name of the node
        :param role: Role of the node.  Valid roles are None,
                     'spine', 'leaf', 'controller', 'loosenode'
        :param parent: Parent pod object of the node.
        """

        # check that name is a string
        if name:
            if not isinstance(name, str):
                raise TypeError("Name must be a string")

        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")

        # check that role is valid
        valid_roles = [None, 'spine', 'leaf', 'controller']
        if role not in valid_roles:
            raise ValueError("role must be one of " + str(valid_roles))

        self.pod = pod
        self.node = node
        self.name = name
        self.role = role
        self.type = 'node'

        self._session = None
        self.fabricSt = None
        self.ipAddress = None
        self.tep_ip = None
        self.macAddress = None
        self.state = None
        self.mode = None
        self.operSt = None
        self.operStQual = None
        self.descr = None
        self.model = None
        self.dn = None
        self.vendor = None
        self.serial = None
        self.health = None

        self.num_ps_slots = None
        self.num_fan_slots = None
        self.num_sup_slots = None
        self.num_lc_slots = None
        self.num_ps_modules = None
        self.num_fan_modules = None
        self.num_sup_modules = None
        self.num_lc_modules = None
        
        self.vpc_info = None
        self.v4_proxy_ip = None
        self.mac_proxy_ip = None
        
        logging.debug('Creating %s %s', self.__class__.__name__, 'pod-' +
                      str(self.pod) + '/node-' + str(self.node))
        self._common_init(parent)

    def get_role(self):
        """ retrieves the node role
        :returns: role
        """
        return self.role

    def getFabricSt(self):
        """ retrieves the fabric state.

        :returns: fabric state
        """
        return self.fabricSt

    @staticmethod
    def _parse_dn(dn):
        """Parses the pod and node from a
           distinguished name of the node.
        """
        name = dn.split('/')
        pod = name[1].split('-')[1]
        node = name[2].split('-')[1]
        return pod, node

    @staticmethod
    def get(session, parent=None, node_id=None):
        """Gets all of the Nodes from the APIC.  If the parent pod is specified,
        only nodes of that pod will be retrieved.

        If parent pod and node_id is specified, only the matching switch will be
        retrieved.

        APIC controller nodes will have a 'role' of 'controller', while
        switch nodes will have a 'role' of 'leaf' or 'spine'

        :param session: APIC session
        :param parent: optional parent object or pod_id
        :param node_id: optional node_id of switch
        
        :returns: list of Nodes
        """
        # need to add pod as parent
        if parent:
            if not isinstance(parent, Pod) and not isinstance(parent, str):
                raise TypeError('An instance of Pod class or string is required to specify pod')
            
        if node_id:
            if not isinstance(node_id, str):
                raise TypeError('The node_id must be a string such as "101".')
            
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        if node_id :
            # this can be enhanced to get a specific node
            node_query_url = ('/api/node/class/fabricNode.json?'
                              'query-target=self')
        else :
            node_query_url = ('/api/node/class/fabricNode.json?'
                              'query-target=self')
            
        nodes = []
        ret = session.get(node_query_url)
        node_data = ret.json()['imdata']
        for apic_node in node_data:
            dist_name = str(apic_node['fabricNode']['attributes']['dn'])
            node_name = str(apic_node['fabricNode']['attributes']['name'])
            node_id = str(apic_node['fabricNode']['attributes']['id'])
            (pod, node_id) = Node._parse_dn(dist_name)
            node_role = str(apic_node['fabricNode']['attributes']['role'])
            node = Node(pod, node_id, node_name, node_role)
            node._session = session
            node._populate_from_attributes(apic_node['fabricNode']['attributes'])
            node._get_topsystem_info()

            # check for pod match if specified
            pod_match = False
            if parent:
                if isinstance(parent, Pod) :
                    if node.pod == parent.pod :
                        pod_match = True
                        parent.add_child(node)
                        node._parent = parent
                else :
                    # pod is a number string
                    if node.pod == parent :
                        pod_match = True
            else :
                pod_match = True

            # check for node match if specified
            node_match = False
            if node_id :
                if node_id == node.node :
                    node_match = True
            else :
                node_match = True

            if node_match and pod_match :

                if node.role == 'leaf' :
                    node._add_vpc_info()
                node.get_health()
                nodes.append(node)
                
        return nodes

    def get_health(self):
        """
        This will get the health of the switch node
        """
        if self.role != 'controller' :
            mo_query_url = '/api/mo/'+self.dn+ '/sys.json?&rsp-subtree-include=stats&rsp-subtree-class=fabricNodeHealth5min'
            ret = self._session.get(mo_query_url)
            data = ret.json()['imdata']
            if data :
                self.health = data[0]['topSystem']['children'][0]['fabricNodeHealth5min']['attributes']['healthLast']
            
    def _add_vpc_info(self):
        """
        This method only runs for leaf switches.  If
        the leaf has a VPC peer, the VPC information will be populated
        and the node.vpc_present flag will be set.

        check for vpcDom sub-object
        and if it exists, then create the entry as a dictionary of values.

        Will first check vpc_inst to see if it is enabled
        then get vpcDom under vpcInst

        peer_present is true if vpcDom exists
        
        From vpcDom get :
            domain_id
            system_mac
            local_mac
            monitoring_policy
            peer_ip
            peer_system_mac
            peer_version
            peer_state
            vtep_ip
            vtep_mac
            oper_role
            
        """
        partial_dn = 'topology/pod-{0}/node-{1}/sys/vpc/inst'.format(self.pod, self.node)
        
        
        mo_query_url = '/api/mo/' + partial_dn + '.json?query-target=self'
        ret = self._session.get(mo_query_url)
        data = ret.json()['imdata'][0]

        vpc_admin_state = data['vpcInst']['attributes']['adminSt']
        result = {'admin_state':vpc_admin_state}
        if vpc_admin_state=='enabled' :
            mo_query_url = '/api/mo/'+partial_dn + '.json?query-target=subtree&target-subtree-class=vpcDom'
            ret = self._session.get(mo_query_url)
            data = ret.json()['imdata']
            if 'vpcDom' in data[0]:
                result['oper_state'] = 'active'
                vpcDom = data[0]['vpcDom']['attributes']
                result['domain_id'] = vpcDom['id']
                result['system_mac'] = vpcDom['sysMac']
                result['local_mac'] = vpcDom['localMAC']
                result['monitoring_policy'] = vpcDom['monPolDn']
                result['peer_ip'] = vpcDom['peerIp']
                result['peer_mac'] = vpcDom['peerMAC']
                result['peer_version'] = vpcDom['peerVersion']
                result['peer_state'] = vpcDom['peerSt']
                result['vtep_ip'] = vpcDom['virtualIp']
                result['vtep_mac'] = vpcDom['vpcMAC']
                result['oper_role'] = vpcDom['operRole']
            else:
                result['oper_state'] = 'inactive'
        else :
            result['oper_state'] = 'inactive'

        self.vpc_info = result
        
        
        
    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.pod == other.pod) and \
            (self.node == other.node) and \
            (self.name == other.name) and \
            (self.role == other.role)

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
        """
        self.serial = attributes['serial']
        self.model = attributes['model']
        self.dn = attributes['dn']
        self.vendor = attributes['vendor']
        self.fabricSt = attributes['fabricSt']
        self.start_time = attributes['modTs']

    def _get_topsystem_info(self):
        """ will read in topSystem object to get more information about Node"""
    
        mo_query_url = '/api/mo/' + self.dn + '/sys.json?query-target=self'
        ret = self._session.get(mo_query_url)
        node_data = ret.json()['imdata']
        
        if len(node_data) > 0:
            self.ipAddress = str(node_data[0]['topSystem']['attributes']['address'])
            self.tep_ip = self.ipAddress
            self.macAddress = str(node_data[0]['topSystem']['attributes']['fabricMAC'])
            self.state = str(node_data[0]['topSystem']['attributes']['state'])
            self.mode = str(node_data[0]['topSystem']['attributes']['mode'])
            
            # now get eqptCh for even more info
            ch_mo_query_url = '/api/mo/' + self.dn + '/sys/ch.json?query-target=self'
            ret = self._session.get(ch_mo_query_url)
            node_data = ret.json()['imdata']

            if len(node_data) > 0:
                self.operSt = str(node_data[0]['eqptCh']['attributes']['operSt'])
                self.operStQual = str(node_data[0]['eqptCh']['attributes']['operStQual'])
                self.descr = str(node_data[0]['eqptCh']['attributes']['descr'])

            # get the total number of ports = number of l1PhysIf
            mo_query_url = '/api/mo/' + self.dn + '/sys.json?query-target=subtree&target-subtree-class=l1PhysIf'
            ret = self._session.get(mo_query_url)
            node_data = ret.json()['imdata']
            self.num_ports = len(node_data)

            # get the total number of ports = number of fan slots
            mo_query_url = '/api/mo/' + self.dn + '/sys/ch.json?query-target=subtree&target-subtree-class=eqptFtSlot'
            ret = self._session.get(mo_query_url)
            node_data = ret.json()['imdata']
            self.num_fan_slots = len(node_data)
            self.num_fan_modules = 0
            if node_data :
                for slot in node_data :
                    if slot['eqptFtSlot']['attributes']['operSt']=='inserted' :
                        self.num_fan_modules +=1

            # get the total number of ports = number of linecard slots
            mo_query_url = '/api/mo/' + self.dn + '/sys/ch.json?query-target=subtree&target-subtree-class=eqptLCSlot'
            ret = self._session.get(mo_query_url)
            node_data = ret.json()['imdata']
            self.num_lc_slots = len(node_data)
            self.num_lc_modules = 0
            if node_data :
                for slot in node_data :
                    if slot['eqptLCSlot']['attributes']['operSt']=='inserted' :
                        self.num_lc_modules +=1

            # get the total number of ports = number of power supply slots
            mo_query_url = '/api/mo/' + self.dn + '/sys/ch.json?query-target=subtree&target-subtree-class=eqptPsuSlot'
            ret = self._session.get(mo_query_url)
            node_data = ret.json()['imdata']
            self.num_ps_slots = len(node_data)
            self.num_ps_modules = 0
            if node_data :
                for slot in node_data :
                    if slot['eqptPsuSlot']['attributes']['operSt']=='inserted' :
                        self.num_ps_modules +=1

            # get the total number of ports = number of supervisor slots
            mo_query_url = '/api/mo/' + self.dn + '/sys/ch.json?query-target=subtree&target-subtree-class=eqptSupCSlot'
            ret = self._session.get(mo_query_url)
            node_data = ret.json()['imdata']
            self.num_sup_slots = len(node_data)
            self.num_sup_modules = 0
            if node_data :
                for slot in node_data :
                    if slot['eqptSupCSlot']['attributes']['operSt']=='inserted' :
                        self.num_sup_modules +=1

            

    def populate_children(self, deep=False):
        """Will populate all of the children modules such as
        linecards, fantrays and powersupplies, of the node.

        :param deep: boolean that when true will cause the entire
                     sub-tree to be populated. When false, only the
                     immediate children are populated

        :returns: List of children objects
        """

        session = self._session

        if self.role == 'controller':
            systemcontrollers = Systemcontroller.get(session, self)
            for systemcontroller in systemcontrollers:
                self.add_child(systemcontroller)
        else:
            linecards = Linecard.get(session, self)
            for linecard in linecards:
                self.add_child(linecard)
            supervisors = Supervisorcard.get(session, self)
            for supervisor in supervisors:
                self.add_child(supervisor)

        fantrays = Fantray.get(session, self)
        for fantray in fantrays:
            self.add_child(fantray)
        powersupplies = Powersupply.get(session, self)
        for powersupply in powersupplies:
            self.add_child(powersupply)

        if deep:
            for child in self._children:
                child.populate_children(deep=True)
        return self._children
    
    def get_model(self):
        """Returns the model string of the node'

        :returns: model of node of type str
        """

        return self.model

    def get_chassis_type(self):
        """Returns the chassis type of this node.  The chassis
        type is derived from the model number.
        This is a chassis type that is compatible with
        Cisco's Cable Plan XML.

        :returns: chassis type of node of type str
        """
        model = self.get_model()
        if model:
            fields = re.split('-', self.get_model())
        else:
            fields = []

        if len(fields) > 0:
            chassis_type = fields[0].lower()
        else:
            chassis_type = None
        return chassis_type


class ENode(Node):
    """External Node.  This class is for switch nodes that are
    connected to the pod, but are not
    ACI nodes, i.e. are not under control of the APIC.
    Examples would be external layer 2 switches,
    external routers, or hypervisor based switches.

    This class will look as much as possible like the Node
    class recognizing that not as much information
    is available to the APIC about them as is available
    about ACI nodes.  Nearly all of the information used
    to create this class comes from LLDP.
    """
    def __init__(self, attributes, session=None, parent=None):
        self.attributes = attributes
        self._parent = parent
        self._session = session

        # check that session is a session
        if self._session:
            if not isinstance(self._session, Session):
                raise TypeError("session must be of type Session")

        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")

        if self._parent:
            if self._parent.has_child(self):
                self._parent.remove_child(self)
            self._parent.add_child(self)

        # check that role is valid
        valid_roles = [None, 'physicalSwitch', 'virtualSwitch']
        if self.attributes.get('role') not in valid_roles:
            raise ValueError("role must be one of " + str(valid_roles) \
                              + ' found ' + self.attributes.get('role'))

        logging.debug('Creating %s %s', self.__class__.__name__, 'pod-' +
                      str(self.attributes.get('pod')) + '/node-' + str(self.attributes.get('id')))
        self._common_init(self._parent)

    def _common_init(self, parent):
        self._deleted = False
        self._children = []
        self._relations = []

    def info(self):
        """
        Node information summary.

        :returns: Formatted string that has a summary of all of the info\
                  gathered about the node.
        """
        text = ''
        textf = '{0:>15}: {1}\n'
        for attrib in self.attributes:
            if attrib[0] != '_':
                text += textf.format(attrib, self.attributes[attrib])
        return text

    def getName(self):
        """Gets name.

        :returns: Name string
        """
        return self.attributes.get('name')

    def getRole(self):
        """ retrieves the node role
        :returns: role
        """
        return self.attributes.get('role')

    @staticmethod
    def _get_physical_switches(session, parent):
        """Look for loose nodes and build an object for each one.
        """

        # if parent:
        #     if not isinstance(parent, Topology):
        #         raise TypeError('An instance of Topology class is required')
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')
        lnode_query_url = ('/api/node/class/fabricLooseNode.json?'
                           'query-target=self')
        lnodes = []
        ret = session.get(lnode_query_url)
        lnode_data = ret.json()['imdata']

        for apic_node in lnode_data:
            node_attrib = {}
            node_attrib['dn'] = str(apic_node['fabricLooseNode']['attributes']['dn'])
            node_attrib['name'] = str(apic_node['fabricLooseNode']['attributes']['name'])
            node_attrib['id'] = str(apic_node['fabricLooseNode']['attributes']['id'])
            node_attrib['role'] = 'physicalSwitch'
            node_attrib['pod'] = None
            node_attrib['status'] = str(apic_node['fabricLooseNode']['attributes']['status'])
            node_attrib['operIssues'] = str(apic_node['fabricLooseNode']
                                            ['attributes']['operIssues'])
            node_attrib['dn'] = str(apic_node['fabricLooseNode']['attributes']['dn'])
            node_attrib['fabricSt'] = 'external'
            node_attrib['descr'] = str(apic_node['fabricLooseNode']['attributes']['sysDesc'])
            node_attrib.update(ENode._get_system_info(session, node_attrib['dn']))
            node = ENode(attributes=node_attrib, session=session, parent=parent)
            lnodes.append(node)
        return lnodes

    @staticmethod
    def _get_virtual_switches(session, parent):
        """will find virtual switch nodes and return a list of such objects.
        """

        class_query_url = ('/api/node/class/compHv.json?query-target=self')
        vnodes = []
        ret = session.get(class_query_url)
        vnode_data = ret.json()['imdata']

        for vnode in vnode_data:
            attrib = {}
            attrib['role'] = 'virtualSwitch'
            attrib['fabricSt'] = 'external'
            attrib['descr'] = str(vnode['compHv']['attributes']['descr'])
            attrib['dn'] = str(vnode['compHv']['attributes']['dn'])
            attrib['name'] = str(vnode['compHv']['attributes']['name'])
            attrib['status'] = str(vnode['compHv']['attributes']['status'])
            attrib['type'] = str(vnode['compHv']['attributes']['type'])
            attrib['state'] = str(vnode['compHv']['attributes']['state'])
            attrib['guid'] = str(vnode['compHv']['attributes']['guid'])
            attrib['oid'] = str(vnode['compHv']['attributes']['oid'])

            vnode = ENode(attributes=attrib, session=session, parent=parent)
            vnodes.append(vnode)

        return vnodes

    @staticmethod
    def get(session, parent=None):
        """Gets all of the loose nodes from the APIC.

        :param session: APIC session
        :param parent: optional parent object of type Topology
        :returns: list of ENodes
        """
        enodes = ENode._get_physical_switches(session, parent)
        enodes.extend(ENode._get_virtual_switches(session, parent))
        return enodes

    @staticmethod
    def _get_dn(session, dn):
        """
        Will get the object that dn refers to.
        """
        mo_query_url = '/api/mo/' + dn + '.json?query-target=self'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        return node_data

    @staticmethod
    def _get_dn_children(session, dn):
        """
        Will get the children of the specified dn
        """

        mo_query_url = '/api/mo/' + dn + '.json?query-target=children'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        return node_data

    @staticmethod
    def _get_system_info(session, dn):
        """This routine will fill in various other attributes of the loose node
        """
        attrib = {}
        mo_query_url = '/api/mo/' + dn + '.json?query-target=children'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']

        for node in node_data:
            if 'fabricLooseLink' in node:
                dn = node['fabricLooseLink']['attributes']['portDn']
                name = dn.split('/')
                pod = name[1].split('-')[1]
                node = str(name[2].split('-')[1])
                if 'phys' in name[4]:
                    result = re.search('phys-\[(.+)\]', dn)
                    lldp_dn = 'topology/pod-' + pod + '/node-' + \
                        node + '/sys/lldp/inst/if-[' + result.group(1) + ']/adj-1'
                else:
                    agg_port_data = ENode._get_dn(session, dn)
                    port = agg_port_data[0]['pcAggrIf']['attributes']['lastBundleMbr']
                    lldp_dn = 'topology/pod-' + pod + '/node-' + \
                        node + '/sys/lldp/inst/if-[' + port + ']/adj-1'

            if 'fabricProtLooseLink' in node:
                dn = node['fabricProtLooseLink']['attributes']['portDn']
                name = dn.split('/')
                pod = name[1].split('-')[1]
                node = str(name[2].split('-')[1])
                lldp_dn = 'topology/pod-' + pod + '/node-' + node + '/sys/lldp/inst/if-['
                if dn:
                    link = ENode._get_dn_children(session, dn)
                    for child in link:
                        if 'pcRsMbrIfs' in child:
                            port = child['pcRsMbrIfs']['attributes']['tSKey']
                lldp_dn = lldp_dn + port + ']/adj-1'

        lldp_data = ENode._get_dn(session, lldp_dn)
        if len(lldp_data) > 0 :
            attrib['ipAddress'] = str(lldp_data[0]['lldpAdjEp']['attributes']['mgmtIp'])
            attrib['name'] = str(lldp_data[0]['lldpAdjEp']['attributes']['sysName'])
    
            chassis_id_t = lldp_data[0]['lldpAdjEp']['attributes']['chassisIdT']
            if chassis_id_t == 'mac':
                attrib['macAddress'] = str(lldp_data[0]['lldpAdjEp']['attributes']['chassisIdV'])
            else:
                attrib['macAddress'] = str(lldp_data[0]['lldpAdjEp']['attributes']['mgmtPortMac'])
            
        attrib['state'] = 'unknown'
        return attrib

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.attributes.get('name') == other.attributes.get('name')) and \
            (self.attributes.get('role') == other.attributes.get('role'))


class Link(BaseACIPhysObject):
    """Link class, equivalent to the fabricLink object in APIC"""
    def __init__(self, pod, link, node1, slot1, port1, node2, slot2, port2, parent=None):
        """
        :param pod: pod id
        :param link: link id
        :param node1: id of node of port at first end of link
        :param slot1: id of slot (linecard) of port at first end of link
        :param port1: id of port at first end of link
        :param node2: id of node of port at second end of link
        :param slot2: id of slot (linecard) of port at second end of link
        :param port2: id of port at second end of link
        :param parent: optional parent object

        """
        self.node1 = node1
        self.slot1 = slot1
        self.port1 = port1
        self.node2 = node2
        self.slot2 = slot2
        self.port2 = port2
        self.linkstate = None
        self.linkstatus = None
        self.pod = pod
        self.link = link
        self.descr = None
        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")

        self.type = 'link'
        self._session = None
        logging.debug('Creating %s %s', self.__class__.__name__,
                      'pod-%s link-%s' % (self.pod, self.link))
        self._common_init(parent)

    @staticmethod
    def get(session, parent_pod=None, node_id=None):
        """Gets all of the Links from the APIC.  If the parent_pod is specified,
        only links of that pod will be retrieved. If the parent_pod is a Pod object
        then the links will be added as children of that pod.

        If node is specified, then only links of that originate
        at the specific node will be returned.
        If node is specified, pod must be specified.

        :param session: APIC session
        :param parent_pod: Optional parent Pod object or identifier string.
        :param node_id: Optional node number string

        :returns: list of links
        """
        pod_id = None
        if parent_pod:
            if not isinstance(parent_pod, Pod) and not isinstance(parent_pod, str):
                raise TypeError('An instance of Pod class or a pod number string is required')

            if isinstance(parent_pod, Pod):
                pod_id = parent_pod.pod
            else:
                pod_id = parent_pod
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        if not parent_pod:
            interface_query_url = ('/api/node/class/fabricLink.json?'
                                   'query-target=self')
        elif pod_id:
            if node_id:
                interface_query_url = ('/api/node/class/fabricLink.json?'
                                       'query-target=self&query-target-filter=eq(fabricLink.n1,"'
                                       + node_id + '")')
            else:
                interface_query_url = ('/api/node/class/fabricLink.json?'
                                       'query-target=self')
        links = []
        ret = session.get(interface_query_url)
        link_data = ret.json()['imdata']
        for apic_link in link_data:
            dist_name = str(apic_link['fabricLink']['attributes']['dn'])
            link_n1 = str(apic_link['fabricLink']['attributes']['n1'])
            link_s1 = str(apic_link['fabricLink']['attributes']['s1'])
            link_p1 = str(apic_link['fabricLink']['attributes']['p1'])
            link_n2 = str(apic_link['fabricLink']['attributes']['n2'])
            link_s2 = str(apic_link['fabricLink']['attributes']['s2'])
            link_p2 = str(apic_link['fabricLink']['attributes']['p2'])
            (pod, link) = Link._parse_dn(dist_name)
            link = Link(pod, link, link_n1, link_s1, link_p1, link_n2, link_s2, link_p2)
            link._session = session
            link._populate_from_attributes(apic_link['fabricLink']['attributes'])
            if pod_id:
                if link.pod == pod_id:
                    if isinstance(parent_pod, Pod):
                        link._parent = parent_pod
                        if link._parent.has_child(link):
                            link._parent.remove_child(link)
                        link._parent.add_child(link)
                    links.append(link)
            else:
                links.append(link)
        return links

    def _populate_from_attributes(self, attributes):
        """ populate various additional attributes """

        self.linkstate = attributes['linkState']
        self.linkstatus = attributes['status']

    def __str__(self):
        text = 'n%s/s%s/p%s-n%s/s%s/p%s' % (self.node1, self.slot1,
                                            self.port1, self.node2, self.slot2, self.port2)
        return text

    def __eq__(self, other):
        """ Two links are considered equal if their class type is the
        same and the end points match.  The link ids are not
        checked.
        """

        if type(self) is not type(other):
            return False
        return (self.pod == other.pod) and (self.node1 == other.node1) \
            and (self.slot1 == other.slot1) and (self.port1 == other.port1)

    def get_node1(self):
        """Returns the Node object that corresponds to the first
        node of the link.  The Node must be a child of
        the Pod that this link is a member of, i.e. it
        must already have been read from the APIC.  This can
        most easily be done by populating the entire
        physical heirarchy from the Pod down.

        :returns: Node object at first end of link
        """

        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")

        nodes = self._parent.get_children(Node)
        for node in nodes:
            if node.node == self.node1:
                return node

    def get_node2(self):
        """Returns the Node object that corresponds to the
        second node of the link.  The Node must be a child of
        the Pod that this link is a member of, i.e. it must
        already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Node object at second end of link
        """

        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")

        nodes = self._parent.get_children(Node)
        for node in nodes:
            if node.node == self.node2:
                return node
        return None

    def get_slot1(self):
        """Returns the Linecard object that corresponds to the
        first slot of the link.  The Linecard must be a child of
        the Node in the Pod that this link is a member of,
        i.e. it must already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Linecard object at first end of link
        """

        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")
        node = self.get_node1()
        if node:
            linecards = node.get_children(Linecard)
            for linecard in linecards:
                if linecard.slot == self.slot1:
                    return linecard
        return None

    def get_slot2(self):
        """Returns the Linecard object that corresponds to the
         second slot of the link.  The Linecard must be a child of
        the Node in the Pod that this link is a member of,
        i.e. it must already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Linecard object at second end of link
        """

        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")
        node = self.get_node2()
        if node:
            linecards = node.get_children(Linecard)
            for linecard in linecards:
                if linecard.slot == self.slot2:
                    return linecard
        return None

    def get_port1(self):
        """Returns the Linecard object that corresponds to the
        first port of the link.  The port must be a child of
        the Linecard in the Node in the Pod that this link is a
        member of, i.e. it must already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Interface object at first end of link
        """

        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")
        linecard = self.get_slot1()
        if linecard:
            interfaces = linecard.get_children(ACI.Interface)
            for interface in interfaces:
                if interface.port == self.port1:
                    return interface
        return None

    def get_port2(self):
        """
        Returns the Linecard object that corresponds to the second port of
        the link. The port must be a child of the Linecard in the Node in
        the Pod that this link is a member of, i.e. it must already have been
        read from the APIC.  This can most easily be done by populating the
        entire physical heirarchy from the Pod down.

        :returns: Interface object at second end of link
        """
        if not self._parent:
            raise TypeError(("Parent pod must be specified in "
                             "order to get node"))
        linecard = self.get_slot2()
        if linecard:
            interfaces = linecard.get_children(ACI.Interface)
            for interface in interfaces:
                if interface.port == self.port2:
                    return interface
        return None

    def get_port_id1(self):
        """
        Returns the port ID of the first end of the link in the
        format pod/node/slot/port

        :returns: port ID string
        """
        return '{0}/{1}/{2}/{3}'.format(self.pod, self.node1, self.slot1, self.port1)

    def get_port_id2(self):
        """
        Returns the port ID of the second end of the link in the
        format pod/node/slot/port

        :returns: port ID string
        """
        return '{0}/{1}/{2}/{3}'.format(self.pod, self.node2, self.slot2, self.port2)

    @staticmethod
    def _parse_dn(dn):
        """Parses the pod and link number from a
           distinguished name of the link.

           :param dn: dn string of the link
           :returns: (pod, link)
        """
        name = dn.split('/')
        pod = str(name[1].split('-')[1])
        link = str(name[2].split('-')[1])

        return pod, link
