How To Contribute
=================

There are three distinct types of contributions that this guide attempts to
support. As such, there may be portions of this document that do not apply to
your particular area of interest.

**Existing Code**
  Add new features or fix bugs in the platform or existing type support
  projects.
**New Type Support**
  Create a new project that adds support for a new content type to Pulp.
**Integration**
  Integrate some other project with Pulp, especially by using the event system
  and REST API.

For New Contributors
^^^^^^^^^^^^^^^^^^^^

If you are interested in contributing to Pulp, the best way is to select a bug
that interests you and submit a patch for it. We use `Bugzilla
<https://bugzilla.redhat.com/buglist.cgi?bug_status=NEW&classification=Community&list_id=2962559&product=Pulp&query_format=advanced&target_release=--->`_
for tracking bugs. Of course, you may have your own idea for a feature or
bugfix as well! You may want to send an email to pulp-list@redhat.com or ask in
the #pulp channel on freenode before working on your feature or bugfix. The
other contributors will be able to give you pointers and advice on how to
proceed. Additionally, if you are looking for a bug that is suitable for a
first-time contributor, feel free to ask.

Pulp is written in Python. While you do not need to be a Python expert to
contribute, it would be advantageous to run through the `Python tutorial
<https://docs.python.org/2/tutorial/>`_ if you are new to Python or programming
in general. Contributing to an open source project like Pulp is a great way to
become proficient in a programming language since you will get helpful feedback
on your code.

Some knowledge of git and GitHub is useful as well. Documentation on both is
available on the `GitHub help page <https://help.github.com/>`_.


Contribution Checklist
^^^^^^^^^^^^^^^^^^^^^^

1. Make sure that you choose the appropriate upstream branch.

   :doc:`Branching <branching>`

2. Test your code. We ask that all new code has 100% coverage.

   :doc:`Testing </dev-guide/policies/testing>`

3. Please ensure that your code follows our style guide.

   :doc:`Style Guide </dev-guide/policies/style>`

4. Please make sure that any new features are documented and that changes are
   reflected in existing docs.

   :doc:`Documentation <documenting>`

5. Please squash your commits and use our commit message guidelines.

   :ref:`rebasing-and-squashing`

6. Make sure your name is in our AUTHORS file found at the root of each of our
   repositories. That way you can prove to all your friends that you
   contributed to Pulp!

Developer Guide
^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 3

   dev_setup
   branching
   merging
   documenting
   bugs
   building
