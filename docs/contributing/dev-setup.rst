
.. _DevSetup:

Developer Setup
===============

There are two ways to automatically configure a development environment. There
is a ``Vagrantfile`` in the `devel <https://github.com/pulp/devel/>`_ git
repository that can automatically deploy a virtual machine or container on your
host with a Pulp development environment configured. Alternatively, there is an
Ansible playbook that can turn a running virtual machine into a Pulp development
environment.

Vagrant uses the Ansible playbook to provision, so if you'd prefer not to use
Vagrant for the initial setup, you can use the playbook directly. Both Vagrant
and Ansible require at least **Python 3.5** and **Ansible 2.2** to be installed
on the host machine.

Vagrant
^^^^^^^

`Vagrant <https://docs.vagrantup.com/>`_ is a tool to aid developers in quickly deploying
development environments. Pulp has provided an example ``Vagrantfile`` in the
`devel <https://github.com/pulp/devel/>`_ git repository called Vagrantfile.example. This
is the easiest way to get started on developing with Pulp if you aren't sure which method
you prefer. Vagrant is available in Fedora.

There are two Vagrant providers available for use: ``libvirt`` (using a virtual machine) and
``docker`` (using a `docker <https://www.docker.com/>`_ container).

Reasons to prefer libvirt:

* doesn't require disabling SELinux on host
* doesn't grant the development environment root-equivalent privileges on host
* may run a different kernel on host vs guest

Reasons to prefer docker:

* uses less resources (RAM, CPU and disk)
* host may freely access processes within the guest (e.g. for debugging)

Prerequisites for libvirt
-------------------------

Install vagrant, ansible, and the SSHFS plugin for vagrant. SSHFS will be used to share your
local code directory with the deployed virtual machine::

      $ sudo dnf install vagrant ansible vagrant-sshfs vagrant-libvirt


Prerequisites for docker
------------------------

#. Install vagrant, ansible, and docker::

      $ sudo dnf install vagrant ansible docker

#. Enable and start the docker service::

      $ sudo systemctl enable docker
      $ sudo systemctl start docker


.. _get-the-source:

Getting the source
------------------

Pulp's code is stored on `GitHub <https://www.github.com/pulp>`_. The repositories should be forked
into your personal GitHub account where all work will be done.

Follow the instructions on that site for checking out each repository with the appropriate
level of access (read/write versus read-only). In most cases, the upstream repositories (pulp)
should be read-only and your forked repositories should be read/write.

To start, cd into the directory where all the code will be checked out. The directory name is
not important, use whatever you like, as long as it is a directory with full read/write privileges
for the current local user::

      $ cd $HOME/devel

These repositories are required to get started with a Pulp development environment::

      $ git clone https://github.com/pulp/devel.git
      $ git clone https://github.com/pulp/pulp.git

The plugin repositories are optional::

      $ git clone https://github.com/pulp/pulp_docker.git
      $ git clone https://github.com/pulp/pulp_ostree.git
      $ git clone https://github.com/pulp/pulp_puppet.git
      $ git clone https://github.com/pulp/pulp_python.git
      $ git clone https://github.com/pulp/pulp_rpm.git

After cloning these repositories, remember to add your forks as read/write remotes if you
want to submit changes for review.

.. note::

  It is important to ensure that your repositories are all checked out to compatible versions.
  If you followed the instructions above, you have checked out master on all repositories which
  should be compatible.

Creating the Development environment
------------------------------------

#. cd into the ``devel`` repository. The Pulp project provides an example Vagrantfile that you can
   use as a starting point by copying it. After you've done that, you can begin provisioning your
   Vagrant environment. We will finish by running ``vagrant reload``. This allows the machine to
   reboot after provisioning::

      $ cd pulp
      $ cp Vagrantfile.example Vagrantfile
      # Choose ONE of the following, for your preferred provider:
      - $ vagrant up --provider=libvirt
      - $ vagrant up --provider=docker
      $ vagrant reload

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


Advanced Vagrant Usage
----------------------

The following steps are all optional, so feel free to pick and choose which you would like to
follow.

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


Vagrant w/ PyCharm
------------------

PyCharm 5.0.1 is mostly usable with Vagrant.

Remote Debugging
****************

To use a remote debugger provided by PyCharm, ensure the PyCharm debug egg is installed in the
Vagrant environment. This can be done in the Vagrant environment using ``sudo pip``
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
********************

With Vagrant, Pulp is not installed on your host system preventing PyCharm from knowing an object
through static analysis. Practically speaking, this causes all Pulp objects to be shown as an
unresolved reference and prevents jumping to the declaration (Ctrl + B).

To resolve this, configure your project with a Vagrant-aware, remote interpreter. In settings,
find the 'Project Interpreter' area and add a Remote Interpreter. Select 'Vagrant'
and give it the path to your vagrant file. In my case this is ``/home/<username>/devel/pulp``.

   .. note:: The remote interpreter copies the indexed remote code locally into PyCharm's cache.
             Be aware, when you jump to a declaration (Ctrl + B), you are being shown PyCharm's
             cached version. For reading code this is fine, but when applying changes, be sure
             you know if you are editing the actual code or a cached copy.


Ansible
^^^^^^^

.. note::

    Usage of `Ansible <https://docs.ansible.com/ansible/index.html>`_ directly instead of Vagrant
    assumes working knowledge of Ansible. Familiarity with topics such as creating inventories,
    running playbooks, and setting extra variables is recommended before proceeding.

These instructions will create a developer install of Pulp on a dedicated development instance.
It is recommended not to use this machine for any other purpose, as the playbook will
disable SELinux and install items as root outside of the system package manager.

The playbook used for developer setup is ``ansible/dev-playbook.yml`` in the ``devel`` repository.

The Vagrant environment is provisioned using this playbook, but some things are slightly different
when Ansible is run outside of Vagrant::

    * Ansible does not check the source code out for you. The wide variety of branches and remotes
      make it difficult to automate this step in a general way. Adding an ansible role to the dev
      playbook to fit your deployment is recommended.
    * The Vagrant role sets up the various user files, like ``.bashrc`` and ``.vimrc``. You can
      optionally enable the vagrant role, which should have no negative effect on a "normal" VM,
      to install these files.

Requirements
------------

* Latest Fedora x86_64 instance that will be dedicated for Pulp development with
  at least 2GB of memory and 10GB of disk space. More disk space is needed if
  you plan on syncing larger repos for test purposes.

* An unprivileged (non-root) user on that instance with passwordless sudo access. You may
  need to edit /etc/sudoers and ensure that the ``wheel`` group has sudo privileges
  ``%wheel ALL=(ALL) NOPASSWD: ALL``, and then the unprivileged user is a member of the wheel
  group (``gpasswd -a <user> wheel``). In recent Fedora Cloud images, the "fedora" user is
  already in the correct group, but the group must be updated to include the ``NOPASSWD:``
  flag.

Getting the Source
------------------

Once your unprivileged user is set up, you need to get the source checked out on the VM
where the playbook will be run. Follow the instructions above for :ref:`getting the
source <get-the-source>` *on your virtual machine* to get all the necessary code cloned
and ready for ansible to use.

Running the Playbook
--------------------

Assuming the source is all checked out on your target VM in ``~/devel``, you should now
be able to run the dev playbook.

.. note::

    ``ansible_python_interpreter`` **MUST** be set to a python 3 interpreter, such as
    ``/usr/bin/python3``. The dev playbook does not work with python 2.


To run the playbook against your VM, ensure the inventory is correct, and then::

    ansible-playbook -e ansible_python_interpreter=/usr/bin/python3 -i inventory ansible/dev-playbook.yml

Use Vagrant's Inventory
***********************

Even if you're using vagrant, you may find it convenient to have more manual control
over the running of the playbook by running ``ansible-playbook`` directly against the
Vagrant inventory. Vagrant stores its inventory in a ``.vagrant`` dir in the same place
as the ``Vagrantfile`` after running ``vagrant up``. Vagrant stores the inventory in
``.vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory``, so pass that to
``ansible-playbook`` as the invetory when running the dev playbook, remember to also
enable the vagrant role::

    ansible-playbook -e ansible_python_interpreter=/usr/bin/python3 -e use_vagrant_role=true \
        -i .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory \
        ansible/dev-playbook.yml

Playbook Variables
------------------

The following variables are available to customize the ansible play.

.. note::

    When declaring variables with path values, ansible does not expand the '~' path
    component to the user homedir. For consistency's sake, consider using absolute
    paths.

pulp_dev_dir
    This must be set to the directory path containing the git clones of Pulp repositories
    on the remote machine. By default, it is set to ``~/devel/``, and only needs to be
    changed if you've cloned the Pulp repositories into a different directory.

pulp_venv_dir
    Defaults to ``~/.virtualenvs``. If you prefer to store your virtualenvs elsewhere,
    override this value.

unprivileged_homedir
    By default, Should be set to the home directory of the unprivileged user. If the
    homedir autodetection does not work for some reason, override this.

use_vagrant_role
    If true, include the vagrant role when running the playbook. This is set to true
    in the Vagrantfile provisioning step, but is otherwise false by default. This installs
    helpful configuration files, like a ``.bashrc`` and ``.vimrc`` which non-vagrant users
    might not want, and ensures the vagrant user has the correct sudo privileges.

use_debug_role
    If true, include the debug role when running the playbook. This installs ``gdb`` and
    a multitude of debug packages that can help when debugging Pulp and other processes.

pulp_facts module
-----------------

The ``core`` playbook role runs the ``pulp_facts`` module, which can be found in
``ansible/library/pulp_facts.py`` in the ``devel`` repository. This module contains most
of the logic that powers other parts of the playbook, particularly the dev role. If you're
adding requirements files or support for entire plugins to the dev playbook, this is where
to start.

See the comments in this file, as well as how the values produced by it get used in the
dev role's ``tasks/main.yml`` file.
