Copying Units Between Repositories
==================================

Pulp provides the ability to copy units between repositories. Units to copy
are specified through a :ref:`criteria <search_criteria>` applied to a
source repository, where only the ``filters`` field applies. All matching units
are imported into the destination repository.

The only restriction is that the destination repository must be configured
with an importer that supports the type of units being copied.

| :method:`post`
| :path:`/v2/repositories/<destination_repo_id>/actions/associate/`
| :permission:`update`
| :param_list:`post`

* :param:`source_repo_id,str,repository from which to copy units`
* :param:`?criteria,criteria document,filters which units to copy from the source repository`

| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to execute asynchronously`

| :return:`call report representing the current state of the delete`

:sample_request:`post` ::

  {
    'source_repo_id' : 'pulp-f17',
    'criteria': {
      'type_ids' : ['rpm'],
      'filters' : {
        'unit' : {
          '$and': [{'name': {'$regex': 'p.*'}}, {'version': {'$gt': '1.0'}}]
        }
      }
    }
  }

