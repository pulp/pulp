Changes From Pulp 2
===================

Renamed Concepts
----------------

Importers -> Remotes
********************

CLI users may not have been aware of Importer objects because they were embedded into CLI commands
with repositories. In Pulp 3, this object is now called : term:`remote`. The scope of this object
has been reduced to interactions with a single external source. They are no longer scoped to a
repository.

Distributors -> Publishers
**************************

CLI users may not have been aware of Distributor objects because they were also embedded into CLI
commands with repositories. In Pulp 3, this object is now called :term:`publisher`. They are no
longer scoped to repositories either. The responsibilities of distributors related to serving
content have been moved to a new object, the :term:`distribution`,

New Concepts
------------

Repository Version
******************

A new feature of Pulp 3 is that the content set of a repository is versioned. Each time the content
set of a repository is changed, a new immutable :term:`repository version<repositoryversion>` is
created.

Direct Lifecycle Management
***************************

A new feature of Pulp 3 is that each time a repository (really, a respoitory version) is published,
an immutable :term:`publication` is created.

Publications are hosted by :term:`distributions<distribution>`, which contain configuration for how
and where to serve a specific publication.

The combination of publications and distributions allows users to promote and rollback instantly.
In a synchronous call, the user can update a distribution (eg. "Production") to host any
pre-created publication.
