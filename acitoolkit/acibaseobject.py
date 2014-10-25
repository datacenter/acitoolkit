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
"""
This module implements the Base Class for creating all of the ACI Objects.
"""
import logging


class BaseRelation(object):
    """
    Class for all basic relations.
    """
    def __init__(self, item, status, relation_type=None):
        """
        A relation consists of the following elements:

        :param item:    The object to which the relationship applies
        :param status:  The status of the relationship.\
                        Valid values are 'attached' and 'detached'
        :param relation_type:   Optional additional information to distinguish\
                                the relationship.\
                                Used in cases where more than 1 type of\
                                relation exists.
        """
        if status not in ('attached', 'detached'):
            raise ValueError
        self.item = item
        self.status = status
        self.relation_type = relation_type

    def is_attached(self):
        """
        :returns: True or False indicating whether the relation is attached.\
        If a relation is detached, it will be deleted from the APIC when the\
        configuration is pushed.
        """
        return self.status == 'attached'

    def is_detached(self):
        """
        :returns: True or False indicating whether the relation is detached.\
        If a relation is detached, it will be deleted from the APIC when the\
        configuration is pushed.
        """
        return not self.is_attached()

    def set_as_detached(self):
        """
        Sets the relation status to 'detached'
        """
        self.status = 'detached'

    def __eq__(self, other):
        return (self.item == other.item and
                self.status == other.status and
                self.relation_type == other.relation_type)


class BaseACIObject(object):
    """
    This class defines functionality common to all ACI objects.
    Functions may be overwritten by inheriting classes.
    """
    def __init__(self, name, parent=None):
        """
        Constructor initializes the basic object and should be called by\
        the init routines of inheriting subclasses.

        :param name: String containing the name of the object\
                     instance
        :param parent: Parent object within the acitoolkit object model.
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
        self.descr = None
        logging.debug('Creating %s %s', self.__class__.__name__, name)
        if self._parent is not None:
            if self._parent.has_child(self):
                self._parent.remove_child(self)
            self._parent.add_child(self)

    def mark_as_deleted(self):
        """
        Mark the object as deleted.  This will cause the JSON status
        to be set to deleted.
        """
        self._deleted = True

    @staticmethod
    def is_interface():
        """
        Indicates whether this object is considered an Interface.\
        The default is False.

        :returns: False
        """
        return False

    def is_deleted(self):
        """
        Check if the object has been deleted.
        :returns: True or False, True indicates the object has been deleted.
        """
        return self._deleted

    def attach(self, item):
        """
        Attach the object to the other object.

        :param item:  Object to be attached.
        """
        if self.is_attached(item):
            self._relations.remove(BaseRelation(item, 'attached'))
        self._relations.append(BaseRelation(item, 'attached'))

    def is_attached(self, item):
        """
        Indicates whether the item is attached to this object/
        :returns: True or False, True indicates the item is attached.
        """
        check = BaseRelation(item, 'attached')
        return check in self._relations

    def detach(self, item):
        """
        Detach the object from the other object.

        :param item:  Object to be detached.
        """
        if self.is_attached(item):
            self._relations.remove(BaseRelation(item, 'attached'))
            self._relations.append(BaseRelation(item, 'detached'))

    def get_children(self):
        """
        :returns: List of children objects.
        """
        return self._children

    def add_child(self, obj):
        """
        Add a child to the children list.

        :param obj: Child object to add to the children list of the\
                    called object.
        """
        self._children.append(obj)

    def has_child(self, obj):
        """
        Check for existence of a child in the children list

        :param obj:  Child object that is the subject of the check.
        :returns:  True or False, True indicates that it does indeed\
                   have the `obj` object as a child.
        """
        for child in self._children:
            if child == obj:
                return True
        return False

    def remove_child(self, obj):
        """
        Remove a child from the children list

        :param obj:  Child object that is to be removed.
        """
        self._children.remove(obj)

    def populate_children(self, deep=False):
        """
        Populates all of the children and then calls populate_children\
        of those children if deep is True.  This method should be\
        overridden by any object that does have children

        :param deep: True or False.  Default is False.
        """
        return None

    def get_parent(self):
        """
        :returns: Parent of this object.
        """
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
        """
        Get all of the interface relations.  Note that multiple classes
        are considered "interfaces" such as Interface, L2Interface,
        L3Interface, etc.

        :param status: Valid values are 'attached' and 'detached'.\
                       Default is 'attached'.
        :returns:  List of interfaces that this object has relations\
                   and the status matches.
        """
        resp = []
        for relation in self._relations:
            if relation.item.is_interface() and relation.status == status:
                resp.append(relation.item)
        return resp

    def get_all_attached(self, attached_class, status='attached'):
        """
        Get all of the relations of objects belonging to the
        specified class with the specified status.

        :param attached_class:  The class that is the subject of the search.
        :param status:  Valid values are 'attached' and 'detached'.\
                        Default is 'attached'.
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
        """
        Get the JSON representation of this class in the actual APIC
        Object Model.

        :param obj_class:  Object Class Name within the APIC model.
        :param attributes:  Additional attributes that should be set\
                            in the JSON.
        :param children:  Children objects to traverse as well.
        :param get_children:  Indicates whether the children objects\
                              should be included.
        :returns: JSON dictionary to be pushed to the APIC.
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
        """
        Generic classmethod to get all of a particular APIC class.

        :param session:  the instance of Session used for APIC communication
        :param toolkit_class: acitoolkit class to return
        :param apic_class:  String containing class name from the APIC object\
                            model.
        :param parent:  Object to assign as the parent to the created objects.
        :param tenant:  Tenant object to assign the created objects.
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

    def find(self, search_object):
        """
        This will check to see if self is a match with ``search_object``
        and then call find on all of the children of search.
        If there is a match, a list containing self and any matches found
        by the children will be returned as a list.

        The criteria for a match is that all attributes of ``self`` are
        compared to all attributes of `search_object`.
        If ``search_object.<attr>`` exists and is the same as ``self.<attr>`` or
        ``search_object.<attr>`` is 'None', then that attribute matches.
        If all such attributes match, then there is a match and self will
        be returned in the result.

        If there is an attribute of ``search_object`` that does not exist in
        ``self``, it will be considered a mismatch.
        If there is an attribute of ``self`` that does not exist in
        ``search_object``, it will be ignored.

        :param search_object: ACI object to search
        :returns:  List of objects
        """
        result = []
        match = True
        for attrib in search_object.__dict__:
            value1 = getattr(search_object, attrib)
            if value1:
                if hasattr(self, attrib):
                    value2 = getattr(self, attrib)
                    if value1 != value2:
                        match = False
                        break
                else:
                    match = False
                    break
        if match:
            result.append(self)
        for child in self._children:
            result.extend(child.find(search_object))
        return result

    def info(self):
        """
        Node information summary.

        :returns: Formatted string that has a summary of all of the info\
                  gathered about the node.
        """
        text = ''
        textf = '{0:>15}: {1}\n'
        for attrib in self.__dict__:
            if attrib[0] != '_':
                text += textf.format(attrib, getattr(self, attrib))
        return text
