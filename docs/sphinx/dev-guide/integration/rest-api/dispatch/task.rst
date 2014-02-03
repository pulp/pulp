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

| :return:`a` :ref:`call_report` representing the task queried

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

All currently running and waiting tasks may be listed. This returns an array of
:ref:`call_report` instances. the array can be filtered by tags.

| :method:`get`
| :path:`/v2/tasks/`
| :permission:`read`
| :param_list:`get`

* :param:`?tag,str,only return tasks tagged with all tag parameters`

| :response_list:`_`

* :response_code:`200,containing an array of tasks`

| :return:`array of` :ref:`call_report`

