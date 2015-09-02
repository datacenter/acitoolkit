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

from acitoolkit.aciphysobject import Session, Fabric
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

    def load_db(self, force_reload=False):

        """
        Will load the search data from a saved search.p file if it exists, otherwise it will
        create a new one by reading the APIC

        If the force_reload option is true, it will reload the data from the APIC and save it irrespective of whether
        the search.p file already exists

        :param force_reload:
        """
        # TODO: provide a way to save multiple different APIC dBs.
        if not self.file_exists(self.save_file) or force_reload:
            print 'load from APIC',
            fabric = Fabric.get(self.session)[0]
            print '.',
            fabric.populate_children(deep=True, include_concrete=True)
            print '...done'

            searchables = fabric.get_searchable()
            print 'Indexing',
            self.index_searchables(searchables)
            print '.',
            self.save_db()
            print '...done'
        else:
            print 'loading from file',
            p_file = open(self.save_file, "rb")
            print '.',
            (self.by_key_value, self.by_key, self.by_value) = pickle.load(p_file)
            print '..done'

        self.keywords = self.get_keywords()
        self.values = self.get_values()

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

    def save_db(self):
        """
        pickle the indexed data structures and save in search.p

        """
        pickle.dump((self.by_key_value, self.by_key, self.by_value), open(self.save_file, "wb"))

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
        for result in sorted(self.ranked_items,
                             key=lambda x: (self.ranked_items[x]['pscore'], self.ranked_items[x]['sscore']), reverse=True):
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

        return resp

    @staticmethod
    def is_primary(item, p_set):
        """
        will return true if the item is a primary item in the result set
        :param item:
        :param p_set:
        :return:
        """
        #if p_set is None:
        #    return False
        #return any(elem.primary == item for elem in p_set)
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
    sdb = SearchDb()
    sdb.set_login_credentials(args)
    try:
        sdb.load_db(args.force)
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
