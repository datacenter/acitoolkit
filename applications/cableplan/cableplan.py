################################################################################
# _    ____ ___                                 #
# / \  / ___|_ _|                                #
# / _ \| |    | |                                 #
#                             / ___ \ |___ | |                                 #
#                 ____      _/_/  _\_\____|___|  _                             #
#                / ___|__ _| |__ | | ___  |  _ \| | __ _ _ __                  #
#               | |   / _` | '_ \| |/ _ \ | |_) | |/ _` | '_ \                 #
#               | |__| (_| | |_) | |  __/ |  __/| | (_| | | | |                #
#                \____\__,_|_.__/|_|\___| |_|   |_|\__,_|_| |_|                #
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
import sys
import re

import acitoolkit as ACI

eTree = None
Verbose_import_ = False
(
    XMLParser_import_none, XMLParser_import_lxml,
    XMLParser_import_elementtree
) = range(3)
XMLParser_import_library = None
try:
    # lxml
    from lxml import etree as eTree

    XMLParser_import_library = XMLParser_import_lxml
    if Verbose_import_:
        print("running with lxml.etree")
except ImportError:
    try:
        # cElementTree from Python 2.5+
        import xml.etree.cElementTree as eTree

        XMLParser_import_library = XMLParser_import_elementtree
        if Verbose_import_:
            print("running with cElementTree on Python 2.5+")
    except ImportError:
        try:
            # ElementTree from Python 2.5+
            import xml.etree.ElementTree as eTree

            XMLParser_import_library = XMLParser_import_elementtree
            if Verbose_import_:
                print("running with ElementTree on Python 2.5+")
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as eTree

                XMLParser_import_library = XMLParser_import_elementtree
                if Verbose_import_:
                    print("running with cElementTree")
            except ImportError:
                try:
                    # normal ElementTree install
                    # noinspection PyUnresolvedReferences
                    import elementtree.ElementTree as eTree

                    XMLParser_import_library = XMLParser_import_elementtree
                    if Verbose_import_:
                        print("running with ElementTree")
                except ImportError:
                    raise ImportError(
                        "Failed to import ElementTree from any known place")


def parsexml_(*args, **kwargs):
    """
    parsexml_
    :param args:
    :param kwargs:
    :return: doc
    """
    if XMLParser_import_library == XMLParser_import_lxml and 'parser' not in kwargs:
        # Use the lxml ElementTree compatible parser so that, e.g.,
        #   we ignore comments.
        kwargs['parser'] = eTree.ETCompatXMLParser()
    doc = eTree.parse(*args, **kwargs)
    return doc

#
# Globals
#

Tag_pattern_ = re.compile(r'({.*})?(.*)')
#
# Support/utility functions.
#


def indent(level):
    """
    Indent the text to a specified level
    :param level: The number of 4 space increments
    :return: String containing the desired number of spaces for indentation
    """
    return level * '    '


def quote_attrib(in_str):
    s1 = (isinstance(in_str, basestring) and in_str or
          '%s' % in_str)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1


def suffix_to_int(string):
    return int(re.search(r'(\d+)$', string).group(1))


class CABLEPLAN:
    def __init__(self, version=None):
        self.version = version
        self.switches = []
        self.links = []
        self.schemaLocation = 'nxos-cable-plan-schema.xsd'
        self.nsmap = None
        self.namespace = 'http://www.cisco.com/cableplan/Schema2'
        self.prefix = 'xsi'
        self.prefix_url = 'http://www.w3.org/2001/XMLSchema-instance'
        self.networkLocation = None
        self.idFormat = 'hostname'

    @classmethod
    def get(cls, source):
        """This will get input a cable plan from 'source'.  If source is a string,
        it will get the cable plan from XML in a file whose name is source.  If it is
        a Session, it will read the corresponding APIC to get the cable plan.

        :param source: filename of type string or Session of type Session

        :returns: CABLEPLAN
        """
        if isinstance(source, str):
            return cls._parse(source)
        elif isinstance(source, ACI.Session):
            return cls._parse_apic(source)
        else:
            raise TypeError('source must of type str or type ACI.Session.  Instead was '+type(source))

    @classmethod
    def _parse(cls, in_file_name):
        doc = parsexml_(in_file_name)
        # This can be enhanced to parse a string rather than just a file with the
        # following line:
        # doc = parsexml_(StringIO(inString))

        root_node = doc.getroot()
        cable_plan = cls()
        cable_plan._build_xml(root_node)
        return cable_plan

    @classmethod
    def _parse_apic(cls, session):
        pod = ACI.Pod.get(session)[0]
        pod.populate_children(deep=True)
        cable_plan = cls()
        cable_plan._build_apic(pod)
        return cable_plan

    def get_switch(self, switch_name=None):
        if switch_name:
            for switch in self.switches:
                if switch.get_name() == switch_name:
                    return switch
            return None
        else:
            return self.switches[:]

    def get_spines(self):
        """Will return list of switches that are spines

        :returns: list of CpSwitch
        """

        switch_list = []
        for switch in self.switches:
            if switch.is_spine():
                switch_list.append(switch)
        return switch_list

    def add_switch(self, new_switch):
        """This will new_switch to the CABLEPLAN.  If the switch already
        exists, it will merge the new_switch with the existing one.
        It will also set the parent of the switch to be the CABLEPLAN.  It will
        return the final switch, i.e. new_switch if no merge occurred or the
        newly merged switch if a merge did occur.

        :param new_switch: switch to be added of type CpSwitch

        :returns: CpSwitch
        """
        if not isinstance(new_switch, CpSwitch):
            raise TypeError('add_switch expects object of type CpSwitch')

        new_switch.set_parent(self)
        for switch in self.switches:
            if switch == new_switch:
                switch.merge(new_switch)
                del new_switch
                return switch
        self.switches.append(new_switch)
        return new_switch

    def delete_switch(self, old_switch):
        if old_switch in self.switches:
            self.switches.remove(old_switch)

    def exists_switch(self, switch):
        return switch in self.switches

    def add_link(self, new_link):
        """Will add a link to the CABLEPLAN.  Duplicates will not be allow, but overlapping will be.

        :param new_link: Link to be added of type CpLink

        :returns: None
        """

        if new_link not in self.links:
            self.links.append(new_link)

    def delete_link(self, link):
        if link in self.links:
            self.links.remove(link)

    def exists_link(self, link):
        return link in self.links

    def get_links(self, switch1=None, switch2=None):
        """Returns a list of links.  If switch is unspecified, it will return all links.  If switch is specified,
        it will return all of the links that are connected to switch.  If both switch1 and swithc2 are specified,
        it will return all links that are connected between the two switches.

        :param switch1: optional first switch of type CpSwitch
        :param switch2: optional second switch of type CpSwitch

        :returns:  list of links of type CpLink
        """

        if switch1:
            link_list = []
            for link in self.links:
                if link.is_connected(switch1, switch2):
                    link_list.append(link)
            return link_list

        else:
            return self.links[:]

    def difference_switch(self, cp):
        """Will return a list of switches that are in self, but not in cp.

        :param cp: cable plan

        :returns: list of CpSwitch
        """
        result = []
        myswitches = self.get_switch()
        cpswitches = cp.get_switch()
        for switch in myswitches:
            if switch not in cpswitches:
                result.append(switch)
        return result

    # Link comparison operations and support functions
    def reset_accounting(self):
        """clears the refernce count on each link
        :rtype : None
        """
        for link in self.links:
            link.reset_accounting()

    def sorted_links(self, switch1, switch2):
        """returns a sorted list of links between switch1 and switch2.  They are sorted by specificity from
        most specific to least specific.  The specificity is determined by which list of ports is the minimum
        between source and destination and which is the minimum across links.
        :rtype : list
        :param switch1:
        :param switch2:
        """
        result = []
        links = self.get_links(switch1, switch2)
        num_links = len(links)
        for i in range(num_links):
            best_order = 100000
            best_link = None
            for link in links:
                if (link.order() < best_order) and (link not in result):
                    best_order = link.order()
                    best_link = link

            if best_order < 100000:
                result.append(best_link)
        return result

    def _switch_link_diff(self, cp, switch1, switch2):
        """ returns a list links that go between switch1 and switch2 that are in self, but not in cp

        :param cp: cable plan of type CP_CABLEPLAN
        :param switch1: first switch of type CpSwitch
        :param switch2: second switch of type CpSwitch

        :returns: list of CpLink
        """
        my_links = self.sorted_links(switch1, switch2)
        other_links = cp.sorted_links(switch1, switch2)
        for my_link in my_links:

            if my_link.remaining_need() > 0:
                # still need to retire some link capacity

                for otherLink in other_links:  # loop through all of the otherLinks to find matches

                    if otherLink.remaining_avail() > 0:
                        # there is still some capacity in otherLink
                        CpLink.match_links(my_link, otherLink)  # match-up links
                    if my_link.remaining_need() == 0:
                        # done with myLink, go get next one
                        break

    def difference_link(self, cp):
        """returns a list of links that are in self, but not in cp.

        :param cp: cable plan of type CABLEPLAN

        :returns: list of CpLink
        """
        result = []
        self.reset_accounting()
        cp.reset_accounting()
        for switch1 in self.get_switch():
            for switch2 in self.get_switch():
                self._switch_link_diff(cp, switch1, switch2)

        for myLink in self.get_links():
            if myLink.remaining_need() > 0:
                result.append(myLink)
        return result

    def export(self, out_file=None, level=0):
        """Will generate XML text of the entire CABLEPLAN and return it as a string.  If
        out_file is specified, it will write the XML to that file.  out_file should be opened for
        writing before calling this method.  'level' specifies the amount of indentation to start with.
        """

        if out_file:
            if not isinstance(out_file, file):
                raise TypeError('expected a file')

        tag = 'CISCO_NETWORK_TYPES'

        text = '<?xml version="1.0" encoding="UTF-8"?>\n'
        text += '<?created by cableplan.py?>\n'
        text += indent(level)
        text += '<%s version=%s xmlns=%s xmlns:%s=%s %s:schemaLocation=%s>\n' % (
            tag, quote_attrib(self.version), quote_attrib(self.namespace), self.prefix, quote_attrib(self.prefix_url),
            self.prefix, quote_attrib(self.namespace + ' ' + self.schemaLocation))

        text += self.export_data_center(level=level + 1)
        text += indent(level)
        text += '</%s>\n' % tag

        if out_file:
            out_file.write(text)
        return text

    def export_data_center(self, level=0):
        """Will generate the XML of the CABLEPLAN with DATA_CENTER as the root.  This will then be
        returned a string. 'level' specifies the indentation level to start with.

        :param level: optional indention level, integer

        :returns: string that is the DATA_CENTER xml
        """
        tag = 'DATA_CENTER'
        text = indent(level)
        text += '<%s networkLocation=%s idFormat=%s>\n' % (
            tag, quote_attrib(self.networkLocation), quote_attrib(self.idFormat))
        switches = self.get_spines()
        for switch in switches:
            text += switch.export(level + 1)

        text += indent(level)
        text += '</%s>\n' % tag

        return text

    @staticmethod
    def _get_attr_value(node, attr_name):

        attrs = node.attrib
        attr_parts = attr_name.split(':')
        value = None
        if len(attr_parts) == 1:
            value = attrs.get(attr_name)
        elif len(attr_parts) == 2:
            prefix, name = attr_parts
            namespace = node.nsmap.get(prefix)
            if namespace is not None:
                value = attrs.get('{%s}%s' % (namespace, name, ))
        return value

    def _get_namespace_prefix(self, nsmap):
        for nsmap_prefix in nsmap:
            if nsmap_prefix is not None:
                self.prefix = nsmap_prefix
                self.prefix_url = nsmap[nsmap_prefix]

            if nsmap_prefix is None:
                self.namespace = nsmap[nsmap_prefix]

    def _get_switch_from_apic_link(self, link, end):
        if end == 1:
            switch_name = link.get_node1().get_name()
        elif end == 2:
            switch_name = link.get_node2().get_name()
        else:
            switch_name = ''
        cp_switches = self.get_switch()
        for cp_switch in cp_switches:
            if cp_switch.get_name() == switch_name:
                return cp_switch

    def _build_apic(self, pod):
        """This will build the cable plan using the configuration of the pod.

        :param pod: Pod

        :returns: None
        """
        nodes = pod.get_children(ACI.Node)
        for node in nodes:
            if node.getFabricSt() == 'active':
                if node.get_role() == 'spine':
                    self.add_switch(CpSwitch(node.get_name(), node.get_chassis_type(), spine=True))
                if node.get_role() == 'leaf':
                    self.add_switch(CpSwitch(node.get_name(), node.get_chassis_type()))
        links = pod.get_children(ACI.Link)
        for link in links:
            switch1 = link.get_node2()
            switch2 = link.get_node2()
            if switch1 and switch2:
                if link.get_node1().getFabricSt() == 'active' and link.get_node2().getFabricSt() == 'active':
                    if link.get_node1().get_role() != 'controller' and link.get_node2().get_role() != 'controller':
                        source_chassis = self._get_switch_from_apic_link(link, 1)
                        dest_chassis = self._get_switch_from_apic_link(link, 2)
                        source_interface = link.get_port1()
                        dest_interface = link.get_port2()
                        source_port = '{0:s}{1:s}/{2:s}'.format(source_interface.interface_type,
                                                                source_interface.module, source_interface.port)
                        dest_port = '{0:s}{1:s}/{2:s}'.format(dest_interface.interface_type,
                                                              dest_interface.module,
                                                              dest_interface.port)

                        self.add_link(
                            CpLink(source_chassis=source_chassis, source_port=source_port, dest_chassis=dest_chassis,
                                   dest_port=dest_port))

    def _build_xml(self, node):

        # start at CISCO_NETWORK_TYPES
        self.version = self._get_attr_value(node, 'version')
        self.nsmap = node.nsmap  # namespace prefix can be found here
        self._get_namespace_prefix(self.nsmap)  # parse out namespace and prefix

        # TODO: should be refined to handle any namespace prefix
        self.schemaLocation = self._get_attr_value(node,
                                                   'xsi:schemaLocation').strip()
        for child in node:
            node_name = Tag_pattern_.match(child.tag).groups()[-1]
            if node_name == 'DATA_CENTER':
                self._parse_xml_data_center(child)

    def _parse_xml_data_center(self, node):
        self.networkLocation = self._get_attr_value(node, 'networkLocation')
        self.idFormat = self._get_attr_value(node, 'idFormat')
        for child in node:
            node_name = Tag_pattern_.match(child.tag).groups()[-1]
            if node_name == 'CHASSIS_INFO':
                self._parse_xml_chassis_info(child)

    def _parse_xml_chassis_info(self, node):
        chassis_name = self._get_attr_value(node, 'sourceChassis')
        chassis_type = self._get_attr_value(node, 'type')
        switch = CpSwitch(chassis_name, chassis_type, spine=True)
        self.add_switch(switch)
        for child in node:
            node_name = Tag_pattern_.match(child.tag).groups()[-1]
            if node_name == 'LINK_INFO':
                self._parse_xml_link_info(child, switch)

    def _parse_xml_link_info(self, node, link_source_chassis):
        link_dest_chassis = self._get_attr_value(node, 'destChassis')
        link_dest_port = self._get_attr_value(node, 'destPort')
        link_source_port = self._get_attr_value(node, 'sourcePort')
        link_min_ports = self._get_attr_value(node, 'minPorts')
        link_max_ports = self._get_attr_value(node, 'maxPorts')

        switch = CpSwitch(link_dest_chassis, chassis_type=None)
        switch = self.add_switch(switch)

        link = CpLink(source_chassis=link_source_chassis, source_port=link_source_port, dest_chassis=switch,
                      dest_port=link_dest_port, min_ports=link_min_ports, max_ports=link_max_ports)
        self.add_link(link)


class CpSwitch(object):
    """ class holding a switch """

    def __init__(self, name, chassis_type=None, spine=False, parent=None):
        self.spine = spine
        self.name = name
        self.chassis_type = chassis_type
        self.parent = None
        if parent:
            self.set_parent(parent)

    def get_name(self):
        """Gets the name of the chassis.

        :returns: str
        """
        return self.name

    def set_name(self, name):
        """Sets the switch name.  This will over-ride any preexisting name.  Note that this new
        name will now become part of the link name for all the links attached to this switch.

        :param name: name string to set in the switch
        """

        self.name = name
        return None

    def get_type(self):
        """Gets the chassis type. Examples of chassis types are 'n7k' or 'n9k'

        :returns: str
        """
        return self.chassis_type

    def set_parent(self, parent):
        """Sets the parent of the switch.  Parent must be of type CABLEPLAN.  If a parent
        CABLEPLAN was already set and it is differnt from parent, then an error is raised.

        :param parent: parent object of type CABLEPLAN
        """

        if not isinstance(parent, CABLEPLAN):
            raise TypeError('expected parent to be of class CABLEPLAN')

        if self.parent:
            if self.parent != parent:
                raise ValueError('This switch was previously assigned to a different CABLEPLAN')

        self.parent = parent

    def is_spine(self):
        """Checks if the 'spine' flag is set.

        :returns: True if the ``spine`` flag is set, otherwise False
        """

        return self.spine

    def merge(self, new_switch):
        """ Merges the content of new_switch with self.  If self has variables set, then they will
        not be changed.  If they have not been set, then they will be assigned the value from new_switch.

        :param new_switch: switch object to merge with self
        """
        if new_switch.spine:
            self.spine = new_switch.spine
        if new_switch.chassis_type:
            self.chassis_type = new_switch.chassis_type

    def __eq__(self, other):
        return self.name == other.name

    def get_links(self):
        """returns a list of CP_LINKS from the parent CABLEPLAN that are connected to self.

        :returns: list of CP_LINKS
        """
        return self.parent.get_links(self)

    def __str__(self):
        return self.name

    def export(self, level):
        tag = 'CHASSIS_INFO'
        text = indent(level)
        text += '<%s sourceChassis=%s type=%s>\n' % (tag, quote_attrib(self.get_name()), quote_attrib(self.get_type()))
        links = self.get_links()
        for link in links:
            text += link.export(self, level + 1)

        text += indent(level)
        text += '</%s>\n' % tag
        return text


# end class CpSwitch

class CpPort:
    """This class holds the information for a link's port.  Since the port can be a single port, a list
    or a range, putting it in a class allows more flexible operations on it.
    """

    def __init__(self, port_set):
        self.ports = self._expand(port_set)
        self.available_ports = None

    @staticmethod
    def _expand(port_set):
        """Will parse the port_set and return a list of enumerated ports or None.
        port_set is string containing a comma separated list of ports or port ranges.
        A port range consists of a starting port separated from an ending port with a dash.
        Both the starting port and ending port are included in the list.
        The format for a port is a string that ends in a forward slash followed by a number.
        The number is what is incremented
        for a range.  A dash, '-' is not legal in the port name.

        :param port_set: string

        :returns: list of str
        """

        if port_set is None:
            return []

        # use a set so that there are no duplicate ports
        port_list = set()
        port_set = re.sub(r'\s+', '', port_set)  # remove unnecessary white space
        ports_n_ranges = port_set.split(',')
        for portOrRange in ports_n_ranges:
            if '-' in portOrRange:
                # this is a range
                startport, endport = portOrRange.split('-')
                prefix = re.findall(r'(.*/)\d+$', startport)
                if len(prefix) != 1:
                    raise ValueError('Badly formed port name in range:"' + startport + '"')

                prefix_e = re.findall(r'(.*/)\d+$', endport)
                if len(prefix_e) != 1:
                    raise ValueError('Badly formed port name in range:"' + endport + '"')

                if prefix[0] != prefix_e[0]:
                    raise ValueError('port range invalid:"' + portOrRange + '"')
                start_num = suffix_to_int(startport)
                end_num = suffix_to_int(endport)

                if start_num > end_num:
                    raise ValueError(
                        'port range invalid - start of range cannot be higher than end:"' + portOrRange + '"')

                for index in range(start_num, end_num + 1):
                    port_name = prefix[0] + str(index)
                    port_list.add(port_name)
            else:
                # this is just a port
                port_list.add(portOrRange)
        return sorted(list(port_list))

    def _rangeify(self):
        """ this will take the list of ports and return a string of comma separated ports and port
        ranges.  A port range will be generated for any sequence longer than two ports.
        """
        if not self.ports:
            return None

        text_list = []
        index = 0
        numports = len(self.ports)

        start_port = self.ports[index]
        cur_port = start_port
        cur_num = suffix_to_int(cur_port)
        cur_prefix = re.findall(r'(.*/)\d+$', cur_port)[0]
        start_num = suffix_to_int(start_port)
        while index < (numports - 1):
            next_port = self.ports[index + 1]
            next_num = suffix_to_int(next_port)
            next_prefix = re.findall(r'(.*/)\d+$', next_port)[0]
            if next_num != cur_num + 1 or next_prefix != cur_prefix:
                # there is a break in the sequence terminate the range
                if cur_num == start_num:
                    text_list.append(start_port)
                elif cur_num - start_num == 1:
                    text_list.append(start_port)
                    text_list.append(cur_port)
                else:
                    text_list.append(start_port + ' - ' + cur_port)

                start_port = next_port
                start_num = suffix_to_int(start_port)

            index += 1
            cur_port = self.ports[index]
            cur_num = suffix_to_int(cur_port)
            cur_prefix = re.findall(r'(.*/)\d+$', cur_port)[0]

        # clean-up - index is one past end, cur is last one looked at
        if cur_num == start_num:
            text_list.append(start_port)
        elif cur_num - start_num == 1:
            text_list.append(start_port)
            text_list.append(cur_port)
        else:
            text_list.append(start_port + ' - ' + cur_port)

        if not text_list:
            text = None
        else:
            text = ', '.join(text_list)

        return text

    def reset_accounting(self):
        self.available_ports = self.ports[:]

    def remove_available_port(self, port):
        if self.ports is None:
            return
        else:
            if port in self.available_ports:
                self.available_ports.remove(port)

    def list(self):
        return self.ports[:]

    def __str__(self):
        text = self._rangeify()
        return str(text)

    def name(self):
        text = self._rangeify()
        return text

    def __eq__(self, other):
        """ compares the content of the port list and returns true if they are the same.  The comparison is case insensitive.
        """

        if not self.ports and not other.ports:
            return True
        elif not self.ports and other.ports:
            return False
        elif self.ports and not other.ports:
            return False

        my_ports = set()
        for port in self.ports:
            my_ports.add(port.lower())

        other_ports = set()
        for port in other.ports:
            other_ports.add(port.lower())

        if len(my_ports ^ other_ports) == 0:
            return True
        else:
            return False


class CpLink:
    def __init__(self, source_chassis, dest_chassis, source_port=None, dest_port=None, min_ports=None, max_ports=None):

        if not isinstance(source_chassis, CpSwitch):
            raise TypeError('expected source_chassis to be of class CpSwitch')
        if not isinstance(dest_chassis, CpSwitch):
            raise TypeError('expected dest_chassis to be of class CpSwitch')

        # allow initialization to be with a list or a string for ports.
        # convert all to a string
        if isinstance(dest_port, list):
            dest_port = ', '.join(dest_port)
        if isinstance(source_port, list):
            source_port = ', '.join(source_port)

        self.minPorts = min_ports
        self.maxPorts = max_ports
        self.refCount = 0
        # initially normalize name
        if source_chassis.get_name() < dest_chassis.get_name():
            self.source_chassis = source_chassis
            self.source_port = CpPort(source_port)
            self.dest_chassis = dest_chassis
            self.destPort = CpPort(dest_port)

        else:
            self.source_chassis = dest_chassis
            self.source_port = CpPort(dest_port)
            self.dest_chassis = source_chassis
            self.destPort = CpPort(source_port)

        # count to track references to a particular link
        self.reset_accounting()

        # the maximum reference count is either self.max_ports or is the maximum number of physical links
        # that this link can specify, whichever is smaller.  If there is no limit, then maxRef is set to 10000

        if self.destPort.ports and self.source_port.ports:
            max_phys_ports = min(len(self.destPort.ports), len(self.source_port.ports))
        elif self.destPort.ports:
            max_phys_ports = len(self.destPort.ports)
        elif self.source_port.ports:
            max_phys_ports = len(self.source_port.ports)
        else:
            max_phys_ports = 10000

        if self.maxPorts:
            self.maxRef = min(max_phys_ports, self.maxPorts)
        else:
            self.maxRef = max_phys_ports

        # self.minRef is the minimum number of physical links needed to meet the requirements of this link
        if self.minPorts:
            self.minRef = int(self.minPorts)
        else:
            self.minRef = 1

    def reset_accounting(self):
        """Resets account on the source and dest ports as well as reference count
        """
        self.destPort.reset_accounting()
        self.source_port.reset_accounting()
        self.refCount = 0

    def remaining_need(self):
        """ returns the remaining number of physical links needed to match against self to satisfy requirements.
        The parameters used to calculate this value are reset by the reset_accounting() method which is typically
        invoked when invoking a difference_link() method on the CABLEPLAN parent object.

        :returns: int
        """
        return max(0, self.minRef - self.refCount)

    def remaining_avail(self):
        """ returns the remaining number of physical links available to match against
        The parameters used to calculate this value are reset by the reset_accounting() method which is typically
        invoked when invoking a difference_link() method on the CABLEPLAN parent object.

        :returns: int
        """

        return max(0, self.maxRef - self.refCount)

    def order(self):
        """Calculates the order of the link defined by the maximum number of physical links this link
        can represent

        :returns: int
        """
        if self.source_port.ports and self.destPort.ports:
            result = min(len(self.source_port.ports), len(self.destPort.ports))
        elif self.source_port.ports:
            result = len(self.source_port.ports)
        elif self.destPort.ports:
            result = len(self.destPort.ports)
        else:
            result = 10000  # this is the any-any case which is unlimited.
        return result

    def get_name(self):
        if self.source_port.name():
            stext = '%s-%s' % (self.source_chassis, self.source_port.name())
        else:
            stext = '%s' % self.source_chassis

        if self.destPort.name():
            dtext = '%s-%s' % (self.dest_chassis, self.destPort.name())
        else:
            dtext = '%s' % self.dest_chassis

        return '(%s,%s)' % (stext, dtext)

    def is_connected(self, switch1, switch2=None):
        """Returns True if switch1 is one of the switch endpoints of the link and switch2 is unspecified
        otherwise is will return True if both switch1 and switch2 are switch endpoints of the link.  If
        switch1 is the same as switch2, it will return False.

        :param switch1: first switch to check if it an end-point of the link
        :param switch2: optional second switch to check if it an end-point of the link

        :returns: True if switch1 (and optional switch2) is an end-point of the link
        """
        s1 = (switch1 == self.source_chassis) or (switch1 == self.dest_chassis)
        if switch2:
            s2 = (self.source_chassis == switch2) or (self.dest_chassis == switch2)
        else:
            s2 = True

        result = s1 and s2 and (switch1 != switch2)
        return result

    def __eq__(self, other):
        if ((self.source_chassis == other.source_chassis) and (self.source_port == other.source_port) and
                (self.dest_chassis == other.dest_chassis) and (self.destPort == other.destPort)):
            return True
        return False

    def has_port_in_common(self, link):
        """Returns True if link has any ports that match self.  It will compare
        all ports included expanded lists of port sets.

        :param link: link to check to see if matches, or overlaps, with self

        :returns: Boolean
        """

        if link.source_chassis == self.source_chassis:
            lnk_ports = set(link.source_port.list())
            slf_ports = set(self.source_port.list())
            if len(lnk_ports & slf_ports) > 0:
                return True

        if link.dest_chassis == self.dest_chassis:
            lnk_ports = set(link.destPort.list())
            slf_ports = set(self.destPort.list())
            if len(lnk_ports & slf_ports) > 0:
                return True

        if link.source_chassis == self.dest_chassis:
            lnk_ports = set(link.source_port.list())
            slf_ports = set(self.destPort.list())
            if len(lnk_ports & slf_ports) > 0:
                return True

        if link.dest_chassis == self.source_chassis:
            lnk_ports = set(link.destPort.list())
            slf_ports = set(self.source_port.list())
            if len(lnk_ports & slf_ports) > 0:
                return True

        return False

    def __str__(self):
        return self.get_name()

    @staticmethod
    def _get_attrib_str(attrib, value):
        text = ''
        if value is not None:
            text = '%s=%s ' % (attrib, quote_attrib(value))
        return text

    def export(self, chassis, level):
        """Will return string of XML describing the LINK_INFO.  It will use 'chassis' to determine
        which is the source chassis so that it will be omitted from the XML and the other chassis will
        become the destination.  'level' is the indentation level.

        :param chassis: Chassis that is the parent of the LINK_INFO xml
        :param level:  Indentation level

        :returns: str
        """

        tag = 'LINK_INFO'

        if chassis == self.source_chassis:

            dport_text = self._get_attrib_str('destPort', self.destPort.name())
            sport_text = self._get_attrib_str('sourcePort', self.source_port.name())
            dchassis_text = self._get_attrib_str('destChassis', self.dest_chassis)
        else:
            dport_text = self._get_attrib_str('destPort', self.source_port.name())
            sport_text = self._get_attrib_str('sourcePort', self.destPort.name())
            dchassis_text = self._get_attrib_str('destChassis', self.source_chassis)

        min_port_text = self._get_attrib_str('minPorts', self.minPorts)
        max_port_text = self._get_attrib_str('maxPorts', self.maxPorts)

        text = '<%s %s%s%s%s%s' % (tag, sport_text, dchassis_text, dport_text, min_port_text, max_port_text)
        text = indent(level) + text.strip()
        text += '/>\n'
        return text

    @staticmethod
    def match_links(link1, link2):
        """This will match-up link1 and link2 and increment the reference count in each link for each
        of the matches that happen.  It will do this until the minimum number of links has been reached for
        link1.  It will return the number of matches that occurred.

        :param link1: first link of type CpLink that is part of the matching
        :param link2: second link of type CpLink that is part of the matching

        :returns: number of matches that occured.
        """

        result = 0
        # match-up ends of link
        if (link1.source_chassis == link2.source_chassis) and (link1.dest_chassis == link2.dest_chassis):
            start1 = link1.source_port
            start2 = link2.source_port
            end1 = link1.destPort
            end2 = link2.destPort
        else:
            # chassis don't match so no link match
            return 0

        # get ends in common - the maximum match will be the min of this overlap
        if start1.ports != [] and start2.ports != []:
            starts = list(set(start1.available_ports) & set(start2.available_ports))
        elif start1.ports:
            starts = start1.available_ports[:]
        elif start2.ports:
            starts = start2.available_ports[:]
        else:
            starts = 'any'

        if end1.ports != [] and end2.ports != []:
            ends = list(set(end1.available_ports) & set(end2.available_ports))
        elif end1.ports:
            ends = end1.available_ports[:]
        elif end2.ports:
            ends = end2.available_ports[:]
        else:
            ends = 'any'

        if starts == 'any':
            len_starts = 10000
        else:
            len_starts = len(starts)

        if ends == 'any':
            len_ends = 10000
        else:
            len_ends = len(ends)

        num_to_retire = min(link1.remaining_need(), link2.remaining_avail(), len_starts, len_ends)

        for index in range(num_to_retire):

            if starts != 'any':
                start1.remove_available_port(starts[index])
                start2.remove_available_port(starts[index])
            if ends != 'any':
                end1.remove_available_port(ends[index])
                end2.remove_available_port(ends[index])

            link1.refCount += 1
            link2.refCount += 1
            result += 1
        return result


# end class LINK


def compare_cable_plans(session, file1, file2=None):
    if file2:
        cp1 = CABLEPLAN.get(file1)
        source1 = file1
        cp2 = CABLEPLAN.get(file2)
        source2 = file2
    else:
        resp = session.login()
        if not resp.ok:
            print '%% Could not login to APIC'
            sys.exit(1)
        cp1 = CABLEPLAN.get(session)
        source1 = 'APIC'
        cp2 = CABLEPLAN.get(file1)
        source2 = file1

    missing_switches = cp1.difference_switch(cp2)
    extra_switches = cp2.difference_switch(cp1)

    if missing_switches:
        print '\nThe following switches are in', source1 + ', but not in', source2
        for switch in missing_switches:
            print '   ', switch.get_name()

    if extra_switches:
        print '\nThe following switches are in', source2 + ', but not in', source1
        for switch in missing_switches:
            print '   ', switch.get_name()

    if missing_switches or extra_switches:
        print 'Link comparisons skipped because the switches are miss-matched'
    else:
        missing_links = cp1.difference_link(cp2)
        extra_links = cp2.difference_link(cp1)

        if missing_links:
            print '\nThe following links in', source1, 'are not found in', source2
            for link in missing_links:
                print '   ', link.get_name()

        if extra_links:
            print '\nThe following links in', source2, 'are not found in', source1
            for link in extra_links:
                print '   ', link.get_name()
        if not missing_links and not extra_links:
            print source1, 'and', source2, 'are the same'


def export_to_file(session, file1=None):
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        sys.exit(1)
    cp = CABLEPLAN.get(session)

    if file1:
        f = open(file1, 'w')
        cp.export(f)
        f.close()
    else:
        print cp.export(),


def main():
    description = 'Simple application that logs on to the APIC and displays stats for all of the Interfaces.'
    creds = ACI.Credentials('apic', description)
    # group = creds.add_mutually_exclusive_group()
    group1 = creds.add_argument_group('Export', 'Export a cable plan')
    group1.add_argument('-e', '--export_file', default=None, const='export text', dest='export_file', nargs='?',
                        help='Export cableplan from running fabric.  If EXPORT_FILE is specified, the '
                             'cableplan will be written to EXPORT_FILE')
    group2 = creds.add_argument_group('Compare', 'Compare cable plans')
    group2.add_argument('-c1', '--cableplan1',
                        type=str, nargs=1,
                        default=None,
                        help="Name of cableplan xml file.  If only CABLEPLAN1 is specified, "
                             "it will be compared to the running fabric.  If it is specified with "
                             "CABLEPLAN2 (the -c2 option), then it will compare CABLEPLAN1 with CABLEPLAN2")
    group2.add_argument('-c2', '--cableplan2',
                        type=str, nargs=1,
                        default=None,
                        help="Name of second cableplan xml file.  The second cableplan file.  This file will "
                             "be compared to CABLEPLAN1.  This option must only be used "
                             "in conjunction with the -c1 option.")

    args = creds.get()

    session = ACI.Session(args.url, args.login, args.password)

    if args.export_file and (args.cableplan1 or args.cableplan2):
        creds.print_help()
        print '\nError: export and compare operations are mutually exclusive'
        exit()

    if args.cableplan2 and not args.cableplan1:
        creds.print_help()
        print '\nError: -c2 option only valid with -c1 option'
        exit()

    if not args.export_file and not args.cableplan1:
        creds.print_help()
        print '\nError: Either export (-e) or compare (-c1) is required'
        exit()

    if args.export_file:
        if args.export_file == 'export text':
            export_to_file(session)
        else:
            export_to_file(session, args.export_file)

    if args.cableplan1:
        if args.cableplan2:
            compare_cable_plans(session, args.cableplan1[0], args.cableplan2[0])
        else:
            compare_cable_plans(session, args.cableplan1[0])


if __name__ == '__main__':
    main()

__all__ = [
    "CpPort",
    "CpLink",
    "CpSwitch",
    "CABLEPLAN",
]
