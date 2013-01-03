.. _event:

Events
======

The Pulp server has the ability to fire events as a response to various actions
taking place in the server. Event listeners are configured to respond to these
events. The event listener's "notifier" is the action that will handle the
event, such as sending a message describing the event over a message bus
or invoking an HTTP callback. Each event listener is the pairing of a notifier
type, its configuration, and one or more event types to listen for.

Notifiers
---------

.. toctree::
   :maxdepth: 1

   email
   http
   amqp

Event Types
-----------

.. toctree::
   :maxdepth: 1

   repo-action-events
