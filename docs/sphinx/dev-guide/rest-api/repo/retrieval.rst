Retrieval
=========

Retrieve a Single Repository
----------------------------

Retrieves information on a single Pulp repository. The returned data includes
general repository metadata and metadata describing any :term:`importers <importer>`
and :term:`distributors <distributor>` associated with it.

| :method:`get`
| :path:`/v2/repositories/<repo_id>/`
| :permission:`read`

| :param_list:`get`

* :param:`?details,bool,shortcut for including both distributors and importers`
* :param:`?importers,bool,include the "importers" attribute on each repository`
* :param:`?distributors,bool,include the "distributors" attribute on each repository`

| :response_list:`_`

* :response_code:`200,if the repository exists`
* :response_code:`404,if no repository exists with the given ID`

| :return:`database representation of the matching repository`

:sample_response:`200` ::

 {
  "display_name": "Harness Repository: harness_repo_1",
  "description": null,
  "distributors": [
    {
      "scratchpad": 1,
      "_ns": "gc_repo_distributors",
      "last_publish": "2012-01-25T15:26:32-05:00",
      "auto_publish": false,
      "distributor_type_id": "harness_distributor",
      "repo_id": "harness_repo_1",
      "publish_in_progress": false,
      "_id": "addf9261-345e-4ce3-ad1e-436ba005287f",
      "config": {
        "publish_dir": "/tmp/harness-publish",
        "write_files": "true"
      },
      "id": "dist_1"
    }
  ],
  "notes": {},
  "content_unit_count": 0,
  "importers": [
    {
      "scratchpad": 1,
      "_ns": "gc_repo_importers",
      "importer_type_id": "harness_importer",
      "last_sync": "2012-01-25T15:26:32-05:00",
      "repo_id": "harness_repo_1",
      "sync_in_progress": false,
      "_id": "bbe81308-ef7c-4c0c-b684-385fd627d99e",
      "config": {
        "num_units": "5",
        "write_files": "true"
      },
      "id": "harness_importer"
    }
  ],
  "id": "harness_repo_1"
 }


Retrieve All Repositories
-------------------------

Returns information on all repositories in the Pulp server. It is worth noting
that this call will never return a 404; an empty list is returned in the case
where there are no repositories.

| :method:`get`
| :path:`/v2/repositories/`
| :permission:`read`
| :param_list:`get`

* :param:`?details,bool,shortcut for including both distributors and importers`
* :param:`?importers,bool,include the "importers" attribute on each repository`
* :param:`?distributors,bool,include the "distributors" attribute on each repository`

| :response_list:`_`

* :response_code:`200,containing the list of repositories`

| :return:`the same format as retrieving a single repository, except the base of the return value is a list of them`

:sample_response:`200` ::

 [
  {
    "display_name": "Harness Repository: harness_repo_1",
    "description": null,
    "distributors": [
      {
        "scratchpad": 1,
        "_ns": "gc_repo_distributors",
        "last_publish": "2012-01-25T15:26:32-05:00",
        "auto_publish": false,
        "distributor_type_id": "harness_distributor",
        "repo_id": "harness_repo_1",
        "publish_in_progress": false,
        "_id": "addf9261-345e-4ce3-ad1e-436ba005287f",
        "config": {
          "publish_dir": "/tmp/harness-publish",
          "write_files": "true"
        },
        "id": "dist_1"
      }
    ],
    "notes": {},
    "content_unit_count": 0,
    "importers": [
      {
        "scratchpad": 1,
        "_ns": "gc_repo_importers",
        "importer_type_id": "harness_importer",
        "last_sync": "2012-01-25T15:26:32-05:00",
        "repo_id": "harness_repo_1",
        "sync_in_progress": false,
        "_id": "bbe81308-ef7c-4c0c-b684-385fd627d99e",
        "config": {
          "num_units": "5",
          "write_files": "true"
        },
        "id": "harness_importer"
      }
    ],
    "id": "harness_repo_1"
  }
 ]

Advanced Search for Repositories
--------------------------------

Please see :ref:`search_api` for more details on how to perform these searches.

Returns information on repositories in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no repositories.

| :method:`post`
| :path:`/v2/repositories/search/`
| :permission:`read`
| :param_list:`post`

* :param:`?importers,bool,include the "importers" attribute on each repository`
* :param:`?distributors,bool,include the "distributors" attribute on each repository`

| :response_list:`_`

* :response_code:`200,containing the list of repositories`

| :return:`the same format as retrieving a single repository, except the base of the return value is a list of them`

:sample_response:`200` ::

 [
  {
    "display_name": "Harness Repository: harness_repo_1",
    "description": null,
    "distributors": [
      {
        "scratchpad": 1,
        "_ns": "gc_repo_distributors",
        "last_publish": "2012-01-25T15:26:32-05:00",
        "auto_publish": false,
        "distributor_type_id": "harness_distributor",
        "repo_id": "harness_repo_1",
        "publish_in_progress": false,
        "_id": "addf9261-345e-4ce3-ad1e-436ba005287f",
        "config": {
          "publish_dir": "/tmp/harness-publish",
          "write_files": "true"
        },
        "id": "dist_1"
      }
    ],
    "notes": {},
    "content_unit_count": 0,
    "importers": [
      {
        "scratchpad": 1,
        "_ns": "gc_repo_importers",
        "importer_type_id": "harness_importer",
        "last_sync": "2012-01-25T15:26:32-05:00",
        "repo_id": "harness_repo_1",
        "sync_in_progress": false,
        "_id": "bbe81308-ef7c-4c0c-b684-385fd627d99e",
        "config": {
          "num_units": "5",
          "write_files": "true"
        },
        "id": "harness_importer"
      }
    ],
    "id": "harness_repo_1"
  }
 ]

Returns information on repositories in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no repositories.

This method is slightly more limiting than the POST alternative, because some
filter expressions may not be serializable as query parameters.

| :method:`get`
| :path:`/v2/repositories/search/`
| :permission:`read`
| :param_list:`get` query params should match the attributes of a Criteria
 object as defined in :ref:`search_criteria`. The exception is the 'fields'
 parameter, which should be specified in singular form as follows:
 For example: /v2/repositories/search/?field=id&field=display_name&limit=20'

* :param:`?details,bool,shortcut for including both distributors and importers`
* :param:`?importers,bool,include the "importers" attribute on each repository`
* :param:`?distributors,bool,include the "distributors" attribute on each repository`

| :response_list:`_`

* :response_code:`200,containing the list of repositories`

| :return:`the same format as retrieving a single repository, except the base of the return value is a list of them`

:sample_response:`200` ::

 [
  {
    "display_name": "Harness Repository: harness_repo_1",
    "description": null,
    "distributors": [
      {
        "scratchpad": 1,
        "_ns": "gc_repo_distributors",
        "last_publish": "2012-01-25T15:26:32-05:00",
        "auto_publish": false,
        "distributor_type_id": "harness_distributor",
        "repo_id": "harness_repo_1",
        "publish_in_progress": false,
        "_id": "addf9261-345e-4ce3-ad1e-436ba005287f",
        "config": {
          "publish_dir": "/tmp/harness-publish",
          "write_files": "true"
        },
        "id": "dist_1"
      }
    ],
    "notes": {},
    "content_unit_count": 0,
    "importers": [
      {
        "scratchpad": 1,
        "_ns": "gc_repo_importers",
        "importer_type_id": "harness_importer",
        "last_sync": "2012-01-25T15:26:32-05:00",
        "repo_id": "harness_repo_1",
        "sync_in_progress": false,
        "_id": "bbe81308-ef7c-4c0c-b684-385fd627d99e",
        "config": {
          "num_units": "5",
          "write_files": "true"
        },
        "id": "harness_importer"
      }
    ],
    "id": "harness_repo_1"
  }
 ]

Retrieve Importers Associated with a Repository
-----------------------------------------------

Retrieves the :term:`importer` (if any) associated with a repository. The list
will either be empty (no importer configured) or contain a single entry.

| :method:`get`
| :path:`/v2/repositories/<repo_id>/importers/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200,containing a list of importers`
* :response_code:`404,if there is no repository with the given ID; this will not occur if the repository exists but has no associated importers`

| :return:`database representation of the repository's importer or an empty list`

:sample_response:`200` ::

 [
  {
    "scratchpad": 1,
    "_ns": "gc_repo_importers",
    "importer_type_id": "harness_importer",
    "last_sync": "2012-01-25T15:26:32-05:00",
    "repo_id": "harness_repo_1",
    "sync_in_progress": false,
    "_id": "bbe81308-ef7c-4c0c-b684-385fd627d99e",
    "config": {
      "num_units": "5",
      "write_files": "true"
    },
    "id": "harness_importer"
  }
 ]

Retrieve Distributors Associated with a Repository
--------------------------------------------------

Retrieves all :term:`distributors <distributor>` associated with a repository.
If the repository has no associated distributors, an empty list is returned.

| :method:`get`
| :path:`/v2/repositories/<repo_id>/distributors/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200,containing a list of distributors`
* :response_code:`404,if there is no repository with the given ID; this will not occur if the repository exists but has no associated distributors`

| :return:`database representations of all distributors on the repository`

:sample_response:`200` ::

 [
  {
    "scratchpad": 1,
    "_ns": "gc_repo_distributors",
    "last_publish": "2012-01-25T15:26:32-05:00",
    "auto_publish": false,
    "distributor_type_id": "harness_distributor",
    "repo_id": "harness_repo_1",
    "publish_in_progress": false,
    "_id": "addf9261-345e-4ce3-ad1e-436ba005287f",
    "config": {
      "publish_dir": "/tmp/harness-publish",
      "write_files": "true"
    },
    "id": "dist_1"
  }
 ]
