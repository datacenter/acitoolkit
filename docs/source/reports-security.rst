ACI Security Report
===================

This application provides simple audit reports that can be used for compliance checks or security audits.


Installation
------------

This reporting application is included in the ``acitoolkit`` package when downloaded using the ``git clone`` method
of installation. The application can be found in the ``acitoolkit/applications/reports`` directory.

Usage
-----

The application is started from the command line.  In its simplest form, it can be invoked by the following command::

  python aci-report-security-audit.py

The full command help is shown below::

  python aci-report-security-audit.py -h

  usage: aci-report-security-audit.py [-h] [-u URL] [-l LOGIN] [-p PASSWORD]
                                      [--csv CSV]

  Simple application that logs on to the APIC and produces a report that can be
  used for security compliance auditing.

  optional arguments:
    -h, --help            show this help message and exit
    -u URL, --url URL     APIC URL e.g. http://1.2.3.4
    -l LOGIN, --login LOGIN
                          APIC login ID.
    -p PASSWORD, --password PASSWORD
                          APIC login password.
    --csv CSV             Output to a CSV file.

Output
------

By default, the audit report is displayed on the screen as comma separated values. If the ``--csv`` command line option
is provided, the output will be sent to the specified filename in proper CSV format.

Each row of the report contains the following information::

  * Tenant name
  * Context (VRF) name
  * Bridge Domain name
  * Application Profile name
  * EPG name
  * Number of Consumer EPG Endpoints
  * Provided Contract name
  * Number of Providing EPG Endpoints
  * Consumed Contract name
  * Protocol specified in the Filter entry
  * Source port range specified in the Filter entry
  * Destination port range specified in the Filter entry
