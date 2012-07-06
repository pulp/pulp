REST API Notifier
=================

The REST API notifier is used to trigger a callback to a REST API when the
event fires. The callback is a POST operation and the body of the call will
be the contents of the event (and thus vary by type).

Configuration
-------------

The following configuration values are supported when using the REST API
notifier:

``url``
  Full URL to invoke to send the event information. This is required