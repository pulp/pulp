Email Notifier
==============

The Email notifier is used to send an email to specified recipients every time
a particular event type fires. The body of the email will be a JSON serialized
version of the event's payload.

Configuration
-------------

The Email notifier is used by specifying the notifier type as ``email``.

The following configuration values are supported when using the Email notifier:

``subject``
Required. The text of the email's subject.

``addresses``
Required. This is a tuple or list of email addresses that should receive emails.

Body
----

The body of an inbound event notification will be a JSON document containing
two keys:

``event_type``
Indicates the type of event that is being sent.

``payload``
JSON document describing the event. This will vary based on the type of event.
