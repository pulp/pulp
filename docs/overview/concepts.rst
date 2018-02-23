Concepts and Terminology
========================

This introduction presents a high level overview of Pulp terminology and concepts. It is designed
to be understandable to an anyone who is familiar with software management even without prior
knowledge of Pulp. This document favors clarity and accuracy over ease of reading.

:term:`pulpcore` is a generalized backend with a REST API and a plugin API. Users will need at
least one :term:`plugin` to manage :term:`content`.  Each :term:`type` of content unit (like rpm or
deb) is defined by a plugin.  Files that belong to a content unit are called
:term:`artifacts<artifact>`. Each content unit can have 0 or many artifacts and artifacts can be
shared by multiple content units.

Content units in Pulp are organized by their membership in :term:`repositories<repository>` over
time. Users can add or remove content units to a repository, which creates a new :term:`repository
version<RepositoryVersion>`.

Content units can be created in Pulp manually. Users specify the content type and the artifacts
that will belong to the new content unit.  Artifacts that are not already known by Pulp should be
uploaded prior to creating a new content unit. Content units created in this way must be manually
added to a repository, creating a new repository version.

Users can fetch content units and add them to their repository by :term:`synchronizing<sync>` from an
external source. To sync from an external source, the user must first create a type-specific
:term:`importer<importer>` that provides the settings necessary to interact with the source. The importer can
then be used to dispatch a sync task, which is documented by each plugin.

All content that is managed by Pulp can be hosted by the :term:`content app`. Users create
type-specific :term:`publishers<publisher>` that provide the settings necessary to generate
:term:`publications<publication>`, which refer to the metadata and artifacts of the content in a
repository version. To host a publication, it must be assigned to a :term:`distribution`, which
determines how and where a publication is served.
