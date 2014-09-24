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

.. warning::

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

In order to build Pulp, you will need the following from the Katello team:

#. An account on Katello's Koji instance
#. A client certificate for your account
#. The Katello CA certificate

In order to publish builds to the Pulp repository, you will need the ssh keypair used to upload
packages to the fedorapeople.org repository. You can get these from members of the Pulp team.

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


Dependencies
---------------------

Building Dependencies
^^^^^^^^^^^^^^^^^^^^^

If you wish to add or update the version or release of one of our dependencies, you should begin by
adding/updating the dependency's tarball, patches, and spec file in the Pulp git repository as
appropriate for the task at hand. Don't forget to set the version/release in the spec file. Once you
have finished that work, you are ready to test the changes. In the directory that contains the
dependency, use tito to build a test RPM. For example, for python-celery::

    $ cd deps/python-celery
    $ tito build --test --rpm

Pay attention to the output from tito. There may be errors you will need to respond to. If all goes
well, it should tell you the location that it placed some RPMs. You should install these RPMs and
test them to make sure they work with Pulp and that you want to introduce this change to the
repository.

If you are confident in your changes, submit a pull request with the changes you have made so far.
Once someone approves the changes, merge the pull request. Once you have done this, you are ready to
tag the git repository with your changes::

    $ tito tag --keep-version

Pay attention to the output of tito here as well. It will instruct you to push you branch and the
new tag to github.

.. warning::

   It is very important that you perform the steps that tito instructs you to do. If you do not,
   others will not be able to reproduce the changes you have made!

Now you are ready to submit the build to Koji::

    $ cd rel-eng/
    $ ./builder.py --build-dependency <dependency_name> --disable-repo-build <version X.Y> <stream>

Substitute your package name, the major and minor version (leave off the point release), and the
stream you wish to build into. The stream can be "testing", "beta", or "stable". To make the above a
little more concrete, here is an example for building python-celery into the 2.4 testing (alpha)
repository::

    $ ./builder.py --build-dependency python-celery --disable-repo-build 2.4 testing

.. note::
   
   Keep in mind that Koji does not allow rebuilding any package version that has been successfully
   built before. Thus, if you have already built python-celery-3.1.11-1.el7.x86_64 in the testing
   stream and you wish to promote it to the beta stream, you cannot use this command to do that.
   Read the next section to find out how to do this.

Bringing Builds into New Tags
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have built a dependency in Koji and you want it to be included in another Koji tag, you can
use builder.py to tag the correct dependencies in automatically::

    $ ./builder.py --update-tag-package-list <version X.Y> <stream>

Continuing on from our earlier example, if everything was so thrilled with your build of
python-celery-3.1.11-1.el7.x86_64 that you had tagged into 2.4 testing that they wanted it in the
2.4 beta stream, all you have to do is this::

    $ ./builder.py --update-tag-package-list 2.4 beta

.. note::

   This command will tag in all packages that builder.py determines are appropriate for X.Y-stream,
   so don't be surprised if you see it tagging in more packages than just python-celery.

.. note::

   The above command will finish quickly, but it will tell you that you need to manually monitor
   Koji and wait for the repository building tasks to complete. You can view
   `active Koji tasks <http://koji.katello.org/koji/tasks>`_. Do not submit any new Koji tasks until
   these complete.

Building Pulp, RPM Support, and Puppet Support
----------------------------------------------

Are you ready to build the platform, RPM, and Puppet packages? If so, you should cd to the top level
directory where you have checked out all three of those repositories. Ensure that all three
repositories have the branches you wish to build checked out. For example, if you are trying to
build a new 2.4.z beta release, all three repositories should have the 2.4-testing branch checked
out::

    $ for r in {pulp,pulp_puppet,pulp_rpm}; do pushd $r; git checkout 2.4-testing; git pull; popd; done;

At this point, you may wish to ensure that the branches are all merged forward to master. This step
is not strictly required at this point, as we will have to do it again later. However, sometimes
developers forget to do this, and it may be advantageous to resolve these problems before tagging.

Next it is time to tag the HEADS of these branches. The Pulp repository has a tag.sh script that you
can use to do this, or you can do it by hand if you like. For example, to tag 2.4.2-0.3.beta you can
do this::

    $ ./pulp/tag.sh -v 2.4.2-0.3.beta

The tag.sh script will ask you to edit the changelog entries, tag the git repositories, and push the
tags to github.

After the repositories are tagged, the next step is to merge the tag changes you
have just made all the way forward to master. You may experience merge conflicts with this step. Be
sure to merge forward on all of the repositories.

.. warning::
   
   Do not use the ours strategy, as that will drop the changelog entries. You must manually resolve
   the conflicts!

We are now prepared to submit the build to Koji. This task is simple::

    $ ./builder.py <X.Y> <stream>

To continue with our example of building a new 2.4 beta::

    $ ./builder.py 2.4 beta

This command will build SRPMs, upload them to Koji, and monitor the resulting builds. If any of them
fail, you can view the
`failed builds <http://koji.katello.org/koji/tasks?state=failed&view=tree&method=all&order=-id>`_ to
see what went wrong. If the build was successful, it will automatically download the results into a
new folder called mash that will be a peer to your git checkouts.

Testing the Build
-----------------

In order to test the build you have just made, you can publish it to the Pulp testing repositories.
Be sure to add the shared SSH keypair to your ssh-agent, and cd into the mash directory::

    $ ssh-add /path/to/key
    $ cd mash/
    $ rsync -avz --delete * pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/testing/<X.Y>/

For our 2.4 beta example, the rsync command would be:

    $ rsync -avz --delete * pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/testing/2.4/

You can now run the automated QE suite against the testing repository to ensure that the build is
stable and has no known issues.

Publishing the Build
--------------------

Alpha builds should only be published to the testing repository. If you have a beta or stable build
that has passed tests in the testing repository, and you wish to promote it to the appropriate
place, you can use a similar rsync command to do so::

    $ rsync -avz --delete * pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/<stream>/<X.Y>/ --dry-run

Replace stream with "beta" or "stable", and substitute the correct version. For our 2.4 beta
example::

    $ rsync -avz --delete * pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/beta/2.4/ --dry-run

Note the ``--dry-run`` argument. This causes rsync to print out what it *would* do. Review its
output to ensure that it is correct. If it is, run the command again while omitting that flag.

New Stable Major/Minor Versions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are publishing a new stable <X.Y> build that hasn't been published before (i.e., X.Y.0-1),
you must also update the symlinks in the repository. There is no automated tool to perform this
step. ssh into repos.fedorapeople.org using the SSH keypair, and perform the task manually. Ensure
that the "X" symlink points at the latest X.Y release, and ensure that the "latest" symlink points
at that largest "X" symlink. For example, if you just published 3.1.0, and the latest 2.Y version
was 2.5, the stable folder should look similar to this::

    [pulpadmin@people03 pulp]$ ls -lah stable/
    total 24K
    drwxrwxr-x. 6 pulpadmin pulpadmin 4.0K Sep 17 18:26 .
    drwxrwxr-x. 7 jdob      gitpulp   4.0K Sep  8 22:40 ..
    lrwxrwxrwx. 1 pulpadmin pulpadmin    3 Aug  9 06:35 2 -> 2.5
    drwxrwxr-x. 7 pulpadmin pulpadmin 4.0K Aug 15  2013 2.1
    drwxrwxr-x. 7 pulpadmin pulpadmin 4.0K Sep  6  2013 2.2
    drwxrwxr-x. 7 pulpadmin pulpadmin 4.0K Dec  5  2013 2.3
    drwxrwxr-x. 7 pulpadmin pulpadmin 4.0K Aug  9 06:32 2.4
    drwxrwxr-x. 7 pulpadmin pulpadmin 4.0K Aug 19 06:32 2.5
    drwxrwxr-x. 7 pulpadmin pulpadmin 4.0K Aug 20 06:32 3.0
    drwxrwxr-x. 7 pulpadmin pulpadmin 4.0K Aug 24 06:32 3.1
    lrwxrwxrwx. 1 pulpadmin pulpadmin    3 Aug 24 06:35 3 -> 3.1
    lrwxrwxrwx. 1 pulpadmin pulpadmin   29 Aug 20 06:32 latest -> /srv/repos/pulp/pulp/stable/3
