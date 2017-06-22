.. _DevSetup:

Developer Setup
===============

To ease developer setup, we have Ansible roles, playbooks and a Vagrantfile in our `pulp/devel <https://github.com/pulp/devel/>`_ repository. Use the :ref:`quickstart` to dive in with an example configuration.

`Ansible <https://docs.ansible.com/ansible/index.html>`_ playbooks can be used to provision a machine with a developer installation of Pulp. It is highly recommended that you develop Pulp on a virtual machine. Have a look at our :ref:`using-ansible` section to change how your machine is provisioned.

`Vagrant <https://docs.vagrantup.com/>`_ is used to create and manage development virtual machines. Configuring Vagrant is beyond the scope of this document, but you can find suggestions in the comments of ``Vagrantfile.example`` and on the `wiki <https://pulp.plan.io/projects/pulp/wiki/Developer_Install_Options>`_. 

.. toctree::
   :maxdepth: 2

   quickstart
   source
   ansible
