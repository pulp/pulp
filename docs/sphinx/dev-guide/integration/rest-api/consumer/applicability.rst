Content Applicability
=====================

Generate Content Applicability for Updated Consumers
----------------------------------------------------

This API regenerates :term:`applicability data` for a given set of consumers
matched by a given :ref:`search_criteria` asynchronously and saves it 
in the Pulp database. It should be used when a consumer profile is updated 
or consumer-repository bindings are updated. Applicability data is regenerated 
for all unit profiles associated with given consumers and for all content types 
that define applicability. Generated applicability data can be queried using 
the `Query Content Applicability` API described below.

The API will return a :ref:`call_report`. Users can check whether the applicability
generation is completed using task id in the :ref:`call_report`. You can run
a single applicability generation task at a time. If an applicability generation 
task is running, any new applicability generation tasks requested are queued 
and postponed until the current task is completed.

| :method:`post`
| :path:`/v2/consumers/actions/content/regenerate_applicability/`
| :permission:`create`
| :param_list:`post`

* :param:`consumer_criteria,object,a consumer criteria object defined in` :ref:`search_criteria`

| :response_list:`_`

* :response_code:`202,if applicability regeneration is queued successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:a :ref:`call_report` representing the current state of the applicability regeneration

:sample_request:`_` ::

 { 
  "consumer_criteria": {
   "filters": {"id": {"$in": ["sunflower", "voyager"]}}
  }
 }

**Tags:**
The task created will have the following tag: ``"pulp:action:content_applicability_regeneration"``

Generate Content Applicability for Updated Repositories
-------------------------------------------------------

This API regenerates :term:`applicability data` for a given set of repositories
matched by a given :ref:`search_criteria` asynchronously and saves it 
in the Pulp database. It should be used when a repository's content is updated. 
Only `existing` applicability data is regenerated for given repositories. 
If applicability data for a consumer-repository combination does not already 
exist, it should be generated using the API `Generate Content Applicability 
for Updated Consumers`.

If any new content types that support applicability are added 
to the given repositories, applicability data is generated for them as well.
Generated applicability data can be queried using 
the `Query Content Applicability` API described below.

The API will return a :ref:`call_report`. Users can check whether the applicability
generation is completed using task id in the :ref:`call_report`. You can run
a single applicability generation task at a time. If an applicability generation 
task is running, any new applicability generation tasks requested are queued 
and postponed until the current task is completed.

| :method:`post`
| :path:`/v2/repositories/actions/content/regenerate_applicability/`
| :permission:`create`
| :param_list:`post`

* :param:`repo_criteria,object,a repository criteria object defined in` :ref:`search_criteria`

| :response_list:`_`

* :response_code:`202,if applicability regeneration is queued successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:a :ref:`call_report` representing the current state of the applicability regeneration

:sample_request:`_` ::

 { 
  "repo_criteria": {
   "filters": {"id": {"$in": ["test-repo", "test-errata"]}}
  }
 }

**Tags:**
The task created will have the following tag: ``"pulp:action:content_applicability_regeneration"``

Generate Content Applicability for a single Consumer
----------------------------------------------------

This API regenerates :term:`applicability data` for the given consumer asynchronously
and saves it in the Pulp database. It can be used by a consumer when its profile is updated
or its consumer-repository bindings are updated. Applicability data is regenerated
for all unit profiles associated with te given consumer and for all content types
that define applicability. Generated applicability data can be queried using
the `Query Content Applicability` API described above.

The API will return a :ref:`call_report`. If an applicability generation
task is running for a given consumer, any new applicability generation tasks requested
are queued and postponed until the current task is completed.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/actions/content/regenerate_applicability/`
| :permission:`create`
| :param_list:`post`

| :response_list:`_`

* :response_code:`202,if applicability regeneration is queued successfully`
* :response_code:`404,if a consumer with given consumer_id does not exist`

| :return:a :ref:`call_report` representing the current state of the applicability regeneration

**Tags:**
The task created will have the following tag: ``"pulp:action:consumer_content_applicability_regeneration"``

Query Content Applicability
---------------------------

This method queries Pulp for the applicability data that applies to a set of
consumers matched by a given :ref:`search_criteria`. The API user may also
optionally specify an array of content types to which they wish to limit the
applicability data.

.. note::
   The criteria is used by this API to select the consumers for which Pulp
   needs to find applicability data. The ``sort`` option can be used in
   conjunction with ``limit`` and ``skip`` for pagination, but the ``sort``
   option will not influence the ordering of the returned applicability reports
   since the consumers are collated together.

The applicability API will return an array of objects in its response. Each
object will contain two keys, ``consumers`` and ``applicability``.
``consumers`` will index an array of consumer ids. These grouped consumer ids
will allow Pulp to collate consumers that have the same applicability together.
``applicability`` will index an object. The applicability object will contain
content types as keys, and each content type will index an array of unit ids.

Each *applicability report* is an object:
 * **consumers** - array of consumer ids
 * **applicability** - object with content types as keys, each indexing an
                       array of applicable unit ids

| :method:`post`
| :path:`/v2/consumers/content/applicability/`
| :permission:`read`
| :param_list:`post`

* :param:`criteria,object,a consumer criteria object defined in` :ref:`search_criteria`
* :param:`content_types,array,an array of content types that the caller wishes to limit the applicability report to` (optional)

| :response_list:`_`

* :response_code:`200,if the applicability query was performed successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`an array of applicability reports`

:sample_request:`_` ::


 { 
  "criteria": {
   "filters": {"id": {"$in": ["sunflower", "voyager"]}}
  },
  "content_types": ["type_1", "type_2"]
 }


:sample_response:`200` ::

 [
    {
        "consumers": ["sunflower"],
        "applicability": {"type_1": ["unit_1_id", "unit_2_id"]}
    },
    {
        "consumers": ["sunflower", "voyager"],
        "applicability": {"type_1": ["unit_3_id"], "type_2": ["unit_4_id"]}
    }
 ]

