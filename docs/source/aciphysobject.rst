aciphysobject module
====================

.. automodule:: aciphysobject
    :members:
    :undoc-members:
    :show-inheritance:

Future Work
-------------------------
Future work items to be added to aciphysobject include:

* Add a stats sub-object.  This object would provide access to all the
  relevant statistics gathered by the system.  An example syntax of
  its use would be something like:

    >>> interface.stats.get()

   >>> counter = interface.stats('foobar')

* Add an events sub-oject.  This would work similarly to the stats
  object.

* Add a top level object called Topology that would have Pod as its
  child.  This object would also contain devices attached to the
  fabric, so called loose nodes, external links, and discovered
  end-points.


