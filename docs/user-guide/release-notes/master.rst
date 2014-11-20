=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

- Pulp now allows user credentials to be read from user's ``~/.pulp/admin.conf``.
  This should allow pulp-admin to be automated more easily and more securely.
  Please see our :ref:`Authentication` documentation for details.

Deprecation
-----------

 * The ``cancel_publish_repo`` method provided by the ``Distributor`` base plugin class is
   deprecated and will be removed in a future release. Read more about the
   :ref:`plugin cancellation changes <plugin_cancel_now_exits_behavior_change>`.

 * The ``cancel_publish_group`` method provided by the ``GroupDistributor`` base plugin class is
   deprecated and will be removed in a future release. Read more about the
   :ref:`plugin cancellation changes <plugin_cancel_now_exits_behavior_change>`.

 * The ``cancel_sync_repo`` method provided by the ``Importer`` base plugin class is deprecated and
   will be removed in a future release. Read more about the
   :ref:`plugin cancellation changes <plugin_cancel_now_exits_behavior_change>`.

Client Changes
--------------

Agent Changes
-------------

Bugs
----

Known Issues
------------

.. _2.5.x_upgrade_to_master:

Upgrade Instructions for 2.5.x --> master
-----------------------------------------

Rest API Changes
----------------

**Search profile attributes for all consumer profiles**

``/pulp/api/v2/consumers/profile/search/``
A new API call is added to search profile attributes for all consumer profiles using the
Search API.

With this API call all the unit profiles can be retrieved at one time instead of querying each
consumer through ``/v2/consumers/<consumer_id>/profiles/``.
It is also possible to query for a single package across all consumers.

Binding API Changes
-------------------

Plugin API Changes
------------------

.. _plugin_cancel_now_exits_behavior_change:

**Cancel Exits Immediately by Default**

    The ``cancel_publish_repo``, ``cancel_publish_group``, and ``cancel_sync_repo`` methods
    provided by the ``Distributor``, ``GroupDistributor``, and ``Importer`` base plugin classes now
    provide a behavior that exits immediately by default. Previously these methods raised a
    NotImplementedError() which required plugin authors to provide an implementation for these
    methods. These methods will be removed in a future version of Pulp, and all plugins will be
    required to adopt the exit-immediately behavior.

    A cancel can occur at any time, which mean that in a future version of Pulp any part of plugin
    code can have its execution interrupted at any time. For this reason, the following
    recommendations should be adopted by plugin authors going forward in preparation for this
    future change:

     * Group together multiple database calls that need to occur together for database consistency.

     * Do not use subprocess. If your plugin code process gets cancelled it could leave orphaned
       processes.

     * Assume that plugin code which is supposed to run later may not run.

     * Assume that the previous executions of plugin code may not have run to completion.
