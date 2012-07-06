REST API Notifier
=================

The REST API notifier is used to trigger a callback to a REST API when the
event fires. The callback is a POST operation and the body of the call will
be the contents of the event (and thus vary by type).

Configuration
-------------

The REST API notifier is used by specifying the notifier type as ``rest-api``.

The following configuration values are supported when using the REST API
notifier:

``url``
  Required. Full URL to invoke to send the event information.

``username``
  If specified, this value will be passed as basic authentication
  credentials when the REST API is invoked.

``password``
  If specified, this value will be passed as basic authentication
  credentials when the REST API is invoked.

Body
----

The body of an inbound event notification will be a JSON document containing
two keys:

``event_type``
  Indicates the type of event that is being sent.

``payload``
  JSON document describing the event. This will vary based on the type of event.
