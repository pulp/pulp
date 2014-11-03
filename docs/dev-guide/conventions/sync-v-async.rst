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

A postponed response indicates that some portion of the command has been
queued to execute asynchronously.  In this case a :ref:`call_report` will be returned
with the results of the synchronously executed portion of the command, if there are any,
and a list of the tasks that have been spawned to complete the work in the future.

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
