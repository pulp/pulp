Status
======

Getting the Server Status
-------------------------

An unauthenticated resource that shows the current status of the pulp server.

| :method:`get`
| :path:`/v2/status/`
| :permission:`none`

| :response_list:`_`

    * :response_code:`200,pulp server is up and running`
    * :response_code:`500,pulp server is down and the administrator should be notified`

| :return:`JSON document showing current server status`

:sample_response:`200` ::

    {"api_version": "2"}

