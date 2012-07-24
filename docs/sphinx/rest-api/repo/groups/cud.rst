Creation, Delete, and Update
============================

.. _create_repo_group:

Create a Repository Group
-------------------------

Creates a new repository group. Group IDs must be unique across all repository
groups in the server. The group can be initialized with a list of repositories
by passing in their IDs during the create call. Repositories can later be added
or removed from the group using the :doc:`membership calls<members>`.

| :method:`post`
| :path:`/v2/repo_groups/`
| :permission:`create`
| :param_list:`post`

* :param:`id,string,unique identifier for the group`
* :param:`?display_name,string,user-friendly name for the repository group`
* :param:`?description,string,user-friendly text describing the group's purpose`
* :param:`?repo_ids,object,list of repositories to add to the group`
* :param:`?notes,object,key-value pairs to programmatically tag the group`

| :response_list:`_`

* :response_code:`201,the group was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a group with the given ID`

| :return:`database representation of the created group`

:sample_request:`_` ::

 {
  "id": "demo-group"
 }

:sample_response:`201` ::

 {
  "scratchpad": null,
  "display_name": null,
  "description": null,
  "_ns": "repo_groups",
  "notes": {},
  "repo_ids": [],
  "_id": {
    "$oid": "500ed9888a905b04e9000021"
  },
  "id": "demo-group",
  "_href": "/pulp/api/v2/repo_groups/demo-group/"
 }


Delete a Repository Group
-------------------------

Deleting a repository group does not affect the underlying repositories; it
simply removes the group and its relationship to all repositories.

| :method:`delete`
| :path:`/v2/repo_groups/<group_id>/`
| :permission:`delete`
| :response_list:`_`

* :response_code:`200,if the delete executed immediately and was successful`
* :response_code:`202,if the request was accepted by the server and will execute in the future`
* :response_code:`404,if the specified group does not exist`

| :return:`None or a call report describing the current state of the delete task`

Update a Repository Group
-------------------------

Once a repository group is created, its display name, description, and notes
can be changed at a later time. The repositories belonging to the group do not
fall under this call and are instead modified using the
:doc:`membership calls<members>`.

Only changes to notes need to be specified. Unspecified notes in this call
remain unaffected. A note is removed by specifying its key with a value of null.

| :method:`put`
| :path:`/v2/repo_groups/<group_id>/`
| :permission:`update`
| :param_list:`post`

* :param:`?display_name,string,user-friendly name for the repository group`
* :param:`?description,string,user-friendly text describing the group's purpose`
* :param:`?notes,object,changes to key-value pairs to programmatically tag the group`

| :response_list:`_`

* :response_code:`200,if the update executed immediately and was successful`
* :response_code:`202,if the update was postponed until the group is available to be updated`
* :response_code:`400,if one of the parameters is invalid`
* :response_code:`404,if the group does not exist`

| :return:`updated database representation of the group`

:sample_request:`_` ::

 {
  "display_name": "Demo Group"
 }

:sample_response:`200` ::

 {
  "scratchpad": null,
  "display_name": "Demo Group",
  "description": null,
  "_ns": "repo_groups",
  "notes": {},
  "repo_ids": [],
  "_id": {
    "$oid": "500ee4028a905b04e900002e"
  },
  "id": "demo-group",
  "_href": "/pulp/api/v2/repo_groups/demo-group/"
 }
