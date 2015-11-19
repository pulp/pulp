import copy

from django.core.urlresolvers import reverse


class BaseSerializer(object):
    """
    Base class to be used for creating serializers
    """

    def __init__(self, instance=None, context=None, multiple=False):
        """
        Initiailization of the serializer

        :param instance: The object or iterable of objects to be serialized.
        :type instance: object or iterable of object
        :param context: Bag of data to make available as each instance is serialized.
        :type context: dict
        :param multiple: Whether or not multiple objects are being serialized.
        :type multiple: bool defaults to False
        """
        self.instance = instance
        self.context = context
        self._exclude_fields = []
        self._mask_fields = []
        self._multiple = multiple
        if hasattr(self, 'Meta'):
            meta = self.Meta
            if hasattr(meta, 'exclude_fields'):
                self._exclude_fields = meta.exclude_fields
            if hasattr(meta, 'mask_fields'):
                self._mask_fields = meta.mask_fields

    def to_representation(self, instance):
        """
        Method called to convert a single instance to it's dictionary form

        :param instance: The object to be converted
        :type instance: object
        :return: serialized form of the object
        :rtype: dict
        """
        raise NotImplementedError

    def get_href(self, instance):
        """
        Get the href for the instance being serialized. If none is returned then
        no href will be added to the serialized object

        :param instance: Instance of the object to be serialized
        :type instance: object
        :return: The href for the object being serialized
        :rtype: str
        """
        return None

    def _to_representation(self, instance):
        """
        Internal method to turn an instance into it's serialized representation

        :param instance: the object to be serialized
        :type instance: object
        :return: The instance object represented as a dictionary ready for jsonification
        :rtype: dict
        """
        representation = self.to_representation(instance)
        if self._exclude_fields:
            for blacklist_field in self._exclude_fields:
                field_accessor = blacklist_field.split('__')
                self._remove_excluded(field_accessor, representation)
        if self._mask_fields:
            for pwd_field in self._mask_fields:
                field_accessor = pwd_field.split('__')
                self._mask_field(field_accessor, representation)

        href = self.get_href(instance)
        if href:
            representation['_href'] = href

        return representation

    def _remove_excluded(self, accessor, representation):
        """
        Internal method to remove excluded fields from the dictionary form of an instance.

        This takes a single accessor and

        :param accessor: The accessor to the particular field to be removed
        :type accessor: list of str
        :param representation: The representation of the instance being serialized
        :type representation: dict
        """
        root_key = accessor[0]
        if representation.get(root_key) is not None:
            if len(accessor) > 1:
                self._remove_excluded(accessor[1:], representation[root_key])
            else:
                representation.pop(root_key, None)

    def _mask_field(self, accessor, representation):
        """
        Internal method to replace password values with a fixed number of asterisks
        during serialization.

        :param accessor: The accessor to the particular field to be removed
        :type accessor: list of str
        :param representation: The representation of the instance being serialized
        :type representation: dict
        """
        root_key = accessor[0]
        if representation.get(root_key) is not None:
            if len(accessor) > 1:
                self._mask_field(accessor[1:], representation[root_key])
            else:
                representation[root_key] = '*****'

    @property
    def data(self):
        """
        Property method to get the serialized form of the instance object for this serializer

        :return: serialized form of this instance
        :rtype: dict
        """
        if self._multiple:
            return [self._to_representation(item) for item in self.instance]
        else:
            return self._to_representation(self.instance)


class DictSerializer(BaseSerializer):
    """
    Base class for all dictionary based objects
    """

    def to_representation(self, instance):
        """
        Method called to convert a single instance to it's dictionary form

        As we are converting a dict to a dict, copy the original so that it is not modified
        as a side effect of using this serializer

        :param instance: The object to be converted
        :type instance: dict
        :return: serialized form of the object
        :rtype: dict
        """
        representation = copy.deepcopy(instance)
        return representation


class ImporterSerializer(DictSerializer):
    """
    Serializer for the pulp Repository Importer objects
    """

    class Meta:
        mask_fields = ['config__basic_auth_password',
                       'config__proxy_password']

    def get_href(self, instance):
        """
        Get the href for the instance being serialized. If none is returned then
        no href will be added to the serialized object

        :param instance: Instance of the object to be serialized
        :type instance: dict
        :return: The href for the object being serialized
        :rtype: str
        """
        return reverse('repo_importer_resource', kwargs={'repo_id': instance['repo_id'],
                                                         'importer_id': instance['id']})
