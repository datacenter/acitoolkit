################################################################################
#                                  _    ____ ___                               #
#                                 / \  / ___|_ _|                              #
#                                / _ \| |    | |                               #
#                               / ___ \ |___ | |                               #
#                         _____/_/   \_\____|___|_ _                           #
#                        |_   _|__   ___ | | | _(_) |_                         #
#                          | |/ _ \ / _ \| | |/ / | __|                        #
#                          | | (_) | (_) | |   <| | |_                         #
#                          |_|\___/ \___/|_|_|\_\_|\__|                        #
#                                                                              #
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""
This module implements the Base Class for creating all of the ACI Objects.
"""
import logging
from .aciSearch import AciSearch
from .acisession import Session


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


class Tag(object):
    def __init__(self, name=None):
        self.name = name
        self._deleted = False

    def is_deleted(self):
        return self._deleted

    def mark_as_deleted(self):
        self._deleted = True

    def __eq__(self, other):
        if isinstance(other, str):
            other = Tag(other)
        return self.name == other.name and self._deleted == other._deleted


class BaseACIObject(AciSearch):
    """
    This class defines functionality common to all ACI objects.
    Functions may be overwritten by inheriting classes.
    """
    def __init__(self, name=None, parent=None):
        """
        Constructor initializes the basic object and should be called by\
        the init routines of inheriting subclasses.

        :param name: String containing the name of the object\
                     instance
        :param parent: Parent object within the acitoolkit object model.
        """
        if isinstance(name, unicode):
            name = str(name)
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
        # self.subscribe = self._instance_subscribe
        # self.unsubscribe = self._instance_unsubscribe
        # self.has_events = self._instance_has_events
        # self.get_event = self._instance_get_event
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
    def _get_children_concrete_classes():
        """
        Get the acitoolkit class of the concrete children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return []

    @classmethod
    def get_deep_apic_classes(cls, include_concrete=False):
        """
        Get all the apic classes needed for this acitoolkit class and
        all of its children.
        :return: list of all apic classes
        """
        resp = cls._get_apic_classes()
        for child_class in cls._get_children_classes():
            resp.extend(child_class.get_deep_apic_classes(include_concrete=include_concrete))
        if include_concrete:
            for child_class in cls._get_children_concrete_classes():
                resp.extend(child_class.get_deep_apic_classes(include_concrete=include_concrete))

        return list(set(resp))

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
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return []

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

        :param tag: string containing the tag name or an instance of Tag
        :returns: True or False.  True indicates the object has this\
                  tag assigned.
        """
        if not isinstance(tag, Tag):
            search_tag = Tag(tag)
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

        :returns: List of tag instances
        """
        return self._tags

    def add_tag(self, tag):
        """
        Assign this object a particular tag.  Tags are strings that can be
        used to classify objects.  More than 1 tag can be assigned to an
        object.

        :param tag: string containing the tag to assign to this object or
                    an instance of Tag
        """
        if not isinstance(tag, Tag):
            tag = Tag(tag)
        self.get_tags().append(tag)

    def remove_tag(self, tag):
        """
        Remove a particular tag from being assigned to this object.
        Note that this does not delete the tag from the APIC.

        :param tag: string containing the tag to remove from this object
                    or an instance of Tag
        """
        if not isinstance(tag, Tag):
            search_tag = Tag(tag)
        self.get_tags().remove(tag)

    def delete_tag(self, tag):
        """
        Mark a particular tag as being deleted from this object.

        :param tag: string containing the tag to delete from this object
                    or an instance of Tag
        """
        if not isinstance(tag, Tag):
            tag = Tag(tag)
        for existing_tag in self.get_tags():
            if existing_tag == tag:
                existing_tag.mark_as_deleted()

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
    def get_deep(cls, full_data, working_data, parent=None, limit_to=[], subtree='full', config_only=False):
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
                    attribute_data = item[key]['attributes']
                    obj = cls(str(attribute_data['name']), parent)
                    obj._populate_from_attributes(attribute_data)
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

    def _instance_subscribe(self, session, extension=''):
        """
        not yet fully implemented
        """
        print ('_instance_subscribe for ', self.name)
        urls = self._get_instance_subscription_urls()
        for url in urls:
            resp = session.subscribe(url + extension)
            print ('Subscribed to ', url + extension, resp, resp.text)
            if not resp.ok:
                return resp
        return resp

    def _instance_has_events(self, session, extension=''):
        """
        Check for pending events from the APIC that pertain to this specific instance

        :param session:  the instance of Session used for APIC communication
        :param extension: Optional string that can be used to extend the URL
        :returns: True or False.  True if there are events pending.
        """
        urls = self._get_instance_subscription_urls()
        for url in urls:
            if session.has_events(url + extension):
                return True
        return False

    def _instance_get_event(self, session, extension=''):
        """
        Gets the event that is pending for this instance.  Events are
        returned in the form of objects.  Objects that have been deleted
        are marked as such.

        :param session:  the instance of Session used for APIC communication
        :param extension: Optional string that can be used to extend the URL
        :returns: list of objects
        """
        urls = self._get_instance_subscription_urls()
        for url in urls:
            url += extension
            if not session.has_events(url):
                continue
            event = session.get_event(url)
            for class_name in self.__class__._get_apic_classes():
                if class_name in event['imdata'][0]:
                    break
            attributes = event['imdata'][0][class_name]['attributes']
            status = str(attributes['status'])
            dn = str(attributes['dn'])
            parent = self.__class__._get_parent_from_dn(self.__class__._get_parent_dn(dn))
            if status == 'created':
                name = str(attributes['name'])
            else:
                name = self.__class__._get_name_from_dn(dn)
            obj = self.__class__(name, parent=parent)
            obj._populate_from_attributes(attributes)
            if status == 'deleted':
                obj.mark_as_deleted()
            return obj

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
            relation = BaseRelation(self, 'attached')
            if relation in item._attachments:
                item._attachments.remove(relation)
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

    def get_child(self, child_type, child_name):
        """
        Gets a specific immediate child of this object

        :param child_type: Class of the child to return
        :param child_name: Name of the child to return
        :return: The specific instance of child_type or None if not found
        """
        children = self.get_children(child_type)
        for child in children:
            if child.name == child_name:
                return child
        return None

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
            child_class.get(self._session, self)

        if deep:
            for child in self._children:
                child.populate_children(deep, include_concrete)

        return self._children

        # assert(deep is True or deep is False)
        # assert(include_concrete is True or include_concrete is False)
        # return None

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

    def _get_all_detached_relation(self, obj_class, relation_type=None):
        """Get all detached relations belonging to a particular class"""
        resp = []
        for relation in self._relations:
            same_obj_class = isinstance(relation.item, obj_class)
            same_relation_type = relation.relation_type == relation_type
            attached = relation.is_attached()
            if same_obj_class and not attached and same_relation_type:
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
            child = {'tagInst': {'attributes': {'name': tag.name}}}
            if tag.is_deleted():
                child['tagInst']['attributes']['status'] = 'deleted'
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

    @staticmethod
    def get_table(aci_object, title=''):

        """
        Abstract method that should be replaced by a version that is specific to
        the object
        :param aci_object:
        :param title:
        :return: list of Table objects
        """
        return [None]


class BaseACIPhysObject(BaseACIObject):
    """Base class for physical objects
    """

    def __init__(self, name='', parent=None, pod=None):
        self._session = None
        self.pod = None
        if pod:
            self.pod = pod
        else:
            if parent:
                self.pod = parent.pod
        super(BaseACIPhysObject, self).__init__(name=name, parent=parent)

    @staticmethod
    def _delete_redundant_policy(infra, policy_type):
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
        infra['infraInfra']['children'].extend(other_infra['infraInfra']['children'])

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
                        infra['infraInfra']['children'][first_occur]['infraFuncP']['children'].append(other_child)
                    del infra['infraInfra']['children'][idx]
        return phys_domain, fabric, infra

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

    @staticmethod
    def get_url(fmt='json'):
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

    def get_children(self, child_type=None):
        """Returns the list of children.  If childType is provided, then
        it will return all of the children of the matching type.

        :param child_type: This optional parameter will cause this method to\
                        return only those children\
                        that match the type of childType.  If this parameter\
                        is ommitted, then all of the children will be returned.

        :returns: list of children
        """
        if child_type:
            children = []
            for child in self._children:
                if isinstance(child, child_type):
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

        # TODO: this does not work.  There are more parameters in the .get method.
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

    @staticmethod
    def check_session(session):
        """
        This will check that the session is of type Session and raise exception if it not
        :param session: the session to check
        :return:
        """

        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

    @classmethod
    def check_parent(cls, parent):
        """
        If a parent is specified, it will check that it is the correct class of parent
        If not, then an exception is raised.
        :param parent:
        :return:
        """
        if parent:
            if not isinstance(parent, cls._get_parent_class()):
                raise TypeError('The parent of this object must be of class {0}'.format(cls._get_parent_class()))


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
        super(BaseACIPhysModule, self).__init__(name='', parent=None)

        self.pod = str(pod)
        self.node = str(node)
        self.slot = str(slot)
        self.serial = None
        self.model = None
        self.dn = None
        self.descr = None
        self.bios = None
        self.firmware = None

        # self._apic_class = None
        self.dn = None

        if parent:
            if not isinstance(parent, str):
                self._parent = parent
                self._parent.add_child(self)

        logging.debug('Creating %s %s', self.__class__.__name__,
                      'pod-' + self.pod + '/node-' + self.node + '/slot-' + self.slot)

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
               (self.slot == other.slot) and (self.get_type() == other.type)

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
    def get_obj(cls, session, apic_classes, parent_node):
        """Gets all of the Nodes from the APIC.  This is called by the
        module specific get() methods.  The parameters passed include the
        APIC object class, apic_classes, so that this will work for
        different kinds of modules.

        :param parent_node: parent object or node id
        :param session: APIC session to use when retrieving the nodes
        :param apic_classes: The object class in APIC to retrieve
        :returns: list of module objects derived from the specified apic_classes

        """
        cls.check_session(session)

        node = None
        if parent_node:
            if not isinstance(parent_node, str):
                cls.check_parent(parent_node)
                node = parent_node.node
            else:
                node = parent_node
        pod = '1'
        if parent_node:
            parent_dn = 'topology/pod-{0}/node-{1}/sys'.format(pod, node)
            interface_query_url = '/api/mo/' + parent_dn + \
                                  '.json?query-target=subtree&target-subtree-class=' + ','.join(apic_classes)
        else:
            interface_query_url = ('/api/node/class/' + apic_classes[0] + '.json?'
                                                                     'query-target=self')
        cards = []
        ret = session.get(interface_query_url)
        card_data = ret.json()['imdata']
        for apic_obj in card_data:
            if apic_classes[0] in apic_obj:
                dist_name = str(apic_obj[apic_classes[0]]['attributes']['dn'])
                (pod, node_id, slot) = cls._parse_dn(dist_name)
                card = cls(pod, node_id, slot)
                card._session = session
                card._populate_from_attributes(apic_obj[apic_classes[0]]['attributes'])

                (card.firmware, card.bios) = card._get_firmware(dist_name)
                if parent_node:
                    if card.node == parent_node.node:
                        if not isinstance(parent_node, str):
                            card._parent = parent_node
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
        self.modify_time = str(attributes['modTs'])

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
        return firmware, bios

    def get_serial(self):
        """Returns the serial number.
        :returns: serial number string
        """
        return self.serial


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
        """
        Returns the port selector.

        :return:
        """
        return self._get_port_selector_json('accportgrp',
                                            self._get_name_for_json())

    def get_port_channel_selector_json(self, port_name):
        return self._get_port_selector_json('accbundle', port_name)
