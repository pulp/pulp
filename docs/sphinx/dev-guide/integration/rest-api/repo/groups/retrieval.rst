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

| :return:`list of groups in the same format as retrieving a single group; empty list if there are none`

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

Retrieve a Distributor Associated with a Repository Group
---------------------------------------------------------

Retrieves a specific distributor associated with a repository group.

| :method:`get`
| :path:`/v2/repo_groups/<group_id>/distributors/<distributor_id>/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200,containing the distributor`
* :response_code:`404,if the specified group or distributor ID does not exist`

:sample_response:`200` ::

 {
  "_href": "/pulp/api/v2/repo_groups/demo-group/distributors/demo_group_distributor/",
  "_id": {
    "$oid": "51f2ccb5eefe871d8c2d605c"
  },
  "_ns": "repo_group_distributors",
  "config": {'http': False, u'https': True},
  "distributor_type_id": "demo_group_distributor",
  "id": "unique_id",
  "last_publish": null,
  "repo_group_id": "demo-group",
  "scratchpad": null
 }

Retrieve Distributors Associated with a Repository Group
--------------------------------------------------------

Retrieve all distributors associated with a repository group. If the repository has no
associated distributors, an empty list is returned.

| :method:`get`
| :path:`/v2/repo_groups/<group_id>/distributors/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200,containing the array of distributor objects`
* :response_code:`404,if the specified group does not exist`

:sample_response:`200` ::

 [
  {
    "_href": "/pulp/api/v2/repo_groups/demo-group/distributors/demo_group_distributor/",
    "_id": {
      "$oid": "51f2ccb5eefe871d8c2d605c"
    },
    "_ns": "repo_group_distributors",
    "config": {'http': False, u'https': True},
    "distributor_type_id": "demo_group_distributor",
    "id": "unique_id",
    "last_publish": null,
    "repo_group_id": "demo-group",
    "scratchpad": null
  }
 ]
