History
=======

Pulp Server keeps track of operations performed on its consumers in the consumer's history. 
The events tracked in the history and their respective event types are as follows:

* Consumer Registered - consumer_registered 
* Consumer Unregistered - consumer_unregistered
* Repository Bound - repo_bound
* Repository Unbound - repo_unbound
* Content Unit Installed - content_unit_installed
* Content Unit Uninstalled - content_unit_uninstalled
* Unit Profile Changed - unit_profile_changed
* Added to a Consumer Group - added_to_group 
* Removed from a Consumer Group - removed_from_group

Note that only operations that are triggered through Pulp are logged. If the consumer installs a content unit 
through another means (eg. rpm, yum etc.) an event will not be logged. The package profile, however, 
will eventually be sent to the server and will reflect any changes that have been made.

A consumer can view its own history using the *consumer history* command.  A number of query arguments 
may be passed in to the *consumer history* command in order to refine the results. Here are a few
examples of querying consumer history:

::

  $ pulp-consumer history --limit 2 --sort ascending --event-type repo_bound
  +----------------------------------------------------------------------+
                        Consumer History [consumer1]
  +----------------------------------------------------------------------+

  Consumer Id:  test-consumer
  Type:         repo_bound
  Details:      
    Distributor Id: yum_distributor
    Repo Id:        test-repo1
  Originator:   SYSTEM
  Timestamp:    2013-01-17T05:43:36Z


  Consumer Id:  test-consumer
  Type:         repo_bound
  Details:      
    Distributor Id: yum_distributor
    Repo Id:        test-repo2
  Originator:   SYSTEM
  Timestamp:    2013-01-17T05:49:09Z

::

  $ pulp-consumer history --start-date 2013-01-17T19:00:00Z --end-date 2013-01-17T21:00:00Z
  +----------------------------------------------------------------------+
                        Consumer History [consumer1]
  +----------------------------------------------------------------------+

  Consumer Id:  consumer1
  Type:         consumer_registered
  Details:      None
  Originator:   admin
  Timestamp:    2013-01-17T19:14:49Z



