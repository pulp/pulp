.. _event:

Events
======

The Pulp server has the ability to fire AMQP events when tasks change their
status. This is enabled by setting ``event_notifications_enabled`` under
``[messaging]`` to ``True`` in ``/etc/pulp/server.conf``. Additionally,
``event_notification_url`` may be set if the notification AMQP server is not
running locally on port 5672.

Messages are published to the ``pulp.api.v2`` topic exchange. Currently only
task status updates are published; they have a routing key of ``tasks.<task
uuid>``. This allows a message consumer to only subscribe to updates for tasks
they are interested in.

The body of the message is a TaskStatus object in JSON form. It typically
contains the task's ID, task status and detailed information about the task's
progress.


Notifiers
---------

.. deprecated:: 2.7
   This section describes a notification framework that has been deprecated and will go away in Pulp 3.0.

.. toctree::
   :maxdepth: 1

   email
   http
   amqp

Event Types
-----------

.. deprecated:: 2.7
   This section describes a notification framework that has been deprecated and will go away in Pulp 3.0.

.. toctree::
   :maxdepth: 1

   repo-action-events
