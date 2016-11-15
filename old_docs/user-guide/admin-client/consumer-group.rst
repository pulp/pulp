Consumer Groups
===============

Consumer Groups allow you to associate any number of consumers with a named group
and perform different actions on it.

::

    $ pulp-admin rpm consumer group --help

    Usage: pulp-admin [SUB_SECTION, ..] COMMAND
    Description: consumer group commands

    Available Sections:
      members - manage members of repository groups
      package - consumer group package installation management

    Available Commands:
      bind   - binds each consumer in a consumer group to a repository
      create - creates a new consumer group
      delete - deletes a consumer group
      list   - lists consumer groups on the Pulp server
      search - searches for consumer groups on the Pulp server
      unbind - unbinds each consumer in a consumer group from a repository
      update - updates the metadata about the group itself (not its members)


Create, Update, Delete
----------------------

To create a consumer group, the only required argument is a unique ID.

::

    $ pulp-admin rpm consumer group create --group-id test-group

    Consumer Group [test-group] successfully created

The ``update`` command takes similar arguments to the ``create`` command.
This call updates metadata about the consumer group itself (not the members).

::

    $ pulp-admin rpm consumer group update --group-id test-group --display-name new-name

    Consumer Group [test-group] successfully updated

The new consumer group can be seen with its unique ID and display name.

::

    $ pulp-admin rpm consumer group list
    +----------------------------------------------------------------------+
                              Consumer Groups
    +----------------------------------------------------------------------+

    Id:           test-group
    Display Name: new-name
    Description:  None
    Consumer Ids: 
    Notes: 

Consumer groups can be removed from the Pulp server using the delete command.
Deleting a consumer group has no effect on the consumers that are members of the group.

::

    pulp-admin rpm consumer group delete --group-id test-group

    Consumer Group [test-group] successfully deleted


Group membership
----------------

Consumers can be associated and unassociated with any existing consumer group.

::

    $ pulp-admin rpm consumer group members

    Usage: pulp-admin [SUB_SECTION, ..] COMMAND
    Description: manage members of repository groups

    Available Commands:
    add    - add consumers to an existing group
    list   - list the consumers in a particular group
    remove - remove consumers from a group

The call is idempotent if the consumer is already memeber of the group.

::

    $ pulp-admin rpm consumer group members add --group-id test-group --str-eq='id=consumer1'

    Consumer Group [test-group] membership updated

    $ pulp-admin rpm consumer group list 
    +----------------------------------------------------------------------+
                              Consumer Groups
    +----------------------------------------------------------------------+

    Id:           test-group
    Display Name: None
    Description:  None
    Consumer Ids: consumer1
    Notes:    

    $ pulp-admin rpm consumer group members list --group-id test-group
    +----------------------------------------------------------------------+
                           Consumer Group Members
    +----------------------------------------------------------------------+

    Id:           consumer1
    Display Name: consumer1
    Description:  None
    Notes:   

Now you can see that consumer1 is part of the group.
Similarly, you can remove consumers from consumer groups.

::

    $ pulp-admin rpm consumer group members remove --group-id test-group --str-eq='id=consumer1'

    Consumer Group [test-group] membership updated


Repository Binding
------------------

The ``bind`` command allows to bind each consumer in a consumer group to a repository.

::

    $ pulp-admin rpm consumer group bind --consumer-group-id test-group --repo-id zoo

    Consumer Group [test-group] successfully bound to repository [zoo]

You can also use the ``unbind`` command to unbind each consumer in a consumer group from a repo.

::

    $ pulp-admin rpm consumer group unbind --consumer-group-id test-group --repo-id zoo

    Consumer Group [test-group] successfully unbound from repository [zoo]


Content Management
------------------

This section manages content on each consumer belonging to the group.

::

    $ pulp-admin rpm consumer group package

    Usage: pulp-admin [SUB_SECTION, ..] COMMAND
    Description: consumer group package installation management

    Available Commands:
    install   - install packages
    uninstall - uninstall packages
    update    - update (installed) packages


    $ pulp-admin rpm consumer group package install --name zsh --consumer-group-id test

    This command may be exited via ctrl+c without affecting the request.


    [-]
    Running...

    Install on consumer [c1] succeeded
    +----------------------------------------------------------------------+
                                 Installed
    +----------------------------------------------------------------------+

    Name:    zsh
    Version: 5.0.7
    Arch:    x86_64
    Repoid:  updates-testing


Search
------

For more targeted results than the ``list`` command provides, you can use Pulp's
:ref:`criteria` search feature to search consumer groups. For example, to find a specific
consumer group that has id 'test':

::

    $ pulp-admin rpm consumer group search --str-eq='id=test'
    +----------------------------------------------------------------------+
                              Consumer Groups
    +----------------------------------------------------------------------+

    Id:           test
    Display Name: None
    Description:  None
    Consumer Ids: 
    Notes:        
    Scratchpad:   None
