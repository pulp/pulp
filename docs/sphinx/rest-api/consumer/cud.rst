Register, Update and Unregister
===============================

Register a Consumer
-------------------

Register a new consumer to the Pulp Server. Consumer IDs must be unique across all consumer
registered to the server.

| :method:`post`
| :path:`/v2/consumers/`
| :permission:`create`
| :param_list:`post`

* :param:`id,string,unique identifier for the consumer`
* :param:`?display_name,string,user-friendly name for the consumer`
* :param:`?description,string,user-friendly text describing the consumer`
* :param:`?notes,object,key-value pairs to programmatically tag the consumer`

| :response_list:`_`

* :response_code:`201,The consumer was successfully registered`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a consumer with the given ID`

| :return:`details of registered consumer along with certificate bundle`

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
  "certificate": "-----BEGIN RSA PRIVATE KEY-----\nMIICXQIBAAKBgQDHnogtBjcZtg7NOVp7kfeehlU57OjHmjGWbNqhAtTEKbQbqehk\nL3vl5lyj6znZ6BWN2gzdVZ7SZ6nUzQVdwBaF13dr1WKMYxGRCkH9OEYKIWS87ghq\nz6w/2LKq7Nxjf/ew4CFwkLwpEQStNdBEnBEdKNCDANg/J4b41FvXj7SeyQIDAQAB\nAoGBAL7K0F8wVJPXhbgzPD9lWWYEAQt3W1oED6c17ZT9Lr07GvFh6UNwexxWnG7z\n0fxrLcbCBY+7WSzDdfh16M4dXafmFNndnFjhJPjIeBgDix1HVDC528P5t6OsWLaW\n5aJuZWLjCE5VKmVlIwKaZNSdaXKxmnjzhs4W8Sfy0VrO2fmtAkEA/kQOpSKaRTXI\nKiSViCCcPCvnKdA8Da//OlMg3WReLJTkCepIrtNk23Xy9Z+JJi5WHf35t2mT+7se\n6Ze/zLWELwJBAMj7EB2ZsDBMncwwBeTUfingSKEAI7ePrIJRrkvr52BwtfkPRjOJ\nyMrkP0lFC08/eOiT1z6iu72OEeIhDRcGNocCQQCCaMuOHNI8/xmbq8nZ2MfpAKd+\nRaQXbRYdhvdLNagre23+O+BtclS/Tp5/JgUExS08EsAaNxdEPDPdoQwpZUvXAkBd\niiw3+p27/Qy8SeWUWSnXB6IF/PCisGXTyXxbrZHkmtC2+FruBcTEWXLzAQWAfsQh\nSx208zx5vrOoEUXsX2HlAkB0w1O/T3IYVZVc13Y9sUcPza9NcHxmrUxqID7EzEkd\nBeuezzFJ4I6+81eN+04QTavdbflyn76XtJx7KTbK+bYw\n-----END RSA PRIVATE KEY-----\n-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCASYwDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUwODA1NDcyOFoXDTIyMDUwNjA1NDcyOFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAx56ILQY3GbYO\nzTlae5H3noZVOezox5oxlmzaoQLUxCm0G6noZC975eZco+s52egVjdoM3VWe0mep\n1M0FXcAWhdd3a9VijGMRkQpB/ThGCiFkvO4Ias+sP9iyquzcY3/3sOAhcJC8KREE\nrTXQRJwRHSjQgwDYPyeG+NRb14+0nskCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nWRVouNJvJtZZLWPPtQbpWghDv38m74AYuDrHvB48xRViU+1qLyiYxWABxKCZYuS0\nMclZs6OUKULx+wCYXVh2mRObI8CjCRvQnltU8ZszVzasJ7pFsD72/VJ09+8LeNZj\nldcjwJeYQcZSkukulkkf2ioUwFXoklxs7b2AYErtt4u0bkByMWzE7Wu9Sn1XZkGe\nlRPLjfs+dbNdIbrrN84/lk3Xr1laMKzfMzTuvl7wLkMpBNViJXWoawugk8WifZUG\nCfPQr+27/q5J5595stuDole4K06l2LM0AzVZTgafEAkANsS44GBAudgJpFOpz8Nb\negUAKkd+dIASCLYgJJmE6g==\n-----END CERTIFICATE-----",
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
-------------------

The update consumer call is centered around updating consumer details.

| :method:`put`
| :path:`/v2/consumers/<consumer_id>/`
| :permission:`update`
| :param_list:`put` The body of the request is a JSON document with a root element
  called "delta". The contents of delta are the values to update. Only changed
  parameters need be specified. The following keys are allowed in the delta
  dictionary. Descriptions for each parameter can be found under the register
  consumer API:

* :param:`display-name,,`
* :param:`description,,`
* :param:`notes,,`

| :response_list:`_`

* :response_code:`200,if the update was executed and successful`
* :response_code:`404,if there is no consumer with the give ID`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`database representation of the consumer (after changes made by the update)`

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
  "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATgwDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE3MzQwNFoXDTIyMDUyMTE3MzQwNFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA2epznXIgdYon\nJYmF7kcUpH3BUgigEP3ynYqnPGHdFw+n111jACmx+GLH8137HZs43XH4RpxZwTXK\nHwyq97Ga8ME9tS4U055QZvzrskX/tNdi1fpgAi3mc7JipFBkQsvwj3rUgCyIrO0w\nV1NZ8iI5Abt1ipXQIdz0U/JgIbhv+E8CAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nVsymqP3aY9CPYdSL6Sg9FH9duM6hudXts7U3HOlFRgLGwAGq4Z6RLZhaRKRz/vB+\nYkv1hpZsF/j0GWGTg+FeBGB5/DJxO/gCzlsaEotdGfTRycN1VOhTgQtd4GukGolF\ntOAPQn9rC5ejrdBpl07jjfZ/vXbIEKzhgcfYetydP6KZ37ee1zUhfR7m0XamoAhf\nR3twCCgxnLvSshYyABBStRsVuuVj+fpPoOU6/dcuOI9YWscpvXG3Slo4FBbDDIEq\nREvMg58JX3xHHO77EAWpiwXyFDg/1TmtbR1uvLJTmgadMoJ5UrOg8QvyneVFW1mp\nuoiM/PNWl//HpMZhE1VB8A==\n-----END CERTIFICATE-----",
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

Unregisters a Consumer
-------------------

Unregister a consumer from the Pulp Server.

| :method:`delete`
| :path:`/v2/consumers/<consumer_id>/`
| :permission:`delete`
| :param_list:`delete`
| :response_list:`_`

* :response_code:`200,The consumer was successfully unregistered`
* :response_code:`404,if there is no consumer with the give ID`

| :return:`null`
