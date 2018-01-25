Glossary
========

.. glossary::

    DRF
        The Django Rest Framework.

    Pagination
        The practice of splitting large datasets into multiple pages.

    Router
        A :term:`DRF` API router exposes registered views (like a :term:`ViewSet`) at
        programatically-made URLs. Among other things, routers save us the trouble of having
        to manually write URLs for every API view.

        http://www.django-rest-framework.org/api-guide/routers/

    Serializer
        A :term:`DRF` Serializer is responsible for representing python objects in the API,
        and for converting API objects back into native python objects. Every model exposed
        via the API must have a related serializer.

        http://www.django-rest-framework.org/api-guide/serializers/

    ViewSet
        A :term:`DRF` ViewSet is a collection of views representing all API actions available
        at an API endpoint. ViewSets use a :term:`Serializer` or Serializers to correctly
        represent API-related objects, and are exposed in urls.py by being registered with
        a :term:`Router`. API actions provided by a ViewSet include "list", "create", "retreive",
        "update", "partial_update", and "destroy". Each action is one of the views that make up
        a ViewSet, and additional views can be added as-needed.

        http://www.django-rest-framework.org/api-guide/viewsets/
