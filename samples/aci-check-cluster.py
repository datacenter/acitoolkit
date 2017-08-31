#!/usr/bin/env python

"""
Simple application that shows all of the processes running on a switch
"""
import sys
import json
from acitoolkit import Credentials, Session, Cluster


def main():
    """
    Main show Process routine
    :return: None
    """
    description = 'Simple application that logs on to the APIC and check cluster information for a fabric'
    creds = Credentials('apic', description)

    args = creds.get()

    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        sys.exit(0)

    cluster = Cluster.get(session)

    if (cluster.config_size != cluster.cluster_size):
        print("*******************************************************")
        print("WARNING, configured cluster size "), cluster.config_size
        print(":   not equal to the actual size "), cluster.cluster_size
        print("WARNING, desired stats collection might be lost")
        print("*******************************************************")
        print("APICs in the cluster"), cluster.name, (":")
        for apic in cluster.apics:
            print(json.dumps(apic, indent=4, sort_keys=True))
    else:
        print("PASS")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
