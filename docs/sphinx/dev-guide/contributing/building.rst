Building Instructions
=====================

Getting Started
---------------

Concepts
^^^^^^^^

There are some concepts you should internalize before you begin making builds. Koji has a concept
called tags. A tag is essentially a grouping of package builds, and it maps to a Yum repository.
Pulp uses one Koji tag per Pulp release stream, per distribution, per architecture. Pulp uses three
release streams per release, corresponding to development, testing, and production. In Koji, these
three concepts map to "testing", "beta", and "" (empty string) in our tag names respectively.

This table maps the git branches to their appropriate Koji tags::

    +---------------+-----------------------------------+
    | Git Branch    | Koji Tag per <distribution>       |
    +===============+===================================+
    | <X.Y>-dev     | pulp-<X.Y>-testing-<distribution> |
    +---------------+-----------------------------------+
    | <X.Y>-testing | pulp-<X.Y>-beta-<distribution>    |
    +---------------+-----------------------------------+
    | <X.Y>-release | pulp-<X.Y>-<distribution>         |
    +---------------+-----------------------------------+

.. warning:

   Note the potential confusion that the X.Y-testing branch maps to the pulp-X.Y-beta-rhel7 tag, not
   the pulp-X.Y-testing-rhel7 tag. It could be wise for us to resolve this by renaming our Koji
   tags to correspond to our dev, testing, and release branch names, but at this time this is how
   they map.

For example, the 2.4 release stream in Pulp platform has three git branches, 2.4-dev, 2.4-testing,
and 2.4-release. For RHEL 7, these map to pulp-2.4-testing-rhel7, pulp-2.4-beta-rhel7, and
pulp-2.4-rhel7, respectively. You can see the full list of Pulp's Koji tags
`here <http://koji.katello.org/koji/search?match=glob&type=tag&terms=pulp*>`_.

Another thing to know about Koji is that once a particular NEVRA is built in Koji, it cannot be
built again. However, it can be tagged into multiple Koji tags. For example, if
python-celery-3.1.11-1.el7.x86_64 is built into the pulp-2.4-beta-rhel7 tag and you wish to add
that exact package in the pulp-2.4-rhel7 tag, you cannot build it again. Instead, you must tag that
package for the new tag. You will see later on in this document that Pulp has a tool to help you do
this.

What you will need
^^^^^^^^^^^^^^^^^^

TODO

Configuring your build environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are interested in building Pulp, it is strongly recommended that you use a separate checkout
from your normal development environment to avoid any potential errors (such as building in local
changes, or building the wrong branches). Thus, the first step is to make a clean checkout of the
three Pulp repositories, and put them somewhere away from your other checkouts::

    $ mkdir ~/pulp_build
    $ cd ~/pulp_build
    $ git clone git@github.com:pulp/pulp.git
    $ git clone git@github.com:pulp_puppet/pulp.git
    $ git clone git@github.com:pulp_rpm/pulp.git

The next step is to install and configure the Koji client on your machine. You will need to put the
Katello CA certificate and your client certificate in your home folder::

    $ sudo yum install koji

Here is an example $HOME/.koji/config file you can use::

    ``
    [koji]

    ;configuration for koji cli tool

    ;url of XMLRPC server
    server = http://koji.katello.org/kojihub

    ;url of web interface
    weburl = http://koji.katello.org/koji

    ;url of package download site
    topurl = http://koji.katello.org/

    ;path to the koji top directory
    ;topdir = /mnt/koji

    ;configuration for SSL athentication

    ;client certificate
    cert = ~/.katello.cert

    ;certificate of the CA that issued the client certificate
    ca = ~/.katello-ca.cert

    ;certificate of the CA that issued the HTTP server certificate
    serverca = ~/.katello-ca.cert
    ``

Make sure you install your Katello CA certificate and client certificate to the paths listed in the
example above::

    $ cp <katello CA> ~/.katello-ca.cert
    $ cp <katello client cert> ~/.katello.cert

If all went well, you should be able to say hello to Koji::

    $ [rbarlow@notepad]~% koji moshimoshi
    olá, rbarlow!

    You are using the hub at http://koji.katello.org/kojihub

Next, you should install Tito::

    $ sudo yum install tito

Now you are ready to begin building.


Building Dependencies
---------------------

Tagging Existing Builds
^^^^^^^^^^^^^^^^^^^^^^^

TODO

Updating Dependency Versions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO

Adding New Dependencies
^^^^^^^^^^^^^^^^^^^^^^^

TODO

Building Pulp, RPM Support, and Puppet Support
----------------------------------------------

TODO

Publishing The Build
--------------------

TODO
