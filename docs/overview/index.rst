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
