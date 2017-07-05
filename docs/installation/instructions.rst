Installation Instructions
=========================

Ansible
-------

PyPI
----

.. tip::

    These are the manual steps to install Pulp. There are Ansible roles that will do all
    of the following for you.

1. Install python3.5 and virtualenv::

   $ sudo dnf install python3
   $ sudo pip3 install virtualenv

2. Create a pulp virtualenv::

   $ virtualenv pulp -p python3
   $ source pulp/bin/activate

3. Install Pulp::

   $ pip3 install pulpcore

4. Move the example server.yaml file from
   ``{virtualenv}/lib/python3.5/site-packages/pulpcore/etc/pulp/server.yaml``
   to ``/etc/pulp/server.yaml``.

5. Add a ``SECRET_KEY`` to your :ref:`server.yaml <server-conf>` file

6. Tell Django which settings you're using::

   $ export DJANGO_SETTINGS_MODULE=pulpcore.app.settings

7. Go through the  :ref:`database-install` and :ref:`broker-install` sections

8. Run Django Migrations::

   $ django-admin migrate --noinput auth
   $ django-admin migrate --noinput
   $ django-admin reset-admin-password --password admin

9. Run Pulp::

   $ django-admin runserver

CentOS, RHEL, Fedora
--------------------

Source
------

.. _database-install:

Database
--------

.. tip::

    These are the manual steps to install the database. There are Ansible roles that will do all
    of the following for you.

You must provide a running Postgres instance for Pulp to use. You can use the same host that you
will run Pulp on, or you can give Postgres its own separate host if you like::

   $ sudo dnf install postgresql postgresql-server python3-psycopg2
   $ sudo postgresql-setup --initdb /var/lib/pgsql/data/base

After installing Postgres, you should configure it to start at boot and start it::

   $ sudo systemctl enable postgresql
   $ sudo systemctl start postgresql

Initialize the pulp database::

   $ sudo -u postgres -i bash
   $ createuser --username=postgres -d -l pulp
   $ createdb --owner=pulp --username=postgres pulp

Don't forget to update your `/var/lib/pgsql/data/pg_hba.conf
<https://www.postgresql.org/docs/9.1/static/auth-pg-hba-conf.html>`_ file, to grant an appropriate
level of database access.

Restart Postgres after updating ``pg_hba.conf``::

   $ sudo systemctl restart postgresql

.. _broker-install:

Message Broker
--------------

.. tip::

    These are the manual steps to install the broker. There are Ansible roles that will install all
    of the following for you.

You must also provide a message broker for Pulp to use. Pulp will work with Qpid or RabbitMQ.
This can be on a different host or the same host that Pulp is running on.


qpidd
^^^^^

To install qpidd, run this command on the host you wish to be the message broker::

   $ sudo dnf install qpid-cpp-server qpid-cpp-server-linearstore

After installing and configuring Qpid, you should configure it to start at boot and start it::

   $ sudo systemctl enable qpidd
   $ sudo systemctl start qpidd


RabbitMQ
^^^^^^^^

To install RabbitMQ, run this command on the host you wish to be the message broker::

   $ sudo dnf install rabbitmq-server

After installing and configuring RabbitMQ, you should configure it to start at boot and start it::

   $ sudo systemctl enable rabbitmq-server
   $ sudo systemctl start rabbitmq-server

