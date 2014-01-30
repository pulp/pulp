Binding
=======

Once a consumer is registered to a Pulp server, it can then :term:`bind <binding>`
to a repository. Binding allows content from a specific repository on the server
to be installed on the consumer. Installation of content can be initiated either
on the consumer or from the server. For example, in the case of RPM content,
binding sets up a repository as a normal yum repository on the consumer. Packages
can be installed with normal yum commands or by initiating an install through
the Pulp server.

Bind
----

Binding to a server requires the consumer to first register. Then a bind command
can be issued for a specific repository. Similar to the ``pulp-admin`` command,
type-specific operations such as ``bind`` are located under a section bearing
the type's name.

::

  $ pulp-consumer rpm bind --repo-id=zoo
  Bind tasks successfully created:

  Task Id: 6e48ce85-60a0-4bf6-b2bb-9617eb7b3ef3

  Task Id: 5bfe25f6-7325-4c29-b6e7-7e8df839570c

Looking at the consumer history, the first action in the list is a bind action
to the specified repository.

::

  $ pulp-consumer history --limit=1
  +----------------------------------------------------------------------+
                          Consumer History [con1]
  +----------------------------------------------------------------------+

  Consumer Id:  con1
  Type:         repo_bound
  Details:
    Distributor Id: yum_distributor
    Repo Id:        zoo
  Originator:   SYSTEM
  Timestamp:    2013-01-02T22:01:17Z


.. note::
  It may take a few moments for the bind to take effect. It happens asynchronously
  in the background, and we are working on a way to show positive confirmation of
  success from ``pulp-consumer``.

Unbind
------

Unbinding is equally simple.

::

  $ pulp-consumer rpm unbind --repo-id=zoo
  Unbind tasks successfully created:

  Task Id: 0c02d974-cf00-44b7-9b63-cdadfc9bfab7

  Task Id: 947b03a6-6911-42c6-a8ce-3161bed08b15

  Task Id: 358e9d1e-8531-4bbd-a8e8-ab64d596b345o

Looking at the history, it is clear that the consumer is no longer bound to the
repository.

::

  $ pulp-consumer history --limit=1
  +----------------------------------------------------------------------+
                          Consumer History [con1]
  +----------------------------------------------------------------------+

  Consumer Id:  con1
  Type:         repo_unbound
  Details:
    Distributor Id: yum_distributor
    Repo Id:        zoo
  Originator:   SYSTEM
  Timestamp:    2013-01-02T22:09:47Z

In case a consumer is bound to a repository on a Pulp server that is no longer
available, the ``--force`` option will make all of the local changes necessary
to unbind from the remote repository without requiring the server to participate.
When using this option, make sure a similar action is taken on the server so it
does not continue to track a binding with the consumer.
