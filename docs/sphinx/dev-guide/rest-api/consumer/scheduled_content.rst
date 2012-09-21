Scheduled Content Management
============================

Pulp has the ability to schedule content unit installs, updates, and uninstalls
on a given consumer. The schedules can be created, manipulated, and queried with
with the following APIs.

Note that all schedule resources are in the format described in
:ref:`scheduled_tasks`.

Scheduling Content Install
--------------------------

**Listing Schedules**

| :method:`GET`
| :path:`/v2/consumers/<consumer id>/schedules/install/`
| :permission:`READ`
| :response_list:`_`

* :response_code:`200, if the consumer exists`
* :response_code:`404, if the consumer does not exist`

| :return:`(possibly empty) list of schedule resources`

:sample_response:`` ::

[
 {'_id': '505cc1216157770636000001',
  '_href': '/pulp/api/v2/consumers/<consumer id>/schedules/install/505cc1216157770636000001/',
  'schedule': 'P1DT',
  'failure_threshold': null,
  'enabled': true,
  'consecutive_failures': 0,
  'remaining_runs': null,
  'first_run': '2012-09-19T00:00:00Z',
  'last_run': '2012-09-20T00:00:00Z',
  'next_run': '2012-09-21T00:00:00Z',
  'options': {},
  'units': [{'type_id': 'rpm',
             'unit_keys': {'name': 'zsh'}},
            {'type_id': 'rpm',
             'unit_keys': {'name': 'bash'}},]
 },
]


**Creating a Schedule**

| :method:`POST`
| :path:`/v2/consumers/<consumer id>/schedules/install/`
| :permission:`CREATE`
| :param_list:`POST`

* :param:`schedule,string,schedule in iso8601 interval format`
* :param:`?failure_threshold,integer,number of consecutive failures allowed before automatically disabling`
* :param:`?enabled,boolean,whether or not the schedule is enabled`
* :param:`?options,object,key - value options to pass to the install agent`
* :param:`units,array,list of units to install`

| :response_list:`_`

* :response_code:`201,if the schedule was successfully created`
* :response_code:`400,if any of the required params are missing or any params are invalid`
* :response_code:`404,if the consumer does not exist`
* :response_code:`409,if another server-side operation is permanently preventing the schedule from being created`
* :response_code:`503,if another server-side operation is temporarily preventing the schedule from being created`

| :return:`resource representation of the new schedule`

:sample_request:`_` ::

 {'schedule': 'R1/P1DT',
  'units': [{'type_id': 'rpm', 'unit_keys': {'name': 'gofer'}}]
 }

:sample_response:`` ::

 {'_id': '505ccb526157770636000002',
  '_href': '/pulp/api/v2/consumers/<consumer id>/schedules/install/505ccb526157770636000002/',
  'schedule': 'R1/P1DT',
  'failure_threshold': null,
  'enabled': true,
  'consecutive_failures': 0,
  'remaining_runs': 1,
  'first_run': '2012-09-22T14:15:00Z',
  'last_run': null,
  'next_run': '2012-09-22T14:15:00Z',
  'options': {},
  'units': [{'type_id': 'rpm', 'unit_keys': {'name': 'gofer'}}],
 }


**Inspecting a Schedule**

| :method:`GET`
| :path:`/v2/consumers/<consumer id>/schedules/install/<schedule id>/`
| :permission:`READ`
| :response_list:`_`

* :response_code:`200,if both the consumer and the scheduled install exist`
* :response_code:`404,if either the consumer or scheduled install does not exist`

| :return:`schedule resource representation`

:sample_response:`` ::

 {'_id': '505ccb526157770636000002',
  '_href': '/pulp/api/v2/consumers/<consumer id>/schedules/install/505ccb526157770636000002/',
  'schedule': 'R1/P1DT',
  'failure_threshold': null,
  'enabled': true,
  'consecutive_failures': 0,
  'remaining_runs': 1,
  'first_run': '2012-09-22T14:15:00Z',
  'last_run': null,
  'next_run': '2012-09-22T14:15:00Z',
  'options': {},
  'units': [{'type_id': 'rpm', 'unit_keys': {'name': 'gofer'}}],
 }



**Updating a Schedule**

| :method:`PUT`
| :path:`/v2/consumers/<consumer id>/schedules/install/<schedule id>/`
| :permission:`UPDATE`
| :param_list:`PUT`

* :param:`?schedule,string,schedule as an iso8601 interval`
* :param:`?failure_threshold,integer,number of allowed consecutive failures before the schedule is disabled`
* :param:`?remaining_runs,integer,number of remaining runs for schedule`
* :param:`?enabled,boolean,whether or not the schedule is enabled`
* :param:`?options,object,key - value options to pass to the install agent`
* :param:`?units,array,list of units to install`

| :response_list:`_`


* :response_code:`200,if the schedule was successfully updated`
* :response_code:`202,if another server-side operation is temporarily preventing the schedule from being updated`
* :response_code:`400,if any of the params are invalid`
* :response_code:`404,if the consumer or schedule does not exist`
* :response_code:`409,if another server-side operation is permanently preventing the schedule from being updated`
* :response_code:``

| :return:`resource representation of the schedule`

:sample_request:`_` ::

 {'schedule': 'P1WT',
  'units': [{'type_id': 'rpm', 'unit_keys': {'name': 'grinder'}},
            {'type_id': 'rpm', 'unit_keys': {'name': 'gofer'}}]
 }

:sample_response:`` ::

 {'_id': '505ccb526157770636000002',
  '_href': '/pulp/api/v2/consumers/<consumer id>/schedules/install/505ccb526157770636000002/',
  'schedule': 'P1WT',
  'failure_threshold': null,
  'enabled': true,
  'consecutive_failures': 0,
  'remaining_runs': null,
  'first_run': '2012-09-22T14:15:00Z',
  'last_run': null,
  'next_run': '2012-09-29T14:15:00Z',
  'options': {},
  'units': [{'type_id': 'rpm', 'unit_keys': {'name': 'gofer'}},
            {'type_id': 'rpm', 'unit_keys': {'name': 'grinder'}}],
 }



**Deleting a Schedule**

| :method:`DELETE`
| :path:`/v2/consumers/<consumer id>/schedules/install/<schedule id>/`
| :permission:`DELETE`
| :response_list:`_`

* :response_code:`200,if the schedule was deleted successfully`
* :response_code:`202,if another server-side operation is temporarily preventing the schedule from being deleted`
* :response_code:`404,if the consumer or schedule does not exist`

| :return:`null`


