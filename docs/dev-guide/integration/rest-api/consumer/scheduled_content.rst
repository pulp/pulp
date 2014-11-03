Scheduled Content Management
============================

Pulp has the ability to schedule content unit installs, updates, and uninstalls
on a given consumer. The schedules can be created, manipulated, and queried with
with the following APIs.

Note that all schedule resources are in the format described in
:ref:`scheduled_tasks`.

For each request, ``<action>`` should be one of ``install``, ``update``, or ``uninstall``.

Listing Schedules
-----------------

| :method:`GET`
| :path:`/v2/consumers/<consumer id>/schedules/content/<action>/`
| :permission:`READ`
| :response_list:`_`

* :response_code:`200, if the consumer exists`
* :response_code:`404, if the consumer does not exist`

| :return:`(possibly empty) array of schedule resources`

:sample_response:`200` ::

 [
  {
    "next_run": "2014-01-28T16:33:26Z",
    "task": "pulp.server.tasks.consumer.update_content",
    "last_updated": 1390926003.828128,
    "first_run": "2014-01-28T10:35:08Z",
    "schedule": "2014-01-28T10:35:08Z/P1D",
    "args": [
      "me"
    ],
    "enabled": true,
    "last_run_at": null,
    "_id": "52e7d8b3dd01fb0c8428b8c2",
    "total_run_count": 0,
    "failure_threshold": null,
    "kwargs": {
      "units": [
        {
          "unit_key": {
            "name": "pulp-server"
          },
          "type_id": "rpm"
        }
      ],
      "options": {}
    },
    "units": [
      {
        "unit_key": {
          "name": "pulp-server"
        },
        "type_id": "rpm"
      }
    ],
    "resource": "pulp:consumer:me",
    "remaining_runs": null,
    "consecutive_failures": 0,
    "options": {},
    "_href": "/pulp/api/v2/consumers/me/schedules/content/update/52e7d8b3dd01fb0c8428b8c2/"
  }
 ]

Creating a Schedule
-------------------

| :method:`POST`
| :path:`/v2/consumers/<consumer id>/schedules/content/<action>/`
| :permission:`CREATE`
| :param_list:`POST`

* :param:`schedule,string,schedule in iso8601 interval format`
* :param:`?failure_threshold,integer,number of consecutive failures allowed before automatically disabling`
* :param:`?enabled,boolean,whether or not the schedule is enabled (enabled by default)`
* :param:`?options,object,key - value options to pass to the install agent`
* :param:`units,array,array of units to install`

| :response_list:`_`

* :response_code:`201,if the schedule was successfully created`
* :response_code:`400,if any of the required params are missing or any params are invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`resource representation of the new schedule`

:sample_request:`_` ::

 {"schedule": "R1/P1DT",
  "units": [{"type_id": "rpm", "unit_keys": {"name": "gofer"}}]
 }

:sample_response:`201` ::

 {
  "next_run": "2012-09-22T14:15:00Z",
  "task": "pulp.server.tasks.consumer.update_content",
  "last_updated": 1390926003.828128,
  "first_run": "2012-09-22T14:15:00Z",
  "schedule": "R1/P1DT",
  "args": [
    "me"
  ],
  "enabled": true,
  "last_run_at": null,
  "_id": "52e7d8b3dd01fb0c8428b8c2",
  "total_run_count": 0,
  "failure_threshold": null,
  "kwargs": {
    "units": [
      {
        "unit_key": {
          "name": "gofer"
        },
        "type_id": "rpm"
      }
    ],
    "options": {}
  },
  "units": [
    {
      "unit_key": {
        "name": "gofer"
      },
      "type_id": "rpm"
    }
  ],
  "resource": "pulp:consumer:me",
  "remaining_runs": 1,
  "consecutive_failures": 0,
  "options": {},
  "_href": "/pulp/api/v2/consumers/me/schedules/content/update/52e7d8b3dd01fb0c8428b8c2/"
 }


Retrieving a Schedule
---------------------

| :method:`GET`
| :path:`/v2/consumers/<consumer id>/schedules/content/<action>/<schedule id>/`
| :permission:`READ`
| :response_list:`_`

* :response_code:`200,if both the consumer and the scheduled install exist`
* :response_code:`404,if either the consumer or scheduled install does not exist`

| :return:`schedule resource representation`

:sample_response:`200` ::

 {
    "_href": "/pulp/api/v2/consumers/me/schedules/content/update/52e7d8b3dd01fb0c8428b8c2/",
    "_id": "52e7d8b3dd01fb0c8428b8c2",
    "args": [
        "consumer1"
    ],
    "consecutive_failures": 0,
    "enabled": true,
    "failure_threshold": null,
    "first_run": "2014-01-28T10:35:08Z",
    "kwargs": {
        "options": {},
        "units": [
            {
                "type_id": "rpm",
                "unit_key": {
                    "name": "pulp-server"
                }
            }
        ]
    },
    "last_run_at": null,
    "last_updated": 1390926003.828128,
    "next_run": "2014-01-28T16:50:47Z",
    "options": {},
    "remaining_runs": null,
    "resource": "pulp:consumer:me",
    "schedule": "2014-01-28T10:35:08Z/P1D",
    "task": "pulp.server.tasks.consumer.update_content",
    "total_run_count": 0,
    "units": [
        {
            "type_id": "rpm",
            "unit_key": {
                "name": "pulp-server"
            }
        }
    ]
 }

Updating a Schedule
-------------------

| :method:`PUT`
| :path:`/v2/consumers/<consumer id>/schedules/content/<action>/<schedule id>/`
| :permission:`UPDATE`
| :param_list:`PUT`

* :param:`?schedule,string,schedule as an iso8601 interval (specifying a recurrence will affect remaining_runs)`
* :param:`?failure_threshold,integer,number of allowed consecutive failures before the schedule is disabled`
* :param:`?remaining_runs,integer,number of remaining runs for schedule`
* :param:`?enabled,boolean,whether or not the schedule is enabled`
* :param:`?options,object,key - value options to pass to the install agent`
* :param:`?units,array,array of units to install`

| :response_list:`_`


* :response_code:`200,if the schedule was successfully updated`
* :response_code:`400,if any of the params are invalid`
* :response_code:`404,if the consumer or schedule does not exist`

| :return:`resource representation of the schedule`

:sample_request:`_` ::

 {
  "units": [{"type_id": "rpm", "unit_keys": {"name": "grinder"}},
            {"type_id": "rpm", "unit_keys": {"name": "gofer"}}]
 }

:sample_response:`200` ::

 {
  "next_run": "2014-01-28T16:54:26Z",
  "task": "pulp.server.tasks.consumer.update_content",
  "last_updated": 1390928066.995197,
  "first_run": "2014-01-28T10:35:08Z",
  "schedule": "2014-01-28T10:35:08Z/P1D",
  "args": [
    "me"
  ],
  "enabled": false,
  "last_run_at": null,
  "_id": "52e7d8b3dd01fb0c8428b8c2",
  "total_run_count": 0,
  "failure_threshold": null,
  "kwargs": {
    "units": [
      {
        "unit_key": {
          "name": "grinder"
        },
        "type_id": "rpm"
      },
      {
        "unit_key": {
          "name": "gofer"
        },
        "type_id": "rpm"
      }
    ],
    "options": {}
  },
  "units": [
    {
      "unit_key": {
        "name": "grinder"
      },
      "type_id": "rpm"
    },
    {
      "unit_key": {
        "name": "gofer"
      },
      "type_id": "rpm"
    }
  ],
  "resource": "pulp:consumer:me",
  "remaining_runs": null,
  "consecutive_failures": 0,
  "options": {},
  "_href": "/pulp/api/v2/consumers/me/schedules/content/update/52e7d8b3dd01fb0c8428b8c2/"
 }

Deleting a Schedule
-------------------

| :method:`DELETE`
| :path:`/v2/consumers/<consumer id>/schedules/content/<action>/<schedule id>/`
| :permission:`DELETE`
| :response_list:`_`

* :response_code:`200,if the schedule was deleted successfully`
* :response_code:`404,if the consumer or schedule does not exist`

| :return:`null`
