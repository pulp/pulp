Server Plugins API
=====================

The pulp server itself has very little built in functionality, so it loads number of plugins
that provide the desired functionality required by administrators.
Loaded plugins can define ``types``, ``importers`` and ``distributors``.


.. _retrieve_content_unit_types:

Retrieve All Content Unit Types
-------------------------------

Queries the server for the loaded content unit type definitions.

| :method:`get`
| :path:`/v2/plugins/types/`
| :permission:`read`

| :response_list:`_`

    * :response_code:`200, list of loaded content types`

| :return:`JSON document showing all loaded content unit types`

:sample_response:`200`::

 [
    {
        "_href": "/pulp/api/v2/plugins/types/puppet_module/",
        "_id": {
            "$oid": "55a391ea45ef481ffab6ac26"
        },
        "_ns": "content_types",
        "description": "Puppet Module",
        "display_name": "Puppet Module",
        "id": "puppet_module",
        "referenced_types": [],
        "search_indexes": [
            "author",
            "tag_list"
        ],
        "unit_key": [
            "name",
            "version",
            "author"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/types/iso/",
        "_id": {
            "$oid": "55a391ea45ef481ffab6ac27"
        },
        "_ns": "content_types",
        "description": "ISO",
        "display_name": "ISO",
        "id": "iso",
        "referenced_types": [],
        "search_indexes": [],
        "unit_key": [
            "name",
            "checksum",
            "size"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/types/docker_image/",
        "_id": {
            "$oid": "55a391ea45ef481ffab6ac28"
        },
        "_ns": "content_types",
        "description": "Docker Image",
        "display_name": "Docker Image",
        "id": "docker_image",
        "referenced_types": [],
        "search_indexes": [],
        "unit_key": [
            "image_id"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/types/rpm/",
        "_id": {
            "$oid": "55a391ea45ef481ffab6ac32"
        },
        "_ns": "content_types",
        "description": "RPM",
        "display_name": "RPM",
        "id": "rpm",
        "referenced_types": [
            "erratum"
        ],
        "search_indexes": [
            "name",
            "epoch",
            "version",
            "release",
            "arch",
            "filename",
            "checksum",
            "checksumtype",
            "version_sort_index",
            [
                "version_sort_index",
                "release_sort_index"
            ]
        ],
        "unit_key": [
            "name",
            "epoch",
            "version",
            "release",
            "arch",
            "checksumtype",
            "checksum"
        ]
    }
 ]


Retrieve a Specific Content Unit Type
-----------------------------------

Retrieves information about a specific content unit type.

| :method:`get`
| :path:`/v2/plugins/types/<type_id>/`
| :permission:`read`

| :response_list:`_`

    * :response_code:`200, the content type exists`
    * :response_code:`404, the content type does not exist`

| :return:`JSON document showing queried content unit type`

:sample_response:`200`::

 {
    "_href": "/pulp/api/v2/plugins/types/iso/",
    "_id": {
        "$oid": "55a391ea45ef481ffab6ac27"
    },
    "_ns": "content_types",
    "description": "ISO",
    "display_name": "ISO",
    "id": "iso",
    "referenced_types": [],
    "search_indexes": [],
    "unit_key": [
        "name",
        "checksum",
        "size"
    ]
 }


.. _getting_importers:

Retrieve All Importer Plugins
-----------------------------

Queries the server for the loaded importer plugins.

| :method:`get`
| :path:`/v2/plugins/importers/`
| :permission:`read`

| :response_list:`_`

    * :response_code:`200, list of loaded importer plugins`

| :return:`JSON document showing all loaded importer plugins`

:sample_response:`200`::

 [
    {
        "_href": "/pulp/api/v2/plugins/importers/puppet_importer/",
        "display_name": "Puppet Importer",
        "id": "puppet_importer",
        "types": [
            "puppet_module"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/importers/yum_importer/",
        "display_name": "Yum Importer",
        "id": "yum_importer",
        "types": [
            "distribution",
            "drpm",
            "erratum",
            "package_group",
            "package_category",
            "rpm",
            "srpm",
            "yum_repo_metadata_file",
            "package_environment"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/importers/nodes_http_importer/",
        "display_name": "Pulp Nodes HTTP Importer",
        "id": "nodes_http_importer",
        "types": [
            "node",
            "repository"
        ]
    }
 ]


Retrieve a Specific Importer Plugin
----------------------------------

Retrieves information about a specific importer plugin.

| :method:`get`
| :path:`/v2/plugins/importers/<importer_id>/`
| :permission:`read`

| :response_list:`_`

    * :response_code:`200, the importer id  exists`
    * :response_code:`404, the importer id does not exist`

| :return:`JSON document showing queried importer`

:sample_response:`200`::

 {
    "_href": "/pulp/api/v2/plugins/importers/puppet_importer/",
    "display_name": "Puppet Importer",
    "id": "puppet_importer",
    "types": [
        "puppet_module"
    ]
 }

 
.. _getting_distributors:

Retrieve All Distributor Plugins
--------------------------------

Queries the server for the loaded distributor plugins.

| :method:`get`
| :path:`/v2/plugins/distributors/`
| :permission:`read`

| :response_list:`_`

    * :response_code:`200, list of loaded distributor plugins`

| :return:`JSON document showing all loaded distributor plugins`

:sample_response:`200`::

 [
    {
        "_href": "/pulp/api/v2/plugins/distributors/yum_distributor/",
        "display_name": "Yum Distributor",
        "id": "yum_distributor",
        "types": [
            "rpm",
            "srpm",
            "drpm",
            "erratum",
            "package_group",
            "package_category",
            "distribution",
            "yum_repo_metadata_file"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/distributors/puppet_distributor/",
        "display_name": "Puppet Distributor",
        "id": "puppet_distributor",
        "types": [
            "puppet_module"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/distributors/nodes_http_distributor/",
        "display_name": "Pulp Nodes HTTP Distributor",
        "id": "nodes_http_distributor",
        "types": [
            "node"
        ]
    },
    {
        "_href": "/pulp/api/v2/plugins/distributors/docker_distributor_web/",
        "display_name": "Docker Web Distributor",
        "id": "docker_distributor_web",
        "types": [
            "docker_image"
        ]
    }  
 ]


Retrieve a Specific Distributor Plugin
------------------------------------

Retrieves information about a specific distributor plugin.

| :method:`get`
| :path:`/v2/plugins/distributors/<distributor_id>/`
| :permission:`read`

| :response_list:`_`

    * :response_code:`200, the distributor id exists`
    * :response_code:`404, the distributor id does not exist`

| :return:`JSON document showing queried distributor`

:sample_response:`200`::

 {
    "_href": "/pulp/api/v2/plugins/distributors/yum_distributor/",
    "display_name": "Yum Distributor",
    "id": "yum_distributor",
    "types": [
        "rpm",
        "srpm",
        "drpm",
        "erratum",
        "package_group",
        "package_category",
        "distribution",
        "yum_repo_metadata_file"
    ]
 }
