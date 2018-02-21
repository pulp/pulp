Concepts and Terminology
========================

This introduction presents a comprehensive high level overview of Pulp terminology and concepts. It
is designed to be understandable to an anyone who is familiar with software management even without
prior knowledge of Pulp. This document favors clarity and accuracy over ease of reading.

:term:`pulpcore`, :term:`plugin`, :term:`content unit<content>`, :term:`type`, :term:`artifact`
    Pulp Core is a generalized backend with a REST API and a plugin API. Users will also need at
    least one plugin to manage content.  Each type of content unit (like rpm or deb) is defined by
    a plugin.  Files that belong to a content unit are called artifacts. Each content unit can have
    0 or many artifacts and artifacts can be shared by multiple content units.

:term:`repository`, **add**, **remove**, :term:`repository version<RepositoryVersion>`
    Content units in Pulp are organized by their membership in repositories over time. Users can
    add or remove content units to a repository, which creates a new repository version.

**content unit creation**, **upload**
    Content units can be created in Pulp manually. Users specify the content type and the artifacts
    that will belong to the new content unit.  Artifacts that are not already known by Pulp should
    be uploaded prior to creating a new content unit. Content units created in this way must be
    manually added to a repository, creating a new repository version.

:term:`sync`, :term:`importer`
    Users can fetch content units and add them to their repository by syncing from an
    external source. To sync from an external source, the user creates an type-specific importer
    that provides the settings necessary to interact with the source.

**hosting**, :term:`content app`, :term:`publisher`, :term:`publication`, :term:`distribution`
    All content that is managed by Pulp can be hosted by the content app. Plugin-defined publishers
    generate publications, which refer to the metadata and artifacts of the content in a repository
    version. To host a publication, it must be assigned to a distribution, which determines how and
    where a publication is served.
