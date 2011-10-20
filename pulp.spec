# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

# -- headers - pulp server ---------------------------------------------------

Name:           pulp
Version:        0.0.214
Release:        4%{?dist}
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
Requires: pymongo >= 1.9
Requires: python-setuptools
Requires: python-webpy
Requires: python-simplejson >= 2.0.9
Requires: python-oauth2
Requires: python-httplib2
Requires: python-isodate >= 0.4.4
Requires: python-BeautifulSoup
Requires: grinder >= 0.0.108
Requires: httpd
Requires: mod_ssl
Requires: m2crypto
Requires: openssl
Requires: python-ldap
Requires: python-gofer >= 0.37
Requires: crontabs
Requires: acl
Requires: mod_wsgi = 3.2-3.sslpatch%{?dist}
Requires: mongodb
Requires: mongodb-server
Requires: qpid-cpp-server
%if 0%{?el5}
# RHEL-5
Requires: python-uuid
Requires: python-ssl
Requires: python-ctypes
Requires: python-hashlib
%endif
%if 0%{?el6}
# RHEL-6
Requires: python-uuid
Requires: python-ctypes
Requires: python-hashlib
Requires: nss >= 3.12.9
Requires: curl => 7.19.7
%endif

# newer pulp builds should require same client version
Requires: %{name}-client >= %{version}


%description
Pulp provides replication, access, and accounting for software repositories.

# -- headers - pulp client ---------------------------------------------------

%package client
Summary:        Client side tools for managing content on pulp server
Group:          Development/Languages
BuildRequires:  rpm-python
Requires: python-simplejson
Requires: python-isodate >= 0.4.4
Requires: m2crypto
Requires: %{name}-common = %{version}
Requires: gofer >= 0.37
%if !0%{?fedora}
# RHEL
Requires: python-hashlib
%endif

%description client
A collection of tools to interact and perform content specific operations such as repo management, 
package profile updates etc.

# -- headers - pulp client ---------------------------------------------------

%package common
Summary:        Pulp common python packages.
Group:          Development/Languages
BuildRequires:  rpm-python

%description common
A collection of resources that are common between the pulp server and client.

# -- headers - pulp cds ------------------------------------------------------

%package cds
Summary:        Provides the ability to run as a pulp external CDS.
Group:          Development/Languages
BuildRequires:  rpm-python
Requires:       %{name}-common = %{version}
Requires:       gofer >= 0.37
Requires:       grinder
Requires:       httpd
Requires:       mod_wsgi = 3.2-3.sslpatch%{?dist}
Requires:       mod_ssl
Requires:       m2crypto

%description cds
Tools necessary to interact synchronize content from a pulp server and serve that content
to clients.

# -- build -------------------------------------------------------------------

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
cp -R etc/pulp/* %{buildroot}/etc/pulp

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

# Client and CDS Gofer Plugins
mkdir -p %{buildroot}/etc/gofer/plugins
mkdir -p %{buildroot}/usr/lib/gofer/plugins
cp etc/gofer/plugins/*.conf %{buildroot}/etc/gofer/plugins
cp src/pulp/client/gofer/pulpplugin.py %{buildroot}/usr/lib/gofer/plugins
cp src/pulp/cds/gofer/cdsplugin.py %{buildroot}/usr/lib/gofer/plugins

# profile plugin
mkdir -p %{buildroot}/etc/yum/pluginconf.d/
mkdir -p %{buildroot}/usr/lib/yum-plugins/
cp etc/yum/pluginconf.d/*.conf %{buildroot}/etc/yum/pluginconf.d/
cp src/pulp/client/yumplugin/pulp-profile-update.py %{buildroot}/usr/lib/yum-plugins/

# Pulp and CDS init.d
mkdir -p %{buildroot}/etc/rc.d/init.d
cp etc/rc.d/init.d/* %{buildroot}/etc/rc.d/init.d/
ln -s etc/rc.d/init.d/goferd %{buildroot}/etc/rc.d/init.d/pulp-agent

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/%{name}*.egg-info

# Touch ghost files (these won't be packaged)
mkdir -p %{buildroot}/etc/yum.repos.d
touch %{buildroot}/etc/yum.repos.d/pulp.repo

# Pulp CDS
# This should match what's in gofer_cds_plugin.conf and pulp-cds.conf
mkdir -p %{buildroot}/var/lib/pulp-cds/repos
mkdir -p %{buildroot}/var/lib/pulp-cds/packages

# Pulp CDS Logging
mkdir -p %{buildroot}/var/log/pulp-cds

# Apache Configuration
mkdir -p %{buildroot}/etc/httpd/conf.d/
cp etc/httpd/conf.d/pulp-cds.conf %{buildroot}/etc/httpd/conf.d/

%clean
rm -rf %{buildroot}

# -- post - pulp server ------------------------------------------------------

%post
setfacl -m u:apache:rwx /etc/pki/content/

# -- post - pulp cds ---------------------------------------------------------

%post cds
setfacl -m u:apache:rwx /etc/pki/content/

# Create the cluster related files and give them Apache ownership;
# both httpd (apache) and gofer (root) will write to them, so to prevent
# permissions issues put them under apache
touch /var/lib/pulp-cds/.cluster-members-lock
touch /var/lib/pulp-cds/.cluster-members

chown apache:apache /var/lib/pulp-cds/.cluster-members-lock
chown apache:apache /var/lib/pulp-cds/.cluster-members

# -- post - pulp client ------------------------------------------------------

%post client
pushd %{_sysconfdir}/rc.d/init.d
if [ "$1" = "1" ]; then
  ln -s goferd pulp-agent
fi
popd

%postun client
if [ "$1" = "0" ]; then
  rm -f %{_sysconfdir}/rc.d/init.d/pulp-agent
fi

# -- files - pulp server -----------------------------------------------------

%files
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/server/
%{python_sitelib}/pulp/repo_auth/
%config %{_sysconfdir}/pulp/pulp.conf
%config %{_sysconfdir}/pulp/repo_auth.conf
%config %{_sysconfdir}/pulp/logging
%config %{_sysconfdir}/httpd/conf.d/pulp.conf
%ghost %{_sysconfdir}/yum.repos.d/pulp.repo
%attr(775, apache, apache) %{_sysconfdir}/pulp
%attr(775, apache, apache) /srv/pulp
%attr(750, apache, apache) /srv/pulp/webservices.wsgi
%attr(750, apache, apache) /srv/pulp/repo_auth.wsgi
%attr(3775, apache, apache) /var/lib/pulp
%attr(3775, apache, apache) /var/www/pub
%attr(3775, apache, apache) /var/log/pulp
%attr(3775, root, root) %{_sysconfdir}/pki/content
%attr(775, root, root) %{_sysconfdir}/rc.d/init.d/pulp-server
%{_sysconfdir}/pki/pulp/ca.key
%{_sysconfdir}/pki/pulp/ca.crt

# -- files - common ----------------------------------------------------------

%files common
%defattr(-,root,root,-)
%doc
%{python_sitelib}/pulp/__init__.*
%{python_sitelib}/pulp/common/

# -- files - pulp client -----------------------------------------------------

%files client
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/client/
%{_bindir}/pulp-admin
%{_bindir}/pulp-client
%{_bindir}/pulp-migrate
%{_exec_prefix}/lib/gofer/plugins/pulpplugin.*
%{_prefix}/lib/yum-plugins/pulp-profile-update.py*
%{_sysconfdir}/gofer/plugins/pulpplugin.conf
%{_sysconfdir}/yum/pluginconf.d/pulp-profile-update.conf
%attr(755,root,root) %{_sysconfdir}/pki/consumer/
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/pulp-profile-update.conf
%config(noreplace) %{_sysconfdir}/pulp/client.conf
%ghost %{_sysconfdir}/rc.d/init.d/pulp-agent

# -- files - pulp cds --------------------------------------------------------

%files cds
%defattr(-,root,root,-)
%doc
%{python_sitelib}/pulp/cds/
%{python_sitelib}/pulp/repo_auth/
%{_sysconfdir}/gofer/plugins/cdsplugin.conf
%{_exec_prefix}/lib/gofer/plugins/cdsplugin.*
%attr(775, apache, apache) /srv/pulp
%attr(750, apache, apache) /srv/pulp/cds.wsgi
%config %{_sysconfdir}/httpd/conf.d/pulp-cds.conf
%config %{_sysconfdir}/pulp/cds.conf
%config %{_sysconfdir}/pulp/repo_auth.conf
%attr(3775, root, root) %{_sysconfdir}/pki/content
%attr(775, root, root) %{_sysconfdir}/rc.d/init.d/pulp-cds
%attr(3775, apache, apache) /var/lib/pulp-cds
%attr(3775, apache, apache) /var/lib/pulp-cds/repos
%attr(3775, apache, apache) /var/lib/pulp-cds/packages
%attr(3775, apache, apache) /var/log/pulp-cds

# -- changelog ---------------------------------------------------------------

%changelog
* Mon Oct 17 2011 James Slagle <jslagle@redhat.com> 0.0.214-3
- 745945 Switch to using openssl to verify a certificate against a CA so that
  we can verify against CA chains. (jslagle@redhat.com)

* Tue Oct 11 2011 James Slagle <jslagle@redhat.com> 0.0.214-2
- 742230 Add startup code to adjust the repo and cds sync schedule in rhui if
  necessary (jslagle@redhat.com)
- 734782 - DuplicateKeyError: E11000 duplicate key error index (from import
  package) Adding retry logic to work around an infrequent timing issue seen
  with mongoDB (jmatthews@redhat.com)
- patch from jlaska to remove bootstrap from the rpm spec (jconnor@redhat.com)
- removed managers import (jconnor@redhat.com)
- remove content import (jconnor@redhat.com)
- remove watchdog (jconnor@redhat.com)
- remove m2crypto import (jconnor@redhat.com)
- no longer using bootstrap.wsgi, removeing (jconnor@redhat.com)
- 743413 - moved all of pulp initialization into application module and pointed
  wsgiimportscript to webservices.wsgi (jconnor@redhat.com)
- changed debugging mode to false (jconnor@redhat.com)
- added some logic to avoid a failure_threshold of 0 bug (jconnor@redhat.com)
- made default failure threshold -1 (jconnor@redhat.com)
- Filter repo sync tasks by repo id when fetching history (jslagle@redhat.com)
- moved snapshotting of task from task enqueue to task run (jconnor@redhat.com)
- Fix for verify_options in cdslib (jmatthews@redhat.com)
- verify checksum/size defaults to False for CDS syncs (jmatthews@redhat.com)
- Adding verify_options of checksum/size for CDS sync (jmatthews@redhat.com)
- Delete grinder object after sync completes (jmatthews@redhat.com)
- 740010 - use the checksum type when creating initial metadata
  (pkilambi@redhat.com)
- changed tests to test that schedulers were all immediate on re-constitution
  of snapshots (jconnor@redhat.com)
- removed pickling of task scheduler and added immediate scheduler on re-
  creation from snapshot (jconnor@redhat.com)
- added some tests to test the validity of serializing and deserializing
  different schedulers (jconnor@redhat.com)
- cherry pickked cded2bdc94ca10c45ac96f0f4e971e7ec7bf09c2 (jconnor@redhat.com)
- Disable checksum/size check on existing packages (jmatthews@redhat.com)
- Config option for existing file checksum/size check (jmatthews@redhat.com)
- 737531 - close YumRepository after getting package lists. (jortel@redhat.com)

* Tue Jul 26 2011 Sayli Karmarkar <skarmark@redhat.com> 0.0.214-1
- Restricting threads to 4 to avoid memory leak (skarmark@redhat.com)
- Brought in line with master's version (jason.dobies@redhat.com)

* Mon Jul 18 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.211-1
- 722446 - fixing pulp to pass in proxy settings correctly to grinder
  (pkilambi@redhat.com)

* Thu Jul 14 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.208-1
- typo in conf file (jconnor@redhat.com)
- added config option to toggle auditing (jconnor@redhat.com)
- Check for None auth before trying to remove emtpy basic http authorization
  (jslagle@redhat.com)
- Switch to using append option instead of merge.  merge is not available on
  rhel 5's apache (jslagle@redhat.com)
- Fix reference to field variable (jslagle@redhat.com)
- 721021 remove empty Basic auth from end of authorization header if specified
  (jslagle@redhat.com)
- Fix check for basic auth (jslagle@redhat.com)
- Add a header that sets a blank Basic authorization for every request, needed
  for repo auth.  Remove the blank authorization when validating from the API
  side. (jslagle@redhat.com)
- Add dist to required relase for mod_wsgi (jslagle@redhat.com)
- Cherry pick d1b8a47445ceca57a9412b86d4c67a3634ed514d from master
  (jslagle@redhat.com)
- Automatic commit of package [mod_wsgi] minor release [3.2-3.sslpatch].
  (jslagle@redhat.com)
- Don't use epoch after all, use a custom release (jslagle@redhat.com)
- Reset release to 3 and use epoch to distinguish our mod_wsgi package
  (jslagle@redhat.com)
- 719955 - log.info is trying to print an entire repo object instead of just
  the id spamming the pulp logs during delete (pkilambi@redhat.com)

* Thu Jul 07 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.204-1
- Update pulp.spec to install repo_auth.wsgi correctly and no longer need to
  uncomment lines for mod_python (jslagle@redhat.com)
- Move repo_auth.wsgi to /srv (jslagle@redhat.com)
- 696669 fix unit tests for oid validation updates (jslagle@redhat.com)
- 696669 move repo auth to mod_wsgi access script handler and eliminate dep on
  mod_python (jslagle@redhat.com)

* Fri Jul 01 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.201-1
- Bringing in line with latest Pulp build version (jason.dobies@redhat.com)

- 718287 - Pulp is inconsistent with what it stores in relative URL, so
  changing from a startswith to a find for the protected repo retrieval.
  (jason.dobies@redhat.com)
- 715071 - lowering the log level during repo delete to debug
  (pkilambi@redhat.com)

* Wed Jun 29 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.199-1
- Incremented to match master. (jason.dobies@redhat.com)
- added args to returned serialized task (jconnor@redhat.com)
- converted timestamp to utc (jconnor@redhat.com)
- removed test that fails due to bug in timezone support, 716243
  (jconnor@redhat.com)
- changed tests to insert iso8601 strings as time stamps (jconnor@redhat.com)
- added tzinfo to start and end dates (jconnor@redhat.com)
- added task cancel command (jconnor@redhat.com)
- added wiki comments and tied cancel task to a url (jconnor@redhat.com)
- changed cds history query to properly deal with iso8601 timestamps
  (jconnor@redhat.com)
- added some ghetto date format validation (jconnor@redhat.com)
- converting expected iso8601 date string to datetime instance
  (jconnor@redhat.com)
- added iso8601 parsing and formating methods for date (only) instances
  (jconnor@redhat.com)
- 713742 - patch by Chris St. Pierre fixed improper rlock instance detection in
  get state for pickling (jconnor@redhat.com)
- 714046 - added login to string substitution (jconnor@redhat.com)
- forgot we want the histories to be descending... (jconnor@redhat.com)
- added new controller for generic task cancelation (jconnor@redhat.com)
- discoverd much easier to use convenience method (jconnor@redhat.com)
- converting timedelta to duration in order to properly format it
  (jconnor@redhat.com)
- fields didnt do what I thought it did (jconnor@redhat.com)
- 706953, 707986 - allow updates to modify existing schedule instead of having
  to re-specify the schedule in its entirety (jconnor@redhat.com)
- added conditional to avoid calling release on garbage collected lock
  (jconnor@redhat.com)
- only release the lock in the dispatcher on exit as we are no longer killing
  the thread on errors (jconnor@redhat.com)
- 714745 - added initial parsing call for start and end dates of cds history so
  that we convert a datetime object to local tz instead of a string
  (jconnor@redhat.com)
- 712083 - changing the error message to warnings (pkilambi@redhat.com)

* Thu Jun 23 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.197-1
- Upped version to match master builds (jason.dobies@redhat.com)
- Adding a preserve metadata as an option at repo creation time. More info
  about feature  can be found at
  https://fedorahosted.org/pulp/wiki/PreserveMetadata (pkilambi@redhat.com)
- 715504 - Apache's error_log also generating pulp log messages
  (jmatthews@redhat.com)

* Tue Jun 21 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.194-1
- Move repos under /var/lib/pulp-cds/repos so we don't serve packages straight
  up (jason.dobies@redhat.com)

* Tue Jun 21 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.193-1
- 707295 - removed relativepath from repo update; updated feed update logic to
  check if relative path matches before allowing update (pkilambi@redhat.com)
- 713493 - fixed auth login to relogin new credentials; will just replace
  existing user certs with new ones (pkilambi@redhat.com)
- Tell grinder to use a single location for package storage.
  (jason.dobies@redhat.com)
- 714691 - fixed type that caused params to resolve to an instance method
  instead of a local variable (jconnor@redhat.com)
- Fixed incorrect variable name (jason.dobies@redhat.com)
- Added CDS sync history to CDS CLI API (jason.dobies@redhat.com)
- Remove unneeded log.error for translate_to_utf8 (jmatthews@redhat.com)
- Added CLI API call for repo sync history (jason.dobies@redhat.com)
- changed corresponding unittest (jconnor@redhat.com)
- changed scheduled task behavior to reset task states on enqueue instead of on
  run (jconnor@redhat.com)
- Changed unit test logfile to /tmp/pulp_unittests.log, avoid log file being
  deleted when unit tests run (jmatthews@redhat.com)
- updated log config for rhel5, remove spaces from 'handlers'
  (jmatthews@redhat.com)
- Disable console logging for unit tests (jmatthews@redhat.com)
- Fix to work around http://bugs.python.org/issue3136 in python 2.4
  (jmatthews@redhat.com)
- Updates for Python 2.4 logging configuration file (jmatthews@redhat.com)
- Pulp logging now uses configuration file from /etc/pulp/logging
  (jmatthews@redhat.com)
- 713176 - Changed user certificate expirations to 1 week. Consumer certificate
  expirations, while configurable, remain at the default of 10 years.
  (jason.dobies@redhat.com)
- more specific documentation (jconnor@redhat.com)
- missed a find_async substitution (jconnor@redhat.com)
- refactored auth_required and error_handler decorators out of JSONController
  base class and into their own module (jconnor@redhat.com)
- eliminated AsyncController class (jconnor@redhat.com)
- making args and kwargs optional (jconnor@redhat.com)
- fixed bug in server class name and added raw request method
  (jconnor@redhat.com)
- default to no debug in web.py (jconnor@redhat.com)
- print the body instead of returning it (jconnor@redhat.com)
- quick and dirty framework for web.py parameter testing (jconnor@redhat.com)
- Updated for CR 13 (jason.dobies@redhat.com)
- Merge branch 'master' of git://git.fedorahosted.org/git/pulp
  (jslagle@redhat.com)
- bz# 709395 Fix cull_history api to convert to iso8601 format
  (jslagle@redhat.com)
- bz# 709395 Update tests for consumer history events to populate test data in
  iso8601 format (jslagle@redhat.com)
- Merge branch 'master' of git://git.fedorahosted.org/git/pulp
  (jslagle@redhat.com)
- bz# 709395 Fix bug in parsing of start_date/end_date when querying for
  consumer history (jslagle@redhat.com)

* Tue Jun 21 2011 Jay Dobies <jason.dobies@redhat.com>
- 707295 - removed relativepath from repo update; updated feed update logic to
  check if relative path matches before allowing update (pkilambi@redhat.com)
- 713493 - fixed auth login to relogin new credentials; will just replace
  existing user certs with new ones (pkilambi@redhat.com)
- Tell grinder to use a single location for package storage.
  (jason.dobies@redhat.com)
- 714691 - fixed type that caused params to resolve to an instance method
  instead of a local variable (jconnor@redhat.com)
- Fixed incorrect variable name (jason.dobies@redhat.com)
- Added CDS sync history to CDS CLI API (jason.dobies@redhat.com)
- Remove unneeded log.error for translate_to_utf8 (jmatthews@redhat.com)
- Added CLI API call for repo sync history (jason.dobies@redhat.com)
- changed corresponding unittest (jconnor@redhat.com)
- changed scheduled task behavior to reset task states on enqueue instead of on
  run (jconnor@redhat.com)
- Changed unit test logfile to /tmp/pulp_unittests.log, avoid log file being
  deleted when unit tests run (jmatthews@redhat.com)
- updated log config for rhel5, remove spaces from 'handlers'
  (jmatthews@redhat.com)
- Disable console logging for unit tests (jmatthews@redhat.com)
- Fix to work around http://bugs.python.org/issue3136 in python 2.4
  (jmatthews@redhat.com)
- Updates for Python 2.4 logging configuration file (jmatthews@redhat.com)
- Pulp logging now uses configuration file from /etc/pulp/logging
  (jmatthews@redhat.com)
- 713176 - Changed user certificate expirations to 1 week. Consumer certificate
  expirations, while configurable, remain at the default of 10 years.
  (jason.dobies@redhat.com)
- more specific documentation (jconnor@redhat.com)
- missed a find_async substitution (jconnor@redhat.com)
- refactored auth_required and error_handler decorators out of JSONController
  base class and into their own module (jconnor@redhat.com)
- eliminated AsyncController class (jconnor@redhat.com)
- making args and kwargs optional (jconnor@redhat.com)
- fixed bug in server class name and added raw request method
  (jconnor@redhat.com)
- default to no debug in web.py (jconnor@redhat.com)
- print the body instead of returning it (jconnor@redhat.com)
- quick and dirty framework for web.py parameter testing (jconnor@redhat.com)
- Updated for CR 13 (jason.dobies@redhat.com)
- Merge branch 'master' of git://git.fedorahosted.org/git/pulp
  (jslagle@redhat.com)
- bz# 709395 Fix cull_history api to convert to iso8601 format
  (jslagle@redhat.com)
- bz# 709395 Update tests for consumer history events to populate test data in
  iso8601 format (jslagle@redhat.com)
- Merge branch 'master' of git://git.fedorahosted.org/git/pulp
  (jslagle@redhat.com)
- bz# 709395 Fix bug in parsing of start_date/end_date when querying for
  consumer history (jslagle@redhat.com)

* Mon Jun 13 2011 Jeff Ortel <jortel@redhat.com> 0.0.190-1
- 707295 - updated to provide absolute path. (jortel@redhat.com)
- added tasks module to restapi doc generation (jconnor@redhat.com)
- added wiki docs for tasks collection (jconnor@redhat.com)
- added task history object details (jconnor@redhat.com)
- changing default exposure of tasking command to false (jconnor@redhat.com)
- added sync history to pic (jconnor@redhat.com)
- Disabling part of test_get_repo_packages_multi_repo that is causing test to
  take an excessive amount of time (jmatthews@redhat.com)
- Adding a 3 min timeout for test_get_repo_packages_multi_repo
  (jmatthews@redhat.com)
- 712366 - Canceling a restored sync task does not work (jmatthews@redhat.com)
- 701736 - currently syncing field shows 100% if you run repo status on a
  resync as soon as you run repo sync (jmatthews@redhat.com)
- Renamed group to cluster in CLI output (jason.dobies@redhat.com)
- Enhace incremental feedback to always show progress (pkilambi@redhat.com)
- changed return of delete to task instead of message (jconnor@redhat.com)
- fixed type in delete action (jconnor@redhat.com)
- removed superfluous ?s in regexes (jconnor@redhat.com)
- forgot leading /s (jconnor@redhat.com)
- fixed wrong set call to add elements in buld (jconnor@redhat.com)
- convert all iterable to tuples from task queries (jconnor@redhat.com)
- resolved name collision in query methods and complete callback
  (jconnor@redhat.com)
- changed inheritence to get right methods (jconnor@redhat.com)
- forgot to actually add the command to the script (jconnor@redhat.com)
- tied new task command into client.conf (jconnor@redhat.com)
- tied in new task command (jconnor@redhat.com)
- added task and snapshot formatting and output (jconnor@redhat.com)
- added class_name field to task summary (jconnor@redhat.com)
- first pass at implementing tasks command and associated actions
  (jconnor@redhat.com)
- Need to have the RPM create the cluster files and give them apache ownership;
  if root owns it apache won't be able to chmod them, and this is easier than
  jumping through those hoops. (jason.dobies@redhat.com)
- Trimmed out the old changelog again (jason.dobies@redhat.com)
- add all state and state validation (jconnor@redhat.com)
- added tasks web application (jconnor@redhat.com)
- added snapshot controllers (jconnor@redhat.com)
- added snapshot id to individual task (jconnor@redhat.com)
- changed task delete to remove the task instead of cancel it
  (jconnor@redhat.com)
- start of task admin web services (jconnor@redhat.com)
- added query methods to async and queue (jconnor@redhat.com)

* Fri Jun 10 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.189-1
- removing errata type constraint from help (skarmark@redhat.com)
- 704194 - Add path component of sync URL to event. (jortel@redhat.com)
- Allow for ---PRIVATE KEY----- without (RSA|DSA) (jortel@redhat.com)
- Fix pulp-client consumer bind to pass certificates to repolib.
  (jortel@redhat.com)
- Fix bundle.validate(). (jortel@redhat.com)
- 704599 - rephrase the select help menu (pkilambi@redhat.com)
- Fix global auth for cert consolidation. (jortel@redhat.com)
- 697206 - Added force option to CDS unregister to be able to remove it even if
  the CDS is offline. (jason.dobies@redhat.com)
- changing the epoch to a string; and if an non string is passed force it to be
  a str (pkilambi@redhat.com)
- migrate epoch if previously empty string  and set to int
  (pkilambi@redhat.com)
- Pass certificate PEM instead of paths on bind. (jortel@redhat.com)
- Fix merge weirdness. (jortel@redhat.com)
- Seventeen taken on master. (jortel@redhat.com)
- Adding a verbose option to yum plugin(on by default) (pkilambi@redhat.com)
- Merge branch 'master' into key-cert-consolidation (jortel@redhat.com)
- Migration chnages to convert pushcount from string to an integer value of 1
  (pkilambi@redhat.com)
- removing constraint for errata type (skarmark@redhat.com)
- 701830 - race condition fixed by pushing new scheduler assignment into the
  task queue (jconnor@redhat.com)
- removed re-raising of exceptions in task dispatcher thread to keep the
  dispatcher from exiting (jconnor@redhat.com)
- added docstring (jconnor@redhat.com)
- added more information on pickling errors for better debugging
  (jconnor@redhat.com)
- Add nss DB script to playpen. (jortel@redhat.com)
- Go back to making --key optional. (jortel@redhat.com)
- Move Bundle class to common. (jortel@redhat.com)
- Support CA, client key/cert in pulp.repo. (jortel@redhat.com)
- stop referencing feed_key option. (jortel@redhat.com)
- consolidate key/cert for repo auth certs. (jortel@redhat.com)
- consolidate key/cert for login & consumer certs. (jortel@redhat.com)

* Wed Jun 08 2011 Jeff Ortel <jortel@redhat.com> 0.0.188-1
- 709703 - set the right defaults for pushcount and epoch (pkilambi@redhat.com)
- removed callable from pickling in derived tasks that only can have one
  possible method passed in (jconnor@redhat.com)
- removed lock pickling (jconnor@redhat.com)
- added assertion error messages (jconnor@redhat.com)
- Automatic commit of package [PyYAML] minor release [3.09-14].
  (jmatthew@redhat.com)
- import PyYAML for brew (jmatthews@redhat.com)
- added overriden from_snapshot class methods for derived task classes that
  take different contructor arguments for re-constitution (jconnor@redhat.com)
- fixed snapshot id setting (jconnor@redhat.com)
- extra lines in errata list and search outputs and removing errata type
  constraint (skarmark@redhat.com)
- adding failure message for assert in intervalschedule test case
  (skarmark@redhat.com)
- added --orphaned flag for errata search (skarmark@redhat.com)
- re-arranging calls so that db gets cleaned up before async is initialized,
  keeping persisted tasks from being loaded (jconnor@redhat.com)
- fixing repo delete issue because of missing handling for checking whether
  repo sync invoked is completed (skarmark@redhat.com)
- added individual snapshot removal (jconnor@redhat.com)
- simply dropping whole snapshot collection in order to ensure old snapshots
  are deleted (jconnor@redhat.com)
- adding safe batch removal of task snapshots before enqueueing them
  (jconnor@redhat.com)
- added at scheduled task to get persisted (jconnor@redhat.com)
- Updated User Guide to include jconnor ISO8601 updates from wiki
  (tsanders@redhat.com)
- Bump to grinder 102 (jmatthews@redhat.com)
- Adding lock for creating a document's id because rhel5 uuid.uuid4() is not
  threadsafe (jmatthews@redhat.com)
- Adding checks to check status of the request return and raise exception if
  its not a success or redirect. Also have an optional handle_redirects param
  to tell the request to override urls (pkilambi@redhat.com)
- dont persist the scheduled time, let the scheduler figure it back out
  (jconnor@redhat.com)
- 700367 - bug fix + errata enhancement changes + errata search
  (skarmark@redhat.com)
- reverted custom lock pickling (jconnor@redhat.com)
- refactored and re-arranged functionality in snapshot storage
  (jconnor@redhat.com)
- added ignore_complete flag to find (jconnor@redhat.com)
- changed super calls and comments to new storage class name
  (jconnor@redhat.com)
- remove cusomt pickling of lock types (jconnor@redhat.com)
- consolidate hybrid storage into 1 class and moved loading of persisted tasks
  to async initialization (jconnor@redhat.com)
- moved all timedeltas to pickle fields (jconnor@redhat.com)
- removed complete callback from pickle fields (jconnor@redhat.com)
- added additional copy fields for other derived task classes
  (jconnor@redhat.com)
- reverted repo sync task back to individual fields (jconnor@redhat.com)
- fixed bug in snapshot id (jconnor@redhat.com)
- reverting back to individual field storage and pickling (jconnor@redhat.com)
- removing thread from the snapshot (jconnor@redhat.com)
- delete old thread module (jconnor@redhat.com)
- renamed local thread module (jconnor@redhat.com)
- one more try before having to rename local thread module (jconnor@redhat.com)
- change thread import (jconnor@redhat.com)
- changed to natice lock pickling and unpickling (jconnor@redhat.com)
- added custom pickling and unpickling of rlocks (jconnor@redhat.com)
- 681239 - user update and create now have 2 options of providing password,
  through command line or password prompt (skarmark@redhat.com)
- more thorough lock removal (jconnor@redhat.com)
- added return of None on duplicate snapshot (jconnor@redhat.com)
- added get and set state magic methods to PulpCollection for pickline
  (jconnor@redhat.com)
- using immediate only hybrid storage (jconnor@redhat.com)
- removed cached connections to handle AutoReconnect exceptions
  (jconnor@redhat.com)
- db version 16 for dropping all tasks serialzed in the old format
  (jconnor@redhat.com)
- more cleanup and control flow issues (jconnor@redhat.com)
- removed unused exception type (jconnor@redhat.com)
- fixed bad return on too many consecutive failures (jconnor@redhat.com)
- corrected control flow for exception paths through task execution
  (jconnor@redhat.com)
- using immutable default values for keyword arguments in constructor
  (jconnor@redhat.com)
- added timeout() method to base class and deprecation warnings for usage of
  dangerous exception injection (jconnor@redhat.com)
- removed pickling of individual fields and instead pickle the whole task
  (jconnor@redhat.com)
- comment additions and cleanup (jconnor@redhat.com)
- remove unused persistent storage (jconnor@redhat.com)
- removed unused code (jconnor@redhat.com)
- change in delimiter comments (jconnor@redhat.com)
- adding hybrid storage class that only takes snapshots of tasks with an
  immediate scheduler (jconnor@redhat.com)
- Adding progress call back to get incremental feedback on discovery
  (pkilambi@redhat.com)
- Need apache to be able to update this file as well as root.
  (jason.dobies@redhat.com)
- Adding authenticated repo support to client discovery (pkilambi@redhat.com)
- 704320 - Capitalize the first letter of state for consistency
  (jason.dobies@redhat.com)
- Return a 404 for the member list if the CDS is not part of a cluster
  (jason.dobies@redhat.com)
- Don't care about client certificates for mirror list
  (jason.dobies@redhat.com)
* Sat Jun 04 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.187-1
- Don't need the ping file, the load balancer now supports a members option
  that will be used instead. (jason.dobies@redhat.com)
- Added ability to query just the members of the load balancer, without causing
  the balancing algorithm to take place or the URL generation to be returned.
  (jason.dobies@redhat.com)
- added safe flag to snapshot removal as re-enqueue of a quickly completing,
  but scheduled task can overlap the insertion of the new snapshot and the
  removal of the old without it (jconnor@redhat.com)
- Add 'id' to debug output (jmatthews@redhat.com)
- Fix log statement (jmatthews@redhat.com)
- Adding more info so we can debug a rhel5 intermittent unit test failure
  (jmatthews@redhat.com)
- Automatic commit of package [python-isodate] minor release [0.4.4-2].
  (jmatthew@redhat.com)
- Revert "Fixing test_sync_multiple_repos to use same logic as in the code to
  check running sync for a repo before deleting it" (jmatthews@redhat.com)
- Bug 710455 - Grinder cannot sync a Pulp protected repo (jmatthews@redhat.com)
- Removing unneeded log statements (jmatthews@redhat.com)
- Removed comment (jmatthews@redhat.com)
- Adding ping page (this may change, but want to get this in place now for
  RHUI)) (jason.dobies@redhat.com)
- Enhancements to Discovery Module: (pkilambi@redhat.com)
- Reload CDS before these calls so saved info isn't wiped out
  (jason.dobies@redhat.com)
- Added better check for running syncsI swear I fixed this once...
  (jconnor@redhat.com)
- adding more information to conclicting operation exception
  (jconnor@redhat.com)
- added tear-down to for persistence to unittests (jconnor@redhat.com)
- typo fix (jconnor@redhat.com)
- Revert "renamed _sync to sycn as it is now a public part of the api"
  (jconnor@redhat.com)
- web service for cds task history (jconnor@redhat.com)
- web service for repository task history (jconnor@redhat.com)
- removed old unittests (jconnor@redhat.com)
- new task history api module (jconnor@redhat.com)
- Changed default file name handling so they can be changed in test cases.
  (jason.dobies@redhat.com)
- Refactored CDS "groups" to "cluster". (jason.dobies@redhat.com)
- updating repo file associations (pkilambi@redhat.com)
- update file delete to use new location (pkilambi@redhat.com)
- 709318 - Changing the file store path to be more unique (pkilambi@redhat.com)
