.. _scheduled_tasks:

Scheduled Tasks
===============

Pulp can schedule a number of tasks to be performed at a later time, on a
recurring interval, or both.

Pulp utilizes the iso8601 interval format for specifying the these schedules. It
supports recurrences, start times, and durations for any scheduled task. The
recurrence and start time is optional on any schedule. When the recurrence is
omitted, it is assumed to recur indefinitely. When the start time is omitted,
the start time is calculated as now plus the length of one duration.

More information on iso8601 interval formats can be found here:
http://en.wikipedia.org/wiki/ISO_8601#Time_intervals

Scheduled tasks are generally treated as sub-collections and corresponding
resources in Pulp's REST API. All scheduled tasks will have the following fields:

 * `_id` The schedule id
 * `_href` The uri path of the schedule resource
 * `schedule` The schedule as specified as an iso8601 interval
 * `failure_threshold` The number of consecutive failures to allow before the scheduled task is automatically disabled
 * `enabled` Whether or not the scheduled task is enabled
 * `consecutive_failures` The number of consecutive failures the scheduled tasks has experienced
 * `remaining_runs` The number of runs remaining
 * `first_run` The date and time of the first run as an iso8601 datetime
 * `last_run` The date and time of the last run as an iso8601 datetime
 * `next_run` The date and time of the next run as an iso8601 datetime

Scheduled tasks may have additional fields that are specific to that particular
task.

Sample scheduled task resource ::

 {
  '_id': '505cba846157770636000000',
  '_href': '/pulp/api/v2/<collection>/<resource id>/schedules/<type>/505cba846157770636000000/',
  'schedule': 'R5/2012-10-31T02:00:00Z/P1WT',
  'failure_threshold': 3,
  'enabled': true,
  'consecutive_failures': 0,
  'remaining_runs': 5,
  'first_run': '2012-10-31T02:00:00Z',
  'last_run': null,
  'next_run': '2012-10-31T02:00:00Z',
 }

