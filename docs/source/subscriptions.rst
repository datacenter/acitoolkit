Getting APIC objects
====================

With the acitoolkit, it is possible to get objects from the APIC
either on demand or through object event subscriptions.  In most
cases, getting the objects on demand will be sufficient.  However, in
cases where action needs to be taken immediately or to avoid frequent
polling of the APIC, event subscriptions can be used.

Objects on demand
-----------------

Getting objects on demand is fairly straightforward.  Each class that
allows getting objects from the APIC has a ``get`` class method.  This
method will return a list of objects belonging to that class type and
will be retrieved from the APIC immediately upon calling.

Since the acitoolkit can be used to control multiple APICs at the same
time, the ``Session`` class instance representing the connection to
the desired APIC is also passed.

An example is shown in the code snippet below.::

   tenants = Tenant.get(session)
   for tenant in tenants:
       print tenant.name

Event subscriptions
-------------------

Event subscriptions allow immediate notification when an object is
created, modified, or deleted.  Events will be received only for
classes or instances that are subscribed.

Class subscriptions
~~~~~~~~~~~~~~~~~~~

To create a class subscription, the class method ``subscribe`` is
called on the desired class along with the appropriate ``Session``
class instance.  This is shown in the code snippet below using the
``Tenant`` class as the example.::

    Tenant.subscribe(session)
    
To check an event has arrived, the method ``has_events`` can be called
on the subscribed class.::

    Tenant.has_events(session)

If there is an event waiting, this will return ``True``.

.. note:: While this may look like it requires polling the APIC, it is
	  actually just checking a local event receive queue.  This
	  event queue is populated by a separate thread receiving
	  events from the APIC.  Thus, calling ``has_event`` will not
	  result in additional communication with the APIC so that
	  this call can be run in a tight loop with minimal overhead
	  and/or spun into a seperate thread if desired.

To retrieve the event, a call is made to the ``get_event`` method as
shown below.::

    event = Tenant.get_event(session)

This will return a instance of the object with the appropriate
settings indicating the change.  For instance, if the ``Tenant`` named *Bob*
is deleted, the event will return a ``Tenant`` instance with the name set
to *Bob* and it will be marked as *deleted*.

To no longer receive events for this particular class, the class
method ``unsubscribe`` can be called.  This will cause the
subscription to be removed from the APIC.::

    Tenant.unsubscribe(session)  
	  
Under the covers, the event subscriptions use a web socket to
communicate with the APIC to receive the events.  The events are then
collected by a thread and placed into an event queue that is then
queried by user code.  Event subscriptions are refreshed automatically
by the toolkit using a separate thread.

Instance subscriptions
~~~~~~~~~~~~~~~~~~~~~~

Instance subscriptions are the same as class subscriptions except that
the events are limited to only that particular object instance such
as::

    bob = Tenant('bob')
    bob.subscribe(session)
    bob.has_events(session)
    event = bob.get_event(session)


A more useful example would be the following code which will wait for
an event for the instance of ``Tenant`` with the name *Bob* and then
print a message if the instance was deleted.::

    bob = Tenant('Bob')
    bob.subscribe(session)
    while True:
        if bob.has_events(session):
	    bobs_event = bob.get_event(session)
	    if bobs_event.is_deleted():
	        print 'Bob was deleted'

