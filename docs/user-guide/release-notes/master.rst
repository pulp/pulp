=========================
Pulp master Release Notes
=========================

Pulp master
===========

New Features
------------

Deprecation
-----------

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
