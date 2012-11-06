Group Membership
================

Consumers can be associated and unassociated with any existing consumer group
at any time using the following REST API.

Associate a Consumer with a Group
---------------------------------

Associate the consumers specified by the :ref:`search_criteria` with
a consumer group.  Consumers that are already associated with the group are
ignored but included in the returned list of matched consumer IDs.

| :method:`post`
| :path:`/v2/consumer_groups/<consumer_group_id>/actions/associate/`
| :permission:`execute`
| :param_list:`post`

* :param:`criteria,object,criteria used to specify the consumers to associate`

| :response_list:`_`

* :response_code:`200,the consumers were successfully associated`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the group does not exist`

| :return:`a list of matched consumer IDs`

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

:sample_response:`` ::

 ["lab1", "lab2"]



Unassociate a Consumer from a Group
-----------------------------------

Unassociate the consumers specified by the :ref:`search_criteria` from
a consumer group.  Consumers that are not associated with the group are
ignored but included in the returned list of matched consumer IDs.

| :method:`post`
| :path:`/v2/consumer_groups/<consumer_group_id>/actions/unassociate/`
| :permission:`execute`
| :param_list:`post`

* :param:`criteria,object,criteria used to specify the consumers to associate`

| :response_list:`_`

* :response_code:`200,the consumers were successfully unassociated`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the group does not exist`

| :return:`a list of matched consumer IDs`

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

:sample_response:`` ::

 ["lab1", "lab2"]

