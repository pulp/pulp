Nodes
=====

This guide covers consumer client commands for managing *Pulp Nodes* in the Pulp Platform.
For an overview, tips, and, troubleshooting, please visit the :ref:`Pulp Nodes Concepts Guide<pulp_nodes>`.

Layout
------

The root level ``node`` section contains the following features.

::

 $ pulp-consumer node --help
 Usage: pulp-consumer [SUB_SECTION, ..] COMMAND
 Description: pulp nodes related commands

 Available Commands:
  activate   - activate a consumer as a child node
  bind       - bind this node to a repository
  deactivate - deactivate a child node
  unbind     - remove the binding between this node and a repository


Activation
----------

A Pulp server that is registered as a consumer to another Pulp server can be
designated as a :term:`child node`. Once :term:`activated<node activation>` on the parent server,
the consumer is recognized as a child node of the parent and can be managed using ``node`` commands.

To activate a consumer as a child node, use the ``node activate`` command. More information
on *node-level* synchronization strategies can be found :ref:`here<node_strategies>`.

::

 $ pulp-consumer node activate --help
 Command: activate
 Description: activate a consumer as a child node

 Available Arguments:

  --strategy - synchronization strategy (mirror|additive) default is additive


A child node may be deactivated using the ``node deactivate`` command. Once deactivated, the
node may no longer be managed using ``node`` commands.

::

 $ pulp-consumer node deactivate --help
 Command: deactivate
 Description: deactivate a child node

.. note:: Consumer un-registration will automatically deactivate the node.


Binding
^^^^^^^

The ``node bind`` command is used to associate a child node with a repository on the parent. This
association determines which repositories may be synchronized to child nodes. The strategy specified
here overrides the default strategy specified when the repository was enabled. More information on
*repository-level* synchronization strategies can be  found :ref:`here<node_strategies>`.

::

 $ pulp-consumer node bind --help
 Command: bind
 Description: bind this node to a repository

 Available Arguments:

  --repo-id  - (required) unique identifier; only alphanumeric, -, and _ allowed
  --strategy - synchronization strategy (mirror|additive) default is additive

The ``node unbind`` command may be used to remove the association between a child node and
a repository. Once the association is removed, the specified repository can no longer be
be synchronized to the child node.

::

 $ pulp-consumer node unbind --help
 Command: unbind
 Description: remove the binding between this node and a repository

 Available Arguments:

  --repo-id - (required) unique identifier; only alphanumeric, -, and _ allowed

.. note:: Only activated nodes and enabled repositories may be specified.
