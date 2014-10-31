Tutorial
========
This document is meant to give a tutorial-like overview of the
acitoolkit package.

Setting up the environment
--------------------------

This tutorial will walk you through installing the acitoolkit using
the sources so that you will be able to edit the samples and even the
acitoolkit source code if so desired.

Download
~~~~~~~~
First, we must download the acitoolkit.  This is best done using git,
but can be done by downloading the package as a zip.

If you have git installed, clone the repository using the following
command::

   git clone https://github.com/datacenter/acitoolkit.git

If git is not installed, you can download the acitoolkit as a zip file
instead.::

   wget https://github.com/datacenter/acitoolkit/archive/master.zip
   unzip master.zip

Install
~~~~~~~

.. sidebar:: Note
	     
   The directory may be named ``acitoolkit-master`` if
   downloaded as a zip file.

Next, cd into the created directory ::

   cd acitoolkit

and install the acitoolkit ::

   python setup.py install

Note that when installing on Mac or Linux, you will likely need to run
this as administrator so preface the command with the ``sudo`` keyword
as follows::

   sudo python setup.py install



Building a Simple Tenant Configuration
--------------------------------------

`Still need to write this section.  Work in progress.`


