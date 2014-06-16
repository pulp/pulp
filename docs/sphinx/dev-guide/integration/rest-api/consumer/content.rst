Content Management
==================

Install Content on a Consumer
-----------------------------

Install one or more content units on a consumer.  This operation is asynchronous.
If dependencies are automatically installed or updated, it is reflected in the
installation report.

The units to be installed are specified in an array.  Each unit in the  array of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be installed.  Both the structure and
content are handler specific.

The caller must also pass an *options* object, which specifies additional install options.
Both the structure and content are handler specific.  The options drive how the handler
performs the operation.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/install/`
| :permission:`create`
| :param_list:`post`

* :param:`units,array,array of content units to install`
* :param:`options,object,install options`

| :response_list:`_`

* :response_code:`202,The install request has been accepted`
* :response_code:`400,if one or more of the parameters is missing or invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`a` :ref:`call_report`

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh", "version": "4.3.17"}, "type_id": "rpm"}
   ],
   "options": {
     "apply": true, "reboot": false, "importkeys": false
   }
 }


**Tags:**
The task created will have the following tags: ``"pulp:action:unit_install",
"pulp:consumer:<consumer_id>"``

.. _content_update:

Update Content on a Consumer
----------------------------

Update one or more content units on a consumer.  This operation is asynchronous.
If dependencies are automatically installed or updated, it is reflected in the
update report.

The units to be updated are specified in an array.  Each unit in the array of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be updated.  Both the structure and
content are handler specific.

The caller must also pass an *options* object, which specifies additional update options.
Both the structure and content are handler specific.  The options drive how the handler
performs the operation.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/update/`
| :permission:`create`
| :param_list:`post`

* :param:`units,array,array of content units to update`
* :param:`options,object,update options`

| :response_list:`_`

* :response_code:`202,The update request has been accepted`
* :response_code:`400,if one or more of the parameters is missing or invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`a` :ref:`call_report`

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh"}, "type_id": "rpm"}
   ],
   "options": {
     "apply": true, "reboot": false, "all": false, "importkeys": false
   }
 }

**Tags:**
The task created will have the following tags: ``"pulp:action:unit_update",
"pulp:consumer:<consumer_id>"``
 

Uninstall Content on a Consumer
-------------------------------

Uninstall one or more content units on a consumer.  This operation is asynchronous.
If dependencies are automatically removed, it is reflected in the uninstall report.

The units to be uninstalled are specified in an array.  Each unit in the array of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be uninstalled.  The value is completely
defined by the handler mapped to the unit's type_id.

The caller must also pass an *options* object, which specifies additional uninstall options.
Both the structure and content are handler specific.  The options drive how the handler
performs the operation.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/uninstall/`
| :permission:`create`
| :param_list:`post`

* :param:`units,array,array of content units to uninstall`
* :param:`options,object,uninstall options`

| :response_list:`_`

* :response_code:`202,The uninstall request has been accepted`
* :response_code:`400,if one or more of the parameters is missing or invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`a` :ref:`call_report`

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh"}, "type_id": "rpm"}
   ],
   "options": {
     "apply": true, "reboot": false
   }
 }
 
**Tags:**
The task created will have the following tags: ``"pulp:action:unit_uninstall",
"pulp:consumer:<consumer_id>"``

