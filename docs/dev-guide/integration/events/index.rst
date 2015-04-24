.. _event:

Events
======

The Pulp server has the ability to fire AMQP events when tasks change their
status. This is enabled by setting ``event_notifications_enabled`` under
``[messaging]`` to ``True`` in ``/etc/pulp/server.conf``. Additionally,
``event_notification_url`` may be set if the notification AMQP server is not
running locally on port 5672.

.. warning::
   It is highly recommended to use ``python-kombu-3.0.24-6.pulp`` or newer
   which includes a fix for a connection leak.


Messages are published to the ``pulp.api.v2`` topic exchange. Currently only
task status updates are published; they have a routing key of
``tasks.<task-uuid>``. This allows a message consumer to only subscribe to
updates for tasks they are interested in.

The body of the message is a :ref:`task_report` object in JSON form. It typically
contains the task's ID, task status and detailed information about the task's
progress.

This example script will read all events from the exchange and print them:

::

  import base64
  from qpid.messaging import Connection

  receiver = Connection.establish('localhost:5672').session().receiver('pulp.api.v2')

  try:
      while True:
          message = receiver.fetch()
          print base64.b64decode(message.content['body'])
  except KeyboardInterrupt:
      print ''

It is important to note that a sync and publish of a small RPM repo can
generate upwards of 400 messages. We do not queue task status update messages
for later delivery due to the number of messages that may pile up.

If you know the UUID of a task you are interested in, you can subscribe to
messages related to that particular task by adding a subject to the listener.
In the example above, this would be done by replacing ``pulp.api.v2`` with
``pulp.api.v2/tasks.<task-uuid>``. The task's UUID is returned by any API calls
that generate asynchronous work.

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
