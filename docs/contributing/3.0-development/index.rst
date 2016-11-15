.. warning::
    All documents within the 3.0-Development section should be considered temporary, and will be removed or relocated prior to the release of Pulp 3.0.

Pulp 3 and Python 3
===================

Pulp 3 will only support Python 3.4+. When introducing new dependencies to Pulp,
ensure they support Python 3 (see http://fedora.portingdb.xyz/). If they do not,
please file an issue in Redmine (related to https://pulp.plan.io/issues/2247) to
track the conversion of the dependency to support Python 3 and begin working with
upstream to convert the package.


3.0 Development
===============

The goal of this section is to create a place for living documents related to the development of Pulp 3.0. Some parts may grow and replace current documentation (plugin API) and others may be temporary guides to making changes (translating from Mongo to Postgres).

.. toctree::
   :maxdepth: 3

   data-modeling
   db-translation-guide
   rest-api
