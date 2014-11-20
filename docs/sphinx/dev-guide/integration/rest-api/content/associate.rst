Copying Units Between Repositories
==================================

Pulp provides the ability to copy units between repositories. Units to copy
are specified through a :ref:`unit association criteria <unit_association_criteria>`
applied to a source repository. The ``filters`` field is used to match units,
and the ``fields`` field is optionally used to limit which fields will be loaded
into RAM and handed off to the importer. Limiting which fields are loaded can
reduce the consumption of RAM, especially when the units have a lot of metadata.
All matching units are imported into the destination repository.

The only restriction is that the destination repository must be configured
with an importer that supports the type of units being copied.

| :method:`post`
| :path:`/v2/repositories/<destination_repo_id>/actions/associate/`
| :permission:`update`
| :param_list:`post`

* :param:`source_repo_id,str,repository from which to copy units`
* :param:`?criteria,criteria document,filters which units to copy from the source repository`
* :param:`?override_config,object,importer configuration values that override the importer's default configuration`

| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to execute asynchronously`

| :return:`a` :ref:`call_report`

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
    },
   'override_config': {
     'resolve_dependencies: true,
     'recursive': true
    },
  }


**Sample result value**::

    "result": {
      "units_successful": [
        {
          "unit_key": {
            "name": "whale",
            "checksum": "3b34234afc8b8931d627f8466f0e4fd352145a2512681ec29db0a051a0c9d893",
            "epoch": "0",
            "version": "0.2",
            "release": "1",
            "arch": "noarch",
            "checksumtype": "sha256"
          },
          "type_id": "rpm"
        }
      ]
    }


**Tags:**
The task created will have the following tags.  ``"pulp:repository:<source_repo_id>",
"pulp:consumer:<destination_repo_id>",
"pulp:action:associate"``

Unassociating Content Units from a Repository
=============================================

Pulp also provides the ability to unassociate units from a repository. Units to
unassociate are specified through a :ref:`unit_association_criteria` applied to
the repository. All matching units are unassociated from the repository.

The only restriction is that the content units can only be unassociated by the
same person that originally associated the units with the repository.

Note that there is a `bug <https://bugzilla.redhat.com/show_bug.cgi?id=1021579>`_
related to this call in which criteria with no type_ids field will remove all
units in a repository.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/actions/unassociate/`
| :permission:`update`
| :param_list:`post`

* :param:`criteria,criteria document,filters which units to unassociate from the repository`

| :response_list:`_`

* :response_code:`202,if the request was accepted by the server to execute asynchronously`

| :return:`a` :ref:`call_report`

**Tags:**
The task created will have the following tags.  ``"pulp:repository:<repo_id>",
"pulp:action:unassociate"``
