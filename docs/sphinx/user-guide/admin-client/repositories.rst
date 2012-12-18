Repositories
============

This guide covers core features for managing repositories in the Pulp Platform.
For more detail about how to work with repositories of a specific content type,
please visit the user guide for that type. Examples will use "rpm" as the demo
type when necessary, but they will be limited to generic features.

Layout
------

The root level ``repo`` section contains the following features. These features
apply across all repositories, regardless of the specific types of content they
will support.

::

  $ pulp-admin repo --help
  Usage: pulp-admin repo [SUB_SECTION, ..] COMMAND
  Description: list repositories and manage repo groups

  Available Sections:
    group - repository group commands
    tasks - list and cancel tasks related to a specific repository

  Available Commands:
    list - lists repositories on the Pulp server

By comparison, many other features are implemented under a root-level section
named for a content type. For example, the RPM repo section looks like this:

::

  $ pulp-admin rpm repo --help
  Usage: pulp-admin repo [SUB_SECTION, ..] COMMAND
  Description: repository lifecycle commands

  Available Sections:
    content - search the contents of a repository
    copy    - copies one or more content units between repositories
    export  - run or view the status of ISO export of a repository
    publish - run, schedule, or view the status of publish tasks
    remove  - remove copied or uploaded modules from a repository
    sync    - run, schedule, or view the status of sync tasks
    uploads - upload modules into a repository

  Available Commands:
    create - creates a new repository
    delete - deletes a repository
    list   - lists repositories on the Pulp server
    search - searches for RPM repositories on the server
    update - changes metadata on an existing repository

The reason for putting repository commands in different places is that some
features will be customized and augmented by plugins, such that their versions of
common commands will only be applicable to their own content. Commands that can
operate on all repositories go in the generic "repo" section.


Create, Update, Delete
----------------------------

To create a repository, the only required argument is a unique ID. Consult the
help text for the create command of each particular repository type to see what
other options are available.

::

  $ pulp-admin rpm repo create --repo-id=foo
  Successfully created repository [foo]

The ``update`` command takes similar arguments to the ``create`` command.

::

  $ pulp-admin rpm repo update --repo-id=foo --display-name='Foo Repo'
  Repository [foo] successfully updated

The new repository can be seen with its unique ID and display name.

::

  $ pulp-admin rpm repo list
  +----------------------------------------------------------------------+
                              RPM Repositories
  +----------------------------------------------------------------------+

  Id:                 foo
  Display Name:       Foo Repo
  Description:        None
  Content Unit Count: 0

Deleting a repository is an asynchronous operation. In case other tasks are
already in progress on this repository, the server will allow those tasks to
complete before executing the deletion. The example below shows how to request
deletion and then check the status of that task.

::

  $ pulp-admin rpm repo delete --repo-id=foo
  The request to delete repository [foo] has been received by the server. The
  progress of the task can be viewed using the commands under "repo tasks"

  $ pulp-admin repo tasks list --repo-id=foo
  +----------------------------------------------------------------------+
                                   Tasks
  +----------------------------------------------------------------------+

  Operations:  delete
  Resources:   foo (repository)
  State:       Successful
  Start Time:  2012-12-17T23:17:46Z
  Finish Time: 2012-12-17T23:17:46Z
  Result:      N/A
  Task Id:     2d4fc3da-7ad7-448c-a9dd-78e79f71ef2f


List
----

This command lists all repositories in Pulp, regardless of their content type. To
list and search repositories only of a particular type, go to that type's area of
the CLI, such as ``pulp-admin rpm repo list``.

::

  $ pulp-admin repo list
  +----------------------------------------------------------------------+
                                Repositories
  +----------------------------------------------------------------------+

  Id:                 pulp
  Display Name:       Pulp
  Description:        Pulp's stable repository
  Content Unit Count: 39

  Id:                 repo1
  Display Name:       repo1
  Description:        None
  Content Unit Count: 0

  Id:                 repo2
  Display Name:       repo2
  Description:        None
  Content Unit Count: 0


Copy Between Repositories
-------------------------

Content units can be copied from one repository to another. For content units
that involve an on-disk file (such as RPMs having a package stored on disk), the
file is only stored once even if it is included in multiple Pulp repositories.

The following example assumes that the repository "foo" has some content units
and that we want to copy them to the repository "bar".

::

  $ pulp-admin rpm repo copy rpm --from-repo-id=foo --to-repo-id=bar
  Progress on this task can be viewed using the commands under "repo tasks".

  $ foo-admin repo tasks list --repo-id=foo
  +----------------------------------------------------------------------+
                                   Tasks
  +----------------------------------------------------------------------+

  Operations:  associate
  Resources:   bar (repository), foo (repository)
  State:       Successful
  Start Time:  2012-12-17T23:27:12Z
  Finish Time: 2012-12-17T23:27:13Z
  Result:      N/A
  Task Id:     8c3a6964-245f-4fe5-9d7c-8c6bac55cffb

The copy was successful. Here you can see that the repository "bar" now has the
same number of content units as "foo".

::

  $ pulp-admin rpm repo list
  +----------------------------------------------------------------------+
                              RPM Repositories
  +----------------------------------------------------------------------+

  Id:                 foo
  Display Name:       foo
  Description:        None
  Content Unit Count: 36

  Id:                 bar
  Display Name:       bar
  Description:        None
  Content Unit Count: 36


Groups
------

Repository Groups allow you to associate any number of repositories, even of
varying content types, with a named group. Features that make use of repository
groups are forthcoming in future releases of Pulp.

Here is an example of creating a repo group and adding members to it:

::

  $ pulp-admin repo group create --group-id='group1' --description='misc. repos' --display-name='Group 1'
  Repository Group [group1] successfully created

  $ pulp-admin repo group members add --group-id=group1 --str-eq='id=repo1'
  Successfully added members to repository group [group1]

.. TODO link this to a section explaining criteria-based search

The ``members add`` command takes advantage of Pulp's generic search feature, so
you can add many repositories at once. In this case, we provided a specific
repository name. Let's look at the result of these two commands by listing the
repository groups.

::

  $ pulp-admin repo group list
  +----------------------------------------------------------------------+
                             Repository Groups
  +----------------------------------------------------------------------+

  Id:           group1
  Display Name: Group 1
  Description:  misc. repos
  Repo Ids:     repo1
  Notes:

Notice that "repo1" shows up in the "Repo Ids" field.


Tasks
-----

Some operations on repositories, such as ``sync``, ``publish``, and ``delete``, may operate
asynchronously. When you execute these operations, Pulp will give you a "task ID".
You can use that task ID to check the status of the operation. From this section
of the CLI, you can ``cancel``, ``list``, and get ``details`` about repository tasks.

::

  $ pulp-admin repo tasks --help
  Usage: pulp-admin tasks [SUB_SECTION, ..] COMMAND
  Description: list and cancel tasks related to a specific repository

  Available Commands:
    cancel  - cancel one or more tasks
    details - displays more detailed information about a specific task
    list    - lists tasks queued or running in the server

