Register, Update, and Unregister
================================

Register a Consumer
-------------------

Register a new consumer with the Pulp server. Consumer IDs must be unique across
all consumers registered to the server.

Part of the reply to this call is an x.509 certificate that is used to identify
the consumer for operations performed on its behalf. The certificate should be
stored with the consumer and used as its client-side SSL certificate to convey
its identification.

| :method:`post`
| :path:`/v2/consumers/`
| :permission:`create`
| :param_list:`post`

* :param:`id,string,unique identifier for the consumer`
* :param:`?display_name,string,user-friendly name for the consumer`
* :param:`?description,string,user-friendly text describing the consumer`
* :param:`?notes,object,key-value pairs to programmatically tag the consumer`

| :response_list:`_`

* :response_code:`201,if the consumer was successfully registered`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a consumer with the given ID`

| :return:`details of registered consumer along with the certificate used to identify the consumer in the future`

:sample_request:`_` ::

 {
  "notes": {"arch": "x86_64", "os": "fedora16"},
  "display_name": null,
  "id": "test-consumer",
  "description": "Fedora 16 test build machine"
 }


:sample_response:`201` ::

 {
   "display_name": "test-consumer",
  "description": "Fedora 16 test build machine",
  "certificate": "-----BEGIN RSA PRIVATE KEY-----[snip]-----END CERTIFICATE-----",
  "_ns": "gc_consumers",
  "notes": {
    "arch": "x86_64",
    "os": "fedora16"
  },
  "capabilities": {},
  "unit_profile": [],
  "_id": {
    "$oid": "4fa8b370e5e7101087000009"
  },
  "id": "test-consumer"
 }


Update a Consumer
-----------------

The update consumer call is used to change the details of an existing consumer.

| :method:`put`
| :path:`/v2/consumers/<consumer_id>/`
| :permission:`update`
| :param_list:`put` The body of the request is a JSON document with a root element
  called ``delta``. The contents of delta are the values to update. Only changed
  parameters need be specified. The following keys are allowed in the delta
  dictionary. Descriptions for each parameter can be found under the register
  consumer API:

* :param:`display-name,,`
* :param:`description,,`
* :param:`notes,,`

| :response_list:`_`

* :response_code:`200,if the update was executed and successful`
* :response_code:`404,if there is no consumer with the given ID`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`database representation of the consumer after changes made by the update`

:sample_request:`_` ::

 {
  "delta": {"display-name": "Test Consumer",
            "notes": {"arch": "x86_64"},
            "description": "QA automation testing machine"}
 }

:sample_response:`200` ::

 {

  "display_name": "test-consumer",
  "description": "QA automation testing machine",
  "certificate": "-----BEGIN CERTIFICATE-----[snip]-----END CERTIFICATE-----",
  "_ns": "gc_consumers",
  "notes": {
    "arch": "x86_64"
  },
  "capabilities": {},
  "unit_profile": [],
  "_id": {
    "$oid": "4fbd1f8ce5e710295000000b"
  },
  "id": "test-consumer"

 }

Unregister a Consumer
---------------------

Unregister a consumer from the Pulp server. If the consumer is configured
with messaging capabilities, it will be notified of its unregistration.

| :method:`delete`
| :path:`/v2/consumers/<consumer_id>/`
| :permission:`delete`
| :param_list:`delete`
| :response_list:`_`

* :response_code:`200,if the consumer was successfully unregistered`
* :response_code:`404,if there is no consumer with the given ID`

| :return:`null`
