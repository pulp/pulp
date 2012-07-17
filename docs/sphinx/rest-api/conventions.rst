Conventions
===========

.. _search_criteria:

Search Criteria
---------------

Pulp offers a standard set of criteria for searching through collections as well
as for specifying resources in a collection to act upon.

Any API that supports this criteria will accept a JSON document with a
**criteria** field. The criteria field will be a sub-document with the following
fields:

 * **filters**
 * **sort**
 * **limit**
 * **skip**
 * **fields**

The **filters** field is itself a document that specifies, using the pymongo
find specification syntax, the resource fields and values to match. For more
information on the syntax, see:
http://www.mongodb.org/display/DOCS/Querying

The **sort** field is an array of arrays. Each specifying a field and a
direction.

The **limit** field is a number that gives the maximum amount of resources to
select. Useful for pagination.

The **skip** field is a number that gives the index of the first resource to
select. Useful for pagination.

The **fields** field is an array of resource field names to return in the
results.

Example search criteria::

 {
  "criteria": {"filters": {"id": {"$in": ["fee", "fie", "foe", "foo"]},
                           "group": {"$regex": ".*-dev"}},
               "sort": [["id", "ascending"], ["timestamp", "descending"]],
               "limit": 100,
               "skip": 0,
               "fields": ["id", "group", "description", "timestamp"]}
 }

.. _search-api:

Search API
----------

The search API is consistent for various data types.  Please see the documentation
for each individual resource type for information about extra parameters and behaviors
specific to that type.

Searching can be done via a GET or POST request, and both utilize the concepts
of :ref:`search_criteria`.

The most robust way to do a search is through a POST request, including a JSON-
serialized representation of a Critera in the body under the attribute
name "criteria". This is useful because some filter syntax is difficult
to serialize for use in a URL.

Returns items from the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no items in the database.

| :method:`post`
| :path:`/v2/<resource type>/search/`
| :permission:`read`
| :param_list:`post` include the key "criteria" whose value is a mapping structure as defined in :ref:`search_criteria`
| :response_list:`_`

* :response_code:`200,containing the list of items`

| :return:`the same format as retrieving a single item, except the base of the return value is a list of them`


The GET method is slightly more limiting than the POST alternative because some
filter expressions may be difficult to serialize as query parameters.

| :method:`get`
| :path:`/v2/<resource type>/search/`
| :permission:`read`
| :param_list:`get` query params should match the attributes of a Criteria
 object as defined in :ref:`search_criteria`. The exception is that field names
 should be specified in singular form with as many 'field=foo' pairs as may
 be required.

For example::

  /pulp/api/v2/<resource type>/search/?field=id&field=display_name&limit=20

| :response_list:`_`

* :response_code:`200,containing the list of items`

| :return:`the same format as retrieving a single item, except the base of the return value is a list of them`

.. _exception_handling:

Exception Handling
------------------

In the event of a failure (non-200 status code), the returned body will be a
JSON document describing the error. This applies to all method calls; for
simplicity, the individual method documentation will not repeat this information.
The document will contain the following:

* **http_status** *(number)* - HTTP status code describing the error.
* **href** *(string)* - Currently unused.
* **error_message** *(string)* - Description of what caused the error; may be empty but will
  be included in the document.
* **exception** *(string)* - Message extracted from the exception if one occurred on
  the server; may be empty if the error was due to a data validation instead of an exception.
* **traceback** *(string)* - Traceback of the exception if one occurred; may be empty for the same reasons as exception.

All methods have the potential to raise a 500 response code in the event of an
unexpected server-side error. Again, for simplicity that has not been listed on
a per method basis but applies across all calls.

Example serialized exception::

 {
  "exception": null,
  "traceback": null,
  "_href": "/pulp/api/v2/repositories/missing-repo/",
  "resource_id": "missing-repo",
  "error_message": "Missing resource: missing-repo",
  "http_request_method": "DELETE",
  "http_status": 404
 }


.. _date_and_time:

Date and Time Formats
---------------------

Pulp utilizes the iso8601 date and time formats. All date/time reporting or
setting is done using iso8601 strings.

