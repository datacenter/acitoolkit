Fake APIC
=========


Purpose 
--------

-  The Fake APIC is designed for users to view Managed Objects (and
   their properties) based on JSON configuration files
-  The Fake APIC works as an **offline-tool** for users who may not have
   access to the APIC, but still want to see certain (or all) Managed
   Objects on the network.

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

-  Modify a sample file such as ``aci-show-epgs.py`` to use the FakeSession class
   from the Fake APIC
   
-  Pass in the JSON files to the FakeSession
   constructor
   
   .. code-block:: python
                   
      from os import listdir
      from acitoolkit.acifakeapic import FakeSession
      ...
      ...
      # Set the directory to the location of the JSON files
      directory = 'applications/snapback/apic-config-db/'
      filenames = [directory + file for file in listdir(directory)
                   if file.endswith('.json')]

      # Create the session
      session = FakeSession(filenames) 

-  Run the file

   .. code:: python

       python aci-show-epgs.py -u <dummy url> -l <dummy login> -p <dummy password>

-  Since this file will be using the Fake APIC, you can pass in *any*
   value for the url, login, and password
-  The Fake APIC works by retrieving data from the JSON files to mimick
   responses from the real APIC
-  Users can pass in queries such as
   ``/api/mo/uni/tn-tenant1/BD-Br1.json?query-target=children``
   to get back responses.

How to pass in queries to the Fake APIC
---------------------------------------

   .. code-block:: python

      ...
      ...
      # to print the data nicely
      import json

      session = FakeSession(filenames)
      query = '/api/mo/uni/tn-tenant1/BD-1.json?query-target=children'
      fake_ret = fake_session.get(query)
      fake_data = fake_ret.json()['imdata']
      data = fake_ret.json()['imdata']
      # print the data from the Fake APIC
      print json.dumps(data, indent=4)
      

What queries the Fake APIC supports
-----------------------------------

-  Any queries starting with ``api/mo/`` can have the **scoping
   filters** of
-  query-target
-  rsp-subtree
-  target-subtree-class
-  Queries starting with ``api/node/class`` can only have the
   ``query-target`` with the value of ``self``
   
   -  values of rsp-subtree and target-subtree-class are supported
      
-  For more information regarding **scoping filters** see page 12 of the
   `Cisco APIC REST API User Guide <http://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/1-x/api/rest/b_APIC_RESTful_API_User_Guide.pdf>`__
   under the section "Applying Query Scoping Filters"

Dependencies
------------

-  Python 2.7
-  Data in the JSON configuration files
-  The Fake APIC can **only** retrieve data that are in the JSON files,
   it cannot retrieve any data from the real APIC
-  The Fake APIC does **not** check for bad queries
