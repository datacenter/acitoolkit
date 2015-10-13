################################################################################
################################################################################
# #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
# #
# Licensed under the Apache License, Version 2.0 (the "License"); you may   #
# not use this file except in compliance with the License. You may obtain   #
# a copy of the License at                                                  #
# #
# http://www.apache.org/licenses/LICENSE-2.0                           #
# #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""  ACISearch: Search application for ACI fabrics

    This file contains the main engine for the search tool that handles
    getting the search keywords and value along with the associated objects.
    It can then return a list of objects that match either the keyword, the value
    or the keyword, value pair.
    It runs as a standalone tool in addition, it can be imported as a library
    such as when used by the GUI frontend.
"""
import datetime
import os.path
import pickle
import sys
from acitoolkit import LogicalModel, ConcreteBD, Tenant, BridgeDomain, Context, Contract

from acitoolkit.aciphysobject import Session, Fabric, PhysicalModel, Node
from acitoolkit.acitoolkitlib import Credentials
from requests import Timeout, ConnectionError


class LoginError(Exception):
    """
    Exception for login errors.
    """
    pass


class SearchDb(object):
    """
    The primary search object that holds all the methods for building the search index as well as querying it.
    """

    def __init__(self):
        """
        Will load in all of the search objects and create
        an index by keyword, value, and keyword value pair.
        """
        self.by_key = {}
        self.by_value = {}
        self.by_key_value = {}
        self.save_file = 'search.p'
        self._session = None
        self.args = None
        self.timeout = None
        self.keywords = []
        self.values = []
        self.ranked_items = {}
        self.map_class = {}  # index of objects by their class

    def lookup_keyword(self, keyword):
        """
        This will return a list of searchable objects that
        are indexed to keyword
        :param keyword:
        :return: list of searchables
        """
        return self.by_key.get(keyword)

    def lookup_value(self, value):
        """
        This will return a list of searchable objects that
        are indexed to value.  If nothing is found, it will
        return `None`
        :param value: str value to search for
        :return: list of searchables
        """

        if value is None:
            return None

        return self.by_value.get(value)

    def lookup_keyword_value(self, keyword, value):
        """
        This will return a list of searchable objects that
        are indexed to a (keyword, value) pair
        :param value:
        :param keyword:
        :return: list of searchables
        """

        return self.by_key_value.get((keyword, value))

    def get_keywords(self):

        """
        gets a sorted list of the key words

        :return:
        """
        return sorted(self.by_key.keys())

    def get_values(self):
        """
        gets a sorted list of the values used in the index

        :return:
        """
        return sorted(self.by_value.keys())

    @staticmethod
    def load_db(force_reload=False, args = None):

        """
        Will load the search data from a saved search.p file if it exists, otherwise it will
        create a new one by reading the APIC

        If the force_reload option is true, it will reload the data from the APIC and save it irrespective of whether
        the search.p file already exists

        :param force_reload:
        """
        sdb = SearchDb()
        if args :
            sdb.set_login_credentials(args)
        # TODO: provide a way to save multiple different APIC dBs.
        if not sdb.file_exists(sdb.save_file) or force_reload or True:
            print 'load from APIC',
            fabric = Fabric.get(sdb.session)[0]
            print '.',
            fabric.populate_children(deep=True, include_concrete=True)
            print '...done'

            searchables = fabric.get_searchable()
            print 'Indexing',
            sdb.index_searchables(searchables)
            print '.',
            sdb.create_object_directory(fabric)
            sdb.save_db()
            print '...done'
        else:
            print 'loading from file',
            p_file = open(sdb.save_file, "rb")
            print '.',
            # (self.object_directory, self.by_key_value, self.by_key, self.by_value) = pickle.load(p_file)
            sdb = pickle.load(p_file)

            print '..done'

        sdb.keywords = sdb.get_keywords()
        sdb.values = sdb.get_values()
        sdb.cross_reference_objects()
        return sdb

    def save_db(self):
        """
        pickle the indexed data structures and save in search.p

        """
        #pickle.dump((self.object_directory, self.by_key_value, self.by_key, self.by_value), open(self.save_file, "wb"))
        pickle.dump(self, open(self.save_file, "wb"))

    @staticmethod
    def file_exists(file_name):
        """
        simply checks for the existence of the indicated file
        :param file_name: file name string
        """
        if os.path.isfile('./' + file_name):
            return True
        return False

    def index_searchables(self, searchables):

        """
        index all the searchable items by key_value, key, and value
        :param searchables: List of searchable objects
        """
        t1 = datetime.datetime.now()
        count = 0
        self.by_key = {}
        self.by_value = {}
        self.by_key_value = {}

        # index searchables by keyword, value and keyword/value
        for searchable in searchables:
            count += 1
            if count % 1000 == 0:
                print count
            atk_class = searchable.object_class
            if atk_class not in self.by_key:
                self.by_key[atk_class] = set([])
            self.by_key[atk_class].add(searchable)

            for term in searchable.terms:

                (keyword, value, relation) = term

                if keyword not in self.by_key:
                    self.by_key[keyword] = set([])
                self.by_key[keyword].add(searchable)

                if value is not None:
                    if value not in self.by_value:
                        self.by_value[value] = set([])

                    self.by_value[value].add(searchable)

                    if (keyword, value) not in self.by_key_value:
                        self.by_key_value[(keyword, value)] = set([])

                    self.by_key_value[(keyword, value)].add(searchable)

        t2 = datetime.datetime.now()
        print 'elapsed time', t2 - t1

    def create_object_directory(self,root):
        """
        Will create a dictionary of all the atk objects indexed by their dn.
        :param root:
        :return:
        """
        self.object_directory = {}
        self._add_dir_entry(root)

    def _add_dir_entry(self, root):
        """
        Will recursively add each object and its children to directory
        :param root:
        :return:
        """
        attrs = root.get_attributes()
        if 'dn' not in attrs:
            print 'no guid'
        guid = attrs['dn']
        if guid in self.object_directory:
            print 'Duplicate guid', guid

        self.object_directory[guid] = root
        for child in root.get_children():
            self._add_dir_entry(child)

        #build class map
        if root.__class__.__name__ not in self.map_class:
            self.map_class[root.__class__.__name__] = []

        self.map_class[root.__class__.__name__].append(root)

    def cross_reference_objects(self):
        """
        Will go through various objects and add gui cross reference related information
        such as adding switches to a tenant object
        :return:
        """

        # map tenants to switches
        for tenant in self.map_class['Tenant']:
            for concrete_bd in self.map_class['ConcreteBD']:
                ctenant_name = concrete_bd.attr['tenant']
                if ctenant_name == tenant.name:
                    switch = concrete_bd._parent
                    self._add_relation('switches', switch, tenant)
                    self._add_relation('tenants', tenant, switch)

        for bridge_domain in self.map_class['BridgeDomain']:
            for concrete_bd in self.map_class['ConcreteBD']:
                if ':' in concrete_bd.attr['name']:
                    cbd_name = concrete_bd.attr['name'].split(':')[-1]
                else:
                    cbd_name = concrete_bd.attr['name']

                if cbd_name == bridge_domain.name and concrete_bd.attr['tenant']==bridge_domain._parent.name:
                    switch = concrete_bd._parent
                    self._add_relation('switches', switch, bridge_domain)
                    self._add_relation('bridge domains', bridge_domain, switch)

                    self._add_relation('concrete BD', concrete_bd, bridge_domain)
                    self._add_relation('logical BD', bridge_domain, concrete_bd)

            relations = bridge_domain._relations
            for relation in relations:
                if isinstance(relation.item, Context):
                    self._add_relation('context', relation.item, bridge_domain)
                    self._add_relation('bridge domains',bridge_domain, relation.item)

        for context in self.map_class['Context']:
            for concrete_bd in self.map_class['ConcreteBD']:
                ccontext_name = concrete_bd.attr['context']
                if ccontext_name == context.name and concrete_bd.attr['tenant']==context._parent.name:
                    switch = concrete_bd._parent
                    self._add_relation('switches', switch, context)
                    self._add_relation('contexts', context, switch)

        for ep in self.map_class['Endpoint']:
            epg = ep._parent
            app_profile = epg._parent
            tenant = app_profile._parent
            self._add_relation('endpoints', ep, app_profile)
            self._add_relation('endpoints', ep, tenant)
            self._add_relation('tenant', tenant, ep)
            self._add_relation('app profile', app_profile, ep)

        for epg in self.map_class['EPG']:
            relations = epg._relations
            for relation in relations:
                if isinstance(relation.item, Contract):
                    if relation.relation_type == 'consumed':
                        self._add_relation('consumes', relation.item, epg)
                        self._add_relation('consumed by', epg, relation.item)
                    elif relation.relation_type == 'provided':
                        self._add_relation('provides', relation.item, epg)
                        self._add_relation('provided by', epg, relation.item)
                    else:
                        print 'unexpected relation type', relation.relation_type
                if isinstance(relation.item, BridgeDomain):
                    self._add_relation('bridge domain',relation.item, epg)
                    self._add_relation('epgs', epg, relation.item)

    @staticmethod
    def _add_relation(relationship_type, child_obj, parent_obj ):
        """
        Will add child_obj to parent_obj with the relationship type
        :param child_obj:
        :param parent_obj:
        :return:
        """
        if 'gui_x_reference' not in parent_obj.__dict__:
            parent_obj.gui_x_reference = {}

        if isinstance(child_obj, BridgeDomain) or isinstance(child_obj, Context) :
            child_name = child_obj._parent.name+':'+child_obj.name
        else:
            child_name = child_obj.name

        record = {'class': child_obj.__class__.__name__, 'name': child_name, 'dn': child_obj.dn}
        if relationship_type not in parent_obj.gui_x_reference:
            parent_obj.gui_x_reference[relationship_type] = []

        for existing_record in parent_obj.gui_x_reference[relationship_type]:
            if record['dn']==existing_record['dn']:
                return
        parent_obj.gui_x_reference[relationship_type].append(record)

    @property
    def session(self):
        """
        session property will return an active session that has been logged in
        If a login had not previously occurred, it will proactively login first.
        :return: Session
        """
        if self._session is None:
            if self.args is not None:
                if self.args.login is not None:
                    self._session = Session(self.args.url, self.args.login, self.args.password)
                    resp = self.session.login(self.timeout)
                else:
                    raise LoginError
            else:
                raise LoginError
            if not resp.ok:
                raise LoginError
        return self._session

    def set_login_credentials(self, args, timeout=2):
        """
        Login to the APIC

        :param args: An instance containing the APIC credentials.  Expected to
                     have the following instance variables; url, login, and
                     password.
        :param timeout:  Optional integer argument that indicates the timeout
                         value in seconds to use for APIC communication.
                         Default value is 2.
        """
        self.args = args
        self.timeout = timeout
        self.clear_switch_info()

    def clear_switch_info(self):
        """
        This will clear out the switch info to force a reload of the switch information from the APIC.
        :return:
        """
        self._session = None

    def get_object_info(self, obj_dn):
        """
        Will return dictionary containing all of the information in the
        object
        :param obj_dn:
        :return:
        """
        result = {}
        atk_obj = self.object_directory[obj_dn]
        attr = atk_obj.get_attributes()

        result['properties'] = {'class': atk_obj.__class__.__name__,'name': attr['name'],'dn':obj_dn}

        result['attributes'] = atk_obj.get_attributes()

        if atk_obj._parent is not None:
            parent = atk_obj._parent.get_attributes()['name']
            parent_dn = atk_obj._parent.get_attributes()['dn']
            parent_class = atk_obj._parent.__class__.__name__
            result['parent'] = {'class':parent_class, 'name':parent, 'dn':parent_dn}
        # else:
        #     result['parent'] = {'class':'None','name':'', 'dn':''}

        children = atk_obj.get_children()
        result['children'] = {}
        for child in children:
            child_class = child.__class__.__name__
            if child_class not in result['children']:
                result['children'][child_class] = []

            result['children'][child_class].append({'class': child.__class__.__name__,
                                                    'name': child.get_attributes()['name'],
                                                    'dn': child.get_attributes()['dn']})

        if 'gui_x_reference' in atk_obj.__dict__:
            result['relations'] = atk_obj.gui_x_reference

        return result

    def get_node_relations(self, atk_obj, result):
        """
        Will add additional relations to the object result as appropriate
        :param result:
        :return:
        """
        if atk_obj.role != 'leaf':
            if 'relations' not in result:
                result['relations'] = {}
            result['relations']['tenants'] = []
            bridge_domains = atk_obj.get_children(ConcreteBD)
            local_tenants = set()
            for bd in bridge_domains:
                local_tenants.add = bd.attr['tenant']
            logical_tenant = []
            for tenant in local_tenants:
                logical_tenant.append(self.map_tenant[tenant])

            for l_tenant in logical_tenant:
                result['relations']['tenant'].append({'class':l_tenant.__class__.__name__,
                                                      'name': l_tenant.name,
                                                      'dn': l_tenant.dn})

    def search(self, term_string):
        """
        This will do the actual search.  The data must already be loaded and indexed before this is invoked.
        :param term_string: string that contains all the terms.
        """
        t1 = datetime.datetime.now()
        terms = get_terms(term_string)
        results = []
        for term in terms:
            t_result = None
            if '::' in term:
                (k, v) = term.split('::')
                if k and v:
                    print 'kv match', term
                    t_result = (term, self.lookup_keyword_value(k, v))
                elif k:
                    print 'v match', term
                    t_result = (term, self.lookup_value(term))
                elif v:
                    print 'k match', term
                    t_result = (term, self.lookup_keyword(term))
            elif term in self.keywords:
                print 'k match', term
                t_result = (term, self.lookup_keyword(term))
            elif term in self.values:
                print 'v match', term
                t_result = (term, self.lookup_value(term))
            else:
                print 'no match', term
            if t_result is not None:
                if t_result[1] is not None:
                    results.append({'result':t_result, 'primaries':set(elem.primary for elem in t_result[1])})

        results2 = self.rank_results(results)
        t2 = datetime.datetime.now()
        print 'elapsed time', t2 - t1
        return results2

    def rank_results(self, unranked_results):
        """
        Will assign a score to each result item according to how relevant it is.  Higher numbers are more relevant.
        unranked_results is a list of results.  Each of the results is a tuple of the matching term and a list of
        items that have that term.
        :param unranked_results:
        """
        master_items = set()
        for results in unranked_results:
            if results['result'][1] is not None:
                master_items = master_items | results['result'][1]

        self.ranked_items = {}
        for item in master_items:
            #self.ranked_items[item] = [0, 0, set()]  # score, sub-score, matching terms
            self.ranked_items[item] = {'pscore':0, 'sscore':0, 'terms':set()}  # score, sub-score, matching terms

        # now calculate sub-score
        # sub-score is one point for any term that is not a primiary hit, but is a secondary hit
        # a primary hit is one where the term directly found the item
        # a secondary hit is one where the term found an item in the heirarchy of the primary item
        #
        # The max sub-score is cumulative, i.e. a sub-score can be greater than the number of terms

        # Check all permutations of term results and calculate score
        print 'start ranking'
        for p_results in unranked_results:
            items = p_results['result'][1]
            for s_results in unranked_results:
                s_primaries = s_results['primaries']
                for item in items:
                    if self.is_primary(item.primary, s_primaries):
                        self.ranked_items[item]['pscore'] += 1
                        self.ranked_items[item]['terms'].add(s_results['result'][0])
                    elif self.is_secondary(item, s_primaries):
                            self.ranked_items[item]['sscore'] += 1
                            self.ranked_items[item]['terms'].add(s_results['result'][0])
        print 'end ranking'
        resp = []
        count = 0
        for result in sorted(self.ranked_items,
                             key=lambda x: (self.ranked_items[x]['pscore'], self.ranked_items[x]['sscore']), reverse=True):

            count += 1
            record = {'pscore': self.ranked_items[result]['pscore'],
                      'sscore': self.ranked_items[result]['sscore'],
                      'name': str(result.primary.name),
                      'path': result.path(),
                      'terms': str('[' + ', '.join(self.ranked_items[result]['terms']) + ']'),
                      'object_type': result.primary.__class__.__name__}
            # record['primary'] = result.primary
            tables = result.primary.get_table([result.primary])
            record['report_table'] = []
            for table in tables:
                if table is not None:
                    record['report_table'].append({'data': table.data,
                                                   'headers': table.headers,
                                                   'title_flask': table.title_flask})
            resp.append(record)
            if count > 100:
                break

        return resp, len(self.ranked_items)

    @staticmethod
    def is_primary(item, p_set):
        """
        will return true if the item is a primary item in the result set
        :param item:
        :param p_set:
        :return:
        """
        return item in p_set

    @classmethod
    def is_secondary(cls, item, s_set):
        """
        Will return true if any item in the item context, excluding the first or primary one, is in s_set

        :param item:
        :param s_set:
        :return:
        """
        return any(
            cls.is_primary(item_context, s_set)
            for item_context in item.context[1:])

    @staticmethod
    def find_primary_in_path(searchable, primary):
        """
        Will go through the context stack and return true if 'primary' is found
        :param searchable:
        :param primary:
        :return: boolean
        """
        if primary in searchable.context:
            return True
        else:
            return False

    def get_search_result(self, terms_string):
        """
        will do search and return records that allow the results to be displayed in GUI
        :param terms_string:
        """
        results = self.search(terms_string)

        return results


def get_terms(strng):
    """
    Will return a list of the separate search terms
    :param strng:
    :return:
    """
    terms = strng.split()
    clean_terms = []
    for term in terms:
        clean_terms.append(term.strip())
    return clean_terms


def main():
    """
    Main execution path when run from the command line
    """
    # Get all the arguments
    description = 'Search tool for APIC.'
    creds = Credentials('apic', description)
    creds.add_argument('-s', '--switch',
                       type=str,
                       default=None,
                       help='Specify a particular switch id to perform search on, e.g. "102"')
    creds.add_argument('-f', '--find',
                       type=str,
                       help='search string')
    creds.add_argument('--force',
                       action="store_true",
                       default=False,
                       help='Force a rebuild of the search index')

    args = creds.get()
    print args
    #sdb = SearchDb()
    #sdb.set_login_credentials(args)
    try:
        sdb = SearchDb.load_db(args.force, args)
    except (LoginError, Timeout, ConnectionError):
        print '%% Could not login to APIC'
        sys.exit(0)

    results = sdb.search(args.find)
    count = 0
    for res in results:
        count += 1
        print 'score', res['pscore'], res['sscore'], res['terms'], res['title'], res['path']
        tables = res['primary'].get_table([res['primary'], ])
        for table in tables:
            if table.data:
                print table.get_text()
        if count > 10:
            print 'Showing 10 of', len(results), 'results'
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
