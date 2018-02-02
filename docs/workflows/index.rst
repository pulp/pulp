Workflows and Use Cases
=======================

Summary
-------

Best practices for managing your content are explained here. A concrete example for each component
of the workflows is documented in plugin documentation. This document explains each workflow using
a specific plug-in, and will contain a link to a more concrete working example in the plug-in
documentation. Documentation for all other plugins can be found TODO(link, plugin page).

This page assumes that the reader is familiar with basic TODO(link, overview/concepts).

Host User Provided Content
--------------------------

This example uses the TODO(link, Python Plugin).

The simplest use case for Pulp is host user uploaded files. For some plugins, like the rpm plugin,
a user could upload ``pulpcore-3.0.0a18.tar.gz`` and ``pip`` can be configured to install from your
Pulp repository.

# TODO(asmacdo) Link each of these to the Workflows section of plugin documentation.
# Upload File
# Create ContentUnit
# Create Repository
# Create Publisher
# Publish (creates a Publication)
# Create a Distribution (serve the Publication)
# Update .piprc
# pip install pulpcore


Mirror an External Repository
-----------------------------

Compose Two Repositories
------------------------

Curate Content from an External Repository
------------------------------------------

Deferred Downloading (Lazy)
---------------------------

Promotion
---------

Scheduling Tasks
----------------
TODO(asmacdo) this?


.. toctree::
   :maxdepth: 2

   upload-publish
   deferred-download
   mirroring
   promotion
   scheduling-tasks
