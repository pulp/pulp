Extensions
==========

Overview
--------

The simplest way to describe the pieces of the client is to start with an
example::

 $ pulp-admin rpm repo list --details

In the above command:

 * ``pulp-admin`` is the name of the client script itself.
 * ``rpm`` and ``repo`` are *sections*. A section is used for organization and
   may contain one or more subsections and/or commands.
 * ``list`` is the actual *command* that is being invoked.
 * ``--details`` is a *flag* that is used to drive the command's behavior.
   Commands can accept flags or *options*, the difference being that the latter
   requires a value to be specified (e.g. ``--repo-id demo-1``).

Extensions can add both sections and commands to the client. Commands can be
added to existing sections, however it is typically preferred that commands be
added to a section created by the extension itself (see
:ref:`extensions_conventions` for more information).


Framework Hook
--------------

The starting point for an extension is a single method with the following signature::

 def initialize(context):
   """
   Entry point into the extension, called when the extension is loaded. This
   call should make any additions or changes to the CLI required by the
   extension. The supplied context provides the necessary hooks to access the
   CLI instance as well as functionality for accessing the Pulp server and
   utilities for displaying information to the user.

   :param context: client context in which the extension is being loaded
   :type  context: pulp.client.extensions.core.ClientContext
   """

The sole argument is the client context in which the extension will run (more
information can be found in :ref:`extensions_client_context`. This method may
then delegate to whatever other modules are necessary.


.. _extensions_client_context:

Client Context
--------------

The client context is passed into the extension by the framework when the
extension is initialized. The context is meant to provide all of the
functionality necessary for the extension to interact with both the client
framework and the server itself. The context contains the following pieces:

 * ``cli`` - The cli attribute is the instance of the actual client framework
   itself. This object is used to add new sections to the client or retrieve
   existing ones.
 * ``prompt`` - The prompt is a utility for writing output to the screen as well
   as for reading user input for interactive commands. A number of formatting
   methods are provided to provide a consistent look and feel for the client,
   such as methods to display a header or print an error message.
 * ``server`` - The client framework creates and initializes an
   instance of the server bindings to connect to the configured Pulp server.
   Extensions should use these bindings when making calls against the
   server.
 * ``config`` - The client framework will load all of the
   configuration files and make them accessible to the extension. A separate
   copy of the configuration is supplied to each extension, so changes may be
   made to this object without affecting other extensions.

.. note::
  Currently, the API for the client context is not published. The code can
  be found at ``ClientContext`` in ``client_lib/pulp/client/extensions/core.py``.


.. _extensions_conventions:

Conventions
-----------

In order to prevent collisions among section names, it is suggested that each
type support bundle create a section at the root of the CLI to contain its
extensions. For example, when installed, the RPM support bundle adds a section
called ``rpm`` in the root of the CLI. Commands within apply only to the plugins
and consumers revolving around the RPM-related content types. The Puppet support
bundle provides a similar structure under the root-level section ``puppet``.

Naturally, there will be similarities between different support commands. Each
support bundle will likely have commands to create a repository, customized
with the configuration options relevant to that bundle's server plugins.
Similarly, the command to sync a repository will be present in each bundle's
section, with specific handling to render the progress report.

To facilitate those similarities, the ``pulp.client.commands`` package provides
a number of reusable commands for common tasks, such as displaying a list of
repositories or adding schedules for an operation. It is preferred that an
extension subclass these reusable commands and use their integration points to
customize them to your needs.

.. note::
  Again, the API for these reusable commands is not yet published. The code
  can be found under ``client_lib/pulp/client/commands``.


Installation
------------

.. _extensions_entry_points:

Entry Points
^^^^^^^^^^^^

Your extension should define a method that will be an entry point. It should
accept one argument and return ``None``. The convention is to use this definition:

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
the default priority level. The default is found in
``pulp.client.extensions.loader.DEFAULT_PRIORITY``, and its value is 5 as of
this writing.

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

.. _extensions_directory:

Directory Loading
^^^^^^^^^^^^^^^^^

For one-off testing purposes, the code for an extension can be placed directly
in a specific directory without the need to install to site-packages. The entry
point method described above is the preferred way to integrate new extensions:

* Create directory in ``/usr/lib/pulp/admin/extensions/`` or ``/usr/lib/pulp/consumer/extensions/``
* Add ``__init__.py`` to created directory.
* Add ``pulp_cli.py`` or ``pulp_shell.py`` as appropriate.
* In the above module, add a ``def initialize(context)`` method.
* The ``context`` object contains the CLI or shell instance that can be
  manipulated to add the extension's functionality.
