Installation Instructions
=========================

.. note::

    As Pulp 3 currently does not have an SELinux Policy, it currently requires the target
    machine to have SELinux set to permissive mode::

    $ sudo setenforce 0

Ansible Galaxy Installation
---------------------------

1. In order to be able to run playbook, ensure python3 and ansible (2.3.2+) are
   installed on the control node::

     $ sudo dnf install python3 ansible

   If your package manager ships an older version of Ansible, consider creating
   a venv and installing Ansible directly from PyPI::

     $ python3 -m venv env
     $ source env/bin/activate
     $ pip install ansible

2. Download ``requirements.yml`` and install Galaxy roles specified in the file::

   $ wget https://raw.githubusercontent.com/pulp/devel/3.0-dev/ansible/requirements.yml
   $ ansible-galaxy install -r requirements.yml -p ./roles

3. To install Pulp locally, download the ``deploy-pulp3.yml`` playbook and run::

   $ wget https://raw.githubusercontent.com/pulp/devel/3.0-dev/ansible/deploy-pulp3.yml
   $ ansible-playbook deploy-pulp3.yml -i localhost, -c local -K

.. note::

    To do a non-local install of Pulp, configure your Ansible
    `inventory <http://docs.ansible.com/ansible/latest/intro_inventory.html>`_
    and run::

    $  ansible-playbook deploy-pulp3.yml

4. Pulp can now be started by going to the target machine and running::

   $ sudo -u pulp -i
   $ source ~/pulpvenv/bin/activate
   $ django-admin runserver

PyPI Installation
-----------------

.. tip::

    These are the manual steps to install Pulp. There are Ansible roles that will do all
    of the following for you.

1. Install python3.5(+)::

   $ sudo dnf install python3

2. Create a pulp venv::

   $ python3 -m venv pulpvenv
   $ source pulpvenv/bin/activate

3. Install Pulp::

   $ pip3 install pulpcore

4. If the the server.yaml file isn't in the default location of `/etc/pulp/server.yaml`, set the
   PULP_SETTINGS environment variable to tell Pulp where to find you server.yaml file::

   $ export PULP_SETTINGS=pulpvenv/lib/python3.6/site-packages/pulpcore/etc/pulp/server.yaml

   .. note::

       The exact path will depend on the major *and* minor Python version found by venv e.g.
       /lib/python3.5/, /lib/python3.6/


5. Add a ``SECRET_KEY`` to your :ref:`server.yaml <server-conf>` file::

   $ echo "SECRET_KEY: '`cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50`'"

6. Tell Django which settings you're using::

   $ export DJANGO_SETTINGS_MODULE=pulpcore.app.settings

7. Go through the :ref:`database-install`, :ref:`broker-install`, and `systemd-setup` sections

8. Run Django Migrations::

   $ pulp-manager makemigrations
   $ pulp-manager migrate --noinput auth
   $ pulp-manager migrate --noinput
   $ pulp-manager reset-admin-password --password admin

9. Run Pulp::

   $ django-admin runserver

CentOS, RHEL, Fedora Installation
---------------------------------

Source Installation
-------------------

1. Install python3.5(+)::

   $ sudo dnf install python3

2. Create a pulp venv::

   $ python3 -m venv pulpvenv
   $ source pulpvenv/bin/activate

3. Install pulpcore-common, pulpcore and pulpcore-plugin::

   $ pip3 install -e "git+https://github.com/pulp/pulp.git@3.0-dev#egg=pulpcore&subdirectory=common"
   $ pip3 install -e "git+https://github.com/pulp/pulp.git@3.0-dev#egg=pulpcore&subdirectory=pulpcore"
   $ pip3 install -e "git+https://github.com/pulp/pulp.git@3.0-dev#egg=pulpcore&subdirectory=plugin"

4. If the the server.yaml file isn't in the default location of `/etc/pulp/server.yaml`, set the
   PULP_SETTINGS environment variable to tell Pulp where to find you server.yaml file::

   $ export PULP_SETTINGS=pulpvenv/src/pulpcore/pulpcore/pulpcore/etc/pulp/server.yaml

5. Add a ``SECRET_KEY`` to your :ref:`server.yaml <server-conf>` file::

   $ echo "SECRET_KEY: '`cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50`'"

6. Tell Django which settings file to use::

   $ export DJANGO_SETTINGS_MODULE=pulpcore.app.settings

7. Go through the :ref:`database-install`, :ref:`broker-install`, and `systemd-setup` sections

8. Run Django Migrations::

   $ pulp-manager makemigrations
   $ pulp-manager migrate --noinput auth
   $ pulp-manager migrate --noinput
   $ pulp-manager reset-admin-password --password admin

9. Run Pulp::

   $ django-admin runserver

.. _database-install:

Database Setup
--------------

To keep Pulp lightweight sqlite3 is the default database, but for production usage PostgreSQL is
recommended. Setup PostgreSQL and configure it in the `databases` section of your server.yaml. See
the `Django database settings documentation <https://docs.djangoproject.com/en/1.11/ref/settings/#databases>`_
for more information on setting the `databases` values in settings.yaml.

.. _broker-install:

Message Broker
--------------

.. tip::

    These are the manual steps to install the broker. There are Ansible roles that will install all
    of the following for you.

You must also provide a message broker for Pulp to use. At this time Pulp 3.0 will only work with
RabbitMQ. This can be on a different host or the same host that Pulp is running on.

RabbitMQ
^^^^^^^^

To install RabbitMQ, run this command on the host you wish to be the message broker::

   $ sudo dnf install rabbitmq-server

After installing and configuring RabbitMQ, you should configure it to start at boot and start it::

   $ sudo systemctl enable rabbitmq-server
   $ sudo systemctl start rabbitmq-server

.. _systemd-setup:

Systemd
-------

.. tip::

    These are the manual steps to create the systemd files. There are Ansible roles that will do
    the following for you.


To run the Pulp services, three systemd files needs to be created in /etc/systemd/system/. Make
sure to substitute ``Environment=PULP_SETTINGS=/path/to/pulp/server.yaml`` with the real location
of server.yaml.

``pulp_resource_manager.service``::

    [Unit]
    Description=Pulp Resource Manager
    After=network-online.target
    Wants=network-online.target

    [Service]
    # Set Environment if server.yaml is not in the default /etc/pulp/ directory
    Environment=PULP_SETTINGS=/path/to/pulp/server.yaml
    User=pulp
    WorkingDirectory=/var/run/pulp_resource_manager/
    RuntimeDirectory=pulp_resource_manager
    ExecStart=/path/to/python/bin/celery worker -A pulpcore.tasking.celery_app:celery -n resource_manager@%%h\
              -Q resource_manager -c 1 --events --umask 18\
              --pidfile=/var/run/pulp_resource_manager/resource_manager.pid

    [Install]
    WantedBy=multi-user.target


``pulp_worker@.service``::

    [Unit]
    Description=Pulp Celery Worker
    After=network-online.target
    Wants=network-online.target

    [Service]
    # Set Environment if server.yaml is not in the default /etc/pulp/ directory
    Environment=PULP_SETTINGS=/path/to/pulp/server.yaml
    User=pulp
    WorkingDirectory=/var/run/pulp_worker_%i/
    RuntimeDirectory=pulp_worker_%i
    ExecStart=/path/to/python/bin/celery worker -A pulpcore.tasking.celery_app:celery\
              -n reserved_resource_worker_%i@%%h -c 1 --events --umask 18\
              --pidfile=/var/run/pulp_worker_%i/reserved_resource_worker_%i.pid

    [Install]
    WantedBy=multi-user.target

These services can then be started by running::

    sudo systemctl start pulp_resource_manager
    sudo systemctl start pulp_worker@1
    sudo systemctl start pulp_worker@2

