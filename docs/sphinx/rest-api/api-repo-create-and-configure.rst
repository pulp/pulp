Create a Repository
===================

Creates a new repository in Pulp. This call only creates the repository in Pulp;
the real functionality of a repository isn't defined until importers and
distributors are added. Repository IDs must be unique across all repositories
in the server.

* **method:** POST
* **path:** /v2/repositories/
* **parameters:** The body of the request is a JSON document that contains the
  following parameters:
 * **id** *(str)* - unique identifier for the repository
 * **display_name** *(str)* - optional; user-friendly name for the repository
 * **description** *(str)* - optional; user-friendly text describing the repository's contents
 * **notes** *(dict)* - optional; key-value pairs to programmatically tag the repository
* **permission:** create
* **success response:** 201
* **failure responses:**
 * 409 - If there is already a repository with the given ID
 * 400 - If one or more of the parameters is invalid
* **return:** database representation of the created repository

Sample request body::

 {
  "display_name": "Harness Repository: harness_repo_1",
  "id": "harness_repo_1"
 }


Sample response body::

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
===================

Much like create repository is simply related to the repository metadata (as
compared to the associated importers/distributors), the update repository call
is centered around updating only that metadata.

* **method:** PUT
* **path:** /v2/repositories/<repo_id>/
* **parameters:** The body of the request is a JSON document with a root element
  called "delta". The contents of delta are the values to update. Only changed
  parameters need be specified. The following keys are allowed in the delta
  dictionary. Descriptions for each parameter can be found under the create
  repository API:
 * **display_name**
 * **description**
 * **notes**
* **permission:** update
* **success response:** 200
* **failure responses:**
 * 404 - If there is no repository with the give ID
 * 400 - If one or more of the parameters is invalid
* **return:** database representation of the repository (after changes made by the update)

Sample request body::

 {
  "delta": {"display_name" : "Updated"},
 }

Sample response body::

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
=====================================

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

* **method:** POST
* **path:** /v2/repositories/<repo_id>/importers/
* **parameters:** The body of the request is a JSON document that contains the following parameters:
 * **importer_type_id** *(str)* - Indicates the type of importer being associated with the repository. There must be an importer installed in the Pulp server with this ID.
 * **importer_config** *(dict)* - Configuration the repository will use to drive the behavior of the importer.
* **permission:** create
* **success response:** 201
* **failure responses:**
 * 404 - If there is no repository with the given ID.
 * 400 - If one or more of the required parameters is missing, the importer type ID refers to a
   non-existent importer, or the importer indicates the supplied configuration is invalid.
 * 500 - If the importer raises an error during initialization.
* **return:** database representation of the importer (not the full repository
  details, just the importer)

Sample request body::

 {
  "importer_type_id": "harness_importer",
  "importer_config": {
    "num_units": "5",
    "write_files": "true"
  }
 }

Sample response body::

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
=========================================

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

* **method:** POST
* **path:** /v2/repositories/<repo_id>/distributors/
* **parameters:** The body of the request is a JSON document that contains the following parameters:
 * **distributor_type_id** *(str)* - Indicates the type of distributor being associated with the
   repository. There must be a distributor installed in the Pulp server with this ID.
 * **distributor_config** *(dict)* - Configuration the repository will use to drive the
   behavior of the distributor.
 * **distributor_id** *(str)* - optional; If specified, this value will be used to refer
   to the distributor. If not specified, one will be randomly assigned to the distributor.
 * **auto_publish** *(bool)* - optional; If true, this distributor will automatically have
   its publish operation invoked after a successful repository sync. Defaults to false if unspecified.
* **permission:** create
* **success response:** 201
* **failure responses:**
 * 404 - If there is no repository with the given ID.
 * 400 - If one or more of the required parameters is missing, the distributor
   type ID refers to a non-existent distributor, or the distributor indicates
   the supplied configuration is invalid.
 * 500 - If the distributor raises an error during initialization.

Sample request body::

 {
  "distributor_id": "dist_1",
  "distributor_type_id": "harness_distributor",
  "distributor_config": {
    "publish_dir": "/tmp/harness-publish",
    "write_files": "true"
  },
  "auto_publish": false
 }

Sample response body::

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
