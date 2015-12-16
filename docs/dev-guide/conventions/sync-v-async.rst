Synchronous and Asynchronous Calls
==================================

Overview
--------

Pulp uses an advanced task queueing system that detects and avoids concurrent
operations that conflict. All REST API calls are managed through this system.
Any REST API will return one of three responses:

* Success Response - 200 OK or a 201 CREATED
* Postponed Response - 202 ACCEPTED
* Conflict Response - 409 CONFLICT

A success response indicates no conflicts were detected and the REST call
executed. This is what is typically expected from a REST API call.

A postponed response indicates that some portion of the command has been queued to execute
asynchronously.  In this case a :ref:`call_report` or a :ref:`group_call_report` will be returned
with the results of the synchronously executed portion of the command.

When a single task is queued or a task with follow up tasks, such as a publish after a sync or unbind
consumers after repo delete, a :ref:`call_report` is returned. The :ref:`call_report` will contain
a list of spawned tasks.

When some number of related tasks are queued, and it is useful to track the state of all of them
together, a :ref:`group_call_report` is returned.

More information on retrieving and displaying task information can be found
:ref:`in the Task Management API documentation <task_management>`.

A conflict response indicates that a conflict was detected that causes the call to
be unserviceable now or at any point in the future. An example of such a situation
is the case where an update operation is requested after a delete operation has
been queued for the resource. The body of this response is Pulp's standard
exception format including the reasons for the response.

.. _call_report:

Call Report
-----------

A 202 ACCEPTED response returns a **Call Report** JSON object as the response body
that has the following fields:

* **result** *(Object)* - the return value of the call, if any
* **error** *(Object)* - error details if an error occurred.  See :ref:`error_details`.
* **spawned_tasks** *(array)* - list of references to tasks that were spawned.  Each
  task object contains the relative url to retrieve the task and the unique ID of the task.

Example Call Report::

 {
  "result": {},
  "error": {},
  "spawned_tasks": [{"_href": "/pulp/api/v2/tasks/7744e2df-39b9-46f0-bb10-feffa2f7014b/",
                     "task_id": "7744e2df-39b9-46f0-bb10-feffa2f7014b" }]
 }

.. _group_call_report:

Group Call Report
-----------------

A 202 ACCEPTED response returns a **Group Call Report** JSON object as the response body that has
the following fields:

* **_href** - Path to the root of task group resource. However, this API endpoint currently
  returns 404 in all cases. You can append `state-summary/` to the URL and perform a GET request
  to retrieve a :ref:`task_group_summary`.
* **group_id** - UUID of the group that all the dispatched tasks belong to.

Example Group Call Report::

 {
     "_href": "/pulp/api/v2/task_groups/16412fcb-06fa-4caa-818b-b103e2a9bf44/",
    "group_id": "16412fcb-06fa-4caa-818b-b103e2a9bf44"
 }

