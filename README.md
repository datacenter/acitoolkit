# acitoolkit [![Documentation Status](https://readthedocs.org/projects/acitoolkit/badge/?version=latest)](https://readthedocs.org/projects/acitoolkit/?badge=latest) [![Build Status](https://api.shippable.com/projects/54ea96315ab6cc13528d52ad/badge?branchName=master)](https://app.shippable.com/projects/54ea96315ab6cc13528d52ad/builds/latest) [![Code Health](https://landscape.io/github/datacenter/acitoolkit/master/landscape.svg?style=flat)](https://landscape.io/github/datacenter/acitoolkit/master)

       ____ _                    _    ____ ___   _____           _ _    _ _
      / ___(_)___  ___ ___      / \  / ___|_ _| |_   _|__   ___ | | | _(_) |_
     | |   | / __|/ __/ _ \    / _ \| |    | |    | |/ _ \ / _ \| | |/ / | __|
     | |___| \__ \ (_| (_) |  / ___ \ |___ | |    | | (_) | (_) | |   <| | |_
      \____|_|___/\___\___/  /_/   \_\____|___|   |_|\___/ \___/|_|_|\_\_|\__|


# Description

The ACI Toolkit is a **Python library** that makes it much easier to
**interact with a Cisco ACI fabric** than other traditional approaches
(using the Cobra SDK or calling the REST API directly). It
**can be used to build all sorts of tools**,
ranging from deployment automation to operation monitoring.

The library provides the ability to implement most use cases in an easy manner,
without having to deal with the complete ACI object model but instead with a
very **small subset of classes that hide most of the underlying complexity**
from the user.

Apart from the actual library, the ACI toolkit
**also includes a set of miscellaneous tools** such an endpoint tracker,
a diagram generator or a tool to identify configuration that deviates from
Cisco's best practices.


# Documentation

Full documentation for the ACI toolkit is published at the following link:
[http://acitoolkit.readthedocs.org/en/latest/](http://acitoolkit.readthedocs.org/en/latest/)


# Installation

## Required Environment

* Python 2.7 or Python3.x
* [setuptools package](https://pypi.python.org/pypi/setuptools)

## Downloading

**Option A: GIT**

If you have git installed, you can clone the repository as follows:

    git clone https://github.com/datacenter/acitoolkit.git

**Option B: Direct Download**

If you don't have GIT you can download the repository as a ZIP file and extract
the contents to a local directory:

[https://github.com/datacenter/acitoolkit/archive/master.zip](https://github.com/datacenter/acitoolkit/archive/master.zip)

**Option C: Docker**

The latest build of this project is also available as a Docker image from
Docker Hub:

    docker pull dockercisco/acitoolkit 

## Installing

Once you have the source files in a local directory, it needs to be installed
using setuptools.

    cd acitoolkit
    python setup.py install

Note that if you need to install it on a specific version of python, you may
need to call it explicitly. For example:

    python2.7 setup.py install
    python3 setup.py install

If you plan on modifying the actual toolkit files, you should install the
developer environment that will link the package installation to your
development directory.

    cd acitoolkit
    python setup.py develop


# Usage

A tutorial and an overview of the acitoolkit object model can be found at:

[http://acitoolkit.readthedocs.org/en/latest/](http://acitoolkit.readthedocs.org/en/latest/)


# License

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

# Contributing

The ACI toolkit is maintained by Cisco but it's open source software so anyone
can contribute to it. Feel free to clone the toolkit and extend it to your
needs.

If you think your enhancements can be useful for the wider community, please
issue a pull request. If your code meets our quality standards, we'd be happy
to merge it on the official trunk and credit you (or your organization) in
the contributors file.
