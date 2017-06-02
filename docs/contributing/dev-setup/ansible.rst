.. _using-ansible:

Using Ansible
=============

Unless you are happy with the example configuration, creating a **custom playbook** is the best way to control your development environment.

This section will explain how to use the Ansible tools we provide, but does not explain basic Ansible topics, which is outside of the scope of this document.


Virtual Machine Requirements
----------------------------

.. warning::

    It is recommended not to use your dev machine for any other purpose, some configurations
    disable SELinux and all configurations install items as root outside of the system package manager.


* Latest Fedora x86_64 instance that will be dedicated for Pulp development with
  at least 2GB of memory and 10GB of disk space. More disk space is needed if
  you plan on syncing larger repos for test purposes.

* An unprivileged (non-root) user on that instance with passwordless sudo access. You may
  need to edit /etc/sudoers and ensure that the ``wheel`` group has sudo privileges
  ``%wheel ALL=(ALL) NOPASSWD: ALL``, and then the unprivileged user is a member of the wheel
  group (``gpasswd -a <user> wheel``). In recent Fedora Cloud images, the "fedora" user is
  already in the correct group, but the group must be updated to include the ``NOPASSWD:``
  flag.

Put Source Code on your VM
--------------------------

Use the :ref:`getsource` guide to put the code into a *development directory on your virtual machine* and make sure the ``pulp_devel_dir`` is set correctly, see `variables`_.

.. _variables:

Playbook Variables
------------------

Some roles have required variables, all of which are given minimal default values and documented in ``ansible/group_vars/all``. ``vars`` defined in your playbook override the defaults.

.. note::

    When declaring variables with path values, ansible does not expand the '~' path
    component to the user homedir. For consistency's sake, consider using absolute
    paths.

.. _ansible-roles:

Ansible Roles
-------------

The ``common`` playbook role runs the ``pulp_facts`` module, which can be found in
``ansible/library/pulp_facts.py`` in the ``devel`` repository. This module contains most
of the logic that powers other parts of the playbook, particularly the dev role.

*Role order matters*:

+---------------+----------+------------------------+-----------------------------------------------+
| Role          | Required | Git Repos              | Description                                   |
+===============+==========+========================+===============================================+
| vagrant       |          |                        | Use *only* if provisioning a Vagrant machine  |
+---------------+----------+------------------------+-----------------------------------------------+
| common        | Required | pulp/pulp, pulp/devel  | *Special Role* gather facts                   |
+---------------+----------+------------------------+-----------------------------------------------+
| broker        | Required |                        | Rabbit Message broker                         |
+---------------+----------+------------------------+-----------------------------------------------+
| db            | Required |                        | PostgreSQL                                    |
+---------------+----------+------------------------+-----------------------------------------------+
| lazy          |          |                        | Streamer                                      |
+---------------+----------+------------------------+-----------------------------------------------+
| dev           | Required |                        | Source install of core Pulp                   |
+---------------+----------+------------------------+-----------------------------------------------+
| plugins       |          |                        | Install plugins                               |
+---------------+----------+------------------------+-----------------------------------------------+
| reset_db      |          |                        | Reset the database and migrate                |
+---------------+----------+------------------------+-----------------------------------------------+
| systemd       |          |                        | Manage Pulp processes with ``systemctl``      |
+---------------+----------+------------------------+-----------------------------------------------+
| smash         |          | PulpQE/pulp-smash      | Integration tests                             |
+---------------+----------+------------------------+-----------------------------------------------+
| dev_tools     |          |                        | Tools useful to many developers (vim, screen) |
+---------------+----------+------------------------+-----------------------------------------------+
| debug         |          |                        | Debugging tools                               |
+---------------+----------+------------------------+-----------------------------------------------+
| release_tools |          |                        | Build and release Pulp                        |
+---------------+----------+------------------------+-----------------------------------------------+
| pulpproject   |          | pulp/pulproject.org    | The website                                   |
+---------------+----------+------------------------+-----------------------------------------------+
| pulp_ca       |          |                        | Generate certs                                |
+---------------+----------+------------------------+-----------------------------------------------+
