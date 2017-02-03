# VERSION 1.0
FROM ubuntu
MAINTAINER Kevin Corbin, kecorbin@cisco.com
RUN apt-get update
RUN apt-get -y install git python python-pip 
RUN apt-get -y install graphviz graphviz-dev pkg-config
WORKDIR /opt
RUN git clone https://github.com/datacenter/acitoolkit
WORKDIR acitoolkit
RUN python setup.py install
