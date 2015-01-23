Visualization Examples
======================

This directory contains a number of visualization examples that can be
used to display information collected using the ``acitoolkit``.  Many of
the examples are meant to run alongside the ``ACI Endpoint Tracker``
application and interact with the MySQL database that the ``ACI Endpoint
Tracker`` populates.  Most of the visualization examples are interactive.

Installation
------------

To run the visualizations, the python package ``Flask`` is required.
This can be installed using ``pip`` as follows::

    pip install flask

It is also recommended that the ``ACI Endpoint Tracker`` is installed.


Usage
-----

Run the visualizations as follows (supplying your own MySQL credentials)::

    python acitoolkit-visualizations.py --mysqlip 127.0.0.1 --mysqllogin root --mysqlpassword password

Alternatively, you can create a `credentials.py` file in the same
directory with the following::

    MYSQLIP='127.0.0.1'
    MYSQLLOGIN='root'
    MYSQLPASSWORD='password'

If the `credentials.py` file is used, run the visualizations as
follows::

    python acitoolkit-visualizations.py

Once the visualizations are running, you should see the following
displayed::

     * Running on http://127.0.0.1:5000/
     * Restarting with reloader


Simply point your favorite web browser to the following URL and explore::

    http://127.0.0.1:5000/
