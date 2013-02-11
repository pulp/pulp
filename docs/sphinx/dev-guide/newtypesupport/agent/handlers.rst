Handlers
========

Overview
--------

An agent handler provides an implementation of predefined capabilities within the Pulp
agent for a specific content type or operating system.  Each handler is defined using a
configuration file, called a *descriptor*.  In addition to handler configuration, the
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


The Handler Descriptor
----------------------

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
 class=PackageHandler
 import_key=1
 permit_reboot=1

 [puppet]
 class=PuppetHandler

 [tar]
 class=TarHandler
 preserve_permissions=1

 [yum]
 class=YumBindHandler
 ssl_verify=0

 [Linux]
 class=LinuxHandler
 reboot_delay=10



In this example, the ``[types]`` section lists support for the ``rpm``, ``puppet``
and ``tar`` content types.  Notice that there are the corresponding sections named ``[rpm]``
``[puppet]`` and ``[tar]`` that map the handler class and specify type specific
configuration.  This pattern is repeated for the ``bind`` and ``system`` properties.