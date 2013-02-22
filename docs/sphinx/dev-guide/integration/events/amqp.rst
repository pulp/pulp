AMQP Notifier
==============

The AMQP notifier is used to send Pulp events to an AMQP message broker. Messages
are sent to a topic exchange. Each message "subject" starts with "pulp.server"
and is then followed by the full message type, such as "repo.sync.finish" to
yield a "subject" (or "topic") of "pulp.server.repo.sync.finish".

The default exchange will be "amq.topic", which is guaranteed to exist. A
new default may be specified in server.conf, and that may be overridden by
the configuration described below.

Configuration
-------------

The AMQP notifier is used by specifying the notifier type as ``amqp``.

The following configuration values are supported when using the AMQP notifier:

``exchange``
  Optional. The name of an AMQP exchange to use. The exchange must be of type
  "topic".

Body
----

The body of an inbound event notification will be a JSON document containing
the following keys:

``event_type``
  Indicates the type of event that is being sent.

``payload``
  JSON document describing the event. This will vary based on the type of event.

``call_report``
  JSON document giving the :ref:`call_report`, if the event was triggered within
  the context of a task. Otherwise this field will be *null*.
