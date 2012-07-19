Content Unit Applicability
==========================

Determine Unit Applicability
----------------------------

Determine whether the specifed content units are applicable to the
specified :term:`consumer`.  What unit "applicability" means varies based on the
type of content unit.  Please see :ref:`search-api` for more details on how to
specify the consumer selection criteria.

| :method:`post`
| :path:`/v2/consumers/actions/content/applicability/`
| :permission:`read`
| :param_list:`post`

* :param:`criteria,object,a consumer criteria object defined in` :ref:`search_criteria`
* :param:`units,list,a list of content units to check`

| :response_list:`_`

* :response_code:`200,if the applicability check was performed successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`a dictionary keyed by consumer ID containing a list applicability reports`

:sample_request:`_` ::

 {
   "units": [{"unit_key": "security-patch", "type_id": "errata"}],
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
       "unit": {"unit_key": {"name": "security-patch_456"}, "type_id": "errata"},
       "details": "mydetails"
     }
   ]
 }