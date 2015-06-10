
.. _DevSetup:

Developer Setup
===============

For the Impatient
-----------------

There are two ways to automatically configure a development environment. There is a Vagrantfile
in the platform git repository that can automatically deploy a virtual machine on your host with a
Pulp development environment configured. Alternatively, there is a script that can turn a blank
running virtual machine into a Pulp development environment.

Vagrant
^^^^^^^

`Vagrant <https://docs.vagrantup.com/>`_ is a tool to aid developers in quickly deploying
development environments. Pulp has provided a ``Vagrantfile`` in the platform git repository. This
is the easiest way to get started on developing with Pulp if you aren't sure which method you
prefer. Vagrant is available in Fedora 21 and newer. Follow these steps:

#. Install vagrant::
   
      $ sudo yum install vagrant-libvirt

#. Install NFS. NFS will be used to share your code directory with the deployed virtual machine::
   
      $ sudo yum install nfs-utils

#. You will need to grant the nfsnobody user rx access to the folder that you check out your code
   under. Many developers check out code into $HOME/devel or similar. In Fedora, $HOME typically
   does not allow such access to other users. If your code is in $HOME, you will need to::
   
      $ setfacl -m user:nfsnobody:r-x $HOME  # Season to taste, as per above

   .. warning::
   
      Wherever you have hosted your code, it would be good to verify that nfsnobody is able to read
      it. If you experience an error message similar to
      "mount.nfs: access denied by server while mounting 192.168.121.1:/path/to/my/code/dir"
      during the vagrant up later, it is likely that nfsnobody is being blocked from reading your
      code directory by either filesystem permissions or SELinux.

#. Start and enable the nfs-server service::

      $ sudo systemctl enable nfs-server && sudo systemctl start nfs-server

#. You will need to allow NFS services through your firewall::
   
      $ sudo firewall-cmd --permanent --add-service=nfs
      $ sudo firewall-cmd --permanent --add-service=rpc-bind
      $ sudo firewall-cmd --permanent --add-service=mountd
      $ sudo firewall-cmd --reload

#. You are now prepared to check out the Pulp code into your preferred location. Change directories
   to that location, and check out at least the platform and the RPM plugins. The RPM plugins are
   needed as the provisioning script configures and synchronizes an example repository::

      $ cd $HOME/devel  # Season to taste
      $ git clone git@github.com:pulp/pulp.git && git clone git@github.com:pulp/pulp_rpm.git

#. Optionally, check out some of our other plugins as well::

      $ git clone git@github.com:pulp/pulp_docker
      $ git clone git@github.com:pulp/pulp_python
      $ git clone git@github.com:pulp/pulp_puppet
      $ git clone git@github.com:pulp/pulp_ostree

   .. note::

      It is important to ensure that your repositories are all checked out to compatible versions.
      If you followed the instructions above, you have checked out master on all repositories which
      should be compatible.

#. Optionally, configure your system policy to allow your user to manage libvirt without needing
   root privileges. Create ``/etc/polkit-1/localauthority/50-local.d/libvirt.pkla`` with the
   following contents, substituting with your user id::

    [Allow your_user_id_here libvirt management permissions]
    Identity=unix-user:your_user_id_here
    Action=org.libvirt.unix.manage
    ResultAny=yes
    ResultInactive=yes
    ResultActive=yes

#. Next, cd into the pulp directory and begin provisioning your Vagrant environment. A possible
   failure point is during provisioning when mongod is building its initial files. This sometimes
   takes longer than systemd allows and can fail. If that happens, simply run ``vagrant provision``.
   We will finish by running ``vagrant reload``. This allows the machine to reboot after
   provisioning.::

      $ cd pulp
      $ vagrant up  # mongod may fail when this runs. vagrant provision will fix it.
      $ vagrant reload  # Reboot the machine at the end to apply kernel updates, etc.

Once you have followed the steps above, you should have a running deployed Pulp development machine.
You can ssh into the environment with ``vagrant ssh``. All of the code is mounted in
/home/vagrant/devel. Your development environment has been configured for
`virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/>`_. If you would like to
activate a virtualenv, you can simply type ``workon <repo_dir>`` to work on any particular Pulp
repo. For example, ``workon pulp`` will activate the Pulp platform virtualenv and cd into the code
directory for you. You can type ``workon pulp_rpm`` for pulp_rpm, ``workon pulp_python`` for
pulp_python, and so forth. Any plugins in folders that start with ``pulp_`` that you had checked out
in your host machine's code folder alongside the Pulp platform repository should have been installed
and configured for virtualenv.


Provisioning Script
^^^^^^^^^^^^^^^^^^^

These instructions will create a developer install of Pulp on a dedicated pre-installed development
instance. It is recommended not to use this machine for any other purpose, as the script will
disable SELinux and install items as root outside of the system package manager.

* Start a RHEL 7 or Fedora 20/21 x86_64 instance that will be dedicated for Pulp development with
  at least 2GB of memory and 10GB of disk space. More disk space is needed if
  you plan on syncing larger repos for test purposes.

* If one does not already exist, create a non-root user on that instance with
  sudo access. If you are using a Fedora cloud image, the "fedora" user is
  sufficient.

* As that user, ``curl -O https://raw.githubusercontent.com/pulp/pulp/master/playpen/dev-setup.sh && bash -e dev-setup.sh``.

   .. warning:: Note that this installs RPMs and makes system modifications that you wouldn't
                want to apply on a VM that was not dedicated to Pulp development.

* While it runs, read the rest of this document! It details what the quickstart
  script does and gives background information on the development
  process.

Source Code
-----------

Pulp's code is stored on `GitHub <http://www.github.com/pulp>`_. The repositories should be forked
into your personal GitHub account where all work will be done. Changes are
submitted to the Pulp team through the pull request process outlined in :doc:`merging`.


Follow the instructions on
that site for checking out each repository with the appropriate level of access (Read+Write v.
Read-Only). In most cases, Read-Only will be sufficient; contributions will be done through
pull requests into the Pulp repositories as described in :doc:`merging`.

Dependencies
------------

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
        python-mock python-paste python-pip python-flake8

The only caveat to this approach is that these dependencies will need to be maintained after this
initial setup. Leaving the testing builds repository enabled will cause them to be automatically
updated on subsequent ``yum update`` calls. Messages are sent to the Pulp mailing list when these
dependencies are updated as well to serve as a reminder to update before the next code update.

Installation
------------

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
--------------

The ``pulp-dev.py`` script has an uninstall option that will remove the symlinks from the system
into the local source directory, as well as the Python packages. It is run using the ``-U`` flag:

::

 $ sudo python ./pulp-dev.py -U

Permissions
-----------

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
-------

Unfortunately, when developing Pulp SELinux needs to be disabled or run in Permissive mode. Most
development environments will be created with ``pulp-dev.py``, which deploys Pulp onto the system
differently than a rpm based install. The SELinux policy of Pulp expects an RPM layout, and if
SELinux is run in Enforcing mode your development to not function correctly.

To turn off SELinux, you can use ``sudo setenforce 0`` which will set SELinux to permissive. By default, SELinux will be enabled on the next restart so make the change persistent by editing ``/etc/sysconfig/selinux``. ::

    SELINUX=permissive

mod_python
----------

Pulp is a mod_wsgi application. The mod_wsgi and mod_python modules can not both be loaded into
Apache at the same time as they conflict in odd ways. Either uninstall mod_python before starting
Pulp or make sure the mod_python module is not loaded in the Apache config.

Start Pulp and Related Services
-------------------------------

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
--------------

The ``pulp-dev.py`` script has an uninstall option that will remove the symlinks from the system
into the local source directory. It is run using the ``-U`` flag:

::

 $ sudo python ./pulp-dev.py -U

Each python package installed above must be removed by its package name.::

  $ sudo pip uninstall <package name>

