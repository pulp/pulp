.. _DevSetup:

Developer Setup
===============

To ease developer setup, we have `Pulplift <https://github.com/ehelms/pulplift>`_ which is based on
the `Forklift <https://github.com/theforeman/forklift>`_ project and utilizes
`Ansible <https://docs.ansible.com/ansible/index.html>`_ roles and playbooks to provide supported
`Vagrant <https://docs.vagrantup.com/>`_ boxes that are more consistent with the user experience.

Clone the 'pulplift', 'pulp', and 'pulp_file' (or any plugins that you'll be working on) repos into
the same directory so that they are peers.

Navigate into the pulplift directory. Run the setup.sh script which will clone the 'forklift' and
`'ansible-pulp3' <https://github.com/pulp/ansible-pulp3>`_ repos::

    ./setup.sh

The parent directory of 'pulplift' is going to be mounted into the vagrant box at
/home/vagrant/devel. Any plugins that need to be installed should be added to the
pulplift/ansible-pulp3/source-install.yml playbook. The paths to the source of the plugins should
start with /home/vagrant/devel/. For example::

    pulp_install_plugins:
      pulp-python:
        app_label: "python"
        source_dir: "/home/vagrant/devel/pulp_python"
      pulp-file:
        app_label: "file"
        source_dir: "/home/vagrant/devel/pulp_file"

Once this is complete, take a look at available boxes with 'vagrant status' and then spin up your
chosen environment::

    vagrant up pulp3-source-fedora28

Activate your virtual environment::

    workon pulp

Happy developing!

.. toctree::
   :maxdepth: 2

   quickstart
   source
   ansible
   runtests


