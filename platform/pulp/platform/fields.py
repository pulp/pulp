"""
Custom Django fields provided by pulp platform
"""
import json

from django.db import models
from django.utils.translation import six


class JSONField(models.TextField):
    """
    A custom Django field to serialize data into a text field and vice versa

    """
    def from_db_value(self, value, *args, **kwargs):
        """
        Converts a value as returned by the database to a Python object

        :param value: The value to convert to Python
        :type value: object

        :param args: unused positional arguments
        :type args: list

        :param kwargs: unused keyword arguments
        :type kwargs: dict

        :return: A Python representation of value
        :rtype: object
        """
        if isinstance(value, six.string_types):
            return self.to_python(value)
        return value

    def to_python(self, value):
        """
        Converts the value into the correct Python object

        :param value: The value to convert to Python
        :type value: object

        :return: A Python representation of value
        :rtype: object
        """
        return json.loads(value)

    def get_db_prep_value(self, value, *args, **kwargs):
        """
        Converts value to a backend-specific value

        :param value: The value to be converted
        :type value: object

        :param args: unused positional arguments
        :type args: list

        :param kwargs: unused keyword arguments
        :type kwargs: dict

        :return: json string representing the object
        :rtype: str
        """
        if value is None:
            return None
        return json.dumps(value)

    def value_to_string(self, obj):
        """
        Converts obj to a string. Used to serialize the value of the field

        :param obj: The object to be converted
        :type obj: object

        :return: Serialized value
        :rtype: str
        """
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value, None)
