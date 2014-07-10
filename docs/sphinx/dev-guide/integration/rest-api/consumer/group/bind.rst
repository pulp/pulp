Repository Binding
==================

.. _group_bind:

Bind a Consumer Group to a Repository
-------------------------------------

Bind a :term:`consumer` group to a :term:`repository's <repository>` :term:`distributor`
for the purpose of consuming published content.  Binding each consumer in the group is performed
through the following steps:

 1. Create each :term:`binding` on server.
 2. Send a request to each consumer to create the binding.
    A separate task is created for each unique combination of :term:`consumer`,
    :term:`repository`, and :term:`distributor`.

The distributor may support configuration options that it may use for that particular
binding. These options are used when generating the payload that is sent to consumers
so they may access the repository. See the individual distributor's documentation for
more information on the format.

| :method:`post`
| :path:`/v2/consumer_groups/<group_id>/bindings/`
| :permission:`create`
| :param_list:`post`

* :param:`repo_id,string,unique identifier for the repository`
* :param:`distributor_id,string,identifier for the distributor`
* :param:`?options,object,options passed to the handler on each consumer`
* :param:`?notify_agent,bool,indicates if the consumer should be sent a message about the new binding; defaults to true if unspecified`
* :param:`?binding_config,object,options to be used by the distributor for this binding`

| :response_list:`_`

* :response_code:`202,if the bind request was accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer group does not exist`

| :return:`A` :ref:`call_report`

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


.. _group_unbind:

Unbind a Consumer Group
-----------------------

Remove a binding between each consumer in a :term:`consumer` group and
a :term:`repository's <repository>` :term:`distributor`.

Unbinding each consumer in the group is performed through the following steps:

 1. Mark each :term:`binding` as deleted on the server.
 2. Send a request to each consumer to remove the binding.
 3. Once each consumer has confirmed that the binding has been removed, it is permanently
    deleted on the server.

The steps for a forced unbind are as follows:

 1. Each :term:`binding` is deleted on the server.
 2. Send a request to each consumer to remove the binding.  The result of each consumer
    request discarded.


In either case step 2 results in a separate task created for each unique combination of :term:`consumer`,
:term:`repository`, and :term:`distributor`.

| :method:`delete`
| :path:`/v2/consumer_groups/<group_id>/bindings/<repo_id>/<distributor_id>`
| :permission:`delete`
| :param_list:`delete` The consumer ID, repository ID and distributor ID are included
  in the URL itself.

* :param:`?force,bool,delete the binding immediately and discontinue tracking consumer actions`
* :param:`?options,object,options passed to the handler on each consumer`

| :response_list:`_`

* :response_code:`202,the unbind request was accepted`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if the consumer group, repository, or distributor does not exist`

| :return:`A` :ref:`call_report`

**Tags:**
Each task created to remove the binding from a :term:`consumer`
will be created with the following tags: ``"pulp:repository:<repo_id>",
"pulp:consumer:<consumer_id>"
"pulp:repository_distributor:<distributor-id>"
"pulp:action:unbind"``

