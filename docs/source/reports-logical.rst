ACI Logical Reports
==================

Logical Tenant level reporting can be dome via this command line application.

Installation
------------

This reporting application is included in the ``acitoolkit`` package when downloaded using the ``git clone`` method
of installation. The application can be found in the ``acitoolkit/applications/reports`` directory.

Usage
-----

The application is started from the command line.  In its simplest form, it can be invoked by the following command::

  python aci-report-logical.py

The full command help is shown below::

  python aci-report-logical.py -h

  usage: aci-report-logical.py [-h] [-u URL] [-l LOGIN] [-p PASSWORD]
                               [-t TENANT] [-all] [-basic] [-context]
                               [-bridgedomain] [-contract] [-taboo] [-filter]
                               [-app_profile] [-epg] [-endpoint]

  Simple application that logs on to the APIC and displays reports for the
  logical model.

  optional arguments:
    -h, --help            show this help message and exit
    -u URL, --url URL     APIC URL e.g. http://1.2.3.4
    -l LOGIN, --login LOGIN
                          APIC login ID.
    -p PASSWORD, --password PASSWORD
                          APIC login password.
    -t TENANT, --tenant TENANT
                          Specify a particular tenant name
    -all                  Show all detailed information
    -basic                Show basic tenant info
    -context              Show Context info
    -bridgedomain         Show Bridge Domain info
    -contract             Show Contract info
    -taboo                Show Taboo (Deny) info
    -filter               Show Filter info
    -app_profile          Show Application Profile info
    -epg                  Show Endpoint Group info
    -endpoint             Show End Point info


Notes
-----

The reporting application can generate a large amount of data. It may take some time to collect all of
the data depending on the size of the ACI fabric. This is especially true when executing the ``-all``
command line option.