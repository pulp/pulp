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

