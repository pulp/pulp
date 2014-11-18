Retrieval
=========

Retrieve Permissions for particular resource
--------------------------------------------

If a resource is specified, permissions for the particular resource are returned.
In this case the array will contain a single item.

| :method:`get`
| :path:`/v2/permissions/`
| :permission:`read`
| :param_list:`get` Resource path URI should be specifield.
 For example to retrieve permissions for "/v2/actions/login/":
 /v2/permissions/?resource=%2Fv2%2Factions%2Flogin%2F

| :response_list:`_`

* :response_code:`200,containing the array of permissions for specified resource`

| :return:`array of database representation of permissions for specified resource`

:sample_response:`200` ::

[
 {
    "_id": {
        "$oid": "546a6ece6754762f1c34b1db"
    },
    "_ns": "permissions",
    "id": "546a6ece6754762f1c34b1db",
    "resource": "/v2/actions/login/",
    "users": {
        "admin": [
            "READ",
            "UPDATE"
        ]
    }
 }
]


Retrieve Permissions for all resources
--------------------------------------

Returns information on permissions for all resources.

| :method:`get`
| :path:`/v2/permissions/`
| :permission:`read`
| :param_list:`get`

| :response_list:`_`

* :response_code:`200,containing the array of permissions`

| :return:`array of database representation of permissions`

:sample_response:`200` ::

 [
  {
    "_ns": "permissions", 
    "_id": {
      "$oid": "5035917fe5e7106f4100000c"
    }, 
    "resource": "/v2/actions/login/", 
    "id": "5035917fe5e7106f4100000c", 
    "users": {
      "admin": [
        "READ", 
        "UPDATE"
      ]
    }
  }, 
  {
    "_ns": "permissions", 
    "_id": {
      "$oid": "5035917fe5e7106f4100000d"
    }, 
    "resource": "/v2/actions/logout/", 
    "id": "5035917fe5e7106f4100000d", 
    "users": {
      "admin": [
        "READ", 
        "UPDATE"
      ]
    }
  }, 
  {
    "_ns": "permissions", 
    "_id": {
      "$oid": "5035917fe5e7106f41000010"
    }, 
    "resource": "/", 
    "id": "5035917fe5e7106f41000010", 
    "users": {
      "admin": [
        "CREATE", 
        "READ", 
        "UPDATE", 
        "DELETE", 
        "EXECUTE"
      ]
    }
  }
 ]


