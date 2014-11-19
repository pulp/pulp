Create, Update, and Delete
==========================

Create a Role
-------------

Create a new role. Role id must be unique across all roles.

| :method:`post`
| :path:`/v2/roles/`
| :permission:`create`
| :param_list:`post`

* :param:`role_id,string,unique id for the role`
* :param:`?display_name,string,user-friendly name for the role`
* :param:`?description,string,user-friendly text describing the role`

| :response_list:`_`

* :response_code:`201,if the role was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a role with the given id`

| :return:`details of created role`

:sample_request:`_` ::

 {
  "display_name": "Role Test", 
  "description": "Demo Role", 
  "role_id": "role-test"
 }


:sample_response:`201` ::

 {
  "display_name": "Role Test", 
  "description": "Demo Role", 
  "_ns": "roles", 
  "_href": "/pulp/api/v2/roles/role-test/", 
  "_id": {
    "$oid": "502cb2d7e5e710772d000049"
  }, 
  "id": "role-test", 
  "permissions": {}
 }


Update a Role
-------------

The update role call is used to change the details of an existing role.

| :method:`put`
| :path:`/v2/roles/<role_id>/`
| :permission:`update`
| :param_list:`put` The body of the request is a JSON document with a root element
  called ``delta``. The contents of delta are the values to update. Only changed
  parameters need be specified. The following keys are allowed in the delta
  object.

* :param:`?display_name,string,user-friendly name for the role`
* :param:`?description,string,user-friendly text describing the role`
* :param:`?permissions,object, key-array pairs of resource to permissions`

| :response_list:`_`

* :response_code:`200,if the update was executed and successful`
* :response_code:`404,if there is no role with the given id`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`database representation of the role including changes made by the update`

:sample_request:`_` ::


 {
  "delta": {
    "display_name": "New Role Test",
    "description": "New Demo Role",
    "permissions": {"/v2/roles/": ["CREATE"]}
  }
 }

:sample_response:`200` ::

 {
  "display_name": "New Role Test", 
  "description": "New Demo Role", 
  "_ns": "roles", 
  "_href": "/pulp/api/v2/roles/role-test/", 
  "_id": {
    "$oid": "502cb2d7e5e710772d000049"
  }, 
  "id": "role-test", 
  "permissions": {"/v2/roles/": ["CREATE"]}
 }

Delete a Role
-------------

Deletes a role from the Pulp server. Users bindings are removed from the role 
and permissions granted to the users because of the role are revoked as well unless
those permissions are granted by other role as well. 

| :method:`delete`
| :path:`/v2/roles/<role_id>/`
| :permission:`delete`
| :param_list:`delete`
| :response_list:`_`

* :response_code:`200,if the role was successfully deleted`
* :response_code:`404,if there is no role with the given id`

| :return:`null`


Add a User to a Role
--------------------

Add a user to an existing role. Note that user with given login is NOT created as part of this operation. 
User with a given login should already exist.

| :method:`post`
| :path:`/v2/roles/<role_id>/users/`
| :permission:`update`
| :param_list:`post`

* :param:`login,string,login of the user to be added to the role`

| :response_list:`_`

* :response_code:`200,if the user was successfully added`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`404,if there is no role with the given id`

| :return:`null`

:sample_request:`_` ::

 {
  "login": "test-login"
 }



Remove a User from a Role
-------------------------

Removes a user from an existing role. 

| :method:`delete`
| :path:`/v2/roles/<role_id>/users/<user_login>/`
| :permission:`delete`
| :param_list:`post`

| :response_list:`_`

* :response_code:`200,if the user was successfully deleted`
* :response_code:`404,if there is no role with the given id`

| :return:`null`


