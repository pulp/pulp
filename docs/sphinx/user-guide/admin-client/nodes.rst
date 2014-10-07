Nodes
=====

This guide covers admin client commands for managing *Pulp Nodes* in the Pulp Platform.
For an overview, tips, and, troubleshooting, please visit the :ref:`Pulp Nodes Concepts Guide<pulp_nodes>`.

Layout
------

The root level ``node`` section contains the following features.

::

 $ pulp-admin node --help
 Usage: pulp-admin [SUB_SECTION, ..] COMMAND
 Description: pulp nodes related commands

 Available Sections:
  repo - repository related commands
  sync - child node synchronization commands

 Available Commands:
  activate   - activate a consumer as a child node
  bind       - bind a child node to a repository
  deactivate - deactivate a child node
  list       - list child nodes
  unbind     - removes the binding between a child node and a repository

Listing
-------

The ``node list`` command may be used to list child :term:`nodes<node>`.

::

 pulp-admin node list --help
 Command: list
 Description: list child nodes

 Available Arguments:

  --fields   - comma-separated list of consumer fields; if specified only the
               given fields will be displayed
  --bindings - if specified, the bindings information is displayed
  --details  - if specified, all of the consumer information is displayed

Activation
----------

A Pulp server that is registered as a consumer to another Pulp server can be
designated as a :term:`child node`. Once :term:`activated<node activation>` on the parent server,
the consumer is recognized as a child node of the parent and can be managed using ``node`` commands.

To activate a consumer as a child node, use the ``node activate`` command. More information
on *node-level* synchronization strategies can be found :ref:`here<node_strategies>`.

::

 $ pulp-admin node activate --help
 Command: activate
 Description: activate a consumer as a child node

 Available Arguments:

  --consumer-id - (required) unique identifier; only alphanumeric, -, and _
                  allowed
  --strategy    - synchronization strategy (mirror|additive) default is additive

A child node may be deactivated using ``node deactivate`` command. Once deactivated, the
node may no longer be managed using ``node`` commands.

::

 $ pulp-admin node deactivate --help
 Command: deactivate
 Description: deactivate a child node

 Available Arguments:

  --node-id - (required) unique identifier; only alphanumeric, -, and _ allowed


.. note:: Consumer (child node) un-registration will automatically deactivate the node. When a node 
          is activated again, it will have the same repositories bound to it as it had before 
          deactivation.   

Repositories
------------

The commands provided in the ``node repo`` section are used to perform *Nodes* specific management
of existing repositories.

::

 $ pulp-admin node repo --help
 Usage: pulp-admin [SUB_SECTION, ..] COMMAND
 Description: repository related commands

 Available Commands:
  disable - disables binding to a repository by a child node
  enable  - enables binding to a repository by a child node
  list    - list node enabled repositories
  publish - publishing commands


Listing
^^^^^^^

A listing of :term:`enabled repositories<enabled repository>` may be obtained by using
the ``node repo list`` command.

::

 $ pulp-admin node repo list --help
 Command: list
 Description: list node enabled repositories

 Available Arguments:

  --details - if specified, detailed configuration information is displayed for
              each repository
  --fields  - comma-separated list of repository fields; if specified, only the
              given fields will displayed
  --all, -a - if specified, information on all Pulp repositories, regardless of
              type, will be displayed

Enabling
^^^^^^^^

A repository may be enabled using the ``node repo enable`` command. More information
on *repository-level* synchronization strategies can be found :ref:`here<node_strategies>`.

::

 $ pulp-admin node repo enable --help
 Command: enable
 Description: enables binding to a repository by a child node

 Available Arguments:

  --repo-id      - (required) unique identifier; only alphanumeric, -, and _
                   allowed
  --auto-publish - if "true", the nodes information will be automatically
                   published each time the repository is synchronized; defaults
                   to "true"

.. warning:: Using auto-publish causes the *Nodes* information to be published each time the
             repository is synchronized. This may increase the time it takes to perform the
             synchronization depending on the size of the repository.

Publishing
^^^^^^^^^^

Manually publishing the *Nodes* data necessary for child node synchronization, can be triggered
using the ``node repo publish`` command.

::

 $ pulp-admin node repo publish --help
 Command: publish
 Description: publishing commands

 Available Arguments:

  --repo-id - (required) unique identifier; only alphanumeric, -, and _ allowed

.. note:: Repositories MUST be published for child node synchronization to be successful.

Binding
^^^^^^^

The ``node bind`` command is used to associate a repository with a child node. This association
determines which repositories may be synchronized to child nodes. The strategy specified here
overrides the default strategy specified when the repository was enabled. More information on
*repository-level* synchronization strategies can be  found :ref:`here<node_strategies>`.

::

 $ pulp-admin node bind --help
 Command: bind
 Description: bind a child node to a repository

 Available Arguments:

  --repo-id  - (required) unique identifier; only alphanumeric, -, and _ allowed
  --node-id  - (required) unique identifier; only alphanumeric, -, and _ allowed
  --strategy - synchronization strategy (mirror|additive) default is additive

The ``node unbind`` command may be used to remove the association between a child node and
a repository. Once the association is removed, the specified repository can no longer be
be synchronized to the child node.

::

 $ pulp-admin node unbind --help
 Command: unbind
 Description: removes the binding between a child node and a repository

 Available Arguments:

  --repo-id - (required) unique identifier; only alphanumeric, -, and _ allowed
  --node-id - (required) unique identifier; only alphanumeric, -, and _ allowed



.. note:: Only activated nodes and enabled repositories may be specified.


Synchronizing
-------------

The synchronization of child nodes may be triggered using the ``node sync`` commands. More
information on node synchronization can be found :ref:`here<node_synchronization>`.

::

 $ pulp-admin node sync --help
 Usage: pulp-admin [SUB_SECTION, ..] COMMAND
 Description: child node synchronization commands

 Available Commands:
  run - triggers an immediate synchronization of a child node

An immediate synchronization can be triggered using the ``node sync run`` command.

::

 $ pulp-admin node sync run --help
 Command: run
 Description: triggers an immediate synchronization of a child node

 Available Arguments:

  --node-id       - (required) unique identifier; only alphanumeric, -, and _ allowed
  --max-downloads - maximum number of downloads permitted to run concurrently
  --max-speed     - maximum bandwidth used per download in bytes/sec

.. warning:: Make sure repositories have been published.
