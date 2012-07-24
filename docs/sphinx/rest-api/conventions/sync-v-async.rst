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

A postponed response indicates a conflict was detected, however the call can be
executed at a later point in time. The call will be carried out by an
asynchronous task on the server. The response body to such a call is a
serialized call report (see below) that contains metadata about the call,
its progress, and resolution. Additionally, an href is provided that can be used
to poll for updates to this information.

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

A 202 ACCEPTED response returns a **call report** JSON object as the response body
that has the following fields:

* **_href** *(string)* - uri path to retrieve subsequent call reports for this task.
* **response** *(string)* - a response from Pulp's tasking system: accepted, postponed, or rejected
* **reasons** *(array)* - a list of reasons for postponed or rejected responses
* **state** *(string)* - the current state of the task
* **task_id** *(string)* - the unique id of the task that is executing the asynchronous call
* **job_id** *(null or string)* - the unique id of the job the task is a part of
* **schedule_id** *(null or string)* - the unique id of the schedule if the call is scheduled
* **progress** *(object)* - arbitrary progress information, usually in the form of an object
* **result** *(any)* - the return value of the call, if any
* **exception** *(null or string)* - the error exception value, if any
* **traceback** *(null or array)* - the resulting traceback if an exception was raised
* **start_time** *(null or string)* - the time the call started executing
* **finish_time** *(null or string)* - the time the call stopped executing
* **tags** *(array)* - arbitrary tags useful for looking up the call report

Example Call Report::

 {
  "exception": null,
  "job_id": null,
  "task_id": "0fe4fcab-a040-11e1-a71c-00508d977dff",
  "tags": [
    "pulp:repository:f16",
    "pulp:action:sync"
  ],
  "reasons": [],
  "start_time": "2012-05-17T16:48:00Z",
  "traceback": null,
  "state": "running",
  "finish_time": null,
  "schedule_id": null,
  "result": null,
  "progress": { <contents depend on the operation> },
  "response": "accepted",
  "_href": "/pulp/api/v2/tasks/0fe4fcab-a040-11e1-a71c-00508d977dff/"
 }

