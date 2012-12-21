HTTP Notifier
=================

The HTTP notifier is used to trigger a callback to a URL when the
event fires. The callback is a POST operation, and the body of the call will
be the contents of the event (and thus vary by type).

.. note::
  This was previously known as a "REST API" notifier in development versions
  of Pulp 2.0. The first build to include the new name was version 2.0.6-0.12.beta

Configuration
-------------

The HTTP notifier is used by specifying the notifier type as ``http``.

The following configuration values are supported when using the HTTP
notifier:

``url``
  Required. Full URL to invoke to send the event information.

``username``
  If specified, this value will be passed as basic authentication
  credentials when the HTTP request is made.

``password``
  If specified, this value will be passed as basic authentication
  credentials when the HTTP request is made.

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
