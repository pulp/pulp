# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           pulp
Version:        0.0.120
Release:        1%{?dist}
Summary:        An application for managing software content

Group:          Development/Languages
License:        GPLv2
URL:            https://fedorahosted.org/pulp/
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose	
BuildRequires:  rpm-python

Requires: %{name}-common = %{version}
Requires: python-pymongo
Requires: python-setuptools
Requires: python-webpy
Requires: python-simplejson
Requires: python-oauth2
Requires: python-httplib2
Requires: grinder >= 0.0.66
Requires: httpd
Requires: mod_wsgi
Requires: mod_python
Requires: mod_ssl
Requires: m2crypto
Requires: openssl
Requires: python-ldap
Requires: gofer-lib >= 0.7
Requires: crontabs
Requires: acl

%if 14%{?fedora} < 13
Requires: qpidd
Requires: qpidd-ssl
Requires: rhm-cpp-server-store
Requires: mongo
Requires: mongo-server
%else:
Requires: qpid-cpp-server
Requires: qpid-cpp-server-ssl
Requires: qpid-cpp-server-store
Requires: mongodb
Requires: mongodb-server
%endif
%if 0%{?rhel} >= 5
Requires: python-uuid
Requires: python-ssl
Requires: python-ctypes
%endif


# newer pulp builds should require same client version
Requires: %{name}-client >= %{version}

%if 0%{?rhel} > 5
Requires: python-hashlib
%endif


%description
Pulp provides replication, access, and accounting for software repositories.


%package client
Summary:        Client side tools for managing content on pulp server
Group:          Development/Languages
BuildRequires:  rpm-python
Requires: python-simplejson
Requires: m2crypto
Requires: %{name}-common = %{version}
Requires: gofer >= 0.7

%if 0%{?rhel} > 5
Requires: python-hashlib
%endif

%description client
A collection of tools to interact and perform content specific operations such as repo management, 
package profile updates etc.


%package common
Summary:        Pulp common python packages.
Group:          Development/Languages
BuildRequires:  rpm-python

%description common
A collection of resources that are common between the pulp server and client.


%package cds
Summary:        Provides the ability to run as a pulp external CDS.
Group:          Development/Languages
BuildRequires:  rpm-python
Requires:       gofer >= 0.7
Requires:       grinder
Requires:       httpd
Requires:       mod_ssl

%if 14%{?fedora} < 13
Requires: qpidd
Requires: qpidd-ssl
Requires: rhm-cpp-server-store
%else:
Requires: qpid-cpp-server
Requires: qpid-cpp-server-ssl
Requires: qpid-cpp-server-store
%endif


%description cds
Tools necessary to interact synchronize content from a pulp server and serve that content
to clients.


%prep
%setup -q

%build
pushd src
%{__python} setup.py build
popd

%install
rm -rf %{buildroot}
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

# Pulp Configuration
mkdir -p %{buildroot}/etc/pulp
cp etc/pulp/* %{buildroot}/etc/pulp

# Pulp Log
mkdir -p %{buildroot}/var/log/pulp

# Apache Configuration
mkdir -p %{buildroot}/etc/httpd/conf.d/
cp etc/httpd/conf.d/pulp.conf %{buildroot}/etc/httpd/conf.d/

# Pulp Web Services
cp -R srv %{buildroot}

# Pulp PKI
mkdir -p %{buildroot}/etc/pki/pulp
mkdir -p %{buildroot}/etc/pki/consumer
cp etc/pki/pulp/* %{buildroot}/etc/pki/pulp

mkdir -p %{buildroot}/etc/pki/content

# Pulp Runtime
mkdir -p %{buildroot}/var/lib/pulp
mkdir -p %{buildroot}/var/lib/pulp/published
mkdir -p %{buildroot}/var/www
ln -s /var/lib/pulp/published %{buildroot}/var/www/pub

# Client Gofer Plugin
mkdir -p %{buildroot}/etc/gofer/plugins
mkdir -p %{buildroot}/usr/lib/gofer/plugins
cp etc/gofer/plugins/*.conf %{buildroot}/etc/gofer/plugins
cp src/pulp/client/gofer/pulp.py %{buildroot}/usr/lib/gofer/plugins

# CDS Gofer Plugin
mkdir -p %{buildroot}/etc/gofer/cds-plugins
cp etc/gofer/cds-plugins/*.conf %{buildroot}/etc/gofer/plugins
cp src/pulp/cds/gofer/gofer_cds_plugin.py %{buildroot}/usr/lib/gofer/plugins

# Pulp Init.d
mkdir -p %{buildroot}/etc/rc.d/init.d
cp etc/rc.d/init.d/pulp-server %{buildroot}/etc/rc.d/init.d/

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/%{name}*.egg-info

# Touch ghost files (these won't be packaged)
mkdir -p %{buildroot}/etc/yum.repos.d
touch %{buildroot}/etc/yum.repos.d/pulp.repo

# Pulp CDS
# This should match what's in gofer_cds_plugin.conf and pulp-cds.conf
mkdir -p %{buildroot}/var/lib/pulp-cds

# Pulp CDS Logging
mkdir -p %{buildroot}/var/log/pulp-cds

# Apache Configuration
mkdir -p %{buildroot}/etc/httpd/conf.d/
cp etc/httpd/conf.d/pulp-cds.conf %{buildroot}/etc/httpd/conf.d/

%clean
rm -rf %{buildroot}


%post
setfacl -m u:apache:rwx /etc/pki/content/


%files
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/server/
%config(noreplace) %{_sysconfdir}/pulp/pulp.conf
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp.conf
%ghost %{_sysconfdir}/yum.repos.d/pulp.repo
%attr(775, apache, apache) %{_sysconfdir}/pulp
%attr(775, apache, apache) /srv/pulp
%attr(750, apache, apache) /srv/pulp/webservices.wsgi
%attr(750, apache, apache) /srv/pulp/bootstrap.wsgi
%attr(3775, apache, apache) /var/lib/pulp
%attr(3775, apache, apache) /var/www/pub
%attr(3775, apache, apache) /var/log/pulp
%attr(3775, root, root) %{_sysconfdir}/pki/content
%attr(3775, root, root) %{_sysconfdir}/rc.d/init.d/pulp-server
%{_sysconfdir}/pki/pulp/ca.key
%{_sysconfdir}/pki/pulp/ca.crt

%files common
%defattr(-,root,root,-)
%doc
%{python_sitelib}/pulp/__init__.*


%files client
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/client/
%{_bindir}/pulp-admin
%{_bindir}/pulp-client
%{_bindir}/pulp-migrate
%{_exec_prefix}/lib/gofer/plugins/pulp.*
%{_sysconfdir}/gofer/plugins/pulp.conf
%attr(755,root,root) %{_sysconfdir}/pki/consumer/
%config(noreplace) %{_sysconfdir}/pulp/client.conf


%files cds
%defattr(-,root,root,-)
%doc
%{_sysconfdir}/gofer/plugins/gofer_cds_plugin.conf
%{_exec_prefix}/lib/gofer/plugins/gofer_cds_plugin.*
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp-cds.conf
/var/lib/pulp-cds
/var/log/pulp-cds


%changelog
* Wed Jan 05 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.120-1
- Replace deprecated @identity function with %{hostname} macro in descriptor.
  This is for compatibility with gofer 0.12. (jortel@redhat.com)
- 655195 - remove consumer cert on client when consumer is deleted gofer plugin
  updated to replace deprecated @identity function with action.
  (jortel@redhat.com)
- Disable amqp events out-of-the-box. (jortel@redhat.com)
- 662680 - Fixing division by 0 error when total packages is 0
  (jconnor@redhat.com)
- 650330 - pulp-migrate script not migrating db from %post of rpm
  (jmatthews@redhat.com)
- 608672 - Fixing RHN syncs to work and catch the exceptions appropriately
  (pkilambi@redhat.com)
- 662769 - Repo Cloning with Origin Feed sets the cert,ca and key to cloone
  repo (pkilambi@redhat.com)
- 636852 - Status of a failed sync is not being reported when you run repo
  status (jmatthews@redhat.com)
- 636072 - Pulp repo sync not cleaning up the temp_repo directories that are in
  the sync directories (jmatthews@redhat.com)
- 633988, 658162 - server option enhancements: (pkilambi@redhat.com)
- 666959 - undefined variable error (pkilambi@redhat.com)
- 623911 - Raise a meaningful exception when user tries to sync a feedless repo
  (pkilambi@redhat.com)
* Wed Dec 22 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.119-1
- 663107 - trimming errata install options to be consistant with package
  installs (pkilambi@redhat.com)
- 663033 - Capitalization mismatch for repo content output
  (pkilambi@redhat.com)
- 662681 - clean up distributions as part of repo delete (pkilambi@redhat.com)
- 662668 - renaming keys to gpgkeys for clarity (pkilambi@redhat.com)
- 662247 - making clone_id a required option (pkilambi@redhat.com)
- 658613 - catch the credentials error (pkilambi@redhat.com)
- bump grinder requires version (pkilambi@redhat.com)
- 634283 - This commit includes, * fix to clean up consumer certificate upon
  consumer delete * raise a message if consumer doesnt exist on consumer update
  (pkilambi@redhat.com)
- 651926 - change the feed help to be more explicit (pkilambi@redhat.com)
- 649025 - Adding group info to repo list (pkilambi@redhat.com)
- 664557 - fixing typos in add/delete help menu (pkilambi@redhat.com)
- replace functools.wraps usage with (fixed) compat.wraps for python 2.4
  compat. (jortel@redhat.com)
- Fixing typos in the help text (pkilambi@redhat.com)
- Adding reboot suggested to errata info (pkilambi@redhat.com)
- Adding support for user input if provided errata during errata install
  requires a system reboot. (pkilambi@redhat.com)

* Tue Dec 21 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.118-1
- Better formatting for registration errors. (jason.dobies@redhat.com)
- Added check when deleting a repo to ensure it's not deployed to any CDS
  instances. (jason.dobies@redhat.com)
- Added query for all CDS instances associated with a given repo.
  (jason.dobies@redhat.com)
- Adding a call to pull in both errata and package info in one call
  (pkilambi@redhat.com)

* Fri Dec 17 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.117-1
- update consumergroup package install for allowing a schedule time
  (jmatthews@redhat.com)
- Adding ability to schedule package installs for a specfied time in future
  (jmatthews@redhat.com)
- improving the package filename fetch query to do a batch lookup to be more
  performant (pkilambi@redhat.com)
- Fix interpreter hang on exit (python 2.4). (jortel@redhat.com)
- Moving search into /services/ handler (pkilambi@redhat.com)
- moving oauth configs to proper section in config file (mmccune@redhat.com)

* Wed Dec 15 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.116-1
- Added delete old repo functionality on CDS sync. (jason.dobies@redhat.com)
- Assemble the path correctly when saving repos. (jason.dobies@redhat.com)
- Support for Dependency Resolution List. This commit includes: * Dependency
  resolver module * API/WS changes to support deplist * CLI changes to support
  pulp-admin package deplist (pkilambi@redhat.com)
- fixing the updates to send back package info (pkilambi@redhat.com)
- Send the server URL information from pulp server to CDS.
  (jason.dobies@redhat.com)
- python-oauth2 has a dependency on python-httplib2 (jason.dobies@redhat.com)

* Tue Dec 14 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.115-1
- Test build for CDS RPM changes
* Fri Dec 10 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.114-1
- Update the last sync timestamp on the CDS at a sync.
  (jason.dobies@redhat.com)
- Added an ID sort as a backup to differentiate between ties.
  (jason.dobies@redhat.com)
- Initial CDS plugin implementation. Seeing issues with grinder connecting to
  pulp repos. (jason.dobies@redhat.com)
- 661850 - Added crontabs as a dependency. (jason.dobies@redhat.com)
- 636525 - Include the checksum information of the package existing on the
  server (pkilambi@redhat.com)

* Thu Dec 09 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.113-1
- Initial work towards getting a CDS RPM built. Still debugging the build.
  (jason.dobies@redhat.com)
- Incremented gofer version to match what the CDS dispatcher is expecting.
  (jason.dobies@redhat.com)
- Updated error handling for gofer 0.7 changes. (jason.dobies@redhat.com)
- Added test cases for dispatcher calls that fail. (jason.dobies@redhat.com)

* Wed Dec 08 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.112-1
- Wired gofer CDS dispatcher and mocked out calls for test cases.
  (jason.dobies@redhat.com)
- Selective Errata sync suppport. This commit includes, (pkilambi@redhat.com)
- invoke connection/auditing initialize prior to other pulp imports
  (jmatthew@redhat.com)
- Replace class decorators in event handlers for python 2.4 compat.
  (jortel@redhat.com)
- Added associate/unassociate to webservices and CLI. (jason.dobies@redhat.com)
- 649118 - [RFE] Support for running mongo DB on separate instance
  (jmatthew@redhat.com)
- Wired up CDS history to webservices and CLI (still need to format).
  (jason.dobies@redhat.com)

* Fri Dec 03 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.111-1
- 658240 - Fixed failing package install on consumergroup because of wrong
  task_id return (skarmark@redhat.com)
- 624512 - Password in new user creation is not displayed on the screen
  (skarmark@redhat.com)
- 655195 - Added missing --consumerid option from pulp-admin consumer cli
  (skarmark@redhat.com)
- Adding support to be able to skip specific content from local and rhn syncs
  (pkilambi@redhat.com)
- fixing the condition causing key error (pkilambi@redhat.com)
- setting skip_dict default to unimplemented sync modules (pkilambi@redhat.com)
- default skip list to empty hash for backward compatibility
  (pkilambi@redhat.com)

* Thu Dec 02 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.110-1
- Adding support to be able to skip specific content from syncs. This commit
  includes (pkilambi@redhat.com)
- Fix messaging unit tests. (jortel@redhat.com)
- Refit pulp (gofer) plugin to match gofer 0.3. (jortel@redhat.com)
- config clean up (pkilambi@redhat.com)
- forgotten file from previous commit (duffy@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (mmccune@redhat.com)
- updated css from mizmo (duffy@redhat.com)
- typo for 'task' (jmatthew@redhat.com)
- fix for repo publish to create published path if it has been deleted
  (jmatthew@redhat.com)
- Added CLI hooks for CDS register, unregister, and list.
  (jason.dobies@redhat.com)
- Added wiring from web services to CDS API. (jason.dobies@redhat.com)
- Finished docs (jason.dobies@redhat.com)
- Added API call for listing all CDS entries. Fixed an issue with the ID not
  being set correctly in the CDS domain model. (jason.dobies@redhat.com)
- updated css and images for better layout and colors (duffy@redhat.com)
- renamed server init.d script from pulpd to pulp-server (jconnor@redhat.com)
- added comment in internal where migration calls should be made
  (jconnor@redhat.com)
- Adding support - for all available content - for listing content by updates-
  only per consumer - new cli changes to include --updates and consumerid
  (pkilambi@redhat.com)
- Header cleanup (jason.dobies@redhat.com)
- Removed unused import (jason.dobies@redhat.com)
- Code and comment cleanup (jason.dobies@redhat.com)
- Added CDS model entity and basic register and retrieval APIs.
  (jason.dobies@redhat.com)
- fixing background for website (mmccune@redhat.com)

* Mon Nov 29 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.109-1
- 655256 - GET on repositories was only allowing admin and not consumers
  causing the auth to fail using consumer certs (pkilambi@redhat.com)
- 655258, new help text for repo update --schedule
  (jconnor@redhat.com)
- added comment about minimum threads in pulp.conf (jconnor@redhat.com)
- updating links to proper spots on the web (mmccune@redhat.com)
- Linked Index to itself... (jrist@redhat.com)
- updated hackergotchis (mmccune@redhat.com)
- Adding some error handling to ldap authentication (pkilambi@redhat.com)

* Fri Nov 19 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.108-1
- 655086 - Fixing the print string to exclude pkg profile by default in
  consumer list (pkilambi@redhat.com)

* Fri Nov 19 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.107-1
- Tag for the sprint 17 community release

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.106-1
- Linked command reference to the wiki. (jrist@redhat.com)

* Thu Nov 18 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.105-1
- Mitigate (imp) module import of .pyc files to do with default filesystem
  encoding. (jortel@redhat.com)
- Fixing the event handler to handle file based or http based gpg key urls
  (pkilambi@redhat.com)
- Example script to parse PackageKit groups info and create pkg grp categories
  in pulp (jmatthew@redhat.com)
- prevent duplicates from package group/category lists (jmatthew@redhat.com)
- Simplify event handler dynamic import. (jortel@redhat.com)
- bug#654681 - Only add distro id to repo if same id doesnt already exist
  (pkilambi@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.104-1
- 

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.103-1
- Revert "trying a replacement for class decorator" holding off on this fix
  until discussion with folks tomorrow This reverts commit
  7ce50dcf218572b3ebf3d0f1fbac062ee212a78b. (skarmark@redhat.com)
- trying a replacement for class decorator (skarmark@redhat.com)
- We need to find proper repolacement for Class decorators
  (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com>
- Revert "trying a replacement for class decorator" holding off on this fix
  until discussion with folks tomorrow This reverts commit
  7ce50dcf218572b3ebf3d0f1fbac062ee212a78b. (skarmark@redhat.com)
- trying a replacement for class decorator (skarmark@redhat.com)
- We need to find proper repolacement for Class decorators
  (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com>
- Revert "trying a replacement for class decorator" holding off on this fix
  until discussion with folks tomorrow This reverts commit
  7ce50dcf218572b3ebf3d0f1fbac062ee212a78b. (skarmark@redhat.com)
- trying a replacement for class decorator (skarmark@redhat.com)
- We need to find proper repolacement for Class decorators
  (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com>
- Revert "trying a replacement for class decorator" holding off on this fix
  until discussion with folks tomorrow This reverts commit
  7ce50dcf218572b3ebf3d0f1fbac062ee212a78b. (skarmark@redhat.com)
- trying a replacement for class decorator (skarmark@redhat.com)
- We need to find proper repolacement for Class decorators
  (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com>
- Revert "trying a replacement for class decorator" holding off on this fix
  until discussion with folks tomorrow This reverts commit
  7ce50dcf218572b3ebf3d0f1fbac062ee212a78b. (skarmark@redhat.com)
- trying a replacement for class decorator (skarmark@redhat.com)
- We need to find proper repolacement for Class decorators
  (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com>
- Revert "trying a replacement for class decorator" holding off on this fix
  until discussion with folks tomorrow This reverts commit
  7ce50dcf218572b3ebf3d0f1fbac062ee212a78b. (skarmark@redhat.com)
- trying a replacement for class decorator (skarmark@redhat.com)
- We need to find proper repolacement for Class decorators
  (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.97-1
- Class decorators are not supported in python2.4 (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.96-1
- Class decorators are not supported in python2.4 (skarmark@redhat.com)

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.95-1
- 

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.94-1
- 

* Thu Nov 18 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.93-1
- sayli hackergotchi (mmccune@redhat.com)
- jconnor (mmccune@redhat.com)
- Preethi was on the website twice. (jrist@redhat.com)



* Mon Nov 15 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.92-1
- QE build

* Fri Nov 12 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.90-1
- Fixing build error because of missing @handler (skarmark@redhat.com)

* Fri Nov 12 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.86-1
- Removing python2.6 syntax from pulp code (skarmark@redhat.com)

* Fri Nov 12 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.85-1
- Removing python2.6 syntax from pulp code (skarmark@redhat.com)

* Fri Nov 12 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.84-1
- Removing python2.6 syntax from pulp code (skarmark@redhat.com)


* Wed Nov 10 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.83-1
- changed migrate script to use different log file to avoid permissions issues
  on fresh install (jconnor@redhat.com)
- Adding list/info functionality for package group categories
  (jmatthew@redhat.com)

* Wed Nov 10 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.82-1
- honor the published flag when exposing kickstart trees via http
  (pkilambi@redhat.com)
- continue checking rest of packages in the batch before exiting
  (pkilambi@redhat.com)
- Allow repos with distributions be accessible via http and browsable
  (pkilambi@redhat.com)
- Changing the create to return back existing distro if exists with same id
  (pkilambi@redhat.com)
- Adding additional checks to catch if distribution already exists
  (pkilambi@redhat.com)
- Adding additional checks to catch if distribution already exists
  (pkilambi@redhat.com)
- Cleanup search packages display of repos and limit data returned
  (jmatthew@redhat.com)
- oh this is not looking good... (jconnor@redhat.com)
- Improved performance of "search packages" (jmatthew@redhat.com)
- Adding support for removing old packages and specifying no of old packages to
  keep on sync (pkilambi@redhat.com)
- Exposing the repos with kickstart trees publicly via http. Apache directives
  to allow access to http://<hostname>/pulp/ks/<relative_path>
  (pkilambi@redhat.com)
- Create symlinks to /ks directory when a distribution is synced/added to the
  repo. Remove the symlinks upon distro removal from repo or repo delete.
  (pkilambi@redhat.com)
- added init.d script to rpm spec (jconnor@redhat.com)
- Fix patch that tests for dir when looking for gpg keys. (jortel@redhat.com)
- Cleaned up CLI display for search packages (jmatthew@redhat.com)
- Distribution Support: (pkilambi@redhat.com)
- Repo 'clean' will delete contents from filesystem as well as mongodb
  (jmatthew@redhat.com)
- fix for preserving group metadata from a package upload (jmatthew@redhat.com)
- 623435 - fix packagegroup metadata for non-synced repos (jmatthew@redhat.com)
- 649861 - adding a package_count field to track packages in a repo
  (mmccune@redhat.com)

* Fri Nov 05 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.81-1
- 649517 - httplib in py2.7 does not handle None headers correctly. Converting
  them to string so http requests pas through (pkilambi@redhat.com)

* Fri Nov 05 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.80-1
- adding ou to populate users script (pkilambi@redhat.com)
- update pulp.spec for gofer lib on 64bit systems and fix for ghost file
  pulp.repo (jmatthew@redhat.com)
- update pulp rpm spec so it will delete /etc/yum.repos.d/pulp.repo when rpm is
  removed (jmatthew@redhat.com)
- Add missing directories for gofer. (jortel@redhat.com)
- 649327 - removed reace conditions in get_descendants where threads
  can exit and have the references disappear while we are collecting them from
  the thread tree (jconnor@redhat.com)
- Change to return uuid of None when not registerd. (jortel@redhat.com)
- Add identity plugin. (jortel@redhat.com)
- configure so gofer lib logs in pulp.log. (jortel@redhat.com)
- Spec changes to support gofer refit. (jortel@redhat.com)
- Refit pulp to use gofer. (jortel@redhat.com)
- fixed bugs in validation for Errata description (which can possible be None)
  and reboot_suggested (which is a bool) (jconnor@redhat.com)
- fixed ldap config to not require user/password anymore. (pkilambi@redhat.com)
- Adding WS/CLI for package search (jmatthew@redhat.com)
- 649668 - Adding --server option to override config setting from commandline
  (pkilambi@redhat.com)
- added auto migration to pulp post script in rpm spec (jconnor@redhat.com)
- incremented pulp version for db versioning (jconnor@redhat.com)
- added new pulp-migrate script, including in setup.py and rpm sepc files
  (jconnor@redhat.com)
- fixed problems with validation found while hand-testing yes, this is a sucky
  commit message (jconnor@redhat.com)
- changed version check to explicit and added it to web services application
  (jconnor@redhat.com)
- changed database initialization to lazy changed logging to setup just before
  use fixed *several* logic errors in db version detection (wtf)
  (jconnor@redhat.com)

* Wed Nov 03 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.78-1
- 648918 - Correcting a small error (skarmark@redhat.com)
- adding regex search to packages call (jmatthew@redhat.com)
- 648918 - Fixing cloned repo delete problem (skarmark@redhat.com)
- 648615 - removed relative_path error in repo clone (skarmark@redhat.com)
- if no password passed in, like in acase of certificates, use a lookup
  (pkilambi@redhat.com)
- changing the user dn to user uid instead of cn by default
  (pkilambi@redhat.com)
- Adding id check to admin cert method after user object is aquired
  (pkilambi@redhat.com)
- remove password display from logs (pkilambi@redhat.com)
- clean up (pkilambi@redhat.com)
- More changes to support authentication via bind (pkilambi@redhat.com)
- External LDAP Support: (pkilambi@redhat.com)
- allowing post and put to a collection to create new resource
  (jconnor@redhat.com)
- changed controller import so they are imported directly into the application
  module (jconnor@redhat.com)
- removed test controllers from web services (jconnor@redhat.com)
- undeprecating the async calls in the base controller as we are still using
  them (jconnor@redhat.com)
- 631970 - Remove requirement to be root user to run pulp-admin.
  (jortel@redhat.com)
- 640724 - formatting consumer get_value output (skarmark@redhat.com)
- 640724 - formatting consumer get_value output (skarmark@redhat.com)
- 639980 - Error messages added when trying to add/delete/update key value for
  a non existent key with pulp-admin consumer (skarmark@redhat.com)
- Fixing unit tests for repo.packages api (skarmark@redhat.com)
- 641901 - Removing repo.packages api inconsistency (skarmark@redhat.com)
- 626451 - put error handling at the top (mmccune@redhat.com)
- 642321 - packagegroup install returns None even when a packagegroup is
  installed successfully. (jmatthew@redhat.com)
- adding comment to show user how to edit password (mmccune@redhat.com)
- 631895 - now you can edit a user and change their password
  (mmccune@redhat.com)
- 634000 -  Adding another check to validate if the consumer bound/unbound
  is same as local consumer before calling repolib update (pkilambi@redhat.com)
- 634000 -  only invoke repolib if consumer exists on the machine pulp-admin
  is executed (pkilambi@redhat.com)

* Fri Oct 29 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.77-1
- 647828 - Older clients are not able to connect to pulp on f13
  (jmatthew@redhat.com)
- 632277 - Configure 'qpid' logger to use pulp appender. (jortel@redhat.com)
- 619077 - fixing variable name (mmccune@redhat.com)
- 647522 - repo delete should now unbind consumers from the repo before
  deleteting (pkilambi@redhat.com)
- 632577 added code to logs.stop_logging to wipe out the existing
  loggers in the python logging module (jconnor@redhat.com)
- 641364 added the -u and -p options back into auth login
  (jconnor@redhat.com)
- 641438 added get_repo method to base RepoAction class that will
  exit if the repo is not found (jconnor@redhat.com)
- 638736 - Fixed.  User 'admin' not permitted by WS controller.
  (jortel@redhat.com)
- 643011 changed the default number of threads for downloads to 5
  this seems to give grinder a chance to actually calculate information needed
  for the progress bar (jconnor@redhat.com)
- 630977 - Repo list output now is formatted to show feed url and type as
  separate fields (pkilambi@redhat.com)
- 623923 - Handle read errors during upload (pkilambi@redhat.com)
- 634283 Adding consumer update to pulp-client (pkilambi@redhat.com)
- 638288 - errata installs should now be successfully scheduled
  (pkilambi@redhat.com)
- skip directories when importing keys (pkilambi@redhat.com)
- fix intermittent unit test failure on test_repo_gpgkeys (jmatthew@redhat.com)
- 643952 - pulp-admin packagegroup install failing (jmatthew@redhat.com)
- added data model version model validation (jconnor@redhat.com)
- added comments and documentation to the version module (jconnor@redhat.com)
- moved setting the version into one module added logging to one.migrate added
  comments to one module for developer posterity (jconnor@redhat.com)
- implemented version set and query methods (jconnor@redhat.com)
- changed script to use changes made in migration package and version module
  (jconnor@redhat.com)
- added database section to conf (jconnor@redhat.com)

* Tue Oct 26 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.76-1
- Fix gpg keys broken by repo publish feature. (jortel@redhat.com)
- Changed to work with 'publish' being a boolean. (jortel@redhat.com)
- unit test update for repo publish (jmatthew@redhat.com)
- Added origin feed type for repo cloning cli, gpg key cloning from parent repo
  and added handling for changing feed of cloned repo when parent is deleted
  (skarmark@redhat.com)
- Async capability for repo cloning added in api and cli (skarmark@redhat.com)
- Update subscribed systems .repo when repo 'publish' is modified.
  (jortel@redhat.com)
- patch from morazi - I stumbled on F14 versions of qpid no longer having the
  Provides:  qpidd & qpidd-ssl (pkilambi@redhat.com)
- fix for getting boolean 'default_to_published' (jmatthew@redhat.com)
- Fix relink() failing in unit tests. (jortel@redhat.com)
- Rename & fix findsubscribed() query. (jortel@redhat.com)
- Expose 'publish' field on repos in WS. (jortel@redhat.com)
- Set enabled= based on repo.published. (jortel@redhat.com)
- Add methods to update .repo on repo subscribers. (jortel@redhat.com)
- Adding repo publish --enable/--disable to CLI (jmatthew@redhat.com)
- 638715 - Changed behavior of history date queries to include the dates
  specified. (jason.dobies@redhat.com)
- 641912 - Added call to start logging on cron initiated scripts.
  (jason.dobies@redhat.com)
- 638710 - Corrected docs on date format. (jason.dobies@redhat.com)
- fix for repo create, we weren't accessing SON doc as a dictionary
  (jmatthew@redhat.com)
- rpm will create dir for 'published' and change symlink to /var/www/pub
  (jmatthew@redhat.com)
- Add repository publish - enable/disable exposure through apache
  (jmatthew@redhat.com)

* Wed Oct 20 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.75-1
- Fixing a local sync - fails sync the first time, only downloads packages but
  does not link it to repo (skarmark@redhat.com)
- Repo cloning api and cli changes (skarmark@redhat.com)
- server gpg keys using http://. Remove 'gpgkeys' from domain model and add
  listkeys() to the API.  This will work better for cloned repos. Add a
  pulp/gpg directory exposed under plain http.  Then, manage symlinks to the
  keys stored under pulp/repos.  RepoLib was refitted to fetch the keys and
  join to a new client.conf property under [cds].  The CLI was changed to
  provide:   'repo update --addkeys'   'repo update --rmkeys'   'repo listkeys'
  for key management. (jortel@redhat.com)
- Adding driver for simulating consumer create and delete events on qpid bus
  (pkilambi@redhat.com)
- Adding support to specify multiple groups when creating a repo
  (pkilambi@redhat.com)
- Adding allow_upload flag to repo collection. Feed repos will have this
  defaulted to 0 and feedless repos will have this enabled to allow uploads
  from clients (pkilambi@redhat.com)
- Adding a server side check to validate if package exists before doing an
  upload (pkilambi@redhat.com)
- Update DB w/ GPG keys during repo sync. (jortel@redhat.com)
- 623704 - Add error handling for duplicate packagroup name on creation
  (jmatthew@redhat.com)
- 623429 - --type option in packagegroup delete_package (jmatthew@redhat.com)

* Fri Oct 15 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.74-1
- 641038 - packagegroup create does not check if the repoid exists or not
  (jmatthew@redhat.com)
- added keyboard exception handler to avoid tracebacks when ctrl+c forground
  syncs (jconnor@redhat.com)
- changing base number of concurrent downloads to 3 to keep sync cancellation
  from taking forever (jconnor@redhat.com)
- moving to mongodb package name for F13+ (mmccune@redhat.com)
- Handle gpg keys when creating a repo. (jortel@redhat.com)
- 629987, 623272, 642003, 641945 package group bug fixes (jmatthew@redhat.com)
- Replace 'repo update' --gpgkeys --setkeys & --clearkeys. (jortel@redhat.com)

* Wed Oct 13 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.73-1
- repo GPG key functionality
- help and output standardization internationalization of all command/action
  descriptions, help messages, and headers separation of concatenated words in
  help output capitolization of output (not help) marked required options as
  required (jconnor@redhat.com)
- implemented auth login w/out overriding main (jconnor@redhat.com)
- 639402 - Fix repository re-sync so it does not delete uploaded packages Added
  a 'repo_defined' attribute to package objects. If the package was created by
  the repo source, then repo_defined=True if a package is an 'uploaded' package
  or anything else, repo_defined=False During a resync we will only remove
  'repo_defined=True' packages (jmatthew@redhat.com)
- restored *posibility of cli spcialization by re-instating the cli package
  (jconnor@redhat.com)
- had to modify when the usage gets set to guarantee the commands and actions
  were already set (jconnor@redhat.com)
- de-specialized the cli class and added mechanism for setting up more
  informative usage messages (jconnor@redhat.com)
- removed command and action autoloading mechanism (magic) pulp scripts now
  explicitly setup their commands and actions converted all scripts, commands,
  and actions to use new paradigm (jconnor@redhat.com)
- converted connection setup to a factory method moved get_credentials to
  credentials module moved setup_connection to connection module changed
  actions to use overridable(?) method setup_connections converted all existing
  actions to use new factory (jconnor@redhat.com)
- 641372 - Upload w/ --dir option returns an error (fix from David Gao)
  (jmatthew@redhat.com)

* Fri Oct 08 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.72-1
- --force flag had got misplaced in consumer cli instead of consumergroup
  during refactoring. Moving it to its right place. (skarmark@redhat.com)
- Adding test_keyvalue_attributes.py for testing CRUD key-value-operations on
  consumers and consumergroups (skarmark@redhat.com)
- 629720 - link for delete_consumer was pointing to consumers instead of
  consumergroups (skarmark@redhat.com)
- Somehow some of my changes were lost after consumer-cli branch merging
  resulting in consumergroup cli errors. Fixing it. (skarmark@redhat.com)
- Major refactoring of how the CLI handles commands and actions
* Mon Oct 04 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.71-1
- API and cli changes for consumer get_keyvalues and --force option for
  consumergroup add_key_values (skarmark@redhat.com)

* Mon Oct 04 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.70-1
- changed packages deferred field to actually return the packages, not just the
  ids (jconnor@redhat.com)
- if relativepath is set of the repo, save the uploaded files to that location
  (pkilambi@redhat.com)
- fix config values for RHN sync, remove debug statements (jmatthew@redhat.com)
- repo resync changes, if a package is deleted from source, delete from pulp
  fix for local syncs, still working on yum repo fetch syncs
  (jmatthew@redhat.com)
- Removing --location from consumer create and --consumerids from consumergroup
  create (non-standard and not really required) (skarmark@redhat.com)
- Minor changes in error messages (skarmark@redhat.com)
- Fixing function name error (skarmark@redhat.com)
- Error handling for adding and updating key-value pair for a consumer group
  when there is conflicting key-value of a consumer belonging to this group
  (skarmark@redhat.com)
- Error handling for adding and updating key value pair for a consumer when
  there is conflicting key-value of a consumergroup that it belongs to
  (skarmark@redhat.com)
- Adding command line options to invoke create,update and delete events
  (pkilambi@redhat.com)

* Wed Sep 29 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.69-1
- adding missing key option to repo create (pkilambi@redhat.com)
- adding fields required to allow cert based access to authenticated repos on
  pulp server (pkilambi@redhat.com)
- Displaying consumergroup key-value attributes in consumergroup list
  (skarmark@redhat.com)
- Addition of update_keyvalue api and cli to consumer and consumergroup
  (skarmark@redhat.com)
- 638182 - user create api now checks for duplicate login names and throws
  error (skarmark@redhat.com)
- Correct (2) RepoLib to properly handle repo URL with leading '/'.
  (jortel@redhat.com)
- Correct RepoLib to properly handle repo URL with leading '/'.
  (jortel@redhat.com)
- fixing some issues while performing errata installs. (pkilambi@redhat.com)
- updating logic for event based product deletes and unit tests
  (pkilambi@redhat.com)
- 634000 - Fixed.update repo on bind/unbind in the API. And, only run
  RepoLib.update() within the CLI only when (not is_admin). (jortel@redhat.com)
- Errata re-sync changes and adding search for repos by errata id If an errata
  is deleted from a repo, we look to see if any other repos contain that
  errata.  If no repos contain it, the errata is deleted, otherwise it is only
  removed from the repo mapping. (jmatthew@redhat.com)
- Adding some exception handling around update product repos
  (pkilambi@redhat.com)
- Adding event based product.update support. This commit includes, driver
  changes to support (pkilambi@redhat.com)
- save the repo objects directly in mongo instead of calling update logic
  (pkilambi@redhat.com)
- Add async RMI to agent to update pulp.repo. (jortel@redhat.com)
- Refit remaining APIs to dispatch to task subsystem for agent actions.
  (jortel@redhat.com)
- make pulp and pulp-client dep on the same version of pulp-common.
  (jortel@redhat.com)
- Updated --help to conform to updated standard. (tsanders@redhat.com)
- Updated --help to conform to updated standard.
  (tsanders@tsanders-x201.(none))
- Updated --help to conform to updated standards. (tsanders@redhat.com)
- Filter out repos by groups using server filters and adding new repo group
  lookup call to append groups dynamically to the query (pkilambi@redhat.com)
- Merge branch 'grinder-opts' (jconnor@redhat.com)
- when newer pulp is installed, it should pull in matching client versions to
  maintain compatibility on servers. (pkilambi@redhat.com)
- when newer pulp is installed, it should pull in matching client versions to
  maintain compatibility on servers. (pkilambi@redhat.com)
- forgot to cleanup commented out line (jmatthew@redhat.com)
- Fix @audit problem when a value contained a non-ascii value Package imports
  were failing on packages that had the registered trademark in their
  description. (jmatthew@redhat.com)
- exposure of more grinder options via config (jconnor@redhat.com)

* Fri Sep 24 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.68-1
- 635803 - Fixed repo sync schedule to use the existing model (for auditing and
  consumer history reapers) for the cron entries. (jason.dobies@redhat.com)
- fixing delete repos to nuke the repo from DB as well as filesystem
  (pkilambi@redhat.com)
* Wed Sep 22 2010 Mike McCune <mmccune@redhat.com> 0.0.67-1
- 634705 - suppress receiving locally published events. (jortel@redhat.com)

* Wed Sep 22 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.66-1
- Ensure complete_callback invoked in failure cases. (jortel@redhat.com)
- 619077 - make the feed check handle not being in the dict
  (mmccune@redhat.com)
- 619077 - implement repo update from CLI (mmccune@redhat.com)
- This commit includes: * Support call for product.deleted event handler to
  look for deleted action on the bus * API call to perform delete action on
  candidate/synced repos * product driver delete call (pkilambi@redhat.com)
- Enhance async API plumbing and refit installpackages(). (jortel@redhat.com)
- 626459 - The temporary yum file should be placed in the /tmp directory.
  (jason.dobies@redhat.com)
- Refactored consumer originator event detection to be done in the consumer
  history API, using the principal to determine if the request is made by an
  admin or consumer. (jason.dobies@redhat.com)
- Consumergroup api and cli changes for key-value attributes
  (skarmark@redhat.com)
- Adding consumer listing by key_value_pairs (skarmark@redhat.com)
- Adding indexes for key_value_pairs (skarmark@redhat.com)
- server-side support for last sync repo field (jconnor@redhat.com)
- merge of repo status command (jconnor@redhat.com)
- organized imports and globals addedd/fixed gettext internationalizaion on all
  print statements used print_header (jconnor@redhat.com)
- 623969 - add unit test for bug (mmccune@redhat.com)
- 623969 - make sure we convert the unicode pass to a string before hmac
  (mmccune@redhat.com)
- Added ability to disable the consumer history purge (jason.dobies@redhat.com)
- Added appropriate indices (jason.dobies@redhat.com)
- changed progress out to use sys.stdout.write instead of print reduced
  foreground sleep time to 1/4 second reduced progress bar size to accomodate
  repos w/ 100,000-999,999 packages (jconnor@redhat.com)
- 636135 - fix string format error (pkilambi@redhat.com)
- Fix SSL char * error (jesusr@redhat.com)
- added sleep back into foreground sync (jconnor@redhat.com)
- adding check for whether key exists before updating it (skarmark@redhat.com)
- adding consumerid for admin functions (skarmark@redhat.com)
- delete_keyvalue should pass in only key information (skarmark@redhat.com)
- Adding cli and api functions for adding and deleting key-value pairs
  (skarmark@redhat.com)
- Adding key_value_pairs in consumer default_fields (skarmark@redhat.com)
- Removing key_value_pairs from ConsumerDeferredFields (skarmark@redhat.com)
- merge of foreground and background sync methods (jconnor@redhat.com)
- fixed internationalization gettext calls (jconnor@redhat.com)
- Adding consumer api and cli changes for adding key-value attributes for
  consumer (skarmark@redhat.com)
- Fixing wrong package name in test_comps.py (skarmark@redhat.com)
- 629987 - Adding a check for existing package in a repo before adding or
  deleting from package group (skarmark@redhat.com)
- 629720 - delete consumer now takes care of deleting consumerid from
  consumergroups as well (skarmark@redhat.com)
- start of GET method handler for repository actions (jconnor@redhat.com)

* Fri Sep 17 2010 Mike McCune <mmccune@gmail.com> 0.0.65-1
- fixing conditonal else statement (mmccune@gmail.com)

* Fri Sep 17 2010 Mike McCune <mmccune@gmail.com> 0.0.64-1
- fedora conditional install of qpid libs (mmccune@gmail.com)

* Fri Sep 17 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.63-1
- Changing the product.created to match envelope on the bus
  (pkilambi@redhat.com)
- add a groupid filter to only display repos by groups (pkilambi@redhat.com)
- Set PendingQueue.ROOT to accessible location for unit tests.
  (jortel@redhat.com)
- Validate file imports if they exist before importing (pkilambi@redhat.com)
- 623900 - Fixed consumer delete call to pymongo to use the correct parameter
  (jason.dobies@redhat.com)
- Adding file/image sync support for local syncs (pkilambi@redhat.com)
- adding qpidd requires since we actually do require these (mmccune@gmail.com)

* Thu Sep 16 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.62-1
- Including files as a sub document in repo collection and send down file count
  per repo on repo list (pkilambi@redhat.com)
- Increase the buffsersize to 2G so we can upload larger files to pulp server
  (pkilambi@redhat.com)
- add close() to Consumer. (jortel@redhat.com)
- removed async sync calls from comps as well (jconnor@redhat.com)
- pushed async support for repo.sync down into api later added list_syncs
  methods for a given repo (jconnor@redhat.com)
- changed the display to replace the packages url with the package count
  instead of a new field (jconnor@redhat.com)
- added package count to client repo list output (jconnor@redhat.com)
- added package_count field to repository information returned by web services
  (jconnor@redhat.com)
- added package_count method to repository api (jconnor@redhat.com)
- fixed a bug where I was creating a weak reference to a weak reference
  (jconnor@redhat.com)
- converted async controllers to use new async api and handle lists of tasks
  being returned by the find call (jconnor@redhat.com)
- changed queue find to return a list of tasks instead of just the first,
  newest one found (jconnor@redhat.com)
- moved canonical server-side queue async module and implemented simple api for
  it (jconnor@redhat.com)
- changed _thread_dict to use weak references so that it no longer needs
  exlicit cleanup (jconnor@redhat.com)
- replaced deprecated call into task thread (jconnor@redhat.com)

* Fri Sep 10 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.61-1
- Added errata install and package profile entries to consumer history.
  (jason.dobies@redhat.com)
- Added defaults to pulp.conf to make the config file more self-documenting.
  This way users can look at a single location for information needed to change
  pulp behavior. (jason.dobies@redhat.com)
- consoldated exception types in thread interruption api to keep me from
  catching an exception that I do not mean to found bug in monkey patch, cut-
  copy-paster error in TaskThread.raise_exception (jconnor@redhat.com)
- use existing repositories method with fields and spec to query repos by group
  instead of a separate method (pkilambi@redhat.com)
- changing product reference to group (pkilambi@redhat.com)
- Added cron tab addition and hook so the cull will be run periodically.
  (jason.dobies@redhat.com)
- Added API call for culling consumer history older than a certain number of
  days. (jason.dobies@redhat.com)
- Adding support for relative_path and groupid when doing a repo create
  (pkilambi@redhat.com)
- include checksum in package store path (pkilambi@redhat.com)
- On demand stub creation for better plugin support. (jortel@redhat.com)
- added tracked thread and made task thread inherit from it monkey patching
  tasking.Thread wit tracked thread added look to task thread raise exception
  to deliver the same exception to all descendant threads (jconnor@redhat.com)

* Tue Sep 07 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.60-1
- Setup callbacks only for repos with source set. A feedless repo can have a
  source as None (pkilambi@redhat.com)
- fixing arch based pkg installs to pass in tuple to yum instead of str
  (pkilambi@redhat.com)
- Added date and limit support to the CLI consumer history queries
  (jason.dobies@redhat.com)
- fixes needed from rename of add_packages_to_group (jmatthew@redhat.com)
- Fixed check for consumer's existence to not rely on the consumer API.
  (jason.dobies@redhat.com)
- Added parser call for handling JSON datetime encodings.
  (jason.dobies@redhat.com)
- 618820 - Fixing indentation error (skarmark@redhat.com)
- 618820 - Adding multiple package support for packagegroup add_package
  (skarmark@redhat.com)
- adding apache perms to /src/pulp so lock files dont complain about perms
  error (pkilambi@redhat.com)
- Wired in consumer history calls to consumer API (jason.dobies@redhat.com)
- 629718 - more defensive code if we have no default locale
  (mmccune@redhat.com)
- Centralized Package Location Feature: (pkilambi@redhat.com)
- Mark messages as persistent. (jortel@redhat.com)
- adding pulpd as a script (mmccune@redhat.com)
- adding pulpd to setup script and making it executable (mmccune@redhat.com)
- 629075 - Return complete NVRE for installed packages. (jortel@redhat.com)
- Added sorting and date range query functionality (jason.dobies@redhat.com)
- Adding a dir for curl scripts to help test ws api (jmatthew@redhat.com)
- Protect against bind to repo that does not exist. (jortel@redhat.com)
- Package re-sync, if a package is deleted from the source it will be removed
  from the repo (jmatthew@redhat.com)
- Add relative_path to repo default fields. (jortel@redhat.com)
- Remove dead file & update repolib to use repo.relative_path instead of repo
  id. (jortel@redhat.com)
- make relativepath default to repoid for non product repos. This should make
  the full path basepath + <repoid> (pkilambi@redhat.com)

* Wed Sep 01 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.59-1
- adding productid to default fields and query ability (mmccune@redhat.com)
- Refine how re-raised (inbound) events are suppressed. (jortel@redhat.com)
- add builtin support for: ~/.pulp/client.conf (jortel@redhat.com)
- Fix for Errata Re-Sync updating info in an existing errata
  (jmatthew@redhat.com)
- Minor changes to event based repos (pkilambi@redhat.com)
- Fix bootstrap startup in wsgi so wont do foreach thread. (jortel@redhat.com)
- expand log format and make start_loggin() idempotent. (jortel@redhat.com)
- add bootstrap to start event listener. (jortel@redhat.com)
- update for errata sync, partial check-in adds fix for removed errata to be
  disassociated with the repo needs fix for updating an existing errata needs
  fix for deleting an errata if no repos are associated to it
  (jmatthew@redhat.com)
- if no relative path, user repoid (pkilambi@redhat.com)
- Invoke API before and only send event on succeeded. (jortel@redhat.com)
- convert the status path to string from unicode before doing a GET
  (pkilambi@redhat.com)
- Adding API call to look up repos by product and unit tests
  (pkilambi@redhat.com)
- fix relativepaths to certs (pkilambi@redhat.com)
- Use relative paths when syncing content to store on filesystem instead of
  repoid. This should help validate the client requests for content via cert
  validation (pkilambi@redhat.com)
- Correcting error in string conversion of argument (skarmark@redhat.com)
- fix product handler import. (jortel@redhat.com)
- Fix method not found exception syntax. (jortel@redhat.com)
- Replace noevent pseudo argument with thread data. (jortel@redhat.com)
- Add stubbed product event hanlder. (jortel@redhat.com)
- Add pulp event framework. (jortel@redhat.com)
- "Printing task id at the time of sync" (skarmark@redhat.com)
- Revert "Reverting cancel sync change to check whether this commit cause json
  errors" Verified that JSON errors were not because of this commit. This
  reverts commit 983791a517a85dd84b4df7197eef207b7e100489.
  (skarmark@redhat.com)

* Fri Aug 27 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.58-1
- Make sure to include the user's home directory in the destination
  (jason.dobies@redhat.com)
- Added hook to use the admin certificate if one is found.
  (jason.dobies@redhat.com)
- Fix the consumer help to list usage correctly (pkilambi@redhat.com)
- Merge branch 'master' of git+ssh://git.fedorahosted.org/git/pulp
  (pkilambi@redhat.com)
- fixing regression where we add list instead of str to install list of there
  is no arch (pkilambi@redhat.com)
- Added CLI hooks for admin login/logout. (jason.dobies@redhat.com)
- Refactored so we have access to the user object to store as the principal if
  the user is authenticated. (jason.dobies@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jconnor@redhat.com)
- implemented progress callbacks for rhn and yum repo syncs this includes a
  "pass-through" callback in tasks, that take a callback argument name and the
  callback function then passes in its own callback wrapper which executes the
  callback and assigns it to a progress field added callback parameters to all
  repo sync methods modified jmathews callback to return a dictionary
  (jconnor@redhat.com)
- Added webservice calls for admin auth certificates (jason.dobies@redhat.com)
- Added API for retrieving an admin certificate for the currently logged in
  user (jason.dobies@redhat.com)
- Merge config writes to alt config when specified. (jortel@redhat.com)
- Renamed to reflect it's an API test (jason.dobies@redhat.com)
- Added return type docs (jason.dobies@redhat.com)
- Removed plain text echo of the user's password (jason.dobies@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jconnor@redhat.com)
- Revert "Reverting cancel sync change to check whether this commit cause json
  errors" Confirmed that JSON errors were not because of this commit This
  reverts commit 983791a517a85dd84b4df7197eef207b7e100489.
  (skarmark@redhat.com)
- Reverting cancel sync change to check whether this commit cause json errors
  (skarmark@redhat.com)
- Not printing task id at the time of sync (skarmark@redhat.com)
- Adding cancel sync and sync status to cli (skarmark@redhat.com)
- shortten environment var. (jortel@redhat.com)
- Add certlib (work in progress) (jortel@redhat.com)
- Default key and cert. (jortel@redhat.com)
- Add PULP_CLIENT_ALTCONF envrionment var to specify alt conf to be merged.
  (jortel@redhat.com)
- changing client.conf to point to localhost and not guardian
  (skarmark@redhat.com)
- repo sync timeout changes (skarmark@redhat.com)
- repo sync timeout changes (skarmark@redhat.com)
- adding productid identifier as an optional reference to tie candlepin product
  to repos (pkilambi@redhat.com)
- some re-organization (jconnor@redhat.com)

* Wed Aug 25 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.57-1
- Missed an entry in the package refactor (jason.dobies@redhat.com)

* Wed Aug 25 2010 Mike McCune <mmccune@redhat.com> 0.0.56-1
- rebuild
* Wed Aug 25 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.55-1
- Release 0.1 build
* Fri Aug 20 2010 Mike McCune <mmccune@redhat.com> 0.0.54-1
- rebuild
* Fri Aug 20 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.53-1
- Missed a server import rename (jason.dobies@redhat.com)
- Merge branch 'master' into code-reorganization (jason.dobies@redhat.com)
- Discontinue installing the egg into site-packages. (jortel@redhat.com)
- Fix .spec problem with pulp-* egg. (jortel@redhat.com)
- Update spec to match code refactoring. (jortel@redhat.com)
- Update spec to match code refactoring. (jortel@redhat.com)
- Update imports for refactoring. (jortel@redhat.com)
- Updated for new package structure and cleaned up unused imports
  (jason.dobies@redhat.com)
- Updated imports for new structure (jason.dobies@redhat.com)
- quiet the logging (mmccune@redhat.com)
- Move pulptools to: pulp.client.  Update pmf imports. (jortel@redhat.com)
- update section names pmf->messaging. (jortel@redhat.com)
- moved to server where it belongs.  Updated imports and .conf section.
  (jortel@redhat.com)
- moved pmf to: pulp.messaging. (jortel@redhat.com)
- First steps in major package refactoring: just shuffling files into the
  proper directories (jason.dobies@redhat.com)
- added unicode cast to principal (jconnor@redhat.com)
- reset does not need to manage a queue managed resource (jconnor@redhat.com)
- check if packages exist before computing the length (pkilambi@redhat.com)
- set the exception to jus message instead of an object so its serializable
  (pkilambi@redhat.com)
- removing bad attributes on Task objects causing tracebacks
  (pkilambi@redhat.com)

* Wed Aug 18 2010 Mike McCune <mmccune@redhat.com> 0.0.52-1
- rebuild

* Mon Aug 16 2010 Jeff Ortel <jortel@redhat.com> 0.0.50-1
- rebuild
* Thu Aug 12 2010 Mike McCune <mmccune@redhat.com> 0.0.49-1
- rebuild
* Fri Aug 06 2010 Mike McCune <mmccune@redhat.com> 0.0.48-1
- rebuild

* Wed Aug 04 2010 Mike McCune <mmccune@redhat.com> 0.0.47-1
- rebuild
* Fri Jul 30 2010 Mike McCune <mmccune@redhat.com> 0.0.46-1
- rebuild
* Thu Jul 29 2010 Mike McCune <mmccune@redhat.com> 0.0.44-1
- rebuild

* Tue Jul 27 2010 Jason L Connor <jconnor@redhat.com> 0.0.43-1
- tio tag
* Tue Jul 27 2010 Jason L Connoe <jconnor@redhat.com> 0.0.42-1
- added gid and sticky bit to /var/[lib,log,www]/pulp directories

* Fri Jul 23 2010 Mike McCune <mmccune@redhat.com> 0.0.41-1
- rebuild
* Thu Jul 22 2010 Jason L Connor <jconnor@redhat.com> 0.0.40-1
- removed juicer from configuration

* Fri Jul 16 2010 Mike McCune <mmccune@redhat.com> 0.0.39-1
- rebuild
* Thu Jul 15 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.37-1
- Turned off client side SSL cert checking (jason.dobies@redhat.com)
- changed string index to find so that the logic will work (jconnor@redhat.com)
- added auditing to users api (jconnor@redhat.com)
- added spec and fields to users api some code clean up added check for neither
  id or certificate in create (jconnor@redhat.com)
- added auditing to packages api (jconnor@redhat.com)
- added auditing to consumer api (jconnor@redhat.com)
- added auditing to the repo api (jconnor@redhat.com)
- fixed bug in copy that doesnt return a list (jconnor@redhat.com)
- finished general code review and cleanup added _get_existing_repo to
  standardize exception message and reduce cut-copy-paste code
  (jconnor@redhat.com)

* Thu Jul 15 2010 Mike McCune <mmccune@redhat.com> 0.0.36-1
- rebuild
* Thu Jul 01 2010 Mike McCune <mmccune@redhat.com> 0.0.35-1
- rebuild

* Thu Jul 01 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.34-1
- Removed unncessary line; ownership of /var/log/pulp is given to apache in
  %post (jason.dobies@redhat.com)

* Wed Jun 30 2010 Mike McCune <mmccune@redhat.com> 0.0.33-1
- rebuild
* Mon Jun 28 2010 Mike McCune <mmccune@redhat.com> 0.0.31-1
- rebuild
* Wed Jun 23 2010 Mike McCune <mmccune@redhat.com> 0.0.28-1
- rebuild
* Mon Jun 21 2010 Mike McCune <mmccune@redhat.com> 0.0.26-1
- Weekly rebuild.  See SCM for history

* Wed Jun 16 2010 Mike McCune <mmccune@redhat.com> 0.0.24-1
- massive amounts of changes from the last few weeks

* Wed Jun 09 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.23-1
- inlcude only pulp and juicer for pulp rpm (pkilambi@redhat.com)
- Adding pulp-tools as a new subrpm (pkilambi@redhat.com)
- Change pythonpath to new client location. (jortel@redhat.com)
- Fix test_consumerwithpackage() in WS unit tests. Add
  juicer/controllers/base.py.params() to get passed parameters.
  (jortel@redhat.com)
- rename client to pulp-tools (pkilambi@redhat.com)
- removing accidental log entry (pkilambi@redhat.com)
- moving client under src for packaging (pkilambi@prad.rdu.redhat.com)
- Add consumer update() in WS. (jortel@redhat.com)
- Assign model object._id in constructor. (jortel@redhat.com)
- Another dumb mistake (jason.dobies@redhat.com)
- Fat fingered the signature (jason.dobies@redhat.com)
- streamline bind/unbind params. (jortel@redhat.com)
- Client side web service implementation for packages (jason.dobies@redhat.com)
- switching to an insert vs append so we always use src in git tree
  (mmccune@redhat.com)
- Add basic web service API tests. (jortel@redhat.com)
- Typo (jason.dobies@redhat.com)
- Initial work on packages API (jason.dobies@redhat.com)
- Added web service hook to consumer clean (jason.dobies@redhat.com)
- Added web service hook to repository clean (jason.dobies@redhat.com)
- Cleaned up for PEP8 format (jason.dobies@redhat.com)
- Cleaning up for PEP8 format (jason.dobies@redhat.com)
- Cleaning up for PEP8 format (jason.dobies@redhat.com)
- Cleaning up for PEP8 format (jason.dobies@redhat.com)
- Fixed broken config test (jason.dobies@redhat.com)
- Docs (jason.dobies@redhat.com)
- Oops, forgot to remove debug info (jason.dobies@redhat.com)
- Fixed logic for importing packages to make sure the package version doesn't
  already exist (jason.dobies@redhat.com)
- Moved non-unit test to common area (jason.dobies@redhat.com)
- Removed unsupported test file (jason.dobies@redhat.com)
- the proxy call's signature matches api (pkilambi@redhat.com)
- Added test case for RHN sync (jason.dobies@redhat.com)

* Wed Jun 09 2010 Pradeep Kilambi <pkilambi@redhat.com>
- Adding pulp-tools as a sub rpm to pulp

* Mon Jun 07 2010 Mike McCune <mmccune@redhat.com> 0.0.22-1
- Renamed method (jason.dobies@redhat.com)
- Refactored out common test utilities (jason.dobies@redhat.com)
- Removed temporary logging message (jason.dobies@redhat.com)

* Mon Jun 07 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.20-1
- reflect the subscribed repos in list (pkilambi@redhat.com)
- Adding bind and unbind support for the cli (pkilambi@redhat.com)
- If repo dir doesnt exist create it before storing the file and adding some
  logging (pkilambi@redhat.com)

* Fri Jun 04 2010 Mike McCune <mmccune@redhat.com> 0.0.18-1
- rebuild
* Thu Jun 03 2010 Mike McCune <mmccune@redhat.com> 0.0.10-1
- large numbers of changes.  see git for list
* Thu Jun 03 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.7-1
- Link the grinder synchronized packages over to apache
  (jason.dobies@redhat.com)
- was missing an import, and CompsException needed to be fully qualified
  (jmatthew@redhat.com)
- make the imports absolute to the files running
  (mmccune@gibson.pdx.redhat.com)
- added pulps configuration to wsgi script (jconnor@redhat.com)
- changed the way juicer handles pulp's configuration at runtime
  (jconnor@redhat.com)
- added preliminary packages controllers cleanup in repositories and consumers
  controllers (jconnor@redhat.com)
- removing failed test (mmccune@gibson.pdx.redhat.com)
- fixing the help options to render based on the command (pkilambi@redhat.com)
- Adding consumer commands and actions to corkscrew (pkilambi@redhat.com)
- debugging and testing of pulp rpm spec for new apache deployment
  (jconnor@redhat.com)
- removing gevet daemon deployment and adding apache deployment
  (jconnor@redhat.com)
- moving the POST to consumers call (pkilambi@redhat.com)
- Adding webservices consumer calls based on available api.
  (pkilambi@redhat.com)
- pkg counts in cli reports and adding consumer connections
  (pkilambi@redhat.com)
- Temporary configuration loading (jason.dobies@redhat.com)

* Wed Jun 02 2010 Jason L Connor <jconnor@redhat.com> 0.0.6-1
- removed gevent deployment
- added apache deployment

* Thu May 27 2010 Adam Young <ayoung@redhat.com> 0.0.5-1
- Updated Dirs in var (ayoung@redhat.com)
- Added a patch to build 32 bit on 64 bit RH systems (ayoung@redhat.com)
- Updated to the WsRepoApi (jason.dobies@redhat.com)
- First pass at web services tests (jason.dobies@redhat.com)
- Renamed RepoConnection methods to be the same as their RepoApi counterpart.
  This way, we can use the RepoConnection object as a web services proxy and
  pass it into the unit tests that make direct calls on the RepoApi object.
  (jason.dobies@redhat.com)
- moving sub calls to separate class (pkilambi@redhat.com)
- fixed typo in doc added id to repo_data for update (jconnor@redhat.com)
- spec file changes to get closer to Fedora compliance. (ayoung@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jason.dobies@redhat.com)
- Missing self reference (jason.dobies@redhat.com)
- added some task cleanup to tasks as well as the base queue class added
  cleanup calls to test_tasks (jconnor@redhat.com)
- fixed missing 'id' parameter to repository update (jconnor@redhat.com)
-  New project for pulp client. Initial commit includes: (pkilambi@redhat.com)
- removing authors (mmccune@redhat.com)
- minor cleanup (mmccune@redhat.com)
- fixed my regular expressions for repositories and test applications changed
  create repo from /repostiories/new/ to just /repositories/ in case someone
  wants a repo called 'new' updated doc to reflect change (jconnor@redhat.com)
- updated docs to reflect new id (jconnor@redhat.com)
- changing regex to accept any type of id (jconnor@redhat.com)
- added creat url to documentation (jconnor@redhat.com)
- added 'next' keyword some formatting cleanup (jconnor@redhat.com)
- create index in background and add more data to PackageGroup objects
  (jmatthew@redhat.com)
- deleting grinder.  now avail in its own git repo (mmccune@redhat.com)
- cleanup on setup and teardown (mmccune@redhat.com)
- Added grinder egg to ignore (jason.dobies@redhat.com)
- Refactored unit tests into their own directory (jason.dobies@redhat.com)
- add methods for listing package groups/categories from repo api
  (jmatthew@redhat.com)
- fixing randomString casing and making unit tests work without root
  (mmccune@redhat.com)
- adding the pulp repo file (jconnor@redhat.com)
- fixed my test_tasks for the fifo tests (jconnor@redhat.com)
- extensive regex construction for at time specifications added some
  documentation to at queues added place-holder persistent queue module
  (jconnor@redhat.com)
- Test update to see if I can commit (jason.dobies@redhat.com)
- adding object/api for PackageGroup and PackageGroupCategory to represent data
  in comps.xml (repodata). (jmatthew@redhat.com)
- mid-stream modifications of more powerful at time spec parser
  (jconnor@redhat.com)
- adding preuninstall to stop a currently running server adding forceful
  deletion of db lock to uninstall (jconnor@redhat.com)
- added user and group cleanup on uninstall to mongo's spec file
  (jconnor@redhat.com)

* Mon May 24 2010 Adam Young <ayoung@redhat.com> 0.0.4-1
- added dep for  setup-tools (ayoung@redhat.com)
- Removed the _U option that was breaking installs on epel. (ayoung@redhat.com)
- Removed build dep on pymongo, as it breaks a mock build. (ayoung@redhat.com)
- Added nosetest, with failing tests excluded. (ayoung@redhat.com)
- Corrected name in changelog (ayoung@redhat.com)
- Updated changelog. (ayoung@redhat.com)
- Updated to work with tito. (ayoung@redhat.com)
- Adding objects for PackageGroup & Category (jmatthew@redhat.com)
- removed duplicate 'consumers' definiton in ConsumerApi (jmatthew@redhat.com)
- adding unique index on all objects based on id (mmccune@redhat.com)
- pointing readme to wiki (mmccune@redhat.com)
- validate downloaded bits before status checks . this way we can clean up
  empty packages and the return error state (pkilambi@redhat.com)
- remove uneeded dir find code.  instead use magic __file__ attrib
  (mmccune@redhat.com)
- make it so we can run our tests from top level of project
  (mmccune@redhat.com)
- Automatic commit of package [grinder] release [0.0.49-1].
  (jmatthew@redhat.com)
- fix 'fetch' call to pass in hashType, this prob showed up during a long sync
  when auth data became stale we would refresh auth data, then re-call fetch.
  The call to fetch was missing hashType (jmatthew@redhat.com)
- Automatic commit of package [pulp] release [0.0.3-1]. (ayoung@redhat.com)
- adding mongo helper for json dumping (mmccune@redhat.com)
- Grinder: before fetching the repodata convert the url to ascii so urlgrabber
  doesnt freakout (pkilambi@redhat.com)
- encode urls to ascii to please urlgrabber (pkilambi@redhat.com)
- logging info change, as per QE request (jmatthew@redhat.com)

* Fri May 21 2010 Adam Young <ayoung@redhat.com> 0.0.3-2
- Added dependencies 
  
* Thu May 20 2010 Adam Young <ayoung@redhat.com> 0.0.3-1
- fixed call to setup to install all files

* Thu May 20 2010 Mike McCune <mmccune@redhat.com> 0.0.2-1
- tito tagging

* Thu May 20 2010 Adam Young 0.0.3-1
- Use macro for file entry for juicer
- strip leading line from files that are not supposed to be scripts 

* Wed May 19 2010 Adam Young  <ayoung@redhat.com> - 0.0.1
- Initial specfile
