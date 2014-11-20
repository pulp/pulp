
.. _DevSetup:

Developer Setup
===============

For the Impatient
^^^^^^^^^^^^^^^^^

These instructions will create a developer install of Pulp on a dedicated
development instance.

* Start a Fedora 20 x86_64 instance that will be dedicated for development with
  at least 2GB of memory and 10GB of disk space. More disk space is needed if
  you plan on syncing larger repos for test purposes.

* If one does not already exist, create a non-root user on that instance with
  sudo access. If you are using a Fedora cloud image, the "fedora" user is
  sufficient.

* As that user, ``curl https://raw.githubusercontent.com/pulp/pulp/master/playpen/dev-setup.sh | bash``.
  Note that this installs RPMs and makes system modifications that you wouldn't
  want to apply on a VM that was not dedicated to Pulp development.

* While it runs, read the rest of this document! It details what the quickstart
  script does and gives background information on the development
  process.

Source Code
^^^^^^^^^^^

Pulp's code is stored on `GitHub <http://www.github.com/pulp>`_. The repositories should be forked
into your personal GitHub account where all work will be done. Changes are
submitted to the Pulp team through the pull request process outlined in :doc:`merging`.


Follow the instructions on
that site for checking out each repository with the appropriate level of access (Read+Write v.
Read-Only). In most cases, Read-Only will be sufficient; contributions will be done through
pull requests into the Pulp repositories as described in :doc:`merging`.

Dependencies
^^^^^^^^^^^^

The easiest way to download the other dependencies is to install Pulp through yum, which will pull in
the latest dependencies according to the spec file.

#. Download the appropriate repository to at: http://repos.fedorapeople.org/repos/pulp/pulp/

   Example for Fedora::

       $ cd /etc/yum.repos.d/
       $ sudo wget https://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo

#. Edit the repo and enable the most recent testing repository.
#. Install the main Pulp groups to get all of the dependencies.
   ``$ sudo yum install @pulp-server-qpid @pulp-admin @pulp-consumer``
#. Remove the installed Pulp RPMs; these will be replaced with running directly from the checked
   out code. ``$ sudo yum remove pulp-\* python-pulp\*``

#. Install some additional dependencies for development::
   
   $ sudo yum install python-setuptools redhat-lsb mongodb mongodb-server \
          qpid-cpp-server qpid-cpp-server-store python-qpid-qmf python-nose \
          python-mock python-paste python-pip

The only caveat to this approach is that these dependencies will need to be maintained after this
initial setup. Leaving the testing builds repository enabled will cause them to be automatically
updated on subsequent ``yum update`` calls. Messages are sent to the Pulp mailing list when these
dependencies are updated as well to serve as a reminder to update before the next code update.

Installation
^^^^^^^^^^^^

Pulp can be installed to run directly from the checked out code base through ``setup.py`` scripts.
Running these scripts requires the ``python-setuptools`` package to be installed. Additionally,
it is also recommended to install ``python-pip`` for access to additional setup-related features.

This method of installation links the git repositories as the locally deployed libraries and scripts.
Any changes made in the working copy will be immediately deployed in the site-packages libraries
and installed scripts. Setup scripts are automatically run for you by ``pulp-dev.py``.

.. note::
  Not all Pulp projects need to be installed in this fashion. When working on a new plugin,
  the Pulp platform can continue to be run from the RPM installation and the pulp_rpm and
  pulp_puppet plugins would not be required.

Additionally, Pulp specific files such as configuration and package directories must be linked to
the checked out code base. These additions are performed by the ``pulp-dev.py`` script located in the
root of each git repository. The full command is::

  $ sudo python ./pulp-dev.py -I

Uninstallation
^^^^^^^^^^^^^^

The ``pulp-dev.py`` script has an uninstall option that will remove the symlinks from the system
into the local source directory, as well as the Python packages. It is run using the ``-U`` flag:

::

 $ sudo python ./pulp-dev.py -U

Permissions
^^^^^^^^^^^

The ``pulp-dev.py`` script links Pulp's WSGI application into the checked out code base. In many
cases, Apache will not have the required permissions to serve the applications (for instance,
if the code is checked out into a user's home directory).

One solution, if your system supports it, is to use ACLs to grant Apache the required permissions.

For example, assuming the Pulp source was checked out to ``~/code/pulp``, the following series of
commands would grant Apache the required access:

::

 $ cd $HOME
 $ setfacl -m user:apache:rwx .
 $ cd code
 $ setfacl -m user:apache:rwx .
 $ cd pulp
 $ setfacl -m user:apache:rwx .


SELinux
^^^^^^^

Unfortunately, when developing Pulp SELinux needs to be disabled or run in Permissive mode. Most
development environments will be created with ``pulp-dev.py``, which deploys Pulp onto the system
differently than a rpm based install. The SELinux policy of Pulp expects an RPM layout, and if
SELinux is run in Enforcing mode your development to not function correctly.

To turn off SELinux, you can use ``sudo setenforce 0`` which will set SELinux to permissive. By default, SELinux will be enabled on the next restart so make the change persistent by editing ``/etc/sysconfig/selinux``. ::

    SELINUX=permissive

mod_python
^^^^^^^^^^

Pulp is a mod_wsgi application. The mod_wsgi and mod_python modules can not both be loaded into
Apache at the same time as they conflict in odd ways. Either uninstall mod_python before starting
Pulp or make sure the mod_python module is not loaded in the Apache config.

Start Pulp and Related Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The instructions below are written to be a simple process to start pulp. You should read the user docs for more information on each of these services. Systemd shown below,see user docs for upstart commands.

Start the broker (Though qpid shown here, it is not your only option)::

    sudo systemctl start qpidd

Start the agent::

    sudo systemctl start goferd

Install a plugin (the server requires at least one to start)::

    git clone https://github.com/pulp/pulp_rpm.git
    cd pulp_rpm
    sudo ./manage_setup_pys.sh develop
    sudo python ./pulp-dev.py -I

Initialize the database::

    sudo systemctl start mongod
    sudo -u apache pulp-manage-db

Start the server::

    sudo systemctl start httpd

Start pulp services::

    sudo systemctl start pulp_workers
    sudo systemctl start pulp_celerybeat
    sudo systemctl start pulp_resource_manager

Login::

    pulp-admin login -u admin

The default password is ``admin``

Uninstallation
^^^^^^^^^^^^^^

The ``pulp-dev.py`` script has an uninstall option that will remove the symlinks from the system
into the local source directory. It is run using the ``-U`` flag:

::

 $ sudo python ./pulp-dev.py -U

Each python package installed above must be removed by its package name.::

  $ sudo pip uninstall <package name>

