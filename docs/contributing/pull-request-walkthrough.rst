Pull Request Walkthrough
========================

Changes to pulpcore are submitted via `GitHub Pull Requests
<https://help.github.com/articles/about-pull-requests/>`_ to the `pulp
<https://github.com/pulp/pulp>`_ repository. Plugin repositories are listed on the :ref:`plugin
table<plugin-table>`.

TODO(how does django phrase this?)
Especially if you have a major change, it is recommended that you :ref:`chat with us<community>`
before you invest a lot of time into patch.

Checklist
---------

#. `Fork <https://help.github.com/articles/fork-a-repo/>`_ `pulp <https://github.com/pulp/pulp>`_ in
   your GitHub account.
#. :doc:`Install Pulp from source.<dev-setup/index>`
#. Create a new branch from the :ref:`appropriate base branch<git-branch>`
#. Make changes, keeping the :doc:`style-guide` in mind
#. Add :doc:`unit tests<testing>` where appropriate.
#. Write TODO(pulp smash)  github issues where appropriate.
#. Update any relevent :doc:`documentation`.
#. TODO(link) Run the linter and unit tests.
#. Check compliance with our :doc:`git` guidelines.
#. Push your branch to your fork and open a `Pull request across forks <https://help.github.com/articles/creating-a-pull-request-from-a-fork/>`_.

Review
------

Travis, ?core team?, merge
