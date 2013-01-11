Server
======

Conflicting Operations
----------------------

Pulp, by its nature, is a highly concurrent application. Everything from the
client and APIs themselves down to the need to allow long running sync processes
to execute in the background lends itself to situations where conflicting
user requests may arise.

The simplest example is a situation where a user attempts to delete a repository
in the process of being synchronized. It is the responsibility of the server
to detect these sorts of situations and preserve the integrity of its data.

The Pulp server employs a coordination layer for this purpose. The majority
of the calls made against the server are first checked to verify their ability
to run. This test will result in one of three situations:

* In many cases, the call will be queued to run at the server's earliest convenience
  (factoring in overall server load).
* If a resource is currently busy, the call may be *postponed* until the resource
  becomes available. For example, if a repository configuration update is requested
  while the repository is performing a sync, the update call will be accepted by
  the server but will not execute until the sync completes.
* In rare cases, the call may be outright *rejected* if the resource is in a state
  where the call will never execute. For example, if a call to delete a repository
  is in the queue and a call is made after that to update its configuration, the
  update call will be rejected due to the fact that the repository will be
  deleted before the update call has a chance to resolve.

The client will indicate which of the three possibilities occurred and provides
commands to work with tasks for a given resource (for instance,
the :ref:`repository tasks <repo-tasks>` series of commands).
