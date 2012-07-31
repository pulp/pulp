Advanced Search For Repository Groups
-------------------------------------

Please see :ref:`search_api` for more details on how to perform these searches.

Returns information on repository groups in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no repository groups.

| :method:`post`
| :path:`/v2/repo_groups/search/`
| :permission:`read`
| :param_list:`post` include the key "criteria" whose value is a mapping
  structure as defined in :ref:`search_criteria`.
| :response_list:`_`

* :response_code:`200,containing the list of repository groups`

| :return:`the same format as retrieving a single repository group, except the base of the return value is a list of them`

:sample_response:`200` ::

    [
     200,
     [
      {
       "scratchpad": null,
       "display_name": "repo group 1",
       "description": "a great group of repos",
       "_ns": "repo_groups",
       "notes": {},
       "repo_ids": [],
       "_id": {
        "$oid": "500839e4e19a00d53700001b"
       },
       "id": "rg1",
       "_href": "/pulp/api/v2/repo_groups/rg1/"
      },
      {
       "scratchpad": null,
       "display_name": "repo group 2",
       "description": "another great group of repos",
       "_ns": "repo_groups",
       "notes": {},
       "repo_ids": [],
       "_id": {
        "$oid": "500839f8e19a00d537000021"
       },
       "id": "rg2",
       "_href": "/pulp/api/v2/repo_groups/rg2/"
      }
     ]
    ]

Returns information on repository groups in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no repository groups.

This method is slightly more limiting than the POST alternative, because some
filter expressions may not be serializable as query parameters.

| :method:`get`
| :path:`/v2/repo_groups/search/`
| :permission:`read`
| :param_list:`get` query params should match the attributes of a Criteria
 object as defined in :ref:`search_criteria`.
 For example: /v2/repo_groups/search/?field=id&field=display_name&limit=20'
| :response_list:`_`

* :response_code:`200,containing the list of repository groups`

| :return:`the same format as retrieving a single repository group, except the base of the return value is a list of them`

:sample_response:`200` ::

    [
     200,
     [
      {
       "scratchpad": null,
       "display_name": "repo group 1",
       "description": "a great group of repos",
       "_ns": "repo_groups",
       "notes": {},
       "repo_ids": [],
       "_id": {
        "$oid": "500839e4e19a00d53700001b"
       },
       "id": "rg1",
       "_href": "/pulp/api/v2/repo_groups/rg1/"
      },
      {
       "scratchpad": null,
       "display_name": "repo group 2",
       "description": "another great group of repos",
       "_ns": "repo_groups",
       "notes": {},
       "repo_ids": [],
       "_id": {
        "$oid": "500839f8e19a00d537000021"
       },
       "id": "rg2",
       "_href": "/pulp/api/v2/repo_groups/rg2/"
      }
     ]
    ]

