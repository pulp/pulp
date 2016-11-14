Publication
===========

Publish a Repository Group
--------------------------

Publish content from a repository group using a repository group's :term:`distributor`. This
call always executes asynchronously and returns a :term:`call report`.

| :method:`post`
| :path:`/v2/repo_groups/<repo_group_id>/actions/publish/`
| :permission:`execute`
| :param_list:`post`

* :param:`id,str,the ID of the distributor to use when publishing; this is not the distributor type ID`
* :param:`?override_config,object,distributor configuration values that override the distributor's
  default configuration for this publish`

| :response_list:`_`

* :response_code:`202, if the publish is set to be executed`
* :response_code:`404, if the repository group ID given does not exist`

| :return:`a` :ref:`call_report` containing a list of spawned tasks that can be polled for a :ref:`task_report`

:sample_request:`_` ::

 {
   "id": "demo_distributor_id",
   "override_config": {}
 }

**Sample result value for the Task Report:**

::

 {
  "_href": "/pulp/api/v2/tasks/a520a839-96ac-4c63-85e4-19a088c81807/",
  "_id": {
   "$oid": "53e243f9b53073e66875efa3"
  },
  "_ns": "task_status",
  "error": null,
  "exception": null,
  "finish_time": "2014-08-06T15:04:25Z",
  "id": "53e243f97bc8f602856d69b9",
  "progress_report": {},
  "result": null,
  "spawned_tasks": [],
  "start_time": "2014-08-06T15:04:25Z",
  "state": "finished",
  "tags": [
   "pulp:repository_group:demo_repo_group",
   "pulp:repository_group_distributor:demo_distributor_id",
   "pulp:action:publish"
  ],
  "task_id": "a520a839-96ac-4c63-85e4-19a088c81807",
  "task_type": "pulp.server.managers.repo.group.publish.publish",
  "traceback": null
 }

**Tags:**
The task created will have the following tags:
``pulp:action:publish``, ``pulp:repository_group:<repo_group_id>``,
``pulp:repository_group_distributor:<group_distributor_id``
