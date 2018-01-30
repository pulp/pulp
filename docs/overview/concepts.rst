.. Pulp models
.. ===========
..
.. Understanding models
.. --------------------
.. # TODO(asmacdo) move models of this to contributor docs
.. # TODO(asmacdo) update for RepositoryVersions
.. # TODO(asmacdo) update from language guide
..
.. There are models which are expected to be used in plugin implementation, so understanding what they
.. are designed for is useful for a plugin writer. Each model below has a link to its documentation
.. where its purpose, all attributes and relations are listed.
..
.. Here is a gist of how models are related to each other and what each model is responsible for.
..
..   :class:`~pulpcore.plugin.models.RepositoryContent` is used to represent this relation.
.. * :class:`~pulpcore.plugin.models.Content` can have :class:`~pulpcore.plugin.models.Artifact`
..   associated with it. :class:`~pulpcore.plugin.models.ContentArtifact` is used to represent this
..   relation.
.. * :class:`~pulpcore.plugin.models.ContentArtifact` can have
..   :class:`~pulpcore.plugin.models.RemoteArtifact` associated with it.
.. * :class:`~pulpcore.plugin.models.Artifact` is a file.
.. * :class:`~pulpcore.plugin.models.RemoteArtifact` contains information about
..   :class:`~pulpcore.plugin.models.Artifact` from a remote source, including URL to perform
..   download later at any point.
.. * :class:`~pulpcore.plugin.models.Importer` knows specifics of the plugin
..   :class:`~pulpcore.plugin.models.Content` to put it into Pulp.
..   :class:`~pulpcore.plugin.models.Importer` defines how to synchronize remote content. Pulp
..   Platform provides support for concurrent  :ref:`downloading <download-docs>` of remote content.
..   Plugin writer is encouraged to use one of them but is not required to.
.. * :class:`~pulpcore.plugin.models.PublishedArtifact` refers to
..   :class:`~pulpcore.plugin.models.ContentArtifact` which is published and belongs to a certain
..   :class:`~pulpcore.app.models.Publication`.
.. * :class:`~pulpcore.plugin.models.PublishedMetadata` is a repository metadata which is published,
..   located in ``/var/lib/pulp/published`` and belongs to a certain
..   :class:`~pulpcore.app.models.Publication`.
.. * :class:`~pulpcore.plugin.models.Publisher` knows specifics of the plugin
..   :class:`~pulpcore.plugin.models.Content` to make it available outside of Pulp.
..   :class:`~pulpcore.plugin.models.Publisher` defines how to publish content available in Pulp.
.. * :class:`~pulpcore.app.models.Publication` is a result of publish operation of a specific
..   :class:`~pulpcore.plugin.models.Publisher`.
.. * :class:`~pulpcore.app.models.Distribution` defines how a publication is distributed for a specific
..   :class:`~pulpcore.plugin.models.Publisher`.
.. * :class:`~pulpcore.plugin.models.ProgressBar` is used to report progress of the task.
..
..
.. An important feature of the current design is deduplication of
.. :class:`~pulpcore.plugin.models.Content` and :class:`~pulpcore.plugin.models.Artifact` data.
.. :class:`~pulpcore.plugin.models.Content` is shared between :class:`~pulpcore.app.models.Repository`,
.. :class:`~pulpcore.plugin.models.Artifact` is shared between
.. :class:`~pulpcore.plugin.models.Content`.
.. See more details on how it affects importer implementation in :ref:`define-importer` section.
.. TODO:
..     After a concept is fully explained, link to related Workflows

Overview
========

This document presents a high level overview of Pulp terminology and concepts. This document is
designed to be comprehensive, and should be understandable to an anyone who is familiar with
software management. This document favors clarity and accuracy over ease of reading.

Note to Plugin Writers
----------------------

This document uses the :doc:`../contributing/platform-api/index`, and is recommended to Plugin writers
only as an overview of concepts. To understand which objects can be used by plugins and how to use
them, see our :ref:`plugin-writer-guide` for an introduction and the :ref:`plugin-api`
documentation for technical details.

Models
------

:class:`~pulpcore.plugin.models.ContentUnit`, :class:`~pulpcore.plugin.models.Artifact`
    :term:`pulpcore` is a generalized backend with a REST API and a plugin API. Users will also need at
    least one **plugin** to manage content.  Each **plugin** defines at least one :term:`type` of
    :term:`ContentUnit` (like .rpm or .deb), which is the smallest set of data that can be managed by
    Pulp. The plural form of :term:`ContentUnit` is ``ContentUnits``, rather than Content or Units.
    Files that belong to a :term:`ContentUnit` are called :term:`Artifacts`, and each :term:`ContentUnit` can
    have 0 or many :term:`Artifacts`.  :term:`Artifacts` can be shared by multiple :term:`ContentUnits`.

:class:`~pulpcore.app.models.Repository`
    [``Repository``, **add**, **remove**, **RepositoryVersion**] ``ContentUnits`` in Pulp are
    organized by their membership in a ``Repository`` over time. Users can **add** or **remove**
    ``ContentUnits`` to a ``Repository`` by creating a new ``RepositoryVersion`` and specifying the
    ``ContentUnits`` to **add** and **remove**.

[**upload**]
    ``ContentUnits`` can be created in Pulp manually. Users specify the ``Artifacts`` that belong
    to the ``ContentUnit`` and the **plugin** that defines the ``ContentUnit`` ``type``.
    ``Artifacts`` that are not already known by Pulp should be **uploaded** to Pulp prior to
    creating a new ``ContentUnit``. ``ContentUnits`` can be manually **added** to a
    ``Repository`` by creating a new ``RepositoryVersion``.

[**external source**, **sync**]
    Users can fetch ``ContentUnits`` and **add** them to their ``Repository`` by **syncing** with an
    **external source**. The logic and configuration that specifies how Pulp should to interact
    with an **external source** is provided by an ``Importer`` and is defined by the same
    **plugin** that defines that ``type`` of ``ContentUnit`` that the **external source** contains.
    ``pulpcore`` supports multiple ``sync_modes``, including ``additive`` (``ContentUnits`` are
    only **added**) and ``mirror`` (``ContentUnits`` are **added** and **removed** to match the
    **external source**.)

[``hosted``, **metdata**, ``Publisher``, ``Publication``, ``Distribution``]
    All ``ContentUnits`` that are managed by Pulp can be **hosted** as part of the ``pulpcore``
    Content App. **plugin** defined ``Publishers`` generate ``Publications``, which
    refer to the **metadata** and ``Artifacts`` of the ``ContentUnits`` in a ``RepositoryVersion``
    To **host** a ``Publication``, assign it to a ``Distribution``, which determines how and where
    a ``Publication`` is served.

Following the Path of Requests
------------------------------

This section explains what happens in Pulp, following the path of 2 requests.

.. _synchronous-request:

Synchronous Request
*******************


:code:`$ http POST http://pulp3.dev:8000/repositories/ name=my-repo`

REST API endpoints are generated by :class:`~pulpcore.app.urls`, which registers all known
:ref:`Viewsets`. The above request is handled by the
:class:`~pulpcore.app.viewsets.RepositoryViewset` because
``RepositoryViewset.endpoint_name`` is "repositories". The Viewset can either handle POST requests
by defining a function ``create`` or by inherriting from ``restframework.mixins.CreateModelMixin``.
The POST body is available to the viewset via ``request.data``, which uses the
:class:`~pulpcore.app.serializers.RepositorySerializer`. Serializers are used to create
objects from request data, validate those objects, and then save them to the database.

The new Repository object is then deserialized and included in the response.

.. code::

    {
        "_href": "http://pulp3.dev:8000/api/v3/repositories/650973d6-354a-4cb1-a392-2573d01682a6/",
        "_latest_version_href": null,
        "_versions_href": "http://pulp3.dev:8000/api/v3/repositories/650973d6-354a-4cb1-a392-2573d01682a6/versions/",
        "description": "",
        "importers": [],
        "name": "myrepo",
        "notes": {},
        "publishers": []
    }

.. _asynchronous-request:

Asynchronous Request
********************

Actions that take a long time or cannot be run concurrently with other actions must take place
inside a Celery Task. This section tracks the path of an asynchronous
request through Pulp and the File Plugin as an example.

The following request occurs after a user has created a repository and an importer.

:code:`$ http POST http://pulp3.dev:8000/api/v3/importers/file/c5d82868-bbf6-423f-98b5-72ba13bbe0d2/sync/`

Like the :ref:`synchronous-request`, the Viewset is registered with :class:`~pulpcore.app.urls`,
but this time, it has another layer. The :class:`~pulpcore.app.viewsets.Importer` is a "Master"
Viewset with ``importers`` as the ``Importer.endpoint_name``. The
``FileImporterViewset.endpoint_name`` is ``file``, so requests to ``api/v3/importers/file/*`` are
handled by :class`TODO(asmacdo)~pulp_file.app.viewsets.FileImporterViewset`. For a more detailed explanation of
how "Master/Detail" works, see :doc:`../contributing/architecture/rest-api`.

FileImporterViewset defines a "Detail Route" called ``sync``, which accepts POST requests to
to the endpoint in the example. The ``sync`` route is primarily responsible for deploying a Celery
Task. In this case, it deploys the :function`TODO(asmacdo)~pulp_file.app.tasks.sync`.

The response is a 202 and contains an href to view the Task. For more on
how Tasks work, see :doc`TODO(asmacdo, stub out Tasks)`.

.. code::

    [
        {
            "_href": "http://pulp3.dev:8000/api/v3/tasks/438bc62e-2431-42c7-a85f-ddc05ad7b039/",
            "task_id": "438bc62e-2431-42c7-a85f-ddc05ad7b039"
        }
    ]
