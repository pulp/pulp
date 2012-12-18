Introduction
============

The admin client is used to remotely manage a Pulp server. This client is
used to manage the operation of the server itself as well as trigger remote
operations on registered consumers.

For more information on the client that runs on Pulp consumers, see the
:doc:`Consumer <../consumer-client/introduction>` section of this guide.

The following sections describe some unique concepts that apply to the admin
client.


Synchronous v. Asynchronous Commands
------------------------------------

Commands run by the client execute in two different ways.

Many commands run synchronously. In these cases, the command is executed
immediately on the server and the results are displayed before the client
process exits. Examples of this behavior include logging in or displaying the
list of repositories.

In certain cases, a request is sent to the server but the client does not
wait for a response. There are several variations of this behavior:

 * For long running operations, the request is sent to the server and the client
   immediately exits. The progress of the operation can be tracked using the
   commands in the ``tasks`` section of the client.
 * Some operations cannot execute while a resource on the server is being used.
   If the resource is available, the operation will execute immediately and
   the result displayed in the client. If the operation is postponed because the
   resource is unavailable, the status of it can be tracked using the commands
   in the ``tasks`` section of the client.
 * In certain circumstances, an operation may be outright rejected based on the
   state of a resource. For example, if a repository has a delete operation
   queued, any subsequent operation on the repository will be rejected.

For more information on the task commands, see the :doc:`tasks` section of
this guide.

Content Type Bundles
--------------------

A portion of the admin client centers around standard Pulp functionality,
such as user management or tasking related operations. However, Pulp's
pluggable nature presents a challenge when it comes to type-specific operations.
For example, the steps for synchronizing a repository will differ based on
the type of content being synchronized.

To facilitate this, the client provides an :term:`extension` mechanism.
Extensions added by a content type :term:`bundle` will customize the client
with commands related to the types being supported. Typically, these commands
will focus around managing repositories of a particular type, however there
is no restriction to what commands an extension may add.

Type-specific sections will branch at the root of the client. For example,
the following is a trimmed output of the client structure. Type-agnostic
repository commands, such as the list of all repositories and group commands,
are found under the ``repo`` section. Commands for managing RPM repositories
and consumers are found under the ``rpm`` section and provided by the RPM
extensions. Similarly, the commands for managing Puppet repositories are found
under the ``puppet`` command::

 $ pulp-admin --map
 rpm: manage RPM-related content and features
   consumer: register, bind, and interact with rpm consumers
     bind:       binds a consumer to a repository
     history:    displays the history of operations on a consumer
     list:       lists summary of consumers registered to the Pulp
     ...
  repo: repository lifecycle commands
    create: creates a new repository
    delete: deletes a repository
    list:   lists repositories on the Pulp server
    ...
 puppet: manage Puppet-related content and features
   repo: repository lifecycle commands
     create:  creates a new repository
     delete:  deletes a repository
     list:    lists repositories on the Pulp server
     ...
 repo: list repositories and manage repo groups
   list: lists repositories on the Pulp server
   group: repository group commands
   ...

As new types are supported, additional root-level sections will be provided in
their content type bundles.
