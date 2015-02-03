Building a Simple Tenant Configuration
======================================
The following section will walk you through the implementation of the
``tutorial.py`` file found in the ``/samples/`` directory.  This code
will create a minimal configuration that will configure 2 interfaces
on the fabric to be on the same network so that they can
communicate. This code can be executed with the following command from
within the ``/samples/`` directory::

   python tutorial.py

Configuration Object Definition
-------------------------------

`Imports`
~~~~~~~~~
The first part of the tutorial program consists of the ``import``
statements.  The ``acitoolkit`` module from the acitoolkit package is
imported as is the ``credentials.py`` file.

.. code-block:: python

   from acitoolkit.acitoolkit import *
   from credentials import *

The ``acitoolkit`` module within the acitoolkit package provides
access to all of the acitoolkit configuration.

The ``credentials.py`` file contains the login credentials for the
APIC and is shown in its entirety below.  It contains the following
variables: ``LOGIN``, ``PASSWORD``, ``URL``, and ``IPADDR``.  These
variables should be modified to the settings of your particular APIC.

.. code-block:: python

   LOGIN = 'admin'
   PASSWORD = 'password'
   IPADDR = '10.1.1.1'
   URL = 'https://' + IPADDR

`Tenant Creation`
~~~~~~~~~~~~~~~~~

All of the configuration will be created within a single tenant named
``tutorial``.  This is done by creating an instance of the Tenant
class and passing it a string containing the tenant name.

.. code-block:: python

   tenant = Tenant('tutorial')

`Application Profile`
~~~~~~~~~~~~~~~~~~~~~

The Application Profile contains all of the Endpoint Groups
representing the application.  The next line of code creates the
application profile.  It does this by creating an instance of the
``AppProfile`` class and passing it a string containing the
Application Profile name and the ``Tenant`` object that this
``AppProfile`` will belong.

.. code-block:: python

   app = AppProfile('myapp', tenant)

Note that many of the objects within the acitoolkit are created in
this way, namely with a name and a parent object.  The parent object
must be an instance of this class's parent class according to the
acitoolkit object model.  The parent class of ``AppProfile`` is
``Tenant``.

`Endpoint Group`
~~~~~~~~~~~~~~~~

The Endpoint Group provides the policy based configuration for
Endpoints that are members of the Endpoint Group.  This is represented
by the ``EPG`` class.  In this case, we create an ``EPG`` with the
name `myapp` and pass the ``AppProfile`` that we created to be the
parent object.

.. code-block:: python

   epg = EPG('myepg', app)

`Context and Bridge Domain`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

We also need an L3 namespace and L2 forwarding domain so we create the
``Context`` and ``BridgeDomain`` in the same manner as we did for the
previous objects.  For both of these classes, the parent class is
Tenant.

.. code-block:: python

   context = Context('myvrf', tenant)
   bd = BridgeDomain('mybd', tenant)

We then associate the ``BridgeDomain`` instance with the ``Context``
instance.  This indicates that this ``BridgeDomain`` exists within
this ``Context``.

.. code-block:: python

   bd.add_context(context)

The ``EPG`` is then associated with the ``BridgeDomain`` that we created.

.. code-block:: python

   epg.add_bd(bd)

Associating the tenant configuration with the network
-----------------------------------------------------

At this point, the tenant configuration is complete.  However, it is
not bound to the physical network yet so let's connect the EPG to 2
interfaces.

`Physical Interfaces`
~~~~~~~~~~~~~~~~~~~~~

First, we must create objects to represent the physical interfaces
using the ``Interface`` class.  Interface objects are named using
interface type, pod, node (switch), module (linecard), and port
names.  In this case, the interface type is ``'eth'`` for ethernet and
the interfaces are located in pod 1 on leaf switch 101 in module 1
within ports 15 and 16.

.. code-block:: python

   if1 = Interface('eth', '1', '101', '1', '15')
   if2 = Interface('eth', '1', '101', '1', '16')

`VLANs`
~~~~~~~

In order to allow multiple EPGs to connect to the same interface, the
ACI fabric uses network virtualization technologies such as VLAN,
VXLAN, and NVGRE to keep the traffic isolated.  In this case, we chose
to use VLAN since it is the most ubiquitous and we chose to use the
same encapsulation on both physical interfaces, namely VLAN 5.

The ``L2Interface class`` represents the virtual L2 network interface.  In
this case, this is the VLAN attached to a given physical interface.
This is the interface where L2 protocols (such as spanning tree in
traditional networks) run.  Link layer protocols such as LLDP run
directly on the physical interface independent of VLANs.

We create the ``L2Interface`` and pass a name ``vlan5_on_if1``, the encapsulation
technology ``vlan``, and the virtual network identifier ``5`` as part of the
contructor.

.. code-block:: python

   vlan5_on_if1 = L2Interface('vlan5_on_if1', 'vlan', '5')

We next associate this ``L2Interface`` to the desired physical
interface.

.. code-block:: python

   vlan5_on_if1.attach(if1)

And we repeat for the second physical interface.

.. code-block:: python

   vlan5_on_if2 = L2Interface('vlan5_on_if2', 'vlan', '5')
   vlan5_on_if2.attach(if2)

Now, we simply associate the ``EPG`` with the ``L2Interface`` objects
that we created.

.. code-block:: python

   epg.attach(vlan5_on_if1)
   epg.attach(vlan5_on_if2)

Deploying to the APIC
----------------------

At this point, the entire configuration is done and all that is left
is connecting to the APIC and deploying the configuration.

First, we log into the APIC.  This is done through the ``Session``
class.  We create an instance and pass it the login credentials,
namely the ``URL``, ``LOGIN``, and ``PASSWORD``.

.. code-block:: python

   session = Session(URL, LOGIN, PASSWORD)

We also initiate the actual login.

.. code-block:: python

   session.login()

Once the login is complete, we can now send our configuration to the
APIC. This is done by calling the ``Session`` object with the
``push_to_apic`` function that requires a URL and the JSON data to
send to the APIC.  All of the configuration for the application
topology is collected under the ``Tenant``.  In order to get the URL to
use and the JSON for our configuration, we simply call the ``Tenant``
instance with ``get_url`` and ``get_json`` respectively.

.. code-block:: python

   resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())

The ``push_to_apic`` call returns an object.  This object is an
instance of the ``Response`` class from the popular `requests
<http://docs.python-requests.org/en/latest/#>`_ library which provides
a rich set of return codes and status.  Here, we simply check that the
call was successful.

.. code-block:: python

   if resp.ok:
      print 'Success'

Displaying the JSON Configuration
---------------------------------

At this point, we're done !  The configuration has been sent to the
APIC.  Congratulations, you just programmed a datacenter fabric !  You
should be able to see your new tenant ``tutorial`` within the APIC GUI
with its new EPG and static path bindings.

The next few lines in the ``tutorial.py`` file simply print what was
sent to the APIC.  You can use this to manually edit the JSON if you
wish to access the richer API on the APIC that the acitoolkit does not
expose.

.. code-block:: python

   print 'Pushed the following JSON to the APIC'
   print 'URL:', tenant.get_url()
   print 'JSON:', tenant.get_json()

Removing the tenant configuration
---------------------------------

The last few lines of the tutorial.py file are commented out.  This is
because if executed they will delete the configuration that we just
sent to the APIC.  In order to delete the tenant configuration, we
simply mark the ``Tenant`` as deleted and push the configuration to
the APIC.  This causes all of the configuration underneath the
``Tenant`` to be deleted.

.. code-block:: python

   #tenant.mark_as_deleted()
   #resp = session.push_to_apic(tenant.get_url(), data=tenant.get_json())

So, if you uncomment these 2 lines and re-run the entire
``tutorial.py`` file, you will again push the configuration to the
APIC, print it again, and then immediately delete the configuration
leaving you where we started.
