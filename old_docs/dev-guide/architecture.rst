Architecture
============

Pulp can be viewed as consisting of two parts, the platform (which includes both
the server and client applications) and plugins (which provide support for a
particular set of content types).


Platform
--------

The Pulp application is a :term:`platform` into which support for particular
types of content is installed. The Pulp Platform refers to the following major
components:

* **Server** - The server-side application includes all of the infrastructure for
  handling repositories, consumers, and users. This includes the plumbing for
  handling functionality related to these pieces, such as synchronizing a
  repository or sending an install request to a consumer. The actual behavior
  of how those methods function, however, is dependent on the plugin fielding
  the request.

* **Client** - The platform includes both the admin and consumer clients. These
  clients contain type-agnostic commands, such as logging in or handling events.
  Each client can be enhanced with type-specific commands through the
  use of :term:`extensions <extension>`.


Plugins
-------

Support for handling specific content types, such as RPMs or Puppet Modules,
is provided through plugins into each of the three major platform components.

.. note::
  The term plugin is typically used to refer just to the server-side plugins.
  Collectively, the set of server and client plugins for a particular
  set of content types are usually referred to as a "support bundle."

* **Plugin** - The server-side components that handle either downloading and
  inventorying content in Pulp (called an :term:`importer`) or publishing
  content in a repository (referred to as a :term:`distributor`).

* **Extension** - The components plugged into either the admin or consumer
  command line clients to provide new commands in the client for type-specific
  operations.


Git Repositories
----------------

Pulp's code is stored on `GitHub <http://www.github.com>`_. The Pulp organization's
GitHub repositories are divided into two types:

* The `Pulp repository <https://github.com/pulp/pulp>`_ is used for all platform code,
  including the server and clients. There should be no code in here that caters
  to a specific content type. Put another way, all plugins to the platform components
  are located outside of this repository.
* Each type support bundle (`RPM <https://github.com/pulp/pulp_rpm>`_,
  `Puppet <https://github.com/pulp/pulp_puppet>`_, etc.) is in its own repository.
  Each of these repositories contains their own `setup.py` and RPM spec files,
  as well as any other configuration files needed to support the plugins (for example,
  httpd configuration files).
