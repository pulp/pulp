Building Instructions
=====================

Getting Started
---------------

Concepts
^^^^^^^^

There are some concepts you should internalize before you begin making builds. Koji has a concept
called tags. A tag is essentially a grouping of package builds.
Pulp uses one Koji tag per Pulp X.Y release stream, per distribution, per architecture.
For example, the 2.6 releases of pulp will build into the pulp-2.6-<distribution> tags in koji.
You can see the full list of Pulp's Koji tags
`here <http://koji.katello.org/koji/search?match=glob&type=tag&terms=pulp*>`_.

Another thing to know about Koji is that once a particular NEVRA (Name, Epoch, Version, Release,
Architecture) is built in Koji, it cannot be built again. However, it can be tagged into multiple
Koji tags. For example, if ``python-celery-3.1.11-1.el7.x86_64`` is built into the
``pulp-2.4-rhel7`` tag and you wish to add that exact package in the ``pulp-2.5-rhel7`` tag,
you cannot build it again. Instead, you must tag that package for the new tag. You will see later
on in this document that Pulp has a tool to help you do this.

Pulp release and testing builds are collections of components that are versioned independently.
For example, the core Pulp server may be at version 2.6 while pulp_docker may be at version 1.0.
This assembly is accomplished using release definitions specified in the
``pulp_packaging/ci/config/releases/<build-name>.yaml`` files. Each file specifies the detail of a
build that the Pulp build scripts can later assemble. The components within that
file specify the target koji tag as well as the individual git repositories and branches that
will be assembled as part of a build. In addition it specifies the directory within
https://repos.fedorapeople.org/repos/pulp/pulp/testing/automation/ where the build results
will be published.

Because there is no way to automatically determine when a particular component needs a new version,
or what that version should be, the build-infrastructure assumes that whatever version is specified
in the rpm spec file is the final version that is required.  If a release build
of that version has already been built in koji then those RPMs will be used.  Ideally, whenever
a branch is forked, or the first commit is pushed into a branch after a release build, the version
should be incremented.

Tools used when building
^^^^^^^^^^^^^^^^^^^^^^^^

Test or release builds (with the exclusion of the signing step) may be performed using
Jenkins.  There are automated jobs that will run nightly which build repositories that can be used
for validation.  When those jobs are initiated manually there is a parameter to enable the
release build process in koji.  If a release build is performed with Jenkins you will still need
to sign the rpms and manually push them to the final location on fedorapeople.

Pulp has some helper scripts in the
`pulp_packaging/ci <https://github.com/pulp/pulp_packaging/tree/master/ci>`_ directory to assist
with builds. These wrapper scripts call `tito <https://github.com/dgoodwin/tito>`_
and `koji <https://fedoraproject.org/wiki/Koji>`_ to do the actual tagging and
build work.

Both packages are in Fedora and EPEL so you should not need to install from
source. Technically you do not need to ever call these scripts directly.
However, some familiarity with both tito and koji is good, especially when
debugging build issues.

What you will need
^^^^^^^^^^^^^^^^^^

In order to build Pulp, you will need the following from the Foreman team:

#. An account on Foreman's Koji instance
#. A client certificate for your account
#. The Katello CA certificate

See the `Foreman Wiki <http://projects.theforeman.org/projects/foreman/wiki/Koji>`_ to get these
items.

In order to publish builds to the Pulp repository, you will need the SSH keypair used to upload
packages to the fedorapeople.org repository. You can get this from members of the Pulp team.

Configuring your build environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are interested in building Pulp, it is strongly recommended that you use a separate checkout
from your normal development environment to avoid any potential errors such as building in local
changes, or building the wrong branches. It is also a good idea to use a build host in a location
with good outbound bandwidth, as the repository publish can be at or over 250 MB. Thus, the first
step is to make a clean checkout of the pulp_packging somewhere away from your other checkouts::

    $ mkdir ~/pulp_build
    $ cd ~/pulp_build
    $ git clone git@github.com:pulp/pulp_packaging.git; done;

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
------------

Building Dependencies
^^^^^^^^^^^^^^^^^^^^^

If you wish to add or update the version or release of one of our dependencies, you should begin by
adding/updating the dependency's tarball, patches, and spec file in the Pulp git repository as
appropriate for the task at hand. **Don't forget to set the version/release in the spec file.** Once
you have finished that work, you are ready to test the changes. In the directory that contains the
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

Pay attention to the output of tito here as well. It will instruct you to push your branch and the
new tag to GitHub.

.. warning::

   It is very important that you perform the steps that tito instructs you to do. If you do not,
   others will not be able to reproduce the changes you have made!

At this point the dependency will automatically be built during all test builds of Pulp and will
automatically have a release build performed when the next release build containing this
dependency is performed.

Test Building Pulp and the plugins
----------------------------------

Are you ready to build something?  If so, you should `cd` to the ``pulp_packaging/ci``
directory.  The next step is to perform the build.  There is a helper script that will
perform the following actions:

#. Load the specified configuration from ``pulp_packaging/ci/config/releases``.
#. Clone all the required git repositories to the ``working/<repo_name>`` directory.
#. Check out the appropriate branch for each git repos.
#. Find all the spec files in the repositories.
#. Check koji to determine if the version in the spec already exists in koji.
#. Test build all the packages that do not already exist in koji.
#. Optionally release build all the packages that do not already exist in koji.
#. Download the already existing packages from koji.
#. Download the scratch built packages from koji.
#. Assemble the repositories for all the associated distributions.
#. Optionally push the repositories to fedorapeople.

The ``build-all.py`` script can be used to do all of this.  For example, to perform a test
build of the 2.6-dev release as specified in ``pulp_packaging/ci/config/releases/2.6-dev.py``
where the results are not pushed to fedorapeople::

    $ build-all.py 2.6-dev --disable-push

At this point, you may wish to ensure that the branches are all merged forward to master. This step
is not strictly required at this point, as we will have to do it again later. However, sometimes
developers forget to do this, and it may be advantageous to resolve potential merge conflicts before
tagging.

Here is a quick way to see if everything's been merged forward through to master. You'll likely want
to edit the BRANCHES list so the branch you are releasing from is the first in the list::

    $ BRANCHES="2.4-release 2.4-testing 2.4-dev 2.5-testing 2.5-dev"; git log origin/master | fgrep -f <(for b in $BRANCHES; do git log origin/$b | head -n1 | awk '{print $NF}' ; done)

Next it is time to raise the version of the branches. This process is different depending on the
stream you are building.

.. note::

   Pulp uses the release field in pre-release builds as a build number. The first pre-release build
   will always be 0.1, and every build thereafter prior to the release will be the last release plus
   0.1, even when switching from alpha to beta. For example, if we have build 7 2.5.0 alphas and it
   is time for the first beta, we would be going from 2.5.0-0.7.alpha to 2.5.0-0.8.beta. We loosely
   follow the
   `Fedora Package Versioning Scheme <http://fedoraproject.org/wiki/Packaging:NamingGuidelines#Package_Versioning>`_.

Checking the versions that will be built
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can use the ``build-all.py`` script to validate versions that will be built/downloaded.
This can be used to double check to ensure that the correct versions have been set in the spec
files. This command will exit immediately after displaying the versions.::

    $ ./build-all.py 2.6-testing --show-versions

If one of the versions is not what you expect updated it using the ``update-version.py`` script
and push the change to GitHub.

Updating Versions
^^^^^^^^^^^^^^^^^
The ``update-version.py`` script will scan a directory and set the versions inside according to
your specifications.  For example, to if you have been working in the ``/tmp/pulp_build`` directory
the following command can be used to update pulp_docker from the release candidate to the release
build version.::

   $ cd /tmp/pulp_build/pulp_packaging/ci/
   $ ./build-all.py 2.6-testing --show-versions
   .. Versions displayed ..
   $ ./update-version.py --update-type stage /tmp/pulp_build/pulp_packaging

At this point you can inspect the files to ensure the versions are as you expect. The changes
will still need to be committed and pushed to GitHub before they can be used to build. You can
rerun the ``build-all.py`` script to check the versions again after your changes have been
pushed to GitHub.


Submit to Koji
^^^^^^^^^^^^^^
We are now prepared to submit the build to Koji. This task is simple::

    $ cd pulp_packaging/ci
    $ ./build-all.py 2.6-testing --release

This command will build SRPMs, upload them to Koji, and monitor the resulting builds. If any of them
fail, you can view the
`failed builds <http://koji.katello.org/koji/tasks?state=failed&view=tree&method=all&order=-id>`_ to
see what went wrong. If the build was successful, it will automatically download the results into a
new folder called mash that will be a peer to the ``pulp_packaging`` directory.

At the end it will automatically upload the resulting build to fedorapeople in the directory
specified in the release config file.

Now is a good time to start our Jenkins builder to run the unit tests in all the supported operating
systems. You can configure it to run the tests in the git branch that you are building. Make sure
these pass before publishing the build.

After the repositories are built, the next step is to merge the tag changes you
have made all the way forward to master. You may experience merge conflicts with this step. Be
sure to merge forward on all of the repositories.

.. warning::
   
   Do not use the ours strategy, as that will drop the changelog entries. You must manually resolve
   the conflicts!

You may experience conflicts when you push these changes. If you do, merge your checkout with
upstream. Then you can ``git push <branch>:<branch>`` after you check the diff to make sure it is
correct. Lastly, do a new git checkout elsewhere and check that ``tito build --srpm`` is tagged
correctly and builds.

Updating Docs
-------------

The docs for Pulp platform and each plugin use `intersphinx <http://sphinx-doc.org/ext/intersphinx.html>`_
to facilitiate linking between documents. It is important that each branch
of Pulp and Pulp plugins link to the correct versions of their sister
documents.  This is accomplished by editing the URLs in the
``intersphinx_mapping`` variable, which is set in ``docs/conf.py`` for
both Pulp platform and all plugins.

Here are some guidelines for what to set the URL to:
 - The master branch of Pulp or any plugins should always point to "latest".
 - Plugins should point to the latest stable version of Pulp that they are
   known to support.
 - Pulp platform's intersphinx URLs should point back to whatever the plugin is
   set to. For example, if the "pulp_foo" plugin's docs for version 1.0 point to
   the "2.8-release" version of the Pulp platform docs, then platform version
   2.8 should point back to "1.0-release" for pulp_foo's docs. This ensures a
   consistent experience when users click back and forth between docs.


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
stable and has no known issues. We have a Jenkins server for this purpose, and you can configure it
to test the repository you just published.

Signing the RPMS
----------------

Before signing RPMs, you will need access to the Pulp signing key. Someone on
the Pulp team can provide you with this. Additionally you should be familiar
with the concepts in the `Creating GPG Keys
<https://fedoraproject.org/wiki/Creating_GPG_Keys>`_ guide.

All alpha, beta and GA RPMs should be signed with the Pulp team's GPG key. A
new key is created for each X release (3.0.0, 4.0.0, etc).  If you are doing a
new X release, a new key needs to be created. To create a new key, run ``gpg
--gen-key`` and follow the prompts. We usually set "Real Name" to "Pulp (3)"
and "Email address" to "pulp-list@redhat.com". Key expiriation should occur
five years after the key's creation date. After creating the key, export both
the private and public keys.  The public key should be saved as
``GPG-RPM-KEY-pulp-3`` and the private as ``pulp-3.private.asc``. The password
can go into ``pulp-3-password.txt``.  Please update ``encrypt.sh`` and
``decrypt.sh`` as well to include the new private key and password file. Run
``encrypt.sh`` to encrypt the new keys.

.. warning::

   If you are making an update to the key repo, be sure to always verify that
   you are not committing the unencrypted private key or password file!

.. note::

   If you are adding a new team member, just add their key to ``encrypt.sh``
   and ``decrypt.sh``, then re-encrypt the keys and commit. The new team member
   will also need to obtain the "sign" permission in koji.

The ``GPG-RPM-KEY-pulp-3`` file should be made available under
https://repos.fedorapeople.org/repos/pulp/pulp/.

If you are simply creating a new build in an existing X stream release, you
need to perform some one-time setup steps in your local environment. First,
create or update your ``~/.rpmmacros`` file to include content like so,
substituting X with your intended release::

    %_gpg_name Pulp (X)

Next, run the following from your mash directory::

    $ find -name "*.rpm" | xargs rpm --addsign

This will sign all of the RPMs in the mash. You then need to import signatures into koji::

   $ find -name "*.rpm" | xargs koji import-sig

.. note::

   Koji does not store the entire signed RPM. It merely stores the additional
   signature metadata, and then re-creates a signed RPM in a different
   directory when the ``write-signed-rpm`` command is issued. The original
   unsigned RPM will remain untouched.

As ``list-signed`` does not seem to work, do a random check in
http://koji.katello.org/packages/ that
http://koji.katello.org/packages/<name>/<version>/<release>/data/sigcache/<sig-hash>/
exists and has some content in it. Once this is complete, you will need to
tell koji to write out the signed RPMs (both commands are run from your mash dir)::

   $ for r in `find -name "*src.rpm"`; do basename $r; done | sort | uniq | sed s/\.src\.rpm//g > /tmp/builds
   $ for x in `cat /tmp/builds`; do koji write-signed-rpm <SIGNATURE-HASH> $x; done

Sync down your mash one more time (run from the ``pulp_packaging/ci`` dir)::

   $ ./build-all.py <release_config> --disable-push --rpmsig <SIGNATURE-HASH>

.. note::

   This command does not download signed RPMs for RHEL 5, due to bugs in RHEL 5
   related to signature verification. While we sign all RPMs including RHEL 5, we
   do not publish the signed RPMs for this particular platform.

After it is synced down, you can publish the build.

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

.. warning::

   Be sure to check that you are publishing the build to the correct repository. It's important to
   never publish an alpha build to anything other than a testing repository. A beta build can go to
   testing or the beta repository (but never the stable repository), and a stable build can go to a
   testing or a stable repository.

If you have published a beta build, you must query Bugzilla for all of our bugs that are in the
``MODIFIED`` state for the version you have published and move them to ``ON_QA``.

After publishing a beta build, email pulp-list@redhat.com to announce the beta. Here is a
typical email you can use::

   Subject: [devel] Pulp beta <version> is available

   Pulp <version> has been published to the beta repositories. This fixes <add some text here>.

If you have published a stable build, there are a few more items to take care of:

#. Update the "latest release" text on http://www.pulpproject.org/.
#. Verify that the new documentation was published. You may need to
   `explicitly build <https://pulp-dev-guide.readthedocs.org/en/latest/contributing/documenting.html#rtd-versions>`_
   them if they were not automatically build.
#. Update the channel topic in #pulp on Freenode with the new release.
#. Move all bugs that were in the ``VERIFIED`` state for this target release to ``CLOSED CURRENT
   RELEASE``.

After publishing a stable build, email pulp-list@redhat.com to announce the new release. Here is
a typical email you can use::

   Subject: Pulp <version> is available!

   The Pulp team is pleased to announce that we have released <version>
   to our stable repositories. <Say if it's just bugfixes or bugs and features>.

   Please see the release notes[0][1][2] if you are interested in reading about
   the fixes that are included. Happy upgrading!

   [0] link to pulp release notes (if updated)
   [0] link to pulp-rpm release notes (if updated)
   [0] link to pulp-puppet release notes (if updated)

Please ensure that the release notes have in fact been updated before sending the email out.

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

The ``rhel-pulp.repo`` and ``fedora-pulp.repo`` files also need to be updated
for the new GPG public key location if you are creating a new X release.
