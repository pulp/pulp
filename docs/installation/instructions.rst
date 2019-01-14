Installation Instructions
=========================

Supported Platforms
-------------------

Pulp should work on any operating system that can provide a Python 3.6+ runtime environment and
the supporting dependencies e.g. a database. Pulp has been demonstrated to work on Ubuntu, Debian,
Fedora, CentOS, and Mac OSX.

.. note::

    As Pulp 3 currently does not have an SELinux Policy, it currently requires the target
    machine to have SELinux set to permissive mode or disabled. If you are not sure if the system is
    capable or is currently running SELinux run the following command::

    $ getenforce

    If the command is not found or the return status is "Permissive" or "Disabled" then skip to step
    1. If the return of the command is "Enforcing" then this next command should be applied::

    $ sudo setenforce 0

Ansible Installation
--------------------

To use ansible roles to install Pulp 3 instead of manual setup refer to
`Pulp 3 Ansible installer <https://github.com/pulp/ansible-pulp3/>`_.

PyPI Installation
-----------------

1. Install python3.6(+) and pip.

2. Create a pulp venv::

   $ python3 -m venv pulpvenv
   $ source pulpvenv/bin/activate

.. note::

   On some operating systems you may need to install a package which provides the ``venv`` module.
   For example, on Ubuntu or Debian you need to run::

   $ sudo apt-get install python3-venv

3. Install Pulp::

   $ pip install pulpcore

.. note::

   To install from source, clone the git repository, navigate to the directory containing the
   ``setup.py`` file, and do a local, editable pip installation::

   $ git clone https://github.com/pulp/pulp.git
   $ cd pulp/
   $ pip install -e pulpcore/
   $ pip install -e common/
   $ pip install -e plugin/


4. Follow the :ref:`configuration instructions <configuration>` to set the ``SECRET_KEY``.

5. Go through the :ref:`database-install`, :ref:`redis-install`, and :ref:`systemd-setup` sections

.. note::

    In place of using the systemd unit files provided in the `systemd-setup` section, you can run
    the commands yourself inside of a shell. This is fine for development but not recommended in production::

    $ /path/to/python/bin/rq worker -n 'resource_manager@%h' -w 'pulpcore.tasking.worker.PulpWorker'
    $ /path/to/python/bin/rq worker -n 'reserved_resource_worker_1@%h' -w 'pulpcore.tasking.worker.PulpWorker'
    $ /path/to/python/bin/rq worker -n 'reserved_resource_worker_2@%h' -w 'pulpcore.tasking.worker.PulpWorker'

8. Run Django Migrations::

   $ pulp-manager migrate --noinput
   $ pulp-manager reset-admin-password --password admin

9. Collect Static Media for live docs and browsable API

   $ pulp-manager collectstatic --noinput

10. Run Pulp:
::

   $ django-admin runserver


.. _database-install:

Database Setup
--------------

You must provide a compatible SQL database for Pulp to use. At this time Pulp 3.0 is only known to work
properly with PostgreSQL. It may work with other databases that Django supports, but no guarantees.

PostgreSQL
^^^^^^^^^^

To install PostgreSQL, refer to the package manager or the
`PostgreSQL install docs <http://postgresguide.com/setup/install.html>`_. Oftentimes you can also find better
installation instructions for your particular operating system from third-parties such as Digital Ocean.

On Ubuntu and Debian, the package to install is named ``postgresql``. On Fedora and CentOS, the package
is named ``postgresql-server``.

The default PostgreSQL user and database name in the provided server.yaml file is ``pulp``. Unless you plan to
customize the configuration of your Pulp installation, you will need to create this user with the proper permissions
and also create the ``pulp`` database owned by the ``pulp`` user. If you do choose to customize your installation,
the database options can be configured in the `DATABASES` section of your server.yaml settings file.
See the `Django database settings documentation <https://docs.djangoproject.com/en/1.11/ref/settings/#databases>`_
for more information on setting the `DATABASES` values in server.yaml.

After installing and configuring PostgreSQL, you should configure it to start at boot, and then start it::

   $ sudo systemctl enable postgresql
   $ sudo systemctl start postgresql

.. _redis-install:

Redis
-----

The Pulp tasking system runs on top of Redis. This can be on a different host or the same host that
Pulp is running on.

To install Redis, refer to your package manager or the
`Redis download docs <https://redis.io/download>`_.

For Fedora, CentOS, Debian, and Ubuntu, the package to install is named ``redis``.

After installing and configuring Redis, you should configure it to start at boot and start it::

   $ sudo systemctl enable redis
   $ sudo systemctl start redis

.. _systemd-setup:

Systemd
-------

To run the Pulp services, three systemd files needs to be created in /etc/systemd/system/. Make
sure to substitute ``Environment=PULP_SETTINGS=/path/to/pulp/server.yaml`` with the real location
of :ref:`configuration file <configuration>`.

``pulp_resource_manager.service``::

    [Unit]
    Description=Pulp Resource Manager
    After=network-online.target
    Wants=network-online.target

    [Service]
    # Set Environment if server.yaml is not in the default /etc/pulp/ directory
    Environment=PULP_SETTINGS=/path/to/pulp/server.yaml
    Environment="DJANGO_SETTINGS_MODULE=pulpcore.app.settings"
    User=pulp
    WorkingDirectory=/var/run/pulp_resource_manager/
    RuntimeDirectory=pulp_resource_manager
    ExecStart=/path/to/python/bin/rq worker -n resource_manager@%%h\
              -w 'pulpcore.tasking.worker.PulpWorker'\
              -c 'pulpcore.rqconfig'\
              --pid=/var/run/pulp_resource_manager/resource_manager.pid

    [Install]
    WantedBy=multi-user.target


``pulp_worker@.service``::

    [Unit]
    Description=Pulp Worker
    After=network-online.target
    Wants=network-online.target

    [Service]
    # Set Environment if server.yaml is not in the default /etc/pulp/ directory
    Environment=PULP_SETTINGS=/path/to/pulp/server.yaml
    Environment="DJANGO_SETTINGS_MODULE=pulpcore.app.settings"
    User=pulp
    WorkingDirectory=/var/run/pulp_worker_%i/
    RuntimeDirectory=pulp_worker_%i
    ExecStart=/path/to/python/bin/rq worker -w 'pulpcore.tasking.worker.PulpWorker'\
              -n reserved_resource_worker_%i@%%h\
              -c 'pulpcore.rqconfig'\
              --pid=/var/run/pulp_worker_%i/reserved_resource_worker_%i.pid

    [Install]
    WantedBy=multi-user.target

These services can then be started by running::

    sudo systemctl start pulp_resource_manager
    sudo systemctl start pulp_worker@1
    sudo systemctl start pulp_worker@2

