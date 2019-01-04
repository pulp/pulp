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

Pulp release and testing builds are collections of components that are versioned independently.
For example, the core Pulp server may be at version 2.6 while pulp_docker may be at version 1.0.
This assembly is accomplished using release definitions specified in the
``pulp-ci/ci/config/releases/<build-name>.yaml`` files. Each file specifies the details
of a build that the Pulp build scripts can later assemble. The components within that
file specify the target koji tag as well as the individual git repositories and branches that
will be assembled as part of a build. In addition it specifies the directories within
https://repos.fedorapeople.org/repos/pulp/pulp/testing/automation/ where the build results
will be published.

.. note::

   For pre-release builds, Pulp uses the build number as the release field. The first pre-release build
   will always be 0.1, and every build thereafter prior to the release will be the last release plus
   0.1, even when switching from alpha to beta. For example, if we have built 7 2.5.0 alphas and it
   is time for the first beta, we would be going from 2.5.0-0.7.alpha to 2.5.0-0.8.beta. For release
   builds, use whole numbers for the build number. We loosely follow the
   `Fedora Package Versioning Scheme <http://fedoraproject.org/wiki/Packaging:NamingGuidelines#Package_Versioning>`_.

Another thing to know about Koji is that once a particular NEVRA (Name, Epoch, Version, Release,
Architecture) is built in Koji, it cannot be built again. However, it can be included in multiple
Koji tags. For example, if ``python-celery-3.1.11-1.el7.x86_64`` is built into the
``pulp-2.4-rhel7`` tag and you wish to add that exact package in the ``pulp-2.5-rhel7`` tag, you
must indicate the build to use in the version field of the release stream's definition file,
``2.5-dev.yaml`` in this case.

Because there is no way to automatically determine when a particular component needs to be rebuilt
or what that version should be, the build-infrastructure assumes that whatever version is specified
in the yaml file is the final version that is required.  If a release build of that version had
already been built in koji then those RPMs will be used. If the version specified in the yaml file
does not match the version in the spec file, the spec file will be updated and the change will be
merged forward using the 'ours' strategy.

Information about the release configs, and which config to use for building, can be found in the
config README, located next to the

When to build from a -dev branch, a tag or hotfix branch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All betas are built from the -release branch of each project. As changes are cherry-picked
to the -release branch of a project, those changes are released with the next beta. Once a beta is
considered stable, the release candidate should be built from the tag that was generated during
the build process of the stable beta. This guarantees that the RPMs generated will be exactly the
same as the ones that were part of the stable beta. Similarly, a GA release should be built from
the tag created by the release candidate.

In some situations you want to include something extra on top of the stable beta. This could be
documentation changes or a particular fix for an issue that was found after releasing the first
release candidate. Hotfixes can be merged to the x.y-release branch that is used to do the
build, and tags updated.

Tools used when building
^^^^^^^^^^^^^^^^^^^^^^^^

Test or release builds (with the exclusion of the signing step) may be performed using
Jenkins.  There are automated jobs that will run nightly which build repositories that can be used
for validation.  When those jobs are initiated manually there is a parameter to enable the
release build process in koji.  If a release build is performed with Jenkins you will still need
to sign the rpms and manually push them to the final location on fedorapeople.

Pulp utilizes an ansible based tool called obal `obal <https://github.com/theforeman/obal>`_
to assist with builds. These scripts call `tito <https://github.com/dgoodwin/tito>`_
and `koji <https://fedoraproject.org/wiki/Koji>`_ to do the actual tagging and
build work.

Both tito and koji are in Fedora and EPEL so you should not need to install from
source. Technically you do not need to ever call these scripts directly.
However, some familiarity with both tito and koji is good, especially when
debugging build issues.  Obal can be installed from pip: ``pip install obal``.

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

Additionally you will need to install the following packages on the machine
you will be building from, using dnf or yum:

* koji
* tito
* obal

Configuring your build environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are interested in building Pulp, you should start by making a clean checkout of
the pulp-packging repository ::

    $ git clone git@github.com:pulp/pulp-packaging.git

The next step is to install and configure the Koji client on your machine. You will need to put the
Katello CA certificate and your client certificate in your home folder.

Here is an example $HOME/.koji/config file you can use::

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

Make sure you install your Katello CA certificate and client certificate to the paths listed in the
example above::

    $ cp <katello CA> ~/.katello-ca.cert
    $ cp <katello client cert> ~/.katello.cert

If all went well, you should be able to say hello to Koji::

    $ [rbarlow@notepad]~% koji moshimoshi
    olá, rbarlow!

    You are using the hub at http://koji.katello.org/kojihub

Now you are ready to begin building.


Building Dependencies
^^^^^^^^^^^^^^^^^^^^^

If you wish to add or update the version or release of one of our dependencies, you should begin by
adding/updating the dependency's spec file in the pulp-packaging repository as appropriate for the
task at hand. **Don't forget to set the version/release in the spec file.** Once you have finished
that work, you are ready to test the changes. In the root of the pulp-packaging directory, use obal
to build a test RPM. For example, for python-celery::

    $ obal scratch python-celery -e 'build_package_test=true'

Pay attention to the output. There may be errors you will need to respond to. If all goes
well, you should be able to download rpms from the koji task. You should install these RPMs and
test them to make sure they work with Pulp and that you want to introduce this change to the
repository.

If you are confident in your changes, submit a pull request with the changes you have made so far.
Once someone approves the changes, merge the pull request. Once you have done this, you are ready
to release the dependency::

    $ obal release python-celery

.. warning::

   If this dependency is for other releases of pulp, you will need tag them into other
   version-release tags in koji

   $ koji tag-build pulp-x.y-el7 python-celery-x.y.z-1.el7


Test Building Pulp and the plugins
----------------------------------

Are you ready to build something? The next step is to ensure that the build that you are going to do
has an appropriate branch in ``pulp-packaging`` (explained in detail above). Double check for each
spec file that the ``Source0`` field points to the branch or tag that you wish to build from and
that the ``version`` field is correct. The ``obal`` script which will perform the following actions:

#. Reads package_manifest.yaml
#. Downloads the Source0 file with git-annex for package
#. Uses tito to build the package in koji
#. (If ``obal release``) Tag the successful build in koji


Run the build script with the following syntax::

    $ obal [options] <name of package or group>

For example, to perform a test build of the 2.15 release as specified in ``pulp-packaging``

    $ obal release pulp_packages -e 'build_package_test=true'

Once builds have finished, ssh into koji and run the pulp mash script to generate the pulp repos.  Once
that has finished, rsync them over from koji to the testing repo for that x.y version of pulp.


Reconcile Redmine Issues
^^^^^^^^^^^^^^^^^^^^^^^^

Before starting a release build, ensure that there are no issues
blocking the version of Pulp about to be released by checking the
`Open Blockers <https://pulp.plan.io/projects/pulp/issues?query_id=75>`_ report in Redmine.

If a release is not blocked, make sure that any issues in a ``MODIFIED`` state that apply
to the branch being released have the Platform Release field set correctly. See the
`MODIFIED - No Release <https://pulp.plan.io/projects/pulp/issues?query_id=65>`_ report in Redmine
for a list of issues that are ``MODIFIED`` but not value for the Platform Release field.

All ``MODIFIED`` issues should include a link to the pull request for the related bugfix or feature,
as well as all commits associated with it. The target release can be determined by examining it's
tracker type in redmine.

* Issues or changes that don't impact user interaction belong in the next bugfix (Z) release.
* Stories or changes that add new user visible items to pulp go into the next feature (Y) release.

If in doubt, check with the developer that fixed the issue to determine which target
release is appropriate.

Similarly, if there are any issues that are ``NEW``, ``ASSIGNED``, or ``POST`` and inappropriately
given a Platform Release, set the Platform Release field to none on those issues.

Finally, check the `Verification Required <https://pulp.plan.io/issues?query_id=84>`_ report and
ensure that there are no unverified issues related to this release, or any releases with a lower
version number.

Submit to Koji
^^^^^^^^^^^^^^

We are now prepared to submit the build to Koji. This task is simple::

    $ cd pulp-packaging/
    $ obal release pulp_packages -t wait

This command will build SRPMs, upload them to Koji, and monitor the resulting builds. If any of them
fail, you can view the
`failed builds <http://koji.katello.org/koji/tasks?state=failed&view=tree&method=all&order=-id>`_ to
see what went wrong. If the build was successful, it will tag them into it's koji release tag.

The mash script will need to be ran on koji and the generated repo needs to be rsynced to fedorapeople.

If you want to start our Jenkins builder to run the unit tests in all the supported operating
systems, you should wait until the build script is finished so that it can push the correct tag to
GitHub. You can configure Jenkins to run the tests in the git branch or tag that you are building.
Make sure these pass before publishing the build.

.. _building-updating-versions:

Updating Versions
^^^^^^^^^^^^^^^^^

We use Jenkins to make nightly builds, so once you have built the package successfully and merged
the changelog forward, you should update the yaml file that Jenkins uses and bump the versions of
all the projects that were included in this build. You can use the ``update-version.py`` script in
the pulp-ci repo to update the versions. This script updates the version in all of the setup.py files.

This script should be run on the 2-master branch after the first prerelease (beta and rc releases)
of a given x.y version to ensure that the nightly builds for that branch are clearly newer than the
current release in progress.

At this point you can inspect the files to ensure the versions are as you expect. Create a merge
request to the appropriate branch to update the version.

Updating Docs
-------------

When releasing a new X or Y release, ensure the following:

* The release config must exist and be up to date in `the packaging repo <https://github.com/pulp/
  pulp-ci/tree/master/ci/config/releases/>`_. For pre-releases this is expected to be named
  ``x.y-build``, and for GA releases it is expected to be named ``x.y-release`` config.

* The Jenkins docs buiding job for the release config must also exist. If it doesn't, update `the
  Jenkins job builder definitions <https://github.com/pulp/pulp-ci/blob/master/ci/jobs/
  projects.yaml>`_ to include the release config. Use Jenkins Job Builder to push the job to
  Jenkins.

* For GA releases, check that the `LATEST variable <https://github.com/pulp/pulp-ci/blob/
  master/ci/docs-builder.py#L15>`_ is up to date. This ensures the latest GA docs will be published
  at the root of the docs.pulpproject.org site.

* Update `supported releases <https://github.com/pulp/pulp-ci/tree/master/ci/config/
  supported-releases.json>`_ to include new X.Y version, and remove any versions no longer
  officially supported.


Once the above changes are merged and the docs building job for the release exists, run the docs
building job for that release from the `Docs Builders page <https://pulp-jenkins.rhev-ci-vms.eng.
rdu2.redhat.com/view/Docs%20Builders/>`_. This should be done for pre-releases and GA releases.

Testing the Build
-----------------

In order to test the build you have just made, you can publish it to the Pulp testing repositories.
Be sure to add the shared SSH keypair to your ssh-agent, ssh into koji::

    [user@koij ~]$ rsync -avz --delete /mnt/koji/releases/split/yum/pulp-<x.y>/pulp/ pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/testing/<X.Y>/

For our 2.15 beta example, the rsync command would be:

    $ rsync -avz --delete /mnt/koji/releases/split/yum/pulp-2.15/pulp/ pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/testing/2.15/

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

For each {name}-x.y.z-{release}.dist, run: (pulp 2.15.0 beta example)::

    $ koji download-build pulp-2.15.0-0.2.beta.el7
    $ koji download-build pulp-2.15.0-0.2.beta.fc25
    $ koji download-build pulp-2.15.0-0.2.beta.fc26
    etc...

Next, run the following from your mash directory::

    $ find . -name "*.rpm" | xargs rpm --addsign

This will sign all of the RPMs in the mash. You then need to import signatures into koji::

   $ find . -name "*.rpm" | xargs koji import-sig

Then write the signed RPM

   $ for r in `find . -name "*src.rpm"`; do basename $r; done | sort | uniq | sed s/\.src\.rpm//g > /tmp/builds
   $ for x in `cat /tmp/builds`; do koji write-signed-rpm [sig_hash] $x; done

.. note::

   Koji does not store the entire signed RPM. It merely stores the additional
   signature metadata, and then re-creates a signed RPM in a different
   directory when the ``write-signed-rpm`` command is issued. The original
   unsigned RPM will remain untouched.

Mash the release on koji (pulp 2.15 example) and sync it locally::

   [user@koji ~]$ pulp-mash-split-2.15.py
   [user@koji ~]$ exit
   [user@local ~]$ rsync -avz --delete koji.katello.org:/mnt/koji/releases/split/yum/pulp-2.15/pulp/ .

Finally, verify the downloaded signatures of the rpms in your mash directory::

   $ find . -name "*.rpm" | xargs rpm --checksig || echo 'Bad signatures!'

RPMs with invalid signatures will be reported in the output, but can be easy to
miss with all the output the scrolls by. xargs will exit with a non-zero exit
code if any of the calls to xargs rpm fail, which will trigger the echo of
"Bad Signatures!" to the shell. Failing RPMs may need to be re-signed.

After it is synced down and verified, you can publish the build.

Publishing the Build
--------------------

Alpha builds should only be published to the testing repository. If you have a beta or stable build
that has passed tests in the testing repository, and you wish to promote it to the appropriate
place, you can use a similar rsync command to do so::

    [user@koji] $ rsync -avz --delete /mnt/koji/releases/split/yum/pulp-<x.y>/pulp/ pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/<stream>/<X.Y>/ --dry-run

Replace ``<stream>`` with "beta" or "stable", and ``<X.Y>`` with the correct version. For our 2.15 beta
example::

    [user@koji] $ rsync -avz --delete /mnt/koji/releases/split/yum/pulp-2.15/pulp/ pulpadmin@repos.fedorapeople.org:/srv/repos/pulp/pulp/beta/2.15/ --dry-run

Note the ``--dry-run`` argument. This causes rsync to print out what it *would* do. Review its
output to ensure that it is correct. If it is, run the command again while omitting that flag.

.. warning::

   Be sure to check that you are publishing the build to the correct repository. It's important to
   never publish an alpha build to anything other than a testing repository. A beta build can go to
   testing or the beta repository (but never the stable repository), and a stable build can go to a
   testing or a stable repository.

If you have published a beta build, you must move all issues and stories for the target release
from ``MODIFIED`` to ``ON_QA``. If this is the first beta build for this version, you must also
update versions on the branch as described :ref:`above <building-updating-versions>`.

If you are publishing a beta or release candidate build, ensure that the build documentation
is listed and linked to on the `documentation page of pulpproject.org <http://pulpproject.org/docs/>`_.

After publishing a beta build, email pulp-list@redhat.com to announce the beta. Here is a
typical email you can use::

   Subject: [devel] Pulp beta <version> is available

   Pulp <version> has been published to the beta repositories[0]. This fixes <add some text here>.

   [0] https://repos.fedorapeople.org/repos/pulp/pulp/beta/

Additional information, such as update instructions and issues addressed, can be included in
these release notes. If a security-related issue (probably assigned a CVE number) is included
in this release, information about the vulnerability and what can be done to address it must
be included in this announcement. This information should already be in the release notes for
the release being built and can be copied from there.

Hotfix releases should mention the specific issues that caused a hotfix to be created, and
feature releases should mention notable new features of interest.

To easily generate a list of issues, start with a redmine report of issues for the current
release (such as the Next Bugfix Release report). Then, under the Redmine filter options,
group the results by Project, remove everything but "Subject" from the list of selected
columns, and Apply the new options. This creates a list of issues that's very easy to copy
and paste into a release announcement. It also generates a URL that can be included in the
release announcement. This URL is very long, so a URL shortener should be used to make the
URL fit into the announcement.

If you have published a stable build, there are a few more items to take care of:

#. Update the "latest release" text on http://www.pulpproject.org/.
#. Run the Jenkins job to update the documentation for this version.
#. Update the channel topic in #pulp on Freenode with the new release.
#. Move all bugs that were in the ``MODIFIED`` or ``ON_QA`` state for this target release to
   ``CLOSED CURRENTRELEASE``.
#. Update the Redmine report for this release type for the next release of that type. For example,
   if this was a z-stream bugfix release, update the 'Next Bugfix Release' to point to the next
   version to be released in that stream. Redmine may need to have that version added before the
   report can be updated.
#. Update the pulp website with a blog post announcing the release, using the template below
#. Mail pulp-list@redhat.com to announce the new release, using the template below

Here is an email template you can use for release announcements::

   Subject: Pulp <version> is available!

   The Pulp team is pleased to announce that we have released <version>
   to our stable repositories[0]. <Say if it's just bugfixes or bugs and features>.

   Please see the release notes[1][2][3] if you are interested in reading about
   the fixes that are included. Happy upgrading!

   [0] https://repos.fedorapeople.org/repos/pulp/pulp/stable/<stream>/
   [0] link to pulp release notes (if updated)
   [0] link to pulp-rpm release notes (if updated)
   [0] link to pulp-puppet release notes (if updated)

Please ensure that the release notes have in fact been updated before sending the email out.
Ideally, the release notes will have been updated before the first beta build of a release.

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

Also the X.Y-1 needs to be added to the "Older, Stable" section of the
`documentation page of pulpproject.org <http://pulpproject.org/docs/>`_.
