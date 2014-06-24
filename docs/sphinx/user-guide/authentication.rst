Authentication
==============

Default
-------

By default, pulp authenticates each request with a username and password against
its own user database. Requests can also authenticate with a client-side SSL
certificate that was provided by pulp's login feature.

Apache Preauthentication
------------------------

If other forms of authentication are desired, authentication can be
delegated to apache, which comes with a variety of authentication plugins that
are well-documented and feature-rich. In order for users to then be authorized
for any operation, they must have already been added to the Pulp user database
using the ``pulp-admin auth user`` commands.

Once an apache authorization module is configured, pulp will read and trust the
``REMOTE_USER`` variable from apache.

.. note:

    Enabling apache preauthentication as described below *disables* authorization
    against the built-in user database, so you will not be able to authenticate
    as ``admin`` after you have enabled it. It's important that you configure a
    user in the ``super-users`` role *before* you enable apache
    preauthentication. Pulp's native (and deprecated) LDAP authentication is
    also disabled; OAuth will continue to work.

Pulp's apache config file (``/etc/httpd/conf.d/pulp.conf``) contains an example
of how to configure an apahce auth module. The examples below demonstrate two
different approaches.

LDAP Whole-API Example
~~~~~~~~~~~~~~~~~~~~~~

To set up apache authentication for the entire REST API, modify the ``<Files
webservices.wsgi>`` stanza in ``/etc/httpd/conf.d/pulp.conf`` to resemble the
following::

    <Files webservices.wsgi>
        # pass everything that isn't a Basic auth request through to Pulp
        SetEnvIfNoCase ^Authorization$ "Basic.*" USE_APACHE_AUTH=1
        Order allow,deny
        Allow from env=!USE_APACHE_AUTH
        Satisfy Any

        # configure basic auth
        AuthType basic
        AuthBasicProvider ldap
        AuthName "Pulp"
        AuthLDAPURL "ldaps://ad.example.com?sAMAccountName"
        AuthLDAPBindDN "cn=pulp,..."
        AuthLDAPBindPassword "adpassword"
        AuthLDAPRemoteUserAttribute sAMAccountName
        AuthzLDAPAuthoritative On
        Require valid-user

        # Standard Pulp REST API configuration goes here...
    </Files>

Note that this *requires* LDAP authentication for the initial login,
and *allows* either LDAP or Pulp certificate authentication on the
entire API.

Basic Auth Login Example
~~~~~~~~~~~~~~~~~~~~~~~~

Many deployments will only use a third-party authentication source for the login
call, and then use pulp's certificate-based auth for successive calls.

You are responsible for ensuring that a user gets created in pulp prior to
any login attempt. Pulp does not support auto-creation of users that exist in
your external source.

Below is a "basic" example that works for demos, but a stronger mechanism is
recommended.

::

    <Location /pulp/api/v2/actions/login>
        AuthType Basic
        AuthName "Pulp Login"
        AuthUserFile /var/lib/pulp/.htaccess
        Require valid-user
    </Location>

For this basic-auth example, the ``.htaccess`` file must then be created using
the ``htpasswd`` command.

Note that this *requires* Apache authentication for the initial login,
and also *requires* Pulp certificate authentication on the entire API.

LDAP
----

.. deprecated:: 2.4
   Please use apache's mod_authnz_ldap to provide preauthentication
   per instructions above.

Pulp supports LDAP authentication by configuring the ``[ldap]``
section in ``server.conf``.  An LDAP user who logs in for the first
time will have a local account automatically created in the Pulp
database.

The following options are supported:

* ``enabled``: Boolean; controls whether or not LDAP authentication is
  enabled. Default: false.
* ``uri``: URL of LDAP server. Default: ``ldap://localhost``
* ``base``: Location in the directory from which the LDAP search
  begins. Default: ``dc=localhost``
* ``tls``: Boolean; controls whether or not to use TLS security.
  Default: false.
* ``default_role``: Role ID to assign LDAP users to by default. This
  role must first be created on the Pulp server. If ``default_role``
  is not set or doesn't exist, LDAP users are given same default
  permissions as local users.
* ``filter``: LDAP filter to limit the LDAP users who can authenticate
  to Pulp.

For example:

.. code-block:: ini

    [ldap]
    enabled = true
    uri = ldap://ldap.example.com
    base = ou=People,dc=example,dc=com
    tls = true
    default_role = ldap-users
    filter = (gidNumber=200)

.. _oauth-config:

OAuth
-----

.. deprecated:: 2.4.0

    OAuth support will be removed in a future release of Pulp. Please do not write new code that
    uses OAuth against Pulp, and please find a suitable replacement if you are already using it.

`OAuth <http://oauth.net/>`_ can be enabled by configuring the
``[oauth]`` section in ``server.conf``.  In order for a user or
consumer to authenticate via OAuth, they must have already been added
to the Pulp user database with the ``pulp-admin auth user`` commands.
The following options are supported:

* ``enabled``: Boolean; controls whether OAuth authentication is
  enabled. Default: false
* ``oauth_key``: Key to enable OAuth style authentication.  Required.
* ``oauth_secret``: Shared secret that can be used for OAuth style
  authentication. Please be sure to choose a secret that is long enough for your desired level of
  security. Required.

For example:

.. code-block:: ini

    [oauth]
    enabled = true
    oauth_key = ab3cd9j4ks73hf7g
    oauth_secret = xyz4992k83j47x0bBoo8fue3yohneepo

.. warning::

   Do not use the key or secret given in the above example. It is important that you use unique and
   secret values for these configuration items.
