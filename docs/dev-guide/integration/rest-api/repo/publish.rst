Publication
===========

.. _repository_publish:

Publish a Repository
--------------------

Publish content from a repository using a repository's :term:`distributor`. This
call always executes asynchronously and will return a :term:`call report`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/actions/publish/`
| :permission:`execute`
| :param_list:`post`

* :param:`id,str,identifies which distributor on the repository to publish`
* :param:`?override_config,object,distributor configuration values that override the distributor's default configuration for this publish`

| :response_list:`_`

* :response_code:`202, if the publish is set to be executed`
* :response_code:`404,if repo does not exist`

| :return:`a` :ref:`call_report` representing the current state of the sync

:sample_request:`_` ::

 {
   "id": "distributor_1",
   "override_config": {},
 }

**Tags:**
The task created will have the following tags:
``"pulp:action:publish","pulp:repository:<repo_id>"``


Scheduling a Publish
--------------------
A repository can be published automatically using an :term:`iso8601 interval`.
To create a scheduled publish, the interval, publish override config, and other
schedule options must be set on a repository's :term:`distributor`.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/schedules/publish/`
| :permission:`create`
| :param_list:`post`

* :param:`schedule,string,the schedule as an iso8601 interval`
* :param:`?override_config,object,the overridden configuration for the distributor to be used on the scheduled publish`
* :param:`?failure_threshold,number,consecutive failures allowed before this scheduled publish is disabled`
* :param:`?enabled,boolean,whether the scheduled publish is initially enabled (defaults to true)`

| :response_list:`_`

* :response_code:`201,if the schedule was successfully created`
* :response_code:`400,if one or more of the parameters are invalid`
* :response_code:`404,if there is no repository or distributor with the specified IDs`

| :return:`schedule report representing the current state of the scheduled call`

:sample_request:`_` ::

 {
  "override_config": {},
  "schedule": "PT1H",
  "failure_threshold": 3,
 }

:sample_response:`201` ::

 {
  "next_run": "2014-01-27T21:27:56Z",
  "task": "pulp.server.tasks.repository.publish",
  "last_updated": 1390858076.682694,
  "first_run": "2014-01-27T21:27:56Z",
  "schedule": "PT1H",
  "args": [
    "demo",
    "puppet_distributor"
  ],
  "enabled": true,
  "last_run_at": null,
  "_id": "52e6cf5cdd01fb70bd0d9c34",
  "total_run_count": 0,
  "failure_threshold": 3,
  "kwargs": {
    "overrides": {}
  },
  "resource": "pulp:distributor:demo:puppet_distributor",
  "remaining_runs": null,
  "consecutive_failures": 0,
  "_href": "/pulp/api/v2/repositories/demo/distributors/puppet_distributor/schedules/publish/52e6cf5cdd01fb70bd0d9c34/"
 }

Updating a Scheduled Publish
----------------------------
The same parameters used to create a scheduled publish may be updated at any point.

| :method:`put`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/schedules/publish/<schedule_id>/`
| :permission:`create`
| :param_list:`put`

* :param:`?schedule,string,new schedule as an iso8601 interval`
* :param:`?override_config,object,new overridden configuration for the importer to be used on the scheduled sync`
* :param:`?failure_threshold,number,new consecutive failures allowed before this scheduled sync is disabled`
* :param:`?enabled,boolean,whether the scheduled sync is enabled`

| :response_list:`_`

* :response_code:`200,if the schedule was successfully updated`
* :response_code:`400,if one or more of the parameters are invalid`
* :response_code:`404,if there is no repository, distributor or schedule with the specified IDs`

| :return:`schedule report representing the current state of the scheduled call (see sample response of Scheduling a Publish for details)`


Deleting a Scheduled Publish
----------------------------
Delete a scheduled publish to remove it permanently from the distributor.

| :method:`delete`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/schedules/publish/<schedule_id>/`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200,if the schedule was deleted successfully`
* :response_code:`404,if there is no repository, distributor or schedule with the specified IDs`

| :return:`null`


Listing All Scheduled Publishes
-------------------------------
All of the scheduled publishes for a given distributor may be listed.

| :method:`get`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/schedules/publish/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200,if repo, distributor exist`
* :response_code:`404,if there is no repository or distributor with the specified IDs`

| :return:`array of schedule reports for all scheduled publishes defined (see sample response of Scheduling a Publish for details)`

:sample_response:`200` ::
 
    {
        "_href": "/pulp/api/v2/repositories/test/distributors/yum_distributor/schedules/publish/54d88df045ef4876fb50c994/",
        "_id": "54d88df045ef4876fb50c994",
        "args": [
            "test",
            "yum_distributor"
        ],
        "consecutive_failures": 0,
        "enabled": true,
        "failure_threshold": null,
        "first_run": "2015-02-09T10:37:36Z",
        "kwargs": {
            "overrides": {}
        },
        "last_run_at": "2015-02-09T10:38:23Z",
        "last_updated": 1423478256.805917,
        "next_run": "2015-02-10T10:37:36Z",
        "remaining_runs": null,
        "resource": "pulp:distributor:test:yum_distributor",
        "schedule": "P1DT",
        "task": "pulp.server.tasks.repository.publish",
        "total_run_count": 1
    }
]



Listing a Single Scheduled Publish
----------------------------------
Each scheduled publish may be inspected.

| :method:`get`
| :permission:`read`
| :path:`/v2/repositories/<repo_id>/distributors/<distributor_id>/schedules/publish/<schedule_id>/`

| :response_list:`_`

* :response_code:`200,if repo, distributor or schedule exist`
* :response_code:`404,if there is no repository, distributor or schedule with the specified IDs`

| :return:`a schedule report for the scheduled publish (see sample response of Scheduling a Publish for details)`

:sample_response:`200` ::

 {
    "_href": "/pulp/api/v2/repositories/test/distributors/yum_distributor/schedules/publish/54d88df045ef4876fb50c994/",
    "_id": "54d88df045ef4876fb50c994",
    "args": [
        "test",
        "yum_distributor"
    ],
    "consecutive_failures": 0,
    "enabled": true,
    "failure_threshold": null,
    "first_run": "2015-02-09T10:37:36Z",
    "kwargs": {
        "overrides": {}
    },
    "last_run_at": "2015-02-09T10:38:23Z",
    "last_updated": 1423478256.805917,
    "next_run": "2015-02-10T10:37:36Z",
    "remaining_runs": null,
    "resource": "pulp:distributor:test:yum_distributor",
    "schedule": "P1DT",
    "task": "pulp.server.tasks.repository.publish",
    "total_run_count": 1
 }



Retrieving Publish History
--------------------------
Retrieve publish history for a repository. Each publish performed on a repository creates a history entry.

| :method:`get`
| :permission:`read`
| :path:`/v2/repositories/<repo_id>/history/publish/<distributor_id>/`

| :param_list:`get`

* :param:`?limit,integer,the maximum number of history entries to return; if not specified, the entire
  history is returned`
* :param:`?sort,string,options are 'ascending' and 'descending'; the array is sorted by the publish timestamp`
* :param:`?start_date,iso8601 datetime,any entries with a timestamp prior to the given date are not returned`
* :param:`?end_date,iso8601 datetime,any entries with a timestamp after the given date are not returned`

| :response_list:`_`

* :response_code:`200,if the history was successfully retrieved`
* :response_code:`404,if the repository id given does not exist`

| :return:`an array of publish history entries`

:sample_response:`200` ::

 [
  {
   "result": "success",
   "distributor_id": "my_demo_distributor",
   "distributor_type_id": "demo_distributor",
   "exception": null,
   "repo_id": "demo_repo",
   "traceback": null,
   "started": "1970:00:00T00:00:00Z",
   "completed": "1970:00:00T00:00:01Z",
   "error_message": null,
  }
 ]

