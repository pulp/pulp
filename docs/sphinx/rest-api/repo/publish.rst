Publication
===========

Publish a Repository
--------------------

Publish content from a repository using a repository's :term:`distributor`. This
call always executes asynchronously and will return a :term:`call report`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/actions/publish/`
| :permission:`update`
| :param_list:`post`

* :param:`override_config,object,distributor configuration values that override the distributor's default configuration for this publish`

| :response_list:`_`

* :response_code:`202, if the publish is set to be executed`
* :response_code:`409, if a conflicting operation is in progress`

| :return:`call report representing the current state of they sync`

:sample_request:`_` ::

 {
   "override_config": {},
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
  "tags": ["pulp:action:publish", "pulp:repository:<repo_id>"],
 }



Scheduling a Publish
--------------------
A repository can be published automatically using an :term:`iso8601 interval`.
To create a scheduled publish, the interval, publish override config, and other
schedule options must be set on a repository's :term:`distributor`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/publish_schedules/`
| :permission:`create`
| :param_list:`post`

* :param:`schedule,string,the schedule as an iso8601 interval`
* :param:`?override_config,object,the overridden configuration for the distributor to be used on the scheduled publish`
* :param:`?failure_threshold,number,consecutive failures allowed before this scheduled publish is disabled`
* :param:`?enabled,boolean,whether the scheduled publish is initially enabled (defaults to true)`

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
  "_href": "/pulp/api/v2/repositories/<repo_id>/distributors/<distributor_id>/publish_schedules/4fa0208461577710b2000000/",
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


Updating a Scheduled Publish
----------------------------
The same parameters used to create a scheduled publish may be updated at any point.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/publish_schedules/<schedule_id>/`
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

| :return:`schedule report representing the current state of the scheduled call (see sample response of Scheduling a Publish for details)`


Deleting a Scheduled Publish
----------------------------
Delete a scheduled publish to remove it permanently from the distributor.

| :method:`delete`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/publish_schedules/<schedule_id>/`
| :permission:`delete`

| :response_list:`_`

* response_code:`200,if the schedule was deleted successfully`
* response_code:`202,if the schedule is in use and the delete is postponed`
* response_code:`503,if the schedule is already in the processes of being deleted`

| :return:`null`


Listing All Scheduled Publishes
-------------------------------
All of the scheduled publishes for a given distributor may be listed.

| :method:`get`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/publish_schedules/`
| :permission:`read`
| :return:`list of schedule reports for all scheduled publishes defined (see sample response of Scheduling a Publish for details)`


Listing a Single Scheduled Publish
----------------------------------
Each scheduled publish may be inspected.

| :method:`get`
| :permission:`read`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/publish_schedules/<schedule_id>/`
| :return:`a schedule report for the scheduled publish (see sample response of Scheduling a Publish for details)`
