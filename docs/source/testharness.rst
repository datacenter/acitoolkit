APIC Test Harness
=================


Purpose 
--------

-  The APIC Test Harness wraps the Fake APIC into an application server
   so that toolkit applications can run against the test harness with
   no modification whatsoever.
-  It can be used to execute toolkit scripts and applications against an
   APIC snapshot rather than a live APIC. For instance, the sample script
   ``acitoolkit/samples/aci-show-endpoints.py`` could be run against the live
   APIC, a snapshot file, yesterday's snapshot file, or even last year's
   snapshot file.
-  It can be used to generate conditions that are very difficult to
   create in real systems such as communication failures, connection resets,
   slow responses, and response timeouts.

Usage
-----

1. To generate JSON configuration files, use the snapback application
   located at ``acitoolkit/applications/snapback``
2. Run the ``aciconfigdb.py`` file

   .. code:: python

       python aciconfigdb.py -u <APIC url> -l <login> -p <password> -s --v1 -a

   -  The ``-s`` option takes the snapshot of the configuration from the
      APIC
   -  The ``--v1`` option takes the snapshot using direct HTTP queries
      rather than the configuration import and export policies. This is
      important to be able to simulate HTTP responses.
   -  The ``-a`` option ensures the configuration includes all properties
      of the class objects

      -  It's **very important** to give the ``-a`` because the Fake APIC
         depends on the all properities of the class objects

   -  The JSON files will be located at:
      ``acitoolkit/applications/snapback/apic-config-db``
   -  Depending on the APIC, getting all the data may take around 5 - 8
      seconds

3. The APIC test harness is located in the ``acitoolkit/applications/testharness``
   directory.

-  Run the ``apic_test_harness.py`` file

   .. code:: python

       python apic_test_harness.py --directory <snapshot directory>

   - The ``--directory`` option provides the directory where the snapshot files are
     located.  If the snapshot was created in the ``snapback`` directory, the command
     would be issued as follows

   .. code:: python

       python apic_test_harness.py --directory ../snapback/apic-config-db/

-  At this point, the APIC test harness is running as an application server.  By
   default, this service runs on the loopback address ``127.0.0.1`` on port ``5000``.

4. Use the APIC test harness

   - Leave the APIC test harness running and execute applications against it.
   - Here is an example usage taken from the ``acitoolkit/samples`` directory showing the usage
     of the ``aci-show-endpoints.py``.

   .. code:: python

       python aci-show-endpoints.py -l admin -p password -u http://127.0.0.1:5000

   - Most of the ``show`` commands found in the ``acitoolkit/samples`` directory can be executed
     against the APIC Test Harness and many applications can be as well.


Full command line options
-------------------------

- The full list of command line arguments is available through the ``--help`` command line
  argument.

   .. code-block:: python

       python apic_test_harness.py -h
       usage: apic_test_harness.py [-h] [--directory DIRECTORY]
                                   [--maxlogfiles MAXLOGFILES]
                                   [--debug [{verbose,warnings,critical}]] [--ip IP]
                                   [--port PORT]

        ACI APIC Test Harness Tool

        optional arguments:
          -h, --help            show this help message and exit
          --directory DIRECTORY
                                Directory containing the Snapshot files
          --maxlogfiles MAXLOGFILES
                                Maximum number of log files (default is 10)
          --debug [{verbose,warnings,critical}]
                                Enable debug messages.
          --ip IP               IP address to listen on.
          --port PORT           Port number to listen on.

   - Log files are stored locally within the directory where the APIC Test Harness is run. For
     the most complete logs, use the ``--debug verbose`` command line argument.
   - If communication is local only, the default IP address of ``127.0.0.1`` should be used.
     If communication will be originated from external sources, the IP address of the interface
     connecting to the outside world should be used.


What APIC Test Harness supports
-------------------------------

-  The APIC Test Harness is not a full blown APIC. It can only respond with the information
   found in the snapshot JSON files. It will accept configuration but the configuration will
   not change the snapshot JSON files.
-  The APIC Test Harness sits on top of the Fake APIC and is limited to what the Fake APIC supports.


Known Issues
------------

-  WebSockets and Event Subscriptions are not supported.
-  Statistics support is limited.
-  No configuration changes are supported.