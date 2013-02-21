Building RPMs
=============

Pulp repositories are configured to be built with the `tito <https://github.com/dgoodwin/tito>`_ tool.
Each build is done against a git tag. The steps are done per git repository and are as follows:

::

 $ cd <git repo root>
 $ tito tag
 $ git push && git push --tags
 $ tito build --rpm

The tito output will indicate the directory the RPMs are built into. The ``--srpm`` flag can be
passed to tito to request SRPMs be built as well.

.. note::
 When testing spec file changes, it is suggested to fork the Pulp repositories into your personal
 GitHub account. That way, any tags created will not affect the Pulp repositories themselves.
