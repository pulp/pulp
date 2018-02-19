Pulp Documentation
==================

Pulp is used to organize content (primarily software packages) by managing repositories.

With Pulp you can:

* fetch external content
* upload your own content
* manage content in versioned repositories
* host and distribute content

Pulp has a :doc:`REST API <integration_guide/index>` and command line interface for management.

Pulp is completely free and open-source!

How to use these docs
---------------------

To keep our documentation comprehensive, we have laid out a number of recommended linear paths for
readers with various needs.

Prospective Users
*****************

If you are evaluating whether you would like to use Pulp, you should begin with TODO(link,
overview/why) to get a very high level explanation of what you can do. Then, head to TODO(link,
overview/concepts) to get an introduction to Pulp terminology. Each type of content that Pulp can
manage is provided by a plugin, so check out our TODO(link, plugins) and their documentation.


New Users
************
If you are new to Pulp, start with our TODO(link, installation) docs and then head to a
specific plugin for their quickstart. From there, you should become familiar with the with TODO(link,
overview/concepts). TODO(link,Workflows) will provide some high level usage examples, and will provide
links to concrete examples in plugin documentation. Then they will be ready to use the TODO(link,
CLI reference docs) and advanced guides.


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

   overview/concepts
   overview/why
   installation/index
   overview/index
   workflows/index
   cli_guide/index
   plugins/index
   integration_guide/index
   contributing/index
   release_notes/index
   troubleshooting
   bugs-features
   glossary
