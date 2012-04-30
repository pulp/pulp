Content Management
==================

Install Content on a Consumer
-----------------------------

Install one or more content units on a consumer.  This operation is asynchrnous
and idempotent.  If a unit is already installed, no action is taken.  Dependancies
are automatically installed or updated as needed and reflected in the installation report.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/install/`
| :permission:`create`
| :param_list:`post`

* :param:`units,list,list of content units to install`
* :param:`options,string,install options`

| :response_list:`_`

* :response_code:`202,The install request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`the asynchronous task information`

:sample_request:`_` ::

 [
  {
    "type_id":"rpm",
    "unit_key": {"name":"zsh"}
  },
  {
    "type_id":"rpm",
    "unit_key": {"name":"gofer-0.66"}
  },
 ]
 
:sample_response:`202` ::

 {
 }



Update Content on a Consumer
----------------------------

Update one or more content units on a consumer.  This operation is asynchrnous
and idempotent.  If a unit is already up to date, no action is taken.  Dependancies
are automatically installed or updated as needed and reflected in the installation report.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/update/`
| :permission:`create`
| :param_list:`post`

* :param:`units,list,list of content units to update`
* :param:`options,string,update options`

| :response_list:`_`

* :response_code:`202,The update request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`the asynchronous task information`

:sample_request:`_` ::

 [
  {
    "type_id":"rpm",
    "unit_key": {"name":"zsh"}
  },
  {
    "type_id":"rpm",
    "unit_key": {"name":"gofer-0.66"}
  },
 ]
 
:sample_response:`202` ::

 {
 }
 

Uninstall Content on a Consumer
-------------------------------

Uninstall one or more content units on a consumer.  This operation is asynchrnous
and idempotent.  If a unit is not installed, no action is taken.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/uninstall/`
| :permission:`create`
| :param_list:`post`

* :param:`units,list,list of content units to uninstall`
* :param:`options,string,uninstall options`

| :response_list:`_`

* :response_code:`202,The uninstall request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`the asynchronous task information`

:sample_request:`_` ::

 [
  {
    "type_id":"rpm",
    "unit_key": {"name":"zsh"}
  },
  {
    "type_id":"rpm",
    "unit_key": {"name":"gofer-0.66"}
  },
 ]
 
:sample_response:`202` ::

 {
 }
