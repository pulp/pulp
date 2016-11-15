Retrieval
=========

Retrieve a Single Role
--------------------------

Retrieves information on a single Role. The returned data includes
general role details.

| :method:`get`
| :path:`/v2/roles/<role_id>/`
| :permission:`read`
| :param_list:`get`

| :response_list:`_`

* :response_code:`200,if the role exists`
* :response_code:`404,if no role exists with the given ID`

| :return:`database representation of the matching role`

:sample_response:`200` ::

 {
  "display_name": "Super Users", 
  "description": "Role indicates users with admin privileges", 
  "_ns": "roles", 
  "_href": "/pulp/api/v2/roles/super-users/", 
  "users": [
    "admin"
  ], 
  "_id": {
    "$oid": "502ca7afe5e7106ef1000007"
  }, 
  "id": "super-users", 
  "permissions": {
    "/": [
      "CREATE", 
      "READ", 
      "UPDATE", 
      "DELETE", 
      "EXECUTE"
    ]
  }
 } 



Retrieve All Roles
----------------------

Returns information on all the roles. An empty array is returned in the case
where there are no roles.

| :method:`get`
| :path:`/v2/roles/`
| :permission:`read`
| :param_list:`get`

| :response_list:`_`

* :response_code:`200,containing the array of roles`

| :return:`the same format as retrieving a single role, except the base of the return value is an array of them`

:sample_response:`200` ::

 [
  {
    "display_name": "Super Users", 
    "description": "Role indicates users with admin privileges", 
    "_ns": "roles", 
    "_href": "/pulp/api/v2/roles/super-users/", 
    "users": [
      "admin"
    ], 
    "_id": {
      "$oid": "502ca7afe5e7106ef1000007"
    }, 
    "id": "super-users", 
    "permissions": {
      "/": [
        "CREATE", 
        "READ", 
        "UPDATE", 
        "DELETE", 
        "EXECUTE"
      ]
    }
  }, 
  {
    "display_name": "test", 
    "description": "foo", 
    "_ns": "roles", 
    "_href": "/pulp/api/v2/roles/test-role1/", 
    "users": [
      "test-login"
    ], 
    "_id": {
      "$oid": "502caa28e5e71073ae000017"
    }, 
    "id": "test-role1", 
    "permissions": {}
  }
 ]

