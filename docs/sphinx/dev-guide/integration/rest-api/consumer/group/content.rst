Content Management
==================

.. _group_content_install:

Install Content on a Consumer Group
-----------------------------------

Install one or more content units on each consumer in the group.  This operation is asynchronous.

The units to be installed are specified in an array.  Each unit in the array of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be installed.  Both the structure and
content are handler specific.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.  The options drive how the handler performs the operation.


| :method:`post`
| :path:`/v2/consumer_groups/<group_id>/actions/content/install/`
| :permission:`create`
| :param_list:`post`

* :param:`units,array,array of content units to install`
* :param:`options,object,install options`

| :response_list:`_`

* :response_code:`202,the install request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer group does not exist`

| :return:`A` :ref:`call_report` that lists each of the tasks that were spawned.

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh", "version": "4.3.17"}, "type_id": "rpm"},
     {"unit_key": {"id": "ERRATA-123"}, "type_id": "erratum"},
     {"unit_key": {"name": "web-server"}, "type_id": "package_group"}
   ],
   "options": {
     "apply": true, "reboot": false, "importkeys": false
   }
 }

**Tags:**
Each task created to install content on a :term:`consumer`
will be created with the following tags:
``"pulp:consumer:<consumer_id>", "pulp:action:unit_install"``

.. _group_content_update:

Update Content on a Consumer Group
----------------------------------

Update one or more content units on each consumer in the group.  This operation is asynchronous.

The units to be updated are specified in an array.  Each unit in the array of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be updated.  Both the structure and
content are handler specific.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.  The options drive how the handler performs the operation.

| :method:`post`
| :path:`/v2/consumer_groups/<group_id>/actions/content/update/`
| :permission:`create`
| :param_list:`post`

* :param:`units,array,array of content units to update`
* :param:`options,object,update options`

| :response_list:`_`

* :response_code:`202,the update request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer group does not exist`


| :return:`A` :ref:`call_report` that lists each of the tasks that were spawned.

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh", "version": "4.3.17"}, "type_id": "rpm"},
     {"unit_key": {"id": "ERRATA-123"}, "type_id": "erratum"},
     {"unit_key": {"name": "web-server"}, "type_id": "package_group"}
   ],
   "options": {
     "apply": true, "reboot": false, "importkeys": false
   }
 }

**Tags:**
Each task created to update content on a :term:`consumer`
will be created with the following tags:
``"pulp:consumer:<consumer_id>", "pulp:action:unit_update"``

.. _group_content_uninstall:

Uninstall Content on a Consumer Group
-------------------------------------

Uninstall one or more content units on each consumer in the group.  This operation is asynchronous.
If dependencies are automatically removed, it is reflected in the uninstall report.

The units to be uninstalled are specified in an array.  Each unit in the array of *units* is an
object containing two required attributes.  The first is the **type_id** which a string
that defines the unit's content type.  The value is unrestricted by the Pulp server but
must match a type mapped to a content :term:`handler` in the agent.  The second is the
**unit_key** which identifies the unit or units to be uninstalled.  The value is completely
defined by the handler mapped to the unit's type_id.

The caller can pass additional options using an *options* object.  Both the structure and
content are handler specific.  The options drive how the handler performs the operation.

| :method:`post`
| :path:`/v2/consumer_groups/<group_id>/actions/content/uninstall/`
| :permission:`create`
| :param_list:`post`

* :param:`units,array,array of content units to uninstall`
* :param:`options,object,uninstall options`

| :response_list:`_`

* :response_code:`202,The uninstall request has been accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer group does not exist`

| :return:`A` :ref:`call_report` that lists each of the tasks that were spawned.

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "zsh", "version": "4.3.17"}, "type_id": "rpm"},
     {"unit_key": {"id": "ERRATA-123"}, "type_id": "erratum"},
     {"unit_key": {"name": "web-server"}, "type_id": "package_group"}
   ],
   "options": {
     "apply": true, "reboot": false
   }
 }

**Tags:**
Each task created to uninstall content on a :term:`consumer`
will be created with the following tags:
``"pulp:consumer:<consumer_id>", "pulp:action:unit_uninstall"``
