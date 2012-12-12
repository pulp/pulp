Introduction
============

.. what is the admin client? where can it run? how does it connect to the server?


Synchronous v. Asynchronous Operations
--------------------------------------

.. explain what kinds of operations will be async and how the CLI interacts with that
.. link to the tasks section

Content Type Bundles
--------------------

A portion of the admin client centers around standard Pulp functionality,
such as user management or tasking related operations. However, Pulp's
pluggable nature presents a challenge when it comes to type-specific operations.
For example, the steps for synchronizing a repository will differ based on
the type of content being synchronized.

To facilitate this, the client provides an :term:`extension` mechanism.
Extensions added by a content type :term:`bundle` and customize the client
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
