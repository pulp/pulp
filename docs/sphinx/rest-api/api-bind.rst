Binding
=======

Bind A Consumer To A Repository
-------------------------------

Bind a :term:`consumer` to a :term:`repository` :term:`distributor` for the purpose
of consuming published content.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/bindings/`
| :permission:`create`
| :param_list:`post`

* :param:`repo_id,string,unique identifier for the repository`
* :param:`distributor_id,string,identifier for the distributor`

| :response_list:`_`

* :response_code:`200,The bind was successfully created`
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
 
 

Unbind A Consumer
-----------------

Remove a binding between a :term:`consumer` and a :term:`repository` :term:`distributor`.

| :method:`delete`
| :path:`/v2/consumers/<consumer_id>/bindings/<repo_id>/<distributor_id>`
| :permission:`delete`
| :param_list:`delete` None

| :response_list:`_`

* :response_code:`200,The bind was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the binding does not exist`

| :return:`database representation of the deleted bind`

 
:sample_response:`200` ::

 {
  "repo_id":"A repository ID",
  "distributor_id":"A repostory distributor ID",
  "consumer_id":"A consumer ID"
 }