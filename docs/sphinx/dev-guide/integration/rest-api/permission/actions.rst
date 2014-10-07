Grant/Revoke permissions from User or Role
==========================================

Grant to user
-------------

Grants permissions to a user.

| :method:`post`
| :path:`/v2/permissions/actions/grant_to_user/`
| :permission:`execute`
| :param_list:`post`

* :param:`login,string,login of existing user`
* :param:`resource,string,resource URI`
* :param:`operations,array,array of operation strings;valid operations:'CREATE','READ','UPDATE','DELETE','EXECUTE'`

| :response_list:`_`

* :response_code:`200,if permissions were successfully granted to the user`
* :response_code:`404,if any of the parameters are invalid`

| :return:`null`

:sample_request:`_` ::

 {
  "operations": ["CREATE", "READ", "DELETE"], 
  "login": "test-login", 
  "resource": "/v2/repositories/"
 }


Revoke from user
----------------

Revokes permissions from a user.

| :method:`post`
| :path:`/v2/permissions/actions/revoke_from_user/`
| :permission:`execute`
| :param_list:`post`

* :param:`login,string,login of existing user`
* :param:`resource,string,resource URI`
* :param:`operations,array,array of operation strings;valid operations:'CREATE','READ','UPDATE','DELETE','EXECUTE'`

| :response_list:`_`

* :response_code:`200,if permissions were successfully revoked from the user`
* :response_code:`404,if any of the parameters are invalid`

| :return:`null`

:sample_request:`_` ::

 {
  "operations": ["CREATE", "DELETE"], 
  "login": "test-login", 
  "resource": "/v2/repositories/"
 }


Grant to role
-------------

Grants permissions to a role. This will add permissions to all users belonging to the role.
Note that users added to the role after granting permissions will inherit these permissions from the role as well.

| :method:`post`
| :path:`/v2/permissions/actions/grant_to_role/`
| :permission:`execute`
| :param_list:`post`

* :param:`role_id,string,id of an existing role`
* :param:`resource,string,resource URI`
* :param:`operations,array,array of operation strings;valid operations:'CREATE','READ','UPDATE','DELETE','EXECUTE'`

| :response_list:`_`

* :response_code:`200,if permissions were successfully granted to the role`
* :response_code:`404,if any of the parameters are invalid`

| :return:`null`

:sample_request:`_` ::

 {
  "operations": ["CREATE", "READ", "DELETE"], 
  "resource": "/v2/repositories/", 
  "role_id": "test-role"
 }


Revoke from role
----------------

Revokes permissions from a role. This will revoke permissions from all users belonging to the role unless they are 
granted by other roles as well. 

| :method:`post`
| :path:`/v2/permissions/actions/revoke_from_role/`
| :permission:`execute`
| :param_list:`post`

* :param:`role_id,string,id of an existing role`
* :param:`resource,string,resource URI`
* :param:`operations,array,array of operation strings;valid operations:'CREATE','READ','UPDATE','DELETE','EXECUTE'`

| :response_list:`_`

* :response_code:`200,if permissions were successfully revoked from the role`
* :response_code:`404,if any of the parameters are invalid`

| :return:`null`

:sample_request:`_` ::

 {
  "operations": ["CREATE", "READ", "DELETE"], 
  "resource": "/v2/repositories/", 
  "role_id": "test-role"
 }




