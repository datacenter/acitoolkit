# aciFaults.py
"""
This module deals with Fault objects.
"""
from .acibaseobject import BaseACIObject
from jsonschema import validate, ValidationError
import os


class Faults(BaseACIObject):
    """
    A class for Fault objects
    """
    def __init__(self):
        self.type = None
        self.subject = None
        self.severity = None
        self.domain = None
        self.descr = None
        self.dn = None
        self.cause = None
        self.rule = None

    def is_deleted(self):
        """
        Not supported

        :raises: AttributeError
        """
        raise AttributeError('\nNot supported on Fault objects.')

    def mark_as_deleted(self):
        """
        Not supported

        :raises: AttributeError
        """
        raise AttributeError('\nNot supported on Fault objects.')

    @classmethod
    def _get_apic_classes(cls):
        """
        Get the APIC classes used by this acitoolkit class.

        :returns: list of strings containing APIC class names
        """
        return ['faultInfo']

    @classmethod
    def _get_apic_classes_in_faults(cls):
        """
        Get the list of APIC classes used by FaultInst object

        :returns: list of strings containing APIC class names
        """
        return ['faultInst', 'faultDelegate']

    @classmethod
    def _get_subscription_urls(self, fault_filter=None):
        """
        Gets the URL used to subscribe fault instances
        in the APIC.

        :param fault_filter: fault_filter is used to filter the attributes of a fault. given in a hash format
                             with domain, types, severity
        :returns: a  URL
        """
        if fault_filter is not None:
            self.validate_fault_filter(fault_filter)

        url = '/api/class/{}.json?subscription=yes'.format(self._get_apic_classes()[0])
        if fault_filter is not None:
            extension = "&query-target-filter="
            if len(fault_filter.keys()) > 1:
                extension += 'and('
                for key in fault_filter.keys():
                    if len(fault_filter[key]) > 1:
                        abc = "or("
                        abc += ", ".join([",".join(["eq(faultInfo." + key, "\"" + str(value) + "\")"])
                                          for value in fault_filter[key]])
                        abc += ")"
                        if not extension.endswith("and("):
                            extension += ","
                        extension += abc
                    else:
                        if not extension.endswith("and("):
                            extension += ","
                        extension += ",".join(["eq(faultInfo." + key, "\"" + str(fault_filter[key][0]) + "\")"])
                extension += ")"
            else:
                for key in fault_filter.keys():
                    if len(fault_filter[key]) > 1:
                        abc = "or("
                        abc += ", ".join([",".join(["eq(faultInfo." + key, "\"" + str(value) + "\")"])
                                          for value in fault_filter[key]])
                        abc += ")"
                        extension += abc
                    else:
                        extension += ",".join(["eq(faultInfo." + key, "\"" + str(fault_filter[key][0]) + "\")"])
            url += extension
        return url

    @classmethod
    def subscribe_faults(self, session, fault_filter=None, only_new=False):
        """
        Subscribe to faults from the APIC that pertain to instances of this
        class.

        :param session:  the instance of Session used for APIC communication
        :param fault_filter: fault_filter is used to filter the attributes of a fault. given in a hash format
                             with domain, types, severity
        :param only_new: Boolean indicating whether to get all events or only the new events. All events (indicated by
                         setting only_new to False) will queue a create event for all of the currently existing objects.
                         Setting only_new to True will only queue events that occur after the initial subscribe. The
                         default has only_new set to False.
        """
        url = self._get_subscription_urls(fault_filter=fault_filter)
        resp = session.subscribe(url, only_new=only_new)
        if resp is not None:
            if not resp.ok:
                return False
        return True

    @classmethod
    def has_faults(self, session, fault_filter=None):
        """
        Check for pending events from the APIC that pertain to instances
        of this class.

        :param session:  the instance of Session used for APIC communication
        :param fault_filter: fault_filter is used to filter the attributes of a fault. given in a hash
                             format with domain, types, severity
        :returns: True or False.  True if there are events pending.
        """
        url = self._get_subscription_urls(fault_filter=fault_filter)
        return session.has_events(url)

    def get_faults_by_filter(self, fault_filter=None):
        """
        filters a fault obj based on the keys given in fault_filter

        :param fault_filter: fault_filter is used to filter the attributes of a fault. given in a hash
                     format with domain, types, severity
        :returns: fault obj if it satisfies fault_filter
        """
        for key in fault_filter.keys():
            for value in fault_filter[key]:
                if getattr(self, key) == value:
                    return self

    @classmethod
    def get_fault(cls, session, extension=''):
        """
        Not implemented for this class.  Use get_faults() instead

        :param session: Not used
        :param extension: Not used
        :raises: AttributeError
        """
        raise AttributeError('\nPlease use get_faults() from the Fault class.\n'
                             'get_fault is meant to be used from specific toolkit classes such as Tenant.')

    @classmethod
    def get_faults(self, session, fault_filter=None, tenant_name=None):
        """
        Gets the fault that is pending for this class.  Faults are
        returned in the form of objects.

        :param session:  the instance of Session used for APIC communication
        :param fault_filter: fault_filter is used to filter the attributes of a fault. given in a hash
                             format with domain, types, severity
        :param tenant_name: tenant_name is a string
        """
        url = self._get_subscription_urls(fault_filter=fault_filter)
        event = session.get_event(url)
        for class_name in self._get_apic_classes_in_faults():
            if class_name in event['imdata'][0]:
                break
        faults = event['imdata']
        fault_objects = []
        for fault in faults:
            obj = self()
            attribute_data = fault[class_name]['attributes']
            obj._populate_from_attributes(attribute_data)
            if tenant_name is not None:
                if tenant_name not in obj.dn:
                    # if not obj['dn'].starts_with('uni/tn-'+tenant_name):
                    continue
            if fault_filter is not None:
                fault_objects.append(obj.get_faults_by_filter(fault_filter=fault_filter))
            else:
                fault_objects.append(obj)
            return fault_objects

    def _populate_from_attributes(self, attributes):
        """Fills in an Fault object with the desired attributes.
           Overridden by inheriting classes to provide the specific attributes
           when getting objects from the APIC.
        """
        self.type = attributes['type']
        self.subject = attributes['subject']
        self.severity = attributes['severity']
        self.domain = attributes['domain']
        self.descr = attributes['descr']
        self.dn = attributes['dn']
        self.cause = attributes['cause']
        self.rule = attributes['rule']

    @classmethod
    def validate_fault_filter(self, fault_filter=None):
        """
        validates the fault_filter with the schema

        :param fault_filter: fault_filter is used to filter the attributes of a fault. given in a hash
                     format with domain, types, severity
        """
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "properties": {
                "domain": {
                    "type": "array",
                    "uniqueItems": False,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "enum": ["infra", "tenant", "security", "management", "framework", "external", "access"]
                    }
                },
                "severity": {
                    "type": "array",
                    "uniqueItems": False,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "enum": ["major", "minor", "critical", "warning", "info", "cleared"]
                    }
                },
                "type": {
                    "type": "array",
                    "uniqueItems": False,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "enum": ["config", "environmental", "communications", "operational"]
                    }
                },
                "code": {
                    "type": "array",
                    "uniqueItems": False,
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
        try:
            validate(fault_filter, schema)
        except ValidationError as e:
            print('JSON configuration validation failed: %s', e.message)
            os._exit(1)
