ACI Endpoint Tracker
====================

The ACI Endpoint Tracker application tracks all of the attachment,
detachment, and movement of Endpoints on the ACI fabric.  It stores
all of this activity in a database that allows administrators to
examine and query the data to gain deep visibility into what is
happening in the network.  The database also provides a foundation for
visualization and querying tools.

Some sample questions that can be answered with the ACI Endpoint Tracker:

* What are all of the current Endpoints on the network ?
* Where is a specific Endpoint ?
* What was connected to the network last Thursday
  between 3:30 and 4:00 ?
* What are all of the Endpoints belonging to a given Tenant ?
* What Endpoints are on this subnet ? 
* What is the history of a given Endpoint (i.e. movement, etc.)?
  
Installation
------------

acitoolkit
~~~~~~~~~~
This application uses the acitoolkit.  The installation steps for the
acitoolkit can be found at `<http://datacenter.github.io/acitoolkit/>`_.

MySQL database
~~~~~~~~~~~~~~
The ACI Endpoint Tracker uses the open source MySQL database to store
the Endpoint data.  MySQL is installed separately and the installation
steps are dependent on the platform.  It is recommended that MySQL be
installed in the same machine as the ACI Endpoint Tracker.

MySQL installation instructions for most platforms can be found here:
`MySQL installation instructions <http://dev.mysql.com/doc/refman/5.7/en/installing.html>`_.

For Ubuntu, the installation instructions can be found here:
`Ubuntu MySQL installation instructions
<https://help.ubuntu.com/12.04/serverguide/mysql.html>`_.

Once the above package is installed, you should verify that the
MySQL database is running.  In Linux and Mac OS X, this can be done by
entering the following command::

    mysqladmin -u root -p status

If the database is running, the output should be similar to below::

    Uptime: 358118  Threads: 3  Questions: 5767  Slow queries: 0
    Opens: 109  Flush tables: 1  Open tables: 61  Queries per second
    avg: 0.016
    
If the database is not running, the output should be similar to
below::

    mysqladmin: connect to server at 'localhost' failed

MySQL Connector
~~~~~~~~~~~~~~~~

In order for the ACI Endpoint Tracker to communicate with the MySQL
database, the MySQL Connector/Python must be installed.  This is
available for most platforms at
`<http://dev.mysql.com/downloads/connector/python/>`_.


Flask
~~~~~
Flask is required for the optional GUI frontend.  The installation
steps for Flask can be found at `<http://flask.pocoo.org/>`_.

.. _credentials:

Usage
-----

The ACI Endpoint Tracker serves as a conduit between the APIC and the
MySQL database. It requires login credentials to both, namely the
username, password, and IP address or URL.

The user can choose any **one** of 3 ways to specify the login
credentials.  If multiple ways are used, they are taken in the
following priority order:

1. **Command Line Arguments**

   The login credentials can be passed directly as command line
   arguments.  The command is shown below::

     python aci-endpoint-tracker.py [[ -u | --url] <apicurl>]
     [[ -l | --login ] <apicusername>] [[ -p | --password ]
     <apicpassword>] [[ -i | --mysqlip ] <mysqlip> [[ -a
     | --mysqladminlogin ] <mysqladminlogin] [[ -s | --mysqlpassword ]
     <mysqlpassword> ]

   where the parameters are as follows:
   
   +----------------+------------------------------------------------+
   +apicurl         | The URL used to communicate with the APIC.     |
   +----------------+------------------------------------------------+
   +apicusername    | The username used to login to the APIC.        |
   +----------------+------------------------------------------------+
   +apicpassword    | The password used to login to the APIC.        |
   +----------------+------------------------------------------------+
   +mysqlip         | The IP address of the MySQL DB host.           |
   +----------------+------------------------------------------------+
   +mysqladminlogin | The username used to login to the MySQL DB     |
   +----------------+------------------------------------------------+
   +mysqlpassword   | The password used to login to the MySQL DB     |
   +----------------+------------------------------------------------+

   An example would be the following::

     python aci-endpoint-tracker.py -u https://172.35.200.100 -l
     admin -p apicpassword -i 127.0.0.1 -a root -s mysqlpassword
  
2. **Environment Variables**

   The login credentials can be pulled from environment variables in
   operating systems such as Mac OS X and various Linux distributions.

   The environmental variables are as follows::

       APIC_URL
       APIC_LOGIN
       APIC_PASSWORD
       APIC_MYSQLIP
       APIC_MYSQLLOGIN
       APIC_MYSQLPASSWORD

   These variables should be set to the correct value.  Setting the
   environment variable is OS dependent.  For example, in Mac OS X,
   environment variables can be set in your ``~/.bash_profile`` as
   follows::

     export APIC_URL=https://172.35.200.100
     export APIC_LOGIN=admin
     export APIC_PASSWORD=apicpassword
     export APIC_MYSQLIP=127.0.0.1
     export APIC_MYSQLLOGIN=root
     export APIC_MYSQLPASSWORD=mysqlpassword
     
   If environmental variables are used to specify the credentials,
   then the following command will execute the ACI Endpoint Tracker.::

       python aci-endpoint-tracker.py
     
3. **Importing a credentials.py file**

   Alternatively, the login credentials can be pulled from a python
   file named ``credentials.py``. In this file, it is assumed that
   the following variables will be set appropriately for your
   environment.::

       URL = 'https://172.35.200.100'
       LOGIN = 'admin'
       PASSWORD = 'apicpassword'
       MYSQLIP = '127.0.0.1'
       MYSQLLOGIN = 'root'
       MYSQLPASSWORD = 'mysqlpassword'

   If a credentials.py file is used to specify the credentials,
   then the following command will execute the ACI Endpoint Tracker.::

       python aci-endpoint-tracker.py


What's it doing ?
-----------------

Once the ACI Endpoint Tracker is running, it will connect to the APIC
and pull all of the existing static and dynamic endpoints that are
currently connected to the fabric along with the relevant associated
information such as:

* Tenant, Application Profile, and EPG membership
* Interface to which it is connected
* Timestamp of when it connected to the fabric

This data is then inserted into a database called ``acitoolkit`` that
the ACI Endpoint Tracker will create.  Within the database, it creates
a single table called ``endpoints`` where all of the endpoint
information will be inserted.
  
Once all of this information is collected, the ACI Endpoint Tracker
subscribes through the web socket interface to any updates to both
static and dynamic endpoints.  When these updates such as endpoint
attachment, detachment, or move occurs, the database will be
immediately updated with the live data.

Note that updates to the database will only occur when the ACI
Endpoint Tracker is running.

Direct Database Query
---------------------

Once the data is in the database, the MySQL client can be used to
query the data directly.  Using this method, the full power of SQL can
be used to provide deep insight into the network endpoint behavior.

To connect to the MySQL database, you can execute the following
command locally on the same host where the database is running.::

    mysql -u <mysqllogin> -p

The client will then prompt for the MySQL database password.  After
successfully entering the password, the MySQL prompt will come up as
shown in the screenshot below::

    $ mysql -u root -p
    Enter password: 
    Welcome to the MySQL monitor.  Commands end with ; or \g.
    Your MySQL connection id is 145
    Server version: 5.6.22 MySQL Community Server (GPL)

    Copyright (c) 2000, 2014, Oracle and/or its affiliates. All rights reserved.

    Oracle is a registered trademark of Oracle Corporation and/or its
    affiliates. Other names may be trademarks of their respective
    owners.

    Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

    mysql> 

At this point, the ``acitoolkit`` database should be available.  The
available databases can be shown by entering the following command at
the prompt.::

    mysql> show databases;

A sample output is shown below.::

    +--------------------+
    | Database           |
    +--------------------+
    | information_schema |
    | acitoolkit         |
    | mysql              |
    | performance_schema |
    | test               |
    +--------------------+
    5 rows in set (0.00 sec)

To switch to the ``acitoolkit`` database, enter the following
command.::

    mysql> use acitoolkit;

The endpoint data is stored in a single table called ``endpoints``.
You can then display all of the endpoint data by the following
query (shown with a snippet of the output).::

    mysql> select * from endpoints;
    +-------------------+---------------+--------------+--------------+-------------+----------------+---------------------+---------------------+
    | mac               | ip            | tenant       | app          | epg         | interface      | timestart           | timestop            |
    +-------------------+---------------+--------------+--------------+-------------+----------------+---------------------+---------------------+
    | 74:26:AC:76:80:5B | 192.168.1.133 | Tenant1      | Application1 | WEB         | VPC1           | 2014-12-09 19:08:27 | 0000-00-00 00:00:00 |
    | 00:50:56:94:D8:73 | 0.0.0.0       | Tenant1      | Application1 | WEB         | eth 1/102/1/12 | 2015-01-13 23:48:15 | 0000-00-00 00:00:00 |
    | 00:50:56:94:07:7E | 0.0.0.0       | Tenant1      | Application1 | WEB         | eth 1/103/1/11 | 2014-12-19 00:58:16 | 0000-00-00 00:00:00 |
    | 00:50:56:94:9A:1C | 192.168.0.5   | Tenant5      | Application1 | USER        | eth 1/102/1/12 | 2015-01-05 15:29:13 | 0000-00-00 00:00:00 |
    | 00:50:56:94:F3:CD | 0.0.0.0       | Tenant5      | Application1 | USER        | eth 1/102/1/12 | 2015-01-13 23:49:33 | 0000-00-00 00:00:00 |
    | 00:50:56:94:17:5E | 0.0.0.0       | Tenant5      | Application1 | WEB         | eth 1/102/1/12 | 2015-01-10 01:55:40 | 0000-00-00 00:00:00 |
    | 00:50:56:94:A9:B5 | 10.0.0.5      | Tenant5      | Application1 | WEB         | eth 1/102/1/12 | 2015-01-05 15:29:13 | 0000-00-00 00:00:00 |
    | 00:50:56:94:93:6F | 0.0.0.0       | Tenant5      | Application1 | WEB         | eth 1/102/1/12 | 2015-01-10 01:55:40 | 0000-00-00 00:00:00 |


At this point, we can query the data using the SQL SELECT command.  If
you haven't used SQL before, you may want to spend some time learning
some of the basic syntax related to the SQL SELECT command as it forms
the basis for all queries in the database.

Here are just a few example queries that are possible.

Various fields can be used to filter the results.

    *Show all of the endpoint information for a specific tenant*::
    
        mysql> select * from endpoints where tenant='cisco';

    *Show all of the endpoints for a given EPG within a certain tenant*::

        mysql> select * from endpoints where tenant='cisco' and epg='WEB';

    *Show all of the endpoints that were on the network on 2014-12-25*::

        mysql> select * from endpoints where timestart <= '2014-12-25'
	and timestop > '2014-12-24';

    *Show all of the history (attach, detach, move) for a particular
    endpoint*::

        mysql> select * from endpoints where ip='10.1.1.1' and
	tenant='cisco';

Output can be limited to certain fields

    *Show the current location of a given endpoint*::

        mysql> select interface from endpoints where ip='10.1.1.1' and
	tenant='cisco';

Unique fields can be shown using the ``distinct`` keyword.

    *Show the EPGs with active endpoints on 2014-12-25*::

        mysql> select distinct tenant,app,epg from endpoints where
	timestart <= '2014-12-25' and timestop > '2014-12-24';


Counts can be provided for filtered data using the ``count`` keyword.

    *Show the number of Endpoints active on 2014-12-25*::

        mysql> select count(*) from endpoints where timestart <=
	'2014-12-25' and timestop > '2014-12-24';

Wildcarding can be used with the ``%`` wildcard.

    *Show the endpoints belonging to a given subnet*::

        mysql> select * from endpoints where ip like '10.10.%';

  
GUI FrontEnd
------------

In addition to the very powerful MySQL interface, there is also a
GUI frontend that allows quick simple searching on the database using
a web browser.  The GUI frontend leverages the `DataTables
<http://www.datatables.net/>`_ package.

Demo
~~~~
The usage of this GUI should be fairly intuitive and a
live demo with fake endpoint data can be found at the link below.
Please give it a try, specifically the Search function to get a feel
for how it works.

`ACI Endpoint Tracker GUI Demo <http://datacenter.github.io/acitoolkit/docsbuild/html/aci-endpoint-tracker-gui.html>`_

For instance, to see all of the endpoints for tenant 'cisco' simply
type cisco in the Search box. To narrow the search further to the
endpoints owned by tenant 'cisco' on leaf 102, type 'cisco 102' in the
Search box.  Also, each column can be sorted by clicking on the arrows
found in each of the column headers.


Usage
~~~~~

To use the GUI front end locally on your own database, you simply need
to execute the ``aci-endpoint-tracker-gui.py`` file assuming you have
installed the Flask package as mentioned in the `Installation`_
section.

The GUI front end deals exclusively with the MySQL database and does
not communicate with the APIC, so it only requires the MySQL
credentials.  These can be passed in the same manner as described for the ACI
Endpoint Tracker `credentials`_. ::

    python aci-endpoint-tracker-gui.py -i 127.0.0.1 -a root -s
    mysqlpassword

It should be noted that while the GUI does not communicate with the
APIC, as long as the Endpoint Tracker is running, the database will
contain the live data for the APIC.

License
-------
Copyright 2015 Cisco Systems, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
