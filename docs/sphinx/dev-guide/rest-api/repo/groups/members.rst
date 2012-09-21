Repository Membership
=====================

.. _add_repo_to_group:

Add Repositories to a Group
---------------------------

One or more repositories can be added to an existing group. The repositories to
be added are specified using a :ref:`search criteria document <search_criteria>`.
This call is idempotent; if a repository is already a member of the group, no
changes are made and no error is raised.

| :method:`post`
| :path:`/v2/repo_groups/<group_id>/actions/associate/`
| :permission:`execute`
| :param_list:`post`

* :param:`criteria,object,a unit association search criteria document`

| :response_list:`_`

* :response_code:`200,if the associate was successfully performed`
* :response_code:`202,if the associate was postponed until the group is available`
* :response_code:`400,if the criteria document is invalid`
* :response_code:`404,if the group cannot be found`

| :return:`list of repository IDs for all repositories in the group`

:sample_request:`_` ::

 {
  "criteria": {
    "filters": {
      "id": {"$in": ["dest-1", "dest-2"]}
    }
  }
 }

:sample_response:`200` ::

 ["dest-2", "dest-1"]

.. _remove_repo_from_group:

Remove Repositories from a Group
--------------------------------

In the same fashion as adding repositories to a group, repositories to remove
are specified through a :ref:`search criteria document <search_criteria>`.
The repositories themselves are unaffected; this call simply removes the
association to the given group.

| :path:`/v2/repo_groups/<group_id>/actions/unassociate/`
| :permission:`execute`
| :param_list:`post`

* :param:`criteria,object,a unit association search criteria document`

| :response_list:`_`

* :response_code:`200,if the removal was successfully performed`
* :response_code:`202,if the removal was postponed until the group is available`
* :response_code:`400,if the criteria document is invalid`
* :response_code:`404,if the group cannot be found`

| :return:`list of repository IDs for all repositories in the group`

:sample_request:`_` ::

 {
  "criteria": {
    "filters": {
      "id": "dest-1"
    }
  }
 }

:sample_response:`200` ::

 ["dest-2", "dest-1"]

