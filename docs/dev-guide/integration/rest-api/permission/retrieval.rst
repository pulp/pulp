Retrieval
=========


Retrieve Permissions
--------------------

Returns information on permissions for all resources. If a resource is specified, 
permissions for the particular resource are returned. In this case the array will contain a single item.

| :method:`get`
| :path:`/v2/permissions/`
| :permission:`read`
| :param_list:`get`

* :param:`?resource,string,resource path URI`

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


