Status
======

.. _getting_the_server_status:

Getting the Server Status
-------------------------

An unauthenticated resource that shows the current status of the Pulp server. A
200 response shows that the server is up and running. Users of this API may
want to examine ``pulp_messaging_connection``, ``pulp_database_connection``
and ``known_workers`` to get more detailed status information.

.. warning:: Clustered Pulp installations have additional monitoring concerns.
    See :ref:`clustered_monitoring` for more information.

.. note:: This API is meant to provide an "at-a-glance" status to aid debugging
    of a Pulp deployment, and is not meant to replace monitoring of Pulp
    components in a production environment.

A healthy Pulp installation will contain exactly one record for
"resource_manager" and "scheduler" in the worker list, and one or more
"reserved_resource_worker" records. It will also have
``messaging_connection`` and ``database_connection`` entries that contain ``{connected: True}``.
Note that if the scheduler is not running, other workers may be running but not
updating their last heartbeat record.

The version of Pulp is also returned via ``platform_version`` in the
``versions`` object. This field is calculated from the "pulp-server" python
package version. Do not use the deprecated ``api_version`` record.

| :method:`get`
| :path:`/v2/status/`
| :permission:`none`

| :response_list:`_`

    * :response_code:`200, pulp server is up and running`

| :return:`JSON document showing current server status`

:sample_response:`200`::

  {
      "api_version": "2",
      "database_connection": {
          "connected": true
      },
      "known_workers": [
          {
              "last_heartbeat": "2015-01-02T20:39:58Z",
              "name": "scheduler@status-info-net0.default.virt"
          },
          {
              "last_heartbeat": "2015-01-02T20:40:34Z",
              "name": "reserved_resource_worker-0@status-info-net0.default.virt"
          },
          {
              "last_heartbeat": "2015-01-02T20:40:36Z",
              "name": "resource_manager@status-info-net0.default.virt"
          }
      ],
      "messaging_connection": {
          "connected": true
      },
      "versions": {
          "platform_version": "2.6.0"
      }
  }
