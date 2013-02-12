Handlers
========

Overview
--------

The pulp agent supports an API for remote operations.  These operations can be divided into
those that are type-specific and those that are not.  In this context, type-specific
includes a wide variety of Pulp conceptual types.  Just as the handling of these types is
pluggable within the Pulp server, they are also pluggable within the Pulp agent.  The agent
delegates the implementation of type-specific operations to the appropriate handler.

The collection of type-specific operations is logically grouped into capabilities to support
a good division of responsibility within handlers.  An agent handler provides an
implementation of one or more of these predefined capabilities.  Each handler is defined
using a configuration file, called a *descriptor*.  In addition to handler configuration, the
descriptor associates capabilities with Python classes that are contributed by the handler.
The mapping of capabilities to handler classes is qualified by a *type* ID that is
appropriate to the capability.

Handler capabilities are as follows:

* The **bind** capability is a collection of agent operations responsible for updating the
  consumer's configuration so that it can consumer content from a specific Pulp repository.
  Handler classes are mapped to the *bind* capability by distributor type ID.
* The **content** capability is a collection of agent operations responsible for installing,
  updating, and uninstalling content on the consumer.  Handler classes are mapped to the
  *content* capability by content type ID.
* The **system** capability is a collection of agent operations responsible for operating
  system level operations.  Handler classes are mapped to the *system* capability using
  the operating system type as defined to the Python interpreter.

The Pulp agent API is segmented into similar capabilities.  When a remote operation request
is received by the agent, the implementation is delegated to appropriate handler based on
the *type* of the object that is the subject of the operation.

For example, the installation of a content unit of type ``tarball`` would be delegated to
the ``install()`` method an instance of the handler class mapped to the *content*
capability and type ID of ``tarball``.


.. _handler_descriptors:

Handler Descriptors
-------------------

The handler descriptor declares and configures an agent handler.  It is an INI formatted
text file that is installed into ``/etc/pulp/agent/conf.d/``.  A descriptor has two required
sections.  The ``[main]`` section defines global handler properties and the ``types`` section
is used to map types to handler classes.

The ``[main]`` section has a required ``enabled`` property.  The handler is loaded into
the agent if enabled evaluates to as defined by Pulp common configuration.

The ``[types]`` section supports three optional properties that correspond to handler capabilities.
The ``[content]`` property is a comma delimited list of Pulp content types that are supported
by handler.  The values listed must correspond to content types defined within the Pulp
platform ``types`` inventory.  The ``bind`` property is a comma delimited list of Pulp
distributor types.  The values listed must correspond to the distributor_type_id of an
installed distributor plugin.  Lastly, the system property is a single value that must
correspond to the operating system name as reported in python by ``os.uname()``.

For each type listed in the content, bind and system properties, there must be a
corresponding section with the same name.  This section has a required ``class`` property
that is used to specify a python class contributed by the handler.  The value of ``class``
must be fully package qualified if it is to be loaded from the python path.  More about this
in the installation section.  In addition to the ``class`` property, this section supports
the inclusion of arbitrary property names which are passed to the specified handler class
as configuration.

Let's take a look at an example::

 [main]
 enabled=1

 [types]
 content=rpm,puppet,tar
 bind=yum
 system=Linux

 [rpm]
 class=pulp_rpm.agent.handler.PackageHandler
 import_key=1
 permit_reboot=1

 [puppet]
 class=pulp_puppet.agent.handler.PuppetHandler

 [tar]
 class=pulp_tar.agent.handler.TarHandler
 preserve_permissions=1

 [yum]
 class=pulp_rpm.agent.handler.YumBindHandler
 ssl_verify=0

 [Linux]
 class=pulp.agent.handler.LinuxHandler
 reboot_delay=10

In this example, the ``[types]`` section lists support for the ``rpm``, ``puppet``
and ``tar`` content types.  Notice that there are the corresponding sections named ``[rpm]``
``[puppet]`` and ``[tar]`` that map the handler class and specify type specific
configuration.  This pattern is repeated for the ``bind`` and ``system`` properties.

.. _handler_classes:

Handler Classes
---------------

The functionality contributed by agent handlers is implemented in handler classes.  The
required API for each class is dictated by the capability to which it's mapped.  For each
capability there is a corresponding abstract base class.

The base classes for each capability is as follows:

* Classes that provide the **content** capability must extend the ``ContentHandler``
  base class and override each method.
* Classes that provide the **bind** capability must extend the ``BindHandler``
  base class and override each method.
* Classes that provide the **system** capability must extend the ``SystemHandler``
  base class and override each method.

.. note::
 Currently, the APIs for the handler base classes are not published. The code can
 be found in ``platform/src/pulp/agent/lib/handler.py``.

By convention, each handler class method signature contains a few standard parameters.
The ``conduit`` parameter is an object that provides access to objects within the agent's
environment.  Such as, the consumer configuration, Pulp server API bindings, the consumer's ID
and a progress reporting object.
The ``options``, as it's name suggests, is a dictionary of options which are dictated by
,and appropriate for, the operation's implementation.

.. note::
 Currently, the APIs for the conduit are not published. The code can
 be found in ``platform/src/pulp/agent/lib/conduit.py``.

Reports
-------

For each handler class and method there is a predefined result report class.  Each method
implementation must return the appropriate report object.  The ``HandlerReport`` class
has three attributes.  The ``succeeded`` flag is boolean indicating the overall success of
the operation.  What success means is entirely at the discretion of the handler writer.  The
``details`` attribute is dictionary containing detailed result of the operation.  Last, the
``num_changes`` attribute indicates the total number of changes made to the consumer's
configuration as a result of the operation.  It is intended that the handler writer use
either the ``set_succeeded()`` or the ``set_failed()`` methods to update the report.  The
``succeeded`` attribute is defaulted to True.

.. note::
 Currently, the APIs for the reports are not published. The code can
 be found in ``platform/src/pulp/agent/lib/report.py``.

Exception Handling
------------------

Exceptions raised during handler class method invocation should be caught and either
handled or incorporated into the result report.  Uncaught exceptions are caught by the
agent handler framework, logged and used to construct the appropriate handler report
object.  The report succeeded attribute is set to False and the ``details`` attribute is
updated to contain the following keys:

* message - The exception message.
* trace - A string representation of the stack trace.

Installation
------------

The two components of an agent handler are installed as follows.  The :ref:`handler_descriptors`
are installed in ``/etc/pulp/agent/conf.d``.  The modules containing :ref:`handler_classes`
can be either installed in the python path or installed in ``/usr/lib/pulp/agent/handlers``.
If installed in the python, the ``class`` property in the descriptor must be fully package
qualified.

The Pulp agent must be restarted for handler changes to take effect.

Logging
-------

The pulp agent is implemented using Gofer plugins.  Agent handler log messages are written
to the standard Gofer agent log at ``/var/log/gofer/agent.log``.

Debugging
---------

The following are instructions for running the Pulp agent within the PyCharm debugger.

Figures
-------

.. _handler_mapping_table:

Table mapping types, handler classes and report classes:

+---------+----------------+------------+--------------+
|Type     |Class           |Method      |Report        |
+=========+================+============+==============+
| content | ContentHandler |install     |ContentReport |
+---------+----------------+------------+--------------+
|         |                |update      |ContentReport |
+---------+----------------+------------+--------------+
|         |                |uninstall   |ContentReport |
+---------+----------------+------------+--------------+
|         |                |profile     |ProfileReport |
+---------+----------------+------------+--------------+
| bind    | BindHandler    |bind        |BindReport    |
+---------+----------------+------------+--------------+
|         |                |unbind      |BindReport    |
+---------+----------------+------------+--------------+
|         |                |clean       |CleanReport   |
+---------+----------------+------------+--------------+
| system  | SystemHandler  |reboot      |RebootReport  |
+---------+----------------+------------+--------------+
