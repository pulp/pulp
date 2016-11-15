Group Membership
================

Consumers can be associated and unassociated with any existing consumer group
at any time using the following REST API.

Associate a Consumer with a Group
---------------------------------

Associate the consumers specified by the :ref:`search_criteria` with
a consumer group. This call is idempotent; if a consumer is already a member 
of the group, no changes are made and no error is raised.

| :method:`post`
| :path:`/v2/consumer_groups/<consumer_group_id>/actions/associate/`
| :permission:`execute`
| :param_list:`post`

* :param:`criteria,object,criteria used to specify the consumers to associate`

| :response_list:`_`

* :response_code:`200,the consumers were successfully associated`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the group does not exist`

| :return:`array of consumer IDs for all consumers in the group`

:sample_request:`_` ::

 {
  "criteria": {
    "filters": {
      "id": {
        "$in": [
          "lab1",
          "lab2"
        ]
      }
    }
  }
 }

:sample_response:`200` ::

 ["lab0", "lab1", "lab2"]



Unassociate a Consumer from a Group
-----------------------------------

Unassociate the consumers specified by the :ref:`search_criteria` from
a consumer group. If a consumer satisfied by the criteria is not a member 
of the group, no changes are made and no error is raised.

| :method:`post`
| :path:`/v2/consumer_groups/<consumer_group_id>/actions/unassociate/`
| :permission:`execute`
| :param_list:`post`

* :param:`criteria,object,criteria used to specify the consumers to associate`

| :response_list:`_`

* :response_code:`200,the consumers were successfully unassociated`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the group does not exist`

| :return:`array of consumer IDs for all consumers in the group`

:sample_request:`_` ::

 {
  "criteria": {
    "filters": {
      "id": {
        "$in": [
          "lab1",
          "lab2"
        ]
      }
    }
  }
 }

:sample_response:`200` ::

 ["lab0"]

