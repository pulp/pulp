Content Sources
===============

Pulp's Content Sources represent external sources of content.


List All Sources
----------------

Get all content sources.

| :method:`get`
| :path:`/v2/content/sources/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200, on success`

| :return:`a list of content source objects`

:sample_response:`200` ::

    [
      {
        "paths": "el7-x86_64/ pulp-el7-x86_64/",
        "name": "Local Content",
        "type": "yum",
        "ssl_validation": "true",
        "expires": "3d",
        "enabled": "1",
        "base_url": "file:///opt/content/disk/",
        "priority": "0",
        "source_id": "disk",
        "max_concurrent": "2",
        "_href": "/pulp/api/v2/content/sources/disk/"
      }
    ]

Get Source By ID
----------------

Get a content source by ID.

| :method:`get`
| :path:`/v2/content/sources/<source-id>/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200, on success`

| :return:`the requested content source object`

:sample_response:`200` ::

    {
    "paths": "el7-x86_64/ pulp-el7-x86_64/",
    "name": "Local Content",
    "type": "yum",
    "ssl_validation": "true",
    "expires": "3d",
    "enabled": "1",
    "base_url": "file:///opt/content/disk/",
    "priority": "0",
    "source_id": "disk",
    "max_concurrent": "2",
    "_href": "/pulp/api/v2/content/sources/disk/"
    }

Refresh All Sources
-------------------

Get all content sources.

| :method:`post`
| :path:`/v2/content/sources/action/refresh/`
| :permission:`update`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`202, on success`

| :return:`a spawned task id`

:sample_response:`202` ::

    [
      {
        "spawned_tasks": [
          {
            "_href": "/pulp/api/v2/tasks/1d893293-5849-47d8-830d-f6f888d347e6/",
            "task_id": "1d893293-5849-47d8-830d-f6f888d347e6"
          }
        ],
        "result": null,
        "error": null
      }
    ]

Refresh Single Source
---------------------

Get all content sources.

| :method:`post`
| :path:`/v2/content/sources/<source-id>/action/refresh/`
| :permission:`update`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`202, on success`

| :return:`a spawned task id`

:sample_response:`202` ::

    [
      {
        "spawned_tasks": [
          {
            "_href": "/pulp/api/v2/tasks/7066c9f0-8606-4842-893a-297d435fe11a/",
            "task_id": "7066c9f0-8606-4842-893a-297d435fe11a"
          }
        ],
        "result": null,
        "error": null
      }
    ]
