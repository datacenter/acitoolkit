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
Collection of utility classes to make getting credentials and configuration easier.
"""
import argparse
import getpass
import os
import acitoolkit
import inspect

from . import aciphysobject
from graphviz import Digraph


class Credentials(object):
    """
    Used to get the APIC and MySQL login credentials from the command
    line (--help gives usage).

    The login credentials are taken in the following order

    * Command line arguments
    * Environment variables
    * File named credentials.py
    * From an interactive prompt

    These are done in a per credential basis so it is possible to specify only
    some of the arguments.  For instance, the username and URL can be specified
    in credentials.py but the password can be taken from the user through the
    interactive prompt.  Another example is using the command line argument to
    override the URL specified in credentials.py to temporarily connect to a
    different APIC.
    """
    def __init__(self, qualifier='apic', description=''):
        def set_default(key):
            """
            Check for the following:
             - environmental variables
             - credentials.py file
            """
            if 'APIC_' + key.upper() in os.environ.keys():
                return os.environ['APIC_' + key.upper()]
            else:
                try:
                    import credentials
                except ImportError:
                    return None
                try:
                    default = credentials.__getattribute__(key.upper())
                    return default
                except AttributeError:
                    return None

        if isinstance(qualifier, str):
            qualifier = (qualifier)
        self._qualifier = qualifier
        self._args = None
        self._parser = argparse.ArgumentParser(description=description)
        if 'apic' in qualifier:
            DEFAULT_URL = set_default('url')
            DEFAULT_LOGIN = set_default('login')
            DEFAULT_PASSWORD = set_default('password')
            DEFAULT_CERT_NAME = set_default('cert_name')
            DEFAULT_KEY = set_default('key')
            #if DEFAULT_PASSWORD is not None:
            #    DEFAULT_CERT_NAME = set_default('cert_name')
            #    DEFAULT_KEY = set_default('key')
            # else:
            #     DEFAULT_CERT_NAME = None
            #     DEFAULT_KEY = None
            self._parser.add_argument('-u', '--url',
                                      default=DEFAULT_URL,
                                      help='APIC URL e.g. http://1.2.3.4')
            self._parser.add_argument('-l', '--login',
                                      default=DEFAULT_LOGIN,
                                      help='APIC login ID.')
            self._parser.add_argument('-p', '--password',
                                      default=DEFAULT_PASSWORD,
                                      help='APIC login password.')
            self._parser.add_argument('--cert-name',
                                      default=DEFAULT_CERT_NAME,
                                      help='X.509 certificate name attached to APIC AAA user')
            self._parser.add_argument('--key',
                                      default=DEFAULT_KEY,
                                      help='Private key matching given certificate, used to generate authentication signature')
        if 'nosnapshotfiles' not in qualifier and 'apic' in qualifier:
            self._parser.add_argument('--snapshotfiles', nargs='+',
                                      help='APIC configuration files')
        if 'mysql' in qualifier:
            DEFAULT_MYSQL_IP = set_default('mysqlip')
            DEFAULT_MYSQL_LOGIN = set_default('mysqllogin')
            DEFAULT_MYSQL_PASSWORD = set_default('mysqlpassword')
            self._parser.add_argument('-i', '--mysqlip',
                                      default=DEFAULT_MYSQL_IP,
                                      help='MySQL IP address.')
            self._parser.add_argument('-a', '--mysqllogin',
                                      default=DEFAULT_MYSQL_LOGIN,
                                      help='MySQL login ID.')
            self._parser.add_argument('-s', '--mysqlpassword',
                                      default=DEFAULT_MYSQL_PASSWORD,
                                      help='MySQL login password.')
        if 'daemon' in qualifier:
            self._parser.add_argument('-d', '--daemon',
                                      help='Run as a Daemon',
                                      action='store_true')
            self._parser.add_argument('--kill',
                                      help='if run as a process, kill it',
                                      action='store_true')
            self._parser.add_argument('--restart',
                                      help='if run as a process, restart it',
                                      action='store_true')
        if 'server' in qualifier:
            DEFAULT_PORT = '5000'
            DEFAULT_IPADDRESS = '127.0.0.1'
            self._parser.add_argument('--ip',
                                      default=DEFAULT_IPADDRESS,
                                      help='IP address to listen on.')
            self._parser.add_argument('--port',
                                      default=DEFAULT_PORT,
                                      help='Port number to listen on.')
            self._parser.add_argument('--test',
                                      action='store_true', default=False,
                                      help='Enable functions for lab testing.')
            self._parser.add_argument('--debug', nargs='?',
                                      choices=['verbose', 'warnings'],
                                      const='warnings',
                                      help='Enable debug messages.')

    @staticmethod
    def _get_from_user(prompt):
        """
        Get the input from the user through interactive prompt.
        Use raw_input or input based on the Python version.
        """
        try:
            resp = raw_input(prompt)
        except NameError:
            resp = input(prompt)
        return resp

    @staticmethod
    def _get_password(prompt):
        """
        Get the password from the user through interactive prompt.
        Using this will ensure that the password is not displayed as
        it is typed.
        """
        return getpass.getpass(prompt)

    def get(self):
        """
        Get the arguments and verify them
        """
        self._args = self._parser.parse_args()
        self.verify()
        return self._args

    def add_argument(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        self._parser.add_argument(*args, **kwargs)

    def add_mutually_exclusive_group(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        return self._parser.add_mutually_exclusive_group(*args, **kwargs)

    def add_argument_group(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        return self._parser.add_argument_group(*args, **kwargs)

    def print_help(self, *args, **kwargs):
        """
        Pass through function to allow the underlying parser to be
        extended.
        """
        return self._parser.print_help(*args, **kwargs)

    def verify(self):
        """
        Verify that the arguments have been passed in some way.  If not,
        ask the user through interactive prompt.
        """
        try:
            if self._args.kill:
                return ''
        except AttributeError:
            pass
        if 'apic' in self._qualifier and 'nosnapshotfiles' not in self._qualifier and self._args.snapshotfiles is None:
            if self._args.login is None:
                self._args.login = self._get_from_user('APIC login username: ')
            if self._args.url is None:
                self._args.url = self._get_from_user('APIC URL: ')

            if self._args.password is None and not (self._args.cert_name or self._args.key):
                self._args.password = self._get_password('APIC Password: ')
            elif self._args.password is None:
                if self._args.cert_name is None:
                    self._args.cert_name = self._get_from_user('Certificate Name: ')
                if self._args.key is None:
                    self._args.key = self._get_from_user('Private Key: ')

        if 'mysql' in self._qualifier:
            if self._args.mysqlip is None:
                self._args.mysqlip = self._get_from_user('MySQL IP address: ')
            if self._args.mysqllogin is None:
                prompt = 'MySQL login username: '
                self._args.mysqllogin = self._get_from_user(prompt)
            if self._args.mysqlpassword is None:
                prompt = 'MySQL Password: '
                self._args.mysqlpassword = self._get_password(prompt)


class AcitoolkitGraphBuilder(object):
    """
    Class to build class hierarchy diagrams for the ACI toolkit Physical and Logical Models
    """
    @staticmethod
    def build_graph_from_parent(root_parent_name):
        """
        Create a graph starting from the root class name

        :param root_parent_name: String containing the class name to use as the root of the class hierarchy graph
        :return: None
        """
        def clean_name(name):
            """
            Convert invalid names to valid names for graphviz
            :param name: String containing the name to convert
            :return: String containing the valid name, converted if necessary
            """
            graphviz_illegal_node_names = ['Node']
            if name in graphviz_illegal_node_names:
                name += ' '
            return name

        def get_child_edges(edges, parent_name):
            """
            Get the child edges for the specified parent class name
            :param edges: List of edges
            :param parent_name: String containing the parent class name
            :return: List of (parentname, childname) edges
            """
            resp = []
            for edge in edges:
                (edge_parent_name, child_class_name) = edge
                if edge_parent_name == parent_name:
                    resp.append(edge)
                    child_edges = get_child_edges(edges, child_class_name)
                    # Combine child_edges and resp with some list/set magic to take only the unique edges
                    resp = list(set(resp) - set(child_edges)) + child_edges
            return resp

        nodes = []
        edges = []

        graph = Digraph(name='ACI Toolkit Class Hierarchy', comment='ACI Toolkit Class Hierarchy', format='pdf')
        graph.node_attr.update(color='lightblue2', style='filled')
        graph.edge_attr.update(arrowhead='none')

        for class_name, class_obj in inspect.getmembers(acitoolkit) + inspect.getmembers(aciphysobject):
            class_name = clean_name(class_name)
            if inspect.isclass(class_obj):
                get_parent_class = getattr(class_obj, "_get_parent_class", None)
                if callable(get_parent_class):
                    if class_obj.mask_class_from_graphs():
                        continue
                    try:
                        parent_class = class_obj._get_parent_class()
                        if class_name not in nodes:
                            nodes.append(class_name)
                        if isinstance(parent_class, list):
                            for parent in parent_class:
                                parent_name = clean_name(parent.__name__)
                                if (parent_name, class_name) not in edges:
                                    edges.append((parent_name, class_name))
                        elif parent_class is not None:
                            parent_name = clean_name(parent_class.__name__)
                            if (parent_name, class_name) not in edges:
                                edges.append((parent_name, class_name))
                    except NotImplementedError:
                        pass

        subgraph_nodes = []

        # Get the edges starting from the root_parent_name as the parent node
        subgraph_edges = get_child_edges(edges, root_parent_name)

        # Derive the nodes from the edges
        for subgraph_edge in subgraph_edges:
            (parent_name, class_name) = subgraph_edge
            if parent_name not in subgraph_nodes:
                subgraph_nodes.append(parent_name)
            if class_name not in subgraph_nodes:
                subgraph_nodes.append(class_name)

        # Fill in the graph
        for subgraph_node in subgraph_nodes:
            graph.node(subgraph_node, subgraph_node)
        for subgraph_edge in subgraph_edges:
            (parent_name, class_name) = subgraph_edge
            graph.edge(parent_name, class_name)

        graph.render('acitoolkit-hierarchy.%s.tmp.gv' % root_parent_name)

        output_file = open('acitoolkit-hierarchy.%s.gv' % root_parent_name, 'w')
        output_file.write('.. graphviz::\n\n')
        with open('acitoolkit-hierarchy.%s.tmp.gv' % root_parent_name, 'r') as input_file:
            for line in input_file:
                output_file.write('    ' + line)
        output_file.close()

    def build_graphs(self):
        """
        Build the graphs starting with the various parent class names
        """
        self.build_graph_from_parent('Fabric')
        self.build_graph_from_parent('PhysicalModel')
        self.build_graph_from_parent('LogicalModel')
