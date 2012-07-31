Retrieval
=========

Retrieve a Single Consumer
--------------------------

Retrieves information on a single Pulp consumer. The returned data includes
general consumer details.

| :method:`get`
| :path:`/v2/consumers/<consumer_id>/`
| :permission:`read`
| :param_list:`get`

* :param:`details,bool,include all details about the consumer`
* :param:`bindings,bool,include information about consumer bindings`

| :response_list:`_`

* :response_code:`200,if the consumer exists`
* :response_code:`404,if no consumer exists with the given ID`

| :return:`database representation of the matching consumer with the addition of repository bindings information for the consumer`

:sample_response:`200` ::

 {
   "display_name": "test-consumer",
   "description": null,
   "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATowDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE5MDY0MFoXDTIyMDUyMTE5MDY0MFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7XNQasWOzu0B\nmIr4ByA91GOXXdL1ygxg1iI7XLt3cKyIl7UiJuVDVqjW4/UJ7In3vZYVgGE4hfye\n9/tTxkcYcFqddMclSHmkYTL5LTB564ToJN3XBUFWoqQgi3/tn9GPHiM8u0BQiqFF\nCL+B8trz/F7oh0CuwwCbh7YSZCYSJjMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nOiaWBqBU5ye8RkOjNg2H8t5EeH5aUi0sQLNd5ER0RKL3hGv7lOaDi2JrEVYefBLW\ntHS7oOKcl1Naf1VI0xoG775fSph+SuHokJkwhqMCZFV+YK5838Rzt46i1s9+EOZn\ncFwn8AUc6f5hlf59OevRzDxzYxd2tFldmlR/mOhIezkpQe/C1bPvYRqu+rNyJNCZ\neoUQkTf/NOQjwYp1u+jyksWGvHctORHPt6OMJwpKu1mhIbmAcNPWvLqvG8kAdU47\nPk3Hipuj/HpjHurn7C6Gm1zb5mgRKaYke6LTf6Hd3/txjBo7gqkwoP3QvPmgV3Dn\n8Y3PoRxp7uq32ogr9j+I1g==\n-----END CERTIFICATE-----",
   "_ns": "gc_consumers",
   "notes": {"arch":"i386"},
   "capabilities": {},
   "unit_profile": [],
   "bindings": [],
   "_id": {
     "$oid": "4fbd3540e5e7102dae000015"
   },
   "id": "test-consumer"
 }


Retrieve All Consumers
----------------------

Returns information on all consumers in the Pulp server. Eventually this call
will support query parameters to limit the results and provide searching capabilities.
This call will never return a 404; an empty list is returned in the case
where there are no consumers.

| :method:`get`
| :path:`/v2/consumers/`
| :permission:`read`
| :param_list:`get`

* :param:`details,bool,include all details about the consumer`
* :param:`bindings,bool,include information about consumer bindings`

| :response_list:`_`

* :response_code:`200,containing the list of consumers`

| :return:`the same format as retrieving a single consumer, except the base of the return value is a list of them`

:sample_response:`200` ::

 [
  {
    "display_name": "test-consumer",
    "description": null,
    "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATowDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE5MDY0MFoXDTIyMDUyMTE5MDY0MFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7XNQasWOzu0B\nmIr4ByA91GOXXdL1ygxg1iI7XLt3cKyIl7UiJuVDVqjW4/UJ7In3vZYVgGE4hfye\n9/tTxkcYcFqddMclSHmkYTL5LTB564ToJN3XBUFWoqQgi3/tn9GPHiM8u0BQiqFF\nCL+B8trz/F7oh0CuwwCbh7YSZCYSJjMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nOiaWBqBU5ye8RkOjNg2H8t5EeH5aUi0sQLNd5ER0RKL3hGv7lOaDi2JrEVYefBLW\ntHS7oOKcl1Naf1VI0xoG775fSph+SuHokJkwhqMCZFV+YK5838Rzt46i1s9+EOZn\ncFwn8AUc6f5hlf59OevRzDxzYxd2tFldmlR/mOhIezkpQe/C1bPvYRqu+rNyJNCZ\neoUQkTf/NOQjwYp1u+jyksWGvHctORHPt6OMJwpKu1mhIbmAcNPWvLqvG8kAdU47\nPk3Hipuj/HpjHurn7C6Gm1zb5mgRKaYke6LTf6Hd3/txjBo7gqkwoP3QvPmgV3Dn\n8Y3PoRxp7uq32ogr9j+I1g==\n-----END CERTIFICATE-----",
    "_ns": "gc_consumers",
    "notes": {"arch":"i386"},
    "capabilities": {},
    "unit_profile": [],
    "bindings": [],
    "_id": {
      "$oid": "4fbd3540e5e7102dae000015"
    },
    "id": "test-consumer"
  },
  {
    "display_name": "test-consumer1",
    "description": null,
    "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATowDQYJKoZIhvcNApCEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE5MDY0MFoXDTIyMDUyMTE5MDY0MFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7XNQasWOzu0B\nmIr4ByA91GOXXdL1ygxg1iI7XLt3cKyIl7UiJuVDVqjW4/UJ7In3vZYVgGE4hfye\n9/tTxkcYcFqddMclSHmkYTL5LTB564ToJN3XBUFWoqQgi3/tn9GPHiM8u0BQiqFF\nCL+B8trz/F7oh0CuwwCbh7YSZCYSJjMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nOiaWBqBU5ye8RkOjNg2H8t5EeH5aUi0sQLNd5ER0RKL3hGv7lOaDi2JrEVYefBLW\ntHS7oOKcl1Naf1VI0xoG775fSph+SuHokJkwhqMCZFV+YK5838Rzt46i1s9+EOZn\ncFwn8AUc6f5hlf59OevRzDxzYxd2tFldmlR/mOhIezkpQe/C1bPvYRqu+rNyJNCZ\neoUQkTf/NOQjwYp1u+jyksWGvHctORHPt6OMJwpKu1mhIbmAcNPWvLqvG8kAdU47\nPk3Hipuj/HpjHurn7C6Gm1zb5mgRKaYke6LTf6Hd3/txjBo7gqkwoP3QvPmgV3Dn\n8Y3PoRxp7uq32ogr9j+I1g==\n-----END CERTIFICATE-----",
    "_ns": "gc_consumers",
    "notes": {},
    "capabilities": {},
    "unit_profile": [],
    "bindings": [],
    "_id": {
      "$oid": "4fbd3540e5e7102dae00000d"
    },
    "id": "test-consumer1"
  }
 ]

Advanced Search for Consumers
-----------------------------

Please see :ref:`search_api` for more details on how to perform these searches.

Returns information on consumers in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no consumers.

| :method:`post`
| :path:`/v2/consumers/search/`
| :permission:`read`
| :param_list:`post` include the key "criteria" whose value is a mapping
  structure as defined in :ref:`search_criteria`.  Optionally include the key
  "bindings" with any value that evaluates to True to have the "bindings"
  attribute added to each returned consumer.

* :param:`criteria,object,the search criteria defined in` :ref:`search_criteria`
* :param:`details,bool,include all details about the consumer`
* :param:`bindings,bool,include information about consumer bindings`  

| :response_list:`_`

* :response_code:`200,containing the list of consumers`

| :return:`the same format as retrieving a single consumer, except the base of the return value is a list of them`

:sample_response:`200` ::

 [
  {
    "display_name": "test-consumer",
    "description": null,
    "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATowDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE5MDY0MFoXDTIyMDUyMTE5MDY0MFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7XNQasWOzu0B\nmIr4ByA91GOXXdL1ygxg1iI7XLt3cKyIl7UiJuVDVqjW4/UJ7In3vZYVgGE4hfye\n9/tTxkcYcFqddMclSHmkYTL5LTB564ToJN3XBUFWoqQgi3/tn9GPHiM8u0BQiqFF\nCL+B8trz/F7oh0CuwwCbh7YSZCYSJjMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nOiaWBqBU5ye8RkOjNg2H8t5EeH5aUi0sQLNd5ER0RKL3hGv7lOaDi2JrEVYefBLW\ntHS7oOKcl1Naf1VI0xoG775fSph+SuHokJkwhqMCZFV+YK5838Rzt46i1s9+EOZn\ncFwn8AUc6f5hlf59OevRzDxzYxd2tFldmlR/mOhIezkpQe/C1bPvYRqu+rNyJNCZ\neoUQkTf/NOQjwYp1u+jyksWGvHctORHPt6OMJwpKu1mhIbmAcNPWvLqvG8kAdU47\nPk3Hipuj/HpjHurn7C6Gm1zb5mgRKaYke6LTf6Hd3/txjBo7gqkwoP3QvPmgV3Dn\n8Y3PoRxp7uq32ogr9j+I1g==\n-----END CERTIFICATE-----",
    "_ns": "gc_consumers",
    "notes": {"arch":"i386"},
    "capabilities": {},
    "unit_profile": [],
    "bindings": [],
    "_id": {
      "$oid": "4fbd3540e5e7102dae000015"
    },
    "id": "test-consumer"
  },
  {
    "display_name": "test-consumer1",
    "description": null,
    "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATowDQYJKoZIhvcNApCEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE5MDY0MFoXDTIyMDUyMTE5MDY0MFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7XNQasWOzu0B\nmIr4ByA91GOXXdL1ygxg1iI7XLt3cKyIl7UiJuVDVqjW4/UJ7In3vZYVgGE4hfye\n9/tTxkcYcFqddMclSHmkYTL5LTB564ToJN3XBUFWoqQgi3/tn9GPHiM8u0BQiqFF\nCL+B8trz/F7oh0CuwwCbh7YSZCYSJjMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nOiaWBqBU5ye8RkOjNg2H8t5EeH5aUi0sQLNd5ER0RKL3hGv7lOaDi2JrEVYefBLW\ntHS7oOKcl1Naf1VI0xoG775fSph+SuHokJkwhqMCZFV+YK5838Rzt46i1s9+EOZn\ncFwn8AUc6f5hlf59OevRzDxzYxd2tFldmlR/mOhIezkpQe/C1bPvYRqu+rNyJNCZ\neoUQkTf/NOQjwYp1u+jyksWGvHctORHPt6OMJwpKu1mhIbmAcNPWvLqvG8kAdU47\nPk3Hipuj/HpjHurn7C6Gm1zb5mgRKaYke6LTf6Hd3/txjBo7gqkwoP3QvPmgV3Dn\n8Y3PoRxp7uq32ogr9j+I1g==\n-----END CERTIFICATE-----",
    "_ns": "gc_consumers",
    "notes": {},
    "capabilities": {},
    "unit_profile": [],
    "bindings": [],
    "_id": {
      "$oid": "4fbd3540e5e7102dae00000d"
    },
    "id": "test-consumer1"
  }
 ]

Returns information on consumers in the Pulp server that match your search
parameters. It is worth noting that this call will never return a 404; an empty
list is returned in the case where there are no consumers.

This method is slightly more limiting than the POST alternative, because some
filter expressions may not be serializable as query parameters.

| :method:`get`
| :path:`/v2/consumers/search/`
| :permission:`read`
| :param_list:`get` query params should match the attributes of a Criteria
 object as defined in :ref:`search_criteria`.
 For example: /v2/consumers/search/?field=id&field=display_name&limit=20'
 Include the key 'bindings' to have the 'bindings' attribute,
  a list of related bindings, added to each returned consumer.
| :response_list:`_`

* :response_code:`200,containing the list of consumers`

| :return:`the same format as retrieving a single consumer, except the base of the return value is a list of them`

:sample_response:`200` ::

 [
  {
    "display_name": "test-consumer",
    "description": null,
    "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATowDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE5MDY0MFoXDTIyMDUyMTE5MDY0MFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7XNQasWOzu0B\nmIr4ByA91GOXXdL1ygxg1iI7XLt3cKyIl7UiJuVDVqjW4/UJ7In3vZYVgGE4hfye\n9/tTxkcYcFqddMclSHmkYTL5LTB564ToJN3XBUFWoqQgi3/tn9GPHiM8u0BQiqFF\nCL+B8trz/F7oh0CuwwCbh7YSZCYSJjMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nOiaWBqBU5ye8RkOjNg2H8t5EeH5aUi0sQLNd5ER0RKL3hGv7lOaDi2JrEVYefBLW\ntHS7oOKcl1Naf1VI0xoG775fSph+SuHokJkwhqMCZFV+YK5838Rzt46i1s9+EOZn\ncFwn8AUc6f5hlf59OevRzDxzYxd2tFldmlR/mOhIezkpQe/C1bPvYRqu+rNyJNCZ\neoUQkTf/NOQjwYp1u+jyksWGvHctORHPt6OMJwpKu1mhIbmAcNPWvLqvG8kAdU47\nPk3Hipuj/HpjHurn7C6Gm1zb5mgRKaYke6LTf6Hd3/txjBo7gqkwoP3QvPmgV3Dn\n8Y3PoRxp7uq32ogr9j+I1g==\n-----END CERTIFICATE-----",
    "_ns": "gc_consumers",
    "notes": {"arch":"i386"},
    "capabilities": {},
    "unit_profile": [],
    "bindings": [],
    "_id": {
      "$oid": "4fbd3540e5e7102dae000015"
    },
    "id": "test-consumer"
  },
  {
    "display_name": "test-consumer1",
    "description": null,
    "certificate": "-----BEGIN CERTIFICATE-----\nMIICHDCCAQQCATowDQYJKoZIhvcNApCEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0\nMB4XDTEyMDUyMzE5MDY0MFoXDTIyMDUyMTE5MDY0MFowGDEWMBQGA1UEAxMNdGVz\ndC1jb25zdW1lcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7XNQasWOzu0B\nmIr4ByA91GOXXdL1ygxg1iI7XLt3cKyIl7UiJuVDVqjW4/UJ7In3vZYVgGE4hfye\n9/tTxkcYcFqddMclSHmkYTL5LTB564ToJN3XBUFWoqQgi3/tn9GPHiM8u0BQiqFF\nCL+B8trz/F7oh0CuwwCbh7YSZCYSJjMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEA\nOiaWBqBU5ye8RkOjNg2H8t5EeH5aUi0sQLNd5ER0RKL3hGv7lOaDi2JrEVYefBLW\ntHS7oOKcl1Naf1VI0xoG775fSph+SuHokJkwhqMCZFV+YK5838Rzt46i1s9+EOZn\ncFwn8AUc6f5hlf59OevRzDxzYxd2tFldmlR/mOhIezkpQe/C1bPvYRqu+rNyJNCZ\neoUQkTf/NOQjwYp1u+jyksWGvHctORHPt6OMJwpKu1mhIbmAcNPWvLqvG8kAdU47\nPk3Hipuj/HpjHurn7C6Gm1zb5mgRKaYke6LTf6Hd3/txjBo7gqkwoP3QvPmgV3Dn\n8Y3PoRxp7uq32ogr9j+I1g==\n-----END CERTIFICATE-----",
    "_ns": "gc_consumers",
    "notes": {},
    "capabilities": {},
    "unit_profile": [],
    "bindings": [],
    "_id": {
      "$oid": "4fbd3540e5e7102dae00000d"
    },
    "id": "test-consumer1"
  }
 ]

