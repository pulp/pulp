Handlers
========

Overview
--------

The pulp agent supports an API for remote operations. These operations can be categorized
as those that are type-specific and those that are not. In this context, the term type-specific
includes a wide variety of Pulp conceptual types. Just as the handling of these types is
pluggable within the Pulp server, it is also pluggable within the Pulp agent. The agent
delegates the implementation of type-specific operations to the appropriate handler.

The collection of type-specific operations is logically grouped into named capabilities to
support a good division of responsibility within handlers. An agent handler provides an
implementation of one or more of these predefined capabilities.

Handler capabilities are as follows:

* The **bind** capability is a collection of agent operations responsible for updating the
  consumer's configuration so that it can consumer content from a specific Pulp repository.
  Handler classes are mapped to the *bind* capability by distributor type ID.
* The **content** capability is a collection of agent operations responsible for installing,
  updating, and uninstalling content on the consumer. Handler classes are mapped to the
  *content* capability by content type ID.
* The **system** capability is a collection of agent operations responsible for operating
  system level operations. Handler classes are mapped to the *system* capability using
  the operating system type as defined to the Python interpreter.

Each handler is defined using a configuration file, called a *descriptor*. In addition to
handler configuration, the descriptor associates capabilities with Python classes that are
contributed by the handler. The mapping of capabilities to handler classes is qualified by
a *type* ID that is appropriate to the capability.

When a remote operation request is received by the agent, the implementation is delegated
to an appropriate handler based on the *type* of the object that is the subject of the operation.

For example, the installation of a content unit of type ``tarball`` would be delegated to
the ``install()`` method on an instance of the handler class mapped to the *content*
capability and type ID of ``tarball``.

.. _handler_descriptors:

Handler Descriptors
-------------------

The handler descriptor declares and configures an agent handler. It is an INI formatted
text file that is installed into ``/etc/Pulp/agent/conf.d/``. A descriptor has two required
sections. The ``[main]`` section defines global handler properties, and the ``[types]`` section
is used to map types to handler classes.

The ``[main]`` section has a required ``enabled`` property. The handler is loaded into
the agent if value of enabled is one of: `(true|yes|1)`.

The ``[types]`` section supports three optional properties that correspond to handler capabilities.
The ``[content]`` property is a comma delimited list of Pulp content types that are supported
by the handler. The values listed must correspond to content types defined within the Pulp
platform ``types`` inventory. The ``bind`` property is a comma delimited list of distributor
types supported by the handler. The values listed must correspond to the distributor_type_id
of a distributor plugin currently installed on the Pulp server. Lastly, the system property
is a single value that must correspond to the operating system name as reported in python
by the ``os.uname()`` function.

For each type listed in the content, bind and system properties, there must be a
corresponding section with the same name. This section has a required property named ``class``
that is used to specify a class that provides the capability for the specified type.
In addition to the ``class`` property, these sections support the inclusion of arbitrary
property names and values which are passed to the specified handler class as configuration.

Let's take a look at a descriptor example::

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

In this example, the ``[types]`` section lists support for the ``rpm``, ``puppet``,
and ``tar`` content types. Notice that there are the corresponding sections named ``[rpm]``
``[puppet]``, and ``[tar]`` that map the handler class and specify-type specific
configuration. This pattern is replicated for the ``bind``, and ``system`` properties.

.. _handler_classes:

Handler Classes
---------------

The functionality contributed by agent handlers is implemented in handler classes. The
required API for each class is dictated by the capability to which it's mapped. For each
capability there is a corresponding abstract base class.

The base classes for each capability are as follows:

* Classes that provide the **content** capability must extend the ``ContentHandler``
  base class and override each method.
* Classes that provide the **bind** capability must extend the ``BindHandler``
  base class and override each method.
* Classes that provide the **system** capability must extend the ``SystemHandler``
  base class and override each method.

.. note::
 Currently, the APIs for the handler base classes are not published. The code can
 be found in ``platform/src/pulp/agent/lib/handler.py``.

By convention, each handler class method signature contains two standard parameters.
The ``conduit`` parameter is an object that provides access to objects within the agent's
environment, such as the consumer configuration, Pulp server API bindings, the consumer's ID,
and a progress reporting object. The ``options`` parameter is a dictionary that defines
options used to influence the operation's implementation.

.. note::
 Currently, the APIs for the conduit are not published. The code can
 be found in ``platform/src/pulp/agent/lib/conduit.py``.

Reports
-------

The agent handler framework defines a set of report classes. Each method implementation
must return the appropriate report object. The ``HandlerReport`` has three main attributes.
The ``succeeded`` flag is boolean indicating the overall success of the operation. The
definition of success is entirely at the discretion of the handler writer. The ``details``
attribute is a dictionary containing the detailed result of the operation. Last, the ``num_changes``
attribute indicates the total number of changes made to the consumer as a result of the
operation. It is intended that the handler writer use either the ``set_succeeded()`` or
the ``set_failed()`` methods to update the report. The default value fo the ``succeeded``
attribute is True.

.. _handler_reports:

Table mapping types, handler classes, and report classes:

+---------+----------------+------------+--------------+
|Type     |Class           |Method      |Report        |
+=========+================+============+==============+
| content | ContentHandler |install()   |ContentReport |
+---------+----------------+------------+--------------+
|         |                |update()    |ContentReport |
+---------+----------------+------------+--------------+
|         |                |uninstall() |ContentReport |
+---------+----------------+------------+--------------+
|         |                |profile()   |ProfileReport |
+---------+----------------+------------+--------------+
| bind    | BindHandler    |bind()      |BindReport    |
+---------+----------------+------------+--------------+
|         |                |unbind()    |BindReport    |
+---------+----------------+------------+--------------+
|         |                |clean()     |CleanReport   |
+---------+----------------+------------+--------------+
| system  | SystemHandler  |reboot()    |RebootReport  |
+---------+----------------+------------+--------------+

.. note::
 Currently, the APIs for the reports are not published. The code can
 be found in ``platform/src/pulp/agent/lib/report.py``.

Exception Handling
------------------

Exceptions raised during handler class method invocation should be caught and either
handled or incorporated into the result report. Uncaught exceptions are caught by the
agent handler framework, logged, and used to construct and return the appropriate handler
report object. In this report object, the ``succeeded`` attribute is set to False, and
the ``details`` attribute is updated to contain the following keys:

* message - The exception message.
* trace - A string representation of the stack trace.

Installation
------------

The two components of an agent handler are installed as follows. The :ref:`handler_descriptors`
are installed in ``/etc/pulp/agent/conf.d``. The modules containing :ref:`handler_classes`
can be either installed in the python path or installed in the ``/usr/lib/pulp/agent/handlers``.
directory. If installed in the python path, the ``class`` property in the descriptor must be
package qualified as needed to be found within the python path.

The Pulp agent must be restarted for handler changes to take effect.

Logging
-------

The Pulp agent is implemented using Gofer plugins. Agent handler log messages are written
to syslog.

