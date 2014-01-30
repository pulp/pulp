Distributors
============

Overview
--------

While an :doc:`importer <importers>` is responsible for bringing content into a repository, a
distributor is used to expose that content from the Pulp server. The specifics for what it means
to expose the repository, performed through an operation referred to as *publishing*, is
dependent on the distributor's goals. Publishing examples include serving the repository
over HTTP/HTTPS, packaging it as an ISO, or using rsync to transfer it into a legacy system.

Operations cannot be performed on a distributor until it is attached to a repository. When adding
a distributor to a repository, the distributor's configuration will be stored in the Pulp server
and provided to the distributor in each operation. More information on how this configuration
functions can be found in the :ref:`configuration section <plugin_config>` of this guide.

Multiple distributors may be associated with a single repository at one time. When publishing
the repository, the user selects which distributor to use.

The :doc:`common` page describes behavior and APIs common to both importers and distributors.

.. note::
 Currently, the API for the base class is not published. The code can
 be found at ``Distributor`` in ``platform/src/pulp/plugins/distributor.py``.


Implementation
--------------

Each distributor must subclass the ``pulp.plugins.distributor.Distributor`` class. That class
defines the operations a distributor may be requested to perform on a repository.

.. warning::
  The distributor instance is not reused between invocations. Any state maintained in the distributor
  is only valid during the current operation's execution. If state is required across multiple
  operations, the :ref:`plugin's scratchpad <scratchpads>` should be used to store the necessary
  information.

There are two methods in the ``Distributor`` class that must be overridden in order for the
distributor to work:

Metadata
^^^^^^^^

The distributor implementation must implement the ``metadata()`` method as
:ref:`described here <plugin_metadata>`.

Configuration Validation
^^^^^^^^^^^^^^^^^^^^^^^^

The distributor implementation must implement the ``validate_config`` method as
:ref:`described here <plugin_config>`.


Functionality
-------------

The primary role of a distributor is to publish a repository. Optionally, the distributor can
provide information to be automatically sent to consumers when they are bound to it.

The sections below will cover a high-level overview of the distributor's functionality. More
information on the specifics of how to implement them are found in the docstrings for each method.

.. warning::
  Both the ``publish_repo`` and ``cancel_publish_repo`` methods must be implemented together.

Publish a Repository
^^^^^^^^^^^^^^^^^^^^

Methods: ``publish_repo``, ``cancel_publish_repo``

The distributor's role in publishing a repository is to take the units currently in the repository and
make them available outside of the Pulp server. The approach for how that is done will vary based on
needs. The typical approach is to serve the repository over HTTP/HTTPS. However, it is also possible to
use a variety of other protocols depending on the nature of the content being served or the specific needs
of a deployment.

The :term:`conduit` passed to the publish call provides the necessary methods to query the content
in a repository. In the event a directory of the repository's content must be created, it is
highly recommended to symlink from the unit's ``storage_path`` rather than copying it.

The conduit defines a ``set_progress`` call that should be used throughout the process
to update the Pulp server with details on what has been accomplished and what remains to be
done. The Pulp server does not require these calls. The progress message must be JSON-serializable
(primitives, lists, dictionaries) but is otherwise entirely at the discretion of the plugin writer.
The most recent progress report is saved in the database and made available to users as a means
to track the progress of the publish.

When implementing the publish functionality, the importer's ``cancel_sync_repo`` method must be
implemented as well. This call will be made on the same instance performing the publish, therefore
it is valid to use an instance variable as a flag the publish process uses to determine if it should
continue.

Consumer Payloads
^^^^^^^^^^^^^^^^^

Method: ``create_consumer_payload``

Depending on the distributor's implementation, it is possible that certain information needs to be
given to consumers attempting to use it. For example, if a distributor supports multiple protocols
such as HTTP and HTTPS, the consumer needs to know which protocol a given repository is configured
to use. This information is referred to as a *consumer payload*.

Each time a consumer binds to a repository's distributor, the ``create_consumer_payload`` method
is called. The format of the payload is up to the plugin writer.

Hosting Static Content
----------------------

You may host static content within the ``/pulp`` URL path. The convention with
existing plugins is to allow content to be published over http, https, or both
by symlinking content into corresponding directories on the filesystem. To
accomplish this, you must create a basic Apache configuration.

Most of your configuration can go in a standard Apache config file like this one:

::

    # /etc/httpd/conf.d/pulp_puppet.conf

    # SSL-related directives can go right in the global config space. The
    # corresponding non-SSL Alias directive must go in a separate config file.
    Alias /pulp/puppet /var/www/pulp_puppet/https/repos

    # directory where repos published for HTTPS get symlinked
    <Directory /var/www/pulp_puppet/https/repos>
        Options FollowSymLinks Indexes
    </Directory>

    # directory where repos published for HTTP get symlinked
    <Directory /var/www/pulp_puppet/http/repos>
        Options FollowSymLinks Indexes
    </Directory>

However, directives such as Alias statements that are specific to the
``<VirtualHost *:80>`` block provided by the platform must go in a separate file.
All files within ``/etc/pulp/vhosts80/`` have their directives "Included" in one
``<VirtualHost *:80>`` block.

::

    # /etc/pulp/vhosts80/puppet.conf

    # Directives in this file get included in the one authoritative
    # <VirtualHost *:80> block provided by the platform.
    Alias /pulp/puppet /var/www/pulp_puppet/http/repos