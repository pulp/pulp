Repository Binding
==================

The Pulp consumer client can be used to manage Pulp :term:`bindings <binding>`
for the registered consumer.  Binding to a Pulp repository creates an association
between the consumer and the specified repository on the Pulp server.  The binding
enables the consumer to access content using :term:`yum`.  Following a successful
``bind`` or ``unbind`` command, the :term:`pulp.repo` is updated to ensure that the
corresponding entry for the binding has been added, updated or removed as appropriate.
Files such as x.509 keys & certificates and GPG keys referenced in the affected
``pulp.repo`` entry are installed or uninstalled on the consumer as needed.


Bind to a Repository
--------------------

The ``bind`` command is used to create a :term:`binding`.

The following parameters are required:

``--repo-id``
  The unique identifier for a Pulp repository.


Unbind from a Repository
------------------------

The ``unbind`` command is used to remove an existing :term:`binding`.

The following parameters are required:

``--repo-id``
  The unique identifier for a Pulp repository.