# ACI Diagram generator

This is a simple application to connect to an APIC using the acitoolkit library, retrieve the configuration and generate diagrams of the configuration. 

##Installation
The main requirement is for GraphViz and the python wrapper PyGraphViz.

On MacOS, the easiest way to install these is (assuming you have HomeBrew and pip setup):

```bash
brew install graphviz
pip install pygraphviz
```

##Usage

```
usage: diagram.py [-h] -l LOGIN -p PASSWORD -u URL -o OUTPUT
                  [-t [TENANTS [TENANTS ...]]] [-v]

Generate logical diagrams of a running Cisco ACI Application Policy
Infrastructure Controller

optional arguments:
  -h, --help            show this help message and exit
  -l LOGIN, --login LOGIN
                        Login for authenticating to APIC
  -p PASSWORD, --password PASSWORD
                        Password for authenticating to APIC
  -u URL, --url URL     URL for connecting to APIC
  -o OUTPUT, --output OUTPUT
                        Output file for diagram - e.g. out.png, out.jpeg
  -t [TENANTS [TENANTS ...]], --tenants [TENANTS [TENANTS ...]]
                        Tenants to include when generating diagrams
  -v, --verbose         show verbose logging information
```

