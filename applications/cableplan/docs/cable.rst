cableplan module
====================
The Cable Plan module allows the programmer to easily import existing
cable plans from XML files, import the currently running cable plan
from an APIC controller, export previously imported cable plans to a
file, and compare cable plans.

More advanced users can use the Cable Plan to easily build a cable plan XML
file, query a cable plan, and modify a cable plan.


.. _tut-using:

****************************
Using the Cable Plan module
****************************


.. _tut-invoking:

Invoking 
========================

The Cable Plan module is imported from the  :file:`cable.py`.::

  from cable import CABLEPLAN

When you want to create a cable plan from the current running topology
of an ACI fabric, simply do the following::
    
  cp = CABLEPLAN.get(session)

Where ``session`` is an ACI session object generated using the
``acitoolkit``.  ``cp`` will be the cable plan object.

You can export that cable plan by opening a file and calling the
``export()`` method as follows::
  
  cpFile = open('cableplan1.xml','w')
  cp.export(cpFile)
  cpFile.close()

The cable plan will be written to the :file:`cableplan1.xml`.

Reading an existing cable plan xml file is equally easy.::

  fileName = 'cableplan2.xml'
  cp2 = CABLEPLAN.get(fileName)

Note that you don't have to explicitly open or close the file.  The
``get(fileName)`` method will take care of that for you.

Comparing cable plans is one of the more interesting cabablilities of
the Cable Plan module and is very easy to do using the "difference"
methods.  When generating the difference between two cable plans, the
module will return those items that exist in the first cable plan, but
not in the second.

For example, assume that in the above example, the second cable plan
read from the :file:`cableplan2.xml` does not have switch "Spine3"
and the first cable plan does have it.  The following example will
print all of the switches in the first cable plan and not in the
second.::
  
  missing_switches = cp1.difference_switch(cp2)
  for switch in missing_switches :
      print switch.get_name()

This will print the following::
  
  Spine3

Similiarly, the following example will print all of the missing
links::

  missing_links = cp1.difference_link(cp2)
  for link in missing_links :
      print link.get_name()

To understand all of the differences between two cable plans it is
necessary to compare them in both directions ::
  
  missing_links = cp1.difference_link(cp2)
  extra_links = cp2.difference_link(cp1)
  print 'The following links are missing from the second cable plan'
  for link in missing_links :
      print link.get_name()
  print 'The following links are extra links in the second cable plan'
  for link in extra_links:
      print link.get_name()

If multiple ports are specified in the link object with minPorts and
maxPorts attributes (see Cable Plan XML Syntax below), it is possible
that a link object in the first cable plan is only partially met by
the link objects in the second cable plan.  The ``remaining_need()``
method of the CpLink object.::
  
  missing_links = cp1.difference_link(cp2)
  for link in missing_links :
     print 'Link',link.get_name(), 'still
     needs',link.remaining_need(),'links to satisfy its mimimum
     requirement'

There is a similar method, ``remaining_avail()`` that returns the
number of physical links the link object could match.

The ``remaining_need()`` and ``remaining_avail()`` values are reset when
the ``difference_link()`` method is invoked.

It might be necessary to compare cable plans when the names of the
switches are different, but the topologies are the same.  This can
easily done by simply changing the names of the switches that are
different and then doing the comparisons.::
  
  switch = cp1.get_switch('Spine1')
  switch.set_name('Spine1_new_name')

This will automatically also fix-up all of the link names that are
connected to the switch whose name is being changed.  Note that this
is also an easy way to change the name of a switch in a cable plan
file.  Simply read it in, change the switch name, and export it out.
The following example will read in :file:`cable_plan2.xml`, change the
name of 'Leaf1' to 'Leaf35', and then export to the same file the
modified cable plan::
  
  fileName = 'cable_plan2.xml'
  cp2 = CABLEPLAN.get(fileName)
  switch = cp2.get_switch('Leaf1')
  switch.set_name('Leaf35')
  f = open(fileName,'w')
  cp2.export(f)
  f.close()

Cable Plan XML Syntax 
========================
The cable plan XML looks like the following ::

    <?xml version="1.0" encoding="UTF-8"?>
    <?created by cable.py?>
    <CISCO_NETWORK_TYPES version="None" xmlns="http://www.cisco.com/cableplan/Schema2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="nxos-cable-plan-schema.xsd">
       <DATA_CENTER networkLocation="None" idFormat="hostname">
          <CHASSIS_INFO sourceChassis="spine1" type="n9k">
             <LINK_INFO sourcePort="eth2/35" destChassis="leaf1" destPort="eth1/50"/>
             <LINK_INFO sourcePort="eth2/3" destChassis="leaf3" destPort="eth1/50"/>
             <LINK_INFO sourcePort="eth2/2" destChassis="leaf2" destPort="eth1/50"/>
          </CHASSIS_INFO>
          <CHASSIS_INFO sourceChassis="spine2" type="n9k">
             <LINK_INFO sourcePort="eth2/1" destChassis="leaf1" destPort="eth1/49"/>
             <LINK_INFO sourcePort="eth2/3" destChassis="leaf3" destPort="eth1/49"/>
             <LINK_INFO sourcePort="eth2/2" destChassis="leaf2" destPort="eth1/49"/>
          </CHASSIS_INFO>
       </DATA_CENTER>
    </CISCO_NETWORK_TYPES>

The CHASSIS_INFO tag normally identifies the spine switches and the
leaf switches are contained in the LINK_INFO.  When the XML is read
in, both leaf and spine switch objects will be created and the
``get_switch()`` and ``get_link()`` methods can be used to access
them.

The LINK_INFO syntax also allows more flexible and loose
specifications of the links.  If the ``sourcePort`` or ``destPort``
attributes are left out, then any port on that corresponding switch
can be used.  The ``sourcePort`` and ``destPort`` attributes can also
take port ranges, and lists as shown here::

  <LINK_INFO sourcePort="eth1/1-eth1/15, eth1/20" destChassis =
  "leaf3"/>

In addition, you can add ``minPorts`` and ``maxPorts`` attributes to
specify the minimum number of ports or maximum number of ports when
multiple are defined.::

  <LINK_INFO sourcePort="eth2/3, eth3/4 - eth3/10",
  destChassis="leaf2", destPort="eth1/1 - eth1/8", minPorts=3,
  maxPorts=5>

If minPorts is omitted, the default will be 1. If maxPorts is
omitted, the default will be unlimited.

When comparing two cable plans using the ``difference_link()`` method,
if the minimum number of links in the first cable plan can be met with
second cable plan, then the difference will show no difference.  Note
that it is possible that requirements of several links specified in
one cable plan may be met by one or more links in the other.
Basically, the difference is calculated such that the minimum
requirements of the first cable plan are met without exceeding the
maximum capacity of the second cable plan.


.. automodule:: cable
    :members:
    :undoc-members:
    :show-inheritance:
