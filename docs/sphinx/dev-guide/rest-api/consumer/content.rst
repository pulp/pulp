Content Management
==================

Install Content on a Consumer
-----------------------------

Install one or more content units on a consumer.  This operation is asynchronous.
If dependencies are automatically installed or updated, it is reflected in the
installation report.

The units to be installed are specified in a list.  Each unit in the list of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be installed.  Both the structure and
content are handler specific.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.  The options drive how the handler performs the operation.


| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/install/`
| :permission:`create`
| :param_list:`post`

* :param:`units,list,list of content units to install`
* :param:`options,object,install options`

| :response_list:`_`

* :response_code:`202,The install request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`the asynchronous task information`

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh", "version": "4.3.17"}, "type_id": "rpm"}
   ],
   "options": {
     "apply": true, "reboot": false, "importkeys": false
   }
 }

:sample_response:`202` ::

 {
   "task_group_id": null, 
   "call_request_id": "4c7d0e50-d8dc-4da6-8996-277d97061086", 
   "exception": null, 
   "_href": "/pulp/api/v2/tasks/4c7d0e50-d8dc-4da6-8996-277d97061086/", 
   "task_id": "4c7d0e50-d8dc-4da6-8996-277d97061086", 
   "call_request_tags": [
     "pulp:consumer:test-consumer", 
     "pulp:action:unit_install"
   ], 
   "reasons": [], 
   "start_time": null, 
   "traceback": null, 
   "schedule_id": null, 
   "finish_time": null, 
   "state": "waiting", 
   "result": null, 
   "dependency_failures": {}, 
   "call_request_group_id": null, 
   "progress": {}, 
   "principal_login": "admin", 
   "response": "accepted", 
   "tags": [
     "pulp:consumer:test-consumer", 
     "pulp:action:unit_install"
   ]
 }



Update Content on a Consumer
----------------------------

Update one or more content units on a consumer.  This operation is asynchronous.
If dependencies are automatically installed or updated, it is reflected in the
update report.

The units to be updated are specified in a list.  Each unit in the list of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be updated.  Both the structure and
content are handler specific.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.  The options drive how the handler performs the operation.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/update/`
| :permission:`create`
| :param_list:`post`

* :param:`units,list,list of content units to update`
* :param:`options,object,update options`

| :response_list:`_`

* :response_code:`202,The update request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`the asynchronous task information`

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh"}, "type_id": "rpm"}
   ],
   "options": {
     "apply": true, "reboot": false, "all": false, "importkeys": false
   }
 }
 
:sample_response:`202` ::

 {
   "task_group_id": null, 
   "call_request_id": "9671c8b6-853d-4a3a-ab5b-0bb719ac1501", 
   "exception": null, 
   "_href": "/pulp/api/v2/tasks/9671c8b6-853d-4a3a-ab5b-0bb719ac1501/", 
   "task_id": "9671c8b6-853d-4a3a-ab5b-0bb719ac1501", 
   "call_request_tags": [
     "pulp:consumer:test-consumer", 
     "pulp:action:unit_update"
   ], 
   "reasons": [], 
   "start_time": null, 
   "traceback": null, 
   "schedule_id": null, 
   "finish_time": null, 
   "state": "waiting", 
   "result": null, 
   "dependency_failures": {}, 
   "call_request_group_id": null, 
   "progress": {}, 
   "principal_login": "admin", 
   "response": "accepted", 
   "tags": [
     "pulp:consumer:test-consumer", 
     "pulp:action:unit_update"
   ]
 }
 

Uninstall Content on a Consumer
-------------------------------

Uninstall one or more content units on a consumer.  This operation is asynchronous.
If dependencies are automatically removed, it is reflected in the uninstall report.

The units to be uninstalled are specified in a list.  Each unit in the list of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be uninstalled.  The value is completely
defined by the handler mapped to the unit's type_id.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.  The options drive how the handler performs the operation.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/uninstall/`
| :permission:`create`
| :param_list:`post`

* :param:`units,list,list of content units to uninstall`
* :param:`options,object,uninstall options`

| :response_list:`_`

* :response_code:`202,The uninstall request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`the asynchronous task information`

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh"}, "type_id": "rpm"}
   ],
   "options": {
     "apply": true, "reboot": false
   }
 }
 
:sample_response:`202` ::

 {
   "task_group_id": null, 
   "call_request_id": "c9195ec7-c101-48ed-a3a5-e8310ee10a5f", 
   "exception": null, 
   "_href": "/pulp/api/v2/tasks/c9195ec7-c101-48ed-a3a5-e8310ee10a5f/", 
   "task_id": "c9195ec7-c101-48ed-a3a5-e8310ee10a5f", 
   "call_request_tags": [
     "pulp:consumer:test-consumer", 
     "pulp:action:unit_uninstall"
   ], 
   "reasons": [], 
   "start_time": null, 
   "traceback": null, 
   "schedule_id": null, 
   "finish_time": null, 
   "state": "waiting", 
   "result": null, 
   "dependency_failures": {}, 
   "call_request_group_id": null, 
   "progress": {}, 
   "principal_login": "admin", 
   "response": "accepted", 
   "tags": [
     "pulp:consumer:test-consumer", 
     "pulp:action:unit_uninstall"
   ]
 }
