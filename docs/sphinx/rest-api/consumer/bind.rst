Repository Binding
==================

Bind a Consumer to a Repository
-------------------------------

Bind a :term:`consumer` to a :term:`repository's <repository>` :term:`distributor`
for the purpose of consuming published content.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/bindings/`
| :permission:`create`
| :param_list:`post`

* :param:`repo_id,string,unique identifier for the repository`
* :param:`distributor_id,string,identifier for the distributor`

| :response_list:`_`

* :response_code:`201,if the bind was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer, repository or distributor does not exist`

| :return:`database representation of the created bind`

:sample_request:`_` ::

 {
   "repo_id": "test-repo",
   "distributor_id": "dist-1"
 }
 
:sample_response:`200` ::

 {
   "repo_id": "test-repo",
   "consumer_id": "test-consumer",
   "_ns": "consumer_bindings",
   "_id": {"$oid": "50085f91e138236f9f00000b"},
   "distributor_id": "dist-1",
   "id": "50085f91e138236f9f00000b"
 }


Unbind a Consumer
-----------------

Remove a binding between a :term:`consumer` and a :term:`repository's <repository>` :term:`distributor`.

| :method:`delete`
| :path:`/v2/consumers/<consumer_id>/bindings/<repo_id>/<distributor_id>`
| :permission:`delete`
| :param_list:`delete` The consumer ID, repository ID and distributor ID are included
  in the URL itself.

| :response_list:`_`

* :response_code:`200,the bind was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the binding does not exist`

| :return:`database representation of the deleted bind`

 
:sample_response:`200` ::

 {
   "repo_id": "test-repo",
   "consumer_id": "test-consumer",
   "_ns": "consumer_bindings",
   "_id": {"$oid": "5008604be13823703800003e"},
   "distributor_id": "dist-1",
   "id": "5008604be13823703800003e"
 }


Retrieve a Single Binding
-------------------------

Retrieves information on a single binding between a consumer and a repository.

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/bindings/<repo_id>/<distributor_id>`
| :permission:`read`
| :param_list:`get` None; the consumer ID, repository ID and distributor ID are included
  in the URL itself. There are no supported query parameters.
| :response_list:`_`

* :response_code:`200,if the bind exists`
* :response_code:`404,if no bind exists with the given IDs`

| :return:`database representation of the matching bind`

:sample_response:`200` ::

 {
   "repo_id": "test-repo",
   "consumer_id": "test-consumer",
   "_ns": "consumer_bindings",
   "_id": {"$oid": "5008604be13823703800003e"},
   "distributor_id": "dist-1",
   "id": "5008604be13823703800003e"
 }


Retrieve All Bindings
---------------------

Retrieves information on all bindings for the specified consumer.

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/bindings/`
| :permission:`read`
| :param_list:`get` None; the consumer ID is included in the URL itself.
      There are no supported query parameters.
| :response_list:`_`

* :response_code:`200,if the consumer exists`

| :return:`a list of database representations of the matching binds`

:sample_response:`200` ::

 [
   {
     "repo_id": "test-repo",
     "consumer_id": "test-consumer",
     " _ns": "consumer_bindings",
     "_id": {"$oid": "5008604be13823703800003e"},
     "distributor_id": "dist-1",
     "id": "5008604be13823703800003e"
   },
     "repo_id": "test-repo2",
     "consumer_id": "test-consumer",
     " _ns": "consumer_bindings",
     "_id": {"$oid": "5008604be13823703800003e"},
     "distributor_id": "dist-1",
     "id": "5008604be13823703800003e"
   },
  ]


Retrieve Binding By Consumer And Repository
-------------------------------------------

Retrieves information on all bindings between a consumer and a repository.

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/bindings/<repo_id>/`
| :permission:`read`
| :param_list:`get` None; the consumer and repository IDs are included
      in the URL itself. There are no supported query parameters.
| :response_list:`_`

* :response_code:`200,if the bind exists`
* :response_code:`404,if no bind exists with the given IDs`

| :return:`a database representation of the matching bind`

:sample_response:`200` ::

 {
   "repo_id": "test-repo",
   "consumer_id": "test-consumer",
   "_ns": "consumer_bindings",
   "_id": {"$oid": "5008604be13823703800003e"},
   "distributor_id": "dist-1",
   "id": "5008604be13823703800003e"
 }