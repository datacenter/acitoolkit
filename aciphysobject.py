"""  Node class
"""
from acibaseobject import BaseACIObject, BaseRelation
from acisession import Session
import json
import logging

class BaseACIPhysObject(BaseACIObject) :
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
    
    def add_child(self, obj):
        """ Add a child to the children list. All children are unique so delete if already there """
        if self.has_child(obj) :
            self.remove_child(obj)
        self._children.append(obj)
        
    def get_children(self, childType = None):
        """ Returns the list of children.  If childType is provided, then
        it will return all of the children of the matching type
        """
        if childType :
            children = []
            for child in self._children :
                if isinstance(child,childType) :
                    children.append(child)
            return children
        else :
            return self._children



    @classmethod
    def exists(cls, session, phys_obj):
        """Check if an apic physical object exists on the APIC.

        INPUT: session, phys_obj
        RETURNS: boolean
        """
        apic_nodes = cls.get(session)
        for apic_node in apic_nodes:
            if phys_obj == apic_node:
                return True
        return False
    

class BaseACIPhysModule(BaseACIPhysObject):
    """ BaseACIPhysModule: base class for cards  """

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

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return (self.pod == other.pod) and (self.node == other.node) and (self.slot == other.slot) and (self.type == other.type)
    
    @staticmethod
    def parse_dn(dist_name):
        """Parses the pod, node from a
           distinguished name of the node.
        """
        name = dist_name.split('/')
        pod = str(name[1].split('-')[1])
        node = str(name[2].split('-')[1])
        slot = str(name[5].split('-')[1])
        return pod, node, slot


    @classmethod
    def get_obj(cls,session, apic_class, parent):
        """Gets all of the Nodes from the APIC
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
            (pod, node_id, slot) = cls.parse_dn(dist_name)
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
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.type = attributes['type']

    def _get_firmware(self, dist_name) :
        
        mo_query_url = '/api/mo/'+dist_name+'/running.json?query-target=self'
        ret = self.session.get(mo_query_url)
        node_data = ret.json()['imdata']
        
        firmware = str(node_data[0]['firmwareCardRunning']['attributes']['version'])
        bios = str(node_data[0]['firmwareCardRunning']['attributes']['biosVer'])
        return (firmware, bios)
        
class Systemcontroller(BaseACIPhysModule):
    """ Motherboard:   """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """
        self.name = 'SysC-'+'/'.join([pod, node, slot])
        self.type = 'systemctrlcard'
        super(Systemcontroller,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls,session, parent=None):
        """Gets all of the linecards from the APIC
        """
        # need to add pod as parent
        return cls.get_obj(session,'eqptBoard', parent)
    
    @staticmethod
    def parse_dn(dist_name):
        """Parses the pod, node from a
           distinguished name of the node.
        """
        name = dist_name.split('/')
        pod = str(name[1].split('-')[1])
        node = str(name[2].split('-')[1])
        slot = '1'
        return pod, node, slot

    def _get_firmware(self, dist_name) :

        name = dist_name.split('/')
        new_dist_name = '/'.join(name[0:4])
        
        mo_query_url = '/api/mo/'+new_dist_name+'/ctrlrfwstatuscont/ctrlrrunning.json?query-target=self'
        ret = self.session.get(mo_query_url)
        node_data = ret.json()['imdata']
        
        firmware = str(node_data[0]['firmwareCtrlrRunning']['attributes']['version'])
        bios = None
        return (firmware, bios)
        
    def _additional_populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.type = str(attributes['type'])

        # I think this is a bug fix to the APIC controller.  The type should be set correctly.
        if self.type == 'unknown' :
                self.type = 'systemctrlcard'
        

class Linecard(BaseACIPhysModule):
    """ Linecard:   """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """
        self.name = 'Lc-'+'/'.join([pod, node, slot])
        self.type = 'linecard'
        super(Linecard,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls,session, parent=None):
        """Gets all of the linecards from the APIC
        """
        # need to add pod as parent
        return cls.get_obj(session,'eqptLC', parent)

class Supervisorcard(BaseACIPhysModule):
    """ Supervisorcard:   """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """
        self.name = 'SupC-'+'/'.join([pod, node, slot])
        self.type = 'supervisor'
        super(Supervisorcard,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        return cls.get_obj(session,'eqptSupC', parent)

class Fantray(BaseACIPhysModule):
    """ Fan Tray:   """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """
        self.name = 'Fan-'+'/'.join([pod, node, slot])
        self.type = 'fantray'
        super(Fantray,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        return cls.get_obj(session,'eqptFt', parent)
    
    def _additional_populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.status = attributes['operSt']
    @staticmethod
    def _get_firmware(dist_name) :
        return (None, None)
    
class Powersupply(BaseACIPhysModule):
    """ Powersupply:   """
    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """
        self.name = 'PS-'+'/'.join([pod, node, slot])
        self.type = 'powersupply'
        super(Powersupply,self).__init__(pod, node, slot, parent)

    @classmethod
    def get(cls, session, parent=None):
        return cls.get_obj(session,'eqptPsu', parent)
    
    def _additional_populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.status = str(attributes['operSt'])
        self.fan_status = str(attributes['fanOpSt'])
        self.voltage_source = str(attributes['vSrc'])
        
    @staticmethod
    def _get_firmware(dist_name) :
        return (None, None)
    

    
class Pod(BaseACIPhysObject):
    """ Pod :  roughly equivalent to fabricPod """
    def __init__(self, pod, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """

        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")
        
        self.pod = str(pod)
        self.type = 'pod'
        self.name = 'pod-'+str(self.pod)
        logging.debug('Creating %s %s', self.__class__.__name__, self.pod)
        self._common_init(parent)
        

    @staticmethod
    def get(session):
        """Gets all of the Pods from the APIC
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
    def populate_children(self) :
        nodes = Node.get(self.session, self)
        for node in nodes :
            self.add_child(node)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.pod == other.pod
    def __str__(self) :
        return 'pod-'+str(self.pod)
    
class Node(BaseACIPhysObject):
    """ Node :  roughly equivalent to fabricNode """
    def __init__(self, pod, node, name, role='switch', parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """

        # check that name is a string
        if name is None or not isinstance(name, str):
            raise TypeError("Name must be a string")

        # check that parent is not a string
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")

        # check that role is valid
        valid_roles = ['switch','controller']
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
    def parse_dn(dist_name):
        """Parses the pod, node from a
           distinguished name of the node.
        """
        name = dist_name.split('/')
        pod = name[1].split('-')[1]
        node = name[2].split('-')[1]
        return pod, node

    @staticmethod
    def _get_name(session, dist_name) :
        name = dist_name.split('/')
        fabricNode_dn = name[0]+'/'+name[1]+'/'+name[2]
        
        mo_query_url = '/api/mo/'+fabricNode_dn+'.json?query-target=self'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        
        return str(node_data[0]['fabricNode']['attributes']['name'])
    
    @staticmethod
    def get(session, parent=None):
        """Gets all of the Nodes from the APIC
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
            (pod, node_id) = Node.parse_dn(dist_name)
            node_role = attributes['role']
            node = Node(pod,node_id,node_name,node_role)
            node.session = session
            node._populate_from_attributes(apic_node['eqptCh']['attributes'])
            node.node = node_id
            node.pod = pod
            node._linecards = []
            node._supervisors = []
            node._fantrays = []
            node._powersupplies = []
            node._parent = parent
            if parent :
                if node.pod == node._parent.pod :
                    if node._parent.has_child(node):
                        self._parent.remove_child(node)
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
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = attributes['ser']
        self.model = attributes['model']
        self.dn = attributes['dn']
        self.descr = attributes['descr']
        
    def populate_children(self, session = None) :
        if session == None :
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

    

