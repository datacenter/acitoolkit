#!/usr/bin/env python

"""
Simple application that logs on to the APIC, pull all CDP neighbours,
and display in text table format
"""
import acitoolkit.acitoolkit as ACI
from acitoolkit import Node
from acitoolkit.aciConcreteLib import ConcreteCdp
from tabulate import tabulate


def main():
    """
    Main show Cdps routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC'
                   'and displays all the CDP neighbours.')
    creds = ACI.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    nodes = Node.get_deep(session, include_concrete=True)
    cdps = []
    for node in nodes:
        node_concrete_cdp = node.get_children(child_type=ConcreteCdp)
        for node_concrete_cdp_obj in node_concrete_cdp:
            cdps.append(node_concrete_cdp_obj)

    tables = ConcreteCdp.get_table(cdps)
    output_list = []
    for table in tables:
        for table_data in table.data:
            if table_data not in output_list:
                output_list.append(table_data)
    print tabulate(output_list, headers=["Node-ID",
                                         "Local Interface",
                                         "Neighbour Device",
                                         "Neighbour Platform",
                                         "Neighbour Interface"])

if __name__ == '__main__':
    main()
