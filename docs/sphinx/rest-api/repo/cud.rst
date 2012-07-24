Creation, Delete, and Configuration
===================================

Create a Repository
-------------------

Creates a new repository in Pulp. This call only creates the repository in Pulp;
the real functionality of a repository isn't defined until importers and
distributors are added. Repository IDs must be unique across all repositories
in the server.

| :method:`post`
| :path:`/v2/repositories/`
| :permission:`create`
| :param_list:`post`

* :param:`id,string,unique identifier for the repository`
* :param:`?display_name,string,user-friendly name for the repository`
* :param:`?description,string,user-friendly text describing the repository's contents`
* :param:`?notes,object,key-value pairs to programmatically tag the repository`

| :response_list:`_`

* :response_code:`201,the repository was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a repository with the given ID`

| :return:`database representation of the created repository`

:sample_request:`_` ::

 {
  "display_name": "Harness Repository: harness_repo_1",
  "id": "harness_repo_1"
 }


:sample_response:`201` ::

 {
  "display_name": "Harness Repository: harness_repo_1",
  "description": null,
  "_ns": "gc_repositories",
  "notes": {},
  "content_unit_count": 0,
  "_id": "harness_repo_1",
  "id": "harness_repo_1"
 }

Update a Repository
-------------------

Much like create repository is simply related to the repository metadata (as
compared to the associated importers/distributors), the update repository call
is centered around updating only that metadata.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/`
| :permission:`update`
| :param_list:`post` The body of the request is a JSON document with a root element
  called "delta". The contents of delta are the values to update. Only changed
  parameters need be specified. The following keys are allowed in the delta
  dictionary. Descriptions for each parameter can be found under the create
  repository API:

* :param:`display_name,,`
* :param:`description,,`
* :param:`notes,,`

| :response_list:`_`

* :response_code:`200,if the update was executed and successful`
* :response_code:`202,if the update was postponed`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if there is no repository with the give ID`

| :return:`database representation of the repository (after changes made by the update)`

:sample_request:`_` ::

 {
  "delta": {"display_name" : "Updated"},
 }

:sample_response:`200` ::

 {
  "display_name": "Updated",
  "description": null,
  "_ns": "gc_repositories",
  "notes": {},
  "content_unit_count": 0,
  "_id": "harness_repo_1",
  "id": "harness_repo_1"
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

* :response_code:`201,if the importer was successfully added`
* :response_code:`400,if one or more of the required parameters is missing, the importer type ID refers to a non-existent importer, or the importer indicates the supplied configuration is invalid`
* :response_code:`404,if there is no repository with the given ID`
* :response_code:`500,if the importer raises an error during initialization`

| :return:`database representation of the importer (not the full repository details, just the importer)`

:sample_request:`_` ::

 {
  "importer_type_id": "harness_importer",
  "importer_config": {
    "num_units": "5",
    "write_files": "true"
  }
 }

:sample_response:`201` ::

 {
  "scratchpad": null,
  "_ns": "gc_repo_importers",
  "importer_type_id": "harness_importer",
  "last_sync": null,
  "repo_id": "harness_repo_1",
  "sync_in_progress": false,
  "_id": "bab0f9d5-dfd1-45ef-bd1d-fd7ea8077d75",
  "config": {
    "num_units": "5",
    "write_files": "true"
  },
  "id": "harness_importer"
 }

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
  "_ns": "gc_repo_distributors",
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

Delete a Repository
-------------------

When a repository is deleted, it is removed from the database and its local
working directory is deleted. The content within the repository, however,
is not deleted. Deleting content is handled through the
:doc:`orphaned unit <../content/orphan>` process.

| :method:`delete`
| :path:`/v2/repositories/<repo_id>/`
| :permission:`delete`
| :response_list:`_`

* :response_code:
* :response_code:`202,if the request was accepted by the server to delete when the repository is available`

| :return:`call report representing the current state of the delete`
