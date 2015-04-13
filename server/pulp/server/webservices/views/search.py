"""
This module contains the SearchView superclass. Your view code should subclass this to create a
search view for a specific model.
"""
import json

from django.views import generic

from pulp.server import exceptions
from pulp.server.auth import authorization
from pulp.server.db.model import criteria
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.views import util


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
                               pulp.server.db.model.base.CriteriaQuerySet, so that the
                               Document's QuerySet will have a find_by_criteria() method.
    :vartype model:            mongoengine.Document
    :cvar    serializer:       If your view needs to modify the QuerySet results before they
                               are returned to the caller, you can define this attribute. It
                               should be set to a function that accepts a single object, and
                               returns a single object.
    :vartype serializer:       staticmethod
    """

    response_builder = staticmethod(util.generate_json_response)
    optional_fields = []

    @classmethod
    def _parse_args(cls, args):
        """
        Separate
        """
        search_params = dict(args)
        options = {}
        for field in cls.optional_fields:
            if search_params.get(field):
                options[field] = search_params.pop(field)

        return search_params, options

    @auth_required(authorization.READ)
    def get(self, request, *args, **kwargs):
        """
        Search for objects using an HTTP GET request.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :return:        HttpReponse containing a list of objects that were matched by the request
        :rtype:         django.http.HttpResponse
        """
        query, options = self._parse_args(request.GET)
        query['filters'] = json.loads(request.GET.get('filters'))

        fields = query.pop('field', '')
        if fields:
            query['fields'] = fields

        return self._generate_response(query, options, *args, **kwargs)

    @auth_required(authorization.READ)
    @util.json_body_required
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
        try:
            # Retrieve the criteria from the POST data
            query = search_params['criteria']
        except KeyError:
            raise exceptions.MissingValue(['criteria'])

        return self._generate_response(query, options, *args, **kwargs)

    @classmethod
    def _generate_response(cls, query, options, *args, **kwargs):
        """
        Perform the database query using the given search data, and return the resuls as a JSON
        serialized HttpReponse object.

        :param query: The criteria that should be used to search for objects
        :type  query: dict
        :return:      The serialized search results in an HttpReponse
        :rtype:       django.http.HttpResponse
        """
        query = criteria.Criteria.from_client_input(query)
        if query.fields:
            if 'id' not in query.fields:
                query.fields.append('id')

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
            search_method = cls.manager.find_by_criteria
        return cls.response_builder(cls.get_results(query, search_method, options, *args, **kwargs))

    @classmethod
    def get_results(cls, query, search_method, options, *args, **kwargs):
        """
        This is designed to search using the class's search method and serialize the results. This
        method can be overriden to account for the need to modify all results post search.
        """
        results = search_method(query)
        if hasattr(cls, 'serializer'):
            results = [cls.serializer(r) for r in results]
        return results
