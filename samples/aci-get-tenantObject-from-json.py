#!/usr/bin/env python

"""
Simple application that takes a tenant json from a file and returns a tenant object
"""
import acitoolkit.acitoolkit as ACI
import argparse
import json


def main():
    """
    Main execution routine

    """
    description = 'Simple application that takes a tenant json from a configfile and returns a tenant object.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-t', '--tenantname', required = True,  help='name of the tenant')
    parser.add_argument('-config','--tenantconfigfile', required=True,
                       help='file containing tenant json')
    args = parser.parse_args()

    tenantObject = None
    if args.tenantconfigfile:
        with open(args.tenantconfigfile) as data_file:
            tenant_json = json.load(data_file)

    tenant = ACI.Tenant(args.tenantname)
    ACI.Tenant.get_from_json(tenant,tenant_json,parent=tenant)
    print(tenant.get_json())

if __name__ == '__main__':
    main()
