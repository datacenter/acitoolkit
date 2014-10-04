"""  Node class
"""
from acibaseobject import BaseACIObject, BaseRelation
from acisession import Session
import json
import logging

class BaseACIPhysObject(BaseACIObject) :
    """ Base class for physical objects
    """
    def _common_init(self, parent) :
        self._deleted = False
        self._parent = parent
        self._children = []
        self._relations = []
        self.session = None
        if self._parent is not None:
            self._parent.add_child(self)

    def get_json(self) :
        """ Returns json representation of the object
    
        INPUT:
        RETURNS: Nothing - physical objects are not modifiable
        """
        pass
    
    def get_url(self,fmt='json'):
        """Get the URL used to push the configuration to the APIC
        if no fmt parameter is specified, the format will be 'json'
        otherwise it will return '/api/mo/uni.' with the fmt string appended.

        INPUT: optional fmt string
        RETURNS: Nothing - physical objects are not modifiable
        """
        pass
    
    def add_child(self, child_obj):
        """ Add a child to the children list. All children must be unique so it will
        first delete the child if it already exists.

        INPUT: child_obj

        RETURN: None
        """
        if self.has_child(child_obj) :
            self.remove_child(child_obj)
        self._children.append(child_obj)
        
    def get_children(self, childType = None):
        """ Returns the list of children.  If childType is provided, then
        it will return all of the children of the matching type.

        INPUT: optional childType

        RETURNS: list of children
        """
        if childType :
            children = []
            for child in self._children :
                if isinstance(child,childType) :
                    children.append(child)
            return children
        else :
            return self._children

    def populate_children(self, deep=False) :
        return None

    @classmethod
    def exists(cls, session, phys_obj):
        """Check if an apic phys_obj exists on the APIC.
        Returns True if the phys_obj does exist.

        INPUT: session, phys_obj
        
        RETURNS: boolean
        """
        apic_nodes = cls.get(session)
        for apic_node in apic_nodes:
            if phys_obj == apic_node:
                return True
        return False
    

class BaseACIPhysModule(BaseACIPhysObject):
    """ BaseACIPhysModule: base class for modules  """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """

        # check that parent is a node
        if parent :
            if not isinstance(parent, Node) :
                raise TypeError('An instance of Node class is required')

        
        self.pod = str(pod)
        self.node = str(node)
        self.slot = str(slot)
        logging.debug('Creating %s %s', self.__class__.__name__, 'pod-'+self.pod+'/node-'+self.node+'/slot-'+self.slot)
        self._common_init(parent)
    def get_pod(self) : 
        """Gets pod id"""
        return self.pod
    def get_node(self) : 
        """Gets node id"""
        return self.node
    def get_slot(self) : 
        """Gets slot id"""
        return self.slot

        
    def __eq__(self, other):
        """ Two modules are considered equal if their class type is the same and pod, node, slot, type all match.
        """
        
        if type(self) is not type(other):
            return False
        return (self.pod == other.pod) and (self.node == other.node) and (self.slot == other.slot) and (self.type == other.type)
    
    @staticmethod
    def _parse_dn(dn):
        """Parses the pod, node, and slot from a
           distinguished name of the node.

           INPUT: string

           OUTPUT: pod, node, slot strings
        """
        name = dn.split('/')
        pod = str(name[1].split('-')[1])
        node = str(name[2].split('-')[1])
        slot = str(name[5].split('-')[1])
        return pod, node, slot


    @classmethod
    def get_obj(cls,session, apic_class, parent):
        """Gets all of the Nodes from the APIC.  This is called by the
        module specific get() methods.  The parameters passed include the
        APIC object class, apic_class, so that this will work for different kinds of modules.

        INPUT: session, apic_class = object class name in APIC, parent
        OUTPUT: list of module objects derived from the specified apic_class
        
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')
        
        interface_query_url = ('/api/node/class/'+apic_class+'.json?'
                               'query-target=self')
        cards = []
        ret = session.get(interface_query_url)
        card_data = ret.json()['imdata']
        for apic_obj in card_data:
            dist_name = str(apic_obj[apic_class]['attributes']['dn'])
            (pod, node_id, slot) = cls._parse_dn(dist_name)
            card = cls(pod, node_id, slot)
            card.session = session
            card._apic_class = apic_class
            card._populate_from_attributes(apic_obj[apic_class]['attributes'])
            card._additional_populate_from_attributes(apic_obj[apic_class]['attributes'])
            (card.firmware, card.bios) = card._get_firmware(dist_name)
            card.node = node_id
            card.pod = pod
            card.slot = slot
            card._parent = parent
            if parent :
                if card.node == parent.node :
                    if card._parent.has_child(card):
                        card._parent.remove_child(card)
                    card._parent.add_child(card)
                    cards.append(card)
            else :
                cards.append(card)
        return cards

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = attributes['ser']
        self.model = attributes['model']
        self.dn = attributes['dn']
        self.descr = attributes['descr']
        
    def _additional_populate_from_attributes(self, attributes):
        """Fills in an object with the additional attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.type = attributes['type']

    def _get_firmware(self, dist_name) :
        """Gets the firmware and bios version for the module from the "running" object in APIC.

        INPUT: dn of module, a string

        OUTPUT: firmware, bios
        """
        
        mo_query_url = '/api/mo/'+dist_name+'/running.json?query-target=self'
        ret = self.session.get(mo_query_url)
        node_data = ret.json()['imdata']
        
        firmware = str(node_data[0]['firmwareCardRunning']['attributes']['version'])
        bios = str(node_data[0]['firmwareCardRunning']['attributes']['biosVer'])
        return (firmware, bios)
        
class Systemcontroller(BaseACIPhysModule):
    """ class of the motherboard of the APIC controller node   """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create the name of the Systemcontroller and set the type
        before calling the base class __init__ method.
        
        """
        self.name = 'SysC-'+'/'.join([pod, node, slot])
        self.type = 'systemctrlcard'
        super(Systemcontroller,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls,session, parent=None):
        """Gets all of the System controllers from the APIC. This information comes from
        the APIC 'eqptBoard' class.

        If parent is specified, it will only get system controllers that are
        children of the the parent.  The system controlles will also be added as children to the parent Node.

        INPUT: session, parent of class Node

        OUTPUT: list of Systemcontrollers
        """
        # need to add pod as parent
        return cls.get_obj(session,'eqptBoard', parent)
    
    @staticmethod
    def _parse_dn(dn):
        """Parses the pod, node from a
           distinguished name of the node and fills in the slot to be '1'

           INPUT: dn of node

           OUTPUT: pod, node, slot
        """
        name = dn.split('/')
        pod = str(name[1].split('-')[1])
        node = str(name[2].split('-')[1])
        slot = '1'
        return pod, node, slot

    def _get_firmware(self, dn) :
        """ Gets the firmware version of the System controller from the firmwareCtrlrRunning attribute of the
        ctrlrrunning object under the ctrlrfwstatuscont object.  It will set the bios to None.

        INPUT: dn

        OUTPUT: firmware, bios
        """
        
        name = dn.split('/')
        new_dist_name = '/'.join(name[0:4])
        
        mo_query_url = '/api/mo/'+new_dist_name+'/ctrlrfwstatuscont/ctrlrrunning.json?query-target=self'
        ret = self.session.get(mo_query_url)
        node_data = ret.json()['imdata']
        
        firmware = str(node_data[0]['firmwareCtrlrRunning']['attributes']['version'])
        bios = None
        return (firmware, bios)
        
    def _additional_populate_from_attributes(self, attributes):
        """Fills in the System controller with additional attributes.
          
        """
        self.type = str(attributes['type'])

        # I think this is a bug fix to the APIC controller.  The type should be set correctly.
        if self.type == 'unknown' :
                self.type = 'systemctrlcard'
        

class Linecard(BaseACIPhysModule):
    """ class for a linecard of a switch   """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create the name of the linecard and set the type
        before calling the base class __init__ method
        """
        self.name = 'Lc-'+'/'.join([pod, node, slot])
        self.type = 'linecard'
        super(Linecard,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls,session, parent=None):
        """Gets all of the linecards from the APIC.  If parent is specified, it will only get linecards that are
        children of the the parent.  The linecards will also be added as children to the parent Node.

        The lincard object is derived mostly from the APIC 'eqptLC' class.
         
        INPUT: session, parent of class Node

        OUTPUT: list of linecards
        """
        return cls.get_obj(session,'eqptLC', parent)

class Supervisorcard(BaseACIPhysModule):
    """class representing the supervisor card of a switch
    """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """
        self.name = 'SupC-'+'/'.join([pod, node, slot])
        self.type = 'supervisor'
        super(Supervisorcard,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the supervisor cards from the APIC.  If parent is specified, it will only get the supervisor card that is
        a child of the the parent Node.  The supervisor will also be added as a child to the parent Node.

        The Supervisorcard object is derived mostly from the APIC 'eqptSupC' class.
         
        INPUT: session, parent of class Node

        OUTPUT: list of linecards
        """
        return cls.get_obj(session,'eqptSupC', parent)

class Fantray(BaseACIPhysModule):
    """ class for the fan tray of a node"""
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create the name of the fan tray and set the type
        before calling the base class __init__ method
        """
        
        self.name = 'Fan-'+'/'.join([pod, node, slot])
        self.type = 'fantray'
        super(Fantray,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the fantrays from the APIC.  If parent is specified, it will only get fantrays that are
        children of the the parent.  The fantrays will also be added as children to the parent Node.

        The fantray object is derived mostly from the APIC 'eqptFt' class.
         
        INPUT: session, parent of class Node

        OUTPUT: list of fantrays
        """
        return cls.get_obj(session,'eqptFt', parent)
    
    def _additional_populate_from_attributes(self, attributes):
        """Fills in an object with additional attributes.
         """
        self.status = attributes['operSt']
    @staticmethod
    def _get_firmware(dist_name) :
        """ Returns None for firmware and bios revisions"""
        
        return (None, None)
    def populate_children(self, deep=False) :
        return None

    
class Powersupply(BaseACIPhysModule):
    """ class for a power supply in a node   """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create the name of the powersupply and set the type
        before calling the base class __init__ method
        """
        self.name = 'PS-'+'/'.join([pod, node, slot])
        self.type = 'powersupply'
        super(Powersupply,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the power supplies from the APIC.  If parent is specified, it will only get power supplies that are
        children of the the parent.  The power supplies will also be added as children to the parent Node.

        The Powersupply object is derived mostly from the APIC 'eqptPsu' class.
         
        INPUT: session, parent of class Node

        OUTPUT: list of powersupplies
        """
        return cls.get_obj(session,'eqptPsu', parent)
    
    def _additional_populate_from_attributes(self, attributes):
        """Fills in an object with additional desired attributes.
        """
        self.status = str(attributes['operSt'])
        self.fan_status = str(attributes['fanOpSt'])
        self.voltage_source = str(attributes['vSrc'])
        
    @staticmethod
    def _get_firmware(dist_name) :
        """ The power supplies do not have a readable firmware or bios revision so
        this will return None for firmware and bios revisions"""

        return (None, None)
    
    def populate_children(self, deep=False) :
        return None


    
class Pod(BaseACIPhysObject):
    """ Pod :  roughly equivalent to fabricPod """
    def __init__(self, pod_id, parent=None):
        """ Initialize the basic object.  It will create the name of the pod and set the type
        before calling the base class __init__ method.  Typically the pod_id will be 1.
        """
        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")
        
        self.pod = str(pod_id)
        self.type = 'pod'
        self.name = 'pod-'+str(self.pod)
        logging.debug('Creating %s %s', self.__class__.__name__, self.pod)
        self._common_init(parent)
        

    @staticmethod
    def get(session):
        """Gets all of the Pods from the APIC.  Generally there will be only one.
        """
        
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')
        interface_query_url = ('/api/node/class/fabricPod.json?'
                               'query-target=self')
        pods = []
        ret = session.get(interface_query_url)
        pod_data = ret.json()['imdata']
        for apic_pod in pod_data:
            dist_name = str(apic_pod['fabricPod']['attributes']['dn'])
            pod_id = str(apic_pod['fabricPod']['attributes']['id'])
            pod = Pod(pod_id)
            pod._populate_from_attributes(apic_pod['fabricPod']['attributes'])
            pod.session = session
            pods.append(pod)
        return pods
    def populate_children(self, deep=False) :
        """ This will cause all of children of the pod to be gotten from the APIC and
        populated as children of the pod.

        If deep is set to True, it will populate the entire tree.

        This method returns nothing.
        """
        
        nodes = Node.get(self.session, self)
        for node in nodes :
            self.add_child(node)
        if deep :
            for child in self._children :
                child.populate_children(deep=True)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.pod == other.pod
    def __str__(self) :
        return 'pod-'+str(self.pod)
    
class Node(BaseACIPhysObject):
    """ Node :  roughly equivalent to eqptNode """
    def __init__(self, pod, node, name, role='switch', parent=None):
        """ Initialize the basic object.  
        """

        # check that name is a string
        if name is None or not isinstance(name, str):
            raise TypeError("Name must be a string")

        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")

        # check that role is valid
        valid_roles = ['spine','leaf','controller']
        if role not in valid_roles :
            raise ValueError("role must be one of "+ str(valid_roles))
        
        self.pod = pod
        self.node = node
        self.name = name
        self.role = role
        self.type = 'node'
        self.session = None
        logging.debug('Creating %s %s', self.__class__.__name__, 'pod-'+self.pod+'/node-'+self.node)
        self._common_init(parent)
        
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
    def _get_name(session, dn) :
        """Retrieves the name of the node from the name attribute of the fabricNode object"""
        
        name = dn.split('/')
        fabricNode_dn = name[0]+'/'+name[1]+'/'+name[2]
        
        mo_query_url = '/api/mo/'+fabricNode_dn+'.json?query-target=self'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        
        return str(node_data[0]['fabricNode']['attributes']['name'])
    
    @staticmethod
    def get(session, parent=None):
        """Gets all of the Nodes from the APIC.  If the parent pod is specified,
        only nodes of that pod will be retrieved.
        """
        # need to add pod as parent
        if parent :
            if not isinstance(parent, Pod) :
                raise TypeError('An instance of Pod class is required')
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')
        interface_query_url = ('/api/node/class/eqptCh.json?'
                               'query-target=self')
        nodes = []
        ret = session.get(interface_query_url)
        node_data = ret.json()['imdata']
        for apic_node in node_data:
            dist_name = str(apic_node['eqptCh']['attributes']['dn'])
            node_name = Node._get_name(session, dist_name)
            (pod, node_id) = Node._parse_dn(dist_name)
            node_role = str(apic_node['eqptCh']['attributes']['role'])
            node = Node(pod, node_id, node_name, node_role, parent)
            node.session = session
            node._populate_from_attributes(apic_node['eqptCh']['attributes'])
            if parent :
                if node.pod == node._parent.pod :
                    if node._parent.has_child(node):
                        node._parent.remove_child(node)
                    node._parent.add_child(node)
                    nodes.append(node)
            else :
                nodes.append(node)
        return nodes

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.pod == other.pod) and (self.node == other.node) and (self.name == other.name) and (self.role == other.role)
    
    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
        """
        self.serial = attributes['ser']
        self.model = attributes['model']
        self.dn = attributes['dn']
        self.descr = attributes['descr']
        
    def populate_children(self, deep=False) :
        """ will populate all of the children modules such as linecards, fantrays and powersupplies, of the node.
        """
        
        session = self.session
            
        if self.role == 'controller' :
            systemcontrollers = Systemcontroller.get(session, self)
            for systemcontroller in systemcontrollers :
                self.add_child(systemcontroller)
            
        else :
            linecards = Linecard.get(session, self)
            for linecard in linecards :
                self.add_child(linecard)
            supervisors = Supervisorcard.get(session, self)
            for supervisor in supervisors :
                self.add_child(supervisor)
            
        fantrays = Fantray.get(session, self)
        for fantray in fantrays :
            self.add_child(fantray)
        powersupplies = Powersupply.get(session, self)
        for powersupply in powersupplies:
            self.add_child(powersupply)

        if deep :
            for child in self._children :
                child.populate_children(deep=True)

