ACI Switch Reports
==================

Switch level reporting can be dome via this command line application.

Installation
------------

This reporting application is included in the ``acitoolkit`` package when downloaded using the ``git clone`` method
of installation. The application can be found in the ``acitoolkit/applications/reports`` directory.

Usage
-----

The application is started from the command line.  In its simplest form, it can be invoked by the following command::

  python aci-report-switch.py

The full command help is shown below::

  python aci-report-switch.py -h

  Simple application that logs on to the APIC and displays reports for the
  switches.
  usage: aci-report-switch.py [-h] [-u URL] [-l LOGIN] [-p PASSWORD] [-s SWITCH]
                            [-all] [-basic] [-linecard] [-supervisor]
                            [-fantray] [-powersupply] [-arp] [-context]
                            [-bridgedomain] [-svi] [-accessrule] [-endpoint]
                            [-portchannel] [-overlay] [-tablefmt TABLEFMT]

  optional arguments:
    -h, --help            show this help message and exit
    -u URL, --url URL     APIC URL e.g. http://1.2.3.4
    -l LOGIN, --login LOGIN
                          APIC login ID.
    -p PASSWORD, --password PASSWORD
                          APIC login password.
    -s SWITCH, --switch SWITCH
                          Specify a particular switch id, e.g. "102"
    -all                  Show all detailed information
    -basic                Show basic switch info
    -linecard             Show Lincard info
    -supervisor           Show Supervisor Card info
    -fantray              Show Fantray info
    -powersupply          Show Power Supply info
    -arp                  Show ARP info
    -context              Show Context (VRF) info
    -bridgedomain         Show Bridge Domain info
    -svi                  Show SVI info
    -accessrule           Show Access Rule and Filter info
    -endpoint             Show End Point info
    -portchannel          Show Port Channel and Virtual Port Channel info
    -overlay              Show Overlay info
    -tablefmt TABLEFMT    Table format [fancy_grid, plain, simple, grid, pipe,
                          orgtbl, rst, mediawiki, latex, latex_booktabs]

Notes
-----

The reporting application can generate a large amount of data. It may take some time to collect all of
the data depending on the size of the ACI fabric. This is especially true when executing the ``-all``
command line option.