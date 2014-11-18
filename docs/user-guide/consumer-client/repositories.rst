Repository Search
=================

For each type of content supported, you can use Pulp's
:ref:`criteria` search feature to search repositories. For example, to find a specific
repo by its id:

::

  $ pulp-consumer rpm repos --str-eq="id=zoo"
  +----------------------------------------------------------------------+
                                Repositories
  +----------------------------------------------------------------------+

  Id:                  zoo
  Display Name:        zoo
  Description:         None
  Content Unit Counts: 
  Last Unit Added:     None
  Last Unit Removed:   None
  Notes:


