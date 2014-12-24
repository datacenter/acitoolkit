############## 
Statistics
############## 


.. toctree::
   :maxdepth: 4

Statistics are gathered at each Interface according to the monitoring
policy referenced by that Interface. See :ref:`Monitor Policy <monitor_policy_label>` for
details of the monitoring policy.

This section describes the statistic counters themselves.

********************
Statistic Families
********************

The statistics are broken into multiple statistic families and each
family consists of a set of specific counters, rate values, and
timestamps.

An enumerated list of statistic families is found in the MonitorStats
class and can be found as follows::

    >>>import acitoolkit.acitoolkit as ACI
    >>>statistic_family_list = ACI.MonitorStats.statsFamilyEnum
    >>>for statistic_family in statistic_family_list:
    ...  print statistic_family

The families are as follows:

* :ref:`egrbytes <egrBytes-label>`
* :ref:`egrPkts <egrPkts-label>`
* :ref:`egrTotal <egrTotal-label>`
* :ref:`egrDropPkts <egrDropPkts-label>`
* :ref:`ingrBytes <ingrBytes-label>`
* :ref:`ingrPkts <ingrPkts-label>`
* :ref:`ingrTotal <ingrTotal-label>`
* :ref:`ingrDropPkts <ingrDropPkts-label>`
* :ref:`ingrUnkBytes <ingrUnkBytes-label>`
* :ref:`ingrUnkPkts <ingrUnkPkts-label>`

Each statistic family is described in detail below and can be accessed
via the ``stats`` object contained in the ``Interface`` object.  Each
stats family is referenced by its name (see list above), a
granularity, and an epoch number in the following manner::

  stats = interface.stats[<stats_family>][<granularity>][<epoch>]

This returns a dictionary of counter name, value pairs.

For example, if you wanted to show the per day total of ingress,
unicast packets from the previous day you would do the following::

  print interface.stats['ingrPkts']['1h'][1]['unicastPer']

The specific counter names can be found at
:ref:`statistics-detail-label`.

Each counter family has an interval start and end value as well which
can be used to understand exactly when the counters were gathered.::

  print 'start', interface.stats['ingrPkts']['1h'][1]['intervalStart']
  print 'end', interface.stats['ingrPkts']['1h'][1]['intervalEnd']
   

********************
Granularity
********************


The ``<granularity>``, also called "interval",  must be one of:

* 5min
* 15min
* 1h
* 1d
* 1w
* 1mo
* 1qtr
* 1year

An enumerated list of granularities is found in the CollectionPolicy
class and can be found as follows::

    >>>import acitoolkit.acitoolkit as ACI
    >>>granularity_list = ACI.CollectionPolicy.granularityEnum
    >>>for granularity in granularity_list:
    ...  print granularity

********************
Epoch
********************

The ``<epoch>`` is an integer representing which set of historical
stats you want to reference.  Epoch ``0`` is the current epoch which
has not yet completed.  Epoch ``1`` is the most recent one and so on.
The length of each epoch is determined by the granularity. 

The number of epochs available will be determined by the retention
policy and granularity specified in the monitoring policy and how long
they have been in place.

For example, if the monitoring policy for a particular statistics
family has a granularity of ``5min`` and a retention policy of ``1h``
and it has been in place for more than one hour, then there will be a
total of 13 epochs, 0 through 12.  Epoch 0 will be the one currently
active.  Epoch 1 will be for the previous 5 minute interval.  Epoch 2
will be for the 5 minute interval previous to epoch 1 and so on.  At
the beginning of the current Epoch, the values in Epoch 0 will be
distorted because they are only for a fraction of that epoch
(potentially a zero fraction) and the other 12 will represent an hour
of history.

****************************************
Update Frequency for current epoch
****************************************

The current epoch, epoch 0, will be updated as it occurs, i.e. in near
real-time.  The interval that it updates depends on the epoch, or interval,
granularity.

==================  =====================
Granularity          Update frequency
==================  =====================
5min                Every 10 seconds
15min               Every 5 minutes
1h                  Every 15 minutes
1d                  Every hour
1w                  Every day
1mo                 Every day
1qtr                Every day
1year               Every day
==================  =====================



