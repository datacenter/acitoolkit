# VERSION 1.0
FROM ubuntu

MAINTAINER Kevin Corbin, kecorbin@cisco.com

RUN apt-get update \
 && apt-get -y install git graphviz-dev pkg-config python python-pip vim-tiny \
 && cd /opt \
 && git clone https://github.com/datacenter/acitoolkit \
 && cd acitoolkit \
 && python setup.py install \
 && apt-get clean
WORKDIR /opt/acitoolkit
CMD ["/bin/bash"]
