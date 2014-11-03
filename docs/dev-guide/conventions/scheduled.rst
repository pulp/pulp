.. _scheduled_tasks:

Scheduled Tasks
===============

Pulp can schedule a number of tasks to be performed at a later time, on a
recurring interval, or both.

Pulp utilizes the ISO8601 interval format for specifying these schedules. It
supports recurrences, start times, and durations for any scheduled task. The
recurrence and start time is optional on any schedule. When the recurrence is
omitted, it is assumed to recur indefinitely. When the start time is omitted,
the start time is assumed to be now.

More information on ISO8601 interval formats can be found here:
http://en.wikipedia.org/wiki/ISO_8601#Time_intervals

Scheduled tasks are generally treated as sub-collections and corresponding
resources in Pulp's REST API. All scheduled tasks will have the following fields:

 * ``_id`` The schedule id
 * ``_href`` The uri path of the schedule resource
 * ``schedule`` The schedule as specified as an ISO8601 interval
 * ``failure_threshold`` The number of consecutive failures to allow before the scheduled task is automatically disabled
 * ``enabled`` Whether or not the scheduled task is enabled
 * ``consecutive_failures`` The number of consecutive failures the scheduled tasks has experienced
 * ``remaining_runs`` The number of runs remaining
 * ``first_run`` The date and time of the first run as an ISO8601 datetime
 * ``last_run_at`` The date and time of the last run as an ISO8601 datetime (changed in 2.4 from ``last_run``)
 * ``next_run`` The date and time of the next run as an ISO8601 datetime
 * ``task`` The name (also the python path) of the task that will be executed

Scheduled tasks may have additional fields that are specific to that particular
task.

Sample scheduled task resource ::

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
    "resource": "pulp:consumer:me",
    "remaining_runs": null,
    "consecutive_failures": 0,
    "options": {},
    "_href": "/pulp/api/v2/consumers/me/schedules/content/update/52e7d8b3dd01fb0c8428b8c2/"
  }

