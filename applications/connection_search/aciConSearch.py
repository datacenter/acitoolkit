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
"""  Connection Search

    This file contains the main routine for reading in the APIC configuration,
    putting it into searchable data structures, and providing an interface
    whereby a search query, in the form of a flow specification, can be made
    and all the matching flow specifications are returned.

    The flow specification used in the search allows any of the fields to be ignored,
    i.e. match any, and the IP addresses to be masked, e.g. you can specify the source
    IP address, SIP, to be 10.13/6
"""
import sys
from copy import copy
import radix
import re
from acitoolkit import Endpoint, Tenant, AppProfile, Contract, EPG, OutsideL3, OutsideEPG, Subnet, ContractSubject, \
    FilterEntry, Context
from acitoolkit.aciphysobject import Session
from acitoolkit.acitoolkitlib import Credentials

SQL = False
TESTMODE = False


class LoginError(Exception):
    """
    Exception for login errors.
    """
    pass


class IpAddress(object):
    """
    This class holds an IP address and allows various functions to be performed on it
    """

    def __init__(self, ip):

        if isinstance(ip, str):

            sections = ip.split('/')
            if len(sections) == 1:
                self._prefixlen = 32
            else:
                self._prefixlen = int(sections[1])

            self.addr = IpAddress.parse_text(sections[0])
        if isinstance(ip, int):
            self._prefixlen = 32
            self.addr = self.n2s(ip)

    @staticmethod
    def parse_text(input_ip):
        ip_bytes = []
        fields = input_ip.split('.')
        if len(fields) > 0:
            ip_bytes.append(fields[0])

        if len(fields) > 1:
            ip_bytes.append(fields[1])
        else:
            ip_bytes.append('0')

        if len(fields) > 2:
            ip_bytes.append(fields[2])
        else:
            ip_bytes.append('0')

        if len(fields) > 3:
            ip_bytes.append(fields[3])
        else:
            ip_bytes.append('0')

        return '.'.join(ip_bytes)

    @property
    def prefix(self):
        return self._get_prefix()

    @property
    def prefixlen(self):
        return self._prefixlen

    @property
    def mask(self):
        return self.n2s(self.mask_num)

    @property
    def mask_num(self):
        return ~(0xFFFFFFFF >> self.prefixlen)

    def _get_prefix(self):
        return self.n2s(self.s2n(self.addr) & self.mask_num) + '/' + str(self.prefixlen)

    def overlap(self, other):
        """
        This will return an IpAddress that is the overlap of self and other
        :param other:
        :return:
        """

        assert isinstance(other, IpAddress)
        max_addr = min(self.max_address(), other.max_address())
        min_addr = max(self.min_address(), other.min_address())

        if min_addr <= max_addr:
            if self.prefixlen > other.prefixlen:
                return self
            else:
                return other

    @staticmethod
    def simplify(ip_list):
        """
        Will combine and then supernet prefixes in list to
        come up with the most simple list
        :param ip_list:
        :return:
        """
        return IpAddress.supernet(IpAddress.combine(ip_list))

    @staticmethod
    def supernet(ip_list):
        """
        Will combine subnets into larger subnets
        :param ip_list:
        :return:
        """
        if len(ip_list) == 1:
            return ip_list

        new_list = copy(ip_list)
        for ip1 in ip_list:
            for index in reversed(range(len(new_list))):
                ip2 = new_list[index]
                if ip1 != ip2:
                    p1 = ip1.prefix_num >> (32 - ip1.prefixlen)
                    p2 = ip2.prefix_num >> (32 - ip2.prefixlen)
                    if (p1 - p2 == 1) and (p1 & 0xFFFFFFFE) == (p2 & 0xFFFFFFFE):
                        new_ip = IpAddress(str(ip1.prefix))
                        new_ip._prefixlen -= 1
                        new_list.remove(ip1)
                        new_list.remove(ip2)
                        new_list.append(new_ip)

        if len(new_list) == len(ip_list):
            return new_list
        else:
            return IpAddress.supernet(new_list)

    @staticmethod
    def combine(ip_list):
        """
        Will go through list and combine any prefixes that can be combined
        and return a new list with result.
        :param ip_list:
        :return:
        """
        new_list = copy(ip_list)
        if len(ip_list) > 1:
            for candidate in ip_list:
                for index in reversed(range(len(new_list))):
                    other = new_list[index]
                    if candidate != other:
                        if IpAddress.encompass(candidate, other):
                            new_list.remove(other)
            if len(new_list) == len(ip_list):
                return new_list
            else:
                return IpAddress.combine(new_list)

        else:
            return ip_list

    @staticmethod
    def encompass(ip1, ip2):
        if ip1.min_address() <= ip2.min_address() and ip1.max_address() >= ip2.max_address():
            return True
        else:
            return False

    def min_address(self):
        """
        returns minimum address in the subnet
        :return:
        """
        return IpAddress(self.n2s(self.prefix_num))

    def max_address(self):
        """
        returns the maximum address in the subnet
        :return:
        """

        return IpAddress(self.prefix_num | ~self.mask_num)

    @staticmethod
    def s2n(address):
        """
        This will convert an address string to a number and return the number
        :param address:
        :return:
        """
        fields = address.split('.')
        result = int(fields[0]) * (2 ** 24)
        result1 = int(fields[1]) * (2 ** 16)
        result2 = int(fields[2]) * (2 ** 8)
        result3 = int(fields[3])
        return result + result1 + result2 + result3

    @property
    def prefix_num(self):
        """
        Will return numeric version of the prefix
        :return:
        """
        sections = self.prefix.split('/')
        fields = sections[0].split('.')
        result = int(fields[0])
        result = (result << 8) + int(fields[1])
        result = (result << 8) + int(fields[2])
        result = (result << 8) + int(fields[3])
        return result

    @staticmethod
    def n2s(address):
        """
        will return a string in the x.y.w.z format given a number
        :param address:
        :return:
        """
        b3 = str((address & 0xFF000000) >> 24)
        b2 = str((address & 0x00FF0000) >> 16)
        b1 = str((address & 0x0000FF00) >> 8)
        b0 = str(address & 0x000000FF)
        return '.'.join([b3, b2, b1, b0])

    def equiv(self, other):
        """
        Checks to see if self is equivalent to other
        This is just like ==, except it will check the prefixes rather than the absolute address
        values.
        :param other:
        :return:
        """
        if str(self.prefix) == str(other.prefix):
            return True
        else:
            return False

    def __repr__(self):
        return '{0}/{1}'.format(self.addr, self.prefixlen)

    def __eq__(self, other):

        if isinstance(other, str):
            if self != IpAddress(other):
                return False
        else:
            if not isinstance(self, IpAddress) or not isinstance(other, IpAddress):
                return False

            if self.prefix_num != other.prefix_num:
                return False
            if self.prefixlen != other.prefixlen:
                return False
            return True

    def __ne__(self, other):

        if self == other:
            return False
        else:
            return True

    def __gt__(self, other):
        """
        returns True if self is greater than other
        :param other:
        :return:
        """
        if self.prefixlen == other.prefixlen:
            return self.min_address().prefix_num > other.min_address().prefix_num
        else:
            return self.prefixlen < other.prefixlen

    def __ge__(self, other):
        """
        returns True if self is greater than or equal to other
        :param other:
        :return:
        """
        if self.prefixlen == other.prefixlen:
            return self.prefix_num >= other.prefix_num
        else:
            return self.prefixlen < other.prefixlen

    def __lt__(self, other):
        """
        returns True if self is less than other
        :param other:
        :return:
        """
        if self.prefixlen == other.prefixlen:
            return self.prefix_num < other.prefix_num
        else:
            return self.prefixlen > other.prefixlen

    def __le__(self, other):
        """
        returns True if self is less than or equal to other
        :param other:
        :return:
        """
        if self.prefixlen == other.prefixlen:
            return self.prefix_num <= other.prefix_num
        else:
            return self.prefixlen > other.prefixlen


# noinspection PyPep8Naming,PyPep8Naming,PyPep8Naming,PyPep8Naming
class ProtocolFilter(object):
    def __init__(self, aci_filter=None):
        self._applyToFrag = 'any'
        self._arpOpc = 'any'
        self._etherT = 'any'
        self._dFromPort = 'any'
        self._dToPort = 'any'
        self._prot = 'any'
        self._sFromPort = 'any'
        self._sToPort = 'any'
        self._tcpRules = 'any'
        if aci_filter is not None:
            self.applyToFrag = aci_filter.applyToFrag
            self.arpOpc = aci_filter.arpOpc
            self.etherT = aci_filter.etherT
            self.dFromPort = aci_filter.dFromPort
            self.dToPort = aci_filter.dToPort
            self.prot = aci_filter.prot
            self.sFromPort = aci_filter.sFromPort
            self.sToPort = aci_filter.sToPort
            self.tcpRules = aci_filter.tcpRules

    @property
    def applyToFrag(self):
        return self._applyToFrag

    @applyToFrag.setter
    def applyToFrag(self, value):
        if value == 'unspecified' or value is None or value == 'any' or value == '*':
            self._applyToFrag = 'any'
        elif value == 'no':
            self._applyToFrag = False
        elif value == 'yes':
            self._applyToFrag = True
        else:
            assert isinstance(value, bool)
            self._applyToFrag = value

    @property
    def arpOpc(self):
        return self._arpOpc

    @arpOpc.setter
    def arpOpc(self, value):
        if value == 'unspecified' or value is None or value == 'any' or value == '*':
            self._arpOpc = 'any'
        else:
            self._arpOpc = value

    @property
    def dFromPort(self):
        return self._dFromPort

    @dFromPort.setter
    def dFromPort(self, value):
        if value == 'unspecified' or value == 'any' or value is None:
            self._dFromPort = 'any'
        else:
            if isinstance(value, str):
                self._dFromPort = self._port_from_string(value)
            else:
                self._dFromPort = value

    @staticmethod
    def _port_from_string(value):
        match_result = re.match('^\d+$', value)
        if match_result is not None:
            return int(value)
        else:
            if value == 'https':
                return 443
            if value == 'http':
                return 80
            if value == 'ftp-data':
                return 20
            if value == 'smtp':
                return 25
            if value == 'dns':
                return 53
            if value == 'pop3':
                return 110
            if value == 'rtsp':
                return 554
            raise ValueError('Unrecognized layer 4 port value in filter: ' + value)

    @property
    def dToPort(self):
        return self._dToPort

    @dToPort.setter
    def dToPort(self, value):
        if value == 'unspecified' or value == 'any' or value is None:
            self._dToPort = 'any'
        else:
            if isinstance(value, str):
                self._dToPort = self._port_from_string(value)
            else:
                self._dToPort = value

    @property
    def sFromPort(self):
        return self._sFromPort

    @sFromPort.setter
    def sFromPort(self, value):
        if value == 'unspecified' or value == 'any' or value is None:
            self._sFromPort = 'any'
        else:
            if isinstance(value, str):
                self._sFromPort = self._port_from_string(value)
            else:
                self._sFromPort = value

    @property
    def sToPort(self):
        return self._sToPort

    @sToPort.setter
    def sToPort(self, value):
        if value == 'unspecified' or value == 'any' or value is None:
            self._sToPort = 'any'
        else:
            if isinstance(value, str):
                self._sToPort = self._port_from_string(value)
            else:
                self._sToPort = value

    @property
    def etherT(self):
        return self._etherT

    @etherT.setter
    def etherT(self, value):
        if value == 'unspecified' or value is None:
            self._etherT = 'any'
        else:
            self._etherT = value

    @property
    def prot(self):
        return self._prot

    @prot.setter
    def prot(self, value):
        if value == 'unspecified' or value is None:
            self._prot = 'any'
        else:
            self._prot = value

    @property
    def tcpRules(self):
        return self._tcpRules

    @tcpRules.setter
    def tcpRules(self, value):
        if value == 'unspecified':
            self._tcpRules = 'any'
        else:
            self._tcpRules = value

    def overlap(self, other):
        """
        will return a ProtocolFilter that is the intersection of self and other
        :param other:
        :return:
        """
        result = ProtocolFilter()
        if self.applyToFrag != 'any' and other.applyToFrag != 'any':
            if self.applyToFrag != other.applyToFrag:
                return None
        result.applyToFrag = other.applyToFrag if self.applyToFrag == 'any' else self.applyToFrag

        if self.arpOpc != 'any' and other.arpOpc != 'any':
            if self.arpOpc != other.arpOpc:
                return None
        result.arpOpc = other.arpOpc if self.arpOpc == 'any' else self.arpOpc

        if self.dFromPort == 'any':
            result.dFromPort = other.dFromPort
        elif other.dFromPort == 'any':
            result.dFromPort = self.dFromPort
        else:
            result.dFromPort = max(self.dFromPort, other.dFromPort)

        if self.dToPort == 'any':
            result.dToPort = other.dToPort
        elif other.dToPort == 'any':
            result.dToPort = self.dToPort
        else:
            result.dToPort = min(self.dToPort, other.dToPort)

        if result.dFromPort > result.dToPort:
            return None

        if self.sFromPort == 'any':
            result.sFromPort = other.sFromPort
        elif other.sFromPort == 'any':
            result.sFromPort = self.sFromPort
        else:
            result.sFromPort = max(self.sFromPort, other.sFromPort)

        if self.sToPort == 'any':
            result.sToPort = other.sToPort
        elif other.sToPort == 'any':
            result.sToPort = self.sToPort
        else:
            result.sToPort = min(self.sToPort, other.sToPort)

        if result.sFromPort > result.sToPort:
            return None

        if self.etherT is not 'any' and other.etherT is not 'any':
            if self.etherT != other.etherT:
                return None
        result.etherT = other.etherT if self.etherT is 'any' else self.etherT

        if self.prot is not 'any' and other.prot is not 'any':
            if self.prot != other.prot:
                return None
        result.prot = other.prot if self.prot is 'any' else self.prot

        if self.tcpRules is not 'any' and other.tcpRules is not 'any':
            if self.tcpRules != other.tcpRules:
                return None
        result.tcpRules = other.tcpRules if self.tcpRules is 'any' else self.tcpRules
        return result

    def __str__(self):
        dport = '{0}-{1}'.format(self.dFromPort, self.dToPort)
        sport = '{0}-{1}'.format(self.sFromPort, self.sToPort)
        return '{0:4} {1:11} {2:11}'.format(self.prot, dport, sport)

    def _port_equal(self, other):
        if self.dFromPort != other.dFromPort:
            return False
        if self.dToPort != other.dToPort:
            return False
        if self.sFromPort != other.sFromPort:
            return False
        if self.sToPort != other.sToPort:
            return False
        return True

    def __eq__(self, other):
        if self.applyToFrag != other.applyToFrag:
            return False
        if self.arpOpc != other.arpOpc:
            return False
        if self.etherT != other.etherT:
            return False
        if not self._port_equal(other):
            return False
        if self.tcpRules != other.tcpRules:
            return False
        return True

    def __gt__(self, other):
        if self.dFromPort > other.dFromPort:
            return True
        if self.sFromPort > other.sFromPort:
            return True
        if self.dToPort > other.dToPort:
            return True
        if self.sToPort > other.sToPort:
            return True
        return False

    def __ge__(self, other):
        return self > other or self._port_equal(other)

    def __lt__(self, other):
        return not self >= other

    def __le__(self, other):
        return self < other or self._port_equal(other)


class SubFlowSpec(object):
    """
    defines one side of a flow without the port numbers, i.e. either source or destination
    """

    def __init__(self, tenant, context, ip):
        self.tenant_name = tenant
        self.context_name = context
        self.ip = ip


class FlowSpec(object):
    """
    This is a structure that holds a flow spec

    """

    def __init__(self):
        self._sip = [IpAddress('0/0')]
        self._dip = [IpAddress('0/0')]
        self.tenant_name = ''
        self.context_name = ''
        self.protocol_filter = []

    def get_source(self):
        return SubFlowSpec(self.tenant_name, self.context_name, self.sip)

    def get_dest(self):
        return SubFlowSpec(self.tenant_name, self.context_name, self.dip)

    @property
    def sip(self):
        return self._sip

    @sip.setter
    def sip(self, value):
        if isinstance(value, list):
            self._sip = value
        elif isinstance(value, str):
            self._sip = [IpAddress(value)]
        else:
            assert isinstance(value, IpAddress)
            self._sip = [value]

    @property
    def dip(self):
        return self._dip

    @dip.setter
    def dip(self, value):
        if isinstance(value, list):
            self._dip = value
        elif isinstance(value, str):
            self._dip = [IpAddress(value)]
        else:
            assert isinstance(value, IpAddress)
            self._dip = [value]

    def __str__(self):
        extras = max(len(self.sip), len(self.dip), len(self.protocol_filter))
        full_sip = sorted(self.sip)
        full_dip = sorted(self.dip)
        tc = '{0}/{1}'.format(self.tenant_name, self.context_name)

        line_format = '{0:20} {1:18} {2:18} {3:28}\n'
        result = line_format.format(tc, full_sip[0], full_dip[0], self.protocol_filter[0])
        if extras > 1:
            for index in range(1, extras):
                dip = ''
                sip = ''
                prot_filter = ''
                if len(full_dip) > index:
                    dip = full_dip[index]
                if len(full_sip) > index:
                    sip = full_sip[index]
                if len(self.protocol_filter) > index:
                    prot_filter = str(self.protocol_filter[index])

                result += line_format.format('', sip, dip, prot_filter)

        return result

    def __eq__(self, other):
        if self.tenant_name != other.tenant_name:
            return False
        if self.context_name != other.context_name:
            return False

        set1 = set()
        set2 = set()
        for item in self.dip:
            set1.add(str(item.prefix))
        for item in other.dip:
            set2.add(str(item.prefix))
        if len(set1 ^ set2) > 0:
            return False
        set1 = set()
        set2 = set()
        for item in self.sip:
            set1.add(str(item.prefix))
        for item in other.sip:
            set2.add(str(item.prefix))
        if len(set1 ^ set2) > 0:
            return False

        set1 = set()
        set2 = set()
        for item in self.protocol_filter:
            set1.add(str(item))
        for item in other.protocol_filter:
            set2.add(str(item))
        if len(set1 ^ set2) > 0:
            return False

        return True

    def __gt__(self, other):
        """
        returns true if self is greater than other based on comparing sip and then dip
        :param other:
        :return:
        """

        if self == other:
            return False
        if self.tenant_name > other.tenant_name:
            return True
        if self.tenant_name < other.tenant_name:
            return False
        if self.context_name > other.context_name:
            return True
        if self.context_name < other.context_name:
            return False

        num_comps = min(len(self.sip), len(other.sip))
        for index in range(num_comps):
            if self.sip[index] > other.sip[index]:
                return True
            elif self._sip[index] < other.sip[index]:
                return False

        if len(self.sip) > len(other.sip):
            return True
        elif len(self.sip) < len(other.sip):
            return False

        num_comps = min(len(self.dip), len(other.dip))
        for index in range(num_comps):
            if self.dip[index] > other.dip[index]:
                return True
            elif self.dip[index] < other.dip[index]:
                return False

        if len(self.dip) > len(other.dip):
            return True
        elif len(self.dip) < len(other.dip):
            return False

        return False

    def __lt__(self, other):
        if self == other:
            return False
        if self > other:
            return False
        return True

    def __ge__(self, other):
        if self == other:
            return True
        if self > other:
            return True
        return False

    def __le__(self, other):
        if self == other:
            return True
        if self < other:
            return True
        return False


class SearchDb(object):
    """
    This class will build the database used by the search
    """

    def __init__(self, session=None):
        """
        Initially this will be built using just dictionaries.  In the future, it may make sense to
        create an SQL db to hold all of the info.
        :return:
        """
        self.epg_contract = {}
        self.contract_filter = {}
        self.session = session
        self.context_radix = {}
        self.tenants_by_name = {}
        self.context_by_name = {}

    def build(self, tenants=None):
        """
        This will read in all of the model and from there build-out the data base
        :param tenants:
        :return:
        """
        if tenants is None:
            tenants = Tenant.get_deep(self.session)

        for tenant in tenants:
            self.tenants_by_name[tenant.name] = tenant
            contexts = tenant.get_children(Context)
            for context in contexts:
                self.context_by_name[(tenant.name, context.name)] = context

            app_profiles = tenant.get_children(AppProfile)
            contracts = tenant.get_children(Contract)
            outside_l3s = tenant.get_children(OutsideL3)

            for app_profile in app_profiles:
                epgs = app_profile.get_children(EPG)
                self.build_ip_epg(epgs)
                self.build_epg_contract(epgs)

            for outside_l3 in outside_l3s:
                self.build_ip_epg_outside_l3(outside_l3)
                self.build_epg_contract_outside_l3(outside_l3)

            self.build_contract_filter(contracts)

    def build_ip_epg(self, epgs):

        """
        This will build the ip to epg mapping
        :param epgs:
        """
        for epg in epgs:
            eps = epg.get_children(Endpoint)
            bridge_domain = epg.get_bd()
            if bridge_domain is not None:
                context = bridge_domain.get_context()
            else:
                context = None
            app_profile = epg.get_parent()
            tenant = app_profile.get_parent()

            if (tenant, context) not in self.context_radix:
                self.context_radix[(tenant, context)] = radix.Radix()

            for ep in eps:
                ip = IpAddress(ep.ip)

                full_epg = (tenant, app_profile, epg)
                node = self.context_radix[(tenant, context)].add(str(ip))
                node.data['epg'] = full_epg
                node.data['location'] = 'internal'

    def build_ip_epg_outside_l3(self, outside_l3):
        """
        will build ip_epg db from OutsideL3
        :param outside_l3:
        :return:
        """

        tenant = outside_l3.get_parent()
        context = outside_l3.get_context()
        if (tenant, context) not in self.context_radix:
            self.context_radix[(tenant, context)] = radix.Radix()

        outside_epgs = outside_l3.get_children(OutsideEPG)
        for outside_epg in outside_epgs:
            subnets = outside_epg.get_children(Subnet)
            full_epg = (tenant, outside_l3, outside_epg)
            for subnet in subnets:
                ip = IpAddress(subnet.get_addr())
                node = self.context_radix[(tenant, context)].add(str(ip))
                node.data['epg'] = full_epg
                node.data['location'] = "external"

    def show_ip_epg(self):
        """
        Will simply print the ip_epg table

        :return:
        """
        for vrf in self.context_radix:
            (tenant, context) = vrf
            for node in self.context_radix[vrf]:
                context_str = "{0}/{1}".format(tenant, context)
                (epg_tenant, app_profile, epg) = node.data['epg']
                print "{4:10} {0:40} {1:30} {2}/{3}".format(context_str, node.prefix, app_profile, epg,
                                                            node.data['location'])

    def build_epg_contract(self, epgs):
        """
        This will build the epg to contract mapping

        :param epgs:
        :return:
        """
        for epg in epgs:
            consumed_contracts = epg.get_all_consumed()
            provided_contracts = epg.get_all_provided()
            app_profile = epg.get_parent()
            epg_tenant = app_profile.get_parent()
            full_epg = (epg_tenant, app_profile, epg)
            if full_epg not in self.epg_contract:
                self.epg_contract[full_epg] = []
            for contract in consumed_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'consume',
                                   'location': 'internal',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[full_epg].append(contract_record)

            for contract in provided_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'provide',
                                   'location': 'internal',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[full_epg].append(contract_record)

    def build_epg_contract_outside_l3(self, outside_l3):
        epg_tenant = outside_l3.get_parent()
        outside_epgs = outside_l3.get_children(OutsideEPG)
        for outside_epg in outside_epgs:
            consumed_contracts = outside_epg.get_all_consumed()
            provided_contracts = outside_epg.get_all_provided()
            full_epg = (epg_tenant, outside_l3, outside_epg)
            if full_epg not in self.epg_contract:
                self.epg_contract[full_epg] = []
            for contract in consumed_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'consume',
                                   'location': 'external',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[full_epg].append(contract_record)

            for contract in provided_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'provide',
                                   'location': 'external',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[full_epg].append(contract_record)

    def show_epg_contract(self):
        """
        Will simply print the epg_contract table

        :return:
        """
        for entry in self.epg_contract:
            (epg_tenant, app_profile, epg) = entry
            for contract_entry in self.epg_contract[entry]:
                (contract_tenant, contract) = contract_entry['contract']
                pro_con = contract_entry['pro_con']
                int_ext = contract_entry['location']

                print "{6:9} {0:20} {1:20} {2:20} {3:20} {4:20} {5:20}" \
                    .format(epg_tenant, app_profile, epg, pro_con, contract_tenant, contract, int_ext)

    def build_contract_filter(self, contracts):
        """
        This will build the contract to filter mapping
        :param contracts:
        :return:
        """
        for contract in contracts:
            tenant = contract.get_parent()
            subjects = contract.get_children(ContractSubject)
            if (tenant, contract) not in self.contract_filter:
                self.contract_filter[(tenant, contract)] = []
            for subject in subjects:
                filters = subject.get_filters()
                for aci_filter in filters:
                    filter_entries = aci_filter.get_children(FilterEntry)

                    for filter_entry in filter_entries:
                        self.contract_filter[(tenant, contract)].append(filter_entry)

    def show_contract_filter(self):
        for (tenant, contract) in self.contract_filter:
            filters = self.contract_filter[(tenant, contract)]
            for filter_entry in filters:
                print "{0:20} {1:20} {2:20}".format(tenant, contract, filter_entry)

    def search(self, flow_spec):
        """
        Given a flow_spec, this will return a set of flow specs from the db that match
        Match is defined as having a non-empty intersection.
        The returned flow_specs will all be within the intersection.

        The steps are:
        find matching IP addresses for the source
        find corresponding EPGs
        find corresponding consumed contracts

        find matching IP addreses for the destination
        find corresponding EPGs
        find corrresponding provided contracts

        find intersection of contracts
        build flow specs.

        :param flow_spec:
        :return:
        """
        result = []
        # first convert name of tenant and context to tenant and context objects
        consumed_contracts = self.find_contracts(flow_spec.get_source(), 'consume')
        provided_contracts = self.find_contracts(flow_spec.get_dest(), 'provide')
        connections = []
        for c_contract in consumed_contracts:
            for p_contract in provided_contracts:
                if c_contract['contract'] == p_contract['contract']:
                    connections.append({'source': c_contract['prefix'],
                                        'source_epg': c_contract['epg'],
                                        'dest': p_contract['prefix'],
                                        'dest_epg': p_contract['epg'],
                                        'contract': c_contract['contract']})

        for connection in connections:
            filters = self.contract_filter[connection['contract']]
            matching_filters = []
            for aci_filter in filters:
                overlap_filter = flow_spec.protocol_filter[0].overlap(ProtocolFilter(aci_filter))
                if overlap_filter is not None:
                    matching_filters.append(overlap_filter)

            if len(matching_filters) > 0:
                result.append(self._build_result_flow_spec(connection, matching_filters))

        # for flow_spec in result:
        #     print flow_spec

        return result

    @staticmethod
    def _build_result_flow_spec(connection, matching_filters):

        result = FlowSpec()
        result.tenant_name = connection['source_epg'][0].name
        source_epg = connection['source_epg']
        if isinstance(source_epg[2], OutsideEPG):
            result.context_name = source_epg[1].get_context().name
        else:
            result.context_name = source_epg[2].get_bd().get_context().name
        result.sip = connection['source']
        result.dip = connection['dest']
        result.protocol_filter = matching_filters
        return result

    def find_contracts(self, subflow_spec, pro_con):
        """
        This will find all the contracts that are either provided or consumed by the
        subflow_spec
        :param subflow_spec:
        :param pro_con:
        :return:
        """
        tenants = []
        tenant_search = '^' + subflow_spec.tenant_name.replace('*', '.*') + '$'
        for tenant_name in self.tenants_by_name:
            match_result = re.match(tenant_search, tenant_name)
            if match_result is not None:
                tenants.append(self.tenants_by_name[tenant_name])

        contexts = []
        context_search = '^' + subflow_spec.context_name.replace('*', '.*') + '$'
        for tenant in tenants:
            for (tenant_name, context_name) in self.context_by_name:
                match_result = re.match(context_search, context_name)
                if match_result is not None and tenant_name == tenant.name:
                    contexts.append(self.context_by_name[(tenant_name, context_name)])

        # tenant = self.tenants_by_name[subflow_spec.tenant_name]
        # context = self.context_by_name[(subflow_spec.tenant_name, subflow_spec.context_name)]

        vrfs = []
        for context in contexts:
            vrfs.append((context.get_parent(), context))
        # vrf = (tenant, context)
        epgs_prefix = {}
        nodes = []

        for vrf in vrfs:
            if vrf in self.context_radix:
                # cover both the case where what we are looking for is covered by a prefix
                # and where it covers more than one address.
                for ip in subflow_spec.ip:

                    node = self.context_radix[vrf].search_best(str(ip.prefix))
                    if node is not None:
                        if node not in nodes:
                            nodes.append(node)
                    temp_nodes = self.context_radix[vrf].search_covered(str(ip.prefix))
                    for node in temp_nodes:
                        if node not in nodes:
                            nodes.append(node)

        # now have all the nodes
        if nodes is not None:
            for node in nodes:
                if node.data['epg'] not in epgs_prefix:
                    epgs_prefix[node.data['epg']] = []

                for ip in subflow_spec.ip:
                    ovlp = ip.overlap(IpAddress(node.prefix))
                    if ovlp is not None:
                        if ovlp not in epgs_prefix[node.data['epg']]:
                            epgs_prefix[node.data['epg']].append(ovlp)

        result = []
        for epg in epgs_prefix:
            if epg in self.epg_contract:
                for entry in self.epg_contract[epg]:
                    if entry['pro_con'] == pro_con:
                        result.append({'contract': entry['contract'],
                                       'prefix': IpAddress.simplify(epgs_prefix[epg]),
                                       'epg': epg})

        return result


def parse_port_range(text):
    """
    This will parse a layer 4 port range or single value
    and return a from and to value
    :param text:
    :return:
    """
    match_result = re.match('(\d+)\W*-\W*(\d+)', text)
    if match_result is not None:
        return match_result.group(1), match_result.group(2)
    elif text == 'any':
        return 'any', 'any'
    else:
        match_result = re.match('^(\d+)$', text)
        if match_result is None:
            raise ValueError('Value error in port range.  Must be either single number or "#-#".  Value given:' + text)
        else:
            return text, text


def build_flow_spec_from_args(args):
    """
    Will build a flow spec from the command line arguments
    :param args:
    :return:
    """
    flow_spec = FlowSpec()
    flow_spec.tenant_name = args.tenant
    flow_spec.context_name = args.context
    flow_spec.sip = [IpAddress(args.sip)]
    flow_spec.dip = [IpAddress(args.dip)]
    filt = ProtocolFilter()
    flow_spec.protocol_filter.append(filt)
    filt.applyToFrag = args.applyToFrag
    filt.arpOpc = args.arpOpc
    filt.etherT = args.etherT
    filt.prot = args.prot
    filt.tcpRules = args.tcpRules
    (filt.dFromPort, filt.dToPort) = parse_port_range(args.dport)
    (filt.sFromPort, filt.sToPort) = parse_port_range(args.sport)
    return flow_spec


def main():
    """
    Main execution path when run from the command line
    """
    # Get all the arguments
    description = 'Connection Search tool for APIC.'
    creds = Credentials('apic', description)

    creds.add_argument('-tenant', type=str, default='any', help='Tenant name (wildcards, "*", accepted), default "*"')
    creds.add_argument('-context', type=str, default='any', help='Tenant name (wildcards, "*", accepted), default "*"')
    creds.add_argument('-sip', type=str, default='0/0', help='Source IP or subnet - e.g. 1.2.3.4/24, default: "0/0"')
    creds.add_argument('-dip', type=str, default='0/0',
                       help='Destination IP or subnet - e.g. 1.2.3.4/24, default: "0/0"')
    creds.add_argument('-dport', type=str, default='any',
                       help='Destination L4 Port value or range, e.g. 20-25 or 80. Default: "any"')
    creds.add_argument('-sport', type=str, default='any',
                       help='Source L4 Port value or range, e.g. 20-25 or 80. Default: "any"')
    creds.add_argument('-etherT', type=str, default='any', help='EtherType, e.g. "ip", "arp", "icmp". Default: "any"')
    creds.add_argument('-prot', type=str, default='any', help='Protocol, e.g. "tcp", "udp". Default: "any"')
    creds.add_argument('-arpOpc', type=str, default='any', help='ARP Opcode, e.g. "req", "ack". Default: "any"')
    creds.add_argument('-applyToFrag', type=str, default='any',
                       help='Apply to fragment, e.g. "yes", "no". Default: "any"')
    creds.add_argument('-tcpRules', type=str, default='any', help='TCP rules, e.g. "syn", "fin". Default: "any"')

    args = creds.get()

    flow_spec = build_flow_spec_from_args(args)
    # todo: verify that a dash can be used in port range.
    
    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print '%% Could not login to APIC'
        sys.exit(0)

    sdb = SearchDb(session)
    sdb.build()
    results = sorted(sdb.search(flow_spec))
    for result in results:
        print result


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
