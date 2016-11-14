Repository Group Distributors
=============================

List Repository Group Distributors
----------------------------------

Retrieves all distributors associated with a given group

| :method:`get`
| :path:`/v2/repo_groups/<group_id>/distributors/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200,if the group exists`

| :return:`an array of objects that represent distributors`

:sample_response:`200`::

 [
  {
    "scratchpad": null,
    "repo_group_id": "test_group",
    "_ns": "repo_group_distributors",
    "last_publish": "2014-06-12T14:38:05Z",
    "distributor_type_id": "group_test_distributor",
    "_id": {
      "$oid": "5399f38b7bc8f60c78d856bf"
    },
    "config": {
      "config_value1": false,
      "config_value2": true
    },
    "id": "2a146bdf-384b-4951-987e-8d42c7c4317f",
    "_href": "2a146bdf-384b-4951-987e-8d42c7c4317f"
  }
 ]


Add a Distributor to a Repository Group
---------------------------------------

Configures a :term:`distributor` for a previously created Pulp repository group. Each
repository group maintains its own configuration for the distributor which is used to
dictate how the distributor will function when it publishes content. The possible
configuration values are contingent on the type of distributor being added; each
distributor type will support a different set of values relevant to how it functions.

Multiple distributors may be associated with a repository group at a given time. There
may be more than one distributor with the same type. The only restriction is
that the distributor ID must be unique across all distributors for a given repository group.

Adding a distributor performs the following validation steps before confirming the addition:

* If provided, the distributor ID is checked for uniqueness in the context of
  the repository. If not provided, a unique ID is generated.
* The distributor plugin is contacted and asked to validate the supplied
  configuration for the distributor. If the distributor indicates its configuration
  is invalid, the distributor is not added to the repository.
* The distributor's distributor_added method is invoked to allow the distributor
  to do any initialization required for that repository. If the plugin raises an
  exception during this call, the distributor is not added to the repository.
* The Pulp database is updated to store the distributor's configuration and the
  knowledge that the repository is associated with the distributor.

The details of the added distributor are returned from the call.

| :method:`post`
| :path:`/v2/repo_groups/<group_id>/distributors/`
| :permission:`create`

| :param_list:`post`

* :param:`distributor_type_id,string,indicates the type of distributor being associated with the
  repository group; there must be a distributor installed in the Pulp server with this ID`
* :param:`distributor_config,object,configuration the repository will use to drive the behavior
  of the distributor`
* :param:`?distributor_id,string,if specified, this value will be used to refer to the distributor;
  if not specified, one will be generated`

| :response_list:`_`

* :response_code:`201,if the distributor was successfully added`
* :response_code:`400,if one or more of the required parameters is missing, the distributor type ID refers
  to a non-existent distributor, or the distributor indicates the supplied configuration is invalid`
* :response_code:`404,if there is no repository with the given ID`

| :return:`an object that represents the newly added distributor`

:sample_response:`201`::

 {
  "scratchpad": null,
  "repo_group_id": "test_group",
  "_ns": "repo_group_distributors",
  "last_publish": null,
  "distributor_type_id": "group_test_distributor",
  "_id": {
    "$oid": "5399fb527bc8f60c77d7c82a"
  },
  "config": {
    "config_value1": false,
    "config_value2": true
  },
  "id": "test_id",
  "_href": "/pulp/api/v2/repo_groups/test_group/distributors/unique_distributor_id/"
 }


Retrieve a Repository Group Distributor
---------------------------------------

Retrieve a specific distributor that is associated with a group.

| :method:`get`
| :path:`/v2/repo_groups/<group_id>/distributors/<distributor_id>/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200,containing an object representing the distributor`
* :response_code:`404,if either the group_id or the distributor_id do not exist on the server`

| :return:`an object that represents the specified distributor`

:sample_response:`200`::

 {
  "scratchpad": null,
  "repo_group_id": "test_group",
  "_ns": "repo_group_distributors",
  "last_publish": null,
  "distributor_type_id": "group_test_distributor",
  "_id": {
    "$oid": "5399fb527bc8f60c77d7c82a"
  },
  "config": {
    "config_value1": false,
    "config_value2": true
  },
  "id": "test_id",
  "_href": "/pulp/api/v2/repo_groups/test_group/distributors/test_id/"
 }


Update a Repository Group Distributor
-------------------------------------

Update the configuration for a :term:`distributor` that has already been associated with a
repository group.

Any distributor configuration value that is not specified remains unchanged.

| :method:`put`
| :path:`/v2/repo_groups/<group_id>/distributors/<distributor_id>/`
| :permission:`update`

| :param_list:`put`

* :param:`distributor_config,object,configuration values to change for the distributor`

| :response_list:`_`

* :response_code:`200,if the configuration was successfully updated`
* :response_code:`404,if there is no repository group or distributor with the specified IDs`

| :return:`an object that represents the updated distributor`

:sample_request:`_`::

 {
  'distributor_config': {
    "config_value2": false
  }
 }

:sample_response:`200`::

 {
  "scratchpad": null,
  "repo_group_id": "test_group",
  "_ns": "repo_group_distributors",
  "last_publish": null,
  "distributor_type_id": "group_test_distributor",
  "_id": {
    "$oid": "5399fb527bc8f60c77d7c82a"
  },
  "config": {
    "config_value1": false,
    "config_value2": false
  },
  "id": "test_id",
  "_href": "/pulp/api/v2/repo_groups/test_group/distributors/test_id/"
 }


Disassociate a Repository Group Distributor
-------------------------------------------

Remove a repository group :term:`distributor` from a repository group

| :method:`delete`
| :path:`/v2/repo_groups/<group_id>/distributors/<distributor_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200,if the distributor was successfully disassociated from the repository group`
* :response_code:`404,if the given group does not have a distributor with the given distributor id,
  or if the given group does not exist`

| :return:`null will be returned if the distributor was successfully removed`
