==================
Installation Guide
==================

PyPI
----

CentOS, RHEL, Fedora
--------------------

Source
------


Configuration Files
-------------------

Pulp's server configuration file is located at `/etc/pulp/server.yaml`

SECRET_KEY
    In order to get a pulp server up and running a `Django SECRET_KEY
    <https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-SECRET_KEY>`_ must be
    provided in server.yaml.

    The following code snippet can be used to generate a random SECRET_KEY

.. code-block:: python
   :linenos:

   import random;

   chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
   print(''.join(random.choice(chars) for i in range(50)))

