Repository Synchronize and Publish Events
=========================================

The following events are related to repo sync and publish operations.

Repository Sync Started
-----------------------

Fired when a repository sync begins.

* **Type ID:** ``repo-sync-started``
* **Body:** Contains the ID of the repository being synchronized.

**Example:** ::

  {
    "repo_id": "pulp-f17"
  }

Repository Sync Finished
------------------------

Fired when a repository sync completes. This event is fired for both successful
and failed sync operations and the body will describe the result.

* **Type ID:** ``repo-sync-finished``
* **Body:** Contains the results of the sync process. The contents will vary
  based on the success or failure of the process.

**Example Success:** ::

  {
    "importer_type_id": "yum_importer",
    "importer_id": "yum_importer",
    "exception": null,
    "repo_id": "pulp-f16",
    "removed_count": 0,
    "started": "2012-07-06T15:49:11-04:00",
    "_ns": "repo_sync_results",
    "completed": "2012-07-06T15:49:14-04:00",
    "traceback": null,
    "summary": {
      <data is contingent on the importer and removed for space>
    },
    "added_count": 0,
    "error_message": null,
    "updated_count": 0,
    "details": {
      <data is contingent on the importer and removed for space>
    },
    "id": "4ff7413a8a905b777d000072",
    "result": "success"
  }

**Example Failure:** ::

  {
    "importer_type_id": "yum_importer",
    "importer_id": "yum_importer",
    "exception": null,
    "repo_id": "pulp-f17",
    "removed_count": 0,
    "started": "2012-07-06T12:06:02-04:00",
    "_ns": "repo_sync_results",
    "completed": "2012-07-06T12:06:02-04:00",
    "traceback": null,
    "summary": {
      <data is contingent on the importer and removed for space>
    },
    "added_count": 0,
    "error_message": null,
    "updated_count": 0,
    "details": null,
    "id": "4ff70cea8a905b777d00000c",
    "result": "failed"
  }

Repository Publish Started
--------------------------

Fired when a repository publish operation begins. This includes if a repository
is configured to automatically publish after a sync.

* **Type ID:** ``repo-publish-started``
* **Body:** Contains the ID of the repository and the ID of the distributor performing
  the publish.

**Example:** ::

  {
    "repo_id": "pulp-f16",
    "distributor_id": "yum_distributor"
  }

Repository Publish Finished
---------------------------

Fired when a repository publish completes. This event is fired for both successful
and failed publish operations and the body will describe the result.

* **Type ID:** ``repo-publish-finished``
* **Body:** Contains the result of the publish process. The contents will vary
  based on the success or failure of the process.

**Example Success:** ::

  {
    "exception": null,
    "repo_id": "pulp-f16",
    "started": "2012-07-06T15:53:41-04:00",
    "_ns": "repo_publish_results",
    "completed": "2012-07-06T15:53:43-04:00",
    "traceback": null,
    "distributor_type_id": "yum_distributor",
    "summary": {
      <data is contingent on the distributor and removed for space>
    },
    "error_message": null,
    "details": {
      <data is contingent on the distributor and removed for space>
    },
    "distributor_id": "yum_distributor",
    "id": "4ff742478a905b777d00008b",
    "result": "success"
  }

