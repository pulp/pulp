Developer Setup
===============

Source Code
^^^^^^^^^^^

Pulp's code is stored on `GitHub <http://www.github.com/pulp>`_. Follow the instructions on
that site for checking out each repository with the appropriate level of access (Read+Write v.
Read-Only). In most cases, Read-Only will be sufficient; contributions will be done through
pull requests into the Pulp repositories as described in :doc:`merging`.

Dependencies
^^^^^^^^^^^^

The easiest way to download the dependencies is to install Pulp through yum, which will pull in
the latest dependencies according to the spec file.

#. Download the appropriate repository file at: http://repos.fedorapeople.org/repos/pulp/pulp/
#. Enable the testing repository ``pulp-v2-testing``.
#. Install the main Pulp groups to get all of the dependencies.
   ``$ sudo yum install @pulp-server @pulp-admin @pulp-consumer``
#. Remove the installed Pulp RPMs; these will be replaced with running directly from the checked
   out code. ``sudo yum remove pulp-\* python-pulp\*``

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
and installed scripts. Setup scripts can be found in the following locations:

* ``<pulp root>/platform/src``
* ``<pulp_rpm root>/rpm-support/src``
* ``<pulp_puppet root>/pulp_puppet_common``
* ``<pulp_puppet root>/pulp_puppet_extensions_admin``
* ``<pulp_puppet root>/pulp_puppet_handlers``
* ``<pulp_puppet root>/pulp_puppet_plugins``

In each of those directories, run ``sudo python ./setup.py develop``.

.. note::
  Not all Pulp projects need to be installed in this fashion. When working on a new plugin,
  the Pulp platform can continue to be run from the RPM installation and the pulp_rpm and
  pulp_puppet plugins would not be required.

Additionally, Pulp specific files such as configuration and package directories must be linked to
the checked out code base. These additions are not performed by ``setup.py`` but rather by the
``pulp-dev.py`` script located in the root of each git repository. The full command is:

::

  $ sudo python ./pulp-dev.py -I

Uninstallation
^^^^^^^^^^^^^^

The ``pulp-dev.py`` script has an uninstall option that will remove the symlinks from the system
into the local source directory. It is run using the ``-U`` flag:

::

 $ sudo python ./pulp-dev.py -U

Each ``setup.py`` installed above must be removed using the command:

::

  $ sudo pip uninstall

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

When running with SELinux enabled, the Pulp policies must be installed. The Pulp platform repository
is the only repository that includes SELinux policies. The syntax is similar to running the
``pulp-dev.py`` command as described above.

Install:

::

 $ sudo python <pulp root>/pulp-selinux.py -I


Uninstall:

::

 $ sudo python <pulp root>/pulp-selinux.py -U


mod_python
^^^^^^^^^^

Pulp is a mod_wsgi application. The mod_wsgi and mod_python modules can not both be loaded into
Apache at the same time as they conflict in odd ways. Either uninstall mod_python before starting
Pulp or make sure the mod_python module is not loaded in the Apache config.
