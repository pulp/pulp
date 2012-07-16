.. _search-api:

Search
======

The search API is consistent for various data types.  Please see the documentation
for each individual data type for information about extra parameters and behaviors
specific to that type.

You can search via a GET or POST request, but in either case you will need to be
familiar with the use of :ref:`search_criteria`.

POST
----
The most robust way to do a search is through a POST request, including a JSON-
serialized representation of a Critera in the body under the attribute
name "criteria". This is useful because some filter syntax is difficult
to serialize for use in a URL.

Returns items from the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no items in the database.

| :method:`post`
| :path:`/v2/<data type>/search/`
| :permission:`read`
| :param_list:`post` include the key "criteria" whose value is a mapping structure as defined in :ref:`search_criteria`
| :response_list:`_`

* :response_code:`200,containing the list of items`

| :return:`the same format as retrieving a single item, except the base of the return value is a list of them`


GET
----

The GET method is slightly more limiting than the POST alternative, because some
filter expressions may be difficult to serialize as query parameters.

| :method:`get`
| :path:`/v2/<data type>/search/`
| :permission:`read`
| :param_list:`get` query params should match the attributes of a Criteria
 object as defined in :ref:`search_criteria`. The exception is that field names
 should be specified in singular form with as many 'field=foo' pairs as may
 be required.

For example: /pulp/api/v2/<data type>/search/?field=id&field=display_name&limit=20'

| :response_list:`_`

* :response_code:`200,containing the list of items`

| :return:`the same format as retrieving a single item, except the base of the return value is a list of them`