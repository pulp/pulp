Planning Guide
==============

This page outlines questions a plugin writer should consider before writing a new plugin.


Naming Your Content Type
^^^^^^^^^^^^^^^^^^^^^^^^

A content type is what Pulp Core will sync and publish. For example, the *file_plugin* adds the
ability to sync and publish files, which are modeled as the content type ``File``.

A plugin can define multiple content types. For a new plugin, starting with one content type and
getting it working end-to-end is usually easier than developing multiple content types at once.

.. note::
   Write down the name of your Content Type


Content Type vs Content Unit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A *Content Type* defines the concept of the new type being added. In contrast, a *Content Unit* is a
specific one of that type. This is the same distinction between a class and an instance of that
class. For example, ``pulp_file`` defines the content type ``File``, which is a class, versus a
specific ``File`` instance which represents a single, specific file.


Content Unit Uniqueness
^^^^^^^^^^^^^^^^^^^^^^^

Pulp Core needs to be able to recognize two Content Units as being the same. Specifically when Pulp
already has a saved copy of a specific content unit, when it encounters that content unit again, how
can Pulp recognize it already has it saved.

Consider `File Content Type <https://github.com/pulp/pulp_file/blob/master/pulp_file/app/models.py#L11-L32>`_
which is unique on ``path`` and ``digest`` together. ``path`` is the file's relative path, and
``digest`` is the SHA256 HEX digest. This causes Pulp to treat a file with the same ``path`` and
``digest`` as the same. Pulp Core enforces uniqueness constraints at the database level and rejects
any save of a second unit if one already exists in the database.

This uniqueness provides a useful de-duplication in cases where a Content Unit is stored in many
repositories inside of Pulp.

.. note::
   Write down what attributes need to define uniqueness together.


Content Unit Attributes
^^^^^^^^^^^^^^^^^^^^^^^

A Content Unit will typically store other attributes in addition to the uniqueness attributes, but
while initially developing a plugin starting with the bare minimum is recommended. In many cases,
these are only the attributes involved in the uniqueness constraints.

For each attribute, consider what type of data it will need to hold. Is it a string, int, float,
date, datetime, etc?

.. note::
   For each attribute, write down the type of data it should to hold.


What is the Client?
^^^^^^^^^^^^^^^^^^^

Typically users fetch a content type using a client, which is typically a command line tool. For
example, Python packages are fetched with *pip*, and Docker images are fetched with the *docker*
command line tool.

.. note::
   Determine if there is a client tool for this content type or not.


How is Content Discovered?
^^^^^^^^^^^^^^^^^^^^^^^^^^

It is important to understand how a content type is discovered by a client. In the simplest case,
the client is explicitly told a url to fetch the content unit via, for example via *http://*. If the
client does not already know the url to download content with, there are two typical designs
that facilitate the discovory of those urls.

One common option is where the links to the downloadable content are contained in metadata files
that are also available via *http(s)://*. An example of this is the ``pulp_file`` plugin which uses
a `PULP_MANIFEST <https://repos.fedorapeople.org/pulp/pulp/fixtures/file/PULP_MANIFEST>`_ file to
provide the relative path of files to be downloaded. After parsing, the client can download the
actual content via *http(s)://*.

Another common design is one where a webservice provides the links to downloadable content. For
example the Python Package Index (PyPI) provides such a service with the "simple" package index.


For example, here is the url format for the "simple" PyPI API:

   ``https://pypi.org/simple/<package_name_here>/``

Here is a concrete example:

   ``https://pypi.org/simple/pulpcore/``

.. note::
   How does a client discover content to download?


Downloading Remote Content Units
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Remote content units should be downloaded in a way that mimics how the client downloads them. For
example, the Python plugin should download its content like *pip* does. In its simplest usage, *pip*
fetches a package tarball or egg via *http://*. To mimic that behavior, a plugin should download a
package tarball or egg via *http://* also.

In the simplest case, *pip* is told the url and can download it without "discovering" it. For
example with a command like:

``pip3 install -e "git+https://github.com/pulp/pulp.git@3.0-dev#egg=pulpcore&subdirectory=common"``

The *Remote Content Unit* can be downloaded using the url.

Here is an example of how *pip* downloads a specific *Remote Content Unit* that it needs to
"discover". For example, assume we want to install the package named ``foo`` with this command:

``pip3 install foo``

With this case, *pip* discovers and then downloads a package as follows:

1. Request package metadata from the server via *https://pypi.org/simple/foo/*
2. Parse the results which includes urls to its corresponding egg, wheel, and other artifact types
3. Download the type of interest


Verifying Downloaded Content
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In many cases, metadata from the server will include size or digest values which allow the client to
verify that downloaded data was downloaded is not corrupted. If this is available for your content
type, it's a good idea to use it.

Pulp's Plugin API provides asyncio based downloaders which provide efficient parallel downloading.
These downloaders provide built-in size and/or digest based verification if the expected values can
be passed into the downloaders. See the :doc:`downloader docs <../../plugins/plugin-api/download>`
for more information.

.. note::
   Is there size or digest metadata for this content type? How can the client discover that data?


Publishing Your Content Units
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pulp organizes content units into repositories, and the user publishes an entire repository. It's
not possible to publish a content unit by itself, or a partial repository of content units.

When publishing a repository, your plugin needs to mimic the layout of both data and metadata. In
the simplest case for content types that don't have metadata, only the content unit data itself
needs to be published.

In most cases, both metadata and content unit data are required to make a usable publication. It's
important to understand what the required metadata is for your content type.

.. note::
   Write down the list of metadata that will be required to be present on the server. Can this
   metadata be served as a flat file, or does it need some sort of live API for a client to
   interact with?


Live APIs
^^^^^^^^^

The Pulp 3 Plugin API allows plugin writers to add a web views that can respond to client requests
and facilitate content discovery. Conceptually, this is called a "Live API". Not many content types
require this, but if they do, it's important to understand what the requirements are.

Typically only published content needs to be discovered, so the "Live API" requirement is thought of
as a publishing requirement.

.. note::
   Write down any requirements for a webserver to interact with a client to facilitate content
   discovery.
