Pre-installed Packages
--------------------------

The ``acitoolkit`` can be downloaded pre-configured as a virtual machine.

Virtual Machine for VMware Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A pre-installed virtual machine in the form of a OVA file for VMware hypervisors
can be found in the link below:

`ACI Toolkit OVA <http://bit.ly/2mV12RQ>`_

The virtual machine is configured with the following parameters::

    Username: acitoolkit
    Password: acitoolkit
    Operating System: Ubuntu 16.04.2
    Processor Cores: 1
    Memory: 1GB

The ``acitoolkit`` and necessary packages are already installed. However, given
the pace of change in datacenter networking, there most likely have been changes
since the VM was created. Luckily, the VM can be updated to the latest version
by entering the following command::

    sudo ~/install

This command be re-run any time to get the latest updates.