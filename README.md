# acitoolkit

# Description

The ACI Toolkit is a set of python libraries that allow basic
configuration of the Cisco APIC controller. It is intended to allow users to quickly begin using the REST API and accelerate the learning curve necessary to begin using the APIC.

Please consult the wiki associated with this Github repository for documentation.

# Installation

## Environment

Required

* Python 2.7+
* [requests library](http://docs.python-requests.org/en/latest/user/install/#install)

## Downloading

Option A:

If you have git installed, clone the repository

    git clone https://github.com/datacenter/acitoolkit.git

Option B:

If you don't have git, [download a zip copy of the repository](https://github.com/datacenter/acitoolkit/archive/master.zip) and extract.


## Installing

After downloading, install using setuptools.

    cd acitoolkit
    python setup.py install

If you plan on modifying the actual toolkit files, you should install the developer environment that will link the package installation to your development directory.

    cd acitoolkit
    python setup.py develop

# Usage

# License

Copyright 2014 Cisco Systems, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
