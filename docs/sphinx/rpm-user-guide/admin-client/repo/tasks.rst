Repository Tasks
================

.. _repo-tasks:

The ``repo tasks`` section of the client provides commands for displaying and
manipulating server-side tasks related to repository operations. More information
on server-side tasks can be found in the :ref:`conflicting operations <coordinator-overview>`
section of the user guide.

Displaying Repository Tasks
---------------------------

The ``list`` command displays any running or queued tasks against a given
repository. It is ordered such that the currently running task appears first
followed by an ordered list of tasks waiting to execute. Tasks are removed from
this list once they are completed. The only argument to
this command is ``--repo-id`` which is required.

Below is a sample output from the ``list`` command. In this example, the
repository "demo" is in the process of synchronizing during which time two
configuration updates were made on the repository and it was then requested to
be deleted::

 $ pulp-admin repo tasks list --repo-id demo
 +----------------------------------------------------------------------+
                                  Tasks
 +----------------------------------------------------------------------+

 Operations:  sync
 Resources:   demo (repository)
 State:       Running
 Start Time:  2012-05-31T12:24:03Z
 Finish Time: Incomplete
 Result:      Incomplete
 Task Id:     82003435-ab1b-11e1-873e-00508d977dff

 Operations:  update
 Resources:   demo (repository)
 State:       Waiting
 Start Time:  Unstarted
 Finish Time: Incomplete
 Result:      Incomplete
 Task Id:     8ba9e9a1-ab1b-11e1-8692-00508d977dff

 Operations:  update
 Resources:   demo (repository)
 State:       Waiting
 Start Time:  Unstarted
 Finish Time: Incomplete
 Result:      Incomplete
 Task Id:     8e3e0854-ab1b-11e1-9778-00508d977dff

 Operations:  delete
 Resources:   demo (repository)
 State:       Waiting
 Start Time:  Unstarted
 Finish Time: Incomplete
 Result:      Incomplete
 Task Id:     91c665ab-ab1b-11e1-ae9f-00508d977dff

Displaying Task Details
-----------------------

Extra information about a task can be displayed using the ``details`` command.
In particular, the raw progress report for the task is displayed in this view.
The contents of that report will vary on the operation being performed by
the task and may be empty for certain operations. This command accepts one
argument, ``--task-id``, which corresponds to the "Task Id" field displayed
in the ``list`` command. The task ID is required when running this command.

Below is a sample output when displaying the details of a sync task::

 $ pulp-admin repo tasks details --task-id 8c2a9094-ab1d-11e1-a54e-00508d977dff
 +----------------------------------------------------------------------+
                               Task Details
 +----------------------------------------------------------------------+

 Operations:   sync
 Resources:    f16 (repository)
 State:        Running
 Start Time:   2012-05-31T12:38:39Z
 Finish Time:  Incomplete
 Result:       Incomplete
 Task Id:      8c2a9094-ab1d-11e1-a54e-00508d977dff
 Progress:
   Importer:
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
           Items Left:  1521
           Items Total: 3107
           Num Error:   0
           Num Success: 1586
           Size Left:   1900702795
           Size Total:  3455015673
         Tree File:
           Items Left:  6
           Items Total: 6
           Num Error:   0
           Num Success: 0
           Size Left:   0
           Size Total:  0
       Error Details:
       Items Left:    1527
       Items Total:   3113
       Num Error:     0
       Num Success:   1586
       Size Left:     1900702795
       Size Total:    3455015673
       State:         IN_PROGRESS
     Errata:
       State: NOT_STARTED
     Metadata:
       State: FINISHED

