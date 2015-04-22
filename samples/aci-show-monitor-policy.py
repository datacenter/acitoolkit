#!/usr/bin/env python
################################################################################
#                 _    ____ ___   _____           _ _    _ _                   #
#                / \  / ___|_ _| |_   _|__   ___ | | | _(_) |_                 #
#               / _ \| |    | |    | |/ _ \ / _ \| | |/ / | __|                #
#              / ___ \ |___ | |    | | (_) | (_) | |   <| | |_                 #
#        ____ /_/   \_\____|___|___|_|\___/ \___/|_|_|\_\_|\__|                #
#       / ___|___   __| | ___  / ___|  __ _ _ __ ___  _ __ | | ___  ___        #
#      | |   / _ \ / _` |/ _ \ \___ \ / _` | '_ ` _ \| '_ \| |/ _ \/ __|       #
#      | |__| (_) | (_| |  __/  ___) | (_| | | | | | | |_) | |  __/\__ \       #
#       \____\___/ \__,_|\___| |____/ \__,_|_| |_| |_| .__/|_|\___||___/       #
#                                                    |_|                       #
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
Simple application that logs on to the APIC and displays all
of the Interfaces.
"""
import sys
import acitoolkit.acitoolkit as ACI


def main():
    """
    Main execution routine

    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = 'Simple application that logs on to the APIC'\
        'and displays all of the monitoring policies.'
    creds = ACI.Credentials('apic', description)
    creds.add_argument('-f', '--flat', action="store_true",
                       help='Show monitor policy flattened - recommended')
    creds.add_argument('-t', '--type', default="all",
                       type=str, choices=['all', 'fabric', 'access'],
                       help='Show a particular monitor policy type (default:all)')
    creds.add_argument('-n', '--name', metavar='POLICYNAME',
                       type=str,
                       help='Show all monitor policies whose name is POLICYNAME')
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    def _getRet(adminState, retention):
        """
        Returns a string for the retention.  If the administrative
        state is 'disabled', it will return a retention string of '-'.
        If the admin state is enabled and the retention is 'none',
        it will return zero. In all other cases it will return
        the retention string.

        :param adminState: The administrative state.  Either 'disabled or 'enabled'
        :param retention:  The retention string.
        :returns: String for the retention.
        """
        if adminState == 'disabled':
            return '-'
        return '0' if retention == 'none' else retention

    def printPolicyFlat(policy):
        """
        Prints the monitoring policy in a tabular format.  A dash ('-')
        indicates that a particular counter family is not gathered at a
        given granularity.  A value of '0' indicates that the statistics
        history is not kept'

        :param policy:  The policy object whose state is to be displayed.
        """
        policyFlat = policy.flat('l1PhysIf')
        policyName = policy.policyType + ':' + policy.name
        result = {}
        for counter in ACI.MonitorStats.statsFamilyEnum:
            rec = []
            for granularity in ACI.CollectionPolicy.granularityEnum:
                adminState = policyFlat[counter][granularity].adminState
                retention = policyFlat[counter][granularity].retention
                rec.append(_getRet(adminState, retention))
            result[counter] = rec

        print('{0:^16}  {1:^7} {2:^7} {3:^7} {4:^7} {5:^7} {6:^7} {7:^7} {8:^7}'.
              format(policyName, *ACI.CollectionPolicy.granularityEnum))
        print('{0:-^16}  {0:-^7} {0:-^7} {0:-^7} {0:-^7} {0:-^7} {0:-^7} '
              '{0:-^7} {0:-^7}'.format(''))

        for counter in ACI.MonitorStats.statsFamilyEnum:
            print('{0:>16}: {1:^7} {2:^7} {3:^7} {4:^7} {5:^7} {6:^7} {7:^7} '
                  '{8:^7}'.format(counter, *result[counter]))

    def printPolicyHeir(obj):
        """
        Prints the monitoring policy in a heirarchical format.

        :param obj: The policy object whose state is to be displayed.
        """
        print(obj)
        formatStr = '{0:27} {1:^11} {2:^9} {3:^10}'
        print(formatStr.format('object', 'granularity', 'retention', 'adminState'))
        print('{0:-^27} {0:-^11} {0:-^9} {0:-^10}'.format(''))

        for collection in obj.collection_policy:
            child = obj.collection_policy[collection]
            print(formatStr.format('Collection', child.granularity,
                                   child.retention, child.adminState))
        for target in obj.monitor_target:
            child = obj.monitor_target[target]
            print('{0:27}'.format('MonitorTarget:' + child.scope))

            for collection in child.collection_policy:
                targetChild = child.collection_policy[collection]
                print(formatStr.format('    Collection', targetChild.granularity,
                                       targetChild.retention,
                                       targetChild.adminState))
            for statFamily in child.monitor_stats:
                targetChild = child.monitor_stats[statFamily]
                print('{0:27}'.format('    ' + targetChild.scope))

                for collection in targetChild.collection_policy:
                    statChild = targetChild.collection_policy[collection]
                    print(formatStr.format('        Collection',
                                           statChild.granularity,
                                           statChild.retention,
                                           statChild.adminState))

    policies = ACI.MonitorPolicy.get(session)

    for policy in policies:
        if args.type != 'all' and policy.policyType != args.type:
            continue

        if args.name:
            if policy.name != args.name:
                continue

        if args.flat:
            printPolicyFlat(policy)
        else:
            printPolicyHeir(policy)

        print

if __name__ == '__main__':
    main()
