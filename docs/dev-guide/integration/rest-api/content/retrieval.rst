Retrieval
=========

Retrieve a Single Unit
----------------------

Returns information about a single content unit.

| :method:`get`
| :path:`/v2/content/units/<content_type>/<unit_id>/`
| :permission:`read`
| :response_list:`_`

* :response_code:`200,if the unit is found`
* :response_code:`404,if there is no unit at the given id`

| :return:`the details of the unit`

:sample_response:`200` ::

    {
      "_id": "046ca98d-5977-400d-b4de-a5bb57c8b7e2",
      "_content_type_id": "type-2",
      "_last_updated": "2013-09-05T17:49:41Z",
      "_storage_path": "/var/lib/pulp/content/type-2/A",
      "key-2a": "A",
      "key-2b": "B",
    }

.. note::
 In the above example, the fields that begin with ``_`` are consistent across content
 types. All other data, such as the example data "key-2a", is contingent on the type
 of unit being retrieved.


Search for Units
----------------

Please see :ref:`search_api` for more details on how to perform these searches.

Returns information on content units in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
array is returned in the case where there are no content units. This is even the
case when the content type specified in the URL does not exist.

| :method:`post`
| :path:`/v2/content/units/<content_type>/search/`
| :permission:`read`
| :param_list:`post`

* :param:`criteria,dict,mapping structure as defined in` :ref:`search_criteria`
* :param:`?include_repos,bool,adds an extra per-unit attribute "repository_memberships" that lists IDs of repositories of which the unit is a member.`

| :response_list:`_`

* :response_code:`200,containing the array of content units`

| :return:`the same format as retrieving a single content unit, except the base of the return value is an array of them`

:sample_response:`200` ::

    [
      {
        "key-2a": "A",
        "_ns": "units_type-2",
        "_id": "046ca98d-5977-400d-b4de-a5bb57c8b7e2",
        "key-2b": "A",
        "_content_type_id": "type-2",
        "repository_memberships": ["repo1", "repo2"]
      },
      {
        "key-2a": "B",
        "_ns": "units_type-2",
        "_id": "2cc5b44a-c5d7-4751-9505-c54ad4f43497",
        "key-2b": "C",
        "_content_type_id": "type-2",
        "repository_memberships": ["repo1"]
      }
    ]

Returns information on content units in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
array is returned in the case where there are no content units. This is even the
case when the content type specified in the URL does not exist.

This method is slightly more limiting than the POST alternative, because some
filter expressions may not be serializable as query parameters.

| :method:`get`
| :path:`/v2/content/units/<content_type>/search/`
| :permission:`read`
| :param_list:`get` query params should match the attributes of a Criteria
 object as defined in :ref:`search_criteria`.
 For example: /v2/content/units/deb/search/?field=id&field=display_name&limit=20'

* :param:`?include_repos,bool,adds an extra per-unit attribute "repository_memberships" that lists IDs of repositories of which the unit is a member.`

| :response_list:`_`

* :response_code:`200,containing the array of content units`

| :return:`the same format as retrieving a single content unit, except the base of the return value is an array of them`

:sample_response:`200` ::

    [
      {
        "key-2a": "A",
        "_ns": "units_type-2",
        "_id": "046ca98d-5977-400d-b4de-a5bb57c8b7e2",
        "key-2b": "A",
        "_content_type_id": "type-2",
        "repository_memberships": ["repo1", "repo2"]
      },
      {
        "key-2a": "B",
        "_ns": "units_type-2",
        "_id": "2cc5b44a-c5d7-4751-9505-c54ad4f43497",
        "key-2b": "C",
        "_content_type_id": "type-2",
        "repository_memberships": ["repo1"]
      }
    ]
