import warnings

from gettext import gettext as _
from urllib.parse import urlparse

from pulpcore.app import tasks
from pulpcore.app.models import MasterModel
from pulpcore.app.response import OperationPostponedResponse

from django.urls import resolve, Resolver404
from django.core.exceptions import ValidationError

from rest_framework import viewsets, mixins, serializers
from rest_framework.generics import get_object_or_404


class GenericNamedModelViewSet(viewsets.GenericViewSet):
    """
    A customized named ModelViewSet that knows how to register itself with the Pulp API router.

    This viewset is discoverable by its name.
    "Normal" Django Models and Master/Detail models are supported by the ``register_with`` method.

    Attributes:
        lookup_field (str): The name of the field by which an object should be looked up, in
            addition to any parent lookups if this ViewSet is nested. Defaults to 'pk'
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
    endpoint_name = None
    nest_prefix = None
    parent_viewset = None
    parent_lookup_kwargs = {}

    @staticmethod
    def get_resource(uri, model):
        """
        Resolve a resource URI to an instance of the resource.

        Provides a means to resolve an href passed in a POST body to an
        instance of the resource.

        Args:
            uri (str): A resource URI.
            model (django.models.Model): A model class.

        Returns:
            django.models.Model: The resource fetched from the DB.

        Raises:
            rest_framework.exceptions.ValidationError: on invalid URI or resource not found.
        """
        try:
            match = resolve(urlparse(uri).path)
        except Resolver404:
            raise serializers.ValidationError(detail=_('URI not valid: {u}').format(u=uri))
        pk = match.kwargs['pk']
        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise serializers.ValidationError(detail=_('URI not found: {u}').format(u=uri))
        except ValidationError:
            raise serializers.ValidationError(detail=_('UUID invalid: {u}').format(u=pk))

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
    def view_name(cls):
        return '-'.join(cls.endpoint_pieces())

    @classmethod
    def urlpattern(cls):
        return '/'.join(cls.endpoint_pieces())

    @classmethod
    def endpoint_pieces(cls):
        # This is a core ViewSet, not Master/Detail. We can use the endpoint as is.
        if cls.queryset.model._meta.master_model is None:
            return (cls.endpoint_name,)
        else:
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
                return []
            return pieces

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.

        For nested ViewSets, it checks that the parent object exists, otherwise return 404.
        For non-nested Viewsets, this does nothing.
        """
        if self.parent_lookup_kwargs:
            self.get_parent_field_and_object()
        super().initial(request, *args, **kwargs)

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

    @classmethod
    def _get_nest_depth(cls):
        """Return the depth that this ViewSet is nested."""
        if not cls.parent_lookup_kwargs:
            return 1
        else:
            return max([len(v.split("__")) for k, v in cls.parent_lookup_kwargs.items()])

    def get_parent_field_and_object(self):
        """
        For nested ViewSets, retrieve the nested parent implied by the url.

        Returns:
            tuple: (parent field name, parent)
        Raises:
            django.http.Http404: When the parent implied by the url does not exist. Synchronous
                                 use should allow this to bubble up and return a 404.
        """
        parent_field = None
        filters = {}
        if self.parent_lookup_kwargs:
            # Use the parent_lookup_kwargs and the url kwargs (self.kwargs) to retrieve the object
            for key, lookup in self.parent_lookup_kwargs.items():
                parent_field, unused, parent_lookup = lookup.partition('__')
                filters[parent_lookup] = self.kwargs[key]
            return parent_field, get_object_or_404(self.parent_viewset.queryset, **filters)

    def get_parent_object(self):
        """
        For nested ViewSets, retrieve the nested parent implied by the url.

        Returns:
            pulpcore.app.models.Model: parent model object
        Raises:
            django.http.Http404: When the parent implied by the url does not exist. Synchronous
                                 use should allow this to bubble up and return a 404.
        """
        return self.get_parent_field_and_object()[1]


class NamedModelViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.ListModelMixin,
                        GenericNamedModelViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`, `partial_update()`,
    `destroy()` and `list()` actions.
    """
    pass


class CreateDestroyReadNamedModelViewSet(mixins.CreateModelMixin,
                                         mixins.RetrieveModelMixin,
                                         mixins.DestroyModelMixin,
                                         mixins.ListModelMixin,
                                         GenericNamedModelViewSet):
    """
    A customized NamedModelViewSet for models that don't support updates.

    A viewset that provides default `create()`, `retrieve()`, `destroy()` and `list()` actions.

    """
    pass


class AsyncUpdateMixin(object):
    """
    Provides an update method that dispatches a task with reservation for a repository
    """
    def update(self, request, pk, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        app_label = instance._meta.app_label
        async_result = tasks.base.general_update.apply_async_with_reservation(
            [instance], args=(pk, app_label, serializer.__class__.__name__),
            kwargs={'data': request.data, 'partial': partial}
        )
        return OperationPostponedResponse([async_result], request)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class AsyncRemoveMixin(object):
    """
    Provides a delete method that dispatches a task with reservation for a repository
    """
    def destroy(self, request, pk, **kwargs):
        """
        Delete a model instance
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        app_label = instance._meta.app_label
        async_result = tasks.base.general_delete.apply_async_with_reservation(
            [instance],
            args=(pk, app_label, serializer.__class__.__name__)
        )
        return OperationPostponedResponse([async_result], request)


class CreateReadAsyncUpdateDestroyNamedModelViewset(mixins.CreateModelMixin,
                                                    mixins.RetrieveModelMixin,
                                                    mixins.ListModelMixin,
                                                    AsyncUpdateMixin,
                                                    AsyncRemoveMixin,
                                                    GenericNamedModelViewSet):
    """
    A viewset that performs asynchronous update and remove operations

    This viewset should be used with resources that require making a reservation for a repository
    during an update or delete.
    """
    pass
