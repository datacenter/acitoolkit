#!/usr/bin/env python
"""
This application replicates the switch CLI command 'show fex'
It largely uses raw queries to the APIC API
"""
from acitoolkit import Credentials, Session
from tabulate import tabulate


class FexCollector(object):
    def __init__(self, url, login, password):
        # Login to APIC
        self._apic = Session(url, login, password)
        if not self._apic.login().ok:
            self._logged_in = False
            print '%% Could not login to APIC'
        else:
            self._logged_in = True

    def _get_query(self, query_url, error_msg):
        resp = self._apic.get(query_url)
        if not resp.ok:
            print error_msg
            print resp.text
            return []
        return resp.json()['imdata']

    def get_fex_attributes(self, node_id, fex_id=None):
        if fex_id is None:
            query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                         '&target-subtree-class=satmDExtCh' % node_id)
        else:
            query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                         '&target-subtree-class=satmDExtCh&query-target-filter=eq(satmDExtCh.id, "%s")' % (node_id,
                                                                                                           fex_id))
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        return self._get_query(query_url, error_message)

    def get_fabric_port_attributes(self, node_id, fex_id):
        query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                     '&target-subtree-class=satmFabP&query-target-filter='
                     'eq(satmFabP.extChId,"%s")' % (node_id, fex_id))
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        return self._get_query(query_url, error_message)

    def get_transceiver_attributes(self, node_id, fab_port_id):
        query_url = ('/api/mo/topology/pod-1/node-%s/sys/satm/fabp-[%s].json?'
                     'query-target=subtree&target-subtree-class=satmRemoteFcot'
                     ',satmRemoteFcotX2' % (node_id, fab_port_id))
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        return self._get_query(query_url, error_message)

    def get_chassis_attributes(self, node_id, fex_id):
        query_url = '/api/mo/topology/pod-1/node-%s/sys/extch-%s.json' % (node_id, fex_id)
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        return self._get_query(query_url, error_message)

    def get_chassis_card_attributes(self, node_id, fex_id):
        query_url = ('/api/mo/topology/pod-1/node-%s/sys/extch-%s.json?'
                    'query-target=subtree&target-subtree-class=eqptExtChCard' % (node_id, fex_id))
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        return self._get_query(query_url, error_message)

    def get_chassis_running_attributes(self, node_id, fex_id):
        query_url = '/api/mo/topology/pod-1/node-%s/sys/extch-%s/running.json' % (node_id, fex_id)
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        return self._get_query(query_url, error_message)

    def get_chassis_cpu_attributes(self, node_id, fex_id):
        query_url = ('/api/mo/topology/pod-1/node-%s/sys/extch-%s.json?'
                    'query-target=subtree&target-subtree-class=eqptExtChCPU' % (node_id, fex_id))
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        return self._get_query(query_url, error_message)

    def get_fex_ids(self, node_id):
        fex_attrs = self.get_fex_attributes(node_id)
        fex_ids = []
        print fex_attrs
        for fex_attr in fex_attrs:
            fex_ids.append(str(fex_attr['satmDExtCh']['attributes']['id']))
        return fex_ids

    def get_node_ids(self, node_id):
        """
        Get the list of node ids from the command line arguments.
        If none, get all of the node ids
        :param args: Command line arguments
        :return: List of strings containing node ids
        """
        if node_id is not None:
            names = [node_id]
        else:
            names = []
            query_url = ('/api/node/class/fabricNode.json?'
                         'query-target-filter=eq(fabricNode.role,"leaf")')
            error_message = 'Could not get switch list from APIC.'
            nodes = self._get_query(query_url, error_message)
            for node in nodes:
                names.append(str(node['fabricNode']['attributes']['id']))
        return names

    @staticmethod
    def print_fex(fex_attr, chassis_attr, detail=False):
        print 'FEX:%s  Description: FEX0%s  state: %s' % (fex_attr['id'],
                                                          fex_attr['id'],
                                                          fex_attr['operSt'])
        print '  FEX version: %s [Switch version: %s]' % (fex_attr['ver'],
                                                          fex_attr['swVer'])

        if detail:
            print '  FEX Interim version:', fex_attr['intVer']
            print '  Switch Interim version:', fex_attr['swIntVer']
        print '  Extender Model: %s, Extender Serial: %s' % (fex_attr['model'],
                                                             fex_attr['ser'])
        print '  Part No:', chassis_attr['partNum']
        if detail:
            print '  Card Id: %s,' % fex_attr['swCId']
            print 'Mac Addr: %s,' % fex_attr['macAddr']
            print 'Num Macs:', fex_attr['numMacs']
            print '  Module Sw Gen:', fex_attr['swGen']
            print ' [Switch Sw Gen: %s]' % fex_attr['swSwGen']
        print ' pinning-mode: static    Max-links: 1'
        print '  Fabric port for control traffic:', fex_attr['controlFPort']

    @staticmethod
    def convert_to_ascii(data):
        data = str(data).split(',')
        resp = ''
        for letter in data:
            resp += str(unichr(int(letter)))
        return resp

    def print_fex_transceiver(self, node_id, fex_id):
        if fex_id is None:
            fex_ids = self.get_fex_ids(node_id)
        else:
            fex_ids = [fex_id]
        for fex_id in fex_ids:
            fab_port_num = 1
            fab_ports = self.get_fabric_port_attributes(node_id, fex_id)
            for fab_port in fab_ports:
                fab_port_attr = fab_port['satmFabP']['attributes']
                if fab_port_attr['id'].startswith('po'):
                    continue
                print 'Fex Uplink:', fab_port_num
                print '    Fabric Port :', fab_port_attr['id']
                if 'fcot-present' in fab_port_attr['flags']:
                    transceiver_attr = self.get_transceiver_attributes(node_id, str(fab_port_attr['id']))
                    try:
                        transceiver_attr = transceiver_attr[0]['satmRemoteFcot']['attributes']
                    except KeyError:
                        raise NotImplementedError  # probably satmRemoteFcotV2
                    print '    sfp is present'
                    print '    name is', self.convert_to_ascii(transceiver_attr['vendorName'])
                    print '    type is', transceiver_attr['typeName']
                    print '    part number is', self.convert_to_ascii(transceiver_attr['vendorPn'])
                    print '    revision is', self.convert_to_ascii(transceiver_attr['vendorRev'])
                    print '    serial number is', self.convert_to_ascii(transceiver_attr['vendorSn'])
                    print '    nominal bitrate is %s MBits/sec' % str(int(transceiver_attr['brIn100MHz']) * 100)
                    print '    Link length supported for 50/125mm fiber is 0 m(s)'
                    print '    Link length supported for 62.5/125mm fiber is 0 m(s)'
                    print '    Link length supported for copper is %s m' % transceiver_attr['distIn1mForCu']
                    print '    cisco id is', transceiver_attr['xcvrId']
                    print '    cisco extended id number is', transceiver_attr['xcvrExtId']
                fab_port_num += 1

    def print_fex_version(self, node_id, fex_id):
        if fex_id is None:
            fex_ids = self.get_fex_ids(node_id)
        else:
            fex_ids = [fex_id]
        for fex_id in fex_ids:
            chassis_attr = self.get_chassis_attributes(node_id, fex_id)
            chassis_attr = chassis_attr[0]['eqptExtCh']['attributes']
            chassis_running_attr = self.get_chassis_running_attributes(node_id, fex_id)
            chassis_running_attr = chassis_running_attr[0]['firmwareExtChRunning']['attributes']
            card_attr = self.get_chassis_card_attributes(node_id, fex_id)
            card_attr = card_attr[0]['eqptExtChCard']['attributes']
            fex_attr = self.get_fex_attributes(node_id, fex_id)
            fex_attr = fex_attr[0]['satmDExtCh']['attributes']
            cpu_attr = self.get_chassis_cpu_attributes(node_id, fex_id)
            cpu_attr = cpu_attr[0]['eqptExtChCPU']['attributes']

            print 'Software'
            print '  Bootloader version:           %s' % chassis_running_attr['loaderVer']
            print '  System boot mode:             primary'
            print '  System image version:         %s [build %s]' % (fex_attr['ver'], fex_attr['intVer'])

            print '\nHardware'
            print '  Module:                       %s' % card_attr['descr']
            print '  CPU:                          %s' % cpu_attr['model']
            print '  Serial number:                %s' % card_attr['modSerial']
            print '  Bootflash:                    locked'

            # TODO: Finish - need to add timestamping

    def show_fex(self, node=None, fex_id=None, detail=False, transceiver=False, version=False):
        """
        Show fex

        :param fex_id: String containing the specific FEX id. If none, all FEXs are used
        :param detail: Boolean indicating whether a detailed report should be given.
        :param transceiver: Boolean indicating whether a transceiver report should be given.
        :param version: Boolean indicating whether a version report should be given.
        :return: None
        """
        for node_id in self.get_node_ids(node):
            if fex_id is None:
                if not (detail or transceiver or version):
                    # Show fex
                    data = []
                    for fex in self.get_fex_attributes(node_id):
                        fex_attr = fex['satmDExtCh']['attributes']
                        data.append((int(fex_attr['id']),
                                     'FEX0' + str(fex_attr['id']),
                                     fex_attr['operSt'],
                                     fex_attr['model'],
                                     fex_attr['ser']))
                    data.sort(key=lambda tup: tup[0])
                    if len(data):
                        print 'Switch:', node_id
                        print tabulate(data, headers=['Number', 'Description', 'State', 'Model', 'Serial'])
                        print '\n'
                elif detail:
                    # Show fex detail
                    fex_ids = self.get_fex_ids(node_id)
                    for fex_id in fex_ids:
                        self.print_show_fex(node_id, fex_id, detailed=True)
                elif transceiver:
                    self.print_fex_transceiver(node_id, None)
            elif detail:
                # Show fex <fex_id> detail
                self.print_show_fex(node_id, fex_id, detailed=True)
            elif transceiver:
                # Show fex <fex_id> transceiver
                self.print_fex_transceiver(node_id, fex_id)
            elif version:
                # Show fex <fex_id> version
                self.print_fex_version(node_id, fex_id)
            else:
                # Show fex <fex_id>
                self.print_show_fex(node_id, fex_id)

    def print_show_fex(self, node_id, fex_id, detailed=False):
        for fex in self.get_fex_attributes(node_id, fex_id):
            fex_attr = fex['satmDExtCh']['attributes']
            for chassis in self.get_chassis_attributes(node_id, fex_attr['id']):
                chassis_attr = chassis['eqptExtCh']['attributes']
                self.print_fex(fex_attr, chassis_attr)
                query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                             '&target-subtree-class=satmFabP&query-target-filter=eq(satmFabP.extChId,"%s")' % (
                                 node_id,
                                 fex_attr['id']))
                resp = self._apic.get(query_url)
                if not resp.ok:
                    print 'Could not collect APIC data for switch %s.' % node_id
                    print resp.text
                    return
                if int(resp.json()['totalCount']) > 0:
                    print '  Fabric interface state:'
                    for interface in resp.json()['imdata']:
                        intf_attr = interface['satmFabP']['attributes']
                        print '    %15s - Interface %4s. State: %s' % (intf_attr['id'],
                                                                       intf_attr['operSt'],
                                                                       intf_attr['fsmSt'])
                        if detailed:
                            query_url = ('/api/mo/topology/pod-1/node-%s/sys/satm/fabp-[%s].json?query-target=subtree'
                                         '&target-subtree-class=satmHostP' % (node_id, intf_attr['id']))
                            resp = self._apic.get(query_url)
                            if not resp.ok:
                                print 'Could not collect APIC data for switch %s.' % node_id
                                print resp.text
                                return
                            if int(resp.json()['totalCount']) > 0:
                                data = []
                                for port in resp.json()['imdata']:
                                    port_attr = port['satmHostP']['attributes']
                                    data.append((port_attr['id'], port_attr['operSt'], port_attr['fabricPort']))
                                data.sort(key=lambda tup: tup[0])
                                print tabulate(data, headers=['Fex Port', 'State', 'Fabric Port'])


def main():
    """
    Main common routine for show fex description
    :return: None
    """
    # Set up the command line options
    creds = Credentials(['apic', 'nosnapshotfiles'],
                        description=("This application replicates the switch "
                                     "CLI command 'show interface'"))
    creds.add_argument('-s', '--switch',
                       type=str,
                       default=None,
                       help='Specify a particular switch id, e.g. "101"')
    creds.add_argument('-f', '--fex',
                       type=str,
                       default=None,
                       help='Specify a particular FEX id, e.g. "101"')
    group = creds.add_mutually_exclusive_group()
    group.add_argument('-d', '--detail',
                       action='store_true',
                       help='Provide a detailed report (equivalent to "show fex detail"')
    group.add_argument('-t', '--transceiver',
                       action='store_true',
                       help='Provide a transceiver report (equivalent to "show fex transceiver"')
    group.add_argument('-v', '--version',
                       action='store_true',
                       help='Provide a version report (equivalent to "show fex version"')
    args = creds.get()

    fex_collector = FexCollector(args.url, args.login, args.password)

    # Show interface description
    fex_collector.show_fex(args.switch, args.fex, args.detail, args.transceiver, args.version)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
