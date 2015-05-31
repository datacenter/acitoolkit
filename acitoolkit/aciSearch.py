__author__ = 'edsall'
#!/usr/bin/env python
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
# all the import


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
    def __init__(self, keyword, value=None, relation='primary'):
        """
        Creates report of basic switch information
        :param keyword: Keyword for a search
        :param value: Optional value for the keyword
        :param relation: Indication of whether the information is first hand, primary, or indirect
        """
        if isinstance(value, unicode):
            value = str(value)
        if isinstance(keyword, unicode):
            keyword = str(keyword)

        assert relation in ['primary', 'indirect']
        assert isinstance(value, str) or (value is None)

        self.value = value

        assert isinstance(keyword, str)
        self.keyword = keyword
        self.relation = relation
        self.context = []

    def add_context(self, aci_object):
        """
        Method to add an aciobject to a Searchable instance.  It will simply be appended to the end of the list

        :param aci_object: acitoolkit object
        """
        self.context.append(aci_object)

    def __str__(self):
        if len(self.context) > 0:
            primary_object = type(self.context[0])
        else:
            primary_object = 'None'
        return '{0:>18}::{1:<18} {2}'.format(self.keyword, self.value, primary_object)

    def __eq__(self, other):
        """
        Two searchables are equal if all the attributes are equal
        """
        if self.value != other.value:
            return False

        if self.keyword != other.keyword:
            return False

        if self.relation != other.relation:
            return False

        if len(self.context) != len(other.context):
            return False

        for index in range(len(self.context)):
            if self.context[index] != other.context[index]:
                return False

        return True



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
        Abstract method that should be implemented in each child object.
        It is here that all of the searchable instances are defined for
        the object.  They are placed in a list and returned as the result
        :rtype : list
        """
        result = []
        # result.append(Searchable(keyword, value, relationship))
        return result



