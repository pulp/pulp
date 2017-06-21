.. _getsource:

Get the Source
==============

It is assumed that any Pulp project repositories are cloned into one directory. As long as Ansible has read and write permissions, it doesnt matter where your **development directory** is.

.. note::

    The git repositories required by each role are documented in :ref:`ansible-roles`.

You will need ``pulp/devel`` and ``pulp/pulp`` at a minimum::

    $ git clone https://github.com/pulp/devel.git
    $ git clone https://github.com/pulp/pulp.git

If you are using ``example-playbook.yml``, that is all you will need. If your playbook includes optional :ref:`ansible-roles`, you may require additional repositories::

    $ git clone https://github.com/PulpQE/pulp-smash.git
    $ git clone https://github.com/pulp/pulpproject.org.git

If the playbook includes the ``plugins`` roles (``example-playbook.yml`` does), plugins cloned into the development directory will also be installed::

    $ git clone https://github.com/pulp/pulp_file.git

.. warning::

    It is important to ensure that your repositories are all checked out to compatible versions.
