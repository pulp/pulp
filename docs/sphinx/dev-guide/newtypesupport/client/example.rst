:orphan:

Extension Example
=================

This example will cover creating an extension with a single command, found in
a new section at the root of the CLI. The full command will be::

 $ pulp-admin example demo --name Jay --show-date


Framework Hook
--------------

The first step is to create the method the framework will invoke when loading
the extension. This method should create the necessary objects to populate the
CLI with the extension's additions.

For this demo, the context is held in a global variable so it can be accessed
when the command is run.

.. code-block:: python

  CONTEXT = None
  def initialize(context):
      global CONTEXT
      CONTEXT = context

Sections
--------

There are two ways to add a new section to either the root of the CLI directly
or to another section. One approach is to manually instantiate the
``pulp.client.extensions.extensions.PulpCliSection`` class, optionally
subclassing it to add any needed enhancements. The instantiated object is then
added to the CLI using the ``add_section`` call or to a parent section with
the ``add_subsection`` call.

The other approach is to use the ``create_section`` helper method found in
the CLI instance itself or the ``create_subsection`` call in
other ``PulpCliSection`` instances. The demo will use the latter approach.

The ``create_section`` call takes the name of the section (i.e. the text that
will be used on the command line directly) and a description for help text
purposes. The ``PulpCliSection`` instance is returned from the call so it can
be further manipulated. The CLI instance is retrieved from the client context.

.. code-block:: python

  ex_section = context.cli.create_section('example', 'Example section')

At this point, if this extension was installed, the new section would appear
in the usage. Installation is covered later in this document.

::

 $ pulp-admin
 Usage: pulp-admin [SUB_SECTION, ..] COMMAND

  Available Sections:
    auth     - manage users, roles and permissions
    bindings - search consumer bindings
    event    - subscribe to event notifications
    example  - Example section
    orphan   - find and remove orphaned content units
    puppet   - manage Puppet-related content and features
    repo     - list repositories and manage repo groups
    rpm      - manage RPM-related content and features
    server   - display info about the server
    tasks    - list and cancel server-side tasks


Commands
--------

Commands associate the user request with the method that will handle it. Commands are added to
sections using a similar approach as with sections. The command can be manually
instantiated from the ``pulp.client.extensions.extensions.PulpCliCommand``
class and added to a section with the ``add_command`` method.

Alternatively, a helper method named ``create_command`` can be used to do both
the instantiation and add it to a section. This call accepts three parameters.
The first is the name of the command which is used to invoke it from the command
line. The second is the description, displayed when viewing the usage of the
command. The third is a reference to the method to run when the command is
executed.

The following snippet creates our demo command and ties it to the ``run_demo``
method.

.. code-block:: python

  demo_command = ex_section.create_command('demo', 'Demo command', run_demo)

The referenced ``run_demo`` must be defined as a method, otherwise the extension
will fail to load. We'll expand on this in the next section, but a simple
implementation is as follows.

.. code-block:: python

  def run_demo(**kwargs):
    CONTEXT.prompt.write('Hello World')


Options and Flags
-----------------

While some commands can simply be executed as is, many will need to accept
user input. These are referred to as *options* and *flags*. Both can be created
by running the appropriate ``create_*`` method on the command instance.

For the demo, we'll add an option that accepts the user's name and a flag that
toggles whether or not the date is printed.

.. code-block:: python

  demo_command.create_option('--name', 'Name of the user', required=True)
  demo_command.create_flag('--show-date', 'If specified, the date will be displayed')

The above snippet configures the ``--name`` option as required. The client
framework will enforce that, displaying the usage text to the user in the event it
is not specified.

.. code-block:: python

  $ pulp-admin example demo
  Command: demo
  Description: Demo command

  Available Arguments:

    --name      - (required) Name of the user
    --show-date - If specified, the date will be displayed

  The following options are required but were not specified:
    --name

The client framework will capture the input and make it available to the command's
execution method in its ``kwargs`` argument. The name of the option/flag is used
as the key and the user input is the value (or ``True`` in the case of a flag).
Below is the ``run_demo`` method from above, enhanced to take advantage of our
newly added options and flags.

.. code-block:: python

  def run_demo(**kwargs):
      CONTEXT.prompt.write('Hello %s' % kwargs['name'])
      if kwargs['show-date']:
          CONTEXT.prompt.write(datetime.datetime.now())

Example usage:

::

  $ pulp-admin example demo --name Jay
  Hello Jay

  $ pulp-admin example demo --name Jay --show-date
  Hello Jay
  2013-02-07 14:54:14.587727


Installation
------------

Instructions on packaging and installing extensions for production deployment
can be found at :ref:`extensions_entry_points`.

For simplicity, this demo will install the extension using the
directory approach. More information can be found in the
:ref:`extensions_directory` section of this guide.

 * Create ``/usr/lib/pulp/admin/extensions/example``
 * Create an empty file in that directory named ``__init__.py``
 * Copy the file containing this demo code to that directory, naming it
   ``pulp_cli.py``

When the ``pulp-admin`` script is run, the usage text will show the
``example`` section created from this demo.


Full Example
------------

.. code-block:: python

  import datetime

  CONTEXT = None

  def initialize(context):
      global CONTEXT
      CONTEXT = context

      ex_section = context.cli.create_section('example', 'Example section')
      demo_command = ex_section.create_command('demo', 'Demo command', run_demo)
      demo_command.create_option('--name', 'Name of the user', required=True)
      demo_command.create_flag('--show-date', 'If specified, the date will be displayed')

  def run_demo(**kwargs):
      CONTEXT.prompt.write('Hello %s' % kwargs['name'])
      if kwargs['show-date']:
          CONTEXT.prompt.write(datetime.datetime.now())

