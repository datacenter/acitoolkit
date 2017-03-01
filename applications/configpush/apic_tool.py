"""
Standalone command line application to push the configuration to the APIC
"""
from apicservice import execute_tool, get_arg_parser
import json
import argparse


def main():
    """
    Main execution routine
    """
    parser = argparse.ArgumentParser(description='ACI Configuration Deployment Tool')
    parser.add_argument('--maxlogfiles', type=int, default=10, help='Maximum number of log files (default is 10)')
    parser.add_argument('--debug', nargs='?',
                        choices=['verbose', 'warnings', 'critical'],
                        const='critical',
                        help='Enable debug messages.')
    parser.add_argument('--config', default=None, help='Configuration file')
    parser.add_argument('-u', '--url',
                        default=None,
                        help='APIC IP address.')
    parser.add_argument('-l', '--login',
                        default=None,
                        help='APIC login ID.')
    parser.add_argument('-p', '--password',
                        default=None,
                        help='APIC login password.')
    parser.add_argument('--displayonly', action='store_true', default=False,
                        help=('Only display the JSON configuration. '
                              'Do not actually push to the APIC.'))
    parser.add_argument('--prompt', action='store_true', default=False,
                        help=('prompts a message to update the tenant with reference to the given config.'
                              'y/n/all ? if yes does the action specified in the message.'
                              'if all,this would allow the user to accept all changes/update.'
                              'if just pressed enter then the default is taken as no'))
    parser.add_argument('--useipepgs', action='store_true', default=False,
                        help=('Use IP based microsegmented EPGS to '
                              'assign the endpoint to the EPG.'))
    parser.add_argument('--tenant',
                        default='acitoolkitpush',
                        help='Tenant name for the configuration')
    parser.add_argument('--app',
                        default='acitoolkitapp',
                        help='Application profile name for the configuration')
    parser.add_argument('--l3ext',
                        default='L3OUT',
                        help='External Routed Network name for the configuration')

    args = parser.parse_args()
    if args.config is None:
        print '%% No configuration file given'
        return

    # Load in the configuration
    try:
        with open(args.config) as config_file:
            config = json.load(config_file)
    except IOError:
        print '%% Could not load configuration file'
        return
    except ValueError:
        print 'Could not load improperly formatted configuration file'
        return

    if 'apic' not in config:
        if args.url is None or args.login is None or args.password is None:
            print 'APIC credentials not given'
            return
        elif args.url is not None and 'http://' in args.url:
            ip_address = args.url.partition('http://')[-1]
            use_https = False
        elif args.url is not None and 'https://' in args.url:
            ip_address = args.url.partition('https://')[-1]
            use_https = True
        else:
            print 'Improperly formatted URL'
            return
        config['apic'] = {'user_name': args.login,
                          'password': args.password,
                          'ip_address': ip_address,
                          'use_https': use_https}

    tool = execute_tool(args)
    resp = tool.add_config(config)
    if resp == 'OK':
        if not args.displayonly:
            print 'Success'
    else:
        print resp


if __name__ == '__main__':
    main()
