Repository Binding
==================

.. _bind:

Bind a Consumer to a Repository
-------------------------------

Bind a :term:`consumer` to a :term:`repository's <repository>` :term:`distributor`
for the purpose of consuming published content.  Binding the consumer is performed
in the following steps:

 1. Create the :term:`binding` on server.
 2. Optionally send a request to the consumer to create the binding.

The distributor may support configuration options that it may use for that particular
binding. These options would be used when generating the payload that is sent to consumers
so they may access the repository. See the individual distributor's documentation for
more information on the format.

| :method:`post`
| :path:`/v2/consumers/<consumer_id>/bindings/`
| :permission:`create`
| :param_list:`post`

* :param:`repo_id,string,unique identifier for the repository`
* :param:`distributor_id,string,identifier for the distributor`
* :param:`?options,object,options passed to the handler on the consumer`
* :param:`?notify_agent,bool,indicates if the consumer should be sent a message about the new binding; defaults to true if unspecified`
* :param:`?binding_config,object,options to be used by the distributor for this binding`

| :response_list:`_`

* :response_code:`200,if the bind request was fully processed on the server`
* :response_code:`202,if an additional task was created to update consumer agents`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer does not exist`

| :return:`A` :ref:`call_report` if any tasks were spawned.  In the event of a 200 response the body will be be the binding that was created.

:sample_request:`_` ::

 {
   "repo_id": "test-repo",
   "distributor_id": "dist-1"
 }

**Tags:**
Each task created to add the binding to a :term:`consumer`
will be created with the following tags: ``"pulp:repository:<repo_id>",
"pulp:consumer:<consumer_id>"
"pulp:repository_distributor:<distributor-id>"
"pulp:action:bind"``

.. _unbind:

Unbind a Consumer
-----------------

Remove a binding between a :term:`consumer` and a :term:`repository's <repository>` :term:`distributor`.

Unbinding the consumer is performed in the following steps:

 1. Mark the :term:`binding` as deleted on the server.
 2. Send a request to the consumer to remove the binding.
 3. Once the consumer has confirmed that the binding has been removed, it is permanently
    deleted on the server.

The steps for a forced unbind are as follows:

 1. The :term:`binding` is deleted on the server. This happens synchronously with the call.
 2. Send a request to the consumer to remove the binding.  The ID of the request to the consumer
    is returned via the spawned_tasks field of the :ref:`call_report`.

If the notify_agent parameter was set to false when the binding was created, no request is sent
to the consumer to remove the binding, so the binding is immediately deleted.

| :method:`delete`
| :path:`/v2/consumers/<consumer_id>/bindings/<repo_id>/<distributor_id>`
| :permission:`delete`
| :param_list:`delete` The consumer ID, repository ID and distributor ID are included
  in the URL itself.

* :param:`?force,bool,delete the binding immediately and discontinue tracking consumer actions`
* :param:`?options,object,options passed to the handler on the consumer`

| :response_list:`_`

* :response_code:`200,if notify_agent was set to false for the binding and it was immediately deleted`
* :response_code:`202,the unbind request was accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer, repo, or distributor IDs don't exist, or if the binding does not exist`

| :return:`A` :ref:`call_report` if any tasks were spawned.

**Tags:**
Each task created to delete the binding from a :term:`consumer`
will be created with the following tags: ``"pulp:repository:<repo_id>",
"pulp:consumer:<consumer_id>"
"pulp:repository_distributor:<distributor-id>"
"pulp:action:unbind"``

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
* :response_code:`404,if the given IDs don't exist, or if no bind exists with the given IDs`

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

| :return:`an array of database representations of the matching binds`

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

* :response_code:`200,if both the consumer and repository IDs are valid`
* :response_code:`404,if one or both of the given ids are not valid`

| :return:`an array of objects, where each object represents a binding`

:sample_response:`200` ::

 [
  {
    "notify_agent": true,
    "repo_id": "test_repo",
    "_href": "/pulp/api/v2/consumers/test_consumer/bindings/test_repo/test_distributor/",
    "type_id": "test_distributor",
    "consumer_actions": [
      {
        "status": "pending",
        "action": "bind",
        "id": "3a8713bb-6902-4f11-a725-17c7f1f6586a",
        "timestamp": 1402688658.785708
      }
    ],
    "_ns": "consumer_bindings",
    "distributor_id": "test_distributor",
    "consumer_id": "test_consumer",
    "deleted": false,
    "binding_config": {},
    "details": {
      "server_name": "pulp.example.com",
      "ca_cert": null,
      "relative_path": "/pulp/repos/test_repo",
      "gpg_keys": [],
      "client_cert": null,
      "protocols": [
        "https"
      ],
      "repo_name": "test_repo"
    },
    "_id": {
      "$oid": "539b54927bc8f6388640871d"
    },
    "id": "539b54927bc8f6388640871d"
  }
 ]

