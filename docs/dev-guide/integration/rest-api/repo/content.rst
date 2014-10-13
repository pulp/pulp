Content Retrieval
=================

Advanced Unit Search
--------------------

A :ref:`unit_association_criteria` can be used to search for units within a
repository.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/search/units/`
| :permission:`read`
| :param_list:`post`

* :param:`criteria,object,a UnitAssociationCriteria`

| :response_list:`_`

    * :response_code:`200, if the search executed`
    * :response_code:`400, if the criteria is missing or not valid`
    * :response_code:`404, if the repository is not found`

| :return:`array of objects representing content unit associations`

:sample_request:`_` ::

 {
   "criteria": {
     "fields": {
       "unit": [
         "name",
         "version"
       ]
     },
     "type_ids": [
       "rpm"
     ],
     "limit": 1
   }
 }

:sample_response:`200` ::

 [
   {
     "updated": "2013-09-04T22:12:05Z",
     "repo_id": "zoo",
     "created": "2013-09-04T22:12:05Z",
     "_ns": "repo_content_units",
     "unit_id": "4a928b95-7c4a-4d23-9df7-ac99978f361e",
     "metadata": {
       "_id": "4a928b95-7c4a-4d23-9df7-ac99978f361e",
       "version": "4.1",
       "name": "bear"
     },
     "unit_type_id": "rpm",
     "owner_type": "importer",
     "_id": {
       "$oid": "522777f5e19a002faebebf79"
     },
     "id": "522777f5e19a002faebebf79",
     "owner_id": "yum_importer"
   }
 ]
