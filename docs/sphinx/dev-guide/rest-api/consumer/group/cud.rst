Create, Delete, and Update
==========================

.. _create_consumer_group:

Create a Consumer Group
-----------------------

Creates a new consumer group. Group IDs must be unique across all consumer
groups defined on the server. A group can be initialized with a list of
consumers by passing their IDs to the create call. Consumers can be added or
removed at anytime using the :doc:`membership calls<consumer_members>`.

| :method:`post`
| :path:`/v2/consumer_groups/`
| :permission:`create`
| :param_list:`post`

* :param:`id,string,unique identifier of the consumer group`
* :param:`?display_name,string,display-friendly name for the consumer group`
* :param:`?description,string,description of the consumer group`
* :param:`?consumer_ids,array,list of consumer ids initially associated with the group`
* :param:`?notes,object,key-value pairs associated with the consumer group`

| :response_list:`_`

* :response_code:`201,consumer group successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409, if a consumer group with the given id already exists`

| :return:`representation of the consumer group resource`

:sample_request:`_` ::

 {
  "id": "test-group",
  "description": "A test group of consumers",
  "consumer_ids": ["first-consumer", "second-consumer"]
 }

:sample_response:`201` ::

 {
  "_id": {"oid": "50407df0cf211b30c37c29f4"},
  "_ns": "consumer_groups",
  "_href": "/v2/consumer_groups/test-group/",
  "id": "test-group",
  "display_name": null,
  "description": "A test group of consumers",
  "consumer_ids": ["first-consumer", "second-consumer"],
  "notes": {}
 }


Update a Consumer Group
-----------------------

All the fields, other than the id, that are available when creating a consumer
group may be updated with this call.

| :method:`put`
| :path:`/v2/consumer_groups/<consumer_group_id>/`
| :permission:`update`
| :param_list:`put`

* :param:`?display_name,string,same as in create call`
* :param:`?description,string,same as in create call`
* :param:`?consumer_ids,array,same as in create call`
* :param:`?notes,object,same as in create call`

| :response_list:`_`

* :response_code:`200,if the update executed immediately and was successful`
* :response_code:`202,if the update was postponed until the group is available to be updated`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the group does not exist`

| :return:`updated representation of the consumer group resource`


Delete a Consumer Group
-----------------------

Deleting a consumer group has no effect on the consumers that are members of the
group, apart from removing them from the group.

| :method:`delete`
| :path:`/v2/consumer_groups/<consumer_group_id>/`
| :permission:`delete`
| :response_list:`_`

* :response_code:`200,if the delete executed immediately and was successful`
* :response_code:`202,if the request was accepted by the server and will execute in the future`
* :response_code:`404,if the specified group does not exist`

| :return:`null or call report representing the current state of the delete task`


