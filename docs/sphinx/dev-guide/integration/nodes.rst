Pulp Nodes
==========

Pulp *Nodes* management is performed using the platform REST API. This document identifies the
specific APIs and defines the data values needed for each call. For more information on *Nodes*
concepts, see the Pulp User Guide.


Activation
----------

Activation is stored as a note on the consumer.

Activate
^^^^^^^^

To activate a consumer as a child node, add a special note to the consumer using the
:ref:`consumer update API<consumer_update>`.

Notes:

 _child-node
   The value ``true`` indicates the consumer is a child node.

 _node-update-strategy
   The value specifies the *node-level* synchronization strategy.

Sample POST body:

::

 {
   "delta": {
     "notes": {
       "_child-node": true,
       "_node-update-strategy": "additive"

     }
   }
 }

Deactivate
^^^^^^^^^^

To deactivate a child node, remove the special notes from the consumer using the
:ref:`consumer update API<consumer_update>`.

Sample POST body:

::

 {
   "delta": {
     "notes": {
       "_child-node": null,
       "_node-update-strategy": null

     }
   }
 }


Repositories
------------

Enabling
^^^^^^^^

Repositories are enabled for use with child nodes by associating the *Nodes* distributor with
the repository using the :ref:`distributor association API<distributor_associate>`.
The ``distributor_type_id`` is ``nodes_http_distributor``.

Sample POST body:

::

 {
   "distributor_id": "nodes_http_distributor",
   "distributor_type_id": "nodes_http_distributor",
   "distributor_config": {},
   "auto_publish": true
 }

Disabling
^^^^^^^^^

Repositories are disabled for use with child nodes by disassociating the *Nodes* distributor and
the repository using the :ref:`distributor disassociation API<distributor_disassociate>`.
The ``distributor_id`` in the URL is ``nodes_http_distributor``.

Publishing
^^^^^^^^^^

Manually publishing the *Nodes* data necessary for child node synchronization can be done using
the :ref:`repository publish API<repository_publish>`.

Sample POST body:

::

 {"override_config": {}, "id": "nodes_http_distributor"}

Binding
-------

Bind
^^^^

Binding a child node to a repository can be done using the :ref:`bind API<bind>`. In the POST body,
the ``notify_agent`` must be set to ``false`` because node bindings do not require agent
participation. The ``binding_config`` can be used to specify the *repository-level*
synchronization strategy. The default is ``additive`` if not specified.

Sample POST body:

::

 {
   "notify_agent": false,
   "binding_config": {"strategy": "additive"},
   "repo_id": "elmer",
   "distributor_id": "nodes_http_distributor"
 }

Unbind
^^^^^^

Unbinding a child node from a repository can be done using the  :ref:`unbind API<unbind>`.
The ``distributor_id`` in the URL is ``nodes_http_distributor``.


Synchronization
---------------

The synchronization of a child node is seen by the parent server as a content update on a consumer.
In this case, the consumer is a child node.

Run
^^^

An immediate synchronization of a child node can be initiated using the
:ref:`content update API<content_update>`. In the POST body, an array of (1) unit with ``type_id`` of
``node`` and ``unit_key`` of ``null`` is specified.

Sample POST body:

::

 {
   "units": [{"type_id": "node", "unit_key": null}],
   "options": {}
 }


To skip the repository synchronization phase of the update, specify the ``skip_content_update`` option
with a value of ``true``.

Sample POST body:

::

 {
   "units": [{"type_id": "node", "unit_key": null}],
   "options": {"skip_content_update": true}
 }


To synchronize individual repositories, use the ``type_id`` of ``repository`` and specify the
repository ID using the ``repo_id`` keyword in the ``unit_key``.

Sample POST body:

::

 {
   "units": [{"type_id": "repository", "unit_key": {"repo_id": "abc"}}],
   "options": {}
 }

