Creation, Deletion, and Configuration
=====================================

Create a Repository
-------------------

Creates a new repository in Pulp. This call accepts optional parameters 
for importer and distributor configuration. More detailed description of 
these parameters can be found below in the documentation of APIs to associate an importer 
or a distributor to an already existing repository. If these parameters are not passed, 
the call will only create the repository in Pulp. The real functionality 
of a repository isn't defined until importers and distributors are added. 
Repository IDs must be unique across all repositories in the server.

| :method:`post`
| :path:`/v2/repositories/`
| :permission:`create`
| :param_list:`post`

* :param:`id,string,unique identifier for the repository`
* :param:`?display_name,string,user-friendly name for the repository`
* :param:`?description,string,user-friendly text describing the repository's contents`
* :param:`?notes,object,key-value pairs to programmatically tag the repository`
* :param:`?importer_type_id,string,type id of importer being associated with the repository`
* :param:`?importer_config,object,configuration the repository will use to drive the behavior of the importer`
* :param:`?distributors,array,array of objects containing values of distributor_type_id, repo_plugin_config, auto_publish, and distributor_id`

| :response_list:`_`

* :response_code:`201,the repository was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a repository with the given ID`
* :response_code:`500,if the importer or distributor raises an error during initialization`

| :return:`database representation of the created repository`

:sample_request:`_` ::

 {
  "display_name": "Harness Repository: harness_repo_1",
  "id": "harness_repo_1",
  "importer_type_id": "harness_importer",
  "importer_config": {
    "num_units": "5",
    "write_files": "true"
  },
  "distributors": [{
  		"distributor_id": "dist_1",
  		"distributor_type_id": "harness_distributor",
  		"distributor_config": {
    		"publish_dir": "/tmp/harness-publish",
    		"write_files": "true"
  		},
  		"auto_publish": false
  	}],
 }


:sample_response:`201` ::

 {
  "scratchpad": {},
  "display_name": "Harness Repository: harness_repo_1",
  "description": null,
  "_ns": "repos",
  "notes": {},
  "content_unit_counts": {},
  "_id": {
    "$oid": "52280416e5e71041ad000066"
  }, 
  "id": "harness_repo_1",
  "_href": "/pulp/api/v2/repositories/harness_repo_1/"
 }

Update a Repository
-------------------

Much like create repository is simply related to the repository metadata (as
compared to the associated importers/distributors), the update repository call
is centered around updating only that metadata.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/`
| :permission:`update`
| :param_list:`put` The body of the request is a JSON document with three
  possible root elements:

* :param:`delta,object,object containing keys with values that should be updated on the repository`
* :param:`?importer_config,object,object containing keys with values that should be updated on the repository's importer config`
* :param:`?distributor_configs,object,object containing keys that are distributor ids, and values that are objects containing keys with values that should be updated on the specified distributor's config`

| :response_list:`_`

* :response_code:`200,if the update was executed and successful`
* :response_code:`202,if the update was executed but additional tasks were created to update nested distributor configurations`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if there is no repository with the give ID`

| :return:`a` :ref:`call_report` containing the database representation of the repository (after changes made by the update)
 and any tasks spawned to apply the consumer bindings for the repository.  See :ref:`bind` for details on the
 bindings tasks that will be generated.

:sample_request:`_` ::

 {
  "delta": {
   "display_name" : "Updated"
  },
  "importer_config": {
   "demo_key": "demo_value"
  }, 
  "distributor_configs": {
   "demo_distributor": {
     "demo_key": "demo_value"
   }
  }
 }

**Sample result value:**
The result field of the :ref:`call_report` contains the database representation of the repository
::

 {
 ...
 "result": {
    "display_name": "zoo",
    "description": "foo",
    "_ns": "repos",
    "notes": {
      "_repo-type": "rpm-repo"
    },
    "content_unit_counts": {
      "package_group": 2,
      "package_category": 1,
      "rpm": 32,
      "erratum": 4
    },
    "_id": {
      "$oid": "5328b2983738202945a3bb47"
    },
    "id": "zoo",
    "_href": "/pulp/api/v2/repositories/zoo/"

  },
  ...
 }


Associate an Importer to a Repository
-------------------------------------

Configures an :term:`importer` for a previously created Pulp repository. Each
repository maintains its own configuration for the importer which is used to
dictate how the importer will function when it synchronizes content. The possible
configuration values are contingent on the type of importer being added; each
importer type will support a different set of values relevant to how it functions.

Only one importer may be associated with a repository at a given time. If a
repository already has an associated importer, the previous association is removed.
The removal is performed before the new importer is initialized, thus there is
the potential that if the new importer initialization fails the repository is
left without an importer.

Adding an importer performs the following validation steps before confirming the addition:

* The importer plugin is contacted and asked to validate the supplied configuration for the importer.
  If the importer indicates its configuration is invalid, the importer is not added to the repository.
* The importer's importer_added method is invoked to allow the importer to do any initialization required
  for that repository. If the plugin raises an exception during this call, the importer is not added to the repository.
* The Pulp database is updated to store the importer's configuration and the knowledge that the repository
  is associated with the importer.

The details of the added importer are returned from the call.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/importers/`
| :permission:`create`
| :param_list:`post`

* :param:`importer_type_id,string,indicates the type of importer being associated with the repository; there must be an importer installed in the Pulp server with this ID`
* :param:`importer_config,object,configuration the repository will use to drive the behavior of the importer`

| :response_list:`_`

* :response_code:`202,if the association was queued to be performed`
* :response_code:`400,if one or more of the required parameters is missing, the importer type ID refers to a non-existent importer, or the importer indicates the supplied configuration is invalid`
* :response_code:`404,if there is no repository with the given ID`
* :response_code:`500,if the importer raises an error during initialization`

| :return:`a` :ref:`call_report` containing the current state of the association task

:sample_request:`_` ::

 {
  "importer_type_id": "harness_importer",
  "importer_config": {
    "num_units": "5",
    "write_files": "true"
  }
 }

**Sample result value for the Task Report:**
The result field of the :ref:`task_report` will contain the database representation of the importer (not the full repository details, just the importer)
::

 {
  "scratchpad": null,
  "_ns": "repo_importers",
  "importer_type_id": "harness_importer",
  "last_sync": null,
  "repo_id": "harness_repo_1",
  "_id": "bab0f9d5-dfd1-45ef-bd1d-fd7ea8077d75",
  "config": {
    "num_units": "5",
    "write_files": "true"
  },
  "id": "harness_importer"
 }

**Tags:**
The task created will have the following tags: ``"pulp:action:update_importer",
"pulp:repository:<repo_id>", "pulp:repository_importer:<importer_type_id>``

.. _distributor_associate:

Associate a Distributor with a Repository
-----------------------------------------

Configures a :term:`distributor` for a previously created Pulp repository. Each
repository maintains its own configuration for the distributor which is used to
dictate how the distributor will function when it publishes content. The possible
configuration values are contingent on the type of distributor being added; each
distributor type will support a different set of values relevant to how it functions.

Multiple distributors may be associated with a repository at a given time. There
may be more than one distributor with the same type. The only restriction is
that the distributor ID must be unique across all distributors for a given repository.

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
| :path:`/v2/repositories/<repo_id>/distributors/`
| :permission:`create`
| :param_list:`post`

* :param:`distributor_type_id,string,indicates the type of distributor being associated with the repository; there must be a distributor installed in the Pulp server with this ID`
* :param:`distributor_config,object,configuration the repository will use to drive the behavior of the distributor`
* :param:`?distributor_id,string,if specified, this value will be used to refer to the distributor; if not specified, one will be randomly assigned to the distributor`
* :param:`?auto_publish,boolean,if true, this distributor will automatically have its publish operation invoked after a successful repository sync. Defaults to false if unspecified`

| :response_list:`_`

* :response_code:`201,if the distributor was successfully added`
* :response_code:`400,if one or more of the required parameters is missing, the distributor type ID refers to a non-existent distributor, or the distributor indicates the supplied configuration is invalid`
* :response_code:`404,if there is no repository with the given ID`
* :response_code:`500,if the distributor raises an error during initialization`

| :return:`database representation of the distributor (not the full repository details, just the distributor)`

:sample_request:`_` ::

 {
  "distributor_id": "dist_1",
  "distributor_type_id": "harness_distributor",
  "distributor_config": {
    "publish_dir": "/tmp/harness-publish",
    "write_files": "true"
  },
  "auto_publish": false
 }

:sample_response:`201` ::

 {
  "scratchpad": null,
  "_ns": "repo_distributors",
  "last_publish": null,
  "auto_publish": false,
  "distributor_type_id": "harness_distributor",
  "repo_id": "harness_repo_1",
  "publish_in_progress": false,
  "_id": "cfdd6ab9-6dbe-4192-bde2-d00db768f268",
  "config": {
    "publish_dir": "/tmp/harness-publish",
    "write_files": "true"
  },
  "id": "dist_1"
 }


Update an Importer Associated with a Repository
-----------------------------------------------

Update the configuration for an :term:`importer` that has already been associated with a
repository.

Any importer configuration value that is not specified remains unchanged.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/`
| :permission:`update`
| :param_list:`put`

* :param:`importer_config,object,object containing keys with values that should be updated on the importer`

| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to update the importer
  when the repository is available`
* :response_code:`404,if there is no repository or importer with the specified IDs`

| :return:`a` :ref:`call_report` which includes a spawned task that should be polled for a :ref:`task_report`

:sample_request:`_` ::

 {
  "importer_config": {
    "demo_key": "demo_value"
  }
 }

**Sample result value for the Task Report:**
The result field of the :ref:`task_report` contains the database representation of the importer.
This does not include the full repository details.
::

  {
    "scratchpad": null,
    "_ns": "repo_importers",
    "importer_type_id": "demo_importer",
    "last_sync": "2013-10-03T14:08:35Z",
    "scheduled_syncs": [],
    "repo_id": "demo_repo",
    "_id": {
      "$oid": "524db282dd01fb194283e53f"
    },
    "config": {
      "demo_key": "demo_value"
    },
    "id": "demo_importer"
  }

**Tags:**
The task created will have the following tags: ``"pulp:action:update_importer",
"pulp:repository:<repo_id>", "pulp:repository_importer:<importer_id>``

Disassociate an Importer from a Repository
------------------------------------------

| :method:`delete`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to disassociate when the repository is available`
* :response_code:`404,if there is no repository or importer with the specified IDs`

| :return:`a` :ref:`call_report`

**Tags:**
The task created will have the following tags: ``"pulp:action:delete_importer",
"pulp:repository:<repo_id>", "pulp:repository_importer:<importer_id>``


Update a Distributor Associated with a Repository
-------------------------------------------------

Update the configuration for a :term:`distributor` that has already been associated with a
repository. This performs the following actions:

1. Updates the distributor on the server.
2. Rebinds any bound consumers.

Any distributor configuration value that is not specified remains unchanged.

The first step is represented by a :ref:`call_report`.  Upon completion of step 1 the
spawned_tasks field will be populated with links to any tasks required to complete step 2.
Updating a distributor causes each binding associated with that repository to be updated as well.
See :ref:`bind` for details.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/`
| :permission:`update`

| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to update the distributor
  when the repository is available`
* :response_code:`404,if there is no repository or distributor with the specified IDs`

| :return:`a` :ref:`call_report`

:sample_request:`_` ::

 {
  "distributor_config": {
    "demo_key": "demo_value"
  },
  "delta": {
    "auto_publish": true
  }
 }

**Tags:**
The task created to update the distributor will have the following tags: ``"pulp:action:update_distributor",
"pulp:repository:<repo_id>", "pulp:repository_distributor:<distributor_id>``
Information about the binding tasks can be found at :ref:`bind`.


.. _distributor_disassociate:

Disassociate a Distributor from a Repository
--------------------------------------------

Disassociating a distributor performs the following actions:

1. Remove the association between the distributor and the repository.
2. Unbind all bound consumers.

The first step is represented by a :ref:`call_report`.  Upon completion of step 1 the
spawned_tasks field will be populated with links to any tasks required complete step 2.
The total number of spawned tasks depends on how many consumers are bound to the repository.

| :method:`delete`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to disassociate when the repository is available`
* :response_code:`404,if there is no repository or distributor with the specified IDs`
* :response_code:`500,if the server raises an error during disassociation`

| :return:`a` :ref:`call_report`

**Tags:**
The task created to delete the distributor will have the following tags:
``"pulp:action:remove_distributor","pulp:repository:<repo_id>", "pulp:repository_distributor:<distributor_id>``


Delete a Repository
-------------------

When a repository is deleted, it is removed from the database and its local
working directory is deleted. The content within the repository, however,
is not deleted. Deleting content is handled through the
:doc:`orphaned unit <../content/orphan>` process.

Deleting a repository is performed in the following major steps:

 1. Delete the repository.
 2. Unbind all bound consumers.

The first step is represented by a :ref:`call_report`.  Upon completion of step 1 the
spawned_tasks field will be populated with links to any tasks required to complete step 2.
The total number of spawned tasks depends on how many consumers are bound to the repository.


| :method:`delete`
| :path:`/v2/repositories/<repo_id>/`
| :permission:`delete`
| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to delete the repository`
* :response_code:`404,if the requested repository does not exist`

| :return:`a` :ref:`call_report`

**Tags:**
The task created to delete the repository will have the following tags:
``"pulp:action:delete","pulp:repository:<repo_id>"``
