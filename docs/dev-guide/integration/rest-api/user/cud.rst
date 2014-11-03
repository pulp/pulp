Create, Update, and Delete
================================

Create a User
-------------------

Create a new user. User logins must be unique across all users.

| :method:`post`
| :path:`/v2/users/`
| :permission:`create`
| :param_list:`post`

* :param:`login,string,unique login for the user`
* :param:`?name,string,name of the user`
* :param:`?password,string,password of the user used for authentication`

| :response_list:`_`

* :response_code:`201,if the user was successfully created`
* :response_code:`400,if one or more of the parameters is invalid`
* :response_code:`409,if there is already a user with the given login`

| :return:`details of created user`

:sample_request:`_` ::

 {
  "login": "test-login",
  "password": "test-password",
  "name": "test name"
 }


:sample_response:`201` ::

 {
  "name": "test name", 
  "roles": [], 
  "_ns": "users", 
  "login": "test-login", 
  "_id": {
    "$oid": "502c83f6e5e7100b0a000035"
  }, 
  "id": "502c83f6e5e7100b0a000035", 
  "_href": "/pulp/api/v2/users/test-login/"
 }


Update a User
-----------------

The update user call is used to change the details of an existing consumer.

| :method:`put`
| :path:`/v2/users/<user_login>/`
| :permission:`update`
| :param_list:`put` The body of the request is a JSON document with a root element
  called ``delta``. The contents of delta are the values to update. Only changed
  parameters need be specified. The following keys are allowed in the delta
  object. Descriptions for each parameter can be found under the create
  user API:

* :param:`password,,`
* :param:`name,,`
* :param:`?roles,array,array of roles to update the user to. In this case, relevant permissions for the user will be updated as well.`

| :response_list:`_`

* :response_code:`200,if the update was executed and successful`
* :response_code:`404,if there is no user with the given login`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`database representation of the user including changes made by the update`

:sample_request:`_` ::

 {
  "delta": {"name": "new name", "password": "new-password"}
 }

:sample_response:`200` ::

 {
  "name": "new name", 
  "roles": [], 
  "_ns": "users", 
  "login": "test-login", 
  "_id": {
    "$oid": "502c83f6e5e7100b0a000035"
  }, 
  "id": "502c83f6e5e7100b0a000035"
 }

Delete a User
---------------------

Deletes a user from the Pulp server. Permissions granted to the user are revoked as well. 

| :method:`delete`
| :path:`/v2/users/<user_login>/`
| :permission:`delete`
| :param_list:`delete`
| :response_list:`_`

* :response_code:`200,if the user was successfully deleted`
* :response_code:`404,if there is no user with the given login`

| :return:`null`
