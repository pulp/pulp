Searching
=========

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
  "criteria": {
    "filters": {"id": {"$in": ["fee", "fie", "foe", "foo"]}, "group": {"$regex": ".*-dev"}},
    "sort": [["id", "ascending"], ["timestamp", "descending"]],
    "limit": 100,
    "skip": 0,
    "fields": ["id", "group", "description", "timestamp"]}
 }

.. _unit_association_criteria:

Unit Association Criteria
-------------------------

The criteria when dealing with units in a repository is slightly different
from the standard model. The metadata about the unit itself is split apart from
the metadata about when and how it was associated to the repository. This split
occurs in the filters, sort, and fields sections.

The valid fields that may be used in the association sections are as follows:

* ``created`` - Timestamp in iso8601 format indicating when the unit was *first*
  associated with the repository.
* ``updated`` - Timestamp in iso8601 format indicating when the unit was
  most recently confirmed to be in the repository.
* ``owner_type`` - Indicates where the association between the unit and
  the repository was created. Valid values are ``importer`` and ``user``.
* ``owner_id`` - Indicates specifically who created the association. This will
  be the importer ID if added by an importer or the user login if added by
  a user.

Example unit association criteria::

  {
    'type_ids' : ['rpm'],
    'filters' : {
      'unit' : <mongo spec syntax>,
      'association' : <mongo spec syntax>
    },
    'sort' : {
      'unit' : [ ['name', 'ascending'], ['version', 'descending'] ],
      'association' : [ ['created', 'descending'] ]
    },
    'limit' : 100,
    'skip' : 200,
    'fields' : {
      'unit' : ['name', 'version', 'arch'],
      'association' : ['created']
    },
    'remove_duplicates' : True
  }

.. _search_api:

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
