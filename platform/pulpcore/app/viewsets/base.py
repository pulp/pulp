import warnings

from pulpcore.app.models import MasterModel
from rest_framework import viewsets


class NamedModelViewSet(viewsets.ModelViewSet):
    """
    A customized ModelViewSet that understands how to register itself with the Pulp API router.

    "Normal" Django Models and Master/Detail models are supported by the ``register_with`` method.

    Attributes:
        lookup_field (str): The name of the field by which an object should be looked up, in
            addition to any parent lookups if this ViewSet is nested. Defaults to 'name'
        endpoint_name (str): The name of the final path segment that should identify the ViewSet's
            collection endpoint.
        nest_prefix (str): Optional prefix under which this ViewSet should be nested. This must
            correspond to the "parent_prefix" of a router with rest_framework_nested.NestedMixin.
            None indicates this ViewSet should not be nested.
        parent_lookup_kwargs (dict): Optional mapping of key names that would appear in self.kwargs
            to django model filter expressions that can be used with the corresponding value from
            self.kwargs, used only by a nested ViewSet to filter based on the parent object's
            identity.
    """
    lookup_field = 'name'
    endpoint_name = None
    nest_prefix = None
    parent_lookup_kwargs = {}

    @classmethod
    def is_master_viewset(cls):
        # ViewSet isn't related to a model, so it can't represent a master model
        if getattr(cls, 'queryset', None) is None:
            return False

        # ViewSet is related to a MasterModel subclass that doesn't have its own related
        # master model, which makes this viewset a master viewset.
        if (issubclass(cls.queryset.model, MasterModel) and
                cls.queryset.model._meta.master_model is None):
            return True

        return False

    @classmethod
    def register_with(cls, router):
        """
        Register this viewset with the API router using derived names and URL paths.

        When called, "normal" models will be registered with the API router using
        the defined endpoint_name as that view's URL pattern, and also as the base
        name for all views defined by this ViewSet (e.g. <endpoint_name>-list,
        <endpoint_name>-detail, etc...)

        Master/Detail models are also handled by this method. Detail ViewSets must
        subclass Master ViewSets, and both endpoints must have endpoint_name set.
        The URL pattern created for detail ViewSets will be a combination of the two
        endpoint_names::

            <master_viewset.endpoint_name>/<detail_viewset.endpoint_name>

        The base name for views generated will be similarly constructed::

            <master_viewset.endpoint_name>-<detail_viewset.endpoint_name>

        """
        # if we have a master model, include its endpoint name in endpoint pieces
        # by looking at its ancestry and finding the "master" endpoint name
        if cls.queryset is None:
            # If this viewset has no queryset, we can't begin to introspect its
            # endpoint. It is most likely a superclass to be used by Detail
            # Model ViewSet subclasses.
            return

        if cls.is_master_viewset():
            # If this is a master viewset, it doesn't need to be registered with the API
            # router (its detail subclasses will be registered instead).
            return

        if cls.queryset.model._meta.master_model is not None:
            # Model is a Detail model. Go through its ancestry (via MRO) to find its
            # eldest superclass with a declared name, representing the Master ViewSet

            master_endpoint_name = None
            # first item in method resolution is the viewset we're starting with,
            # so start finding parents at the second item, index 1.
            for eldest in reversed(cls.mro()):
                try:
                    if eldest.endpoint_name is not None:
                        master_endpoint_name = eldest.endpoint_name
                        break
                except AttributeError:
                    # no endpoint_name defined, need to get more specific in the MRO
                    continue

            pieces = (master_endpoint_name, cls.endpoint_name)

            # ensure that neither piece is None/empty and that they are not equal.
            if not all(pieces) or pieces[0] == pieces[1]:
                # unable to register; warn and return
                msg = ('Unable to determine viewset inheritance path for master/detail '
                       'relationship represented by viewset {}. Does the Detail ViewSet '
                       'correctly subclass the Master ViewSet, and do both have endpoint_name '
                       'set to different values?').format(cls.__name__)
                warnings.warn(msg, RuntimeWarning)
                return
        else:
            # "Normal" model, can just use endpoint_name directly.
            pieces = (cls.endpoint_name,)

        urlpattern = '/'.join(pieces)
        view_name = '-'.join(pieces)
        router.register(urlpattern, cls, view_name)

    def get_queryset(self):
        """
        Gets a QuerySet based on the current request.

        For nested ViewSets, this adds parent filters to the result returned by the superclass. For
        non-nested ViewSets, this returns the original QuerySet unchanged.

        Returns:
            django.db.models.query.QuerySet: the queryset returned by the superclass with additional
                filters applied that match self.parent_lookup_kwargs, to scope the results to only
                those associated with the parent object.
        """
        qs = super().get_queryset()
        if self.parent_lookup_kwargs:
            filters = {}
            for key, lookup in self.parent_lookup_kwargs.items():
                filters[lookup] = self.kwargs[key]
            qs = qs.filter(**filters)
        return qs
