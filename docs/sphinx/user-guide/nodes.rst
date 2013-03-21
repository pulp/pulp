
Nodes
=====

Overview
--------

The *Pulp Nodes* concept describes the relationship between two Pulp servers for the purpose of
sharing content.  In this relationship, one is designated the *parent* and the other is designated
the *child*.  The *child* node consumes content that is provided by the *parent* node.
It is important to understand that a child :term:`node` is a complete and fully functional Pulp
server capable of operating autonomously.

The following terms are used when discussing *Nodes*:

  node
    A Pulp server that has the *Nodes* support installed and has a content sharing
    relationship to another Pulp server.

  parent node
    A Pulp node that provides content to another Pulp server that has been registered
    as a :term:`consumer`.

  child node
    A Pulp node that consumes content from another Pulp server.  The child node must be
    registered as a consumer to the parent and been activated as a child node.

  node activation
    The designation of a registered consumer as a child node.

  enabled repository
    A Pulp repository that has been *enabled* for :term:`binding` by a child node.


Node Topologies
^^^^^^^^^^^^^^^

Pulp nodes may be related to form tree structures.  Intermediate nodes may be designated
as both a parent and child node.

.. image:: images/node-topology.png


Node Anatomy
^^^^^^^^^^^^

The anatomy of both parent and child nodes is simple.  Parent nodes are Pulp servers
that have the *Nodes* support installed.  A Child node is a Pulp server with both the *Nodes*
and *Consumer* support installed.

.. image:: images/node-anatomy.png


Installation
------------

Since Pulp nodes *are* Pulp servers, the installation instructions for *Nodes* support
assumes that the :ref:`server installation <server_installation>` has been completed.  Next,
following the instructions below on each server depending on its intended role within the
node topology.

Parent
^^^^^^

1. Install the node parent package.

::

  $ sudo yum install pulp-node-parent

2. Restart Apache.

::

 $ sudo service httpd restart


Child
^^^^^

A child node is Pulp server + a Pulp consumer.  Installing the *Nodes* child support
installs the pulp-consumer package group as a dependency.

1. Install the node child package.

::

 $ sudo yum install pulp-node-child

2. Restart Apache.
::

 $ sudo service httpd restart

3. Restart the Pulp Agent

::

 $ sudo service pulp-agent restart


Admin Client Extensions
^^^^^^^^^^^^^^^^^^^^^^^

The admin extensions provide *Nodes* specific commands used to perform nodes administration.
These tasks include the following:

 * Child node activation.
 * Child node deactivation.
 * List child nodes.
 * Enable repositories for node binding.
 * Disable repositories for node binding.
 * List enabled repositories.
 * Bind a child node to a repository.
 * Unbind a child node from a repository.
 * Initiate repository publishing of *Nodes* content.
 * Initiate child node synchronization.

Install the *Nodes* admin client extensions.

::

 $ sudo yum install pulp-node-admin-extensions



Registration & Activation
-------------------------

Once the *Nodes* child support has been installed on a Pulp server it can be registered to a
parent server.  This is accomplished using the Pulp Consumer client.  As we've mentioned, a child
node is both a Pulp server and a Pulp consumer.  To register:

1. edit the /etc/pulp/consumer/consumer.conf file and set the ``host`` property in the ``[server]``
section to the hostname or IP address of the Pulp server to be use as the child node's parent.


Binding To Repositories
-----------------------



Troubleshooting
---------------