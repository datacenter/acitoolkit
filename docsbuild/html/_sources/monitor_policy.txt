.. _monitor_policy_label:

Monitor Policy
--------------------
The monitor policy, :py:class:`acitoolkit.acitoolkit.MonitorPolicy`, defines what 
statistical information is gathered
and how long historical information is kept.  It is also where events
that are triggered by these stats are configured (to be supported).

Multiple monitoring policies can be defined and various APIC objects
then reference the monitoring policy they are using.  For example,
a ``l1PhysIf`` object in the APIC has an attribute called ``monPolDn``
which is the distinguishing name of the monitoring policy that it
references.  In the toolkit, the ``l1PhysIf`` object is represented by
the :py:class:`acitoolkit.acitoolkit.Interface` class.

There are two types of monitoring policies:``fabric`` and ``access``
and they are identified by the ``policyType`` attribute of the monitor
policy.  The ``fabric`` type is used to monitor ACI fabric interfaces
while the ``access`` type is used to monitor ACI access or ``infra``
interfaces.  The same class is used for both types of monitoring
policies in the acitoolkit.

The monitoring policy is a hierarchical policy consisting of monitor
policy class, :py:class:`acitoolkit.acitoolkit.MonitorPolicy`, at the
top with the following classes below it:
:py:class:`acitoolkit.acitoolkit.MonitorTarget`,
:py:class:`acitoolkit.acitoolkit.MonitorStats`, and
:py:class:`acitoolkit.acitoolkit.CollectionPolicy`.

The following diagram shows their relationship.

.. image:: monitorpolicyhier.png

**CollectionPolicy** is where the actual collection policy is
defined.  What it applies to is determined by where it is in the
monitoring policy hierarchy.  The three most important attributes of the
collection policy are ``adminState``, ``granularity`` and ``retention``.  Additional
attributes are a ``name`` and ``description`` which are optional and
can be set using the ``setName(<name>)`` and
``setDescription(<description>)`` methods respectively.

The ``adminState`` attribute can be ``enabled``, ``disabled`` or
``inherited``.  If ``enabled``, that granularity of statistics will be
gathered.  If ``disabled``, that granularity of statistics will not be
gathered and *neither will any larger granularities*.  This is because
the statistics gathered at one granularity are then rolled up into the
larger granularity.  If you don't gather the finer one, then there is
no data to roll up to the coarser one.

If the ``adminState`` is set to ``inherited``, the current object does
not determine the ``adminState``.  Instead, the ``adminState`` of the
collection policy of the next higher level in the monitoring policy
hierarchy will be used.  This means that the ``adminState`` at the
highest level of the monitoring policy *cannot* be set to
``inherited`` because there is no higher level to inherit from.

The ``granularity`` attribute can have one of the following values:

====== ==============
 Value           Meaning
====== ==============
5min          5 minutes
15min        15 minutes
1h              1 hour
1d              1 day
1w              1 week
1mo           1 month
1qtr           1 quarter
1year         1 year
====== ==============

This is the time interval over which the stats are initially gathered
and the interval for which they are kept.

For example, if the granularity is ``15min``, then the cumulative
stats for that granularity will start at 0 at the beginning of the 15
minute interval and will accumulate during the interval.  At the end
of the interval, the final values will be moved to the historical
statistics if the ``retention`` attribute is so configured.  The rate
statistics will be the rate during the 15 minute interval and the rate
averages will be the average rate during the 15 minute interval.

Statistics are only kept for granularities that have an adminState of
``enabled`` either explicitly or through inheritance and no finer
(smaller) granularities are ``disabled``.

The ``retention`` attribute determines how long historical data at a
given granularity is kept.  It can have one of the following values:

==========     ============================== 
 Value                      Meaning
==========     ==============================
none                      Do not keep historical data
inherited                Use the policy from the next  higher level of hierarchy
5min                     5 minutes
15min                   15 minutes
1h                         1 hour
1d                         1 day
1w                        1 week
10d                       10 days
1mo                      1 month
1qtr                       1 quarter
1year                     1 year
2year                     2 years
3year                    3 years
==========     ==============================

It does not make any sense to have a retention period that is less
than the granularity, however this is not checked for in the
acitoolkit.

**MonitorStats** sets the scope for any collection policy under it.
The scope here is a family of statistics.  The possible scope values
are as follows:



============  ================== 
Value                        Description
============  ==================  
egrBytes                    Egress bytes
egrPkts                     Egress packets
egrTotal                    Egress total
egrDropPkts              Egress drop packets
ingrBytes                   Ingress bytes
ingrPkts                    Ingress packets
ingrTotal                   Ingress total
ingrDropPkts            Ingress drop packets
ingrUnkBytes            Ingress unknown bytes
ingrUnkPkts             Ingress unknown packets
============  ================== 

A more detailed description of the statistics can be found here.

The collection policies under the ``MonitorStats`` object determine
the default collection policy for the set of statistics selected by
the above scope.

Other attributes of the ``MonitorStats`` class are ``name`` and
``description`` which can be set with the ``setName(<name>)`` and
``setDescription(<description>)`` methods respectively.  Setting these
attributes is optional.

**MonitorTarget** sets the scope to a particular APIC target object
for all of the collections policies below it.  Currently, there is
only one APIC target object type supported and that is 'l1PhysIf'.
The ``scope`` attribute is where the target type is stored.
Support for additional target objects will be added as required.   The
``scope`` attributed is initialized when the MonitorTarget is created
and cannot be changed.

Other attributes of the ``MonitorStats`` class are ``name`` and
``description`` which can be set with the ``setName(<name>)`` and
``setDescription(<description>)`` methods respectively.  Setting these
attributes is optional.

**MonitorPolicy** is the root of the monitor policy hierarchy.  This
object must have ``name`` and ``policyType`` attribute.  The
``policyType`` must be either ``fabric`` or ``access`` and the name
must be unique for each ``policyType``.

The monitor policy will be referenced by its ``policyType`` and
``name`` by individual APIC objects.

The monitor policy contains the default collection policies as well as
any ``MonitorTarget`` objects that specify a more specific scope.

The monitor policy must contain a ``CollectionPolicy`` for each
granularity and the ``adminState`` and ``retention`` attributes of the
``CollectionPolicy`` cannot be ``inherited`` because they are at the
top of the inheritance tree.  When a MonitorPolicy object is created,
it will be initialized with the appropriate ``CollectionPolicy``
objects, which, in turn, will be set to a default administrative state
of ``disabled``.  This means that these polies *must* be overwritten
if stats should be collected.  They can either be explicitly replaced
with the ``add_collection_policy(<CollectionPolicy object>)`` method,
or implicitly replaced by more specific collection policies in the
inheritance hierarchy.
 

Policy Resolution
^^^^^^^^^^^^^^^^^^^

The ultimate policy that is applied to any counter is determined by
walking through the monitoring policy from the top down.  The
collection policy at each level
of the hierarchy determines how statistics will be kept for those
statistics that are *in scope*.  

For example, the collection policy
for each granularity is specified at the top of the hierarchy under
the MonitorPolicy object.  These collection policies will apply to all
statistics unless overwritten by a more specific policy under a
MonitorTarget object.

If there is a MonitorTarget object, it will set the scope for the
monitoring policy to be more specific for the collection policies
under it.  Initially, the only target supported is 'l1PhyIf' which is
for an ``Interface`` object.  Any collection policies under this
``MonitorTarget`` will override the corresponding collection policy under
the ``MonitorPolicy`` parent object.  It is possible that there are no
collection policies specified at this level.

If there are ``MonitorStats`` objects under the ``MonitorTarget`` object, they
will set the scope to be even more specific for the collection policies
under them.  Each ``MonitorStats`` object can have under it collection policies for
any of the granularities.






