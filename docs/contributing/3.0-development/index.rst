.. warning::
    All documents within the 3.0-Development section should be considered temporary, and will be
    removed or relocated prior to the release of Pulp 3.0.

3.0 Development
===============

The goal of this section is to create a place for living documents related to the development of
Pulp 3.0. Some parts may grow and replace current documentation (plugin API) and others may be
temporary guides to making changes (translating from Mongo to Postgres).

.. toctree::
   :maxdepth: 3

   app-layout
   data-modeling
   db-translation-guide
   rest-api

Pulp 3 and Python 3
-------------------

Pulp 3 will only support Python 3.5+. When introducing new dependencies to Pulp,
ensure they support Python 3 (see http://fedora.portingdb.xyz/). If they do not,
please file an issue in Redmine (related to https://pulp.plan.io/issues/2247) to
track the conversion of the dependency to support Python 3 and begin working with
upstream to convert the package.

Docstrings
----------

`PUP-2 <https://github.com/pulp/pups/blob/master/pup-0002.md>`_ adopted Google style for
:ref:`google-docstrings`. When porting code from Pulp 2 to Pulp 3, convert all the docstrings to the
new style. vim-style regexes can be used to speed up the process. Together, these will convert all
of the parameters to Google Style::

    # Typed params
    %s/\(\s*\):param\s\+\(.*\):\s\+\(.*\)\n\s*:type\s\+.\+:\s\+\(.*\)/\1 \2 (\4): \3

    # Untyped params
    %s/\(\s*\):param\s\+\(.*\):\s\+\(.*\)/\1 \2: \3
