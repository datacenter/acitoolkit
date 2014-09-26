"""
This module implements the Base Class for creating all of the ACI Objects
"""
import logging
import jsontoxml
from xml.dom.minidom import parseString


class BaseRelation(object):
    """Class for all basic relations.
       A relation consists of the following elements:
       item:    The object to which the relationship applies
       status:  The status of the relationship
                Valid values are 'attached' and 'detached'
       relation_type:   Additional information to distinguish the relationship.
                        Used in cases where more than 1 type of relation exists
       """
    def __init__(self, item, status, relation_type=None):
        if status not in ('attached', 'detached'):
            raise ValueError
        self.item = item
        self.status = status
        self.relation_type = relation_type

    def is_attached(self):
        """Returns whether the relation is attached.
           If a relation is detached, it is to be deleted from the APIC
        """
        return self.status == 'attached'

    def is_detached(self):
        """Returns whether the relation is detached.
           If a relation is detached, it is to be deleted from the APIC
        """
        return not self.is_attached()

    def set_as_detached(self):
        """Set the relation as detached"""
        self.status = 'detached'

    def __eq__(self, other):
        return (self.item == other.item and
                self.status == other.status and
                self.relation_type == other.relation_type)


class BaseACIObject(object):
    """This class defines functionality common to all ACI objects.
       Functions may be overwritten by inheriting classes.
    """
    def __init__(self, name, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.
        """
        if name is None or not isinstance(name, str):
            raise TypeError
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")
        self.name = name
        self._deleted = False
        self._children = []
        self._relations = []
        self._parent = parent
        logging.debug('Creating %s %s', self.__class__.__name__, name)
        if self._parent is not None:
            if self._parent.has_child(self):
                self._parent.remove_child(self)
            self._parent.add_child(self)

    def mark_as_deleted(self):
        """Mark the object as deleted.  This will cause the JSON/XML status
           to be set to deleted
        """
        self._deleted = True

    @staticmethod
    def is_interface():
        """Return whether this object is considered an Interface

        RETURN: False
        """
        return False

    def is_deleted(self):
        """ Check if the object has been deleted. """
        return self._deleted

    def attach(self, item):
        """Attach the object to the other object"""
        if self.is_attached(item):
            self._relations.remove(BaseRelation(item, 'attached'))
        self._relations.append(BaseRelation(item, 'attached'))

    def is_attached(self, item):
        """Returns True if the item is attached to this object"""
        check = BaseRelation(item, 'attached')
        return check in self._relations

    def detach(self, item):
        """Detach the object from the other object"""
        if self.is_attached(item):
            self._relations.remove(BaseRelation(item, 'attached'))
            self._relations.append(BaseRelation(item, 'detached'))

    def get_children(self):
        """ Returns the list of children """
        return self._children

    def add_child(self, obj):
        """ Add a child to the children list """
        self._children.append(obj)

    def has_child(self, obj):
        """ Check for existence of a child in the children list """
        for child in self._children:
            if child == obj:
                return True
        return False

    def remove_child(self, obj):
        """ Remove a child from the children list """
        self._children.remove(obj)

    def get_parent(self):
        """ Returns the parent of this object """
        return self._parent

    def _has_any_relation(self, other_class):
        """Check if the object has any relation to the other class"""
        for relation in self._relations:
            is_other_class = isinstance(relation.item, other_class)
            if is_other_class and relation.is_attached():
                return True
        return False

    def _has_relation(self, obj, relation_type=None):
        """Check if the object has a relation to the other object"""
        for relation in self._relations:
            same_item = relation.item == obj
            same_relation_type = relation.relation_type == relation_type
            if same_item and relation.is_attached() and same_relation_type:
                return True
        return False

    def _add_relation(self, obj, relation_type=None):
        """Add a relation to the object"""
        if self._has_relation(obj):
            return
        relation = BaseRelation(obj, 'attached', relation_type)
        self._relations.append(relation)

    def _remove_relation(self, obj, relation_type=None):
        """Remove a relation from the object"""
        removal = BaseRelation(obj, 'attached', relation_type)
        for relation in self._relations:
            if relation == removal:
                relation.set_as_detached()
        return True

    def _remove_all_relation(self, obj_class, relation_type=None):
        """Remove all relations belonging to a particular class"""
        for relation in self._relations:
            same_obj_class = isinstance(relation.item, obj_class)
            same_relation_type = relation.relation_type == relation_type
            attached = relation.is_attached()
            if same_obj_class and same_relation_type and attached:
                relation.set_as_detached()

    def _get_any_relation(self, obj_class, relation_type=None):
        """Return a single relation belonging to a particular class.
           This will return the first relation encountered.
        """
        for relation in self._relations:
            same_obj_class = isinstance(relation.item, obj_class)
            same_relation_type = relation.relation_type == relation_type
            attached = relation.is_attached()
            if same_obj_class and attached and same_relation_type:
                return relation.item

    def _get_all_relation(self, obj_class, relation_type=None):
        """Get all relations belonging to a particular class"""
        resp = []
        for relation in self._relations:
            same_obj_class = isinstance(relation.item, obj_class)
            same_relation_type = relation.relation_type == relation_type
            attached = relation.is_attached()
            if same_obj_class and attached and same_relation_type:
                resp.append(relation.item)
        return resp

    def get_interfaces(self, status='attached'):
        """Get all of the interface relations"""
        resp = []
        for relation in self._relations:
            if relation.item.is_interface() and relation.status == status:
                resp.append(relation.item)
        return resp

    def get_all_attached(self, attached_class, status='attached'):
        """Get all of the relations of objects beloging to the
           specified class
        """
        resp = []
        for relation in self._relations:
            same_class = isinstance(relation.item, attached_class)
            same_status = relation.status == status
            if same_class and same_status:
                resp.append(relation.item)
        return resp

    def _get_url_extension(self):
        """Get the URL extension used for a particular object"""
        return ''

    def __str__(self):
        return self.name

    def get_json(self, obj_class, attributes=None,
                 children=None, get_children=True):
        """ Get the JSON representation of this class in the actual APIC
            Object Model
        """
        if children is None:
            children = []
        if attributes is None:
            attributes = {}
        children_json = []
        for child in children:
            children_json.append(child)
        if get_children:
            for child in self._children:
                data = child.get_json()
                if data is not None:
                    if isinstance(data, list):
                        for item in data:
                            children_json.append(item)
                    else:
                        children_json.append(data)
        if self._deleted:
            attributes['status'] = 'deleted'
        resp = {obj_class: {'attributes': attributes,
                            'children': children_json}}
        return resp

    def get_xml(self, pretty_xml=False):
        """Return the XML form to send to the APIC"""
        return self.get_xml_from_json(self.get_json(), pretty_xml)

    @staticmethod
    def get_xml_from_json(json_file, pretty_xml=False):
        """Convert the JSON output into XML format"""
        xml_file = jsontoxml.dicttoxml(json_file, root=False, attr_type=False)
        if pretty_xml is True:
            return parseString(xml_file).toprettyxml()
        else:
            return xml_file

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        if self.get_parent() != other.get_parent():
            return False
        return self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        pass

    def _generate_attributes(self):
        """Gets the attributes used in generating the JSON for the object
        """
        attributes = {}
        attributes['name'] = self.name
        return attributes

    @classmethod
    def get(cls, session, toolkit_class, apic_class, parent=None, tenant=None):
        """Gets all of a particular class.
        """
        if isinstance(tenant, str):
            raise TypeError
        logging.debug('%s.get called', toolkit_class.__name__)
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
            name = str(object_data[apic_class]['attributes']['name'])
            obj = toolkit_class(name, parent)
            attribute_data = object_data[apic_class]['attributes']
            obj._populate_from_attributes(attribute_data)
            resp.append(obj)
        return resp
