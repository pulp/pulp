Tasks
=====


Introduction
------------

The Pulp server uses an internal tasking system to handle requests that may
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

It provides all the same information as the ``details`` command, but for every
task currently operating on the pulp server.


Canceling a Task
----------------

Tasks may be canceled before they are run (i.e. in the waiting state) or while
they are running if they support cancellation.

The **pulp-admin** command line client provides the ``tasks`` section and the
``cancel`` command to try and cancel a task identified by the required
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

It is important to note that not all tasks support cancellation once they enter
the running state. If you try to cancel one of these tasks you will get the
following message

::

 $ pulp-admin tasks cancel --task-id e0e0a250-eded-468f-9d97-0419a00b130f
 Cancel Not Implemented for Task: e0e0a250-eded-468f-9d97-0419a00b130f

