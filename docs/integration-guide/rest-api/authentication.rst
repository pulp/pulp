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
  * Firefox `Modify Header Value <https://addons.mozilla.org/en-US/firefox/addon/modify-header-value/>`_

Basic Authentication
--------------------

Any call to the REST API may use
`HTTP basic authentication <http://tools.ietf.org/html/rfc1945#section-11.1>`_ to provide
a username and password.
