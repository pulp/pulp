Pulp Client Extensions
======================

Overview
--------

Both the Pulp Admin Client and the Pulp Consumer Client use an extension mechanism
to allow additions and changes to be made depending on a developer's needs. Pulp
makes use of Python's entry point feature, by which the client discovers extensions
at run time and initializes each, allowing them to add new sections and commands.


Create an Entry Point
---------------------

Your extension should define a method that will be an entry point. It should
accept one argument, and the convention is to use this definition:

::

  from pulp.client.extensions.decorator import priority

  @priority()
  def initialize(context):
      """
      :type context: pulp.client.extensions.core.ClientContext
      """
      pass

The ClientContext instance includes a reference to everything you need to add new
commands and sections to the CLI. Look at the
`Puppet Extensions <https://github.com/pulp/pulp_puppet/tree/master/pulp_puppet_extensions_admin>`_
for an example of how to add features to the CLI.

The ``@priority()`` decorator controls the order in which this extension will be
loaded relative to other extensions. By not passing a value, this example accepts
the default priority level.


Advertise the Entry Point
-------------------------

Python entry points are advertised within the package's ``setup.py`` file. As an
example, here is that file from the Pulp Puppet Extensions Admin package.

::

  from setuptools import setup, find_packages

  setup(
      name='pulp_puppet_extensions_admin',
      version='2.0.0',
      license='GPLv2+',
      packages=find_packages(exclude=['test', 'test.*']),
      author='Pulp Team',
      author_email='pulp-list@redhat.com',
      entry_points = {
          'pulp.extensions.admin': [
              'repo_admin = pulp_puppet.extensions.admin.repo.pulp_cli:initialize',
          ]
      }
  )

Notice that the entry point name is ``pulp.extensions.admin``. That distinguishes
it as an extension for the admin client. A consumer extension would use the
name ``pulp.extensions.consumer``. Technically these names could be changed, or
new ones could be used if new CLI tools are developed. The "admin" and "consumer"
portions of these names come from config files ``/etc/pulp/admin/admin.conf`` and
``/etc/pulp/consumer/consumer.conf``. Each has a "[client]" section with a "role"
setting. That said, the intent is for these to stay the same, and it is sufficient
to assume that they will.


Legacy Pattern
--------------

Quick start guide to writing an extension. The entry point method described above
is the preferred way to integrate new extensions, but this pattern is maintained
for backward compatibility:

* Create directory in ``/var/lib/pulp/client/*/extensions/``.
* Add ``__init__.py`` to created directory.
* Add ``pulp_cli.py`` or ``pulp_shell.py`` as appropriate.
* In the above module, add a ``def initialize(context)`` method.
* The ``context`` object contains the CLI or shell instance that can be manipulated to add the extension's functionality.
