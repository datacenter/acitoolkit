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
* :ref:`ingrStorm <ingrStorm-label>`


*******************
Accessing Stats
*******************

Each statistic family is described in detail below and can be accessed
via the ``stats`` object contained in the ``Interface`` object.  

You first use the get() method to read the stats from the APIC
controller.::

  stats = interface.stats.get()

This will return a data structure that will allow each counter
to be referenced by its name (see list above), a
granularity, and an epoch number in the following manner::

  counter = stats[<stats_family>][<granularity>][<epoch>][<counter_name>]

For example, if you wanted to show the per day total of ingress,
unicast packets from the previous day you would do the following::

  stats = interface.stats.get()
  print stats['ingrPkts']['1h'][1]['unicastPer']

The specific counter names can be found at
:ref:`statistics-detail-label`.

Each counter family has an interval start and end value as well which
can be used to understand exactly when the counters were gathered.::

  print 'start', interface.stats['ingrPkts']['1h'][1]['intervalStart']
  print 'end', interface.stats['ingrPkts']['1h'][1]['intervalEnd']
   
One thing to note about accessing the stats is that if a particular
counter is not currently being kept by the APIC controller, that
particular counter will not be returned by the get() method.  This
means that you should either test for its existence before accessing
it, or use the standard python dictionary get method to 
return a default value that your code can handle::

  print stats['ingrPkts']['1h'][1].get('unicastPer',0)

A typical example of counters that may not exist would be for an
epoch that is not being retained or a granularity that is not 
be gathered.

One issue with the above is that some counters are floating point, some
are integers and some are timestamps.  Returning a default of
zero can lead to inconsistent formatting.  To work around this problem
use the ``retrieve()`` method that will return 
the coutner value or a default value that is consistent.  The format
of the retrive method is as follows::

  interface.stats.retrieve(<stats_family>,<granularity>,<epoch>,<counter_name>)

The get() method will load the counter values and then they are accessed by
the retrieve method as follows::

  interface.stats.get()
  print interface.stats.retrieve('ingrPkts','1h',1,'unicastPer')

Note that the result of the ``get()`` method was not used.  It did cause
a read of the stats from the APIC which are then stored in the
``interface.stats`` object.  After that, the ``interface.stats.retrieve()``
method will access those previously read counters.  The ``retrieve()``
method will not refresh the counters.

aci-show-interface-stats.py
----------------------------

The interface stats can also be accessed via the simple python script
``aci-show-interface-stats.py``.  This script has a couple of display
options to customize the output.

A simple run of the script will display each interface in the network
and a couple of selected stats for each::

  python aci-show-interface-stats.py

The default display is for the ``5min`` granularity and the current,
i.e. 0, epoch.  An alternative granularity can be selected with the
``-granularity`` command line option.::

  python aci-show-interface-stats.py -granularity 1h

The epoch can be specified with the ``-epoch`` option.::

  python aci-show-interface-stats.py -granularity 1h -epoch 3

A specific interface can be specified with the ``-interface`` option.  
This might be useful
if there are a large number of interfaces.::

  python aci-show-interface-stats.py -g 1h -e 3 -interface 1/201/1/1

Note that we are also showing the abbreviated form of the other
command line options.  The above will show stats for pod 1, switch
201, slot 1, port 1.

If all of the stats for a given interface are desired, the ``-full``
option should be used.

  python aci-show-interface-stats.py -g 1h -e 3 -i 1/201/1/1 -full

This last option will show only those stats that have been collected
according to the monitoring policy.  Also, note that this last option
only works when the ``-interface`` option is also used.






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



