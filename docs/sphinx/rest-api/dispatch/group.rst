.. _task_group_management:

Task Group Management
=====================

In addition to individual tasks, Pulp utilizes groups of tasks to execute
related calls asynchronously. These **task groups** can be inspected and
managed through the following API.

Polling Task Group Progress
---------------------------

Polling a task group will return a list of :ref:`call_report` instances. Each
call report related to an individual task in the group.

| :method:`get`
| :path:`/v2/task_groups/<task_group_id>/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200, if the task group is found`
* :response_code:`404, if the task group is not found`

| :return:`list of call reports representing the states of each task in the task group`

:sample_response:`200` ::

 [
  {"_href": "/pulp/api/v2/task_groups/7744e2df-39b9-46f0-bb10-feffa2f7014b/",
   "response": "running",
   "reasons": [{"resource_type": "repository", "resource_id": "test-repo", "operation": "update"}],
   "state": "running",
   "task_id": "d6b6fe8e-ff0f-40e4-bb3c-9e547f0cc4a0",
   "task_group_id": "7744e2df-39b9-46f0-bb10-feffa2f7014b",
   "schedule_id": null,
   "progress": {},
   "result": null,
   "exception": null,
   "traceback": null,
   "start_time": "2012-05-13T23:00:02Z",
   "finish_time": null,
   "tags": ["pulp:repository:test-repo"],},
  {"_href": "/pulp/api/v2/task_groups/cfc486e2-10d4-4274-b857-7df65efa870d/",
   "response": "postponed",
   "reasons": [{"resource_type": "repository", "resource_id": "test-repo", "operation": "update"}],
   "state": "running",
   "task_id": "ecdc463b-470e-4778-9b73-bf1f864f04e6",
   "task_group_id": "cfc486e2-10d4-4274-b857-7df65efa870d",
   "schedule_id": null,
   "progress": {},
   "result": null,
   "exception": null,
   "traceback": null,
   "start_time": null,
   "finish_time": null,
   "tags": ["pulp:repository:test-repo"],}
 ]



Cancelling a Task Group
-----------------------

Some task groups may be cancelled by the user before they complete. Tasks within
the task group are individually cancelled, just like under
:ref:`task_management`. Tasks within the task group that have already
completed simply ignore the cancel request.

| :method:`delete`
| :path:`/v2/task_groups/<task_group_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200, if the task group was successfully cancelled`
* :response_code:`404, if the task group could not be found`
* :response_code:`501, if the task group does not support cancellation`

| :return:`null`


Listing Task Groups
-------------------

All currently active tasks groups (task groups that have at least one task in
the *waiting* or *running* state) may be listed. Unlike it's analog in the tasks
collection, this call does not return :ref:`call_report` instances. Instead, it
return a list of links to individual task group resources (see Polling Task
Group Progress above).

| :method:`get`
| :path:`/v2/task_groups/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200`

| :return:`(possibly empty) list of task group links`

:sample_response:`200` ::

 [
  {"task_group_id": "673da74f-cd45-4f7b-8a2c-d6469dceb3e1",
   "_href": "/v2/task_groups/673da74f-cd45-4f7b-8a2c-d6469dceb3e1/"},
  {"task_group_id": "1821e87b-13a7-48d4-af4b-994ac7ca4331",
   "_href": "/v2/task_groups/1821e87b-13a7-48d4-af4b-994ac7ca4331/"}
 ]



