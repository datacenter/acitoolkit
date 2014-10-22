import sys
import getopt
import re
import base64
import datetime as datetime_

from acisession import Session
from credentials import *
from acitoolkit import *
from aciphysobject import *

etree_ = None
Verbose_import_ = False
(
    XMLParser_import_none, XMLParser_import_lxml,
    XMLParser_import_elementtree
) = range(3)
XMLParser_import_library = None
try:
    # lxml
    from lxml import etree as etree_
    XMLParser_import_library = XMLParser_import_lxml
    if Verbose_import_:
        print("running with lxml.etree")
except ImportError:
    try:
        # cElementTree from Python 2.5+
        import xml.etree.cElementTree as etree_
        XMLParser_import_library = XMLParser_import_elementtree
        if Verbose_import_:
            print("running with cElementTree on Python 2.5+")
    except ImportError:
        try:
            # ElementTree from Python 2.5+
            import xml.etree.ElementTree as etree_
            XMLParser_import_library = XMLParser_import_elementtree
            if Verbose_import_:
                print("running with ElementTree on Python 2.5+")
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree_
                XMLParser_import_library = XMLParser_import_elementtree
                if Verbose_import_:
                    print("running with cElementTree")
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree_
                    XMLParser_import_library = XMLParser_import_elementtree
                    if Verbose_import_:
                        print("running with ElementTree")
                except ImportError:
                    raise ImportError(
                        "Failed to import ElementTree from any known place")


def parsexml_(*args, **kwargs):
    if (XMLParser_import_library == XMLParser_import_lxml and
            'parser' not in kwargs):
        # Use the lxml ElementTree compatible parser so that, e.g.,
        #   we ignore comments.
        kwargs['parser'] = etree_.ETCompatXMLParser()
    doc = etree_.parse(*args, **kwargs)
    return doc

#
# Globals
#

Tag_pattern_ = re.compile(r'({.*})?(.*)')
#
# Support/utility functions.
#


def indent(level):

    indent_string = ''
    for idx in range(level):
        indent_string += '   '
    return indent_string


def quote_attrib(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
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




class CABLEPLAN :
    def __init__(self, version=None) :
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
    def get(cls,source) :
        """This will get input a cable plan from 'source'.  If source is a string,
        it will get the cable plan from XML in a file whose name is source.  If it is
        a Session, it will read the corresponding APIC to get the cable plan.

        INPUT: source = [str,Session]

        RETURNS: CABLEPLAN
        """
        if isinstance(source, str) :
            rootObj = cls._parse(source)
        elif isinstance(source, Session) :
            rootObj = cls._parseAPIC(source)
        return rootObj

    @classmethod
    def _parse(cls,inFileName, silence=True):
        doc = parsexml_(inFileName)
        # This can be enhanced to parse a string rather than just a file with the
        # following line:
        # doc = parsexml_(StringIO(inString))
        
        rootNode = doc.getroot()
        cable_plan = cls()
        cable_plan._buildXML(rootNode)
        return cable_plan

    @classmethod
    def _parseAPIC(cls,session):
        pod = Pod.get(session)[0]
        pod.populate_children(deep=True)
        cable_plan = cls()
        cable_plan._buildAPIC(pod)
        return cable_plan

    def get_switch(self, switch_name=None) :
        if switch_name :
            for switch in self.switches :
                if switch.get_name() == switch_name :
                    return switch
            return None
        else :
            return self.switches[:]
    def get_spines(self) :
        """Will return list of switches that are spines

        INPUT: None

        RETURNS: list of CP_SWITCH
        """

        switchList = []
        for switch in self.switches :
            if switch.isSpine() :
                switchList.append(switch)
        return switchList
    
                
    def add_switch(self, new_switch) :
        """This will new_switch to the CABLEPLAN.  If the switch already
        exists, it will merge the new_switch with the existing one.
        It will also set the parent of the switch to be the CABLEPLAN.  It will
        return the final switch, i.e. new_switch if no merge occurred or the
        newly merged switch if a merge did occur.

        INPUT: new_switch = CP_SWITCH

        RETURNS: CP_SWITCH
        """
        if not isinstance(new_switch, CP_SWITCH) :
            raise TypeError('add_switch expects object of type CP_SWITCH')
        
        new_switch.set_parent(self)
        for switch in self.switches :
            if switch == new_switch :
                switch.merge(new_switch)
                del new_switch
                return switch
        self.switches.append(new_switch)
        return new_switch
    
    def delete_switch(self, old_switch) :
        if old_switch in self.switches :
            self.switches.remove(old_switch)
            
    def exists_switch(self, switch) :
        return switch in self.switches
    
    def add_link(self, new_link) :
        """Will add a link to the CABLEPLAN.  Duplicates will not be allow, but overlapping will be.

        INPUT: new_link = CP_LINK

        RETURNS: None
        """
        
        if new_link not in self.links :
            self.links.append(new_link)
            
    def delete_link(self, link) :
        if link in self.links :
            self.links.remove(link)
            
    def exists_link(self, link) :
        return link in self.links
    
    def get_links(self, switch1=None, switch2=None) :
        """Returns a list of links.  If switch is unspecified, it will return all links.  If switch is specified,
        it will return all of the links that are connected to switch.  If both switch1 and swithc2 are specified,
        it will return all links that are connected between the two switches.

        INPUT: [switch=CP_SWITCH]

        RETURNS :  list of CP_LINK
        """
        
        if switch1 :
            link_list = []
            for link in self.links :
                if link.isConnected(switch1,switch2) :
                    link_list.append(link)
            return link_list
                
        else :
            return self.links[:]

    def difference_switch(self, cp) :
        """Will return a list of switches that are in self, but not in cp.

        INPUT: cp = CABLEPLAN

        RETURNS: list of CP_SWITCH
        """
        result = []
        myswitches = self.get_switch()
        cpswitches = cp.get_switch()
        for switch in myswitches:
            if switch not in cpswitches :
                result.append(switch)
        return result
    
    # Link comparison operations and support functions
    def _resetAccounting(self) :
        """clears the refernce count on each link
        """
        for link in self.links :
            link.resetAccounting()

    def _sorted_links(self, switch1, switch2) :
        """returns a sorted list of links between switch1 and switch2.  They are sorted by specificity from
        most specific to least specific.  The specificity is determined by which list of ports is the minimum
        between source and destination and which is the minimum across links.
        """
        result = []
        links = self.get_links(switch1, switch2)
        numLinks = len(links)
        for i in range(numLinks) :
            bestOrder = 100000
            for link in links :
                if (link.order() <  bestOrder) and (link not in result) :
                    bestOrder = link.order()
                    bestLink = link

            if bestOrder < 100000 :
                result.append(bestLink)
        return result
    
    def _switch_link_diff(self, cp, switch1, switch2) :
        """ returns a list links that go between switch1 and switch2 that are in self, but not in cp

        INPUT: cp=CABLEPLAN, switch1 = CP_SWITCH, switch2=CP_SWITCH

        RETURNS: list of CP_LINK
        """
        result = []
        myLinks = self._sorted_links(switch1, switch2)
        otherLinks = cp._sorted_links(switch1, switch2)
        for myLink in myLinks :
            
            if myLink.remainingNeed() > 0 :
                #still need to retire some link capacity
                
                for otherLink in otherLinks :  # loop through all of the otherLinks to find matches

                    if otherLink.remainingAvail() > 0 :
                        #there is still some capacity in otherLink
                        numMatch = CP_LINK.match_links(myLink, otherLink) #match-up links
                    if myLink.remainingNeed() == 0 :
                        #done with myLink, go get next one
                        break

    def difference_link(self, cp) :
        """returns a list of links that are in self, but not in cp.

        INPUT: cp=CABLEPLAN

        RETURNS: list of CP_LINK
        """
        result = []
        self._resetAccounting()
        cp._resetAccounting()
        for switch1 in self.get_switch() :
            for switch2 in self.get_switch() :
                self._switch_link_diff(cp, switch1, switch2)
        
        for myLink in self.get_links() :
            if myLink.remainingNeed() > 0 :
                result.append(myLink)
        return result
    
            
    def export(self, outFile=None, level = 0) :
        """Will generate XML text of the entire CABLEPLAN and return it as a string.  If
        outFile is specified, it will write the XML to that file.  outFile should be opened for
        writing before calling this method.  'level' specifies the amount of indentation to start with.
        """
        
        if outFile :
            if not isinstance(outFile, file) :
                raise TypeError('expected a file')

        eol_ = '\n'
        tag = 'CISCO_NETWORK_TYPES'

        text = ('<?xml version="1.0" encoding="UTF-8"?>\n')
        text += '<?created by cableplan.py?>\n'
        text += indent(level)
        text += '<%s version=%s xmlns=%s xmlns:%s=%s %s:schemaLocation=%s>\n' % (tag, quote_attrib(self.version), quote_attrib(self.namespace), self.prefix, quote_attrib(self.prefix_url), self.prefix, quote_attrib(self.namespace+' '+self.schemaLocation))

        text += self.export_data_center(level=level+1)
        text += indent(level)
        text += '</%s>\n' % tag

        if outFile :
            outFile.write(text)
        return text
        
    def export_data_center(self, level=0) :
        """Will generate the XML of the CABLEPLAN with DATA_CENTER as the root.  This will then be
        returned a string. 'level' specifies the indentation level to start with.

        INPUT: [level=int]

        RETURNS: str
        """
        tag = 'DATA_CENTER'
        text = indent(level)
        text += '<%s networkLocation=%s idFormat=%s>\n' % (tag, quote_attrib(self.networkLocation), quote_attrib(self.idFormat))
        switches = self.get_spines()
        for switch in switches :
            text += switch.export(level+1)
            
        text += indent(level)
        text += '</%s>\n' % tag

        return text


    def _get_attr_value(self,node,attr_name) :

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
    
    def _get_namespace_prefix(self, nsmap) :
        for nsmap_prefix in nsmap :
            if nsmap_prefix != None :
                self.prefix = nsmap_prefix
                self.prefix_url = nsmap[nsmap_prefix]

            if nsmap_prefix == None :
                self.namespace = nsmap[nsmap_prefix]
    def _get_switch_from_apic_link(self, link, end) :
        if end==1 :
            switch_name = link.get_node1().get_name()
        if end==2 :
            switch_name = link.get_node2().get_name()
        cp_switches = self.get_switch()
        for cp_switch in cp_switches :
            if cp_switch.get_name() == switch_name :
                return cp_switch
            
    def _buildAPIC(self, pod) :
        """This will build the cable plan using the configuration of the pod.

        INPUT: pod = Pod

        RETURNS: None
        """
        nodes = pod.get_children(Node)
        for node in nodes :

            if node.get_role() == 'spine' :
                self.add_switch(CP_SWITCH(node.get_name(), node.get_chassisType(), spine=True))
            if node.get_role() == 'leaf' :
                self.add_switch(CP_SWITCH(node.get_name(), node.get_chassisType()))
        links = pod.get_children(Link)
        for link in links :

            if link.get_node1().get_role() != 'controller' and link.get_node2().get_role() != 'controller' :
                sourceChassis = self._get_switch_from_apic_link(link,1)
                destChassis = self._get_switch_from_apic_link(link,2)
                sourceInterface = link.get_port1()
                destInterface = link.get_port2()
                sourcePort = '%s%s/%s' % (sourceInterface.interface_type, sourceInterface.module, sourceInterface.port)
                destPort = '%s%s/%s' % (destInterface.interface_type, destInterface.module, destInterface.port)
            
                self.add_link(CP_LINK(sourceChassis=sourceChassis, sourcePort=sourcePort,destChassis=destChassis,destPort=destPort))            

    def _buildXML(self, node) :

        #start at CISCO_NETWORK_TYPES
        self.version = self._get_attr_value(node, 'version')
        self.nsmap = node.nsmap #namespace prefix can be found here
        self._get_namespace_prefix(self.nsmap)  # parse out namespace and prefix
        self.schemaLocation = self._get_attr_value(node, 'xsi:schemaLocation').strip() #should refined to handle any namespace prefix
        for child in node :
            node_name = Tag_pattern_.match(child.tag).groups()[-1]
            if node_name == 'DATA_CENTER' :
                self._parseXML_DATA_CENTER(child)

    def _parseXML_DATA_CENTER(self, node) :
        self.networkLocation = self._get_attr_value(node, 'networkLocation')
        self.idFormat = self._get_attr_value(node, 'idFormat')
        for child in node :
            node_name = Tag_pattern_.match(child.tag).groups()[-1]
            if node_name == 'CHASSIS_INFO' :
                self._parseXML_CHASSIS_INFO(child)
                
    def _parseXML_CHASSIS_INFO(self,node) :
        chassis_name = self._get_attr_value(node, 'sourceChassis')
        chassis_type = self._get_attr_value(node, 'type')
        switch = CP_SWITCH(chassis_name, chassis_type, spine=True)
        self.add_switch(switch)
        for child in node :
            node_name = Tag_pattern_.match(child.tag).groups()[-1]
            if node_name == 'LINK_INFO' :
                self._parseXML_LINK_INFO(child, switch)
                
    def _parseXML_LINK_INFO(self,node,link_sourceChassis) :
        link_destChassis = self._get_attr_value(node, 'destChassis')
        link_destPort = self._get_attr_value(node, 'destPort')
        link_sourcePort = self._get_attr_value(node, 'sourcePort')
        link_minPorts = self._get_attr_value(node, 'minPorts')
        link_maxPorts = self._get_attr_value(node, 'maxPorts')

        switch = CP_SWITCH(link_destChassis,chassis_type=None)
        switch = self.add_switch(switch)
        
        link = CP_LINK(sourceChassis = link_sourceChassis, sourcePort = link_sourcePort, destChassis = switch, destPort = link_destPort, minPorts = link_minPorts, maxPorts= link_maxPorts)
        self.add_link(link)
        
        
class CP_SWITCH :
    """ class holding a switch """
    def __init__(self, name, chassis_type=None, spine=False, parent= None) :
        self.spine = spine
        self.name = name
        self.chassis_type = chassis_type
        self.parent = None
        if parent :
            self.set_parent(parent)
        
    def get_name(self) :
        """Gets the name of the chassis.

        INPUT: None

        RETURNS: str
        """
        return self.name
    def set_name(self, name) :
        """Sets the switch name.  This will over-ride any preexisting name.  Note that this new
        name will now become part of the link name for all the links attached to this switch.

        INPUT: name=str

        RETURNS: None
        """

        self.name = name
        return None
    
    
    def get_type(self) :
        """Gets the chassis type. Examples of chassis types are 'n7k' or 'n9k'

        INPUT : None
        
        RETURNS : str 
        """
        return self.chassis_type
    
    def set_parent(self, parent) :
        """Sets the parent of the switch.  Parent must be of type CABLEPLAN.  If a parent
        CABLEPLAN was already set and it is differnt from parent, then an error is raised.

        INPUT: parent=CABLEPLAN

        RETURNS: None
        """

        if not isinstance(parent, CABLEPLAN) :
            raise TypeError('expected parent to be of class CABLEPLAN')

        if self.parent:
            if self.parent != parent :
                raise ValueError('This switch was previously assigned to a different CABLEPLAN')

        self.parent = parent
        
    def isSpine(self) :
        """Checks if the 'spine' flag is set.

        INPUT: None

        RETURNS: Boolean
        """
        
        return self.spine
    def merge(self, new_switch) :
        """ Merges the content of new_switch with self.  If self has variables set, then they will
        not be changed.  If they have not been set, then they will be assigned the value from new_switch.

        INPUT: new_switch=CP_SWITCH
        
        RETURNS: None
        """
        if new_switch.spine : self.spine = new_switch.spine
        if new_switch.chassis_type : self.chassis_type = new_switch.chassis_type
            
    def __eq__(self, other) :
        return self.name == other.name
    def get_links(self) :
        """returns a list of CP_LINKS from the parent CABLEPLAN that are connected to self.

        INPUT: None

        RETURNS: list of CP_LINKS
        """
        return self.parent.get_links(self)
        
        
    def __str__(self) :
        return self.name
    
    def export(self, level) :
        tag = 'CHASSIS_INFO'
        text = indent(level)
        text += '<%s sourceChassis=%s type=%s>\n' % (tag, quote_attrib(self.get_name()), quote_attrib(self.get_type()))
        links = self.get_links()
        for link in links :
            text += link.export(self,level+1)
            
        text += indent(level)
        text += '</%s>\n' % tag
        return text
#end class CP_SWITCH

class CP_PORT :
    """This class holds the information for a link's port.  Since the port can be a single port, a list
    or a range, putting it in a class allows more flexible operations on it.
    """
    def __init__(self, portSet) :
        self.ports = self._expand(portSet)

    def _expand(self, portSet) :
        """Will parse the portSet and return a list of enumerated ports or None.
        portSet is string containing a comma separated list of ports or port ranges.
        A port range consists of a starting port separated from an ending port with a dash.
        Both the starting port and ending port are included in the list.
        The format for a port is a string that ends in a forward slash followed by a number.  The number is what is incremented
        for a range.  A dash, '-' is not legal in the port name.

        INPUT: portSet = str

        RETURNS: list of str
        """

        if portSet == None :
            return []
        
        portList = set()  #use a set so that there are no duplicate ports
        portSet = re.sub('\s+','',portSet)  # remove unnecessary white space
        portsNranges = re.split(',',portSet)
        for portOrRange in portsNranges :
            if '-' in portOrRange :
                # this is a range
                [startport, endport] = re.split('-',portOrRange)
                prefix = re.findall('(.*/)\d+$', startport)
                if len(prefix) != 1 :
                    raise ValueError('Badly formed port name in range:"'+startport+'"')
                
                prefix_e = re.findall('(.*/)\d+$', endport)
                if len(prefix_e) != 1 :
                    raise ValueError('Badly formed port name in range:"'+endport+'"')
                
                if prefix[0] != prefix_e[0] :
                    raise ValueError('port range invalid:"'+portOrRange+'"')
                startNum = int(re.findall('(\d+)$', startport)[0])
                endNum = int(re.findall('(\d+)$', endport)[0])

                if startNum > endNum :
                    raise ValueError('port range invalid - start of range cannot be higher than end:"'+portOrRange+'"')
                
                for index in range(startNum, endNum+1) :
                    portName = prefix[0] + str(index)
                    portList.add(portName)
            else :
                # this is just a port
                portList.add(portOrRange)
        return sorted(list(portList))
    
    def _rangeify(self) :
        """ this will take the list of ports and return a string of comma separated ports and port
        ranges.  A port range will be generated for any sequence longer than two ports.
        """
        if not self.ports :
            return None
        
        text_list = []
        index = 0
        numports = len(self.ports)
        done = False

        startPort = self.ports[index]
        curPort = startPort
        curNum = int(re.findall('(\d+)$', curPort)[0])
        curPrefix = re.findall('(.*/)\d+$', curPort)[0]
        startNum = int(re.findall('(\d+)$', startPort)[0])
        while index < (numports-1) :
            nextPort = self.ports[index+1]
            nextNum = int(re.findall('(\d+)$', nextPort)[0])
            nextPrefix = re.findall('(.*/)\d+$', nextPort)[0]
            if nextNum != curNum+1 or nextPrefix != curPrefix:
                # there is a break in the sequence terminate the range
                if curNum==startNum :
                    text_list.append(startPort)
                elif curNum - startNum == 1 :
                    text_list.append(startPort)
                    text_list.append(curPort)
                else :
                    text_list.append(startPort+' - '+curPort)
                    
                startPort = nextPort
                startNum = int(re.findall('(\d+)$', startPort)[0])
                
            index += 1
            curPort = self.ports[index]
            curNum = int(re.findall('(\d+)$', curPort)[0])
            curPrefix = re.findall('(.*/)\d+$', curPort)[0]
                            
        # clean-up - index is one past end, cur is last one looked at
        if curNum==startNum :
            text_list.append(startPort)
        elif curNum - startNum == 1 :
            text_list.append(startPort)
            text_list.append(curPort)
        else :
            text_list.append(startPort+' - '+curPort)

        if text_list == [] :
            text = None
        else :
            text = ', '.join(text_list)

        return text
    def resetAccounting(self) :
        self.available_ports = self.ports[:]
    def remove_available_port(self, port) :
        if self.ports == None :
            return
        else :
            if port in self.available_ports :
                self.available_ports.remove(port)
                
    def list(self) :
        return self.ports[:]
    def __str__(self) :
        text = self._rangeify()
        return str(text)
    def name(self) :
        text = self._rangeify()
        return text
    
    def __eq__(self, other) :
        """ compares the content of the port list and returns true if they are the same.  The comparison is case insensitive.
        """
        
        if not self.ports and not other.ports :
            return True
        elif not self.ports and other.ports :
            return False
        elif self.ports and not other.ports :
            return False

        my_ports = set()
        for port in self.ports :
            my_ports.add(port.lower())
            
        other_ports = set()
        for port in other.ports :
            other_ports.add(port.lower())
            
        if len(my_ports ^ other_ports) == 0 :
            return True
        else :
            return False
        
        
class CP_LINK : 
    def __init__(self, sourceChassis, destChassis, sourcePort = None, destPort = None, minPorts = None, maxPorts = None) :
        
        if not isinstance(sourceChassis, CP_SWITCH) :
            raise TypeError('expected sourceChassis to be of class CP_SWITCH')
        if not isinstance(destChassis, CP_SWITCH) :
            raise TypeError('expected destChassis to be of class CP_SWITCH')

        # allow initialization to be with a list or a string for ports.
        # convert all to a string
        if isinstance(destPort, list) :
            destPort = ', '.join(destPort)
        if isinstance(sourcePort, list) :
            sourcePort = ', '.join(sourcePort)
            
        self.minPorts = minPorts
        self.maxPorts = maxPorts
        # initially normalize name
        if sourceChassis.get_name() < destChassis.get_name() :
            self.sourceChassis = sourceChassis
            self.sourcePort = CP_PORT(sourcePort)
            self.destChassis = destChassis
            self.destPort = CP_PORT(destPort)
             
        else :
            self.sourceChassis = destChassis
            self.sourcePort = CP_PORT(destPort)
            self.destChassis = sourceChassis
            self.destPort = CP_PORT(sourcePort)

        # count to track references to a particular link
        self.resetAccounting()

        # the maximum reference count is either self.maxPorts or is the maximum number of physical links
        # that this link can specify, whichever is smaller.  If there is no limit, then maxRef is set to 10000

        if self.destPort.ports and self.sourcePort.ports :
            maxPhysPorts = min(len(self.destPort.ports), len(self.sourcePort.ports))
        elif self.destPort.ports :
            maxPhysPorts = len(self.destPort.ports)
        elif self.sourcePort.ports :
            maxPhysPorts = len(self.sourcePort.ports)
        else :
            maxPhysPorts = 10000

        if self.maxPorts :
            self.maxRef = min(maxPhysPorts, self.maxPorts)
        else :
            self.maxRef = maxPhysPorts

        # self.minRef is the minimum number of physical links needed to meet the requirements of this link
        if self.minPorts :
            self.minRef = int(self.minPorts)
        else :
            self.minRef = 1
            
    def resetAccounting(self) :
        """Resets account on the source and dest ports as well as reference count

        INPUT: None

        RETURNS: None
        """
        self.destPort.resetAccounting()
        self.sourcePort.resetAccounting()
        self.refCount = 0

    def remainingNeed(self) :
        """ returns the remaining number of physical links needed to match against self to satisfy requirements.
        The parameters used to calculate this value are reset by the resetAccounting() method which is typically
        invoked when invoking a difference_link() method on the CABLEPLAN parent object.

        INPUT: None

        RETURNS: int
        """
        return max(0,self.minRef-self.refCount)
    
    def remainingAvail(self):
        """ returns the remaining number of physical links available to match against
        The parameters used to calculate this value are reset by the resetAccounting() method which is typically
        invoked when invoking a difference_link() method on the CABLEPLAN parent object.

        INPUT: None

        RETURNS: int
        """
        
        return max(0,self.maxRef-self.refCount)
    
    def order(self) :
        """Calculates the order of the link defined by the maximum number of physical links this link
        can represent

        INPUT: None

        RETURNS: int
        """
        if self.sourcePort.ports and self.destPort.ports :
            result = min(len(self.sourcePort.ports), len(self.destPort.ports))
        elif self.sourcePort.ports :
            result = len(self.sourcePort.ports)
        elif self.destPort.ports :
            result = len(self.destPort.ports)
        else :
            result = 10000  # this is the any-any case which is unlimited.
        return result
    
    def get_name(self) :
        if self.sourcePort.name() :
            sText = '%s-%s' % (self.sourceChassis, self.sourcePort.name())
        else :
            sText = '%s' % self.sourceChassis
            
        if self.destPort.name() :
            dText = '%s-%s' % (self.destChassis, self.destPort.name())
        else :
            dText = '%s' % self.destChassis
            
        return '(%s,%s)' % (sText, dText)

    def isConnected(self, switch1, switch2=None ) :
        """Returns True if switch1 is one of the switch endpoints of the link and switch2 is unspecified
        otherwise is will return True if both switch1 and switch2 are switch endpoints of the link.  If
        switch1 is the same as switch2, it will return False.

        INPUT: switch1 = CP_SWITCH, [switch2=CP_SWITCH]

        RETURNS: Boolean
        """
        s1 = (switch1 == self.sourceChassis) or (switch1 == self.destChassis)
        if switch2 :
            s2 = (self.sourceChassis == switch2) or (self.destChassis ==switch2 )
        else :
            s2 = True

        result = s1 and s2 and (switch1 != switch2)
        return result
    
            
            
    def __eq__(self, other) :
        if ((self.sourceChassis == other.sourceChassis) and (self.sourcePort==other.sourcePort) and
            (self.destChassis == other.destChassis) and (self.destPort == other.destPort)) :
            return True
        return False
    

    def hasPortInCommon(self,link):
        """Returns True if link has any ports that match self.  It will compare
        all ports included expanded lists of port sets.

        INPUT: link=CP_LINK
        
        RETURNS: Boolean
        """
        
        if link.sourceChassis == self.sourceChassis :
            lnk_ports = set(link.sourcePort.list())
            slf_ports = set(self.sourcePort.list())
            if len(lnk_ports & slf_ports) > 0 :
                return True
        
        if link.destChassis == self.destChassis :
            lnk_ports = set(link.destPort.list())
            slf_ports = set(self.destPort.list())
            if len(lnk_ports & slf_ports) > 0 :
                return True
        
        if link.sourceChassis == self.destChassis :
            lnk_ports = set(link.sourcePort.list())
            slf_ports = set(self.destPort.list())
            if len(lnk_ports & slf_ports) > 0 :
                return True
        
        if link.destChassis == self.sourceChassis :
            lnk_ports = set(link.destPort.list())
            slf_ports = set(self.sourcePort.list())
            if len(lnk_ports & slf_ports) > 0 :
                return True
        
        
        return False
    
                                     
    def __str__(self) :
        return self.get_name()
    
    def _get_attrib_str(self,attrib, value) :
        text = ''
        if value != None :
            text = '%s=%s ' % (attrib, quote_attrib(value))
        return text
            
    def export(self, chassis, level) :
        """Will return string of XML describing the LINK_INFO.  It will use 'chassis' to determine
        which is the source chassis so that it will be omitted from the XML and the other chassis will
        become the destination.  'level' is the indentation level.

        INPUT: chassis=CP_SWITCH, level=int
        
        RETURNS: str
        """
        
        tag = 'LINK_INFO'
        
        if chassis == self.sourceChassis :

            dPortText = self._get_attrib_str('destPort', self.destPort.name())
            sPortText = self._get_attrib_str('sourcePort', self.sourcePort.name())
            dChassisText = self._get_attrib_str('destChassis', self.destChassis)
        else :
            dPortText = self._get_attrib_str('destPort', self.sourcePort.name())
            sPortText = self._get_attrib_str('sourcePort', self.destPort.name())
            dChassisText = self._get_attrib_str('destChassis', self.sourceChassis)
            
        minPortText = self._get_attrib_str('minPorts', self.minPorts)
        maxPortText = self._get_attrib_str('maxPorts', self.maxPorts)
            
        text = '<%s %s%s%s%s%s' % (tag, sPortText, dChassisText, dPortText, minPortText, maxPortText)
        text = indent(level) + text.strip()
        text += '/>\n'
        return text
    
    @staticmethod
    def match_links(link1, link2) :
        """This will match-up link1 and link2 and increment the reference count in each link for each
        of the matches that happen.  It will do this until the minimum number of links has been reached for
        link1.  It will return the number of matches that occurred.

        INPUT: link1=CP_LINK, link2=CP_LINK

        RETURNS: int
        """

        result = 0
        # match-up ends of link
        if (link1.sourceChassis == link2.sourceChassis) and (link1.destChassis == link2.destChassis) :
            start1 = link1.sourcePort
            start2 = link2.sourcePort
            end1 = link1.destPort
            end2 = link2.destPort
        else :
            # chassis don't match so no link match
            return 0
        
        #get ends in common - the maximum match will be the min of this overlap
        if start1.ports != [] and start2.ports!=[] :
            starts = list(set(start1.available_ports) & set(start2.available_ports))
        elif start1.ports !=[] :
            starts = start1.available_ports[:]
        elif start2.ports !=[] :
            starts = start2.available_ports[:]
        else :
            starts = 'any'
                
        
        if end1.ports != [] and end2.ports!=[] :
            ends = list(set(end1.available_ports) & set(end2.available_ports))
        elif end1.ports !=[] :
            ends = end1.available_ports[:]
        elif end2.ports !=[] :
            ends = end2.available_ports[:]
        else :
            ends = 'any'
            
        if starts == 'any':
            lenStarts = 10000
        else :
            lenStarts = len(starts)

        if ends == 'any':
            lenEnds = 10000
        else :
            lenEnds = len(ends)

    
        numToRetire = min(link1.remainingNeed(),link2.remainingAvail(),lenStarts,lenEnds)

        for index in range(numToRetire) :

            if starts != 'any' :
                start1.remove_available_port(starts[index])
                start2.remove_available_port(starts[index])
            if ends != 'any' :
                end1.remove_available_port(ends[index])
                end2.remove_available_port(ends[index])
                
            link1.refCount += 1
            link2.refCount += 1
            result += 1
        return result
    
        
#end class LINK


USAGE_TEXT = """
Usage: python cableplan.py -c <in_xml_file1> [<in_xml_file2>]
Usage: python cableplan.py -e [<out_xml_file>]
   -c : compare.  If two file names are given, then they will be compared,
        if only one file is given, it will be compared to the running fabric
        
   -e : export.  This will read from the fabric and export to the named file
        the currently running cable plan.  If no filename is given, it will
        just output the text.
"""

def compareCablePlans(file1, file2=None) :
    if file2 :
        cp1 = CABLEPLAN.get(file1)
        source1 = file1
        cp2 = CABLEPLAN.get(file2)
        source2 = file2
    else :
        session  = Session(URL, LOGIN, PASSWORD)
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

    if missing_switches :
        print '\nThe following switches are in',source1+', but not in',source2
        for switch in missing_switches :
            print '   ',switch.get_name()

    if extra_switches :
        print '\nThe following switches are in',source2+', but not in',source1
        for switch in missing_switches :
            print '   ',switch.get_name()

    if missing_switches or extra_switches :
        print 'Link comparisons skipped because the switches are miss-matched'
    else :
        missing_links = cp1.difference_link(cp2)
        extra_links = cp2.difference_link(cp1)

        if missing_links :
            print '\nThe following links in',source1,'are not found in',source2
            for link in missing_links :
                print '   ',link.get_name()
                
        if extra_links :
            print '\nThe following links in',source2,'are not found in',source1
            for link in extra_links :
                print '   ',link.get_name()
        if not missing_links and not extra_links :
            print source1,'and',source2,'are the same'
            

def exportToFile(file1=None) :
    session  = Session(URL, LOGIN, PASSWORD)
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        sys.exit(1)
    cp = CABLEPLAN.get(session)
    
    
    if file1 :
        f = open(file1, 'w')
        cp.export(f)
        f.close()
    else :
        print cp.export(),
        
        
    
def usage():
    print USAGE_TEXT
    sys.exit(1)

def main():
    args = sys.argv[1:]
    if len(args) in [1,2, 3]:
        if args[0] == '-e' :
            if len(args) == 1 :
                exportToFile()
            elif len(args) == 2 :
                exportToFile(args[1])
            else :
                usage()
        elif args[0] == '-c' :
            if len(args) == 2 :
                compareCablePlans(args[1])
            elif len(args) == 3 :
                compareCablePlans(args[1], args[2])
            else :
                usage()
    else:
        usage()


if __name__ == '__main__':
    main()


__all__ = [
    "CP_PORT",
    "CP_LINK",
    "CP_SWITCH",
    "CABLEPLAN",
]
