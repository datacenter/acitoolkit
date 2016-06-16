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
Search test
"""
import unittest

from aciConSearchGui import input_parser, build_flow_spec
from aciConSearch import IpAddress

LIVE_TEST = False


class Test_Parse_Input(unittest.TestCase):
    """
    Checks that the object model is correctly setup
    """

    def test_parse_one(self):
        res = input_parser("sip=10/9")
        self.assertEqual(res['sip'], '10/9')

    def test_parse_multiple(self):
        res = input_parser('sip=10/9 dip=1.2.3.4')
        self.assertEqual(res['sip'], '10/9')
        self.assertEqual(res['dip'], '1.2.3.4')

        res = input_parser('sip=10/9 dport=10 - 20 tenant=cisco*')
        self.assertEqual(len(res), 3)
        self.assertEqual(res['sip'], '10/9')
        self.assertEqual(res['dport'], '10-20')
        self.assertEqual(res['tenant'], 'cisco*')

        res = input_parser('sip=10.3.4/9 dport= 10 tenant =  cisco*')
        self.assertEqual(len(res), 3)
        self.assertEqual(res['sip'], '10.3.4/9')
        self.assertEqual(res['dport'], '10')
        self.assertEqual(res['tenant'], 'cisco*')

        res = input_parser('tenant=10.3.4/9 dport= 10 tenant =  cisco*')
        self.assertEqual(len(res), 2)
        self.assertEqual(res['dport'], '10')
        self.assertEqual(res['tenant'], 'cisco*')

        res = input_parser('tennant=10.3.4/9 dport= 10 tenant =  cisco*')
        self.assertEqual(len(res), 2)
        self.assertEqual(res['dport'], '10')
        self.assertEqual(res['tenant'], 'cisco*')

        res = input_parser('arpOpc=10.3.4/9 dport= 10 tenant =  cisco* sport= 5- 40')
        self.assertEqual(len(res), 4)
        self.assertEqual(res['dport'], '10')
        self.assertEqual(res['tenant'], 'cisco*')
        self.assertEqual(res['arpOpc'], '10.3.4/9')
        self.assertEqual(res['sport'], '5-40')

        res = input_parser('arpOpc=10.3.4/9 dport= 10 -40 tenant =  cisco* sport= 5- 40')
        self.assertEqual(len(res), 4)
        self.assertEqual(res['dport'], '10-40')
        self.assertEqual(res['tenant'], 'cisco*')
        self.assertEqual(res['arpOpc'], '10.3.4/9')
        self.assertEqual(res['sport'], '5-40')

        res = input_parser('5- 40 dfs')
        self.assertEqual(len(res), 0)

    def test_build_flow_spec(self):
        res = build_flow_spec('tenant=a context=b sip=1.2.3.4 dip=10/24 arpOpc=req etherT=ip prot=tcp dport=10 - 20')
        self.assertEqual(res.tenant_name, 'a')
        self.assertEqual(res.context_name, 'b')
        self.assertEqual(res.sip[0], IpAddress('1.2.3.4'))
        self.assertEqual(res.dip[0], IpAddress('10.0.0.0/24'))
        self.assertEqual(res.protocol_filter[0].arpOpc, 'req')
        self.assertEqual(res.protocol_filter[0].etherT, 'ip')
        self.assertEqual(res.protocol_filter[0].prot, 'tcp')
        self.assertEqual(res.protocol_filter[0].dFromPort, 10)
        self.assertEqual(res.protocol_filter[0].dToPort, 20)

        res = build_flow_spec('sport=45- 49 tcpRules=syn')
        self.assertEqual(res.tenant_name, '*')
        self.assertEqual(res.context_name, '*')
        self.assertEqual(res.sip[0], IpAddress('0/0'))
        self.assertEqual(res.dip[0], IpAddress('0/0'))
        self.assertEqual(res.protocol_filter[0].arpOpc, 'any')
        self.assertEqual(res.protocol_filter[0].etherT, 'ip')
        self.assertEqual(res.protocol_filter[0].prot, 'tcp')
        self.assertEqual(res.protocol_filter[0].sFromPort, 45)
        self.assertEqual(res.protocol_filter[0].sToPort, 49)
        self.assertEqual(res.protocol_filter[0].tcpRules, 'syn')

        res = build_flow_spec('sport=45 tcpRules=syn')
        self.assertEqual(res.tenant_name, '*')
        self.assertEqual(res.context_name, '*')
        self.assertEqual(res.sip[0], IpAddress('0/0'))
        self.assertEqual(res.dip[0], IpAddress('0/0'))
        self.assertEqual(res.protocol_filter[0].arpOpc, 'any')
        self.assertEqual(res.protocol_filter[0].etherT, 'ip')
        self.assertEqual(res.protocol_filter[0].prot, 'tcp')
        self.assertEqual(res.protocol_filter[0].sFromPort, 45)
        self.assertEqual(res.protocol_filter[0].sToPort, 45)
        self.assertEqual(res.protocol_filter[0].tcpRules, 'syn')

        res = build_flow_spec('etherT=arp')
        self.assertEqual(res.tenant_name, '*')
        self.assertEqual(res.context_name, '*')
        self.assertEqual(res.sip[0], IpAddress('0/0'))
        self.assertEqual(res.dip[0], IpAddress('0/0'))
        self.assertEqual(res.protocol_filter[0].arpOpc, 'any')
        self.assertEqual(res.protocol_filter[0].etherT, 'arp')
        self.assertEqual(res.protocol_filter[0].prot, 'any')
        self.assertEqual(res.protocol_filter[0].sFromPort, 'any')
        self.assertEqual(res.protocol_filter[0].sToPort, 'any')
        self.assertEqual(res.protocol_filter[0].tcpRules, 'any')

    def test_infer_multiple_filters(self):
        res = build_flow_spec('dport=80')
        self.assertEqual(len(res.protocol_filter), 2)
        exp = [res.protocol_filter[0].prot, res.protocol_filter[1].prot]
        self.assertTrue('tcp' in exp)
        self.assertTrue('udp' in exp)

        self.assertEqual(res.protocol_filter[0].etherT, 'ip')
        self.assertEqual(res.protocol_filter[1].etherT, 'ip')

        res = build_flow_spec('sport=80')
        self.assertEqual(len(res.protocol_filter), 2)
        exp = [res.protocol_filter[0].prot, res.protocol_filter[1].prot]
        self.assertTrue('tcp' in exp)
        self.assertTrue('udp' in exp)

        self.assertEqual(res.protocol_filter[0].etherT, 'ip')
        self.assertEqual(res.protocol_filter[1].etherT, 'ip')


@unittest.skipIf(LIVE_TEST is False, 'Not performing live APIC testing')
class TestLiveAPIC(unittest.TestCase):
    def login_to_apic(self):
        """Login to the APIC
           RETURNS:  Instance of class Session
        """
        pass


if __name__ == '__main__':
    unittest.main()
