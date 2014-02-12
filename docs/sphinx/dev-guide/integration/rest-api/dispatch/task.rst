.. _task_management:

Task Management
===============

Pulp can execute almost any call asynchronously and some calls are always
executed asynchronously. Pulp provides REST APIs to inspect and manage the
tasks executing these calls.

.. _task_report:

Task Report
-----------

The task information object is used to report information about any asynchronously executed
task.

* **_href** *(string)* - uri path to retrieve this task report object.
* **state** *(string)* - the current state of the task. The possible values include: 'waiting', 'skipped', 'running', 'suspended', 'finished', 'error', 'canceled', and 'timed out'.
* **task_id** *(string)* - the unique id of the task that is executing the asynchronous call
* **progress** *(object)* - arbitrary progress information, usually in the form of an object
* **result** *(any)* - the return value of the call, if any
* **exception** *(null or string)* - **deprecated** the error exception value, if any
* **traceback** *(null or array)* - **deprecated** the resulting traceback if an exception was raised
* **start_time** *(null or string)* - the time the call started executing
* **finish_time** *(null or string)* - the time the call stopped executing
* **tags** *(array)* - arbitrary tags useful for looking up the call report
* **spawned_tasks** *(null or array)* - List of uri for any tasks that were spawned by this task.
* **error** *(null or object)* - Any, errors that occurred that did not cause the overall call to fail.  See :ref:`error_details`.

.. note::
  The **exception** and **traceback** fields have been deprecated as of Pulp 2.4.  The information about errors
  that have occurred will be contained in the error block.  See :ref:`error_details` for more information.

Example Task Report::

 {
  "_href": "/pulp/api/v2/tasks/0fe4fcab-a040-11e1-a71c-00508d977dff/",
  "state": "running",
  "task_id": "0fe4fcab-a040-11e1-a71c-00508d977dff",
  "progress": {}, # contents depend on the operation
  "result": null,
  "start_time": "2012-05-17T16:48:00Z",
  "finish_time": null,
  "tags": [
    "pulp:repository:f16",
    "pulp:action:sync"
  ],
  "spawned_tasks": [{"href": "/pulp/api/v2/tasks/7744e2df-39b9-46f0-bb10-feffa2f7014b/",
                     "task_id": "7744e2df-39b9-46f0-bb10-feffa2f7014b" }],
  "error": null
 }


Polling Task Progress
---------------------

Poll a task for progress and result information for the asynchronous call it is
executing. Polling returns a :ref:`task_report`

| :method:`get`
| :path:`/v2/tasks/<task_id>/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200, if the task is found`
* :response_code:`404, if the task is not found`

| :return:`a` :ref:`task_report` representing the task queried

Cancelling a Task
-----------------

Some asynchronous tasks may be cancelled by the user before they complete. A
task must be in the *waiting* or *running* states in order to be cancelled.

| :method:`delete`
| :path:`/v2/tasks/<task_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200, if the task was successfully cancelled`
* :response_code:`404, if the task is not found`
* :response_code:`409, if the task is already in a complete state`

| :return:`null`


Listing Tasks
-------------

All currently running and waiting tasks may be listed. This returns an array of
:ref:`task_report` instances. the array can be filtered by tags.

| :method:`get`
| :path:`/v2/tasks/`
| :permission:`read`
| :param_list:`get`

* :param:`?tag,str,only return tasks tagged with all tag parameters`

| :response_list:`_`

* :response_code:`200,containing an array of tasks`

| :return:`array of` :ref:`task_report`

