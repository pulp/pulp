Documentation
=============

Principles
----------

Pulp's documentation is designed with the following principles:

#. Docs (other than quickstarts) should avoid documenting external projects, providing links instead wherever
   reasonable.
#. Documentation Layout should be designed for users to intuitively be able to find information, and
   they should see introductory material before advanced topics.
#. Documentation should make heavy use of cross references to limit repitition.
#. Pulp specific terminology should be be defined and added to the glossary.
#. Documentation should stay consistent with the language used in the :ref:`/overview/concepts`.
#. Each guide (being a set of documents to be consumed together) should contain:
   #. Summary of content
   #. Intended audience.
   #. Links to prerequisite material
   #. Links to related material

Building the Docs:
------------------

If you are using a developer Vagrant box, the docs requirements should already be installed.

Otherwise, (in your virtualenv), you should install the docs requirements, which live in the "docs"
directory of the pulp/pulp repository::

    (pulp) $ pip install -r docs/requirements.txt

To build the docs, simply use ``make``::

    (pulp) $ make html

Use your browser to load the generated html, which lives in ``docs/_build/html/``

You do not need to clean the docs before rebuilding, however you can do it by running::

    (pulp) $ make clean
