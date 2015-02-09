Synchronization
===============

Sync a Repository
-----------------

Syncs content into a repository from a feed source using the repository's
:term:`importer`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/actions/sync/`
| :permission:`execute`
| :param_list:`post`

* :param:`override_config,object,importer configuration values that override the importer's default configuration for this sync`

| :response_list:`_`

* :response_code:`202,if the sync is set to be executed`
* :response_code:`404,if repo does not exist`

| :return:`a` :ref:`call_report`

:sample_request:`_` ::

 {
   "override_config": {"verify_checksum": false,
                       "verify_size": false},
 }

**Tags:**
The task created will have the following tags:
``"pulp:action:sync", "pulp:repository:<repo_id>"``


Scheduling a Sync
-----------------
A repository can be synced automatically using an :term:`iso8601 interval`.
To create a scheduled sync, the interval, sync override config, and other
schedule options must be set on the repository's :term:`importer`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/schedules/sync/`
| :permission:`create`
| :param_list:`post`

* :param:`schedule,string,the schedule as an iso8601 interval`
* :param:`?override_config,object,the overridden configuration for the importer to be used on the scheduled sync`
* :param:`?failure_threshold,number,consecutive failures allowed before this scheduled sync is disabled`
* :param:`?enabled,boolean,whether the scheduled sync is initially enabled (defaults to true)`

| :response_list:`_`

* :response_code:`201,if the schedule was successfully created`
* :response_code:`400,if one or more of the parameters are invalid`
* :response_code:`404,if there is no repository or importer with the specified IDs`

| :return:`schedule report representing the current state of the scheduled call`

:sample_request:`_` ::

 {
  "override_config": {},
  "schedule": "00:00:00Z/P1DT",
  "failure_threshold": 3,
 }

:sample_response:`201` ::

 {
  "next_run": "2014-01-27T21:41:50Z",
  "task": "pulp.server.tasks.repository.sync_with_auto_publish",
  "last_updated": 1390858910.292712,
  "first_run": "2014-01-27T21:41:50Z",
  "schedule": "PT1H",
  "args": [
    "demo"
  ],
  "enabled": true,
  "last_run_at": null,
  "_id": "52e6d29edd01fb70bd0d9c37",
  "total_run_count": 0,
  "failure_threshold": 3,
  "kwargs": {
    "overrides": {}
  },
  "resource": "pulp:importer:demo:puppet_importer",
  "remaining_runs": null,
  "consecutive_failures": 0,
  "_href": "/pulp/api/v2/repositories/demo/importers/puppet_importer/schedules/sync/52e6d29edd01fb70bd0d9c37/"
 }



Updating a Scheduled Sync
-------------------------
The same parameters used to create a scheduled sync may be updated at any point.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/schedules/sync/<schedule_id>/`
| :permission:`create`
| :param_list:`put`

* :param:`?schedule,string,new schedule as an iso8601 interval`
* :param:`?override_config,object,new overridden configuration for the importer to be used on the scheduled sync`
* :param:`?failure_threshold,number,new consecutive failures allowed before this scheduled sync is disabled`
* :param:`?enabled,boolean,whether the scheduled sync is enabled`

| :response_list:`_`

* :response_code:`200,if the schedule was successfully updated`
* :response_code:`400,if one or more of the parameters are invalid`
* :response_code:`404,if there is no repository, importer or schedule with the specified IDs`

| :return:`schedule report representing the current state of the scheduled call (see sample response of Scheduling a Sync for details)`


Deleting a Scheduled Sync
-------------------------
Delete a scheduled sync to remove it permanently from the importer.

| :method:`delete`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/schedules/sync/<schedule_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200,if the schedule was deleted successfully`
* :response_code:`404,if there is no repository, importer or schedule with the specified IDs`

| :return:`null`


Listing All Scheduled Syncs
---------------------------
All of the scheduled syncs for a given importer may be listed.

| :method:`get`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/schedules/sync/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200,if repo, importer exist`
* :response_code:`404,if there is no repository or importer with the specified IDs`

| :return:`array of schedule reports for all scheduled syncs defined`

:sample_response:`200` ::

 [
    {
        "_href": "/pulp/api/v2/repositories/test/importers/yum_importer/schedules/sync/54d8852245ef4876fade7cc2/",
        "_id": "54d8852245ef4876fade7cc2",
        "args": [
            "test"
        ],
        "consecutive_failures": 0,
        "enabled": true,
        "failure_threshold": null,
        "first_run": "2015-02-09T10:00:02Z",
        "kwargs": {
            "overrides": {}
        },
        "last_run_at": "2015-02-09T10:00:23Z",
        "last_updated": 1423476133.825821,
        "next_run": "2015-02-10T10:00:02Z",
        "remaining_runs": null,
        "resource": "pulp:importer:test:yum_importer",
        "schedule": "P1DT",
        "task": "pulp.server.tasks.repository.sync_with_auto_publish",
        "total_run_count": 1
    }
 ]



Listing a Single Scheduled Sync
-------------------------------
Each scheduled sync may be inspected.

| :method:`get`
| :permission:`read`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/schedules/sync/<schedule_id>/`

| :response_list:`_`

* :response_code:`200,if repo, importer, schedule exist`
* :response_code:`404,if there is no repository, importer or schedule with the specified IDs`

| :return:`a schedule report for the scheduled sync`

:sample_response:`200` ::

 {
    "_href": "/pulp/api/v2/repositories/test/importers/yum_importer/schedules/sync/54d8852245ef4876fade7cc2/",
    "_id": "54d8852245ef4876fade7cc2",
    "args": [
        "test"
    ],
    "consecutive_failures": 0,
    "enabled": true,
    "failure_threshold": null,
    "first_run": "2015-02-09T10:00:02Z",
    "kwargs": {
        "overrides": {}
    },
    "last_run_at": "2015-02-09T10:00:23Z",
    "last_updated": 1423476133.825821,
    "next_run": "2015-02-10T10:00:02Z",
    "remaining_runs": null,
    "resource": "pulp:importer:test:yum_importer",
    "schedule": "P1DT",
    "task": "pulp.server.tasks.repository.sync_with_auto_publish",
    "total_run_count": 1
 }


Retrieving Sync History
-----------------------
Retrieve sync history for a repository. Each sync performed on a repository creates a history entry.

| :method:`get`
| :permission:`read`
| :path:`/v2/repositories/<repo_id>/history/sync/`

| :param_list:`get`

* :param:`?limit,integer,the maximum number of history entries to return; if not specified, the entire
  history is returned`
* :param:`?sort,string,options are 'ascending' and 'descending'; the array is sorted by the sync timestamp`
* :param:`?start_date,iso8601 datetime,any entries with a timestamp prior to the given date are not returned`
* :param:`?end_date,iso8601 datetime,any entries with a timestamp after the given date are not returned`

| :response_list:`_`

* :response_code:`200,if the history was successfully retrieved`
* :response_code:`404,if the repository id given does not exist`

| :return:`an array of sync history entries`

:sample_response:`200` ::

 [
  {
   "result": "success",
   "importer_id": "my_demo_importer",
   "exception": null,
   "repo_id": "demo_repo",
   "traceback": null,
   "started": "1970:00:00T00:00:00Z",
   "completed": "1970:00:00T00:00:01Z",
   "importer_type_id": "demo_importer",
   "error_message": null,
  }
 ]
