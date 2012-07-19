Unit Profiles
=============

Create A Profile
----------------

Create a :term:`unit profile` associated with a :term:`consumer`.  Performs
an update if a profile already exists for the specified content type.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/profiles/`
| :permission:`create`
| :param_list:`post`

* :param:`content_type,string,the content type ID`
* :param:`profile,any,the content profile`

| :response_list:`_`

* :response_code:`201,if the bind was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`The created profile object`

:sample_request:`_` ::

 {
   "content_type": "rpm",
   "profile": {"version": "1.0", "name": "zsh"}

 }

:sample_response:`201` ::

 {
   "profile": {"version": "1.0", "name": "zsh"},
   "_ns": "consumer_unit_profiles",
   "consumer_id": "test-consumer",
   "content_type": "rpm",
   "_id": {"$oid": "5008500ae138230abe000095"},
   "id": "5008500ae138230abe000095"
 }


Update A Profile
----------------

Update a :term:`unit profile` associated with a :term:`consumer`.

| :method:`put`
| :path:`/v2/consumers/<consumer_id>/profiles/<content-type>/`
| :permission:`create`
| :param_list:`post`

* :param:`content_type,string,the content type ID`
* :param:`profile,any,the content profile`

| :response_list:`_`

* :response_code:`201,if the bind was successfully updated`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`The created profile object`

:sample_request:`_` ::

 {
   "content_type": "rpm",
   "profile": {"version": "1.0", "name": "zsh"}

 }

:sample_response:`201` ::

 {
   "profile": {"version": "1.0", "name": "zsh"},
   "_ns": "consumer_unit_profiles",
   "consumer_id": "test-consumer",
   "content_type": "rpm",
   "_id": {"$oid": "5008500ae138230abe000095"},
   "id": "5008500ae138230abe000095"
 }


Retrieve All Profiles
---------------------

Retrieves information on all :term:`unit profile` associated with
a :term:`consumer`.

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/profiles/`
| :permission:`read`
| :param_list:`get` None; There are no supported query parameters
| :response_list:`_`

* :response_code:`200,regardless of whether any profiles exist`
* :response_code:`404,if the consumer does not exists`

| :return:`a list of database representations of unit profiles`

:sample_response:`200` ::

 [
   {
     "profile": {"version": "2.0", "arch": "x86_64", "name": "ksh"},
     "_href": "/v2/consumers/test-consumer/profiles/test-consumer/rpm/",
     "content_type": "rpm",
     "_ns": "consumer_unit_profiles",
     "_id": {"$oid": "5008518fe138230b7a000088"},
     "id": "5008518fe138230b7a000088",
     "consumer_id": "test-consumer"
   },
   {
     "profile": {"version": "1.0", "name": "zsh"},
     "_href": "/v2/consumers/test-consumer/profiles/test-consumer/rpm/",
     "content_type": "rpm",
     "_ns": "consumer_unit_profiles",
     "_id": {"$oid": "5008518fe138230b7a000087"},
     "id": "5008518fe138230b7a000087",
     "consumer_id": "test-consumer"
   }
 ]

Retrieve A profile By Content Type
----------------------------------

Retrieves a :term:`unit profile` associated with a :term:`consumer` by
content type.

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/profiles/<content_type>/`
| :permission:`read`
| :param_list:`get` None; There are no supported query parameters
| :response_list:`_`

* :response_code:`200,regardless of whether any profiles exist`
* :response_code:`404,if the consumer or requested profile does not exists`

| :return:`a database representation of the requested unit profile`

:sample_response:`200` ::

 {
   "profile": {"version": "2.0", "arch": "x86_64", "name": "ksh"},
   "_href": "/v2/consumers/test-consumer/profiles/test-consumer/rpm/",
   "content_type": "rpm",
   "_ns": "consumer_unit_profiles",
   "_id": {"$oid": "5008518fe138230b7a000088"},
   "id": "5008518fe138230b7a000088",
   "consumer_id": "test-consumer"
 }
