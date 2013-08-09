Content Applicability
=====================

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
| :path:`/v2/consumers/actions/content/applicability/`
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
  'criteria': {
   'filters': {'id': {'$in': ['sunflower', 'voyager']}},
  },
  'content_types': ['type_1', 'type_2']
 }


:sample_response:`200` ::

 [
    {
        'consumers': ['sunflower'],
        'applicability': {'type_1': ['unit_1_id', 'unit_2_id']}
    },
    {
        'consumers': ['sunflower', 'voyager'],
        'applicability': {'type_1': ['unit_3_id'], 'type_2': ['unit_4_id']}
    }
 ]
