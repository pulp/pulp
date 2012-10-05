Content Management
==================

Install Content on a Consumer
-----------------------------

Install one or more content units on a consumer.  This operation is asynchronous
and idempotent.  If a unit is already installed, no action is taken.  Dependencies
are automatically installed or updated as needed and reflected in the installation report.

The units to be installed are specified in a list.  Each unit in the list of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be installed.  Both the structure and
content are handler specific.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.


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
     {"unit_key": {"name": "zsh"}, "type_id": "rpm"}
   ],
   "options": {
     "apply": true, "reboot": false
   }
 }

:sample_response:`202` ::

 {
 }



Update Content on a Consumer
----------------------------

Update one or more content units on a consumer.  This operation is asynchronous
and idempotent.  If a unit is already up to date, no action is taken.  Dependencies
are automatically installed or updated as needed and reflected in the installation report.

The units to be updated are specified in a list.  Each unit in the list of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be updated.  Both the structure and
content are handler specific.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.

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
     "apply": true, "reboot": false
   }
 }
 
:sample_response:`202` ::

 {
 }
 

Uninstall Content on a Consumer
-------------------------------

Uninstall one or more content units on a consumer.  This operation is asynchronous
and idempotent.  If a unit is not installed, no action is taken.

The units to be uninstalled are specified in a list.  Each unit in the list of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be uninstalled.  The value is completely
defined by the handler mapped to the unit's type_id.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.

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
 }
