Consumer History
================

Retrieve Consumer Event History
-------------------------------

Retrieves the history of events that occurred on a consumer. The list can be
filtered by a number of fields including the event type and event timestamp data.
Pagination support in the form of limits and skips is also provided.

Valid values for the event type filtering are as follows:

* consumer_registered
* consumer_unregistered
* repo_bound
* repo_unbound
* content_unit_installed
* content_unit_uninstalled
* unit_profile_changed
* added_to_group
* removed_from_group

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/history/`
| :permission:`read`
| :param_list:`get`

* :param:`?event_type,str,type of event to retrieve; must be one of the values enumerated above`
* :param:`?limit,str,maximum number of results to retrieve`
* :param:`?sort,str,direction of sort by event timestamp; possible values: 'ascending', 'descending'`
* :param:`?start_date,str,earliest date of events that will be retrieved; format: yyyy-mm-dd`
* :param:`?end_date,str,latest date of events that will be retrieved; format: yyyy-mm-dd`

| :response_list:`_`

* :response_code:`200,for the successful retrieval of consumer history`
* :response_code:`404,if the given consumer is not found`

| :return:`list of event history objects`

:sample_request:`_` ::

 /pulp/api/v2/consumers/test-consumer/history/?sort=descending&limit=2&event_type=consumer_registered

:sample_response:`200` ::

 [
  {
    "originator": "SYSTEM", 
    "timestamp": "2012-05-23T19:06:40Z", 
    "consumer_id": "test-consumer", 
    "details": null, 
    "_ns": "gc_consumer_history", 
    "_id": {
      "$oid": "4fbd3540e5e7102dae000016"
    }, 
    "type": "consumer_registered", 
    "id": "4fbd3540e5e7102dae000016"
  }, 
  {
    "originator": "SYSTEM", 
    "timestamp": "2012-05-23T19:03:29Z", 
    "consumer_id": "test-consumer1", 
    "details": null, 
    "_ns": "gc_consumer_history", 
    "_id": {
      "$oid": "4fbd3481e5e7102dae00000f"
    }, 
    "type": "consumer_registered", 
    "id": "4fbd3481e5e7102dae00000f"
  } 
 ]
