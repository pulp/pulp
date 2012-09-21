Retrieval
=========

Retrieve a Single Repository Group
----------------------------------

Retrieves information on a single repository group.

| :method:`get`
| :path:`/v2/repo_groups/<group_id>/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200,if the repository group is found`
* :response_code:`404,if the group cannot be found`

| :return:`database representation of the matching repository group`

:sample_response:`200` ::

 {
  "scratchpad": null,
  "display_name": "Demo Group",
  "description": null,
  "_ns": "repo_groups",
  "notes": {},
  "repo_ids": [
    "dest-2"
  ],
  "_id": {
    "$oid": "500ee4028a905b04e900002e"
  },
  "id": "demo-group",
  "_href": "/pulp/api/v2/repo_groups/demo-group/"
 }

Retrieve All Repository Groups
------------------------------

Retrieves information on all repository groups in the Pulp server. This call
will never return a 404; an empty list is returned in the event there are
no groups defined.

This call supports the search query parameters as described in
:ref:`the search API conventions <search_api>`.

| :method:`get`
| :path:`/v2/repo_groups/`
| :permission:`read`
| :param_list:`get`
| :response_list:`_`

* :response_code:`200,containing the list of repository groups`

| :return:`list of groups in the same format as retrieving a single group; empty list if there are none defined`

:sample_response:`200` ::

 [
  {
    "scratchpad": null,
    "display_name": null,
    "description": null,
    "_ns": "repo_groups",
    "notes": {},
    "repo_ids": [],
    "_id": {
      "$oid": "500ead8a8a905b04e9000019"
    },
    "id": "g1",
    "_href": "/pulp/api/v2/repo_groups/g1/"
  },
  {
    "scratchpad": null,
    "display_name": "Demo Group",
    "description": null,
    "_ns": "repo_groups",
    "notes": {},
    "repo_ids": [
      "dest-2"
    ],
    "_id": {
      "$oid": "500ee4028a905b04e900002e"
    },
    "id": "demo-group",
    "_href": "/pulp/api/v2/repo_groups/demo-group/"
  }
 ]

