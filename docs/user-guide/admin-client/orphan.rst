Orphaned Content Units
======================


Introduction
------------

Repositories are the container into which content is drawn into Pulp and by which
Pulp serves content. However, under the hood, Pulp actually manages content
separately from repositories. This allows Pulp to minimize disk space by never
duplicating content that is shared between repositories (i.e. content units
that appear in more than one repository).

The consequence of this approach is that when a repository is deleted from the
Pulp server, the content associated with that repository is not. Content units
that are no longer associated with any repositories are referred to as
**orphaned content units** or simply **orphans**.

This page describes the management of orphaned content units.


Listing Orphaned Content Units
------------------------------

The **pulp-admin** command line client provides the ``orphan`` section and the
``list`` command to inspect the orphaned content units on your server::

 $ pulp-admin orphan list --type=rpm --details
 Arch:          noarch
 Checksum:      7e9cad8b2cd436079fd524803ec7fa209a666ecdda05c6f9c8c5ee70cdea9ce6
 Checksumtype:  sha256
 Epoch:         0
 Id:            a0079ca2-1d4f-4d01-8307-3f183f1843a6
 Name:          tito
 Release:       1.fc16
 Version:       0.4.9

 +----------------------------------------------------------------------+
                                 Summary
 +----------------------------------------------------------------------+

 RPM:    1
 Total:  1

You can filter the list by content type by using the ``--type=<type>`` flag.

You can use the ``--details`` flag to list the individual orphaned content
units. Otherwise only the **Summary** section is displayed. This flag is not
available when the content type is omitted, and will be ignored if specified.


Removing Orphaned Content Units
-------------------------------

The **pulp-admin** command line client provides the ``orphan`` section and
``remove`` command to remove orphaned content units from your server.

It has three flags:

 * ``--type=<type>`` to remove all the orphaned content units of a particular type
 * ``--id=<id>`` to remove a particular orphaned content unit
 * ``--all`` to remove all the orphaned content units on the server

::

 $ pulp-admin orphan remove --all
 Request accepted

 check status of task e239ae4f-7fad-4004-bfb6-8e06f17d22ef with "pulp-admin tasks details"

 $ pulp-admin tasks details --task-id e239ae4f-7fad-4004-bfb6-8e06f17d22ef
 +----------------------------------------------------------------------+
                               Task Details
 +----------------------------------------------------------------------+

 Operations:
 Resources:    orphans (content_unit)
 State:        Successful
 Start Time:   2012-12-09T03:26:51Z
 Finish Time:  2012-12-09T03:26:51Z
 Result:       N/A
 Task Id:      e239ae4f-7fad-4004-bfb6-8e06f17d22ef
 Progress:

 $ pulp-admin orphan list
 $

