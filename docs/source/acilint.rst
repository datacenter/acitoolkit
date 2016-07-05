ACI Lint
========

``acilint`` is a static analysis tool for Cisco ACI fabrics.  Some
example use cases for such a tool include the following:

* Configuration Analysis

    In this purpose, it can be used to examine the APIC configuration
    and determine whether any of the configuration could be possibly problematic or
    suspicious.  It examines the configuration much like static code
    analysis tools such as the original *lint* checker did for
    software development in *C* or *pylint* for *Python*.  It
    generates **Warnings** and **Errors** that give indications that
    the configuration should be examined.  Often these Warnings are
    not problems, but incomplete or stale configuration that is not
    currently in use.

* Compliance, Governance, and Auditing

    In this purpose, it can be used to determine whether the
    configuration meets higher level goverance and compliance rules.
    These rules are similar to *lint* style rules but exploit the APIC
    ability to provide additional classification tags on objects. Tags
    provide a simple and flexible way to classify any APIC object in
    one or more user-defined groups.

    For example, EPGs can be tagged as secure and non-secure.  A
    compliance rule can be defined that specifies that secure EPGs
    cannot consume a contract from a non-secure EPG.  Upon violation
    of this rule, a **warning** or an **error** can be raised.

Usage
-----

``acilint`` can be run against the current running APIC configuration or a
previously saved set of configuration snapshot files.

Running using Live APIC configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``acilint`` collects the configuration directly from the APIC, it
needs the proper login credentials.  These can be passed via the command
line arguments, a ``credentials.py`` file, environment variables, or if none of
these, the user will be directly queried.

The following example shows how to run using the command line
arguments for credentials::

    python acilint.py -l admin -p password -u https://1.2.3.4

where ``admin`` is the APIC login username, ``password`` is the APIC
password, and ``https://1.2.3.4`` is the URL used to login to the
APIC.

Running using Configuration Snapshot files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``snapback`` application provides the ability to save snapshots of
the APIC configuration into JSON files.  ``acilint`` can use these snapshot
files as input rather than connecting to a live APIC.

This can be useful in debugging as it lets the user compare the ``acilint``
output of the live APIC to the output of a previous configuration snapshot.
``acilint`` can also be used to perform some "What If" scenarios. A single
configuration snapshot actually consists of multiple snapshot files. These
configuration files are then fed as input into ``acilint``. These snapshot
files fed into ``acilint`` can actually be from different configuration
snapshot versions creating an entirely new configuration that may have never
existed on the APIC, but we can run ``acilint`` against this configuration to
check for possible errors and warnings that would occur if this configuration
were to be deployed.

The following example shows how to run with configuration snapahot files as
input::

    python acilint.py --snapshotfiles infra.json tenant-cisco.json fabric.json

Customization
~~~~~~~~~~~~~

By default, all checks will be performed.  However, like many static
code analysis tools, ``acilint`` is customizable and only the desired
warnings and errors can be issued.

To customize ``acilint``, generate a configuration file with the
following command::

    python acilint.py --generateconfigfile acilint.cfg

or even shorter::

    python acilint.py -g acilint.cfg

where ``acilint.cfg`` is the filename you wish to create.

The generated configuration file will contain a list of all of the
current checks being performed.

An example config file is shown below::

    # acilint configuration file
    # Remove or comment out any warnings or errors that you no longer wish to see
     error_001
     error_002
     warning_001
     warning_002
     warning_003

To remove checks, either:

* Delete the line containing the check, or
* Comment it out by prepending a ``#`` in front of the check

Errors and Warnings
-------------------

The following list of Errors and Warnings are performed by
``acilint``.  Since ``acilint`` is written on top of the
``acitoolkit`` package, the checks are limited to the functionality
exposed by that package.  However as the ``acitoolkit`` expands, so
shall ``acilint``.

Warnings
~~~~~~~~

+------------+--------------------------------------------+
|warning_001 |Tenant has no app profile                   |
+------------+--------------------------------------------+
|warning_002 |Tenant has no context                       |
+------------+--------------------------------------------+
|warning_003 |AppProfile has no EPGs                      |
+------------+--------------------------------------------+
|warning_004 |Context has no BridgeDomain                 |
+------------+--------------------------------------------+
|warning_005 |BridgeDomain has no EPGs assigned           |
+------------+--------------------------------------------+
|warning_006 |Contract is not provided at all             |
+------------+--------------------------------------------+
|warning_007 |Contract is not consumed at all             |
+------------+--------------------------------------------+
|warning_008 |EPG providing contracts but in a Context    |
|            |with no enforcement                         |
+------------+--------------------------------------------+
|warning_010 |EPG providing contract but consuming EPG is |
|            |in a different context                      |
+------------+--------------------------------------------+
|warning_011 |Contract contains bi-directional TCP        |
|            |Subjects                                    |
+------------+--------------------------------------------+
|warning_012 |Contract contains bi-directional UDP        |
|            |Subjects                                    |
+------------+--------------------------------------------+
|warning_013 |Contract has no Subjects                    |
+------------+--------------------------------------------+
|warning_014 |Contract has Subjects with no Filters       |
+------------+--------------------------------------------+

Errors
~~~~~~

+------------+---------------------------------------------+
|error_001   |BridgeDomain has no context                  |
+------------+---------------------------------------------+
|error_002   |EPG has no BD assigned                       |
+------------+---------------------------------------------+
|error_005   |Duplicate or overlapping subnets in Context  |
+------------+---------------------------------------------+
|error_006   |ExternalNetwork Subnets duplicated in fabric |
+------------+---------------------------------------------+

Critical
~~~~~~~~

+-------------+--------------------------------------------+
|critical_001 |Compliance check example                    |
+-------------+--------------------------------------------+

critical_001 is a compliance check example that will perform the
following:

* Ensure that all of the EPGs in the system have been classified as
  *secure* and *nonsecure* using the tagging capability provided by
  the ``acitoolkit``.

* Ensures that none of the *secure* EPGs can communicate with the
  *nonsecure* EPGs by checking that no contract provided by *secure*
  EPGs is consumed by *nonsecure* EPGs.


Developing Checks
-----------------

Additional checks can be added through new methods on the ``Checker``
class.  If the method begins with ``warning_`` or ``error_`` or
``critical_``, it will automatically be executed as part of the
``acilint`` execution.  The new checks will also automatically inherit
the customization capability through the usage of the configuration
file.  Some familiarity with the ``acitoolkit`` object model is
necessary to write additional checks.
