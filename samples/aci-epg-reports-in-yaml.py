#!/usr/bin/env python

"""
Simple application that logs on to the APIC and displays all
EPGs.
"""
import socket
import yaml
import sys
from acitoolkit import Credentials, Session, Tenant, AppProfile, EPG, Endpoint


def main():
    """
    Main show EPGs routine
    :return: None
    """
    # Login to APIC
    description = ('Simple application that logs on to the APIC'
                   ' and displays all of the EPGs.')
    creds = Credentials('apic', description)
    args = creds.get()
    session = Session(args.url, args.login, args.password)
    resp = session.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Download all of the tenants, app profiles, and EPGs
    # and store the names as tuples in a list
    tenants = Tenant.get_deep(session)
    tenants_list = []
    for tenant in tenants:
        tenants_dict = {}
        tenants_dict['name'] = tenant.name

        if tenant.descr:
            tenants_dict['description'] = tenant.descr

        tenants_dict['app-profiles'] = []
        for app in tenant.get_children(AppProfile):
            app_profiles = {'name': app.name}
            if app.descr:
                app_profiles['description'] = app.descr
            app_profiles['epgs'] = []

            for epg in app.get_children(EPG):
                epgs_info = {'name': epg.name}
                if epg.descr:
                    epgs_info['description'] = epg.descr
                epgs_info['endpoints'] = []

                for endpoint in epg.get_children(Endpoint):
                    endpoint_info = {'name': endpoint.name}
                    if endpoint.ip != '0.0.0.0':
                        endpoint_info['ip'] = endpoint.ip
                        try:
                            hostname = socket.gethostbyaddr(endpoint.ip)[0]
                        except socket.error:
                            hostname = None
                        if hostname:
                            endpoint_info['hostname'] = hostname
                    if endpoint.descr:
                        endpoint_info['description'] = endpoint.descr

                    epgs_info['endpoints'].append(endpoint_info)
                app_profiles['epgs'].append(epgs_info)
            tenants_dict['app-profiles'].append(app_profiles)
        tenants_list.append(tenants_dict)

    tenants_info = {'tenants': tenants_list}
    print(yaml.safe_dump(tenants_info, sys.stdout,
                         indent=4, default_flow_style=False))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
