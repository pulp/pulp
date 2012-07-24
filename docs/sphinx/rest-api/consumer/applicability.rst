Content Unit Applicability
==========================

Determine Unit Applicability
----------------------------

Determines whether the specifed content units are applicable to the
specified :term:`consumer`.  What unit *applicability* means varies based on the
type of content unit.  Please see :ref:`search_api` for more details on how to
specify the consumer selection criteria.

Each *unit* is an object specified as follows:

 * **type_id** (string) - the content type ID
 * **unit_key** (<dependant on *type_id* >) - the unit key; uniquely identifies the unit

Each returned *ApplicabilityReport* is an object:

 * **unit** (object) - a content *unit* (see above)
 * **applicable** (bool) - a flag that indicates whether the unit is applicable
 * **summary** (<dependant on plugin>) - a summary of the applicability calculation
 * **details** (<dependant on plugin>) - the details of the applicability calculation

| :method:`post`
| :path:`/v2/consumers/actions/content/applicability/`
| :permission:`read`
| :param_list:`post`

* :param:`criteria,object,a consumer criteria object defined in` :ref:`search_criteria`
* :param:`units,list,a list of content units to check (see unit above)`

| :response_list:`_`

* :response_code:`200,if the applicability check was performed successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`a dictionary keyed by consumer ID containing a list of applicability report (see above)`

:sample_request:`_` ::

 {
   "units": [
     {"unit_key": {"name": "security-patch_123"}, "type_id": "errata"},
   ],
   "criteria": {
     "sort": [["id", "ascending"]],
     "filters": {"id": {"$in": ["test-1", "test-2"]}}}
 }

:sample_response:`200` ::

 {
   "test-1": [
     {
       "summary": "mysummary",
       "applicable": true,
       "unit": {"unit_key": {"name": "security-patch_123"}, "type_id": "errata"},
       "details": "mydetails"
     }
   ],
   "test-2": [
     {
       "summary": "mysummary",
       "applicable": true,
       "unit": {"unit_key": {"name": "security-patch_123"}, "type_id": "errata"},
       "details": "mydetails"
     }
   ]
 }