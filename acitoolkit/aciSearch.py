# !/usr/bin/env python
################################################################################
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
Implements the Searchable class
"""


class Searchable(object):
    """
    This class hold a search term as a keyword, value pair and a list
    of acitoolkit objects that are related to that term.  The first item on the list is
    the object where the term came from and is considered a "primary" object.  Subsequent objects
    on the list are added as the instance of Searchable is passed up the object heirarchy and
    they provide context for the primary object.

    For example, a search term might be an ip address.  The list might then objects representing, in order,
    [endpoint, epg, applicatin profile, tenant, aci fabric].  The endpoint is the primary object, i.e. the object
    that has the ip address.  That endpoint is then a member of the epg which is in the application profile which
    is in the tenant which is deployed on the fabric.

    The relationship of the search term to the primary acitoolkit object can either be `direct` or `indirect`.
    A `direct` relationship is one where the object is a primary source or the source closest to where the search term
    comes from.  An `indirect` relationship is one where the object has learned the information from some other place
    or has be informed of the information from another place.

    An example might be the ip address of a tunnel end-point.  If switch A learns the address of switch B, then switch
    A has an `indirect` relation to the address while switch B would have a `direct` relation to that address.

    This `direct`/`indirect` relationship can be used by an application that is displaying the information to
    prioritize which ones are displayed first, i.e. to rank them.
    """
    def __init__(self, dirty_terms=()):
        """
        Creates a search item which is the list of search terms, the items the search terms come from
        and the context of the item.
        """
        self.terms = set()
        self.attr = set()
        self.value = set()
        self.attr_value = set()
        for term in dirty_terms:
            keyword, value = term[:2]
            relation = term[2] if len(term) == 3 else 'primary'
            self.add_term(keyword, value, relation)
        self.context = []

    def add_term(self, attr, value=None, relation='primary'):
        """
        Will add a search attr, value pair to the searchable item
        It will also add the relation.
        :param attr:
        :param value:
        :param relation:
        """
        if isinstance(value, unicode):
            value = str(value)
        if isinstance(attr, unicode):
            attr = str(attr)

        assert relation in ['primary', 'secondary']
        assert isinstance(value, str) or (value is None)
        assert isinstance(attr, str)

        self.terms.add((attr, value, relation))
        self.attr.add(attr)
        self.value.add(value)
        self.attr_value.add((attr, value))

    @property
    def primary(self):
        """
        Will return the first item of the context which is the current item.

        :return:
        """
        if len(self.context) > 0:
            return self.context[0]
        else:
            return 'None'

    @property
    def object_class(self):
        """
        will return the acitoolkit class of the primary item as a string
        :return: str
        """
        return self.primary.__class__.__name__

    def add_context(self, aci_object):
        """
        Method to add an aciobject to a Searchable instance.  It will simply be appended to the end of the list

        :param aci_object: acitoolkit object
        """
        self.context.append(aci_object)

    def __str__(self):
        return '{} {}'.format(self.primary, self.path())

    def path(self):
        """
        Will return a string which is contructed by putting a slash between the names of all the items in the context

        :return:
        """
        path = self.primary.dn
        return path

    def __key(self):

        return self.primary

    def __eq__(self, y):
        return self.__key() == y.__key()

    def __hash__(self):
        return hash(self.__key())


class AciSearch(object):
    """
    This class is a base class that creates a method for rolling up through the object heirarchy all of the
    Searchable instances.
    """

    def get_searchable(self):
        """
        Method to recursively retrieve all of the searchable items from all the children objects, add
        the current object to them as additional context, append the local searchable terms, and
        return the result.
        """

        searchables = self._define_searchables()
        for child in self._children:
            searchables.extend(child.get_searchable())
        for searchable in searchables:
            searchable.add_context(self)
        return searchables

    def _define_searchables(self):
        """
        Abstract method that should be called in each child object.
        It is here that all of the searchable instances are defined for
        the object.  They are placed in a list and returned as the result
        :rtype : list
        """
        result = Searchable()
        atk_attrs = self.get_attributes()
        for atk_attr in atk_attrs:
            if atk_attrs[atk_attr] is not None:
                if isinstance(atk_attrs[atk_attr], list):
                    attr_list = atk_attrs[atk_attr]
                    for attr in attr_list:
                        if isinstance(atk_attrs[atk_attr], str) or isinstance(atk_attrs[atk_attr], bool):
                            result.add_term(atk_attr, str(attr))
                        #     print(atk_attr, str(attr))
                        # else:
                        #     print("wrong type %s" % str(atk_attr))
                elif not isinstance(atk_attrs[atk_attr], str) and not isinstance(atk_attrs[atk_attr], bool):
                    # print("wrong type %s" % str(atk_attr))
                    pass
                else:
                    result.add_term(atk_attr, str(atk_attrs[atk_attr]))
        return [result]

    @staticmethod
    def _dedup_searchables(result):

        deduped = []
        for item in result:
            if item not in deduped:
                deduped.append(item)
        return deduped
