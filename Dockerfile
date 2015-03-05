# VERSION 1.0
FROM ubuntu
MAINTAINER Kevin Corbin, kecorbin@cisco.com
RUN echo "deb http://archive.ubuntu.com/ubuntu precise main universe" > /etc/apt/sources.list
RUN apt-get update
RUN apt-get -y install git python python-pip 
WORKDIR /opt
RUN git clone https://github.com/datacenter/acitoolkit
WORKDIR acitoolkit
RUN python setup.py install
