"""
Standalone command line application to push the configuration to the APIC
"""
from apicservice import execute_tool, get_arg_parser
import json


def main():
    """
    Main execution routine
    """
    parser = get_arg_parser()
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
    parser.add_argument('--tenant',
                        default='acitoolkitpush',
                        help='Tenant name for the configuration')
    parser.add_argument('--app',
                        default='acitoolkitapp',
                        help='Application profile name for the configuration')

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

    if not args.displayonly and 'apic' not in config:
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


if __name__ == '__main__':
    main()
