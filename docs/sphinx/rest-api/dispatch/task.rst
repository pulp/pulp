.. _task_management:

Task Management
===============

Pulp can execute almost any call asynchronously and some calls are always
executed asynchronously. Pulp provides REST APIs to inspect and manage the
tasks executing these calls.


Polling Task Progress
---------------------

Poll a task for progress and result information for the asynchronous call it is
executing. Polling returns a :ref:`call_report`

| :method:`get`
| :path:`/v2/tasks/<task_id>/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200, if the task is found`
* :response_code:`404, if the task is not found`

| :return:`call report representing the current state of the asynchronous call`

:sample_response:`202` ::

 {
  "_href": "/pulp/api/v2/tasks/7744e2df-39b9-46f0-bb10-feffa2f7014b/",
  "response": "postponed",
  "reasons": [{"resource_type": "repository", "resource_id": "test-repo", "operation": "update"}],
  "state": "running",
  "task_id": "7744e2df-39b9-46f0-bb10-feffa2f7014b",
  "job_id": null,
  "schedule_id": null,
  "progress": {},
  "result": null,
  "exception": null,
  "traceback": null,
  "start_time": "2012-05-13T23:00:02Z",
  "finish_time": null,
  "tags": ["pulp:repository:test-repo"],
 }


Cancelling a Task
-----------------

Some asynchronous tasks may be cancelled by the user before they complete. A
task must be in the *waiting* or *running* states in order to be cancelled and
must have support for the cancel.

| :method:`delete`
| :path:`/v2/tasks/<task_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200, if the task was successfully cancelled`
* :response_code:`404, if the task is not found`
* :response_code:`501, if the task does not support cancellation`

| :return:`null`


Listing Tasks
-------------

All currently running and waiting tasks may be listed. This returns a list of
:ref:`call_report` instances. The list can be filtered by tags.

| :method:`get`
| :path:`/v2/tasks/`
| :permission:`read`
| :param_list:`get`

* :param:`?tag,str,only return tasks tagged with all tag parameters`

| :return:`list of call reports (see Polling Task Progress above for example)`

