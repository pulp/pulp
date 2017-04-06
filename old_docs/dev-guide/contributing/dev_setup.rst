
.. _DevSetup:

Developer Setup
===============

There are two ways to automatically configure a development environment. There
is a Vagrantfile in the `devel <https://github.com/pulp/devel/>`_ git
repository that can automatically deploy a virtual machine or container on your
host with a Pulp development environment configured. Alternatively, there is a
script that can turn a blank running virtual machine into a Pulp development
environment. This document assumes that you are running a recent version of Fedora
although these steps should be roughly the same on other distributions. Package managers
and package names may differ if you're not using Fedora as your development platform so
be aware as you follow this document.

Vagrant
^^^^^^^

`Vagrant <https://docs.vagrantup.com/>`_ is a tool to aid developers in quickly deploying
development environments. Pulp has provided an example ``Vagrantfile`` in the
`devel <https://github.com/pulp/devel/>`_ git repository called Vagrantfile.example. This
is the easiest way to get started on developing with Pulp if you aren't sure which method
you prefer. Vagrant is available in Fedora.

There are two Vagrant providers that the Pulp project has made available for use:
``libvirt`` (using a virtual machine) and ``docker`` (using a `docker <https://www.docker.com/>`_ container).

Reasons to prefer libvirt:

* doesn't grant the development environment root-equivalent privileges on host
* may run a different kernel on host vs guest

Reasons to prefer docker:

* uses less resources (RAM, CPU and disk)
* improved performance
* host may freely access processes within the guest (e.g. for debugging)
* no extra firewall ports to open on your development platform

Prerequisites for Vagrant
-------------------------

#. Install Vagrant and Ansible. Vagrant will manage your development vms or containers and Ansible
   is used to configure the system once it is running. ::

      $ sudo dnf install vagrant ansible

.. note::
  ``libvirt`` is the only officially supported and tested provider and will work in all cases.
  ``docker`` provider is available, but might not be fully functional.

Prerequisites for libvirt
-------------------------

Follow these steps:

#. Install Vagrant, Ansible, and nfs-utils. NFS will be used to share your code directory with the
   deployed virtual machine::

      $ sudo dnf install nfs-utils vagrant-libvirt

#. You will need to grant the nfsnobody user rx access to the folder that you check out your code
   under. Many developers check out code into $HOME/devel or similar. In Fedora, $HOME typically
   does not allow such access to other users. If your code is in $HOME, you will need to::

      $ setfacl -m user:nfsnobody:r-x $HOME  # Season to taste, as per above

   .. warning::

      Wherever you have hosted your code, it would be good to verify that nfsnobody is able to read
      it. If you experience an error message similar to
      "mount.nfs: access denied by server while mounting 192.168.121.1:/path/to/my/code/dir"
      during the Vagrant up later, it is likely that nfsnobody is being blocked from reading your
      code directory by either filesystem permissions or SELinux.

#. Start and enable the nfs-server service::

      $ sudo systemctl enable nfs-server && sudo systemctl start nfs-server

#. You will need to allow NFS services through your firewall::

      $ sudo firewall-cmd --permanent --add-service=nfs
      $ sudo firewall-cmd --permanent --add-service=rpc-bind
      $ sudo firewall-cmd --permanent --add-service=mountd
      $ sudo firewall-cmd --reload

.. note::

  If Vagrant will not start due to the error message
  ``error creating bridge interface virbr0: File exists``, you can solve it by using
  ``ifconfig virbr0 down`` and ``brctl delbr virbr``

Prerequisites for docker
------------------------

Follow these steps:

#. Install docker::

      $ sudo dnf install docker

#. Enable and start the docker service::

      $ sudo systemctl enable docker
      $ sudo systemctl start docker

Creating the Vagrant environment
--------------------------------

After preparing either the libvirt or docker prerequisites using the instructions above:

#. You are now prepared to check out the Pulp code into your preferred location.
   All of the repositories must exist parallel to each other for the default configuration in Vagrant.
   Change directories to the location that you want your Pulp git repositories to exist
   and check out the development tools repository and the Pulp platform repository::

      $ cd $HOME/devel  # Season to taste.
      $ git clone git@github.com:pulp/devel.git
      $ git clone git@github.com:pulp/pulp.git

#. Check out the plugins you wish to develop or use as well::

      $ git clone git@github.com:pulp/pulp_deb.git
      $ git clone git@github.com:pulp/pulp_docker.git
      $ git clone git@github.com:pulp/pulp_openstack.git
      $ git clone git@github.com:pulp/pulp_ostree.git
      $ git clone git@github.com:pulp/pulp_puppet.git
      $ git clone git@github.com:pulp/pulp_python.git
      $ git clone git@github.com:pulp/pulp_rpm.git

   .. note::

      It is important to ensure that your repositories are all checked out to compatible versions.
      If you followed the instructions above, you have checked out master on all repositories which
      should be compatible.

#. Next, cd into the ``devel`` directory. The Pulp project provides an example Vagrantfile that you can
   use as a starting point by copying it. ::

      $ cd devel
      $ cp Vagrantfile.example Vagrantfile

#. You can open the Vagrantfile in your favorite editor and modify it to better fit your
   development preferences. This step is entirely optional as the default Vagrantfile should
   work for most users. Refer to the :ref:`Advanced Vagrant <dev-setup-advanced-vagrant>` section
   below for some helpful tips. ::

      $ vim Vagrantfile

#. After you've happy with your Vagrantfile, you can begin provisioning your
   Vagrant environment. We will finish by running ``vagrant reload``. This allows the machine to
   reboot after provisioning. ::

      # Choose ONE of the following, for your preferred provider:
      $ vagrant up --provider=libvirt
      $ sudo vagrant up --provider=docker
      # The above will run for a while while it provisions your development environment.
      $ vagrant reload  # Reboot the machine at the end to apply kernel updates, etc.

   .. note::

      If you want to do a ``vagrant up`` without having to enter your sudo password, please follow the
      instructions mentioned in the 'Root Privilege Requirement' section of
      `Vagrant docs <https://www.vagrantup.com/docs/synced-folders/nfs.html>`_.

   .. note::

      You may need to run ``vagrant`` as sudo if using docker. The docker daemon is typically
      only available to the root user.

#. Once you have followed the steps above, you should have a running deployed Pulp development
   machine. ssh into your Vagrant environment::

      $ vagrant ssh

Whenever you connect to your Vagrant environment, you will be greeted by a message of the day
that gives you some helpful hints. All of the code is mounted in
/home/vagrant/devel. Your development environment has been configured for
`virtualenvwrapper <http://virtualenvwrapper.readthedocs.io/en/latest/>`_. If you would like to
activate a virtualenv, you can simply type ``workon <repo_dir>`` to work on any particular Pulp
repo. For example, ``workon pulp`` will activate the Pulp platform virtualenv and cd into the code
directory for you. You can type ``workon pulp_rpm`` for pulp_rpm, ``workon pulp_python`` for
pulp_python, and so forth. Any plugins in folders that start with ``pulp_`` that you had checked out
in your host machine's code folder alongside the Pulp platform repository should have been installed
and configured for virtualenv.

Using Vagrant
-------------

The Vagrant environment provides some useful built-in commands by default.
More information about them can be found in command ``phelp``.

List of most useful commands:

* ``pstart`` - Starts all pulp related servicies
* ``ppopulate`` - Load default testing repositories

.. note::

    You have to issue ``pstart`` after starting vagrant.

.. note::

    If Vagrant is stopped incorrectly, mongo may not be able to start.
    This can be solved by removing the file ``/var/lib/mongodb/mongod.lock``.
    To avoid this, always stop your Vagrant environment with ``vagrant halt``.

.. _dev-setup-advanced-vagrant:

Advanced Vagrant
^^^^^^^^^^^^^^^^

The following steps are all optional, so feel free to pick and choose which you would like to
follow.

#. If your provisioning of the Vagrant box fails or you make modifications to the scripts
   or Ansible roles that provision the Vagrant box, you must re-run the provisioning in Vagrant
   because it will only run once. ::

      $ vagrant provision

#. You can configure your Vagrant enviroment to cache RPM packages you download with dnf. To do
   this, uncomment the line ``'.dnf-cache' => '/var/cache/dnf'``, which syncs the ``.dnf-cache``
   directory (relative to the Vagrantfile) to ``/var/cache/dnf``. You will need to create the
   ``.dnf-cache`` directory manually with ``mkdir .dnf-cache``.

#. When using Vagrant, you probably have noticed that you are frequently prompted for passwords to
   manage libvirt. You can configure your system policy to allow your user to manage libvirt without
   needing root privileges. Create ``/etc/polkit-1/localauthority/50-local.d/libvirt.pkla`` with the
   following contents, substituting with your user id::

    [Allow your_user_id_here libvirt management permissions]
    Identity=unix-user:your_user_id_here
    Action=org.libvirt.unix.manage
    ResultAny=yes
    ResultInactive=yes
    ResultActive=yes

#. You can configure your Vagrant environment to use
   `kvm's unsafe cache mode <http://libvirt.org/formatdomain.html#elementsDisks>`_. If you do this,
   you will trade data integrity on your development environment's filesystem for a noticeable speed
   boost. In your Vagrantfile, there is a commented line ``domain.volume_cache = "unsafe"``. To use
   the unsafe cache mode, simply uncomment this line.

   You can also configure Vagrant to use the unsafe cache for all Vagrant guests on your system by
   creating ``~/.vagrant.d/Vagrantfile`` with the following contents::

    # -*- mode: ruby -*-
    # vi: set ft=ruby :


    Vagrant.configure(2) do |config|
        config.vm.provider :libvirt do |domain|
            # Configure the unsafe cache mode in which the host will ignore fsync requests from the
            # guest, speeding up disk I/O. Since our development environment is ephemeral, this is
            # OK. You can read about libvirt's cache modes here:
            # http://libvirt.org/formatdomain.html#elementsDisks
            domain.volume_cache = "unsafe"
        end
    end

   .. warning::

    This is dangerous! However, the development environment is intended to be "throw away", so
    if you end up with a corrupted environment you will need to destroy and recreate it.
    Fortunately, the code you are working on will be shared from your host via NFS so your work
    should have data safety.

#. You can use SSHFS rather than NFS if you're using libvirt. The downside is SSHFS does not perform
   quite as well as NFS, but the upside is you do not need to configure or run NFS, nor do you need
   to allow Vagrant to edit your /etc/exports file. At the time of this writing, the ``vagrant-sshfs``
   package is not yet in Fedora, although the package is in the process of being reviewed. The author
   provides a COPR repository you can enable to install the RPM::

    $ sudo dnf copr enable dustymabe/vagrant-sshfs
    $ sudo dnf install vagrant-sshfs

   You need to modify your Vagrantfile to use SSHFS::

    # -*- mode: ruby -*-
    # vi: set ft=ruby :


    Vagrant.configure(2) do |config|
        config.vm.define "dev" do |dev|
            VAGRANT_SYNCED_FOLDERS.each do |host_path, guest_path|
                # Use SSHFS instead of NFS. The ``-o nonempty`` option is passed to allow
                # mounts on non-empty directories.
                dev.vm.synced_folder host_path, guest_path, type: "sshfs", sshfs_opts_append: "-o nonempty"
            end
        end
    end


Vagrant w/ PyCharm
^^^^^^^^^^^^^^^^^^

PyCharm 5.0.1 is mostly usable with Vagrant.

Remote Debugging
----------------

To use a remote debugger provided by PyCharm, ensure the PyCharm debug egg is installed in the
Vagrant environment. This can be done in the Vagrant environment using ``easy_install``
so it is available in all virtualenv environments the Vagrantfile sets up.

When SSHing to Vagrant, use a reverse SSH tunnel to allow the Vagrant environment to connect
back to your host system where the PyCharm remote debugger is listening. ``vagrant ssh`` allows
you to specify arbitrary SSH commands using the ``--`` syntax. Assuming a PyCharm remote debugger
is listening on port 12345, connect to Vagrant with a reverse tunnel using::

      $ vagrant ssh -- -R 12345:localhost:12345

You'll also need to configure local to remote path mappings to allow PyCharm to treat your host
code checkout corresponds with the remote Vagrant code. To do this, edit the PyCharm remote
debugger instance and add the following path mapping configuration::

      /home/<your_username>/devel=/home/vagrant/devel

Resolving References
--------------------

With Vagrant, Pulp is not installed on your host system preventing PyCharm from knowing an object
through static analysis. Practically speaking, this causes all Pulp objects to be shown as an
unresolved reference and prevents jumping to the declaration (Ctrl + B).

To resolve this, configure your project with a Vagrant-aware, remote interpreter. In settings,
find the 'Project Interpreter' area and add a Remote Interpreter. Select 'Vagrant'
and give it the path to your Vagrant file. In my case this is ``/home/<username>/devel/pulp``.

   .. note:: The remote interpreter copies the indexed remote code locally into PyCharm's cache.
             Be aware, when you jump to a declaration (Ctrl + B), you are being shown PyCharm's
             cached version. For reading code this is fine, but when applying changes, be sure
             you know if you are editing the actual code or a cached copy.


Provisioning Script
^^^^^^^^^^^^^^^^^^^

These instructions will create a developer install of Pulp on a dedicated pre-installed development
instance. It is recommended not to use this machine for any other purpose, as the script will
disable SELinux and install items as root outside of the system package manager.

* Fedora 22 x86_64 instance that will be dedicated for Pulp development with
  at least 2GB of memory and 10GB of disk space. More disk space is needed if
  you plan on syncing larger repos for test purposes.

* If one does not already exist, create a non-root user on that instance with
  sudo access. If you are using a Fedora cloud image, the "fedora" user is
  sufficient.

* As that user, ``curl -O https://raw.githubusercontent.com/pulp/devel/master/scripts/dev-setup.sh && bash -e dev-setup.sh``.

   .. warning:: Note that this installs RPMs and makes system modifications that you wouldn't
                want to apply on a VM that was not dedicated to Pulp development.

* While it runs, read the rest of this document! It details what the quickstart
  script does and gives background information on the development
  process.

Source Code
-----------

Pulp's code is stored on `GitHub <https://www.github.com/pulp>`_. The repositories should be forked
into your personal GitHub account where all work will be done. Changes are
submitted to the Pulp team through the pull request process outlined in :doc:`merging`.


Follow the instructions on
that site for checking out each repository with the appropriate level of access (Read+Write v.
Read-Only). In most cases, Read-Only will be sufficient; contributions will be done through
pull requests into the Pulp repositories as described in :doc:`merging`.

Dependencies
------------

The easiest way to download the other dependencies is to install Pulp through yum or dnf, which
pulls in the latest dependencies according to the spec file.

#. Download the appropriate repository from https://repos.fedorapeople.org/repos/pulp/pulp/

   Example for Fedora::

       $ cd /etc/yum.repos.d/
       $ sudo wget https://repos.fedorapeople.org/repos/pulp/pulp/fedora-pulp.repo

#. Edit the repo and enable the most recent testing repository.

#. When using dnf, install the dependencies with this command.
   ``$ sudo dnf install -y $(rpmspec -q --queryformat '[%{REQUIRENAME}\n]' *.spec | grep -v "/.*" | grep -v "python-pulp.* " | grep -v "pulp.*" | uniq)``

#. When using yum, install all Pulp packages to get the dependencies::

    $ sudo yum install pulp-server python-qpid qpid-tools \
    pulp-rpm-plugins pulp-puppet-plugins pulp-docker-plugins \
    pulp-admin-client pulp-rpm-admin-extensions \
    pulp-puppet-admin-extensions pulp-docker-admin-extensions \
    pulp-consumer-client pulp-rpm-consumer-extensions \
    pulp-puppet-consumer-extensions pulp-agent pulp-rpm-handlers pulp-rpm-yumplugins \
    pulp-puppet-handlers python-gofer-qpid

#. When using yum, remove the installed Pulp RPMs; these will be replaced with running directly from the checked
   out code. ``$ sudo yum remove pulp-\* python-pulp\*``

#. Install some additional dependencies for development::

        $ sudo yum install python-setuptools redhat-lsb mongodb mongodb-server \
        qpid-cpp-server qpid-cpp-server-linearstore python-qpid-qmf python-nose \
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

The instructions below are written to be a simple process to start Pulp. You should read the user docs for more information on each of these services. Systemd shown below,see user docs for upstart commands.

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

Start Pulp services::

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
