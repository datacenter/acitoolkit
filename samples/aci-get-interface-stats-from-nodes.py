#!/usr/bin/env python

import sys
import locale
from time import localtime, strftime
from operator import attrgetter
from acitoolkit.aciphysobject import Node, Linecard, Interface
from acitoolkit.acitoolkit import Credentials, Session

class Stats(object):
    """
    The Stats class contains the code and methods for fetching the statistics.
    """
    def __init__(self, session, txtformat='text', verbose=0):
        """
        Initialize a statistics session.

        :param self:
        :param session:
        :param txtformat: Output format, 'text' or 'csv'
        :param verbose: Verbosity level of debug output
        """
        print('Getting inital info from APIC....')
        self.session = session
        self.nodes = Node.get_deep(session)
        self.txtformat = txtformat
        self.verbose = verbose
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            pass

    numeric_speed = {
        '100G': 100000000000,
        '50G': 50000000000,
        '40G': 40000000000,
        '25G': 25000000000,
        '10G': 10000000000,
        '1G': 1000000000,
        '100M': 100000000,
        '10M': 10000000,
        'inherit': 10000000000,  # Not really, but a default.
    }

    def get_int_traffic(self, node_type, interval, threshold):
        """
        Get interface traffic stats from nodes of the given type.

        :param self:
        :param node_type: The type of node ('leaf' or 'spine') to get stats
                from. This is list of types.
        :param threshold: The minimum utilization threshold percentage.
        """
        if self.txtformat == 'csv':
            csv = True
            print("'Node Name','Interface','Epoch','Ingress bit rate'," \
                  "'Egress bit rate'")
        else:
            csv = False
            print("Report generated on {}.".format(
                  strftime("%Y-%b-%d %H:%M:%S %Z", localtime())))
            print("Using reporting threshold of {:d}%.".format(threshold))

        max_in_per = max_out_per = 0
        for node in sorted(self.nodes, key=attrgetter('name')):
            if node.role in node_type:
                if not csv:
                    print("  Node =", node.name)
                if self.verbose > 0:
                    print >> sys.stderr, "  Node =", node.name
                for lc in sorted(node.get_children(Linecard),
                                 key=attrgetter('name')):
                    if not csv:
                        print("    Linecard =", lc.name)
                    if self.verbose > 0:
                        print >> sys.stderr, "    Linecard =", lc.name
                    for intf in sorted(Interface.get(self.session, lc),
                                       key=attrgetter('name')):
                        info_dict = dict(intf.infoList())
                        if self.verbose > 0:
                            print >> sys.stderr, "      Interface =", \
                                                 intf.name
                        if info_dict['attributes']['operSt'] != 'up':
                            if self.verbose > 1:
                                print >> sys.stderr, "        Oper Status:", \
                                                     info_dict['attributes'
                                                               ]['operSt']
                            continue
                        intf_speed = self.numeric_speed[
                            info_dict['attributes']['operSpeed']]
                        stats = intf.stats.get()
                        excess_interval_count = interval_count = 0

                        # Convert from bytes to bits...
                        if not (('ingrTotal' in stats) and
                                (interval in stats['ingrTotal'])):
                            continue

                        max_value_in = 0
                        max_value_out = 0
                        max_value = 0
                        max_value_time = None
                        for epoch in stats['ingrTotal'][interval]:
                            value_in = intf.stats.retrieve('ingrTotal',
                                                           interval, epoch,
                                                           'bytesRate') * 8
                            value_out = intf.stats.retrieve('egrTotal',
                                                            interval, epoch,
                                                            'bytesRate') * 8
                            value_time = intf.stats.retrieve('egrTotal',
                                                             interval, epoch,
                                                             'intervalStart')
                            if csv:
                                print("'{}','{}',{},{},{}".format(
                                    node.name, intf.name, value_time,
                                    value_in, value_out))
                            else:
                                interval_count += 1
                                value_in_per = (value_in / intf_speed) * 100
                                value_out_per = (value_out / intf_speed) * 100
                                max_in_per = max([max_in_per, value_in_per])
                                max_out_per = max([max_out_per,
                                                   value_out_per])
                                if (threshold < (value_in_per)) or \
                                        (threshold < (value_out_per)):
                                    excess_interval_count += 1
                                    if (max_value < value_in) and \
                                            (value_out < value_in):
                                        max_value = max_value_in = value_in
                                        max_value_out = value_out
                                        max_value_time = value_time
                                    elif (max_value < value_out):
                                        max_value_in = value_in
                                        max_value = max_value_out = value_out
                                        max_value_time = value_time

                        if excess_interval_count and not csv:
                            print("      Interface =", intf.name)
                            print("      Interface Speed = {}({})".format(
                                  info_dict['attributes']['operSpeed'],
                                  locale.format('%d', intf_speed, True)))
                            print("        Highest usage interval with " \
                                  " utilization exceeding {}% for {}.".format(
                                      threshold, interval))
                            print("          Interval time: {}".format(
                                max_value_time))
                            print("          Ingress bps: {}".format(
                                locale.format('%d', max_value_in, True)))
                            print("          Egress bps: {}".format(
                                locale.format('%d', max_value_out, True)))
                            print("        {} of {} intervals over {}%" \
                                  " utilization".format(excess_interval_count,
                                                        interval_count,
                                                        threshold))

        if not csv:
            print("Max input usage found is {:d}%".format(int(max_in_per)))
            print("Max output usage found is {:d}%".format(int(max_out_per)))


def get_interface_stats_from_nodes():
    """
    Main execution routine

    :return: None
    """
    description = ('get_stats - A program to fetch statistics from an ACI '
                   'Fabric.')
    creds = Credentials('apic', description)
    creds.add_argument('-f', '--format', required=False, default='text',
                       help='Specify output format [csv, text]')
    creds.add_argument('-i', '--interval', required=False, default='15min',
                       help='Specify the aggregation interval')
    creds.add_argument('-n', '--node_type', required=False, default='spine',
                       help='Specify the type of node [spine, leaf, both]')
    creds.add_argument('-t', '--threshold', required=False, default=60,
                       type=int,
                       help='Specify the threshold for printing usage.')
    creds.add_argument('-v', '--verbose', action='count',
                       help='Specify verbosity of debug output.')

    args = creds.get()
    if args.format not in ['text', 'csv']:
        print >> sys.stderr, "Error: Unknown output format: '{}'".format(
            args.format)
        sys.exit(3)
    if args.interval not in ['5min', '15min', '1h', '1d', '1w', '1mo', '1qtr',
                             '1year']:
        print >> sys.stderr, "Error: Unknown interval '{}'".format(
            args.interval)
        sys.exit(4)
    if args.node_type in ['spine', 'leaf']:
        node_type = [args.node_type]
    elif args.node_type in ['both']:
        node_type = ['spine', 'leaf']
    else:
        print >> sys.stderr, "Error: Unknown node type: '{}'".format(
            args.node_type)
        sys.exit(5)
    if args.threshold > 100:
        threshold = 100
    elif args.threshold < 0:
        threshold = 0
    else:
        threshold = args.threshold

    # Login to APIC
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    statistics = Stats(session, args.format, args.verbose)
    statistics.get_int_traffic(node_type, args.interval, threshold)


if __name__ == "__main__":
    get_interface_stats_from_nodes()
