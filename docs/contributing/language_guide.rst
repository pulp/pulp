Language Guide
==============

Purpose
-------

This guide defines and explains Pulp terms and concepts. Before you contribute to the Pulp docs,
please read through this guide and use the established language where possible. This document is
designed to be comprehensive, and should be understandable to an anyone who is familiar with
software management. This document favors clarity and accuracy over ease of reading.

Notation
--------

Each paragraph is preceded by a list of terms that are covered for the first time. In the paragraph
body, terms that correspond to Python code are capitalized based on their type (see PEP 8) and are
indicated by double backticks \`\`object\`\`. (``ClassName``, ``function_name``).  Terms that are
not code objects in in bold. (**plugin**)

Definitions
-----------

[``ContentUnit``, **plugin**, ``type``, ``Artifact``]
    ``pulpcore`` is a generalized backend with a REST API and a plugin API. Users will also need at
    least one **plugin** to manage content.  Each **plugin** defines at least one ``type`` of
    ``ContentUnit`` (like .rpm or .deb), which is the smallest set of data that can be managed by
    Pulp. The plural form of ``ContentUnit`` is ``ContentUnits``, rather than Content or Units.
    Files that belong to a ``ContentUnit`` are called ``Artifacts``, and each ``ContentUnit`` can
    have 0 or many ``Artifacts``.  ``Artifacts`` can be shared by multiple ``ContentUnits``.

[``Repository``, **add**, **remove**, **RepositoryVersion**]
    ``ContentUnits`` in Pulp are organized by their membership in a ``Repository`` over time. Users
    can **add** or **remove** ``ContentUnits`` to a ``Repository`` by creating a new
    ``RepositoryVersion`` and specifying the ``ContentUnits`` to **add** and **remove**.

[**upload**]
    ``ContentUnits`` can be created in Pulp manually. Users specify the ``Artifacts`` that belong
    to the ``ContentUnit`` and the **plugin** that defines the ``ContentUnit`` ``type``.
    ``Artifacts`` that are not already known by Pulp should be **uploaded** to Pulp prior to
    creating a new ``ContentUnit``. ``ContentUnits`` can be manually **added** to a
    ``Repository`` by creating a new ``RepositoryVersion``.

[**external source**, **sync**]
    Users can fetch ``ContentUnits`` and **add** them to their ``Repository`` by **syncing** with an
    **external source**. The logic and configuration that specifies how Pulp should to interact
    with an **external source** is provided by an ``Remote`` and is defined by the same
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
