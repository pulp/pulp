Retrieval
=========

Retrieve a Single User
--------------------------

Retrieves information on a single Pulp user. The returned data includes
general user details.

| :method:`get`
| :path:`/v2/users/<user_login>/`
| :permission:`read`
| :param_list:`get`

| :response_list:`_`

* :response_code:`200,if the user exists`
* :response_code:`404,if no user exists with the given ID`

| :return:`database representation of the matching user excluding user password`

:sample_response:`200` ::

 {
  "name": "admin", 
  "roles": [
    "super-users"
  ], 
  "_ns": "users", 
  "login": "admin", 
  "_id": {
    "$oid": "502c47ace5e7100b0a000008"
  }, 
  "id": "502c47ace5e7100b0a000008", 
  "_href": "/pulp/api/v2/users/admin/"
 } 



Retrieve All Users
----------------------

Returns information on all users in the Pulp server. An empty array is returned in the case
where there are no users.

| :method:`get`
| :path:`/v2/users/`
| :permission:`read`
| :param_list:`get`

| :response_list:`_`

* :response_code:`200,containing the array of users`

| :return:`the same format as retrieving a single user, except the base of the return value is an array of them`

:sample_response:`200` ::

 [
  {
    "name": "admin", 
    "roles": [
      "super-users"
    ], 
    "_ns": "users", 
    "login": "admin", 
    "_id": {
      "$oid": "502c47ace5e7100b0a000008"
    }, 
    "id": "502c47ace5e7100b0a000008", 
    "_href": "/pulp/api/v2/users/admin/"
  }, 
  {
    "name": "test name", 
    "roles": [], 
    "_ns": "users", 
    "login": "test-login", 
    "_id": {
      "$oid": "502c8c08e5e7100b0a000049"
    }, 
    "id": "502c8c08e5e7100b0a000049", 
    "_href": "/pulp/api/v2/users/test-login/"
  }
 ]
 

Advanced Search for Users
--------------------------------

Please see :ref:`search_api` for more details on how to perform these searches.
