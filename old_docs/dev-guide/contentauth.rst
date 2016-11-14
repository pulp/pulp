.. _content_auth_mechanisms:

Content Authentication Mechanisms
=================================

Pulp allows administrators to require users to authenticate in order to receive
content. Typically this is done by checking an SSL client certificate.

Content authentication is primarly done in conjunction with a Katello instance
and is outside the scope of this document. However, users may want to add their
own authentication methods. This is done by writing a method that returns
either True or False depending on if the user is allowed access and then
telling Pulp about this method via Python entry points.

Note that **all** authenticators must return True in order to let the request
through. Authentication is typically based on the contents of the ``environ``
parameter. This is a dictionary containing various environment variables from
Apache. When authoring plugins, it may be helpful to log the contents of
``environ`` to see what is being passed in.

For example, if you wanted to create a simple method that let everyone through
but logged a message, you could do something like this:

::
    def authenticate(environ):
        print "No checking here, just let the user through!"
        return True

Then, tell Pulp about this via an entry point in ``setup.py``. In this example,
our ``authenticate()`` method lives in ``example_auth.example``.

::

    entry_points={
        'pulp_content_authenticators': [
            'example_auth=example_auth.example:authenticate'
        ]
    }

You should be all set at this point. Simply make a request and check
``/var/log/httpd/error_log`` to see if the message printed. Your request will
need to pass all auth checks to see the log message; once one check fails then
the rest are not executed. If the ``authenticate`` method raises an exception
for any reason then mod_wsgi will write a message to ``ssl_error_log`` and deny
the request.

If you would like to disable a specific plugin, simply set
``disabled_authenticators`` in ``/etc/pulp/repo_auth.conf`` to the name of the
authenticator in the entry point. In the example above, we would set it to
``example_auth``. Multiple entries can be given via comma-seperated values.
