import copy

from django.core.urlresolvers import reverse

from pulp.server.db.model import criteria


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
        self._remapped_fields = {}
        if hasattr(self, 'Meta'):
            meta = self.Meta
            if hasattr(meta, 'exclude_fields'):
                self._exclude_fields = meta.exclude_fields
            if hasattr(meta, 'mask_fields'):
                self._mask_fields = meta.mask_fields
            if hasattr(meta, 'remapped_fields'):
                self._remapped_fields = meta.remapped_fields

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
        if root_key in representation:
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
        if root_key in representation:
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


class ModelSerializer(BaseSerializer):
    """
    Base serializer for Mongoengine Documents.
    """

    def to_representation(self, instance):
        """
        Transforms a Mongoengine Document into a serialized dictionary.

        :param instance: document to serialize
        :type  instance: mongoengine.Document

        :return: external dictionary representation of the document
        """
        document_dict = {}
        for field in instance._fields:
            if field in self._remapped_fields:
                document_dict[self._remapped_fields[field]] = getattr(instance, field)
            else:
                document_dict[field] = getattr(instance, field)

        return document_dict

    def _translate_filters(self, model, filters):
        """
        Iterate through the filters and translate them to use our internal db representation.

        :param model: the class that defines this document's fields
        :type  model: sublcass of mongoengine.Document
        :param filters: dict used to filter results
        :type  filters: dict, following mongo syntax

        :return: the same filters dictionary, with fields translated to the new db representation
        :rtype:  dict, following mongo syntax
        """
        translated_dict = {}
        for field in filters.iterkeys():
            if field in self._remapped_fields.itervalues():
                translated_dict[self._translate(model, field)] = filters[field]
            else:
                translated_dict[field] = filters[field]
        return translated_dict

    def _translate(self, model, field):
        """
        Converts an external representation of a field to the Mongoengine db_field.

        :param model: the class that defines this document's fields
        :type  model: sublcass of mongoengine.Document
        :param field: field name (external representation)
        :type  field: basestring

        :return: the key that mongoengine uses to store this field in the database
        :rtype:  basestring
        """
        for internal, external in self._remapped_fields.iteritems():
            if external == field:
                return getattr(model, internal).db_field
        else:
            return getattr(model, field).db_field

    def translate_criteria(self, model, crit):
        """
        To preserve backwards compatability of our search API, we must translate the fields from
        the external representation to the internal representation. This is done most often with
        'id' since this is not an allowable key in the database in Mongoengine.

        This method relies on a map defined in the subclass's Meta: `remapped_fields` which should
        be a dictionary containing the fields that have been renamed in the format:

        {'internal repr': 'external repr'}

        :param model: the class that defines this document's fields
        :type  model: sublcass of mongoengine.Document
        :param crit: criteria object to be translated from external to internal representation
        :type  crit: pulp.server.db.model.criteria.Criteria

        :return: translated Criteria object
        :rtype:  pulp.server.db.model.criteria.Criteria
        """
        crit_dict = crit.as_dict()
        crit_dict['filters'] = self._translate_filters(model, crit.filters)
        if crit.sort:
            sort = [(self._translate(model, field), direc) for field, direc in crit.sort]
            crit_dict['sort'] = sort
        if crit.fields:
            crit_dict['fields'] = [self._translate(model, field) for field in crit.fields]
        return criteria.Criteria.from_dict(crit_dict)


class Repository(ModelSerializer):
    """
    Serializer for Repositories.
    """

    class Meta:
        """
        Contains information that the base serializer needs to properly handle a Repository object.
        """
        exclude_fields = []
        remapped_fields = {'repo_id': 'id', 'id': '_id'}

    def get_href(self, instance):
        """
        Build the href for a repository.

        :param instance: repository being serialized
        :type  instance: pulp.server.db.model.Repository

        :return: REST href for the given repository instance
        :rtype:  str
        """
        return reverse('repo_resource', kwargs={'repo_id': instance.repo_id})


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
