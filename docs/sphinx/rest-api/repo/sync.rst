Synchronization
===============

Sync a Repository
-----------------

Syncs content into a repository from a feed source using the repository's
:term:`importer`. This call always executes asynchronously and will return a
:term:`call report`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/actions/sync/`
| :permission:`update`
| :param_list:`post`

* :param:`override_config,object,importer configuration values that override the importer's default configuration for this sync`

| :response_list:`_`

* :response_code:`202,if the sync is set to be executed`
* :response_code:`409,if a conflicting operation is in progress`

| :return:`call report representing the current state of they sync`

:sample_request:`_` ::

 {
   "override_config": {"verify_checksum": false,
                       "verify_size": false},
 }

:sample_response:`202` ::

 {
  "_href": "/pulp/api/v2/tasks/7744e2df-39b9-46f0-bb10-feffa2f7014b/",
  "response": "accepted",
  "reasons": [],
  "state": "waiting",
  "task_id": "7744e2df-39b9-46f0-bb10-feffa2f7014b",
  "job_id": null,
  "schedule_id": null,
  "progress": {},
  "result": null,
  "exception": null,
  "traceback": null,
  "start_time": null,
  "finish_time": null,
  "tags": ["pulp:action:sync", "pulp:repository:<repo_id>"],
 }



Scheduling a Sync
-----------------
A repository can be synced automatically using an :term:`iso8601 interval`.
To create a scheduled sync, the interval, sync override config, and other
schedule options must be set on the repository's :term:`importer`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/sync_schedules/`
| :permission:`create`
| :param_list:`post`

* :param:`schedule,string,the schedule as an iso8601 interval`
* :param:`?override_config,object,the overridden configuration for the importer to be used on the scheduled sync`
* :param:`?failure_threshold,number,consecutive failures allowed before this scheduled sync is disabled`
* :param:`?enabled,boolean,whether the scheduled sync is initially enabled (defaults to true)`

| :response_list:`_`

* :response_code:`201,if the schedule was successfully created`
* :response_code:`503,if the resources needed to create the schedule are temporarily unavailable`

| :return:`schedule report representing the current state of the scheduled call`

:sample_request:`_` ::

 {
  "override_config": {},
  "schedule": "00:00:00Z/P1DT",
  "failure_threshold": 3,
 }

:sample_response:`201` ::

 {
  "_id": "4fa0208461577710b2000000",
  "_href": "/pulp/api/v2/repositories/<repo_id>/importers/<importer_id>/sync_schedules/4fa0208461577710b2000000/",
  "schedule": "00:00:00Z/P1DT",
  "failure_threshold": 3,
  "consecutive_failures": 0,
  "first_run": null,
  "last_run": null,
  "next_run": "2012-07-13T00:00:00Z",
  "remaining_runs": null,
  "enabled": true,
  "override_config": {},
 }


Updating a Scheduled Sync
-------------------------
The same parameters used to create a scheduled sync may be updated at any point.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/sync_schedules/<schedule_id>/`
| :permission:`create`
| :param_list:`put`

* :param:`?schedule,string,new schedule as an iso8601 interval`
* :param:`?override_config,object,new overridden configuration for the importer to be used on the scheduled sync`
* :param:`?failure_threshold,number,new consecutive failures allowed before this scheduled sync is disabled`
* :param:`?enabled,boolean,whether the scheduled sync is enabled`

| :response_list:`_`

* :response_code:`200,if the schedule was successfully updated`
* :response_code:`202,if the schedule is in use and the update is postponed`
* :response_code:`503,if there is a conflicting operation in progress`

| :return:`schedule report representing the current state of the scheduled call (see sample response of Scheduling a Sync for details)`


Deleting a Scheduled Sync
-------------------------
Delete a scheduled sync to remove it permanently from the importer.

| :method:`delete`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/sync_schedules/<schedule_id>/`
| :permission:`delete`

| :response_list:`_`

* response_code:`200,if the schedule was deleted successfully`
* response_code:`202,if the schedule is in use and the delete is postponed`
* response_code:`503,if the schedule is already in the processes of being deleted`

| :return:`null`


Listing All Scheduled Syncs
---------------------------
All of the scheduled syncs for a given importer may be listed.

| :method:`get`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/sync_schedules/`
| :permission:`read`
| :return:`list of schedule reports for all scheduled syncs defined (see sample response of Scheduling a Sync for details)`


Listing a Single Scheduled Sync
-------------------------------
Each scheduled sync may be inspected.

| :method:`get`
| :permission:`read`
| :path:`/v2/repositories/<repo_id>/importers/<importer_id>/sync_schedules/<schedule_id>/`
| :return:`a schedule report for the scheduled sync (see sample response of Scheduling a Sync for details)`
