Repository Search
=================

For each type of content supported, you can use Pulp's
:ref:`criteria` search feature to search repositories. For example, to find all
RPM repositories that contain at least one content unit:

::

  $ pulp-consumer rpm repos --gt 'content_unit_count=0'
  +----------------------------------------------------------------------+
                                Repositories
  +----------------------------------------------------------------------+

  Id:                 pulp
  Display Name:       pulp
  Description:        None
  Content Unit Count: 39
  Notes:

  Id:                 repo1
  Display Name:       repo1
  Description:        None
  Content Unit Count: 36
  Notes:
