Catalog
=======

The content catalog contains information about content that is provided by Pulp's alternate
content sources.


Deleting Entries
----------------

Delete entries from the catalog by content source by ID.

| :method:`delete`
| :path:`/v2/content/catalog/<source-id>/`
| :permission:`delete`
| :param_list:`delete` None
| :response_list:`_`

* :response_code:`200,even if no entries matched and deleted`

| :return:`A summary of entries deleted`

:sample_response:`200` ::

 {"deleted": 10}


