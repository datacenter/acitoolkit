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
import itertools
import radix
import re
from acitoolkit import Endpoint, Tenant, AppProfile, Contract, EPG, OutsideL3, OutsideEPG, ContractSubject, \
    FilterEntry, Context, OutsideNetwork, Fabric
from acitoolkit.aciphysobject import Session
from acitoolkit.acitoolkit import BaseTerminal, InputTerminal, AnyEPG
from acitoolkit.acitoolkitlib import Credentials

if radix.__version__ < '0.9.5':
    raise AssertionError("!!! Please upgrade your py-radix to a version later than 0.9.4.  "
                         "You are running {0}!!!".format(radix.__version__))


class LoginError(Exception):
    """
    Exception for login errors.
    """
    pass


def IpAddress(address):
    """Take an IP string/int and return an object of the correct type.
    :param address:

    """
    try:
        return Ipv4Address(address)
    except ValueError:
        pass

    try:
        return Ipv6Address(address)
    except:
        raise ValueError('{0} does not appear to be an IPv4 or IPv6 address'.format(address))


class Ipv4Address(object):
    """
    This class holds an IP address and allows various functions to be performed on it
    """

    def __init__(self, ip):

        self._addr = None
        if isinstance(ip, int):
            self._prefixlen = 32
            self.addr = ip

        elif isinstance(ip, str):
            if ip == '':
                self._prefixlen = 0
                self.addr = 0
            else:
                sections = ip.split('/')
                if len(sections) == 1:
                    self._prefixlen = 32
                else:
                    self._prefixlen = int(sections[1])

                self.addr = sections[0]

    @classmethod
    def valid_ip(cls, address):
        try:
            host_bytes = address.split('.')
            if host_bytes[-1] == '':
                host_bytes.pop()
            valid = [int(b) for b in host_bytes]
            valid = [b for b in valid if 0 <= b <= 255]
            return len(host_bytes) == len(valid)
        except ValueError:
            return False

    @property
    def addr(self):
        return self.n2s(self._addr)

    @addr.setter
    def addr(self, value):
        if isinstance(value, str):
            self._addr = Ipv4Address.parse_text(value)
        else:
            assert isinstance(value, int)
            self._addr = value

    @classmethod
    def parse_text(cls, input_ip):
        if cls.valid_ip(input_ip):
            fields = input_ip.split('.')
            if fields[-1] == '':
                fields.pop()
            result = int(fields[0]) << 8
            if len(fields) > 1:
                result += int(fields[1])
            result <<= 8

            if len(fields) > 2:
                result += int(fields[2])

            result <<= 8

            if len(fields) > 3:
                result += int(fields[3])
        else:
            raise ValueError

        return result

    @property
    def prefix(self):
        return self.n2s(self._addr & self.mask_num) + '/' + str(self.prefixlen)

    @property
    def prefix_num(self):
        """
        Will return numeric version of the prefix
        :return:
        """
        return self._addr & self.mask_num

    @property
    def prefixlen(self):
        return self._prefixlen

    @property
    def mask(self):
        return self.n2s(self.mask_num)

    @property
    def mask_num(self):
        return ~(0xFFFFFFFF >> self.prefixlen)

    def overlap(self, other):
        """
        This will return an IpAddress that is the overlap of self and other
        :param other:
        :return:
        """

        assert isinstance(other, Ipv4Address)
        max_addr = min(self.max_address(), other.max_address())
        min_addr = max(self.min_address(), other.min_address())

        if min_addr <= max_addr:
            if self.prefixlen > other.prefixlen:
                return self
            else:
                return other
        else:
            return None

    @classmethod
    def simplify(cls, ip_list):
        """
        Will combine and then supernet prefixes in list to
        come up with the most simple list
        :param ip_list:
        :return:
        """
        return cls.supernet(cls.combine(ip_list))

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
                        new_ip = Ipv4Address(ip1.prefix)
                        new_ip._prefixlen -= 1
                        new_list.remove(ip1)
                        new_list.remove(ip2)
                        new_list.append(new_ip)

        if len(new_list) == len(ip_list):
            return new_list
        else:
            return Ipv4Address.supernet(new_list)

    @staticmethod
    def combine(ip_list):
        """
        Will go through list and combine any prefixes that can be combined
        and return a new list with result.
        :param ip_list:
        :return:
        """
        list1 = list(ip_list)
        if len(ip_list) > 1:
            list2 = copy(list1)
            done = False
            while not done:
                done = True
                for a, b in itertools.combinations(list1, 2):
                    if Ipv4Address.encompass(a, b):
                        try:
                            list2.remove(b)
                        except ValueError:
                            pass
                        done = False
                    elif Ipv4Address.encompass(b, a):
                        try:
                            list2.remove(a)
                        except ValueError:
                            pass
                        done = False
                list1 = copy(list2)
        return list1

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
        return Ipv4Address(self._addr & self.mask_num)

    def max_address(self):
        """
        returns the maximum address in the subnet
        :return:
        """

        return Ipv4Address((self._addr & self.mask_num) | ~self.mask_num)

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
        return self.prefix_num == other.prefix_num

    def __repr__(self):
        return '{0}/{1}'.format(self.addr, self.prefixlen)

    def __eq__(self, other):

        if isinstance(other, str):
            if self == Ipv4Address(other):
                return True
            else:
                return False
        else:
            if not isinstance(self, Ipv4Address) or not isinstance(other, Ipv4Address):
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


class Ipv6Address(object):
    """
    This class holds an IP address and allows various functions to be performed on it
    """

    def __init__(self, ip):

        self._addr = None
        if isinstance(ip, str):
            if ip == '':
                self._prefixlen = 0
                self.addr = [0, 0, 0, 0, 0, 0, 0, 0]
            else:
                sections = ip.split('/')
                if len(sections) == 1:
                    self._prefixlen = 128
                else:
                    self._prefixlen = int(sections[1])

                self.addr = sections[0]
        elif isinstance(ip, list):
            self._prefixlen = 128
            self.addr = ip
        else:
            assert TypeError("expect either string or list of 8 integers")

    @property
    def addr(self):
        return self._addr

    @addr.setter
    def addr(self, value):
        if isinstance(value, list):
            self._addr = value

        elif isinstance(value, str):
            self._addr = Ipv6Address.parse_text(value)

    @staticmethod
    def parse_text(input_ip):
        assert ':' in input_ip

        addr = [0, 0, 0, 0, 0, 0, 0, 0]
        fields = input_ip.split(':')
        index = 0
        for index in range(len(fields)):
            if fields[index] == '':
                break
            else:
                addr[index] = int(fields[index], 16)

        if index < 8:
            byte_position = 7
            for index in reversed(range(len(fields))):
                if fields[index] == '':
                    break
                addr[byte_position] = int(fields[index], 16)
                byte_position -= 1

        return addr

    @property
    def prefix(self):
        return self.n2s(Ipv6Address.apply_mask(self, self.mask()).addr) + '/' + str(self.prefixlen)

    @property
    def prefix_num(self):
        """
        Will return numeric version of the prefix
        :return:
        """
        return Ipv6Address.apply_mask(self, self.mask()).addr

    @property
    def prefixlen(self):
        return self._prefixlen

    @prefixlen.setter
    def prefixlen(self, value):
        self._prefixlen = value

    def mask(self):
        result = [0, 0, 0, 0, 0, 0, 0, 0]
        remaining_prefixlen = self.prefixlen
        index = 0
        while remaining_prefixlen > 16:
            result[index] = 0xFFFF
            remaining_prefixlen -= 16
            index += 1

        result[index] = ((0xFFFF << 16 - remaining_prefixlen) & 0xFFFF)

        return result

    @staticmethod
    def apply_mask(ipv6, mask):
        if isinstance(ipv6, Ipv6Address):
            ip = ipv6
        else:
            ip = Ipv6Address(ipv6)
        new_ip = []
        for index in range(8):
            new_ip.append(ip.addr[index] & mask[index])
        return Ipv6Address(new_ip)

    def overlap(self, other):
        """
        This will return an Ipv6Address that is the overlap of self and other
        :param other:
        :return:
        """

        assert isinstance(other, Ipv6Address)
        max_addr = min(self.max_address(), other.max_address())
        min_addr = max(self.min_address(), other.min_address())

        if min_addr <= max_addr:
            if self.prefixlen > other.prefixlen:
                return self
            else:
                return other
        else:
            return None

    @classmethod
    def simplify(cls, ip_list):
        """
        Will combine and then supernet prefixes in list to
        come up with the most simple list
        :param ip_list:
        :return:
        """
        return cls.supernet(cls.combine(ip_list))

    @classmethod
    def supernet(cls, ip_list):
        """
        Will combine subnets into larger subnets
        :param ip_list:
        :return:
        """
        if len(ip_list) == 1:
            return list(ip_list)

        if isinstance(ip_list, list):
            list1 = set(ip_list)
        else:
            list1 = copy(ip_list)

        list2 = copy(list1)
        done = True
        for a, b in itertools.combinations(list1, 2):
            if a == b:
                if b in list2:
                    list2.remove(b)
            elif a.prefixlen == b.prefixlen:
                p1 = cls(a.prefix_num)
                p2 = cls(b.prefix_num)
                p1.prefixlen = a.prefixlen - 1
                p2.prefixlen = b.prefixlen - 1
                if p1.prefix == p2.prefix:
                    new_ip = cls(p1.prefix)
                    if a in list2:
                        list2.remove(a)
                    if b in list2:
                        list2.remove(b)
                    list2.add(new_ip)
                    done = False
        if done:
            return list(list2)
        else:
            return cls.supernet(list2)

    @classmethod
    def combine(cls, ip_list):
        """
        Will go through list and combine any prefixes that can be combined
        and return a new list with result.
        :param ip_list:
        :return:
        """
        list1 = list(ip_list)
        if len(ip_list) > 1:
            list2 = copy(list1)
            done = False
            while not done:
                done = True
                for a, b in itertools.combinations(list1, 2):
                    if Ipv4Address.encompass(a, b):
                        try:
                            list2.remove(b)
                        except ValueError:
                            pass
                        done = False
                    elif Ipv4Address.encompass(b, a):
                        try:
                            list2.remove(a)
                        except ValueError:
                            pass
                        done = False
                list1 = copy(list2)

        return list1

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
        return Ipv6Address(self.prefix_num)

    def max_address(self):
        """
        returns the maximum address in the subnet
        :return:
        """
        new_ip = []
        mask = self.mask()
        addr = self.addr
        for index in range(8):
            new_ip.append(addr[index] | (~mask[index] & 0xFFFF))
        return Ipv6Address(new_ip)

    @staticmethod
    def n2s(address):
        """
        will return a string in the x.y.w.z format given a number
        :param address:
        :return:
        """
        result = '{0:x}:{1:x}:{2:x}:{3:x}:{4:x}:{5:x}:{6:x}:{7:x}'.format(*address)

        pat = re.compile('^0:0:0:0:0:0:0:0$')
        if re.search(pat, result):
            return '::'
        pat = re.compile('(^0:0:0:0:0:0:0:|:0:0:0:0:0:0:0$)')
        if re.search(pat, result):
            return re.sub(pat, '::', result, 1)
        pat = re.compile('(^0:0:0:0:0:0:|:0:0:0:0:0:0:|:0:0:0:0:0:0$)')
        if re.search(pat, result):
            return re.sub(pat, '::', result, 1)
        pat = re.compile('(^0:0:0:0:0:|:0:0:0:0:0:|:0:0:0:0:0$)')
        if re.search(pat, result):
            return re.sub(pat, '::', result, 1)
        pat = re.compile('(^0:0:0:0:|:0:0:0:0:|:0:0:0:0$)')
        if re.search(pat, result):
            return re.sub(pat, '::', result, 1)
        pat = re.compile('(^0:0:0:|:0:0:0:|:0:0:0$)')
        if re.search(pat, result):
            return re.sub(pat, '::', result, 1)
        pat = re.compile('(^0:0:|:0:0:|:0:0$)')
        if re.search(pat, result):
            return re.sub(pat, '::', result, 1)
        return result

    def equiv(self, other):
        """
        Checks to see if self is equivalent to other
        This is just like ==, except it will check the prefixes rather than the absolute address
        values.
        :param other:
        :return:
        """
        return self.prefix_num == other.prefix_num

    def __repr__(self):
        return self.n2s(self.addr) + '/' + str(self.prefixlen)

    def __eq__(self, other):

        if isinstance(other, str):
            if self == Ipv6Address(other):
                return True
            else:
                return False
        else:
            if not isinstance(self, Ipv6Address) or not isinstance(other, Ipv6Address):
                return False

            for index in range(8):
                if self.addr[index] != other.addr[index]:
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
            a1 = self.min_address().addr
            a2 = other.min_address().addr
            for index in range(8):
                if a1[index] > a2[index]:
                    return True
                elif a1[index] < a2[index]:
                    return False
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
        self.direction = 'both'
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
            try:
                self.direction = aci_filter.direction
            except AttributeError:
                pass

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
            if self.etherT == 'any':
                self.etherT = 'arp'

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
    def dPort(self):
        return '{0}-{1}'.format(self.dFromPort, self.dToPort)

    @dPort.setter
    def dPort(self, value):
        """
        This is a way to set both dFromPort and dToPort in a single shot
        :param value:
        :return:
        """
        if isinstance(value, int):
            self.dFromPort = value
            self.dToPort = value
        else:
            fields = re.split('[\s-]+', value)
            if len(fields) > 1:
                self.dFromPort = fields[0]
                self.dToPort = fields[1]
            elif len(fields) == 1:
                self.dFromPort = fields[0]
                self.dToPort = fields[0]

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
    def sPort(self):
        return '{0}-{1}'.format(self.sFromPort, self.sToPort)

    @sPort.setter
    def sPort(self, value):
        """
        This is a way to set both sFromPort and sToPort in a single shot
        :param value:
        :return:
        """
        if isinstance(value, int):
            self.sFromPort = value
            self.sToPort = value
        else:
            fields = re.split('[\s-]+', value)
            if len(fields) > 1:
                self.sFromPort = fields[0]
                self.sToPort = fields[1]
            elif len(fields) == 1:
                self.sFromPort = fields[0]
                self.sToPort = fields[0]

    @property
    def etherT(self):
        return self._etherT

    @etherT.setter
    def etherT(self, value):
        if value == 'unspecified' or value is None:
            self._etherT = 'any'
        else:
            self._etherT = str(value)

    @property
    def prot(self):
        return self._prot

    @prot.setter
    def prot(self, value):
        if value == 'unspecified' or value is None:
            self._prot = 'any'
        else:

            self._prot = str(value)

            if self.etherT == 'any':
                if value in ['icmp', 'igmp', 'tcp', 'egp', 'igp', 'udp', 'icmpv6', 'eigrp', 'ospfigp', 'pim', 'l2tp']:
                    self.etherT = 'ip'

    @property
    def tcpRules(self):
        return self._tcpRules

    @tcpRules.setter
    def tcpRules(self, value):
        if value == 'unspecified':
            self._tcpRules = 'any'
        else:
            self._tcpRules = value
            if self.prot == 'any' and self.tcpRules != 'any':
                self.prot = 'tcp'

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

        if self.direction is not 'both' and other.direction is not 'both':
            if self.tcpRules != other.tcpRules:
                return None
        result.direction = other.direction if self.direction is 'both' else self.direction

        return result

    def __str__(self):
        dport = '{0}-{1}'.format(self.dFromPort, self.dToPort)
        sport = '{0}-{1}'.format(self.sFromPort, self.sToPort)
        return '{0:4} {1:4} {2:11} {3:11} {4:4}'.format(self.etherT,
                                                        self.arpOpc if self.etherT == 'arp' else self.prot,
                                                        dport,
                                                        sport, self.direction)

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
        if self.prot != other.prot:
            return False
        if not self._port_equal(other):
            return False
        if self.tcpRules != other.tcpRules:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        if self.dFromPort > other.dFromPort:
            return True
        if self.sFromPort > other.sFromPort:
            return True
        if self.dToPort > other.dToPort:
            return True
        if self.sToPort > other.sToPort:
            return True
        if self.prot > other.prot:
            return True
        if self.etherT > other.etherT:
            return True
        if self.arpOpc > other.arpOpc:
            return True
        if self.tcpRules > other.tcpRules:
            return True
        if self.applyToFrag > other.applyToFrag:
            return True
        return False

    def __ge__(self, other):
        return self > other or self == other

    def __lt__(self, other):
        return not self >= other

    def __le__(self, other):
        return self < other or self == other


class SubFlowSpec(object):
    """
    defines one side of a flow without the port numbers, i.e. either source or destination
    """

    def __init__(self, tenant, context, ip, contract, contract_tenant):
        self.tenant_name = tenant
        self.context_name = context
        self.ip = ip
        self.contract = contract
        self.contract_tenant = contract_tenant


class FlowSpec(object):
    """
    This is a structure that holds a flow spec

    """

    def __init__(self):
        self._sip = [IpAddress('0/0')]
        self._dip = [IpAddress('0/0')]
        self.tenant_name = '*'
        self.context_name = '*'
        self.protocol_filter = []
        self.source_epg = None
        self.src_epg_type = None
        self.dest_epg = None
        self.dst_epg_type = None
        self.contract = None
        self.contract_tenant = None
        self.src_tenant_name = None
        self.src_app_profile = None
        self.src_app_profile_type = None
        self.dst_tenant_name = None
        self.dst_app_profile = None
        self.dst_app_profile_type = None

    def get_source(self):
        return SubFlowSpec(self.tenant_name, self.context_name, self.sip, self.contract, self.contract_tenant)

    def get_dest(self):
        return SubFlowSpec(self.tenant_name, self.context_name, self.dip, self.contract, self.contract_tenant)

    @property
    def sip(self):
        return self._sip

    @sip.setter
    def sip(self, value):
        if isinstance(value, list):
            self._sip = value
        elif isinstance(value, set):
            self._sip = list(value)
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
        elif isinstance(value, set):
            self._dip = list(value)
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

    def __ne__(self, other):
        return not self == other

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

        num_comps = min(len(self.dip), len(other.dip))
        for index in range(num_comps):
            if sorted(self.dip)[index] > sorted(other.dip)[index]:
                return True
            elif sorted(self.dip)[index] < sorted(other.dip)[index]:
                return False

        if len(self.dip) > len(other.dip):
            return True
        elif len(self.dip) < len(other.dip):
            return False

        num_comps = min(len(self.sip), len(other.sip))
        for index in range(num_comps):
            if sorted(self.sip)[index] > sorted(other.sip)[index]:
                return True
            elif sorted(self.sip)[index] < sorted(other.sip)[index]:
                return False

        if len(self.sip) > len(other.sip):
            return True
        elif len(self.sip) < len(other.sip):
            return False

        num_comps = min(len(self.protocol_filter), len(other.protocol_filter))
        for index in range(num_comps):
            if self.protocol_filter[index] > other.protocol_filter[index]:
                return True
            elif self.protocol_filter[index] < other.protocol_filter[index]:
                return False

        if len(self.protocol_filter) > len(other.protocol_filter):
            return True
        elif len(self.protocol_filter) < len(other.protocol_filter):
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
        self._implied_contract_guid = 0
        self.epg_contract = {}
        self.contract_filter = {}
        self.session = session
        self.context_radix = {}
        self.tenants_by_name = {}
        self.context_by_name = {}
        self.initialized = False
        self.valid_tenants = None

    def build(self, tenants=None):
        """
        This will read in all of the model and from there build-out the data base
        :param tenants:
        :return:
        """
        if tenants is None:
            fabric = Fabric()
            # tenants = Tenant.get_deep(self.session, parent=fabric, names=('mgmt', 'common'))
            tenants = Tenant.get_deep(self.session, parent=fabric)

        for tenant in tenants:
            self.tenants_by_name[tenant.name] = tenant
            contexts = tenant.get_children(Context)
            for context in contexts:
                self.context_by_name[(tenant.name, context.name)] = context
                any_epgs = context.get_children(AnyEPG)
                self.build_epg_contract(any_epgs)

            app_profiles = tenant.get_children(AppProfile)
            outside_l3s = tenant.get_children(OutsideL3)

            for app_profile in app_profiles:
                epgs = app_profile.get_children(EPG)
                self.build_ip_epg(epgs)
                self.build_epg_contract(epgs)

            for outside_l3 in outside_l3s:
                self.build_ip_epg_outside_l3(outside_l3)
                self.build_epg_contract_outside_l3(outside_l3)

            contracts = tenant.get_children(Contract)

            self.build_contract_filter(contracts)
        self.initialized = True

    def build_ip_epg(self, epgs):

        """
        This will build the ip to epg mapping
        :param epgs:
        """
        for epg in epgs:
            eps = epg.get_children(Endpoint)

            ep_ips = [IpAddress(ep.ip) for ep in eps]
            bridge_domain = epg.get_bd()
            any_epg = []
            if bridge_domain is not None:
                context = bridge_domain.get_context()
                if context is not None:
                    any_epg = context.get_children(AnyEPG)
            else:
                context = None

            if context not in self.context_radix:
                self.context_radix[context] = radix.Radix()

            for ip in ep_ips:
                node = self.context_radix[context].add(str(ip))
                node.data['epg'] = epg
                node.data['any_epg'] = None
                if len(any_epg) > 0:
                    if any_epg[0]._relations is not None:
                        node.data['any_epg'] = any_epg[0]

                node.data['location'] = 'internal'

    def build_ip_epg_outside_l3(self, outside_l3):
        """
        will build ip_epg db from OutsideL3
        :param outside_l3:
        :return:
        """

        context = outside_l3.get_context()
        if context not in self.context_radix:
            self.context_radix[context] = radix.Radix()

        outside_epgs = outside_l3.get_children(OutsideEPG)
        for outside_epg in outside_epgs:
            subnets = outside_epg.get_children(OutsideNetwork)
            for subnet in subnets:
                ip = IpAddress(subnet.get_addr())
                node = self.context_radix[context].add(str(ip))
                node.data['epg'] = outside_epg
                node.data['location'] = "external"

    def build_epg_contract(self, epgs):
        """
        This will build the epg to contract mapping

        :param epgs:
        :return:
        """
        for epg in epgs:
            consumed_contracts = set(epg.get_all_consumed())
            consumed_cif = epg.get_all_consumed_cif()
            for contract_if in consumed_cif:
                import_contracts = contract_if.get_import_contract()

                if import_contracts is not None:
                    consumed_contracts = consumed_contracts | set([import_contracts])
            provided_contracts = set(epg.get_all_provided())

            if isinstance(epg, EPG):
                implied_contract = self._get_implied_contract(epg.get_parent().get_parent())
                consumed_contracts.add(implied_contract)
                provided_contracts.add(implied_contract)
            if epg not in self.epg_contract:
                self.epg_contract[epg] = []
            for contract in consumed_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'consume',
                                   'location': 'internal',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[epg].append(contract_record)

            for contract in provided_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'provide',
                                   'location': 'internal',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[epg].append(contract_record)

    def _get_implied_contract(self, tenant):
        """
        returns an implied contract that represents a contract
        for traffic within the EPG.  It is an allow all contract, but
        has a unique name.
        :return:
        """
        name = 'implied_contract_' + str(self._implied_contract_guid)
        self._implied_contract_guid += 1
        implied_contract = Contract(name, tenant)
        FilterEntry('entry1',
                    applyToFrag='no',
                    arpOpc='unspecified',
                    dFromPort='unspecified',
                    dToPort='unspecified',
                    etherT='unspecified',
                    prot='unspecified',
                    sFromPort='unspecified',
                    sToPort='unspecified',
                    tcpRules='unspecified',
                    parent=implied_contract)
        implied_contract.implied = True
        return implied_contract

    def build_epg_contract_outside_l3(self, outside_l3):
        outside_epgs = outside_l3.get_children(OutsideEPG)
        for outside_epg in outside_epgs:
            consumed_contracts = outside_epg.get_all_consumed()
            provided_contracts = outside_epg.get_all_provided()
            if outside_epg not in self.epg_contract:
                self.epg_contract[outside_epg] = []
            for contract in consumed_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'consume',
                                   'location': 'external',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[outside_epg].append(contract_record)

            for contract in provided_contracts:
                contract_tenant = contract.get_parent()
                contract_record = {'pro_con': 'provide',
                                   'location': 'external',
                                   'contract': (contract_tenant, contract)}
                self.epg_contract[outside_epg].append(contract_record)

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
                self.contract_filter[(tenant, contract)] = set()
            for subject in subjects:
                filters = subject.get_filters()
                for aci_filter in filters:
                    filter_entries = aci_filter.get_children(FilterEntry)

                    for filter_entry in filter_entries:
                        filter_entry.direction = 'both'
                        self.contract_filter[(tenant, contract)].add(filter_entry)
                terminals = subject.get_children(BaseTerminal)
                for terminal in terminals:
                    if isinstance(terminal, InputTerminal):
                        filter_direction = 'in'
                    else:
                        filter_direction = 'out'
                    filters = terminal.get_filters()
                    for aci_filter in filters:
                        filter_entries = aci_filter.get_children(FilterEntry)
                        for filter_entry in filter_entries:
                            filter_entry.direction = filter_direction
                            self.contract_filter[(tenant, contract)].add(filter_entry)

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

        find matching IP addresses for the destination
        find corresponding EPGs
        find corresponding provided contracts

        find intersection of contracts
        build flow specs.

        :param flow_spec:
        :return:
        """
        # todo: add multiple flow_specs
        # t1 = datetime.datetime.now()
        result = []
        # first convert name of tenant and context to tenant and context objects
        consumed_contracts = self.find_contracts(flow_spec.get_source(), 'consume')
        provided_contracts = self.find_contracts(flow_spec.get_dest(), 'provide')
        connections = []
        for c_contract in consumed_contracts:
            for p_contract in provided_contracts:
                if c_contract['contract'] == p_contract['contract']:
                    if c_contract['epg'] == p_contract['epg']:
                        try:
                            if c_contract['contract'][1].implied:
                                connections.append({'source': c_contract['prefix'],
                                                    'source_epg': c_contract['epg'],
                                                    'source_tenant': c_contract['tenant'],
                                                    'dest': p_contract['prefix'],
                                                    'dest_epg': p_contract['epg'],
                                                    'dest_tenant': p_contract['tenant'],
                                                    'contract': c_contract['contract']})
                        except AttributeError:
                            pass
                    else:
                        connections.append({'source': c_contract['prefix'],
                                            'source_epg': c_contract['epg'],
                                            'source_tenant': c_contract['tenant'],
                                            'dest': p_contract['prefix'],
                                            'dest_epg': p_contract['epg'],
                                            'dest_tenant': p_contract['tenant'],
                                            'contract': c_contract['contract']})

        # t2 = datetime.datetime.now()
        # print 'connections done', t2-t1
        # t1=t2
        for connection in connections:
            if connection['source_tenant'] in self.valid_tenants or connection['dest_tenant'] in self.valid_tenants:
                filters = self.contract_filter[connection['contract']]
                matching_filters = []
                for aci_filter in filters:
                    for fs_p_filter in flow_spec.protocol_filter:
                        aci_protocol_filter = ProtocolFilter(aci_filter)
                        overlap_filter = fs_p_filter.overlap(aci_protocol_filter)
                        if overlap_filter is not None:
                            matching_filters.append(aci_protocol_filter)

                if len(matching_filters) > 0:
                    result.append(self._build_result_flow_spec(connection, matching_filters))
        # t2 = datetime.datetime.now()
        # print 'search result done', t2-t1
        # t1=t2

        # for flow_spec in result:
        #   print flow_spec

        return result

    @staticmethod
    def _build_result_flow_spec(connection, matching_filters):

        result = FlowSpec()
        result.tenant_name = connection['source_epg'].get_parent().get_parent().name
        source_epg = connection['source_epg']
        if isinstance(source_epg, OutsideEPG):
            result.context_name = source_epg.get_parent().get_context().name
        elif isinstance(source_epg, AnyEPG):
            result.context_name = source_epg.get_parent().name
        else:
            result.context_name = source_epg.get_bd().get_context().name

        result.sip = next(iter(connection['source'])).simplify(connection['source'])
        result.dip = next(iter(connection['dest'])).simplify(connection['dest'])
        result.protocol_filter = matching_filters
        epg = connection['source_epg']
        result.src_tenant_name = epg.get_parent().get_parent().name
        result.src_app_profile = epg.get_parent().name
        if isinstance(epg.get_parent(), AppProfile):
            result.src_app_profile_type = "AppProfile"
        else:
            result.src_app_profile_type = "Context"

        result.source_epg = epg.name
        if isinstance(epg, EPG):
            result.src_epg_type = "EPG"
        else:
            result.src_epg_type = "L3Out"
        epg = connection['dest_epg']
        result.dst_tenant_name = epg.get_parent().get_parent().name
        result.dst_app_profile = epg.get_parent().name
        if isinstance(epg.get_parent(), AppProfile):
            result.dst_app_profile_type = "AppProfile"
        else:
            result.dst_app_profile_type = "Context"
        result.dest_epg = epg.name
        if isinstance(epg, EPG):
            result.dst_epg_type = "EPG"
        else:
            result.dst_epg_type = "L3Out"
        result.contract_tenant = connection['contract'][1].get_parent().name
        result.contract = connection['contract'][1].name

        return result

    def find_contracts(self, subflow_spec, pro_con):
        """
        This will find all the contracts that are either provided or consumed by the
        subflow_spec
        :param subflow_spec:
        :param pro_con:
        :return:
        """
        # t1 = datetime.datetime.now()
        self.valid_tenants = set()
        tenant_search = '^' + subflow_spec.tenant_name.replace('*', '.*') + '$'
        for tenant_name in self.tenants_by_name:
            match_result = re.match(tenant_search, tenant_name)
            if match_result is not None:
                self.valid_tenants.add(tenant_name)

        # t2 = datetime.datetime.now()
        # print 'tenants done', t2-t1
        # t1=t2

        # if 'common' not in tenants:
        tenants = self.valid_tenants | {'common'}
        contexts = set()
        context_search = '^' + subflow_spec.context_name.replace('*', '.*') + '$'
        for (tenant_name, context_name) in self.context_by_name:
            if tenant_name in tenants:
                match_result = re.match(context_search, context_name)
                context = self.context_by_name[(tenant_name, context_name)]
                # if context not in contexts:
                # todo: redundant entries are created
                if match_result is not None:
                    contexts.add(context)
                if tenant_name == 'common':
                    contexts.add(context)

        epgs_prefix = {}
        nodes = set()

        # t2 = datetime.datetime.now()
        # print 'contexts done', t2-t1
        # t1=t2
        for context in contexts:
            if context in self.context_radix:
                # cover both the case where what we are looking for is covered by a prefix
                # and where it covers more than one address.

                for ip in subflow_spec.ip:

                    node = self.context_radix[context].search_best(str(ip.prefix))
                    if node is not None:
                        nodes.add(node)
                    temp_nodes = self.context_radix[context].search_covered(str(ip.prefix))

                    if node is not None:

                        for node2 in temp_nodes:
                            if node2.data['epg'] != node.data['epg']:
                                nodes.add(node2)
                    else:
                        for node2 in temp_nodes:
                            nodes.add(node2)

        # t2 = datetime.datetime.now()
        # print 'nodes done', t2-t1
        # t1=t2
        # now have all the nodes
        if nodes is not None:
            for node in nodes:

                if node.data['epg'] not in epgs_prefix:
                    epgs_prefix[node.data['epg']] = set()
                epgs_prefix[node.data['epg']].add(IpAddress(node.prefix))

                try:
                    if node.data['any_epg'] is not None:
                        if node.data['any_epg'] not in epgs_prefix:
                            epgs_prefix[node.data['any_epg']] = set()
                        epgs_prefix[node.data['any_epg']].add(IpAddress(node.prefix))
                except KeyError:
                    pass

        # t2 = datetime.datetime.now()
        # print 'overlap done', t2-t1
        # t1=t2
        result = []
        for epg in epgs_prefix:
            if epg in self.epg_contract:
                for entry in self.epg_contract[epg]:
                    if entry['pro_con'] == pro_con:
                        if subflow_spec.contract is not None:
                            if subflow_spec.contract == entry['contract'][1].name:
                                result.append({'contract': entry['contract'],
                                               'prefix': epgs_prefix[epg],
                                               'epg': epg,
                                               'tenant': epg.get_parent().get_parent().name})
                        else:
                            result.append({'contract': entry['contract'],
                                           'prefix': epgs_prefix[epg],
                                           'epg': epg,
                                           'tenant': epg.get_parent().get_parent().name})

        # t2 = datetime.datetime.now()
        # print 'result done', t2-t1
        # t1=t2

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

    creds.add_argument('-tenant', type=str, default='*', help='Tenant name (wildcards, "*", accepted), default "*"')
    creds.add_argument('-context', type=str, default='*', help='Context name (wildcards, "*", accepted), default "*"')
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
    creds.add_argument('-tcpRules', type=str, default='any', help='TCP rules, e.g. "syn", "fin", "est". Default: "any"')

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
