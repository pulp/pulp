import copy

from bson.objectid import ObjectId
from django.core.urlresolvers import reverse

from pulp.server import exceptions


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
            document_dict[self.translate_field_reverse(field)] = getattr(instance, field)
        return document_dict

    def translate_filters(self, model, filters):
        """
        Recursively translate mongo queries from our external API to our internal db representation.

        Mongo queries follow one of the following forms:
            1. {"key": "value"} - ex. {"id": "thing1"}
            2. {"key": {query}} - ex. {"id": {"$exists": 1}}
            3. {"$key": [list of items] - ex. {'$in': ['this', 'or_this']
            4. {"$key": [list of queries] - ex. {'$and': [{query_1}, {query_2}]
            5. {"$key": {dict}} - ex. {"$elemMatch": {query}}

        For cases 1 and 2, the key may need to be translated. Cases 3 - 5, the key does not need to
        be translated because it is a mongo operator. For cases 2, 4, and 5, there may be nested
        queries that will need to be translated. Possible nested queries are passed to the helper
        function `_translate_nested_query` to recurse properly.

        :param model: the class that defines this document's fields
        :type  model: sublcass of mongoengine.Document
        :param filters: dict used to filter results
        :type  filters: dict, following mongo query syntax

        :return: filters dictionary, with fields translated
        :rtype:  dict, following mongo query syntax
        """
        translated_dict = {}
        for key, value in filters.iteritems():
            # Do not translate mongo operator keys, but value may contain queries (case 3-5)
            if key.startswith('$'):
                new_key = key
                new_value = self._translate_nested_query(model, value)
            else:
                remapped = self._remapped_fields.itervalues()
                if key == '_id':  # _id is a special case
                    new_key = '_id'
                    # Translate the value only if _id is in remapped_fields
                    new_value = self._translate__id(value) if '_id' in remapped else value
                else:
                    # Case 1 and 2 keys may need to be translated
                    new_key = self.translate_field(model, key) if key in remapped else key
                    # Keep the value (case 1) or translate the nested query (case 2)
                    new_value = self._translate_nested_query(model, value)
            translated_dict[new_key] = new_value
        return translated_dict

    def _translate_nested_query(self, model, query_piece):
        """
        Handle a nested piece of a query based on its type.

        This function handles the following cases:
            1. {"key": "value"}
            2. {"key": {query}}
            3. {"key": [list, of, items]}
            4. {"key": [{list}, {of}, {queries}]

        :param model: the class that defines this document's fields
        :type  model: sublcass of mongoengine.Document
        :param query_piece: part of a query, follows mongo syntax
        :type  query_piece: any type. if dict or list, it will be translated
        :return: translated query_piece
        :rtype:  same as type(query_piece)
        """
        if isinstance(query_piece, list):  # Case 3 - 4
            new_queries = []
            for each in query_piece:
                # Each nested query should be translated
                if isinstance(each, dict):  # Case 4
                    new_queries.append(self.translate_filters(model, each))
                else:  # Case 3
                    new_queries.append(each)
            return new_queries
        elif isinstance(query_piece, dict):  # Case 2
            return self.translate_filters(model, query_piece)
        else:  # Case 1
            return query_piece

    def _translate__id(self, search_term):
        """
        The `_id` field is a special case because the db contains ObjectId's but the user may
        search for the string representation of the ObjectId. This function attempts to convert
        any `_id` strings into an ObjectId.

        :param search_term: if string, convert to ObjectId, if dict, convert it's contents.
        :type  search_term: string or dict

        :return: ObjectId or dict containing ObjectId's where there were string reprs of ObjectIds
        :raises exceptions.InvalidValue: if the data structure cannot be converted.
        """
        err_msg = 'Unable to perform search with `_id={0}`'.format(search_term)
        # search_term is the string version of an ObjectId
        if isinstance(search_term, basestring):
            return ObjectId(search_term)
        # This will break of many of the more complex searches but allows $in and $nin
        elif isinstance(search_term, dict):
            translated = {}
            for key, value in search_term.iteritems():
                # value is the string version of an ObjectId
                if isinstance(value, basestring):
                    translated[key] = ObjectId(value)
                # value is a list of string versions of ObjectIds
                elif isinstance(value, list):
                    translated[key] = [ObjectId(str_id) for str_id in value]
                else:
                    raise exceptions.InvalidValue(err_msg)
            return translated
        else:
            raise exceptions.InvalidValue(err_msg)

    def translate_field(self, model, field):
        """
        Converts an external representation of a field to the Mongoengine db_field.

        :param model: the class that defines this document's fields
        :type  model: sublcass of mongoengine.Document
        :param field: field name (external representation)
        :type  field: basestring

        :return: the key that mongoengine uses to store this field in the database
        :rtype:  basestring
        """
        try:
            for internal, external in self._remapped_fields.iteritems():
                if external == field:
                    return getattr(model, internal).db_field
            else:
                return getattr(model, field).db_field
        except AttributeError:
            raise exceptions.InvalidValue(
                "Field: <{0}> does not exist on objects in the <{1}> collection".format(
                    field, model._meta['collection']))

    def translate_field_reverse(self, field):
        """
        Converts an internal db field name to the external representation of a field

        :param field: field name (internal name)
        :type  field: basestring

        :return: the remapped field name to use in external representations
        :rtype:  basestring
        """
        # If the field name is in the remapped_fields dict, return its value
        # Otherwise, return the field name as-is
        return self._remapped_fields.get(field, field)

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
        # Circular import avoidance, since criteria imports models which imports serializers
        from pulp.server.db.model.criteria import Criteria
        crit_dict = crit.as_dict()
        if crit.filters:
            crit_dict['filters'] = self.translate_filters(model, crit.filters)
        if crit.sort:
            sort = [(self.translate_field(model, field), direc) for field, direc in crit.sort]
            crit_dict['sort'] = sort
        if crit.fields:
            crit_dict['fields'] = [self.translate_field(model, field) for field in crit.fields]
        return Criteria.from_dict(crit_dict)

    def serialize(self, instance):
        """Help convert a single unit to it's dictionary form, handling special field types.

        This object is modified in-place, and should only be invoked by calling
        :py:func:`pulp.server.webservices.views.serializers.content.serialize_unit_with_serializer`
        in responses that still serialize pymongo dicts.

        :param instance: The object to be converted
        :type instance: dict
        """
        # base implementation is a no-op
        pass


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


class ImporterSerializer(ModelSerializer):
    """
    Serializer for the pulp Repository Importer objects
    """

    class Meta:
        mask_fields = ['config__basic_auth_password',
                       'config__proxy_password']
        remapped_fields = {'id': '_id'}

    def get_href(self, instance):
        """
        Get the href for the instance being serialized. If none is returned then
        no href will be added to the serialized object

        :param instance: Instance of the object to be serialized
        :type instance: dict
        :return: The href for the object being serialized
        :rtype: str
        """
        return reverse(
            'repo_importer_resource',
            kwargs={'repo_id': instance['repo_id'], 'importer_id': instance['importer_type_id']}
        )

    def to_representation(self, *args):
        """
        Modify serializer in two ways:

        - `id` field has been removed from the db, but we add it back in for backwards compatibility
        - Redact data from `last_override_config` for security reasons.
        """
        representation = super(ImporterSerializer, self).to_representation(*args)
        representation['id'] = representation['importer_type_id']
        representation['last_override_config'] = {}  # CVE https://pulp.plan.io/issues/3521
        return representation


class Distributor(ModelSerializer):
    """
    Serializer for Distributors.
    """

    class Meta:
        """
        Specifies to the base serializer how to properly handle a Distributor Document.
        """
        remapped_fields = {'distributor_id': 'id', 'id': '_id'}

    def get_href(self, instance):
        """
        Build the href for the distributor instance.
        """
        href = reverse(
            'repo_distributor_resource',
            kwargs={'repo_id': instance['repo_id'],
                    'distributor_id': instance['distributor_id']}
        )
        return href

    def to_representation(self, *args):
        """
        Redacts data from `last_override_config` for security reasons.
        """
        representation = super(Distributor, self).to_representation(*args)
        representation['last_override_config'] = {}  # CVE https://pulp.plan.io/issues/3521
        return representation


class User(ModelSerializer):
    """
    Serializer for Users.
    """

    class Meta:
        """
        Contains information that the base serializer needs to properly handle a Repository object.
        """
        exclude_fields = ['password']
        remapped_fields = {'id': '_id'}

    def get_href(self, instance):
        """
        Build the href for a user.

        :param instance: user being serialized
        :type  instance: pulp.server.db.model.Repository

        :return: REST href for the given user instance
        :rtype:  str
        """
        return reverse('user_resource', kwargs={'login': instance.login})

    def translate_filters(self, model, filters):
        """
        Override the parent class to handle the case of a user provided filter including `id`.
        Since this is no longer in the database we stay backwards compatible by instead searching
        by `_id`.

        :param model: the class that defines this document's fields
        :type  model: sublcass of mongoengine.Document
        :param filters: dict used to filter results
        :type  filters: dict, following mongo syntax

        :return: the same filters dictionary, with fields translated to the new db representation
        :rtype:  dict, following mongo syntax
        """
        if filters and filters.get('id'):
            filters['_id'] = filters.pop('id')
        return super(User, self).translate_filters(model, filters)
