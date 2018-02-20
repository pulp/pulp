Glossary
========

.. glossary::

    Artifact
        A file that belongs to a :term:`ContentUnit`.

    Artifacts
        Just to make sphinx happy

    ContentUnit
        The smallest that of data that is managed by Pulp. :term:`ContentUnits` are added and removed to
        :term:`Repositories`, and can have multiple :term:`Artifacts`. `ContentUnits` have a :term:`type` (like .rpm or
        .deb) that is defined by :term:`Plugins`.

    ContentUnits
        Just to make sphinx happy about crosslinks

    DRF
        The Django Rest Framework.

    Pull
        (was sync)
        Plugin-defined task that adds and/or removes ContentUnits to a Repository, creating a new
        RepositoryVersion.

    Union
        pull.mode
        Pull creates a new RepositoryVersion that contains all ContentUnits that were present in
        the **previous version or the external source**. Same behavior as "additive" sync_mode
        in Pulp 2. This operation is **only additive**.

    Intersection
        pull.mode
        Pull creates a new RepositoryVersion that contains all ContentUnits that were present in
        **both** the **previous version and the external source**.  This operation is **only
        subtractive**.

    Synchronize
        pull.mode
        Task creates a new RepositoryVersion that contains exactly the set of ContentUnits that are
        present in the **external source**.

    Remote
        (was Importer)
        User-definable settings that define how to interact with an **external source**. These
        settings are used to :term:`Pull` from the :term:`Remote`.

    PublishSettings
        (was Publisher)
        User-definable settings to be used by a publish task.

    RepositoryVersion(was RepositoryVersino)
        A version of a Repository's content set. A new version is created whenever content is added
        to or removed from a Repository. Within the context of the plugin.RepositoryVersion
        wrapper, all changes are **staged**. As soon as the context is exited, changes are
        **committed**, creating 1 RepositoryVersion. RepositoryVersions are numbered serially,
        their content set is immutable, but any RepositoryVersion can be deleted. When
        a RepositoryVersions are deleted, its changes are **squashed** into the next committed
        RepositoryVersion. If a failure prevents a RepositoryVersion from being created, its
        ``complete`` flag is left ``False`` until it is cleaned up. Failed RepositoryVersions are
        still assigned a version number, and the next new RepositoryVersion will increment again.

    Repository
        A series of RepositoryVersions. A ContentUnit can be considered "in a Repository" if the
        ContentUnit is in the latest RepositoryVersion. It is also correct to say that a
        ContentUnit is "in a RepositoryVersion".

    Pagination
        The practice of splitting large datasets into multiple pages.

    pulpcore
        A generalized backend with a Plugin API an a REST API. It uses :term:`Plugins` to manage
        :term:`ContentUnits`.

    Plugin
        A Django app that exends ``pulpcore`` to manage one or more "types" of ContentUnit.

    Plugins
        stupid sphinx, just do what i want

    Publication
        The metadata and Artifacts of the ContentUnits in a RepositoryVersion. Publications are
        hosted when they are assigned to a Distribution.

    Publisher
        A plugin-defined object that contains settings required to publish a specific type of
        ContentUnit.


    Repository
        A versioned set of ContentUnits.

    Repositories
        Just to make sphinx happy about crosslinks

    RepositoryVersion
        An immutable snapshot of the set of ContentUnits that are in a Repository.

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

    type
        Plugins define "types" of ContentUnit, like rpm or debian

    ViewSet
        A :term:`DRF` ViewSet is a collection of views representing all API actions available
        at an API endpoint. ViewSets use a :term:`Serializer` or Serializers to correctly
        represent API-related objects, and are exposed in urls.py by being registered with
        a :term:`Router`. API actions provided by a ViewSet include "list", "create", "retreive",
        "update", "partial_update", and "destroy". Each action is one of the views that make up
        a ViewSet, and additional views can be added as-needed.

        http://www.django-rest-framework.org/api-guide/viewsets/
