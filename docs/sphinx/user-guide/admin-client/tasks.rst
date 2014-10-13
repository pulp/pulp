Tasks
=====


Introduction
------------

The Pulp server uses `Celery <http://www.celeryproject.org>`_ to handle requests that may
take longer than a HTTP request timeout to execute. Many of the commands from the
**pulp-admin** command line client will return messages along the lines of

::

 Request accepted

 check status of task e239ae4f-7fad-4004-bfb6-8e06f17d22ef with "pulp-admin tasks details"

This means the server's REST API returned a 202 ACCEPTED response with the task
information for the task that is handling the request.

This page details querying and managing these tasks.


Details
-------

The **pulp-admin** command line client provides the ``tasks`` section and the
``details`` command to inspect the runtime details of a task, identified with the
required ``--task-id=<id>`` flag.

::

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

In the output above there are several sections:

 * *Operations*: a list of operations that are being performed by this task
 * *Resources*: a list of resources that are being operated on
 * *State*: the state of the task, such as: Waiting, Running, Successful or Error
 * *Start Time*: the UTC time the task started
 * *Finish Time*: the UTC time the task finished
 * *Result*: the reported result of the task, if any
 * *Task Id*: a unique identifier for the task (as a UUID)
 * *Progress*: arbitrary progress information provided by the task, if any


Listing
-------

To see all the tasks on the server at any given time, the **pulp-admin**
command line client provides the ``tasks`` section and the ``list`` command.

It provides all the same information as the ``details`` command, but for every task that has been
executed on the pulp server. The length of history depends on the settings described below.

In addition to tasks launched using pulp-admin or the API , ``reaper`` and ``monthly`` tasks appear
in the list.

The ``reaper`` task is responsible for cleaning up the database on a regularly scheduled interval.
The interval is configured with ``reaper_interval`` in ``[data_reaping]`` section of
``/etc/pulp/server.conf``. The value can be whole or fraction of days. The length of time to keep
documents for each collection is also configured in the same section. ``archived_calls``,
``task_status_history``, ``consumer_history``, ``repo_sync_history``, ``repo_publish_history``,
``repo_group_publish_history``, and ``task_result_history`` take values of whole or fraction of
days to keep that type of history. This database cleanup is needed because these transactions can
occur very frequently and as result the database can grow to an unreasonable size.

The ``monthly`` task is run every 30 days to clean up data referencing any repositories that no
longer exist.

Canceling a Task
----------------

Tasks may be canceled before they are run (i.e. in the waiting state) or while
they are running.

The **pulp-admin** command line client provides the ``tasks`` section and the
``cancel`` command to cancel a task identified by the required
``--task-id`` flag.

::

 $ pulp-admin tasks cancel --task-id e0e0a250-eded-468f-9d97-0419a00b130f

 $ pulp-admin tasks details --task-id e0e0a250-eded-468f-9d97-0419a00b130f
 +----------------------------------------------------------------------+
                               Task Details
 +----------------------------------------------------------------------+

 Operations:   sync
 Resources:    ff7-e6 (repository)
 State:        Cancelled
 Start Time:   2012-12-09T04:28:10Z
 Finish Time:  2012-12-09T04:29:09Z
 Result:       N/A
 Task Id:      e0e0a250-eded-468f-9d97-0419a00b130f
 Progress:
   Yum Importer:
     Comps:
       State: NOT_STARTED
     Content:
       Details:
         Delta Rpm:
           Items Left:  0
           Items Total: 0
           Num Error:   0
           Num Success: 0
           Size Left:   0
           Size Total:  0
         File:
           Items Left:  0
           Items Total: 0
           Num Error:   0
           Num Success: 0
           Size Left:   0
           Size Total:  0
         Rpm:
           Items Left:  6
           Items Total: 37
           Num Error:   0
           Num Success: 31
           Size Left:   112429996
           Size Total:  149958122
         Tree File:
           Items Left:  0
           Items Total: 0
           Num Error:   0
           Num Success: 0
           Size Left:   0
           Size Total:  0
       Error Details:
       Items Left:    0
       Items Total:   37
       Num Error:     0
       Num Success:   31
       Size Left:     112429996
       Size Total:    149958122
       State:         CANCELED
     Errata:
       State: NOT_STARTED
     Metadata:
       State: FINISHED

.. Note::

   It is possible for tasks to complete or experience an error before the task cancellation request
   is processed. In these instances, the task's final state might not be "canceled" even though a
   cancel was requested.
