################################################################################
#                                  _    ____ ___                               #
#                                 / \  / ___|_ _|                              #
#                                / _ \| |    | |                               #
#                               / ___ \ |___ | |                               #
#                         _____/_/   \_\____|___|_ _                           #
#                        |_   _|__   ___ | | | _(_) |_                         #
#                          | |/ _ \ / _ \| | |/ / | __|                        #
#                          | | (_) | (_) | |   <| | |_                         #
#                          |_|\___/ \___/|_|_|\_\_|\__|                        #
#                                                                              #
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""ACI Toolkit module for physical objects
"""
import copy
import logging
from operator import attrgetter, itemgetter
import re

from .acibaseobject import (
    BaseACIObject, BaseACIPhysModule, BaseACIPhysObject, BaseInterface
)
from .acicounters import AtomicCountersOnGoing, InterfaceStats
from .aciSearch import Searchable
from .acisession import Session
from .aciTable import Table
# TODO: resolve circular dependency and import only LogicalModel
import acitoolkit as ACI


class Systemcontroller(BaseACIPhysModule):
    """ class of the motherboard of the APIC controller node   """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create the name
        of the Systemcontroller and set the type
        before calling the base class __init__ method.

        :param pod: pod id
        :param node: node id
        :param slot: slot id
        :param parent: optional parent object

        """
        self.type = 'systemctrlcard'
        self.check_parent(parent)
        super(Systemcontroller, self).__init__(pod, node, slot, parent)
        self.name = 'SysC-' + '/'.join([pod, node, slot])

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['eqptBoard']

        return resp

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object

        :returns: class of parent object
        """
        return Node

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/sys/ch/bslot/board')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/sys/ch/bslot/board')[1].split('/')[0]
        return name

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the System controllers from the APIC.
        This information comes from
        the APIC 'eqptBoard' class.

        If parent is specified, it will only get system
        controllers that are children of the the parent.
        The system controlles will also be added as children
        to the parent Node.

        :param session: APIC session
        :param parent: parent Node

        :returns: list of Systemcontrollers
        """
        return cls.get_obj(session, cls._get_apic_classes(), parent)

    @staticmethod
    def _parse_dn(dn):
        """Parses the pod, node from a
           distinguished name of the node and fills in the slot to be '1'

           :param dn: dn of node

           :returns: pod, node, slot
        """
        name = dn.split('/')
        pod = str(name[1].split('-')[1])
        node = str(name[2].split('-')[1])
        slot = '1'
        return pod, node, slot

    def _get_firmware(self, dn):
        """Gets the firmware version of the System controller
        from the firmwareCtrlrRunning attribute of the
        ctrlrrunning object under the ctrlrfwstatuscont object.
        It will set the bios to None.

        :param dn: dn of node

        :returns: firmware, bios
        """
        name = dn.split('/')
        new_dist_name = '/'.join(name[0:4])

        mo_query_url = '/api/mo/' + new_dist_name + \
                       '/ctrlrfwstatuscont/ctrlrrunning.json?query-target=self'
        ret = self._session.get(mo_query_url)
        node_data = ret.json()['imdata']

        firmware = None
        if node_data:
            if 'firmwareCtrlrRunning' in node_data[0]:
                firmware = str(node_data[0]['firmwareCtrlrRunning']['attributes']['version'])

        bios = None
        return firmware, bios

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        :param attributes:
        """
        self.serial = str(attributes['ser'])
        self.model = str(attributes['model'])
        self.dn = str(attributes['dn'])
        self.descr = str(attributes['descr'])
        self.type = str(attributes['type'])
        self.oper_st = str(attributes['operSt'])
        self.modify_time = str(attributes['modTs'])
        # I think this is a bug fix to the APIC controller.  The type should be set correctly.
        if self.type == 'unknown':
            self.type = 'systemctrlcard'


class Cluster(BaseACIObject):
    """
    Represents the global settings of the Cluster
    """
    def __init__(self, name, parent=None):
        """
        :param name:  String containing the name of this Cluster object.
        """
        super(Cluster, self).__init__(name, parent)
        self.name = name
        self.config_size = None
        self.cluster_size = None
        self.apics = []

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the Clusters from the APIC.

        :returns: Instance of Cluster class.
        """
        # start at top
        infra_query_url = '/api/node/class/infraCont.json'
        ret = session.get(infra_query_url)
        cluster_info = ret.json()['imdata']
        infra_cluster_url = '/api/node/class/infraClusterPol.json'
        ret = session.get(infra_cluster_url)
        ret_cluster = ret.json()['imdata']
        cluster = cls('apic-cluster', parent=parent)
        cluster.config_size = ret_cluster[0]['infraClusterPol']['attributes']['size']
        for apic in cluster_info:
            cluster.apics.append(apic['infraCont']['attributes']['dn'])
        cluster._populate_from_attributes(cluster_info[0]['infraCont']['attributes'])
        return cluster

    def _populate_from_attributes(self, attributes):
        """"Fills in an object with desired attributes.
        """
        self.cluster_size = str(attributes['size'])
        self.name = str(attributes['fbDmNm'])

    def get_config_size(self):
        """
        :returns: configured size of the cluster, i.e. # of APICs
        """
        return self.config_size

    def get_cluster_size(self):
        """
        reads information about the APIC cluster
        :return:
        """
        return self.cluster_size

    def get_apics(self):
        return self.apics


class Linecard(BaseACIPhysModule):
    """ class for a linecard of a switch   """

    def __init__(self, arg0=None, arg1=None, slot=None, parent=None):
        """Initialize the basic object.  It will create the
        name of the linecard and set the type
        before calling the base class __init__ method.
        If arg1 is an instance of a Node, then pod,
        and node are derived from the Node and the slot_id
        is from arg0.  If arg1 is not a Node, then arg0
        is the pod, arg1 is the node id, and slot is the slot_id

        In other words, this Linecard object can either be initialized by

        `>>> lc = Linecard(slot_id, parent_switch)`

        or

        `>>> lc = Linecard(pod_id, node_id, slot_id)`

        or

        `>>> lc = Linecard(pod_id, node_id, slot_id, parent_switch)`

        :param arg0: pod_id if arg1 is a node_id, slot_id if arg1 is of type Node
        :param arg1: node_id string or parent Node of type Node
        :param slot: slot_id if arg1 is node_id  Not required if arg1 is a Node
        :param parent: parent switch of type Node.  Not required if arg1 is used instead.

        :returns: None
        """
        if isinstance(arg1, self._get_parent_class()):
            slot_id = arg0
            pod = arg1.pod
            node = arg1.node
            parent = arg1
        else:
            slot_id = slot
            pod = arg0
            node = arg1

        self.type = 'linecard'
        self.check_parent(parent)
        super(Linecard, self).__init__(pod, node, slot_id, parent)
        self.name = 'Lc-' + '/'.join([str(pod), str(node), str(slot_id)])

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['eqptLC']

        return resp

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object

        :returns: class of parent object
        """
        return Node

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/lc-')[0]

    @staticmethod
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return [Interface]

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the linecards from the APIC.  If parent is
        specified, it will only get linecards that are
        children of the the parent.  The linecards will also
        be added as children to the parent Node.

        The lincard object is derived mostly from the APIC 'eqptLC' class.

        :param session: APIC session
        :param parent: optional parent of class Node

        :returns: list of linecards
        """
        return cls.get_obj(session, cls._get_apic_classes(), parent)

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = str(attributes['ser'])
        self.model = str(attributes['model'])
        self.descr = str(attributes['descr'])
        self.num_ports = str(attributes['numP'])
        self.hardware_version = str(attributes['hwVer'])
        self.hardware_revision = str(attributes['rev'])
        self.type = str(attributes['type'])
        self.oper_st = str(attributes['operSt'])
        self.dn = str(attributes['dn'])
        self.modify_time = str(attributes['modTs'])

    @staticmethod
    def get_table(linecards, super_title=''):
        """
        Will create table of line card information
        :param super_title:
        :param linecards:
        """
        result = []

        headers = ['Slot', 'Model', 'Ports',
                   'Firmware', 'Bios', 'HW Ver', 'Hw Rev',
                   'Oper St', 'Serial', 'Modify Time']
        table = []
        for module in sorted(linecards, key=attrgetter('slot')):
            table.append([module.slot,
                          module.model,
                          module.num_ports,
                          module.firmware,
                          module.bios,
                          module.hardware_version,
                          module.hardware_revision,
                          module.oper_st,
                          module.serial,
                          module.modify_time])

        result.append(Table(table, headers, title=super_title + 'Linecards'))
        return result

    # def _define_searchables(self):
    #     """
    #     Create all of the searchable terms
    #
    #     :rtype : list of Searchable
    #     """
    #     results = super(Linecard, self)._define_searchables()
    #
    #     for result in results:
    #         if self.hardware_version is not None:
    #             result.add_term('version', self.hardware_version)
    #
    #         if self.hardware_revision is not None:
    #             result.add_term('revision', self.hardware_revision)
    #
    #     return results


class Supervisorcard(BaseACIPhysModule):
    """Class representing the supervisor card of a switch
    """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  This should be called by the
            init routines of inheriting subclasses.

            :param pod: pod id
            :param node: node id
            :param slot: slot id
            :param parent: optional parent object
        """
        self.type = 'supervisor'
        self.check_parent(parent)
        super(Supervisorcard, self).__init__(pod, node, slot, parent)
        self.name = 'SupC-' + '/'.join([pod, node, slot])

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['eqptSupC']

        return resp

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object

        :returns: class of parent object
        """
        return Node

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/sys/ch/supslot-1/sup')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/sys/ch/supslot-1/sup')[1].split('/')[0]
        return name

    @classmethod
    def get(cls, session, parent_node=None):
        """Gets all of the supervisor cards from the APIC.
        If parent is specified, it will only get the
        supervisor card that is a child of the the parent Node.
        The supervisor will also be added as a child to the parent Node.

        The Supervisorcard object is derived mostly from the
        APIC 'eqptSupC' class.

        If `parent_node` is a str, then it is the Node id of the switch
        for the supervisor.

        :param session: APIC session
        :param parent_node: optional parent switch of class Node or the node id of a switch

        :returns: list of linecards
        """
        #        if parent_node:
        #            if not isinstance(parent_node, Node) and not isinstance(parent_node, str):
        #                raise TypeError('An instance of Node class or node id string is requried')

        return cls.get_obj(session, cls._get_apic_classes(), parent_node)

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = str(attributes['ser'])
        self.model = str(attributes['model'])
        self.dn = str(attributes['dn'])
        self.descr = str(attributes['descr'])
        self.type = str(attributes['type'])
        self.num_ports = str(attributes['numP'])
        self.hardware_version = str(attributes['hwVer'])
        self.hardware_revision = str(attributes['rev'])
        self.oper_st = str(attributes['operSt'])
        self.modify_time = str(attributes['modTs'])

    @staticmethod
    def get_table(modules, super_title=''):
        """
        Will create table of supervisor information
        :param super_title:
        :param modules:
        """
        result = []

        headers = ['Slot', 'Model', 'Ports', 'Firmware', 'Bios',
                   'HW Ver', 'Hw Rev', 'Oper St', 'Serial', 'Modify Time']
        table = []
        for module in sorted(modules, key=attrgetter('slot')):
            table.append([module.slot,
                          module.model,
                          module.num_ports,
                          module.firmware,
                          module.bios,
                          module.hardware_version,
                          module.hardware_revision,
                          module.oper_st,
                          module.serial,
                          module.modify_time])

        result.append(Table(table, headers, title=super_title + 'Supervisors'))
        return result

    # def _define_searchables(self):
    #     """
    #     Create all of the searchable terms
    #
    #     :rtype : list of Searchable
    #     """
    #
    #     results = super(Supervisorcard, self)._define_searchables()
    #
    #     for result in results:
    #         if self.hardware_version is not None:
    #             result.add_term('version', self.hardware_version)
    #
    #         if self.hardware_revision is not None:
    #             result.add_term('revision', self.hardware_revision)
    #
    #     return results


class Fantray(BaseACIPhysModule):
    """Class for the fan tray of a node"""

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create
        the name of the fan tray and set the type
        before calling the base class __init__ method
        :param pod: pod id
        :param node: node id
        :param slot: slot id
        :param parent: optional parent object
        """
        self.type = 'fantray'
        self.status = None
        self.check_parent(parent)
        super(Fantray, self).__init__(pod, node, slot, parent)
        self.name = 'FT-' + '/'.join([pod, node, slot])

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['eqptFt']

        return resp

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object

        :returns: class of parent object
        """
        return Node

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/ft-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/ft-')[1].split('/')[0]
        return name

    @staticmethod
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return [Fan]

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the fantrays from the APIC.  If parent
        is specified, it will only get fantrays that are
        children of the the parent.  The fantrays will
        also be added as children to the parent Node.

        The fantray object is derived mostly from the APIC 'eqptFt' class.

        :param session: APIC session
        :param parent: optional parent switch of class Node

        :returns: list of fantrays
        """
        #        if parent:
        #            if not isinstance(parent, Node):
        #                raise TypeError('An instance of Node class is requried')
        fans = cls.get_obj(session, cls._get_apic_classes(), parent)
        return fans

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = str(attributes['ser'])
        self.model = str(attributes['model'])
        self.dn = str(attributes['dn'])
        self.descr = str(attributes['descr'])
        self.oper_st = str(attributes['operSt'])
        self.name = str(attributes.get('fanName', 'None'))
        self.status = str(attributes['status'])
        self.modify_time = str(attributes['modTs'])
        self.id = str(attributes['id'])
        (pod, node, slot) = self._parse_dn(self.dn)
        self.pod = pod
        self.node = node
        self.slot = slot

    def _get_firmware(self, dist_name):
        """ Returns None for firmware and bios revisions"""
        return None, None

    @staticmethod
    def get_table(modules, title=''):
        """
        Will create table of fantry information
        :param title:
        :param modules:
        """
        result = []

        headers = ['Slot', 'Model', 'Name', 'Tray Serial',
                   'Fan ID', 'Oper St', 'Direction', 'Speed', 'Fan Serial']
        table = []
        by_id = attrgetter('id')
        for fantray in sorted(modules, key=attrgetter('slot')):
            fans = fantray.get_children(Fan)

            first_fan = sorted(fans, key=by_id)[0]
            table.append([fantray.slot,
                          fantray.model,
                          fantray.name,
                          fantray.serial,
                          'fan-' + first_fan.id,
                          first_fan.oper_st,
                          first_fan.direction,
                          first_fan.speed,
                          first_fan.serial])
            for fan in sorted(fans, key=by_id):
                if fan != first_fan:
                    table.append([fantray.slot,
                                  fantray.model,
                                  fantray.name,
                                  fantray.serial,
                                  'fan-' + fan.id,
                                  fan.oper_st,
                                  fan.direction,
                                  fan.speed,
                                  fan.serial])

        result.append(Table(table, headers, title=title + 'Fan Trays'))
        return result

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return self.get_name()


class Fan(BaseACIPhysModule):
    """Class for the fan of a fan tray"""

    def __init__(self, parent=None):
        """ Initialize the basic fan.

            :param parent: optional parent Fantray object
            """
        self.type = 'fan'
        if parent:
            super(Fan, self).__init__(parent.pod, parent.node, parent.slot, parent)
        else:
            super(Fan, self).__init__(pod=None, node=None, slot=None, parent=parent)
        self.descr = None
        self.oper_st = None
        self.direction = None
        self.speed = None
        self.id = None

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['eqptFan']

        return resp

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object

        :returns: class of parent object
        """
        return Fantray

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/fan-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/fan-')[1].split('/')[0]
        return name

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the fans from the APIC.  If parent
        is specified, it will only get fantrays that are
        children of the the parent.  The fantrays will
        also be added as children to the parent Node.

        The fan object is derived mostly from the APIC 'eqptFan' class.

        :param session: APIC session
        :param parent: optional parent fantray of class Fantray

        :returns: list of fans
        """

        cls.check_session(session)
        cls.check_parent(parent)
        fans = []

        # get the total number of ports = number of power supply slots
        if parent:
            mo_query_url = '/api/mo/' + parent.dn + \
                           '.json?query-target=subtree&target-subtree-class=' + \
                           ','.join(cls._get_apic_classes())

        else:
            mo_query_url = ('/api/node/class/eqptFan.json?'
                            'query-target=self')

        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        if node_data:
            for fan_obj in node_data:
                fan = Fan()
                fan._populate_from_attributes(fan_obj['eqptFan']['attributes'])
                # now get speed if it is being monitored
                mo_query_url = '/api/mo/' + fan.dn + \
                               '.json?rsp-subtree-include=stats&rsp-subtree-class=eqptFanStats5min'
                ret = session.get(mo_query_url)
                stat_data = ret.json()['imdata']
                fan.speed = 'unknown'
                if stat_data:
                    if 'eqptFan' in stat_data[0]:
                        if 'children' in stat_data[0]['eqptFan']:
                            if stat_data[0]['eqptFan']['children']:
                                if 'eqptFanStats5min' in stat_data[0]['eqptFan']['children'][0]:
                                    fan.speed = \
                                        str(stat_data[0]['eqptFan']['children'][0]
                                            ['eqptFanStats5min']['attributes']['speedLast'])

                if parent:
                    fan._parent = parent
                    parent.add_child(fan)
                fans.append(fan)
        return fans

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.dn = str(attributes['dn'])
        self.id = str(attributes['id'])
        self.descr = str(attributes['descr'])
        self.oper_st = str(attributes['operSt'])
        self.direction = str(attributes['dir'])
        self.model = str(attributes['model'])
        self.serial = str(attributes['ser'])
        self.name = 'fan-{0}'.format(self.id)
        (pod, node, slot) = self._parse_dn(self.dn)
        self.pod = pod
        self.node = node
        self.slot = slot

    def __eq__(self, other):
        """compares two fans and returns True if they are the same.
        """
        if isinstance(other, self.__class__):
            key_attrs = attrgetter('model', 'id', '_parent')
            return key_attrs(self) == key_attrs(other)
        return NotImplemented

    def __str__(self):
        """
        Default print string

        :return: str
        """
        return 'Fan-' + self.id

    @staticmethod
    def get_table(modules, title=''):
        """
        Will create table of fantry information
        :param title:
        :param modules:
        """
        result = []

        headers = ['Fan ID', 'Oper St', 'Direction', 'Speed', 'Fan Serial']
        table = []
        for fan in sorted(modules, key=attrgetter('id')):
            table.append(['fan-' + fan.id,
                          fan.oper_st,
                          fan.direction,
                          fan.speed,
                          fan.serial])

        result.append(Table(table, headers, title=title + 'Fan Trays'))
        return result


class Powersupply(BaseACIPhysModule):
    """ class for a power supply in a node   """

    def __init__(self, pod, node, slot, parent=None):
        """ Initialize the basic object.  It will create
        the name of the powersupply and set the type
        before calling the base class __init__ method
        :param pod: pod id
        :param node: node id
        :param slot: slot id
        :param parent: optional parent object
        """
        self.type = 'powersupply'
        self.check_parent(parent)
        super(Powersupply, self).__init__(pod, node, slot, parent)
        self.status = None
        self.voltage_source = None
        self.fan_status = None
        self.name = 'PS-' + '/'.join([pod, node, slot])

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['eqptPsu']

        return resp

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object

        :returns: class of parent object
        """
        return Node

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/psu-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/psu-')[1].split('/')[0]
        return name

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the power supplies from the APIC.
        If parent is specified, it will only get power supplies that are
        children of the the parent.  The power supplies
        will also be added as children to the parent Node.

        The Powersupply object is derived mostly from the APIC 'eqptPsu' class.

        :param session: APIC session
        :param parent: optional parent switch of class Node

        :returns: list of powersupplies
        """
        return cls.get_obj(session, cls._get_apic_classes(), parent)

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.serial = str(attributes['ser'])
        self.model = str(attributes['model'])
        self.dn = str(attributes['dn'])
        self.descr = str(attributes['descr'])
        self.oper_st = str(attributes['operSt'])
        self.fan_status = str(attributes['fanOpSt'])
        self.voltage_source = str(attributes['vSrc'])
        self.hardware_version = str(attributes['hwVer'])
        self.hardware_revision = str(attributes['rev'])
        self.status = str(attributes['status'])
        self.modify_time = str(attributes['modTs'])

    @staticmethod
    def _get_firmware(dist_name):
        """ The power supplies do not have a readable firmware or bios revision so
        this will return None for firmware and bios revisions"""

        return None, None

    @staticmethod
    def get_table(modules, super_title=''):
        """
        Will create table of power supply information
        :param super_title:
        :param modules:
        """
        result = []
        headers = ['Slot', 'Model', 'Source Power',
                   'Oper St', 'Fan State', 'HW Ver', 'Hw Rev', 'Serial', 'Uptime']

        table = []
        for pwr_sup in sorted(modules, key=attrgetter('slot')):
            # pwr_sup = modules[slot]
            table.append([pwr_sup.slot,
                          pwr_sup.model,
                          pwr_sup.voltage_source,
                          pwr_sup.oper_st,
                          pwr_sup.fan_status,
                          pwr_sup.hardware_version,
                          pwr_sup.hardware_revision,
                          pwr_sup.serial,
                          pwr_sup.modify_time])

        result.append(Table(table, headers, title=super_title + 'Power Supplies'))
        return result

    # def _define_searchables(self):
    #     """
    #     Create all of the searchable terms
    #
    #     :rtype : list of Searchable
    #     """
    #     results = super(Powersupply, self)._define_searchables()
    #     for result in results:
    #         if self.hardware_version is not None:
    #             result.add_term('version', self.hardware_version)
    #         if self.hardware_revision is not None:
    #             result.add_term('revision', self.hardware_revision)
    #         if self.voltage_source is not None:
    #             result.add_term('voltage', self.voltage_source)
    #
    #     return results


class Pod(BaseACIPhysObject):
    """ Pod :  roughly equivalent to fabricPod """

    def __init__(self, pod, dn=None, parent=None):
        """ Initialize the basic object.  It will
            create the name of the pod and set the type
            before calling the base class __init__ method.
            Typically the pod_id will be 1.

            :param pod: pod id string
            :param dn: distinguished name
            :param parent: optional parent object
            """
        super(Pod, self).__init__()
        self.check_parent(parent)
        self.type = 'pod'
        self.dn = dn
        self.pod = pod
        self.name = 'pod-' + str(self.pod)
        logging.debug('Creating %s %s', self.__class__.__name__, self.pod)
        if dn is not None:
            self.atomic_counters = AtomicCountersOnGoing(self, dn)
        if parent:
            self._parent = parent
            self._parent.add_child(self)

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return PhysicalModel

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/pod-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/pod-')[1].split('/')[0]
        return name

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['fabricPod']
        return resp

    @staticmethod
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return [Node, Link, ExternalSwitch]

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the Pods from the APIC.  Generally there will be only one.

        :param parent: optional parent of class PhysicalModel
        :param session: APIC session
        :returns: list of Pods.  Note that this will be a
                  list even though there typically
                  will only be one item in the list.
        """
        cls.check_session(session)
        cls.check_parent(parent)

        class_query_url = '/api/node/class/fabricPod.json?query-target=self'
        pods = []
        apic_class = cls._get_apic_classes()[0]
        ret = session.get(class_query_url)
        pod_data = ret.json()['imdata']
        for apic_pod in pod_data:
            if apic_class in apic_pod:
                dn = str(apic_pod[apic_class]['attributes']['dn'])
                pod_id = str(apic_pod[apic_class]['attributes']['id'])
                pod = Pod(pod_id, dn)
                pod._session = session
                if parent:
                    pod._parent = parent
                    pod._parent.add_child(pod)
                pods.append(pod)
        return pods

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.pod == other.pod
        return NotImplemented

    def __str__(self):
        return self.name


class Node(BaseACIPhysObject):
    """Node :  roughly equivalent to fabricNode """

    def __init__(self, name=None, pod=None, node=None, role=None, parent=None):
        """
            :param pod: String representation of the pod number
            :param node: String representation of the node number
            :param name: Name of the node
            :param role: Role of the node.  Valid roles are None,
                         'spine', 'leaf', 'controller', 'loosenode'
            :param parent: Parent pod object of the node.
            """
        if name:
            if not isinstance(name, str):
                raise TypeError("Name must be a string")

        self.check_parent(parent)
        valid_roles = [None, 'spine', 'leaf', 'controller', 'vleaf', 'vip', 'protection-chain', 'unsupported']
        if role not in valid_roles:
            raise ValueError(
                "role must be one of " + str(valid_roles) + " instead found " + str(role) + ' for node ' + node)
        self.pod = pod
        self.node = node
        self.role = role
        self.type = 'node'
        super(Node, self).__init__(name=name, pod=pod, parent=parent)
        self._session = None
        self.fabricSt = None
        self.ipAddress = None
        self.tep_ip = None
        self.macAddress = None
        self.state = None
        self.mode = None
        self.oper_st = None
        self.operStQual = None
        self.descr = None
        self.model = None
        self.dn = None
        self.vendor = None
        self.serial = None
        self.health = None
        self.firmware = None
        self.num_ps_slots = 0
        self.num_fan_slots = 0
        self.num_sup_slots = 0
        self.num_lc_slots = 0
        self.num_ps_modules = 0
        self.num_fan_modules = 0
        self.num_sup_modules = 0
        self.num_lc_modules = 0
        self.num_ports = 0
        self.inb_mgmt_ip = None
        self.oob_mgmt_ip = None
        self.system_uptime = None
        self.vpc_info = None
        self.v4_proxy_ip = None
        self.mac_proxy_ip = None
        self.dynamic_load_balancing_mode = None
        logging.debug('Creating %s %s', self.__class__.__name__, 'pod-' +
                      str(self.pod) + '/node-' + str(self.node))
        # self._common_init(parent)

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return Pod

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/node-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/node-')[1].split('/')[0]
        return name

    @classmethod
    def get_event(cls, session):
        """
        Gets the event that is pending for this class.  Events are
        returned in the form of objects.  Objects that have been deleted
        are marked as such.

        :param session:  the instance of Session used for APIC communication
        """
        urls = cls._get_subscription_urls()
        for url in urls:
            if not session.has_events(url):
                continue
            event = session.get_event(url)
            for class_name in cls._get_apic_classes():
                if class_name in event['imdata'][0]:
                    break
            attributes = event['imdata'][0][class_name]['attributes']
            status = str(attributes['status'])
            dn = str(attributes['dn'])
            pod_id, node_id = Node._parse_dn(dn)

            node_dn = 'topology/pod-{0}/node-{1}'.format(pod_id, node_id)
            base_url = '/api/mo/' + node_dn + '.json?'
            working_data = WorkingData(session, Node, base_url)

            parent = cls._get_parent_from_dn(cls._get_parent_dn(dn))

            data = working_data.get_class('fabricNode')
            for apic_node in data:
                if 'fabricNode' in apic_node:
                    dist_name = str(apic_node['fabricNode']['attributes']['dn'])
                    node_name = str(apic_node['fabricNode']['attributes']['name'])
                    (pod, node_id) = cls._parse_dn(dist_name)
                    node_role = str(apic_node['fabricNode']['attributes']['role'])
                    node = cls(pod, node_id, node_name, node_role)
                    node._session = session
                    node._populate_from_attributes(apic_node['fabricNode']['attributes'])
                    node._get_topsystem_info(working_data)

                    # check for pod match if specified
                    pod_match = False
                    if parent:
                        if isinstance(parent, Pod):
                            if node.pod == parent.pod:
                                pod_match = True
                                node._parent = parent
                        else:
                            # pod is a number string
                            if node.pod == parent:
                                pod_match = True
                    else:
                        pod_match = True

                    # check for node match if specified
                    node_match = False
                    if node_id:
                        if node_id == node.node:
                            node_match = True
                    else:
                        node_match = True

                    if node_match and pod_match:
                        if node.role == 'leaf':
                            node._add_vpc_info(working_data)
                        node.get_health()
                        node.get_firmware(working_data)

                        if isinstance(parent, Pod):
                            node._parent.add_child(node)

                    if status == 'deleted':
                        node.mark_as_deleted()
                    return node

    @staticmethod
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return [Systemcontroller, Supervisorcard, Linecard, Powersupply, Fantray]

    @staticmethod
    def _get_children_concrete_classes():
        """
        Get the acitoolkit class of the concrete children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        # TODO: resolve circular dependency
        from .aciConcreteLib import (
            ConcreteAccCtrlRule, ConcreteArp, ConcreteBD, ConcreteContext,
            ConcreteEp, ConcreteFilter, ConcreteLoopback, ConcreteOverlay,
            ConcretePortChannel, ConcreteVpc,
            ConcreteCdp, ConcreteLLdp
        )

        return [ConcreteArp, ConcreteAccCtrlRule, ConcreteBD, ConcreteOverlay,
                ConcretePortChannel, ConcreteEp, ConcreteFilter, ConcreteLoopback,
                ConcreteContext, ConcreteVpc,
                ConcreteCdp, ConcreteLLdp]

    @classmethod
    def _get_apic_classes(cls):
        """gets list of all apic classes used to build this acitoolkit class
        """
        resp = ['fabricNode', 'firmwareCardRunning', 'topSystem', 'vpcInst', 'vpcDom',
                'eqptCh', 'l1PhysIf', 'eqptFtSlot', 'eqptLCSlot', 'eqptPsuSlot',
                'eqptSupCSlot', 'topoctrlLbP',
                # 'topoctrlVxlanP'
                ]
        return resp

    def get_role(self):
        """ retrieves the node role
        :returns: role
        """
        return self.role

    def getFabricSt(self):
        """ retrieves the fabric state.

        :returns: fabric state
        """
        return self.fabricSt

    @staticmethod
    def _parse_dn(dn):
        """Parses the pod and node from a
           distinguished name of the node.
        """
        name = dn.split('/')
        pod = name[1].split('-')[1]
        node = name[2].split('-')[1]
        return pod, node

    @classmethod
    def get(cls, session, parent=None, node_id=None):
        """Gets all of the Nodes from the APIC.  If the parent pod is specified,
        only nodes of that pod will be retrieved.

        If parent pod and node_id is specified, only the matching switch will be
        retrieved.

        APIC controller nodes will have a 'role' of 'controller', while
        switch nodes will have a 'role' of 'leaf' or 'spine'

        :param session: APIC session
        :param parent: optional parent object or pod_id
        :param node_id: optional node_id of switch

        :returns: list of Nodes
        """
        # need to add pod as parent
        cls.check_session(session)

        if parent:
            if not isinstance(parent, cls._get_parent_class()) and not isinstance(parent, str):
                raise TypeError('An instance of Pod class or string is required to specify pod')
            else:
                if isinstance(parent, cls._get_parent_class()):
                    pod_id = parent.pod
                else:
                    pod_id = parent
        else:
            pod_id = '1'

        try:
            if isinstance(node_id, unicode):
                node_id = str(node_id)
        # In Python3 there is no unicode type
        except NameError:
            if isinstance(node_id, str):
                node_id = str(node_id)

        if node_id:
            if not isinstance(node_id, str):
                raise TypeError('The node_id must be a string such as "101".')

        if node_id:
            node_dn = 'topology/pod-{0}/node-{1}'.format(pod_id, node_id)
            base_url = '/api/mo/' + node_dn + '.json?'
            working_data = WorkingData(session, Node, base_url)

        else:
            class_url = '/api/node/class/fabricNode.json'
            ret = session.get(class_url)
            ret._content = ret._content.decode().replace('\n', '').encode()
            data = ret.json()['imdata']
            working_data = WorkingData()
            for item in data:
                if 'fabricNode' in item:
                    if 'role' in item['fabricNode']['attributes']:
                        if item['fabricNode']['attributes']['role'] in ['leaf', 'spine', 'controller']:
                            node_dn = item['fabricNode']['attributes']['dn']
                            base_url = '/api/mo/' + node_dn + '.json?'
                            working_data.add(session, Node, base_url)

                            # base_url = '/api/mo/topology/pod-{0}.json?'.format(pod_id)

        nodes = []
        data = working_data.get_class('fabricNode')
        for apic_node in data:
            if 'fabricNode' in apic_node:
                dist_name = str(apic_node['fabricNode']['attributes']['dn'])
                node_name = str(apic_node['fabricNode']['attributes']['name'])
                (pod, node_id) = cls._parse_dn(dist_name)
                node_role = str(apic_node['fabricNode']['attributes']['role'])
                node = cls(node_name, pod, node_id, node_role)
                node._session = session
                node._populate_from_attributes(apic_node['fabricNode']['attributes'])
                node._get_topsystem_info(working_data)

                # check for pod match if specified
                pod_match = False
                if parent:
                    if isinstance(parent, Pod):
                        if node.pod == parent.pod:
                            pod_match = True
                            node._parent = parent
                    else:
                        # pod is a number string
                        if node.pod == parent:
                            pod_match = True
                else:
                    pod_match = True

                # check for node match if specified
                node_match = False
                if node_id:
                    if node_id == node.node:
                        node_match = True
                else:
                    node_match = True

                if node_match and pod_match:
                    if node.role == 'leaf':
                        node._add_vpc_info(working_data)
                    node.get_health()
                    node.get_firmware(working_data)

                    if isinstance(parent, Pod):
                        node._parent.add_child(node)

                    nodes.append(node)
        return nodes

    def get_firmware(self, working_data):
        """
        retrieves firmware version
        :param working_data:
        """
        if self.role != 'controller':
            dn = self.dn + '/sys/ch/supslot-1/sup/running'
            data = working_data.get_object(dn)
            if data:
                if 'firmwareCardRunning' in data:
                    self.firmware = data['firmwareCardRunning']['attributes']['version']

    def get_health(self):
        """
        This will get the health of the switch node
        """
        if self.role != 'controller':
            mo_query_url = '/api/mo/' + self.dn + \
                           '/sys.json?&rsp-subtree-include=stats&rsp-subtree-class=fabricNodeHealth5min'
            ret = self._session.get(mo_query_url)
            data = ret.json()['imdata']
            if data:
                if 'topSystem' in data[0]:
                    if 'children' in data[0]['topSystem']:
                        ts_child = data[0]['topSystem']['children']
                        if 'fabricNodeHealth5Min' in ts_child[0]:
                            self.health = ts_child[0]['fabricNodeHealth5min']['attributes']['healthLast']

    def _add_vpc_info(self, working_data):
        """
        This method only runs for leaf switches.  If
        the leaf has a VPC peer, the VPC information will be populated
        and the node.vpc_present flag will be set.

        check for vpcDom sub-object
        and if it exists, then create the entry as a dictionary of values.

        Will first check vpc_inst to see if it is enabled
        then get vpcDom under vpcInst

        peer_present is true if vpcDom exists

        From vpcDom get :
            domain_id
            system_mac
            local_mac
            monitoring_policy
            peer_ip
            peer_system_mac
            peer_version
            peer_state
            vtep_ip
            vtep_mac
            oper_role
        """
        partial_dn = 'topology/pod-{0}/node-{1}/sys/vpc/inst'.format(self.pod, self.node)

        vpc_admin_state = 'disabled'
        data = working_data.get_object(partial_dn)
        if data:
            if 'vpcInst' in data:
                vpc_admin_state = data['vpcInst']['attributes']['adminSt']

        result = {'admin_state': vpc_admin_state}
        if vpc_admin_state == 'enabled':
            result['oper_state'] = 'inactive'
            data = working_data.get_subtree('vpcDom', partial_dn)
            if data:
                if 'vpcDom' in data[0]:
                    result['oper_state'] = 'active'
                    vpc_dom = data[0]['vpcDom']['attributes']
                    result['domain_id'] = vpc_dom['id']
                    result['system_mac'] = vpc_dom['sysMac']
                    result['local_mac'] = vpc_dom['localMAC']
                    result['monitoring_policy'] = vpc_dom['monPolDn']
                    result['peer_ip'] = vpc_dom['peerIp']
                    result['peer_mac'] = vpc_dom['peerMAC']
                    result['peer_version'] = vpc_dom['peerVersion']
                    result['peer_state'] = vpc_dom['peerSt']
                    result['vtep_ip'] = vpc_dom['virtualIp']
                    result['vtep_mac'] = vpc_dom['vpcMAC']
                    result['oper_role'] = vpc_dom['operRole']

        else:
            result['oper_state'] = 'inactive'
        self.vpc_info = result

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            key_attrs = attrgetter('pod', 'node', 'name', 'role')
            return key_attrs(self) == key_attrs(other)
        return NotImplemented

    def _populate_from_attributes(self, attributes):
        """Fills in an object with the desired attributes.
        """
        self.serial = str(attributes['serial'])
        self.model = str(attributes['model'])
        self.dn = str(attributes['dn'])
        self.vendor = str(attributes['vendor'])
        self.fabricSt = str(attributes['fabricSt'])
        self.modify_time = str(attributes['modTs'])

    def _get_topsystem_info(self, working_data):
        """ will read in topSystem object to get more information about Node"""

        node_data = working_data.get_object(self.dn + '/sys')
        if node_data is not None:
            if 'topSystem' in node_data:

                self.ipAddress = str(node_data['topSystem']['attributes']['address'])
                self.tep_ip = self.ipAddress
                self.macAddress = str(node_data['topSystem']['attributes']['fabricMAC'])
                self.state = str(node_data['topSystem']['attributes']['state'])
                self.mode = str(node_data['topSystem']['attributes']['mode'])
                self.oob_mgmt_ip = str(node_data['topSystem']['attributes'].get('oobMgmtAddr'))
                self.inb_mgmt_ip = str(node_data['topSystem']['attributes'].get('inbMgmtAddr'))
                self.system_uptime = str(node_data['topSystem']['attributes'].get('systemUpTime'))

                # now get eqptCh for even more info
                node_data = working_data.get_object(self.dn + '/sys/ch')
                if node_data:
                    if 'eqptCh' in node_data:
                        self.oper_st = str(node_data['eqptCh']['attributes']['operSt'])
                        self.operStQual = str(node_data['eqptCh']['attributes']['operStQual'])
                        self.descr = str(node_data['eqptCh']['attributes']['descr'])

                # get the total number of ports = number of l1PhysIf
                node_data = working_data.get_subtree('l1PhysIf', self.dn + '/sys')
                if node_data:
                    self.num_ports = str(len(node_data))

                # get the total number of ports = number of fan slots
                node_data = working_data.get_subtree('eqptFtSlot', self.dn + '/sys')
                if node_data:
                    self.num_fan_slots = str(len(node_data))

                self.num_fan_modules = 0
                if node_data:
                    for slot in node_data:
                        if slot['eqptFtSlot']['attributes']['operSt'] == 'inserted':
                            self.num_fan_modules += 1
                self.num_fan_modules = str(self.num_fan_modules)

                # get the total number of ports = number of linecard slots
                node_data = working_data.get_subtree('eqptLCSlot', self.dn + '/sys/ch')
                self.num_lc_slots = str(len(node_data))
                self.num_lc_modules = 0
                if node_data:
                    for slot in node_data:
                        if slot['eqptLCSlot']['attributes']['operSt'] == 'inserted':
                            self.num_lc_modules += 1
                self.num_lc_modules = str(self.num_lc_modules)

                # get the total number of ports = number of power supply slots
                node_data = working_data.get_subtree('eqptPsuSlot', self.dn + '/sys/ch')
                self.num_ps_slots = str(len(node_data))
                self.num_ps_modules = 0
                if node_data:
                    for slot in node_data:
                        if slot['eqptPsuSlot']['attributes']['operSt'] == 'inserted':
                            self.num_ps_modules += 1
                self.num_ps_modules = str(self.num_ps_modules)

                # get the total number of ports = number of supervisor slots
                node_data = working_data.get_subtree('eqptSupCSlot', self.dn + '/sys/ch')
                self.num_sup_slots = str(len(node_data))
                self.num_sup_modules = 0
                if node_data:
                    for slot in node_data:
                        if slot['eqptSupCSlot']['attributes']['operSt'] == 'inserted':
                            self.num_sup_modules += 1
                self.num_sup_modules = str(self.num_sup_modules)

                # get dynamic load balancing config
                self.dynamic_load_balancing_mode = 'unknown'

                lb_data = working_data.get_subtree('eqptSupCSlot', self.dn + '/sys')
                for lb_info in lb_data:
                    if 'topoctrlLbP' in lb_info:
                        self.dynamic_load_balancing_mode = lb_info['topoctrlLbP']['attributes']['dlbMode']

                # get vxlan info
                self.ivxlan_udp_port = 'unknown'

                # node_data = working_data.get_subtree('topoctrlVxlanP', self.dn + '/sys')
                # for info in node_data:
                #     if 'topoctrlVxlanP' in info:
                #         self.ivxlan_udp_port = info['topoctrlVxlanP']['attributes']['udpPort']

    @property
    def operSt(self):
        """
        changed value to "oper_st" so this makes the class backward compatible
        :return:
        """
        return self.oper_st

    def populate_children(self, deep=False, include_concrete=False):
        """Will populate all of the children modules such as
        linecards, fantrays and powersupplies, of the node.

        :param deep: boolean that when true will cause the entire
                     sub-tree to be populated. When false, only the
                     immediate children are populated
        :param include_concrete: boolean to indicate that concrete objects should also be populated

        :returns: List of children objects
        """

        session = self._session
        for child_class in self._get_children_classes():
            child_class.get(session, self)

        if include_concrete and self.role != 'controller':
            # todo: currently only have concrete model for switches - need to add controller
            query_url = '/api/mo/topology/pod-' + self.pod + '/node-' + self.node + \
                        '/sys.json?'

            working_data = WorkingData(session, Node, query_url, deep=True, include_concrete=True)
            for concrete_class in self._get_children_concrete_classes():
                concrete_class.get(working_data, self)

        if deep:
            for child in self._children:
                child.populate_children(deep, include_concrete)

        return self._children

    def get_chassis_type(self):
        """Returns the chassis type of this node.  The chassis
        type is derived from the model number.
        This is a chassis type that is compatible with
        Cisco's Cable Plan XML.

        :returns: chassis type of node of type str
        """
        if self.model:
            fields = self.model.split('-')
            chassis_type = fields[0].lower()
        else:
            chassis_type = None

        return chassis_type

    @staticmethod
    def get_table(switches, title=''):
        """
            Creates report of basic switch information
            :param switches: Array of Node objects
            :param title: optional title for this table
            """
        headers = ['Name',
                   'Pod ID',
                   'Node ID',
                   'Serial Number',
                   'Model',
                   'Role',
                   'Fabric State',
                   'State',
                   'Firmware',
                   'Health',
                   'In-band managment IP',
                   'Out-of-band managment IP',
                   'Number of ports',
                   'Number of Linecards (inserted)',
                   'Number of Sups (inserted)',
                   'Number of Fans (inserted)',
                   'Number of Power Supplies (inserted)',
                   'System Uptime',
                   'Dynamic Load Balancing']
        table = []
        for switch in sorted(switches, key=attrgetter('node')):
            table.append([switch.name,
                          switch.pod,
                          switch.node,
                          switch.serial,
                          switch.model,
                          switch.role,
                          switch.fabricSt,
                          switch.state,
                          switch.firmware,
                          switch.health,
                          switch.inb_mgmt_ip,
                          switch.oob_mgmt_ip,
                          switch.num_ports,
                          str(switch.num_lc_slots) + '(' + str(switch.num_lc_modules) + ')',
                          str(switch.num_sup_slots) + '(' + str(switch.num_sup_modules) + ')',
                          str(switch.num_fan_slots) + '(' + str(switch.num_fan_modules) + ')',
                          str(switch.num_ps_slots) + '(' + str(switch.num_ps_modules) + ')',
                          switch.system_uptime,
                          switch.dynamic_load_balancing_mode])
        if len(table) > 7:
            table_orientation = 'horizontal'
        else:
            table_orientation = 'vertical'

        if len(table) > 3:
            columns = 1
        else:
            columns = 2
        result = [Table(table, headers,
                        title=str(title) + '' if (title != '') else '' + 'Basic Information',
                        table_orientation=table_orientation, columns=columns)]
        return result

    def _define_searchables(self):
        """
        Create all of the searchable terms

        :rtype : list of Searchable
        """
        results = super(Node, self)._define_searchables()

        if self.role != 'controller':
            results[0].add_term('switch', self.name)
            results[0].add_term('switch', self.node)
        else:
            results[0].add_term('controller', self.name)
            results[0].add_term('controller', self.node)
            results[0].add_term('apic', self.name)
            results[0].add_term('apic', self.node)

        results[0].add_term('ipv4', self.inb_mgmt_ip)
        results[0].add_term('ipv4', self.oob_mgmt_ip)
        results[0].add_term('ipv4', str(self.tep_ip))
        results[0].add_term('management', self.inb_mgmt_ip)
        results[0].add_term('management', self.oob_mgmt_ip)

        return results


class ExternalSwitch(BaseACIPhysObject):
    """External Node.  This class is for switch nodes that are
    connected to the pod, but are not
    ACI nodes, i.e. are not under control of the APIC.
    Examples would be external layer 2 switches,
    external routers, or hypervisor based switches.

    This class will look as much as possible like the Node
    class recognizing that not as much information
    is available to the APIC about them as is available
    about ACI nodes.  Nearly all of the information used
    to create this class comes from LLDP.
    """

    def __init__(self, name=None, parent=None):
        self.check_parent(parent)
        self._parent = parent

        self._role = None
        self.dn = None
        self.name = None
        self.ip = None
        self.mac = None
        self.id = None
        self.pod = None
        self.status = None
        self.oper_issues = None
        self.fabric_st = 'external'
        self.role = 'external_switch'
        self.descr = None
        self.type = None
        self.state = None
        self.guid = None
        self.oid = None
        super(ExternalSwitch, self).__init__(name=name, parent=parent)

    @classmethod
    def _get_parent_class(cls):
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return Pod

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        if 'comp/' in dn:
            return dn.split('comp/prov-VMware/ctrlr-[DC1]-vcenter1/hv-')[0]
        else:
            return dn.split('topology/lsnode-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        if 'comp/' in dn:
            name = dn.split('comp/prov-VMware/ctrlr-[DC1]-vcenter1/hv-')[1]
        else:
            name = dn.split('topology/lsnode-')[1]
        return name

    @classmethod
    def _get_apic_classes(cls):
        """
        returns list of all apic classes used to build this toolkit class
        :return:
        """
        return ['fabricLooseNode', 'compHv', 'fabricLooseLink', 'pcAggrIf',
                'fabricProtLooseLink', 'pcRsMbrIfs', 'lldpAdjEp']

    def getRole(self):
        """ retrieves the node role
        :returns: role
        """
        return self.role

    @property
    def role(self):
        """
        Getter for role.
        :return: role
        """
        return self._role

    @role.setter
    def role(self, value):
        """
        Setter for role.  Will check that only valid roles are used
        :param value: role
        :return:None
        """
        valid_roles = [None, 'external_switch']
        if value not in valid_roles:
            raise ValueError("role must be one of " + str(valid_roles) + ' found ' + str(value))
        self._role = value

    @classmethod
    def get_event(cls, session):
        """
        not yet fully implemented
        """
        urls = cls._get_subscription_urls()
        for url in urls:
            if not session.has_events(url):
                continue
            event = session.get_event(url)
            for class_name in cls._get_apic_classes():
                if class_name in event['imdata'][0]:
                    break
            if class_name == "fabricLooseNode" or class_name == "compHv":
                attributes = event['imdata'][0][class_name]['attributes']
                status = str(attributes['status'])
                dn = str(attributes['dn'])
                if status == 'created':
                    name = str(attributes['name'])
                else:
                    name = cls._get_name_from_dn(dn)
                obj = cls(name, parent=None)
                if url == "/api/class/fabricLooseNode.json?subscription=yes":
                    obj._populate_physical_from_attributes(attributes)
                elif url == "/api/class/compHv.json?subscription=yes":
                    obj._populate_virtual_from_attributes(attributes)
                obj._get_system_info(session)
                if status == 'deleted':
                    obj.mark_as_deleted()
                return obj
            return

    @classmethod
    def _get_physical_switches(cls, session, parent):
        """Look for loose nodes and build an object for each one.
        """

        # if parent:
        # if not isinstance(parent, Topology):
        # raise TypeError('An instance of Topology class is required')
        lnode_query_url = ('/api/node/class/fabricLooseNode.json?'
                           'query-target=self')
        lnodes = []
        ret = session.get(lnode_query_url)
        lnode_data = ret.json()['imdata']

        for apic_node in lnode_data:
            if 'fabricLooseNode' in apic_node:
                external_switch = cls(apic_node['fabricLooseNode']['attributes']['sysName'])
                external_switch._populate_physical_from_attributes(apic_node['fabricLooseNode']['attributes'])
                external_switch._get_system_info(session)

                if parent:
                    if isinstance(parent, cls._get_parent_class()):
                        external_switch._parent = parent
                        external_switch._parent.add_child(external_switch)

                lnodes.append(external_switch)

        return lnodes

    def _populate_physical_from_attributes(self, attr):
        self.dn = str(attr['dn'])
        self.name = str(attr['sysName'])
        self.id = str(attr['id'])
        self.status = str(attr['status'])
        self.oper_issues = str(attr['operIssues'])
        self.descr = str(attr['sysDesc'])

    @classmethod
    def _get_virtual_switches(cls, session, parent):
        """will find virtual switch nodes and return a list of such objects.
        """

        class_query_url = '/api/node/class/compHv.json?query-target=self'
        vnodes = []
        ret = session.get(class_query_url)
        vnode_data = ret.json()['imdata']

        for apic_node in vnode_data:

            if 'compHv' in apic_node:
                external_switch = cls(apic_node['compHv']['attributes']['name'])
                external_switch._populate_virtual_from_attributes(apic_node['compHv']['attributes'])
                external_switch._get_system_info(session)

                if parent:
                    if isinstance(parent, cls._get_parent_class()):
                        external_switch._parent = parent
                        external_switch._parent.add_child(external_switch)

                vnodes.append(external_switch)

        return vnodes

    def _populate_virtual_from_attributes(self, attr):

        self.dn = str(attr['dn'])
        self.name = str(attr['name'])
        self.descr = str(attr['descr'])
        self.type = str(attr['type'])
        self.state = str(attr['state'])
        self.guid = str(attr['guid'])
        self.oid = str(attr['oid'])

    @classmethod
    def get(cls, session, parent=None):
        """Gets all of the loose nodes from the APIC.

        :param session: APIC session
        :param parent: optional parent object of type Topology
        :returns: list of ENodes
        """
        cls.check_session(session)
        cls.check_parent(parent)

        enodes = cls._get_physical_switches(session, parent)
        enodes.extend(cls._get_virtual_switches(session, parent))
        return enodes

    @staticmethod
    def _get_dn(session, dn):
        """
        Will get the object that dn refers to.
        """
        mo_query_url = '/api/mo/' + dn + '.json?query-target=self'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        return node_data

    @staticmethod
    def _get_dn_children(session, dn):
        """
        Will get the children of the specified dn
        """

        mo_query_url = '/api/mo/' + dn + '.json?query-target=children'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        return node_data

    def _get_system_info(self, session):
        """This routine will fill in various other attributes of the loose node
        :param session:
        """
        mo_query_url = '/api/mo/' + self.dn + '.json?query-target=children'
        ret = session.get(mo_query_url)
        node_data = ret.json()['imdata']
        lldp_dn = None
        for node_info in node_data:
            if 'fabricLooseLink' in node_info:
                dn = node_info['fabricLooseLink']['attributes']['portDn']
                name = dn.split('/')
                pod = name[1].split('-')[1]
                node = str(name[2].split('-')[1])
                if 'phys' in name[4]:
                    result = re.search(r'phys-\[(.+)\]', dn)
                    lldp_dn = 'topology/pod-' + pod + '/node-' + \
                              node + '/sys/lldp/inst/if-[' + result.group(1) + ']/adj-1'
                else:
                    agg_port_data = ExternalSwitch._get_dn(session, dn)
                    if agg_port_data:
                        if 'pcAggrIf' in agg_port_data[0]:
                            port = agg_port_data[0]['pcAggrIf']['attributes']['lastBundleMbr']
                            lldp_dn = 'topology/pod-' + pod + '/node-' + \
                                      node + '/sys/lldp/inst/if-[' + port + ']/adj-1'

            if 'fabricProtLooseLink' in node_info:
                dn = node_info['fabricProtLooseLink']['attributes']['portDn']
                name = dn.split('/')
                pod = name[1].split('-')[1]
                node = str(name[2].split('-')[1])
                lldp_dn = 'topology/pod-' + pod + '/node-' + node + '/sys/lldp/inst/if-['
                if dn:
                    link = ExternalSwitch._get_dn_children(session, dn)
                    for child in link:
                        if 'pcRsMbrIfs' in child:
                            port = child['pcRsMbrIfs']['attributes']['tSKey']
                            lldp_dn = lldp_dn + port + ']/adj-1'

        if lldp_dn:
            lldp_data = ExternalSwitch._get_dn(session, lldp_dn)
        else:
            lldp_data = []

        if lldp_data:
            if 'lldpAdjEp' in lldp_data[0]:
                self.ip = str(lldp_data[0]['lldpAdjEp']['attributes']['mgmtIp'])
                self.name = str(lldp_data[0]['lldpAdjEp']['attributes']['sysName'])

                chassis_id_t = lldp_data[0]['lldpAdjEp']['attributes']['chassisIdT']
                if chassis_id_t == 'mac':
                    self.mac = str(lldp_data[0]['lldpAdjEp']['attributes']['chassisIdV'])
                else:
                    self.mac = str(lldp_data[0]['lldpAdjEp']['attributes']['mgmtPortMac'])

        self.state = 'unknown'

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name == other.name
        return NotImplemented


class Link(BaseACIPhysObject):
    """Link class, equivalent to the fabricLink object in APIC"""

    def __init__(self, name=None, parent=None):
        """
            :param parent: optional parent object

            """
        super(Link, self).__init__(parent=parent)
        self.node1 = None
        self.slot1 = None
        self.port1 = None
        self.node2 = None
        self.slot2 = None
        self.port2 = None
        self.linkstate = None
        self.linkstatus = None
        self.pod = None
        self.link = None
        self.descr = None
        if isinstance(parent, str):
            raise TypeError("Parent object can't be a string")
        self.type = 'link'
        self._session = None
        logging.debug('Creating %s %s', self.__class__.__name__,
                      'pod-%s link-%s' % (self.pod, self.link))
        # self._common_init(parent)

    @staticmethod
    def _get_parent_class():
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return Pod

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['fabricLink']

        return resp

    @classmethod
    def get(cls, session, parent_pod=None, node_id=None):
        """Gets all of the Links from the APIC.  If the parent_pod is specified,
        only links of that pod will be retrieved. If the parent_pod is a Pod object
        then the links will be added as children of that pod.

        If node is specified, then only links of that originate
        at the specific node will be returned.
        If node is specified, pod must be specified.

        :param session: APIC session
        :param parent_pod: Optional parent Pod object or identifier string.
        :param node_id: Optional node number string

        :returns: list of links
        """
        cls.check_session(session)

        pod_id = None
        if parent_pod:
            if not isinstance(parent_pod, cls._get_parent_class()) and not isinstance(parent_pod, str):
                raise TypeError('An instance of Pod class or a pod number string is required')

            if isinstance(parent_pod, Pod):
                pod_id = parent_pod.pod
            else:
                pod_id = parent_pod

        interface_query_url = '/api/node/class/fabricLink.json?query-target=self'
        if not parent_pod:
            interface_query_url = '/api/node/class/fabricLink.json?query-target=self'
        elif pod_id:
            if node_id:
                interface_query_url = ('/api/node/class/fabricLink.json?'
                                       'query-target=self&query-target-filter=eq(fabricLink.n1,"'
                                       + node_id + '")')
            else:
                interface_query_url = '/api/node/class/fabricLink.json?query-target=self'
        links = []
        ret = session.get(interface_query_url)
        link_data = ret.json()['imdata']
        for apic_link in link_data:
            if 'fabricLink' in apic_link:
                link = Link()
                link._session = session
                link._populate_from_attributes(apic_link['fabricLink']['attributes'])
                if pod_id:
                    if link.pod == pod_id:
                        if isinstance(parent_pod, Pod):
                            link._parent = parent_pod
                            link._parent.add_child(link)
                        links.append(link)
                else:
                    links.append(link)
        return links

    def _populate_from_attributes(self, attributes):
        """ populate various additional attributes """

        self.linkstate = attributes['linkState']
        self.linkstatus = attributes['status']
        self.dn = str(attributes['dn'])
        self.modify_time = str(attributes['modTs'])
        self.node1 = str(attributes['n1'])
        self.slot1 = str(attributes['s1'])
        self.port1 = str(attributes['p1'])
        self.node2 = str(attributes['n2'])
        self.slot2 = str(attributes['s2'])
        self.port2 = str(attributes['p2'])
        (pod, link) = Link._parse_dn(self.dn)
        self.pod = pod
        self.link = link
        self.name = 'n{0}/s{1}/p{2}_n{3}/s{4}/p{5}'.format(self.node1,
                                                           self.slot1,
                                                           self.port1,
                                                           self.node2,
                                                           self.slot2,
                                                           self.port2)

    def __str__(self):
        text = 'n%s/s%s/p%s-n%s/s%s/p%s' % (self.node1, self.slot1,
                                            self.port1, self.node2, self.slot2, self.port2)
        return text

    def __eq__(self, other):
        """ Two links are considered equal if their class type is the
        same and the end points match.  The link ids are not
        checked.
        """
        if isinstance(other, self.__class__):
            key_attrs = attrgetter('pod', 'node1', 'slot1', 'port1')
            return key_attrs(self) == key_attrs(other)
        return NotImplemented

    def get_node1(self):
        """Returns the Node object that corresponds to the first
        node of the link.  The Node must be a child of
        the Pod that this link is a member of, i.e. it
        must already have been read from the APIC.  This can
        most easily be done by populating the entire
        physical heirarchy from the Pod down.

        :returns: Node object at first end of link
        """
        return self._get_node(1)

    def get_node2(self):
        """Returns the Node object that corresponds to the
        second node of the link.  The Node must be a child of
        the Pod that this link is a member of, i.e. it must
        already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Node object at second end of link
        """
        return self._get_node(2)

    def _get_node(self, node_number):
        """Common implementation of get_node1() and get_node2()"""
        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")
        target_node = {1: self.node1, 2: self.node2}[node_number]
        matching_nodes = (
            node for node in self._parent.get_children(Node)
            if node == target_node
        )
        return next(matching_nodes, None)

    def get_slot1(self):
        """Returns the Linecard object that corresponds to the
        first slot of the link.  The Linecard must be a child of
        the Node in the Pod that this link is a member of,
        i.e. it must already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Linecard object at first end of link
        """
        return self._get_slot(1)

    def get_slot2(self):
        """Returns the Linecard object that corresponds to the
         second slot of the link.  The Linecard must be a child of
        the Node in the Pod that this link is a member of,
        i.e. it must already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Linecard object at second end of link
        """
        return self._get_slot(2)

    def _get_slot(self, slot_number):
        """Common implementation of get_slot1() and get_slot2()"""
        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")
        target_slot = {1: self.slot1, 2: self.slot2}[slot_number]
        node = self._get_node(slot_number)
        linecards = node.get_children(Linecard) if node else ()
        matching_linecards = (
            linecard for linecard in linecards if linecard.slot == target_slot
        )
        return next(matching_linecards, None)

    def get_port1(self):
        """Returns the Interface object that corresponds to the
        first port of the link.  The port must be a child of
        the Linecard in the Node in the Pod that this link is a
        member of, i.e. it must already have been read from the APIC.  This can
        most easily be done by populating the entire physical
        heirarchy from the Pod down.

        :returns: Interface object at first end of link
        """
        return self._get_port(1)

    def get_port2(self):
        """
        Returns the Interface object that corresponds to the second port of
        the link. The port must be a child of the Linecard in the Node in
        the Pod that this link is a member of, i.e. it must already have been
        read from the APIC.  This can most easily be done by populating the
        entire physical heirarchy from the Pod down.

        :returns: Interface object at second end of link
        """
        return self._get_port(2)

    def _get_port(self, port_number):
        """Common implementation of get_port1() and get_port2()"""
        if not self._parent:
            raise TypeError("Parent pod must be specified in order to get node")
        target_port = {1: self.port1, 2: self.port2}[port_number]
        linecard = self._get_slot(port_number)
        interfaces = linecard.get_children(Interface) if linecard else ()
        matching_interfaces = (
            interface for interface in interfaces
            if interface.port == target_port
        )
        return next(matching_interfaces, None)

    def get_port_id1(self):
        """
        Returns the port ID of the first end of the link in the
        format pod/node/slot/port

        :returns: port ID string
        """
        return '{0}/{1}/{2}/{3}'.format(self.pod, self.node1, self.slot1, self.port1)

    def get_port_id2(self):
        """
        Returns the port ID of the second end of the link in the
        format pod/node/slot/port

        :returns: port ID string
        """
        return '{0}/{1}/{2}/{3}'.format(self.pod, self.node2, self.slot2, self.port2)

    @staticmethod
    def _parse_dn(dn):
        """Parses the pod and link number from a
           distinguished name of the link.

           :param dn: dn string of the link
           :returns: (pod, link)
        """
        name = dn.split('/')
        pod = str(name[1].split('-')[1])
        link = str(name[2].split('-')[1])

        return pod, link

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/lnkcnt-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/lnkcnt-')[1].split('/')[0]
        return name


class Interface(BaseInterface):
    """This class defines a physical interface.
    """

    def __init__(self, interface_type, pod, node, module, port,
                 parent=None, session=None, attributes=None):

        self._session = session
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = copy.deepcopy(attributes)
        self.interface_type = str(interface_type)
        self.pod = str(pod)
        self.node = str(node)
        self.module = str(module)
        self.port = str(port)

        self.if_name = self.interface_type + ' ' + self.pod + '/'
        self.if_name += self.node + '/' + self.module + '/' + self.port
        super(Interface, self).__init__(self.if_name, None)
        self._session = session
        self.porttype = ''
        self.adminstatus = ''  # up or down
        self.speed = '10G'  # 100M, 1G, 10G or 40G
        self.mtu = ''
        self._cdp_config = None
        self._lldp_config = None
        self.type = 'interface'
        self.attributes['type'] = 'interface'
        self.id = interface_type + module + '/' + port

        self._parent = parent
        if parent:
            self._parent.add_child(self)
        try:
            dn = self.attributes['dn']
        except KeyError:
            dn = 'topology/pod-%s/node-%s/sys/phys-[%s%s/%s]' % (pod, node, interface_type, module, port)
        self.stats = InterfaceStats(self, dn)

        self.attributes['interface_type'] = str(interface_type)
        self.attributes['pod'] = str(pod)
        self.attributes['node'] = str(node)
        self.attributes['module'] = str(module)
        self.attributes['port'] = str(port)
        self.attributes['if_name'] = self.if_name

    def is_interface(self):
        """
        Returns whether this instance is considered an interface.

        :returns: True
        """
        return True

    def is_cdp_enabled(self):
        """
        Returns whether this interface has CDP configured as enabled.

        :returns: True or False
        """
        return self._cdp_config == 'enabled'

    def is_cdp_disabled(self):
        """
        Returns whether this interface has CDP configured as disabled.

        :returns: True or False
        """
        return self._cdp_config == 'disabled'

    def enable_cdp(self):
        """
        Enables CDP on this interface.
        """
        self._cdp_config = 'enabled'

    def disable_cdp(self):
        """
        Disables CDP on this interface.
        """
        self._cdp_config = 'disabled'

    def is_lldp_enabled(self):
        """
        Returns whether this interface has LLDP configured as enabled.

        :returns: True or False
        """
        return self._lldp_config == 'enabled'

    def is_lldp_disabled(self):
        """
        Returns whether this interface has LLDP configured as disabled.

        :returns: True or False
        """
        return self._lldp_config == 'disabled'

    def enable_lldp(self):
        """
        Enables LLDP on this interface.
        """
        self._lldp_config = 'enabled'

    def disable_lldp(self):
        """
        Disables LLDP on this interface.
        """
        self._lldp_config = 'disabled'

    def get_type(self):
        """
        getter method for object.type

        :return: the type
        """
        return self.type

    @staticmethod
    def get_serial():
        """
        getter for the serial number

        :return: None
        """
        return None

    @staticmethod
    def get_url():
        """
        Gets URLs for physical domain, fabric, and infra.

        :return:
        """
        phys_domain_url = '/api/mo/uni.json'
        fabric_url = '/api/mo/uni/fabric.json'
        infra_url = '/api/mo/uni.json'
        return phys_domain_url, fabric_url, infra_url

    def _get_name_for_json(self):
        return '%s-%s-%s-%s' % (self.pod, self.node,
                                self.module, self.port)

    def push_to_apic(self, session):
        """
        Push the configuration to the APIC

        :param session: the instance of Session used for APIC communication
        :returns: Response class instance from the requests library.\
                  response.ok is True if request is sent successfully.
        """
        for i in range(0, len(self.get_url())):
            if self.get_json()[i] is not None and self.get_url()[i] is not None:
                resp = session.push_to_apic(self.get_url()[i],
                                            self.get_json()[i])
                if not resp.ok:
                    print('%% Error: Could not push configuration to APIC for url:', self.get_url()[i])
                    return resp
        return resp

    def get_json(self):
        """
        Get the json for an interface.  Returns a tuple since the json is
        required to be sent in multiple posts. A call to get_url will return
        the URLs which the JSON can be sent.

        :return: Tuple containing the phys_domain, fabric, infra JSONs
        """
        fabric = None
        # Physical Domain json
        vlan_ns_dn = 'uni/infra/vlanns-allvlans-static'
        vlan_ns_ref = {'infraRsVlanNs': {'attributes':
                                         {'tDn': vlan_ns_dn},
                                         'children': []}}
        phys_domain = {'physDomP': {'attributes': {'name': 'allvlans'},
                                    'children': [vlan_ns_ref]}}

        # Infra json
        infra = {'infraInfra': {'attributes': {}, 'children': []}}
        node_profile, accport_selector = self.get_port_selector_json()
        infra['infraInfra']['children'].append(node_profile)
        infra['infraInfra']['children'].append(accport_selector)
        speed_name = 'speed%s' % self.speed
        hifpol_dn = 'uni/infra/hintfpol-%s' % speed_name
        speed = {'fabricHIfPol': {'attributes': {'autoNeg': 'on',
                                                 'dn': hifpol_dn,
                                                 'name': speed_name,
                                                 'speed': self.speed},
                                  'children': []}}
        infra['infraInfra']['children'].append(speed)
        name = self._get_name_for_json()
        accportgrp_dn = 'uni/infra/funcprof/accportgrp-%s' % name
        speed_attr = {'tnFabricHIfPolName': speed_name}
        speed_children = {'infraRsHIfPol': {'attributes': speed_attr,
                                            'children': []}}
        cdp_children = None
        if self._cdp_config is not None:
            cdp_data = {'tnCdpIfPolName': 'CDP_%s' % self._cdp_config}
            cdp_children = {'infraRsCdpIfPol': {'attributes': cdp_data}}
        lldp_children = None
        if self._lldp_config is not None:
            lldp_data = {'tnLldpIfPolName': 'LLDP_%s' % self._lldp_config}
            lldp_children = {'infraRsLldpIfPol': {'attributes': lldp_data}}
        att_ent_dn = 'uni/infra/attentp-allvlans'
        att_ent_p = {'infraRsAttEntP': {'attributes': {'tDn': att_ent_dn},
                                        'children': []}}
        speed_ref = {'infraAccPortGrp': {'attributes': {'dn': accportgrp_dn,
                                                        'name': name},
                                         'children': [speed_children,
                                                      att_ent_p]}}
        if cdp_children is not None:
            speed_ref['infraAccPortGrp']['children'].append(cdp_children)
        if lldp_children is not None:
            speed_ref['infraAccPortGrp']['children'].append(lldp_children)
        speed_ref = {'infraFuncP': {'attributes': {}, 'children': [speed_ref]}}
        infra['infraInfra']['children'].append(speed_ref)

        phys_dom_dn = 'uni/phys-allvlans'
        rs_dom_p = {'infraRsDomP': {'attributes': {'tDn': phys_dom_dn}}}
        infra_att_entity_p = {'infraAttEntityP': {'attributes':
                                                  {'name': 'allvlans'},
                                                  'children': [rs_dom_p]}}
        infra['infraInfra']['children'].append(infra_att_entity_p)

        if self._cdp_config is not None:
            cdp_if_pol = {'cdpIfPol': {'attributes': {'adminSt': self._cdp_config,
                                                      'name': 'CDP_%s' % self._cdp_config}}}
            infra['infraInfra']['children'].append(cdp_if_pol)

        if self._lldp_config is not None:
            lldp_if_pol = {'lldpIfPol': {'attributes': {'adminRxSt': self._lldp_config,
                                                        'adminTxSt': self._lldp_config,
                                                        'name': 'LLDP_%s' % self._lldp_config}}}
            infra['infraInfra']['children'].append(lldp_if_pol)

        if self.adminstatus != '':
            adminstatus_attributes = {'tDn': self._get_path()}
            if self.adminstatus == 'up':
                admin_dn = 'uni/fabric/outofsvc/rsoosPath-['
                admin_dn = admin_dn + self._get_path() + ']'
                adminstatus_attributes['dn'] = admin_dn
                adminstatus_attributes['status'] = 'deleted'
            else:
                adminstatus_attributes['lc'] = 'blacklist'
            adminstatus_json = {'fabricRsOosPath':
                                {'attributes': adminstatus_attributes,
                                 'children': []}}
            fabric = {'fabricOOServicePol': {'children': [adminstatus_json]}}

        fvns_encap_blk = {'fvnsEncapBlk': {'attributes': {'name': 'encap',
                                                          'from': 'vlan-1',
                                                          'to': 'vlan-4092'}}}
        fvns_vlan_inst_p = {'fvnsVlanInstP': {'attributes':
                                              {'name': 'allvlans',
                                               'allocMode': 'static'},
                                              'children': [fvns_encap_blk]}}
        infra['infraInfra']['children'].append(fvns_vlan_inst_p)

        return phys_domain, fabric, infra

    def _get_path(self):
        """Get the path of this interface used when communicating with
           the APIC object model.
        """
        return 'topology/pod-%s/paths-%s/pathep-[eth%s/%s]' % (self.pod,
                                                               self.node,
                                                               self.module,
                                                               self.port)

    @staticmethod
    def parse_name(name):
        """Parses a name that is of the form:
        <type> <pod>/<mod>/<port>
        :param name: Distinguished Name (dn)
        """
        interface_type = name.split()[0]
        name = name.split()[1]
        (pod, node, module, port) = name.split('/')
        return interface_type, pod, node, module, port

    @classmethod
    def create_from_name(cls, name):
        return cls(*cls.parse_name(name))

    @staticmethod
    def _parse_physical_dn(dn):
        """
        Handles DNs that look like the following:
        topology/pod-1/node-103/sys/phys-[eth1/12]
        """
        name = dn.split('/')
        pod = name[1].split('-')[1]
        node = name[2].split('-')[1]
        module = name[4].split('[')[1]
        interface_type = module[:3]
        module = module[3:]
        port = name[5].split(']')[0]

        return interface_type, pod, node, module, port

    @staticmethod
    def _parse_path_dn(dn):
        """
        Handles DNs that look like the following:
        topology/pod-1/paths-102/pathep-[eth1/12]
        topology/pod-1/paths-1012/pathep-[c01-nas-n06-IfPolGrp]
        """
        pod = dn.partition('/pod-')[-1].split('/')[0]
        node = dn.partition('/paths-')[-1].split('/')[0]
        port_name = dn.partition('/pathep-[')[-1].split(']')[0]
        if port_name[:3] == 'eth':
            module = port_name[3:].split('/')[0]
            port = port_name[3:].split('/')[1]
            interface_type = 'eth'
        else:
            module = ''
            port = port_name
            interface_type = 'pol'

        # name = dn.split('/')
        # module = name[3].split('[')[1]
        # interface_type = module[:3]
        # module = module[3:]
        # port = name[4].split(']')[0]

        return interface_type, pod, node, module, port

    @staticmethod
    def _parse_extpath_dn(dn):
        pod = dn.partition('/pod-')[-1].split('/')[0]
        node = dn.partition('/paths-')[-1].split('/')[0]
        module = dn.partition('/extpaths-')[-1].split('/')[0]
        interface = dn.partition('/pathep-[')[-1].partition(']')[0]
        interface_type = interface[:3]
        module = module + ':' + interface[3:].partition('/')[0]
        port = interface[3:].partition('/')[-1]

        return interface_type, pod, node, module, port

    @classmethod
    def parse_dn(cls, dn):
        """
        Parses the pod, node, module, port from a distinguished name
        of the interface.

        :param dn: String containing the interface distinguished name
        :returns: interface_type, pod, node, module, port
        """
        if 'sys' in dn.split('/'):
            return cls._parse_physical_dn(dn)
        elif '/extpaths-' in dn:
            return cls._parse_extpath_dn(dn)
        else:
            return cls._parse_path_dn(dn)

    @staticmethod
    def _get_discoveryprot_policies(session, prot):
        """
        :param prot: String containing either 'cdp' or 'lldp'
        """
        prot_policies = {}
        if prot == 'cdp':
            prot_class = 'cdpIfPol'
        elif prot == 'lldp':
            prot_class = 'lldpIfPol'
        else:
            raise ValueError

        query_url = '/api/node/class/%s.json?query-target=self' % prot_class
        ret = session.get(query_url)
        prot_data = ret.json()['imdata']
        for policy in prot_data:
            if ('%s' % prot_class) in policy:
                attributes = policy['%s' % prot_class]['attributes']
                if prot == 'cdp':
                    prot_policies[attributes['name']] = attributes['adminSt']
                else:
                    prot_policies[attributes['name']] = attributes['adminTxSt']
        return prot_policies

    @staticmethod
    def _get_discoveryprot_relations(session, interfaces, prot, prot_policies):
        if prot == 'cdp':
            prot_relation_class = 'l1RsCdpIfPolCons'
            prot_relation_dn_class = '/cdpIfP-'
            prot_relation_dn = '/rscdpIfPolCons'
        elif prot == 'lldp':
            prot_relation_class = 'l1RsLldpIfPolCons'
            prot_relation_dn_class = '/lldpIfP-'
            prot_relation_dn = '/rslldpIfPolCons'
        else:
            raise ValueError

        query_url = ('/api/node/class/l1PhysIf.json?query-target=subtree&'
                     'target-subtree-class=%s' % prot_relation_class)
        ret = session.get(query_url)
        prot_data = ret.json()['imdata']
        for prot_relation in prot_data:
            if prot_relation_class in prot_relation:
                attributes = prot_relation[prot_relation_class]['attributes']
                policy_name = attributes['tDn'].split(prot_relation_dn_class)[1]
                intf_dn = attributes['dn'].split(prot_relation_dn)[0]
                search_intf = Interface(*Interface._parse_physical_dn(intf_dn))
                for intf in interfaces:
                    if intf == search_intf:
                        if prot_policies[policy_name] == 'enabled':
                            if prot == 'cdp':
                                intf.enable_cdp()
                            else:
                                intf.enable_lldp()
                        else:
                            if prot == 'cdp':
                                intf.disable_cdp()
                            else:
                                intf.disable_lldp()
                        break
        return interfaces

    @classmethod
    def _get_parent_class(cls):
        """
        Gets the acitoolkit class of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: class of parent object
        """
        return Linecard

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('/phys-')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('/phys-')[1].split('/')[0]
        return name

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        resp = ['l1PhysIf', 'ethpmPhysIf', 'l1RsCdpIfPolCons', 'l1RsLldpIfPolCons',
                'cdpIfPol', 'lldpIfPol']

        return resp

    @classmethod
    def get(cls, session, pod_parent=None, node=None, module=None, port=None):
        """
        Gets all of the physical interfaces from the APIC if no parent is
        specified. If a parent of type Linecard is specified, then only
        those interfaces on that linecard are returned and they are also
        added as children to that linecard.

        If the pod, node, module and port are specified, then only that
        specific interface is read.

        If the pod and node are specified, then only those interfaces are
        read

        :param session: the instance of Session used for APIC communication
        :param pod_parent: Linecard instance to limit interfaces or pod\
                           number (optional)
        :param node: Node id string.  This specifies the switch to read.\
                     (optional)
        :param module: Module id string.  This specifies the module or\
                       slot of the port. (optional)
        :param port: Port number.  This is the port to read. (optional)

        :returns: list of Interface instances
        """
        if not isinstance(session, Session):
            raise TypeError('An instance of Session class is required')

        if port:
            if not isinstance(port, str):
                raise TypeError('When specifying a specific port, the port'
                                ' must be a identified by a string')
            if not isinstance(module, str):
                raise TypeError(('When specifying a specific port, the module'
                                 ' must be identified by a string'))
            if not isinstance(node, str):
                raise TypeError(('When specifying a specific port, the node '
                                 'must be identified by a string'))
            if not isinstance(pod_parent, str):
                raise TypeError(('When specifying a specific port, the pod '
                                 'must be identified by a string'))
        # Handle case where only node is specified
        elif node:
            if not isinstance(pod_parent, str):
                raise TypeError(('When specifying a specific node, the pod '
                                 'must be identified by a string'))
        else:
            if pod_parent:
                if not isinstance(pod_parent, cls._get_parent_class()):
                    raise TypeError('Interface parent must be a {0} object'.format(cls._get_parent_class()))

        cdp_policies = Interface._get_discoveryprot_policies(session, 'cdp')
        lldp_policies = Interface._get_discoveryprot_policies(session, 'lldp')

        if port:
            dist_name = 'topology/pod-{0}/node-{1}/sys/phys-[eth{2}/{3}]'.format(pod_parent, node, module, port)
            interface_query_url = ('/api/mo/' + dist_name + '.json?query-target=self')
            eth_query_url = ('/api/mo/' + dist_name + '/phys.json?query-target=self')
        # add the case where we return all of the ports of a given node
        elif node:
            dist_name = 'topology/pod-1/node-{0}/sys'.format(node)
            interface_query_url = ('/api/mo/' + dist_name + '.json?query-target=children&target-subtree-class=l1PhysIf')
            eth_query_url = ('/api/mo/' + dist_name + '.json?query-target=subtree&target-subtree-class=ethpmPhysIf')

        else:
            interface_query_url = '/api/node/class/l1PhysIf.json?query-target=self'
            eth_query_url = '/api/node/class/ethpmPhysIf.json?query-target=self'

        ret = session.get(interface_query_url)
        interface_data = ret.json()['imdata']

        # also get information about the ethernet interface
        eth_resp = session.get(eth_query_url)
        resp = []
        eth_data = eth_resp.json()['imdata']

        # re-index the ethernet port info so it can be referenced by dn
        eth_data_dict = {}
        for obj in eth_data:
            eth_data_dict[obj['ethpmPhysIf']['attributes']['dn']] = obj['ethpmPhysIf']['attributes']

        for interface in interface_data:
            if 'l1PhysIf' in interface:
                attributes = {}
                dist_name = str(interface['l1PhysIf']['attributes']['dn'])
                attributes['dn'] = dist_name

                porttype = str(interface['l1PhysIf']['attributes']['portT'])
                attributes['porttype'] = porttype
                adminstatus = str(interface['l1PhysIf']['attributes']['adminSt'])
                attributes['adminstatus'] = adminstatus
                speed = str(interface['l1PhysIf']['attributes']['speed'])
                attributes['speed'] = speed
                mtu = str(interface['l1PhysIf']['attributes']['mtu'])
                attributes['mtu'] = mtu
                identifier = str(interface['l1PhysIf']['attributes']['id'])
                attributes['id'] = identifier
                attributes['monPolDn'] = str(interface['l1PhysIf']['attributes']['monPolDn'])
                attributes['name'] = str(interface['l1PhysIf']['attributes']['name'])
                attributes['descr'] = str(interface['l1PhysIf']['attributes']['descr'])
                attributes['usage'] = str(interface['l1PhysIf']['attributes']['usage'])
                try:
                    attributes['operSt'] = eth_data_dict[dist_name + '/phys']['operSt']
                    attributes['operSpeed'] = eth_data_dict[dist_name + '/phys']['operSpeed']
                except KeyError:
                    attributes['operSt'] = 'unknown'
                    attributes['operSpeed'] = 'unknown'

                interface_obj = ACI._interface_from_dn(dist_name)
                for attribute in attributes:
                    interface_obj.attributes[attribute] = attributes[attribute]
                interface_obj._session = session
                interface_obj.porttype = porttype
                interface_obj.adminstatus = adminstatus
                interface_obj.speed = speed
                interface_obj.mtu = mtu
                interface_obj.dn = dist_name

                if not isinstance(pod_parent, str) and pod_parent:
                    if interface_obj.pod == pod_parent.pod and interface_obj.node == pod_parent.node and \
                            interface_obj.module == pod_parent.slot:
                        interface_obj._parent = pod_parent
                        interface_obj._parent.add_child(interface_obj)
                        resp.append(interface_obj)
                else:
                    resp.append(interface_obj)

        resp = Interface._get_discoveryprot_relations(session, resp, 'cdp', cdp_policies)
        resp = Interface._get_discoveryprot_relations(session, resp, 'lldp', lldp_policies)
        return resp

    def __str__(self):
        attr_names = 'if_name', 'porttype', 'adminstatus', 'speed', 'mtu'
        return '\t'.join(attrgetter(*attr_names)(self))

    def __eq__(self, other):
        # TODO: simplify and isinstance
        if not isinstance(self, type(other)):
            return False
        if (self.interface_type == other.interface_type and
                self.pod == other.pod and
                self.node == other.node and
                self.module == other.module and
                self.port == other.port):
            return True
        return False

    def get_adjacent_port(self):
        """
        This will return the port ID of the port at the other end of the link.

        For Access ports, it will only have a result if it is connected to
        a controller node.

        If no link is found, then the result will be None.  That does not mean
        that nothing is connected, just that a fabric link is not connected.

        :returns : Port ID string
        """
        result = None

        links = Link.get(self._session, '1', self.node)
        for link in links:
            if link.port1 == self.port:
                return link.get_port_id2()
        return result


class WorkingData(object):
    """
    This class will hold the entire json tree
    from topSystem down, for a switch.
    The attributes of a specific class can be retrieved
    in which case it will be as a list of objects.
    It will allow all children of an object to be retrieved
    result is list of objects
    It will allow an instance of a class to be retrieved returned
    as a single object.
    """

    def __init__(self, session=None, toolkit_class=None, url=None, deep=False, include_concrete=False):

        self.by_class = {}
        self.by_dn = {}
        self.vnid_dict = {}
        self.ctx_dict = {}
        self.bd_dict = {}
        self.rawjson = {}
        self.session = session
        self.add(session, toolkit_class, url, deep, include_concrete)

    def add(self, session=None, toolkit_class=None, url=None, deep=False, include_concrete=False):
        """

        :param session:
        :param toolkit_class:
        :param url:
        :param deep:
        :param include_concrete:
        :return:
        """
        self.session = session
        if session is None:
            return

        if deep:
            apic_classes = toolkit_class.get_deep_apic_classes(include_concrete=include_concrete)
        else:
            # noinspection PyProtectedMember
            apic_classes = toolkit_class._get_apic_classes()
        query_url = url + 'query-target=subtree&target-subtree-class=' + ','.join(apic_classes)

        ret = session.get(query_url)
        ret._content = ret._content.decode().replace('\n', '').encode()
        data = ret.json()['imdata']

        if data:
            self.rawjson = ret.json()['imdata']
        else:
            self.rawjson = None
        if self.rawjson is not None:
            if 'error' not in self.rawjson:
                self._index_objects()

                self.build_vnid_dictionary()

    def _index_objects(self):
        """
        Will index the json by dn and by class for easy reference
        """
        for item in self.rawjson:
            for apic_class in item:
                if apic_class != u'error':
                    self.by_dn[item[apic_class]['attributes']['dn']] = item
                    if apic_class not in self.by_class:
                        self.by_class[apic_class] = []

                    # fix apparent bug in APIC where multiple nodes are returned for the APIC node
                    if apic_class == 'fabricNode':
                        if item[apic_class]['attributes']['role'] in ['leaf', 'spine']:
                            self.by_class[apic_class].append(item)
                        else:
                            if (item[apic_class]['attributes']['role'] == 'controller') \
                                    and (item not in self.by_class[apic_class]):

                                # look through all the objects in 'fabricNode' class and only insert if
                                # this controller not already there.
                                found = False
                                for item_in_class in self.by_class[apic_class]:
                                    if item[apic_class]['attributes']['dn'] == \
                                            item_in_class[apic_class]['attributes']['dn']:
                                        found = True
                                        break
                                if not found:
                                    self.by_class[apic_class].append(item)

                    else:
                        self.by_class[apic_class].append(item)

    def get_class(self, class_name):
        """
        returns all the objects of a given class
        :param class_name: The name of the class you are looking for.
        """
        result = self.by_class.get(class_name)
        if not result:
            return []
        return result

    def get_subtree(self, class_name, dname):
        """
        will return list of matching classes and their attributes

        It will get all classes that
        are classes under dn.
        :param class_name: name of class you are looking for
        :param dname: Distinguished Name (dn)
        """
        result = []

        classes = self.get_class(class_name)
        if classes:
            for class_record in classes:
                for class_id in class_record:
                    obj_dn = class_record[class_id]['attributes']['dn']
                    if obj_dn.startswith(dname + '/'):
                        result.append(class_record)
        return result

    def get_object(self, dname):
        """
        Will return the object specified by dn.
        :param dname: Distinguished Name (dn)
        """
        # start at top
        result = self.by_dn.get(dname)
        if not result:
            return None
        return result

    def build_vnid_dictionary(self):
        """
        Will build a dictionary that is indexed by
        vnid and will return context or bridge_domain
        and the name of that segment.
        :param self:
        """

        # pull in contexts first
        ctx_data = self.get_class('l3Inst')[:]
        ctx_data.extend(self.get_class('l3Ctx')[:])
        for ctx in ctx_data:
            if 'l3Ctx' in ctx:
                class_id = 'l3Ctx'
            else:
                class_id = 'l3Inst'

            if '-' in ctx[class_id]['attributes']['encap']:
                vnid = str(ctx[class_id]['attributes']['encap'].split('-')[1])
            else:
                vnid = str(ctx[class_id]['attributes']['encap'])
            name = str(ctx[class_id]['attributes']['name'])
            record = {'name': name, 'type': 'context'}
            self.vnid_dict[vnid] = record

            # and opposite dictionary
            self.ctx_dict[name] = vnid
        # pull in bridge domains next
        bd_data = self.get_class('l2BD')
        for l2bd in bd_data:
            vnid = str(l2bd['l2BD']['attributes']['fabEncap'].split('-')[1])
            name = str(l2bd['l2BD']['attributes']['name'].split(':')[-1])
            if not name:
                name = vnid
            dname = str(l2bd['l2BD']['attributes']['dn'])
            fields = dname.split('/')
            context_dn = '/'.join(fields[0:-1])
            ctx_data = self.get_object(context_dn)
            if 'l3Ctx' in ctx_data:
                context = str(ctx_data['l3Ctx']['attributes']['name'])
            elif 'l3Inst' in ctx_data:
                context = str(ctx_data['l3Inst']['attributes']['name'])
            else:
                context = None

            record = {'name': name, 'type': 'bd', 'context': context}
            self.vnid_dict[vnid] = record

            # and opposite dictionary
            self.bd_dict[name] = vnid


class Process(BaseACIPhysObject):
    """
    Class to hold information about a process running on a node - either switch or controller
    """

    def __init__(self):
        """

        :return:
        """
        super(Process, self).__init__(name='', parent=None)
        self.id = None
        self.name = None
        self.oper_st = None
        self.cpu_execution_time_ave = None
        self.cpu_invoked = None
        self.cpu_execution_time_max = None
        self.cpu_usage_last = None
        self.cpu_usage_avg = None
        self.mem_alloc_avg = None
        self.mem_alloc_last = None
        self.mem_alloc_max = None
        self.mem_used_avg = None
        self.mem_used_last = None
        self.mem_used_max = None

    @classmethod
    def get(cls, session, parent):
        """

        :param session:
        :param parent:
        :return:
        """
        cls.check_session(session)
        if not isinstance(parent, Node):
            raise TypeError('An instance of Node as the parent is required')

        result = []
        pod = parent.pod
        node = parent.node

        node_dn = 'topology/pod-{0}/node-{1}'.format(pod, node)
        node_query_url = '/api/mo/' + node_dn + '/sys/procsys.json?query-target=children&rsp-subtree-include=stats' \
                                                '&rsp-subtree-class=statsCurr'

        ret = session.get(node_query_url)
        processes = ret.json()['imdata']
        for child in processes:
            if 'procProc' not in child:
                continue
            if child['procProc']:
                process = Process()
                process._populate_from_attributes(child['procProc']['attributes'])
                process._populate_stats(child['procProc']['children'])

                if parent:
                    process._parent = parent
                    process._parent.add_child(process)
                result.append(process)
        return result

    def _populate_from_attributes(self, attr):
        """

        :param attr:
        :return:
        """
        self.id = attr['id']
        self.name = attr['name']
        self.oper_st = attr['operSt']
        self.dn = attr['dn']

    def _populate_stats(self, children):
        """
        Will read the most current stats and populate parameters accordingly
        :param children:
        :return:
        """
        for child in children:

            if 'procProcCPU5min' in child:
                attr = child['procProcCPU5min']['attributes']
                self.cpu_avg_execution_time_avg = attr['avgExecAvg']
                self.cpu_avg_execution_time_max = attr['avgExecMax']
                self.cpu_avg_execution_time_last = attr['avgExecLast']
                self.cpu_max_execution_time_avg = attr['maxExecAvg']
                self.cpu_max_execution_time_max = attr['maxExecMax']
                self.cpu_max_execution_time_last = attr['maxExecLast']
                self.cpu_invoked_avg = attr['invokedAvg']
                self.cpu_invoked_max = attr['invokedMax']
                self.cpu_invoked_last = attr['invokedLast']
                self.cpu_usage_avg = attr['usageAvg']
                self.cpu_usage_max = attr['usageMax']
                self.cpu_usage_last = attr['usageLast']

            if 'procProcMem5min' in child:
                attr = child['procProcMem5min']['attributes']
                self.mem_alloc_avg = attr['allocedAvg']
                self.mem_alloc_max = attr['allocedMax']
                self.mem_alloc_last = attr['allocedLast']
                self.mem_used_avg = attr['usedAvg']
                self.mem_used_max = attr['usedMax']
                self.mem_used_last = attr['usedLast']

    @staticmethod
    def get_table(aci_objects, title='Process'):
        """

        :param aci_objects: list of process objects to build table for
        :param title: Title of the table
        :return: Table
        """
        result = []

        headers = ['Name', 'id', 'Oper State', 'Avg CPU Exec Avg', 'Avg CPU Exec Last',
                   'CPU Usage Avg', 'CPU Usage Last', 'Mem Alloc Avg', 'Mem Alloc Last',
                   'Mem Used Avg', 'Mem Used Last']

        table = []
        for aci_object in aci_objects:
            table.append([
                aci_object.name,
                aci_object.id,
                aci_object.oper_st,
                aci_object.cpu_avg_execution_time_avg,
                aci_object.cpu_avg_execution_time_last,
                aci_object.cpu_usage_avg,
                aci_object.cpu_usage_last,
                aci_object.mem_alloc_avg,
                aci_object.mem_alloc_last,
                aci_object.mem_used_avg,
                aci_object.mem_used_last
            ])

        table = sorted(table, key=itemgetter(0, 1))
        result.append(Table(table, headers, title=title + 'Process CPU and MEM'))

        return result


class PhysicalModel(BaseACIObject):
    """
    This is the root class for the physical part of the network.  It's corrolary is the LogicalModel class.
    It is a container that can hold all of physical model instances.  Initially this is only an instance of Pod.

    From this class, you can populate all of the children classes.
    """

    def __init__(self, session=None, parent=None):
        """
        Initialization method that sets up the Fabric.
        :return:
        """
        if session:
            assert isinstance(session, Session)

        if parent:
            assert isinstance(parent, Fabric)

        super(PhysicalModel, self).__init__(name='', parent=parent)
        self.dn = 'topology'
        self._session = session

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return Fabric

    @staticmethod
    def _get_parent_dn(dn):
        """
        Gets the dn of the parent object
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: string containing dn
        """
        return dn.split('topology')[0]

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        name = dn.split('topology')[1].split('/')[0]
        return name

    @staticmethod
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return [Pod]

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by the acitoolkit class.
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: list of strings containing APIC class names
        """
        return []

    @classmethod
    def get(cls, session=None, parent=None):
        """
        Method to get all of the PhysicalModels.  It will get one and return it in a list.
        :param session:
        :param parent:
        :return: list of PhysicalModel
        """
        physical_model = PhysicalModel(session=session, parent=parent)
        return [physical_model]

    @classmethod
    def get_deep(cls, session, include_concrete=False):
        """
        Will return the atk object and the entire tree under it.
        :param session: APIC session to use
        :param include_concrete: flag to indicate that concrete objects should also be included
        :return:
        """
        atk_objects = cls(session)
        for atk_object in atk_objects:
            atk_object.populate_children(deep=True, include_concrete=include_concrete)
        return atk_objects


class Fabric(BaseACIObject):
    """
    This is the root class for the acitoolkit.  It is a container that
    can hold all of the other instances of the acitoolkit classes.

    From this class, you can populate all of the children classes.
    """

    def __init__(self, session=None, parent=None):
        """
        Initialization method that sets up the Fabric.
        :return:
        """
        # if session:
        #  assert isinstance(session, Session)

        super(Fabric, self).__init__(name='', parent=None)

        self._session = session
        self.dn = '/'

    @staticmethod
    def _get_parent_class():
        """
        Gets the class of the parent object

        :returns: class of parent object
        """
        return None

    @staticmethod
    def _get_name_from_dn(dn):
        """
        Get the instance name from the dn

        :param dn: string containing the distinguished name URL
        :return: string containing the name
        """
        return 'Fabric'

    @staticmethod
    def _get_parent_dn(dn):
        """
        Get the parent DN

        :param dn: string containing the distinguished name URL
        :return: None
        """
        return None

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by the acitoolkit class.
        Meant to be overridden by inheriting classes.
        Raises exception if not overridden.

        :returns: list of strings containing APIC class names
        """
        return []

    @classmethod
    def get(cls, session):
        """

        :param session:
        """
        cls.check_session(session)
        fabric = Fabric(session)
        fabric.name = 'Fabric'
        return [fabric]

    @classmethod
    def get_deep(cls, session, include_concrete=False):
        """
        Will return the entire tree of the fabric.
        :param session: APIC session to use
        :param include_concrete: flag to indicate that concrete objects should also be included
        :return:
        """
        fabrics = cls.get(session)
        fabrics[0].populate_children(deep=True, include_concrete=include_concrete)
        return fabrics

    @staticmethod
    def _get_children_classes():
        """
        Get the acitoolkit class of the children of this object.
        This is meant to be overridden by any inheriting classes that have children.
        If they don't have children, this will return an empty list.
        :return: list of classes
        """
        return [PhysicalModel, ACI.LogicalModel]

    def _define_searchables(self):
        """
        Create all of the searchable terms

        """
        results = super(Fabric, self)._define_searchables()
        results[0].add_term('model', 'physical')

        return results
