#!/usr/bin/env python

"""
Simple application that logs on to the APIC, pull all LLDP neighbours,
and display in text table format
"""
import acitoolkit.acitoolkit as ACI
from acitoolkit import Node
from acitoolkit.aciConcreteLib import ConcreteLLdp
from tabulate import tabulate


def main():
    """
    Main show LLdps routine
    :return: None
    """
    # Take login credentials from the command line if provided
    # Otherwise, take them from your environment variables file ~/.profile
    description = ('Simple application that logs on to the APIC'
                   'and displays all the LLDP neighbours.')
    creds = ACI.Credentials('apic', description)
    args = creds.get()

    # Login to APIC
    session = ACI.Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    nodes = Node.get_deep(session, include_concrete=True)
    lldps = []
    for node in nodes:
        node_concrete_lldp = node.get_children(child_type=ConcreteLLdp)
        for node_concrete_lldp_obj in node_concrete_lldp:
            lldps.append(node_concrete_lldp_obj)

    tables = ConcreteLLdp.get_table(lldps)
    output_list = []
    for table in tables:
        for table_data in table.data:
            if table_data not in output_list:
                output_list.append(table_data)
    print(tabulate(output_list, headers=["Node-ID",
                                         "Local Interface",
                                         "Ip",
                                         "Name",
                                         "Chassis_id_t",
                                         "Neighbour Platform",
                                         "Neighbour Interface"]))

if __name__ == '__main__':
    main()
