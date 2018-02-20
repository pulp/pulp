Pulp Documentation
==================

Pulp is used to organize content (primarily software packages) by managing repositories.

With Pulp you can:

* fetch external content
* upload your own content
* manage content in versioned repositories
* host and distribute content

Pulp has a :doc:`REST API <integration-guide/index>` and command line interface for management.

Pulp is completely free and open-source!

How to use these docs
---------------------

To keep our documentation comprehensive, we have laid out a number of recommended linear paths for
readers with various needs.


New Users
************
A good place for new users to start is with TODO(link, overview/concepts), which gives a high level
introduction to Pulp concepts and terminology. After following our TODO(link, installation) docs,
the simplest way to get concrete experience is to install a plugin and use its quickstart. From there,
see our TODO(link,Workflows) to find best practices for common use cases. From there, users should
explore the reference documentation, particularly the TODO(link, CLI ref).


Plugin Writer
*************

The recommended flow for Plugin writers is documented on TODO(plugin-writer/index).

Integrator (REST API consumer)
******************************

The recommended flow for Plugin writers is documented on TODO(integration-guide/index).

pulpcore contributors
*********************

The recommended flow for Plugin writers is documented on TODO(contributing/index).

.. toctree::
   :maxdepth: 2

   overview/index
   installation/index
   overview/index
   workflows/index
   cli-guide/index
   plugins/index
   integration-guide/index
   contributing/index
   release-notes/index
   troubleshooting
   bugs-features
   glossary
