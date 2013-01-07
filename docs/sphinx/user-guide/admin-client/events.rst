Events
======

Pulp has an event system that makes it easy for third party application to integrate
and for users to stay informed via email about the Pulp server's activity. A
specific set of operations inside the Pulp server produce reports about what they
accomplished, and those reports are fed into an event framework. Users can then
setup event listeners that listen for specific events, which then sends notifications
to the user or an automated service. Notifier types include email, AMQP, and HTTP.

Listeners
---------

Event listeners connect one or more event types with a notifier.

::

  $ pulp-admin event listener
  Usage: pulp-admin listener [SUB_SECTION, ..] COMMAND
  Description: manage server-side event listeners

  Available Sections:
    amqp  - manage amqp listeners
    email - manage email listeners
    http  - manage http listeners

  Available Commands:
    delete - delete an event listener
    list   - list all of the event listeners in the system

From this section of the CLI, you can ``list`` and ``delete`` listeners, or drill
down into type-specific sections to ``create`` and ``update``. Examples for each
type of notifier appear below.

Email
-----

Event reports can be sent directly to an email address. The messages currently
consists of a JSON-serialized representation of the actual event body. This meets
a basic use case for having email notification with all of the available event
data, but we intend to make the output more human-friendly in the future.

.. note::
  Before attempting to setup email notifications, be sure to configure the "[email]"
  section of Pulp's settings file, ``/etc/pulp/server.conf``

::

  $ pulp-admin event listener email create --help
  Command: create
  Description: create a listener

  Available Arguments:

    --event-type - (required) one of "repo.sync.start", "repo.sync.finish",
                   "repo.publish.start", "repo.publish.finish". May be specified
                   multiple times. To match all types, use value "*"
    --subject    - (required) text of the email's subject
    --addresses  - (required) this is a comma separated list of email addresses
                   that should receive these notifications. Do not include spaces.

To add an email notifier, you must specify what types of events to listen to,
what the email subject should be, and who should receive the emails.

::

  $ pulp-admin event listener email create --event-type="repo.sync.start" --subject="pulp notification" --addresses=someone@redhat.com,another@redhat.com
  Event listener successfully created

  $ pulp-admin event listener list
  Event Types:       repo.sync.start
  Id:                5081a42ce19a00ea4300000e
  Notifier Config:
    Addresses: someone@redhat.com, another@redhat.com
    Subject:   pulp notification
  Notifier Type Id:  email

Using python's builtin testing MTA, the following message was captured after being
sent by the above-configured listener.

::

  $ python -m smtpd -n -c DebuggingServer localhost:1025
  ---------- MESSAGE FOLLOWS ----------
  Content-Type: text/plain; charset="us-ascii"
  MIME-Version: 1.0
  Content-Transfer-Encoding: 7bit
  Subject: pulp notification
  From: no-repy@your.domain
  To: someone@redhat.com
  X-Peer: 127.0.0.1

  {
    "call_report": {
      "task_group_id": "aaa8f2ec-964c-4d62-bba9-3191aad9c3ea",
      "exception": null,
      "task_id": "79be77a8-1a20-11e2-aeb9-1803731e94c4",
      "tags": [
        "pulp:repository:pulp2",
        "pulp:action:sync"
      ],
      "reasons": [],
      "start_time": "2012-10-19T19:09:16Z",
      "traceback": null,
      "schedule_id": null,
      "finish_time": null,
      "state": "running",
      "result": null,
      "progress": {},
      "principal_login": "admin",
      "response": "accepted"
    },
    "event_type": "repo.sync.start",
    "payload": {
      "repo_id": "pulp2"
    }
  }
  ------------ END MESSAGE ------------

HTTP
----

Event reports can be sent via a POST call to any URL, and basic auth credentials
may be supplied. The body of the HTTP request is a JSON-serialized version of the
event report. Here is an example of creating an HTTP listener.

::

  $ pulp-admin event listener http create --event-type=repo.sync.start --url=http://myserver.redhat.com
  Event listener successfully created

  [mhrivnak@redhrivnak pulp]$ pulp-admin event listener list
  Event Types:       repo.sync.start
  Id:                50bf51ffdd01fb5b9d000003
  Notifier Config:
    URL: http://myserver.redhat.com
  Notifier Type Id:  http

AMQP
----

AMQP is an industry standard for integrating separate systems, applications, or
even components within an application through asynchronous messages. Pulp's event
reports can be sent as the body of an AMQP message to a message broker, where it
will be forwarded to any number of clients who subscribe to Pulp's topic exchange.

Pulp uses `Apache Qpid <http://qpid.apache.org/>`_ as an AMQP broker and publishes
its messages to a `topic exchange <https://access.redhat.com/knowledge/docs/en-US/Red_Hat_Enterprise_MRG/1.1/html/Messaging_User_Guide/chap-Messaging_User_Guide-Exchanges.html#sect-Messaging_User_Guide-Exchange_Types-Topic_Exchange>`_.
Even though AMQP is a widely-adopted standard protocol, there are several
incompatible versions of it. For this reason, there is not another broker that
can be used in place of Qpid.

.. note::
  Before using an AMQP notifier, be sure to look in Pulp's server config file
  (``/etc/pulp/server.conf``) in the "[messaging]" section to configure your settings.

::

  $ pulp-admin event listener amqp create --help
  Command: create
  Description: create a listener

  Available Arguments:

    --event-type - (required) one of "repo.sync.start", "repo.sync.finish",
                   "repo.publish.start", "repo.publish.finish". May be specified
                   multiple times. To match all types, use value "*"
    --exchange   - optional name of an exchange that overrides the setting from
                   server.conf

Here you can also specify an exchange name. If you don’t specify one, it will
default to the value pulled from ``/etc/pulp/server.conf`` in the "[messaging]"
section. If you don’t set one there either, Pulp will default to "amq.topic",
which is an exchange guaranteed to be available on any broker. Regardless of
what name you choose (we suggest "pulp" as a reasonable choice), you do not need
to create the exchange or take any action on the AMQP broker. Pulp will
automatically create the exchange if it does not yet exist.

As for selecting event types, if you are unsure, we suggest going with "*" to
select all of them. The client can choose which types of messages they want to
subscribe to based on hierarchically matching against the event type (called a
"subject" in AMQP). It is cheap and fast to send a message to a broker, making it
convenient to fire and forget. Let the clients decide which subjects they care
about. More about subject matching `here <https://access.redhat.com/knowledge/docs/en-US/Red_Hat_Enterprise_MRG/1.1/html/Messaging_User_Guide/chap-Messaging_User_Guide-Exchanges.html#sect-Messaging_User_Guide-Exchange_Types-Topic_Exchange>`_.

This is an example of creating an AMQP event listener.

::

  $ pulp-admin event listener amqp create --event-type='*' --exchange=pulp
  Event listener successfully created

  [mhrivnak@dhcp-230-147 pulp]$ pulp-admin event listener list
  Event Types:       *
  Id:                5092d9b3e19a00c58600000c
  Notifier Config:
    Exchange: pulp
  Notifier Type Id:  amqp

Event Types
-----------

These are the types of events that can be associated with listeners, and each
description includes a partial list of the types of data that gets reported.

repo.publish.start
  Fires when any repository starts a publish operation.
    * start time
    * repo_id
    * user who initiated the sync
    * task ID

repo.publish.finish
  Fires when any repository finishes a publish operation.
    * start time
    * end time
    * repo_id
    * task ID
    * success/failure
    * number of items published
    * errors

repo.sync.start
  Fires when any repository starts a sync operation.
    * start time
    * repo_id
    * user who initiated the sync
    * task ID

repo.sync.finish
  Fires when any repository finishes a sync operation.
    * start time
    * end time
    * repo_id
    * task ID
    * success/failure
    * number of items imported
    * errors

