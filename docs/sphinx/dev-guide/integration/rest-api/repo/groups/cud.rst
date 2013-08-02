Creation, Deletion, and Configuration
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
* :param:`?repo_ids,array,list of repository ids to add to the group`
* :param:`?notes,object,key-value pairs to programmatically tag the group`
* :param:`?distributors,array,list of distributors to associate with the group on creation`

| :response_list:`_`

* :response_code:`201,the group was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a group with the given ID`

| :return:`database representation of the created group`

:sample_request:`_` ::

 {
  "id": "demo-group",
  "display_name": "Demo Group",
  "description": "Demo group description",
  "notes": {
    "key": "value"
  },
  "repo_ids": [
    "demo-repo1", 
    "demo-repo2"
  ],
  "distributors": [
    {
      "distributor_type_id": "demo_group_distributor",
      "distributor_config": {},
      "distributor_id": "optional_distributor_id"
    }
  ],
 }

:sample_response:`201` ::

 {
  "scratchpad": null,
  "id": "demo-group",
  "display_name": "Demo Group",
  "description": "Demo group description",
  "_ns": "repo_groups",
  "notes": {
    "key": "value"
  },
  "repo_ids": [
    "demo-repo1",
    "demo-repo2"
  ],
  "distributors": [
    {
      "distributor_type_id": "demo_group_distributor",
      "distributor_config": {},
      "distributor_id": "optional_distributor_id"
    }
  ],
  "_id": {
    "$oid": "500ed9888a905b04e9000021"
  },
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

Associate a Distributor to a Repository Group
---------------------------------------------

Configures a group distributor for a previously created Pulp repository group. The possible
configuration values are contingent on the type of distributor being added; each distributor
type will support a different set of values relevant to how it functions.

Multiple distributors may be associated with a repository group at a given time. The only
restriction is that the distributor ID must be unique across all distributors for a given repository.

Adding a distributor performs the following validation steps before confirming the addition:

* If provided, the distributor ID is is checked for uniqueness in the context of the repository
  group. If not provided, a unique ID is generated.
* The distributor plugin is contacted and asked to validate the supplied configuration for the
  distributor. If the distributor indicates the given configuration is invalid, the distributor is
  not added to the repository group.
* The distributor is contacted and asked to perform any necessary initialization for the distributor.
  If the plugin raises an exception during this step, the distributor is not added to the repository group.
* The Pulp database is updated to store the distributor's configuration and the knowledge that the
  repository is associated with the distributor.

The details of the added distributor are returned from the call.

| :method:`post`
| :path:`/v2/repo_groups/<group_id>/distributors/`
| :permission:`create`
| :param_list:`post`

* :param:`distributor_type_id,string,indicates the type of distributor being associated with
  the repository group; there must be a distributor installed in the Pulp server with this ID`
* :param:`distributor_config,object,configuration the repository group will use to drive the
  behavior of the distributor`
* :param:`?distributor_id,string,if specified, this value will be used to refer to the
  distributor; if not specified, a unique id will be generated`

| :response_list:`_`

* :response_code:`201,if the distributor was successfully added`
* :response_code:`400,if one or more of the required parameters is missing, the distributor type
  ID refers to a non-existent distributor, or the distributor indicates the supplied configuration
  is invalid`
* :response_code:`404,if there is no repository with the given ID`
* :response_code:`500,if the distributor raises an error during initialization`

| :return:`database representation of the distributor (not the full repository details,
  just the distributor)`

:sample_request:`_` ::

 {
  "distributor_type_id": "demo_group_distributor",
  "distributor_config": {
    "config_key": "config_value"
  },
  "distributor_id": "optional_unique_id"
 }

:sample_response:`201` ::

 {
  "_href": "/pulp/api/v2/repo_groups/demo-group/distributors/demo_group_distributor/",
  "_id": {
    "$oid": "51f2c2e7eefe871d8c2d6049"
  },
  "_ns": "repo_group_distributors",
  "config": {
    "config_key": "config_value"
  },
  "distributor_type_id": "demo_group_distributor",
  "id": "optional_unique_id",
  "last_publish": null,
  "repo_group_id": "demo-group",
  "scratchpad": null
 }

Disassociate a Distributor from a Repository Group
--------------------------------------------------

Disassociating a distributor removes the association between the distributor and the repository

| :method:`delete`
| :path:`/v2/repo_groups/<group_id>/distributors/<distributor_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200,if the distributor was successfully removed`
* :response_code:`404,if there was repository group or distributor with the specified IDs`
* :response_code:`500,if the server raises an error during disassociation`

| :return:`null`
