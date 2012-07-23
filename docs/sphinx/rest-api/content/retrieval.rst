Retrieval
=========

Search for Units
----------------

Please see :ref:`search_api` for more details on how to perform these searches.

Returns information on content units in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no content units. This is even the
case when the content type specified in the URL does not exist.

| :method:`post`
| :path:`/v2/content/units/<content_type>/search/`
| :permission:`read`
| :param_list:`post` include the key "criteria" whose value is a mapping structure as defined in :ref:`search_criteria`
| :response_list:`_`

* :response_code:`200,containing the list of content units`

| :return:`the same format as retrieving a single content unit, except the base of the return value is a list of them`

:sample_response:`200` ::

    [
      {
        "key-2a": "A",
        "_ns": "units_type-2",
        "_id": "046ca98d-5977-400d-b4de-a5bb57c8b7e2",
        "key-2b": "A",
        "_content_type_id": "type-2"
      },
      {
        "key-2a": "B",
        "_ns": "units_type-2",
        "_id": "2cc5b44a-c5d7-4751-9505-c54ad4f43497",
        "key-2b": "C",
        "_content_type_id": "type-2"
      }
    ]

Returns information on content units in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no content units. This is even the
case when the content type specified in the URL does not exist.

This method is slightly more limiting than the POST alternative, because some
filter expressions may not be serializable as query parameters.

| :method:`get`
| :path:`/v2/content/units/<content_type>/search/`
| :permission:`read`
| :param_list:`get` query params should match the attributes of a Criteria
 object as defined in :ref:`search_criteria`.
 For example: /v2/content/units/deb/search/?field=id&field=display_name&limit=20'
| :response_list:`_`

* :response_code:`200,containing the list of content units`

| :return:`the same format as retrieving a single content unit, except the base of the return value is a list of them`

:sample_response:`200` ::

    [
      {
        "key-2a": "A",
        "_ns": "units_type-2",
        "_id": "046ca98d-5977-400d-b4de-a5bb57c8b7e2",
        "key-2b": "A",
        "_content_type_id": "type-2"
      },
      {
        "key-2a": "B",
        "_ns": "units_type-2",
        "_id": "2cc5b44a-c5d7-4751-9505-c54ad4f43497",
        "key-2b": "C",
        "_content_type_id": "type-2"
      }
    ]
