Filtering
=========

Filtering Backend 
-----------------

http://www.django-rest-framework.org/api-guide/filtering/#setting-filter-backends

We will be using the rest framework's DjangoFilterBackend. This can set universally in the Django settings.py or in an individual ViewSet. Setting it universally is probably better for our purposes because we still have to explicitly define what filtering is allowed for each viewset.

.. note::

    This will add a dependency: `django-filter` 


Allowing Filters
----------------

Filters must be explicitly specified and are not enabled by default. 


filter_fields
^^^^^^^^^^^^^

The simplest method of adding filters is simply to define `filter_fields` on the ViewSet. Fields specified here will be "filterable", but only using equality.

To use this request:

.. code-block:: bash

    http 'http://192.168.121.134:8000/api/v3/repositories/?slug=singing-gerbil'

This is what the ViewSet should look like:

.. code-block:: python 

    class RepositoryViewSet(viewsets.ModelViewSet):
        lookup_field = 'slug'
        queryset = models.Repository.objects.all()
        serializer_class = serializers.RepositorySerializer
        filter_fields = ('slug',)


FilterSet
^^^^^^^^^

Defining a `FilterSet` allows more options. To start with, this is a `ViewSet` and `FilterSet` that allows the same request:

.. code-block:: bash

    http 'http://192.168.121.134:8000/api/v3/repositories/?slug=singing-gerbil'


.. code:: python 

    class RepositoryFilter(filters.FilterSet):
        pass

        class Meta:
            model = models.Repository
            fields = ['slug']

    class RepositoryViewSet(viewsets.ModelViewSet):
        lookup_field = 'slug'
		queryset = models.Repository.objects.all()
		serializer_class = serializers.RepositorySerializer
		filter_class = RepositoryFilter


Beyond Equality
***************

A `FilterSet` also allows filters that are more advanced than equality. We have access to any of the filters provided out of the box by `django-filter`. 

https://django-filter.readthedocs.io/en/latest/ref/filters.html#filters

Simply define any filters in the `FilterSet` and then include them in `fields` in the Filter's Meta class.

`http 'http://192.168.121.134:8000/api/v3/repositories/?slug_contains=singing'`

.. code-block:: python 

    class RepositoryFilter(filters.FilterSet):
        slug_contains = django_filters.filters.CharFilter(name='slug', lookup_expr='contains')

        class Meta:
            model = models.Repository
            fields = ['slug_contains']


Custom Filters
**************

If the filters provided by `django-filter` do not cover a use case, we can create custom filters from the `django-filter` base classes.

"In" is a special relationship and is not covered by the base filters, however we can create a custom filter based on the `BaseInFilter`.

.. code-block:: bash

    http 'http://192.168.121.134:8000/api/v3/repositories/?slug_in_list=singing-gerbil,versatile-pudu'


.. code-block:: python 

        class CharInFilter(django_filters.filters.BaseInFilter,
                           django_filters.filters.CharFilter):
            pass

        class RepositoryFilter(filters.FilterSet):
        slug_in_list = CharInFilter(name='slug', lookup_expr='in')

            class Meta:
                model = models.Repository
                fields = ['slug_in_list']

.. note::
    We should be careful when naming these filters. Using `repo__in` would be fine because repo is not defined on this model. However, using `slug__in` does *not* work because Django gets to it first looking for a subfield `in` on the slug. 
