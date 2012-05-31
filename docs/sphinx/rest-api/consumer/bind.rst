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

* :response_code:`200,if the bind was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer, repository or distributor does not exist`

| :return:`database representation of the created bind`

:sample_request:`_` ::

 {
  "repo_id":"A repository ID",
  "distributor_id":"A repostory distributor ID"
 }
 
:sample_response:`200` ::

 {
  "repo_id":"A repository ID",
  "distributor_id":"A repostory distributor ID",
  "consumer_id":"A consumer ID"
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
  "consumer_id" : "demo_consumer",
  "repo_id" : "demo_repository",
  "distributor_id" : "distributor_1",
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

| :return:`database representation of the matching repository`

:sample_response:`200` ::

 {
  "consumer_id" : "demo_consumer",
  "repo_id" : "demo_repository",
  "distributor_id" : "distributor_1",
 }
