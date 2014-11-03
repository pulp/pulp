Unit Profiles
=============

Create A Profile
----------------

Create a :term:`unit profile` and associate it with the specified :term:`consumer`.
Unit profiles are associated to consumers by content type.  Each consumer may
be associated with one profile of a given content type at a time.  If a
profile of the specified content type is already associated with the consumer,
it is replaced with the profile supplied in this call.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/profiles/`
| :permission:`create`
| :param_list:`post`

* :param:`content_type,string,the content type ID`
* :param:`profile,object,the content profile`

| :response_list:`_`

* :response_code:`201,if the profile was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`The created unit profile object`

:sample_request:`_` ::

 {
   "content_type": "rpm",
   "profile": [{"arch": "i686",
                "epoch": 0,
                "name": "glib2",
                "release": "2.fc17",
                "vendor": "Fedora Project",
                "version": "2.32.4"},
               {"arch": "x86_64",
                "epoch": 0,
                "name": "rpm-libs",
                "release": "8.fc17",
                "vendor": "Fedora Project",
                "version": "4.9.1.3"}]
 }

:sample_response:`201` ::

 {
   "profile": [{"arch": "i686",
                "epoch": 0,
                "name": "glib2",
                "release": "2.fc17",
                "vendor": "Fedora Project",
                "version": "2.32.4"},
               {"arch": "x86_64",
                "epoch": 0,
                "name": "rpm-libs",
                "release": "8.fc17",
                "vendor": "Fedora Project",
                "version": "4.9.1.3"}],
   "_ns": "consumer_unit_profiles",
   "consumer_id": "test-consumer",
   "content_type": "rpm",
   "_href": "/pulp/api/v2/consumers/test-consumer/profiles/test-consumer/rpm/",
   "profile_hash": "2ecdf09a0f1f6ea43b5a991b468866bc07bcf8c2ac8251395ef2d78adf6e5c5b",
   "_id": {"$oid": "5008500ae138230abe000095"},
   "id": "5008500ae138230abe000095"
 }


Replace a Profile
-----------------

Replace a :term:`unit profile` associated with the specified :term:`consumer`.
Unit profiles are associated to consumers by content type.  Each consumer may
be associated to one profile of a given content type at one time.  If no
unit profile matching the specified content type is currently associated to the
consumer, the supplied profile is created and associated with the consumer
using the specified content type.

| :method:`put`
| :path:`/v2/consumers/<consumer_id>/profiles/<content-type>/`
| :permission:`update`
| :param_list:`put`

* :param:`profile,object,the content profile`

| :response_list:`_`

* :response_code:`201,if the profile was successfully updated`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`The created unit profile object`

:sample_request:`_` ::

 {
   "profile": [{"arch": "i686",
                "epoch": 0,
                "name": "glib2",
                "release": "2.fc17",
                "vendor": "Fedora Project",
                "version": "2.32.4"},
               {"arch": "x86_64",
                "epoch": 0,
                "name": "rpm-libs",
                "release": "8.fc17",
                "vendor": "Fedora Project",
                "version": "4.9.1.3"}]
 }

:sample_response:`201` ::

 {
   "profile": [{"arch": "i686",
                "epoch": 0,
                "name": "glib2",
                "release": "2.fc17",
                "vendor": "Fedora Project",
                "version": "2.32.4"},
               {"arch": "x86_64",
                "epoch": 0,
                "name": "rpm-libs",
                "release": "8.fc17",
                "vendor": "Fedora Project",
                "version": "4.9.1.3"}],
   "_ns": "consumer_unit_profiles",
   "consumer_id": "test-consumer",
   "content_type": "rpm",
   "_href": "/pulp/api/v2/consumers/test-consumer/profiles/test-consumer/rpm/",
   "profile_hash": "2abcf09a0f1f6ea43b5a991b468866bc07bcf8c2ac8251395ef2d78adf6e5c5b",
   "_id": {"$oid": "5008500ae138230abe000095"},
   "id": "5008500ae138230abe000095"
 }


Retrieve All Profiles
---------------------

Retrieves information on all :term:`unit profile`s associated with
a :term:`consumer`.

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/profiles/`
| :permission:`read`
| :param_list:`get` None; There are no supported query parameters
| :response_list:`_`

* :response_code:`200,regardless of whether any profiles exist`
* :response_code:`404,if the consumer does not exist`

| :return:`an array of unit profile objects or an empty array if none exist`

:sample_response:`200` ::

 [
  {"_href": "/pulp/api/v2/consumers/test-consumer/profiles/test-consumer/test-content-type/",
   "_id": {"$oid": "521d92b1e5e7102f7500004a"},
   "_ns": "consumer_unit_profiles",
   "consumer_id": "test-consumer",
   "content_type": "test-content-type",
   "id": "521d92b1e5e7102f7500004a",
   "profile": [{"arch": "i686",
                "epoch": 0,
                "name": "glib2",
                "release": "2.fc17",
                "vendor": "Fedora Project",
                "version": "2.32.4"},
               {"arch": "x86_64",
                "epoch": 0,
                "name": "rpm-libs",
                "release": "8.fc17",
                "vendor": "Fedora Project",
                "version": "4.9.1.3"}],
   "profile_hash": "15df1c6105edacd6b167d2e9dd87311b069f50cebb2f7968ef185c1d6eae5197"
  },
  {"_href": "/pulp/api/v2/consumers/test-consumer/profiles/test-consumer/rpm/",
   "_id": {"$oid": "5217d77de5e710796700000c"},
   "_ns": "consumer_unit_profiles",
   "consumer_id": "test-consumer",
   "content_type": "rpm",
   "id": "5217d77de5e710796700000c",
   "profile": [{"arch": "i686",
                "epoch": 0,
                "name": "glib2",
                "release": "2.fc17",
                "vendor": "Fedora Project",
                "version": "2.32.4"}],
   "profile_hash": "15df1c6105edacd6b167d2e9dd87311b069f50cebb2f7968ef185c1d6eae5197"
  }
 ]


Retrieve a Profile By Content Type
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

| :return:`the requested unit profile object`

:sample_response:`200` ::

 {
   "_href": "/pulp/api/v2/consumers/test-consumer/profiles/test-consumer/test-content-type/",
   "_id": {"$oid": "521d92b1e5e7102f7500004a"},
   "_ns": "consumer_unit_profiles",
   "consumer_id": "test-consumer",
   "content_type": "test-content-type",
   "id": "521d92b1e5e7102f7500004a",
   "profile": [{"arch": "i686",
                "epoch": 0,
                "name": "glib2",
                "release": "2.fc17",
                "vendor": "Fedora Project",
                "version": "2.32.4"},
               {"arch": "x86_64",
                "epoch": 0,
                "name": "rpm-libs",
                "release": "8.fc17",
                "vendor": "Fedora Project",
                "version": "4.9.1.3"}],
   "profile_hash": "15df1c6105edacd6b167d2e9dd87311b069f50cebb2f7968ef185c1d6eae5197"
 }
