Object Model
============

The acitoolkit object model is divided into 3 sub-areas

* Application Topology Object Model
* Interface Object Model
* Physical Topology Object Model

Application Topology
--------------------
The acitoolkit defines the fabric configuration using a set of
policies that describes the application logical topology.  This
logical topology is defined using a set of objects that are contained
according to the below class diagram.

.. image:: apptopo.png
	   
**Tenant** is the root class within the acitoolkit object model
hierarchy.  All of the application topology configuration occurs
within a Tenant.

**AppProfile** is the Application Profile class.  It contains the
configuration for a given application.

**EPG** is the Endpoint Group class.  This is the object for
defining configuration that is applied when endpoints connect to the
fabric.

**Context** is the class representing an L3 namespace (roughly, a
traditional VRF in Cisco terminology).

**BridgeDomain** is the class representing an L2 forwarding domain
(roughly, a traditional VLAN).  It is associated with a single
Context.

**Subnet** is the class representing an L3 subnet.  It is associated
with a single BridgeDomain.

**OutsideEPG** is the class representing an EPG that connects to the
world outside the fabric.  This is where routing protocols such as
OSPF are enabled.

**Contracts** define the application network services being provided
and consumed by EPGs.  EPGs may provide and consume many contracts.

**Taboos** define the application network services that can never be
provided or consumed by EPGs.

**FilterEntry** contained within either a Contract or a Taboo.
Defines the traffic profile that the Contract or Taboo applies.

Interface Object Model
----------------------
Interfaces provide the linkage between the application logical
topology and the underlying physical network topology.  The Interface
set of classes are connected through a series of attachment
relationships as shown in the class diagram below.

.. image:: interfacemodel.png

**Interface** class represents the **Physical Interfaces**.  These are the
objects that link the logical topology with the physical world.  These
objects represent the access ports on the leaf switches.  These are
the interfaces that the endpoints will physically attach.

.. sidebar:: Link aggregation

   A `link aggregation` is a logical link layer interface composed of
   one or more physical interfaces. Commonly referred to as
   Etherchannel or PortChannel.
   

**PortChannel** class represents the logical aggregated ethernet port
formed by Link Aggregation.  This is done by creating a PortChannel
instance and attaching one or more Interface instances to it.  When
interfaces belonging to 2 separate switches are assigned to the same
PortChannel, this is referred to as a VPC or Virtual Port Channel. In
the acitoolkit, VPCs are also represented by the PortChannel class.

**L2Interface** class represents the logical L2 network attachment on
an Ethernet interface.  In this case, the Ethernet interface could be
an Interface class instance or PortChannel class instance as both are
considered representations of link layer Ethernet interfaces.

Multiple logical L2 network attachments can occur on the same Ethernet
interface.  When this occurs, the L2Interface instances must use
different encapsulation identifiers and/or different encapsulation
types.  The valid encapsulation types are:

* VLAN
* VXLAN
* NVGRE

**L3Interface** class represents the logical L3 network attachment on
an L2Interface.  The L3Interface instance is where the IP address
resides.

**OSPFInterface** class represents the logical router interface that
routes from the L3Interface instance.  It contains the OSPF-specific
interface configuration.

Physical Topology
-----------------

`Need a diagram of the physical classes`

`For those who have read this far, still working on this page.  An
update should be coming soon.`





