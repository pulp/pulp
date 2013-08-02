Publication
===========

.. _repository_group_publish:

Publish a Repository Group
--------------------------

Publish content from a repository using a repository group's :term:`distributor`. This
call always executes asynchronously and will return a :term:`call report`.

| :method:`post`
| :path:`/v2/repo_groups/<group_id>/actions/publish/`
| :permission:`execute`
| :param_list:`post`

* :param:`id,str,the unique id of the distributor associated with the repository group to
  use for this publish operation`
* :param:`?override_config,object,distributor configuration values that override the distributor's
  default configuration for this publish operation. These settings will not be saved.`

| :response_list:`_`

* :response_code:`202, if the publish is set to be executed`
* :response_code:`409, if a conflicting operation is in progress`

| :return:`call report representing the current state of the publish`

:sample_request:`_` ::

 {
   "id": "demo_distributor_id",
   "override_config": {}
 }

:sample_response:`202` ::

 {
  "task_group_id": null,
  "call_request_id": "d7885e5a-6ab7-4790-9414-049763fc66ab",
  "exception": null,
  "_href": "/pulp/api/v2/tasks/d7885e5a-6ab7-4790-9414-049763fc66ab/",
  "task_id": "d7885e5a-6ab7-4790-9414-049763fc66ab",
  "call_request_tags": [
    "pulp:repository_group:test-group",
    "pulp:repository_group_distributor:demo_group_distributor",
    "pulp:action:publish"
  ],
  "reasons": [],
  "start_time": null,
  "traceback": null,
  "schedule_id": null,
  "finish_time": null,
  "state": "waiting",
  "result": null,
  "dependency_failures": {},
  "call_request_group_id": null,
  "progress": {},
  "principal_login": "SYSTEM",
  "response": "accepted",
  "tags": [
    "pulp:repository_group:demo-group",
    "pulp:repository_group_distributor:demo_group_distributor",
    "pulp:action:publish"
  ]
 }
