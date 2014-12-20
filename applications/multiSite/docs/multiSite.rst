MultiSite
====================
The multiSite module allows the programmer to easily copy existing
tenant or application from an APIC account to another APIC account.
The detail steps are:

1. pull a json file from a APIC account.
#. push the json file to github.
#. pull the json from github.
#. push the json to another APIC account.

Github is used as a bridge for transferring json file from one APIC
to another APIC. It also stores the record of the change of the json
file.


.. _tut-using:

****************************
Using
****************************


.. _tut-invoking:

Usage
========================

The ``copy_tenant.py`` and ``copy_application.py`` provide a fast and easy
way to copy a tenant or an application from a APIC to another APIC.

Put the APIC info and your github account info in ``credentials.py``.
Then simply run::

  python copy_tenant.py

or ::

  python copy_application.py

Then you will copy a tenant or an application from one APIC to another APIC.
