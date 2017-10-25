Authentication
==============

All calls to REST API endpoints must be authenticated as a particular User.

.. tip::
  The password for the "admin" user can be set using two methods.

      ``pulp-manager reset-admin-password``

  The above command prompts the user to enter a new password for "admin" user.

      ``pulp-manager reset-admin-password --random``

  The above command generates a random password for "admin" user and prints it to the screen.

.. tip::
  If you are using django rest framework browsable API these browser addons may come handy:

  * Chrome `ModHeader <https://chrome.google.com/webstore/detail/modheader/idgpnmonknjnojddfkpgkljpfnnfcklj>`_
  * Firefox `Modify Headers <https://addons.mozilla.org/cs/firefox/addon/modify-headers/>`_

Basic Authentication
--------------------

Any call to the REST API may use
`HTTP basic authentication <http://tools.ietf.org/html/rfc1945#section-11.1>`_ to provide
a username and password.

JWT Authentication
------------------

Alternatively you can use `JSON Web Tokens authentication <https://tools.ietf.org/html/rfc7519>`_.

Token Structure
^^^^^^^^^^^^^^^

The structure of the token consists of ``username`` and ``exp``. The tokens are signed by each
user's individual secret by HMAC SHA-256 ("HS256") algorithm.

Example:
::
    {
      "username": "admin",
      "exp": 1501172472
    }

Obtaining token from server
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can "login" to Pulp by supplying your credentials in POST request and obtain a JWT token
with expiration time set by ``JWT_AUTH.JWT_EXPIRATION_DELTA``


 * **method:** ``post``
 * **path:** ``api/v3/jwt/``
 * response list:
    * **code:** ``200`` - credentials were accepted
    * **code:** ``400`` - credentials are wrong

 **Sample POST request:**
 ::
  {
    "username": "admin",
    "password": "admin_password"
  }


 **Sample 200 Response Body:**
 ::
    {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwiZXhwIjoxNTAyMzgzMDExfQ.3ZpcclxV6hN8ui2HUbwXLJsHl2lhesiCPeDVV2GIbJg"
    }

Using a token
^^^^^^^^^^^^^

For using JWT tokens you have to set ``Authorization`` header as follows:
::
  Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwiZXhwIjoxNTAyMzgzMDExfQ.3ZpcclxV6hN8ui2HUbwXLJsHl2lhesiCPeDVV2GIbJg

User secret
^^^^^^^^^^^

To achieve ability to invalidate all user's tokens each user have their own secret key which is
used to sign their tokens. The change of the secret will lead to invalidation of all user's
tokens. The change is independent on password.

You can reset user secret to random by calling the jwt reset endpoint:


 * **method:** ``post``
 * **path:** ``api/v3/users/<username>/jwt_reset/``
 * response list:
    * **code:** ``200`` - jwt reset
    * **code:** ``400`` - invalid credentials

If you have enabled ``JWT_AUTH.JWT_ALLOW_SETTING_USER_SECRET`` you can set the user's secret
via user API endpoint.

The secret is stored in User model in field ``jwt_secret``.

Offline token generation
^^^^^^^^^^^^^^^^^^^^^^^^

If you have enabled ``JWT_AUTH.JWT_ALLOW_SETTING_USER_SECRET`` users can set their secrets and
therefore are able to generate tokens offline.

If you have pulpcore installed in your environment you can do the following:

.. code-block:: python

   from datetime import timedelta

   from pulpcore.app.auth.jwt_utils import generate_token_offline

   username = "admin"
   jwt_secret = "admin_token_secret"
   exp_delta = timedelta(days=7)  # This value is optional, default 14 days
   token = generate_token_offline(username, jwt_secret, exp_delta)

If not you can implement the above function like this:

.. code-block:: python

   import jwt  # pip install pyjwt
   from datetime import datetime, timedelta


   def generate_token_offline(username, jwt_secret, exp_delta=timedelta(days=14)):
       """
         Generate JWT token for pulp offline from username and secret.

         This function can be used for JWT token generation on client without
         the need of connection to pulp server. The only things you need to
         know are `username` and `jwt_secret`.

         Args:
             username (str): username
             jwt_secret (str): User's JWT token secret
             exp_delta (datetime.timedelta, optional):
                 Token expiration time delta. This will be added to
                 `datetime.utcnow()` to set the expiration time.
                 If not set default 14 days is used.

         Returns:
             str: JWT token

       """
       return jwt.encode(
           {
               'username': username,
               'exp': datetime.utcnow() + exp_delta
           },
           jwt_secret,
           'HS256',
       ).decode("utf-8")

.. warning::
  When tokens are generated on client. The client can set **ANY** expiration time they want
  no matter what is set in ``JWT_EXPIRATION_DELTA``.
