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

* **Client** - The platform includes the code necessary to run the command line
  clients. Each client uses the same base code and is customized through the
  use of :term:`extensions <extension>`.

* **Agent** - The agent runs on a consumer and is used to field requests sent
  from the Pulp server to that consumer. Similar to the client, the platform
  provides the agent and relies on the use of :term:`handlers <handler>` plugins
  to provide support for a particular content type.

Plugins
-------

Support for handling specific content types, such as RPMs or Puppet Modules,
is provided through plugins into each of the three major platform components.

.. note::
  The term plugin is typically used to refer just to the server-side plugins.
  Collectively, the set of server, client, and agent plugins for a particular
  set of content types are usually referred to as a "support bundle."

* **Plugin** - The server-side components that handle either downloading and
  inventorying content in Pulp (called an :term:`importer`) or publishing
  content in a repository (referred to as a :term:`distributor`).

* **Extension** - The components plugged into either the admin or consumer
  clients to provide new commands in the client for type-specific operations.

* **Handler** - The agent-side components that are used to field invocations
  from the server to a consumer, such as binding to a repository or installing
  content.


