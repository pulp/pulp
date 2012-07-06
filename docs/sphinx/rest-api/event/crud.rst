Event Listener Creation and Configuration
=========================================

The Pulp server has the ability to fire events as a response to various actions
taking place in the server. Event listeners are configured to respond to these
events. The event listener's "notifier" is the action that will handle the
event, such as sending a message describing the event over a message bus
or invoking a callback REST API. Each event listener is the pairing of a notifier
type, its configuration, and one or more event types to listen for.

Create an Event Listener
------------------------

Creates a new listener in the server that will be notified of any events of
the configured event types. Each listener must specify a notifier type to handle
the event and any configuration necessary for that notifier type. A list of
event types is also specified; the newly created listener is only notified
when events of the given types are fired.

| :method:`post`
| :path:`/v2/events/`
| :permission:`create`
| :param_list:`post`

* :param:`notifier_type,str,one of the supported notifier type IDs`
* :param:`notifier_config,object,configuration values the notifier will use when it handles an event`
* :param:`event_types,list,list of event type IDs that this listener will handle`

| :response_list:`_`

* :response_code:`201,the event listener was successfully created`
* :response_code:`400,if one of the required parameters is missing or an invalid event type is specified`

| :return:`database representation of the created event listener, including its ID`

:sample_request:`_` ::

 {
   "notifier_type_id" : "rest-api",
   "notifier_config" : {
     "url" : "http://localhost/api"
   },
   "event_types" : ["repo-sync-finished", "repo-publish-finished"]
 }

:sample_response:`201` ::

 {
   "_href": "/pulp/api/v2/events/4ff708048a905b7016000008/",
   "_id": {"$oid": "4ff708048a905b7016000008"},
   "_ns": "event_listeners",
   "event_types": [
     "repo-sync-finished",
     "repo-publish-finished"
   ],
   "id": "4ff708048a905b7016000008",
   "notifier_config": {
     "url": "http://localhost/api"
   },
   "notifier_type_id": "rest-api"
 }


Retrieve All Event Listeners
----------------------------

Returns a list of all event listeners in the server.

| :method:`get`
| :path:`/v2/events/`
| :permission:`read`

| :response_list:`_`

* :response_code:`200,list of event listeners, empty list if there are none`

| :return:`database representation of each event listener`

:sample_response:`200` ::

  [
   {
     "_href": "/pulp/api/v2/events/4ff708048a905b7016000008/",
     "_id": {"$oid": "4ff708048a905b7016000008"},
     "_ns": "event_listeners",
     "event_types": [
       "repo-sync-finished",
       "repo-publish-finished"
     ],
     "id": "4ff708048a905b7016000008",
     "notifier_config": {
       "url": "http://localhost/api"
     },
     "notifier_type_id": "rest-api"
   }
  ]

Delete an Event Listener
------------------------

Deletes an event listener. The event listener is identified by its ID which
is found either in the create response or in the data returned by listing all
event listeners.

| :method:`delete`
| :path:`/v2/events/<event_listener_id>`
| :permission:`delete`

| :response_list:`_`

* :response_code:`200,if the event listener was successfully deleted`
* :response_code:`404,if the given event listener does not exist`

| :return:`None`

Update an Event Listener Configuration
--------------------------------------

Changes the configuration for an existing event listener. The notifier type
cannot be changed. The event listener being updated is referenced by its ID
which is found either in the create response or in the data returned by listing
all event listeners.

If the notifier configuration is updated, the following rules apply:

* Configuration keys that are not mentioned in the updated configuration remain
  unchanged.
* Configuration keys with a value of none are removed entirely from the server-side
  storage of the notifier's configuration.
* Any configuration keys with non-none values are saved in the configuration,
  overwriting the previous value for the key if one existed.

Updating the event types is simpler; if present, the provided event types list
becomes the new list of event types for the listener. The previous list is
overwritten.

| :method:`put`
| :path:`/v2/events/<event_listener_id>/`
| :permission:`update`
| :param_list:`put`

* :param:`?notifier_config,object,dictates changes to the configuration as described above`
* :param:`?event_types,list,list of new event types for the listener to listen for`

| :response_list:`_`

* :response_code:`200,if the listener was successfully updated`
* :response_code:`400,if an invalid event type is specified`
* :response_code:`404,if the given event listener does not exist`

| :return:`database representation of the updated listener`

:sample_request:`_` ::

  {
    "event_types" : ["repo-sync-started"]
  }

:sample_response:`200` ::

  {
    "_href": "/pulp/api/v2/events/4ff73d598a905b777d000014/",
    "_id": {"$oid": "4ff73d598a905b777d000014"},
    "_ns": "event_listeners",
    "event_types": [
      "repo-sync-started"
    ],
    "id": "4ff73d598a905b777d000014",
    "notifier_config": {
      "url": "https://localhost/pulp/api/jdob/"
    },
    "notifier_type_id": "rest-api"
  }
