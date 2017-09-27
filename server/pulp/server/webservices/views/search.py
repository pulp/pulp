"""
This module contains the SearchView superclass. Your view code should subclass this to create a
search view for a specific model.
"""
import json

from django.views import generic
from pymongo.errors import OperationFailure

from pulp.server import exceptions
from pulp.server.auth import authorization
from pulp.server.db.model import criteria
from pulp.server.webservices.views import util
from pulp.server.webservices.views.decorators import auth_required


class SearchView(generic.View):
    """
    This class is meant to be subclassed by views that need to provide search functionality on a
    Pulp model. In most cases, it should be possible for the subclasses to define only a few class
    variables. Subclasses must define at least one of these two class attributes:

    0) If the SearchView is for searching a MongoEngine model, model should be defined.
    1) If it's for an "old-style" model, manager must be defined.

    :cvar    response_builder: The function that should be used to turn the search results
                               into a JSON serialized Django Response object. If not defined,
                               this defaults to
                               pulp.server.webservices.views.util.generate_json_response.
    :vartype response_builder: staticmethod
    :cvar    manager:          Define this class attribute if you are making a SearchView for
                               a model that has not yet been converted to MongoEngine. It
                               should represent an instance of the Model's manager class,
                               which must have a find_by_criteria() method.
    :vartype manager:          object
    :cvar    model:            Define this class attribute if you are making a SearchView for
                               a MongoEngine Document. The model must have a meta class
                               attribute defined with the 'queryset_class' key indexing
                               pulp.server.db.querysets.CriteriaQuerySet, so that the
                               Document's QuerySet will have a find_by_criteria() method.
    :vartype model:            mongoengine.Document
    :cvar    serializer:       If your view needs to modify the QuerySet results before they
                               are returned to the caller, you can define this attribute. It
                               should be set to a function that accepts a single object, and
                               returns a single object. Where possible, such as serializing a
                               model instance, sane serializers are used by default, and this
                               method should not be defined.
    :vartype serializer:       staticmethod
    """

    response_builder = staticmethod(util.generate_json_response_with_pulp_encoder)
    optional_string_fields = tuple()
    optional_bool_fields = tuple()

    @classmethod
    def _parse_args(cls, args):
        """
        Some search views can contain options in addition to parameters. This function separates
        those options (which should be defined in the subclass) from the search arguments.
        :param args: Search parameters mixed with extra options.
        :type  args: dict

        :return: filtered search parameters and options
        :rtype:  tuple containing a 2 dicts
        """
        options = {}
        for field in filter(args.__contains__, cls.optional_bool_fields):
            value = args.pop(field)
            if isinstance(value, basestring):
                options[field] = value.lower() == 'true'
            else:
                options[field] = value

        for field in filter(args.__contains__, cls.optional_string_fields):
            options[field] = args.pop(field)

        return args, options

    @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        Search for objects using an HTTP GET request. Parses the get parameters and builds a dict
        that should be identical to the request body had this been a POST request.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :return:        HttpReponse containing a list of objects that were matched by the request
        :rtype:         django.http.HttpResponse

        :raises InvalidValue: if `filters` or `sort` is passed but is not valid JSON
        """
        search_params = {}
        for field, value in request.GET.iteritems():
            # These fields need to be loaded from json
            if field in ['filters', 'sort']:
                try:
                    search_params[field] = json.loads(value)
                except ValueError:
                    raise exceptions.InvalidValue(field)
            # The user passes a set of singular values, and a list of values is extracted.
            elif field == 'field':
                search_params['fields'] = request.GET.getlist('field')
            # All other fields are singluar, including options.
            else:
                search_params[field] = value

        query, options = self._parse_args(search_params)
        return self._generate_response(query, options, *args, **kwargs)

    @auth_required(authorization.READ)
    @util.parse_json_body(json_type=dict)
    def post(self, request, *args, **kwargs):
        """
        Search for objects using an HTTP POST request.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :return:        HttpReponse containing a list of objects that were matched by the request
        :rtype:         django.http.HttpResponse

        :raises MissingValue: if required param `criteria` is not passed in the body.
        """
        search_params, options = self._parse_args(request.body_as_json)
        query = search_params.get('criteria')
        if query is None:
            raise exceptions.MissingValue(['criteria'])
        return self._generate_response(query, options, *args, **kwargs)

    @classmethod
    def _serialize_results(cls, results, only=None):
        """
        Serialize a set of search results

        If a model is related to this view and that model has a SERIALIZER attribute, that
        will be used to serialize results by default.

        The default behavior can be overridden by implementing the serializer staticmethod
        on your SearchView implementation.

        :param results: A list of search results from a search query
        :type  results: list

        :return: serialized search results
        :rtype:  list
        """
        # serializer staticmethod is used if it exists...
        if hasattr(cls, 'serializer'):
            results = [cls.serializer(r) for r in results]
        # ...otherwise go through sane defaults here
        elif hasattr(cls, 'model') and hasattr(cls.model, 'SERIALIZER'):
            results = cls.model.SERIALIZER(results, multiple=True).data
            if only is not None:
                _trim_results(cls.model, results, only)
        return results

    @classmethod
    def _generate_response(cls, query, options, *args, **kwargs):
        """
        Perform the database query using the given search data, and return the resuls as a JSON
        serialized HttpReponse object.

        :param query: The criteria that should be used to search for objects
        :type  query: dict
        :param options: Extra options that individual views can use to optionally modify the data.
        :type  options: dict
        :return:      The serialized search results in an HttpReponse
        :rtype:       django.http.HttpResponse

        :raises exceptions.InvalidValue: if pymongo is unable to use the criteria object
        """
        query = criteria.Criteria.from_client_input(query)

        # Our MongoEngine SearchViews will have cls.model set to the MongoEngine model, while the
        # "old" style objects will have the cls.manager attribute set to the model's manager. While
        # it does seem like it should be possible to have both kinds of views set find_by_criteria,
        # or have them both set what their manager is, MongoEngine does QuerySet caching (which is
        # awesome, but also means that we can't reuse a QuerySet from search to search). Once we
        # have converted all of our models to MongoEngine, we can drop the below block and always
        # use cls.model.objects.find_by_criteria, and all subclasses just need to define cls.model.
        if hasattr(cls, 'model'):
            search_method = cls.model.objects.find_by_criteria
        else:
            # id field should always be in query.fields. We are forced to do this twice, here and
            # in the queryset for the mongoengine work. This is necessary because in mongoengine
            # id is an alias to _id, and queries must be translated to reflect that. If we append
            # id before this split, our serializers will translate this id also.
            if query.fields and 'id' not in query.fields:
                query.fields.append('id')
            search_method = cls.manager.find_by_criteria

        # We do not validate all aspects of the criteria object, so if pymongo has a problem we
        # raise an InvalidValue.
        try:
            return cls.response_builder(cls.get_results(query, search_method, options,
                                                        *args, **kwargs))
        except OperationFailure, e:
            invalid = exceptions.InvalidValue('criteria')
            invalid.add_child_exception(e)
            raise invalid

    @classmethod
    def get_results(cls, query, search_method, options, *args, **kwargs):
        """
        This is designed to search using the class's search method and serialize the results. This
        method can be overriden to account for the need to modify all results post search.

        :param query: The criteria that should be used to search for objects
        :type  query: dict
        :param search_method: function that should be used to search
        :type  search_method: func
        :param options: additional options for including extra data
        :type  options: dict

        :return: search results
        :rtype:  list
        """
        only = query.get('fields')
        results = list(search_method(query))
        return cls._serialize_results(results, only=only)


def _trim_results(model, results, only):
    """
    Remove key/value pairs from results that are not required or specified by `fields`.
    """
    min_fields = set(['_id', 'id', '_href'])
    required_fields = set([field for field, val in model._fields.items() if val.required])
    return_fields = set(only) | min_fields | required_fields
    # remove subfield from return fields names
    return_fields_list = list(return_fields)
    for i in range(len(return_fields_list)):
        f = return_fields_list[i]
        if "." in f:
            return_fields_list[i] = f.split(".")[0]
    return_fields = set(return_fields_list)
    # filter
    # assumption: subfields of dict fields were already filtered beforehand,
    # there is no need to filter them again here
    for result in results:
        for k, v in result.items():
            if k not in return_fields:
                result.pop(k)
