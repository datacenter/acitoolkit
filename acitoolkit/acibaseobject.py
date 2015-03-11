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
        self._attachments = []
        self._tags = []
        self._parent = parent
        self.descr = None
        self.subscribe = self._instance_subscribe
        self.unsubscribe = self._instance_unsubscribe
        logging.debug('Creating %s %s', self.__class__.__name__, name)
        if self._parent is not None:
            if self._parent.has_child(self):
                self._parent.remove_child(self)
            self._parent.add_child(self)

    @classmethod
    def _get_subscription_urls(cls):
        """
        Gets the set of URLs used to subscribe to class changes
        in the APIC.

        :returns: Set of URL strings
        """
        resp = []
        for class_name in cls._get_apic_classes():
            resp.append('/api/class/%s.json?subscription=yes' % class_name)
        return resp

    def _get_instance_subscription_urls(self):
        """
        Gets the set of URLs used to subscribe to instance changes
        in the APIC.

        :returns: Set of URL strings
        """
        raise NotImplementedError

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by the acitoolkit class.
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: list of strings containing APIC class names
        """
        raise NotImplementedError

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        raise NotImplementedError

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        raise NotImplementedError

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Parse the name out of a dn string.
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing name
        """
        raise NotImplementedError

    @classmethod
    def _get_toolkit_to_apic_classmap(cls):
        """
        Gets the APIC class to an acitoolkit class mapping dictionary
        :returns: dict of APIC class names to acitoolkit classes
        """
        return {}

    def _extract_attributes(self, attributes):
        """
        Used internally by get_deep to populate the attributes
        Will be overridden when necessary

        :param attributes: data to extract attributes from
        """
        pass

    def _extract_relationships(self, data):
        """
        Used internally by get_deep to populate the relationships
        Will be overridden when necessary.  The default implementation
        is here.

        :param data: data to extract relationships from
        """
        for child in self.get_children():
            child._extract_relationships(data)

    def has_tag(self, tag):
        """
        Checks whether this object has a particular tag assigned.

        :param tag: string containing the tag
        :returns: True or False.  True indicates the object has this\
                  tag assigned.
        """
        return tag in self.get_tags()

    def has_tags(self):
        """
        Checks whether this object has any tags assigned at all.

        :returns: True or False.  True indicates the object has at least one \
                  tag assigned.
        """
        return len(self.get_tags()) > 0

    def get_tags(self):
        """
        Get the tags assigned to this object.

        :returns: List of tag strings
        """
        return self._tags

    def add_tag(self, tag):
        """
        Assign this object a particular tag.  Tags are strings that can be
        used to classify objects.  More than 1 tag can be assigned to an
        object.

        :param tag: string containing the tag to assign to this object
        """
        self.get_tags().append(tag)

    def remove_tag(self, tag):
        """
        Remove a particular tag from being assigned to this object.

        :param tag: string containing the tag to assign to this object
        """
        self.get_tags().remove(tag)

    @classmethod
    def _get_parent_from_dn(cls, dn):
        """
        Derive the parent object using a dn

        :param dn: String containing a distinguished name of an object
        """
        parent_class = cls._get_parent_class()
        if parent_class is None:
            return None
        parent_name = parent_class._get_name_from_dn(dn)
        parent_dn = cls._get_parent_dn(dn)
        parent_obj = parent_class(parent_name,
                                  parent_class._get_parent_from_dn(parent_dn))
        return parent_obj

    @classmethod
    def get_deep(cls, full_data, working_data, parent=None):
        """
        Gets all instances of this class from the APIC and gets all of the
        children as well.

        :param full_data:
        :param working_data:
        :param parent:
        """
        for item in working_data:
            for key in item:
                if key in cls._get_apic_classes():
                    obj = cls(str(item[key]['attributes']['name']), parent)
                    obj._extract_attributes(item[key]['attributes'])
                    if 'children' in item[key]:
                        for child in item[key]['children']:
                            for apic_class in child:
                                class_map = cls._get_toolkit_to_apic_classmap()
                                if apic_class not in class_map:
                                    if apic_class == 'tagInst':
                                        obj._tags.append(str(child[apic_class]['attributes']['name']))
                                    continue
                                else:
                                    class_map[apic_class].get_deep(full_data=full_data,
                                                                   working_data=[child],
                                                                   parent=obj)
        return obj

    @classmethod
    def subscribe(cls, session):
        """
        Subscribe to events from the APIC that pertain to instances of this
        class.

        :param session:  the instance of Session used for APIC communication
        """
        urls = cls._get_subscription_urls()
        for url in urls:
            resp = session.subscribe(url)
            if resp is not None:
                if not resp.ok:
                    return resp
        return resp

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

    @classmethod
    def has_events(cls, session):
        """
        Check for pending events from the APIC that pertain to instances
        of this class.

        :param session:  the instance of Session used for APIC communication
        :returns: True or False.  True if there are events pending.
        """
        urls = cls._get_subscription_urls()
        for url in urls:
            if session.has_events(url):
                return True
        return False

    def _instance_subscribe(self, session):
        """
        not yet fully implemented
        """
        url = self._get_instance_subscription_url()
        resp = session.subscribe(url)
        return resp

    @classmethod
    def unsubscribe(cls, session):
        """
        Unsubscribe for events from the APIC that pertain to instances of this
        class.

        :param session:  the instance of Session used for APIC communication
        """
        for class_name in cls._get_apic_classes():
            url = '/api/class/%s.json?subscription=yes' % class_name
            session.unsubscribe(url)

    def _instance_unsubscribe(self):
        """
        _instance_unsubscribe: to be implemented
        """
        pass

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
            item._attachments.remove(BaseRelation(self, 'attached'))
        self._relations.append(BaseRelation(item, 'attached'))
        item._attachments.append(BaseRelation(self, 'attached'))

    def _check_relation(self, item, status):
        """
        Internal function to return whether a relation exists to the
        specified item with the given status.

        :returns: True or False, True indicates the relation exists.
        """
        check = BaseRelation(item, status)
        return check in self._relations

    def is_attached(self, item):
        """
        Indicates whether the item is attached to this object/
        :returns: True or False, True indicates the item is attached.
        """
        return self._check_relation(item, 'attached')

    def is_detached(self, item):
        """
        Indicates whether the item is detached from this object.
        :returns: True or False, True indicates the item is detached.
        """
        return self._check_relation(item, 'detached')

    def detach(self, item):
        """
        Detach the object from the other object.
        A relationship is either 'attached', 'detached', or does not exist.\
        A detached relationship will cause the relationship to be deleted\
        when pushed to the APIC.

        :param item:  Object to be detached.
        """
        if self.is_attached(item):
            self._relations.remove(BaseRelation(item, 'attached'))
            item._attachments.remove(BaseRelation(self, 'attached'))
        if not self.is_detached(item):
            self._relations.append(BaseRelation(item, 'detached'))
            item._attachments.append(BaseRelation(self, 'detached'))

    def _check_attachment(self, item, status):
        """
        Internal function to return whether an attachment exists to the
        specified item with the given status.

        :returns: True or False, True indicates the attachment exists.
        """
        check = BaseRelation(item, status)
        return check in self._attachments

    def has_attachment(self, item):
        """
        Indicates whether this object is attached to the item/
        :returns: True or False, True indicates the object is attached.
        """
        return self._check_attachment(item, 'attached')

    def has_detachment(self, item):
        """
        Indicates whether the object is detached from this item.
        :returns: True or False, True indicates the object is detached.
        """
        return self._check_attachment(item, 'detached')

    def get_children(self, only_class=None):
        """
        Get a list of the immediate child objects of this object.

        :param only_class: Optional parameter that will be used to limit the\
                           objects returned to only those belonging to the\
                           class passed in this parameter.
        :returns: List of children objects.
        """
        if only_class is not None:
            resp = []
            for child in self._children:
                if isinstance(child, only_class):
                    resp.append(child)
            return resp
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
        assert(deep is True or deep is False)
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

    def _get_all_relations_by_class(self, relations, attached_class,
                                    status='attached'):
        """
        Internal function to get relations or attachments for a given class.

        :param relations: list of relations or attachments
        :param attached_class:  The class that is the subject of the search.
        :param status:  Valid values are 'attached' and 'detached'.\
                        Default is 'attached'.
        """
        resp = []
        for relation in relations:
            same_class = isinstance(relation.item, attached_class)
            same_status = relation.status == status
            if same_class and same_status:
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
        return self._get_all_relations_by_class(self._relations,
                                                attached_class,
                                                status)

    def get_all_attachments(self, attached_class, status='attached'):
        """
        Get all of the attachments to an object belonging to the
        specified class with the specified status.

        :param attached_class:  The class that is the subject of the search.
        :param status:  Valid values are 'attached' and 'detached'.\
                        Default is 'attached'.
        """
        return self._get_all_relations_by_class(self._attachments,
                                                attached_class,
                                                status)

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
        for tag in self._tags:
            child = {'tagInst': {'attributes': {'name': tag}}}
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
        if self.descr:
            attributes['descr'] = self.descr
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
        If ``search_object.<attr>`` exists and is the same as ``self.<attr>``
        or ``search_object.<attr>`` is 'None', then that attribute matches.
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
        textf = '{0:>16}: {1}\n'
        for attrib in self.__dict__:
            if attrib[0] != '_':
                text += textf.format(attrib, getattr(self, attrib))
        return text

    def infoList(self):
        """
        Node information.  Returns a list of (attr, value) tuples.

        :returns: list of [(attr, value),]
        """
        result = []
        for attrib in self.__dict__:
            if attrib[0] != '_':
                result.append((attrib, getattr(self, attrib)))
        return result
