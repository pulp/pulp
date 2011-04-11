# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           pulp
Version:        0.0.162
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
Requires: pymongo >= 1.9
Requires: python-setuptools
Requires: python-webpy
Requires: python-simplejson >= 2.0.9
Requires: python-oauth2
Requires: python-httplib2
Requires: grinder >= 0.0.92
Requires: httpd
Requires: mod_wsgi
Requires: mod_ssl
Requires: m2crypto
Requires: openssl
Requires: python-ldap
Requires: python-gofer >= 0.28
Requires: crontabs
Requires: acl
Requires: mongodb
Requires: mongodb-server
Requires: qpid-cpp-server
%if 0%{?fedora}
# Fedora
Requires: mod_python
%endif
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
%endif

# newer pulp builds should require same client version
Requires: %{name}-client >= %{version}


%description
Pulp provides replication, access, and accounting for software repositories.


%package client
Summary:        Client side tools for managing content on pulp server
Group:          Development/Languages
BuildRequires:  rpm-python
Requires: python-simplejson
Requires: m2crypto
Requires: %{name}-common = %{version}
Requires: gofer >= 0.28
%if !0%{?fedora}
# RHEL
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
Requires:       %{name}-common = %{version}
Requires:       gofer >= 0.28
Requires:       grinder
Requires:       httpd
Requires:       mod_ssl
Requires:       m2crypto
%if 0%{?fedora}
# Fedora
Requires: mod_python
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

# Client and CDS Gofer Plugins
mkdir -p %{buildroot}/etc/gofer/plugins
mkdir -p %{buildroot}/usr/lib/gofer/plugins
cp etc/gofer/plugins/*.conf %{buildroot}/etc/gofer/plugins
cp src/pulp/client/gofer/pulp.py %{buildroot}/usr/lib/gofer/plugins
cp src/pulp/cds/gofer/cdsplugin.py %{buildroot}/usr/lib/gofer/plugins

# Pulp and CDS init.d
mkdir -p %{buildroot}/etc/rc.d/init.d
cp etc/rc.d/init.d/* %{buildroot}/etc/rc.d/init.d/

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

# For Fedora, enable the mod_python handler in the httpd config
%if 0%{?fedora} || 0%{?rhel} > 5
# Remove the comment flags for the auth handler lines (special format on those is #-)
sed -i -e 's/#-//g' /etc/httpd/conf.d/pulp.conf
%endif

%post cds
setfacl -m u:apache:rwx /etc/pki/content/

# For Fedora, enable the mod_python handler in the httpd config
%if 0%{?fedora} || 0%{?rhel} > 5
# Remove the comment flags for the auth handler lines (special format on those is #-)
sed -i -e 's/#-//g' /etc/httpd/conf.d/pulp-cds.conf
%endif

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


%files
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/server/
%{python_sitelib}/pulp/repo_auth/
%config(noreplace) %{_sysconfdir}/pulp/pulp.conf
%config(noreplace) %{_sysconfdir}/pulp/repo_auth.conf
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
%{python_sitelib}/pulp/cds/
%{python_sitelib}/pulp/repo_auth/
%{_sysconfdir}/gofer/plugins/cdsplugin.conf
%{_exec_prefix}/lib/gofer/plugins/cdsplugin.*
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp-cds.conf
%config(noreplace) %{_sysconfdir}/pulp/cds.conf
%config(noreplace) %{_sysconfdir}/pulp/repo_auth.conf
%attr(3775, root, root) %{_sysconfdir}/pki/content
%attr(3775, root, root) %{_sysconfdir}/rc.d/init.d/pulp-cds
/var/lib/pulp-cds
/var/log/pulp-cds


%changelog
* Mon Apr 11 2011 Jeff Ortel <jortel@redhat.com> 0.0.162-1
- Prevent multiple syncs on the same repo from occuring at the same time.
  (jmatthews@redhat.com)
- Add a check for a neg. bandwidth limit in repo_sync (jmatthews@redhat.com)
- 687353 - moved to use KeyStore.list(); added unit test. (jortel@redhat.com)
- changed task queue uniqueness to ignore kwargs and instead take into account
  the scheduler (jconnor@redhat.com)
- added check for None in scheduled time (jconnor@redhat.com)
- 694846 fixed the rest of them (jconnor@redhat.com)
- 694846 fixed cast to float of timestamp bug (jconnor@redhat.com)
- fixing utc time error in timeouts and task culling (jconnor@redhat.com)
- Move [heartbeat] to cds.conf. (jortel@redhat.com)
- 680427 - %postun needs to be enclosed in if[ = 0] for updates.  is the count
  of packages with the same name in the transaction. (jortel@redhat.com)
- enable auth handler and mod python hooks for el6 (pkilambi@redhat.com)
- 672326 - adding ability to auto import gpg keys whle performing remote
  installs (pkilambi@redhat.com)
- Inject heartbeat info at (consumer) WS layer. (jortel@redhat.com)
- Add heartbeat information & 'cds info' command. (jortel@redhat.com)
- Add Task Scheduling feature. (jconnor@redhat.com)
- added next_scheduled_sync to repo data (jconnor@redhat.com)
- fixed bug in Task str method that was not stringifying the keyword arguments
  (jconnor@redhat.com)
- changed the dispatcher thread to exit immediately instead of executing one
  last time after the exit flag is set (jconnor@redhat.com)
- added string representations for scheduler objects (jconnor@redhat.com)
- moved schedule to scheduler logic to scheduled_sync module
  (jconnor@redhat.com)
- adding init of scheduled sync on startup (jconnor@redhat.com)
- added schedules listing (jconnor@redhat.com)
- added check for type in schedule validation (jconnor@redhat.com)
- added get and delete methods for repos (jconnor@redhat.com)
- fixed a bug in error handling (jconnor@redhat.com)
- adding contrib directory for various tools (jconnor@redhat.com)
- moved enqueue out of package, package group, and errata install tasks and
  into the web services layer (jconnor@redhat.com)
- converted task queue to priority queue based on task scheduled_time
  (jconnor@redhat.com)
- made the ImmediateScheduler a single to keep memory and constructor time down
  (jconnor@redhat.com)
- modified Task to allow tasks to self-schedule (jconnor@redhat.com)
- first pass at scheduling module and base, immediate, at, and interval
  scheduler classes (jconnor@redhat.com)
- made the max concurrent tasks running configurable (jconnor@redhat.com)
- changed config import so that we don't have a race condition between the
  async import and parsing the config file (jconnor@redhat.com)
- changed task cancelation to not block on the thread.cancel() call this keeps
  the queue from remaining locked while a task cancels, potentiall blocking all
  the main wsgi threads (jconnor@redhat.com)
- changed cancel to not cancel if task is alreadly completed/
  (jconnor@redhat.com)
- renamed task.stop to task.cancel, because that's what we're doing
  (jconnor@redhat.com)
* Wed Apr 06 2011 Jeff Ortel <jortel@redhat.com> 0.0.161-1
- Moving pickling and unpickling logic to Task.py; Also changed unit tests
  accordingly (skarmark@redhat.com)
- 692888 - cleanup yum logging FileHandler(s).  Major hack until yum fixes.
  (jortel@redhat.com)
- 692876 - Fixes leaked file descriptors to: /var/lib/rpm/*.
  (jortel@redhat.com)
- Fix lockfile race condition. (jortel@redhat.com)

* Fri Apr 01 2011 Jeff Ortel <jortel@redhat.com> 0.0.160-1
- Bump to grinder 0.92 to fix minor issue displaying download progress for
  first item in repo sync (jmatthews@redhat.com)
- Adding ability to limit threads on a per repo sync operation & unit tests for
  bandwidth limiting (jmatthews@redhat.com)
- Persistence model from my-tasking branch added to master
  (skarmark@redhat.com)
- 674103 - fixing the GET request query for repo list by groups
  (pkilambi@redhat.com)
- 692669 -  groupid options need to be stacked into a list instead of a string
  (pkilambi@redhat.com)
- Support for scheduling metadata generation for a repository and check its
  status (pkilambi@redhat.com)
- Better QPID/SSL configuration. (jortel@redhat.com)

* Wed Mar 30 2011 Jeff Ortel <jortel@redhat.com> 0.0.159-1
- Convert CDS plugin configuration to SafeConfigParser. (jortel@redhat.com)
- With the addition of repo_auth to CDS, it now needs m2crypto.
  (jason.dobies@redhat.com)
- Add mod python to CDS RPM for fedora (jason.dobies@redhat.com)
- Moved CDS httpd post script to %post cds (jason.dobies@redhat.com)
- Need to add pki directory to CDS for repo auth (jason.dobies@redhat.com)
- Wired up repo and CDS apis to send repo auth info to CDS instances.
  (jason.dobies@redhat.com)
- Added repo_auth package to CDS RPM (jason.dobies@redhat.com)
- Add CDS heartbeat. (jortel@redhat.com)
- Turn on auth handling in the CDS for fedora. (jason.dobies@redhat.com)
- Wiring up for sending repo auth info to CDS instances
  (jason.dobies@redhat.com)
- Added dispatcher (and mock) calls for repo auth (jason.dobies@redhat.com)
- Added hook to remove old protected repo listings if relative path changes.
  (jason.dobies@redhat.com)
- Changed CLI logic to use the new repo update API for cert bundles.
  (jason.dobies@redhat.com)
- Changing the order of options passed to createrepo; apaprently rhel5
  createrepo is not smart enough to know its a option (pkilambi@redhat.com)
- 683498 -  fixing the help and co options for add/remove files
  (pkilambi@redhat.com)
- Massive refactoring of how config properties are handled by repo auth to
  account for running: on the server, on a CDS, and out of apache.
  (jason.dobies@redhat.com)
- 671547 - fixing error message to be explicit when scheduling errata installs
  (pkilambi@redhat.com)
- 670204: fixing repo list output (pkilambi@redhat.com)
- 683112 - fixing the error message to be more explicit (pkilambi@redhat.com)
- 683511 - fixing help text to be clearer (pkilambi@redhat.com)
- 689954 - fix the messages to say content instead of packages
  (pkilambi@redhat.com)
- Added CDS plugin hooks for setting repo and global auth.
  (jason.dobies@redhat.com)
- Added ability to remove consumer certs from a repo (jason.dobies@redhat.com)
- Enhance createrepo to preserve sqlite files, prestodelta metadata and
  updateinfo metadata (pkilambi@redhat.com)
- Added CDS plugin hooks for setting repo and global auth.
  (jason.dobies@redhat.com)
- Added ability to remove consumer certs from a repo (jason.dobies@redhat.com)
- Require grinder 0.91 (jmatthew@redhat.com)
- Require gofer 0.28 (jortel@redhat.com)
- Add ability to specify bandwidth limit for yum sync operations
  (jmatthew@redhat.com)
- Refactor (gofer) cdsplugin into: plugin & cdslib. (jortel@redhat.com)
- Fixed issue in repo update where removing consumer certs didn't flag the repo
  as unprotected. (jason.dobies@redhat.com)
- Added support for removing items from a cert bundle without deleting the
  whole directory. (jason.dobies@redhat.com)
- Added repo update/delete with cert test cases. (jason.dobies@redhat.com)
- Rename cds (gofer) plugin to 'cdsplugin'. (jortel@redhat.com)
- Added test cases for the no client cert cases (jason.dobies@redhat.com)
- Added safety check to repo URL matching and handle the case where the client
  doesn't provide a certificate. (jason.dobies@redhat.com)
- Changed lookup to get apache error log hook (jason.dobies@redhat.com)
* Mon Mar 28 2011 Jeff Ortel <jortel@redhat.com> 0.0.158-1
- Added protected repo listings file and hooks in repo create/update/delete to
  keep it updated. (jason.dobies@redhat.com)
- 691415 - Fixed schizophrenic behavior of pulp-client where it was neither
  accepting not letting the action finish without consumer id
  (skarmark@redhat.com)
- Clean up QPID dependancies. (jortel@redhat.com)
- Requires gofer 0.27.
- 690903 - fix typo. (jortel@redhat.com)
- 690903 - fix typo. (jortel@redhat.com)
- Minor fix for removing comma at the end of key-value pairs for consumergroup
  (skarmark@redhat.com)
- Minor fix for removing comma at the end of key-value pairs for consumergroup
  (skarmark@redhat.com)
- Added protected repo listing file support (jason.dobies@redhat.com)
- Integrated global CA verification into handler framework
  (jason.dobies@redhat.com)
- Added repo auth config file to pulp-dev (jason.dobies@redhat.com)
- Added repo_auth.conf to CDS and server configuration files
  (jason.dobies@redhat.com)
- Added short-circuit plugin to prevent further auth checks if the server has
  repo auth disabled (jason.dobies@redhat.com)
- Removed old auth handler and updated httpd configs to point to the new
  implementation. (jason.dobies@redhat.com)
- Added CLI options for enabling/disabling global repo auth
  (jason.dobies@redhat.com)
- 690633 - fixed minor typo in filter info error message (skarmark@redhat.com)
- 668483 - Fixed pulp-client consumer commands accepting --id as a parameter
  (skarmark@redhat.com)
- 690635 - Error message on filter delete mentions use of --force if associated
  to repos (skarmark@redhat.com)
- 690498 - changing wrong help text for filter add_packages and remove_packages
  (skarmark@redhat.com)
- Exposed service to enable/disable global repo auth (jason.dobies@redhat.com)
- Changed API to return the list of success/failed CDS instances.
  (jason.dobies@redhat.com)
- Added support for 206 PARTIAL CONTENT responses. (jason.dobies@redhat.com)
* Thu Mar 24 2011 Jeff Ortel <jortel@redhat.com> 0.0.157-1
- Add the repo auth package to the server RPM (will clean this up later, just
  need to make sure this isn't breaking the RPM build)
  (jason.dobies@redhat.com)
- Added reentrant locking to cert writes (jason.dobies@redhat.com)
- Added support for global repo cert bundles. (jason.dobies@redhat.com)
- 674119 - fixing the options for repo content (pkilambi@redhat.com)
- 669422 - Added validation for timeout values (skarmark@redhat.com)
- 668087 - Repo sync --timeout help now indicates units and an example
  (skarmark@redhat.com)
- Moved repo cert utils into the repo_auth package. (jason.dobies@redhat.com)
- 681344 - repo group is back to an array of strings until we see it necessary
  to be a hash (pkilambi@redhat.com)
- Added function to verify a cert against a CA without shelling out to openssl.
  (jason.dobies@redhat.com)
- Added auth handler framework so we can support multiple types of
  authentication styles. (jason.dobies@redhat.com)
- Hooked up consumer cert bundle to CLI. (jason.dobies@redhat.com)
- Provide for arbitrary data to be sent with heartbeat. (jortel@redhat.com)
- DB version 7 (jason.dobies@redhat.com)
- Updated repo API to accept two cert bundles, one for consumer certs and one
  for feed certs. (jason.dobies@redhat.com)
- 681344 - changing repo group id to be a hash instead of a list of strings.
  (pkilambi@redhat.com)

* Mon Mar 21 2011 John Matthews <jmatthews@redhat.com> 0.0.156-1
- fixed changelog edit (jmatthews@redhat.com)
* Mon Mar 21 2011 John Matthews <jmatthew@redhat.com> 0.0.155-1
- Add distinction of el5 or el6 in pulp.spec, remove python-ssl from el6
  (jmatthews@redhat.com)

* Fri Mar 18 2011 Jeff Ortel <jortel@redhat.com> 0.0.154-1
- 684890 - using get_required_option instead of separate checking in cli for
  consistency (skarmark@redhat.com)
- require gofer 0.24. (jortel@redhat.com)
- Apply review comments. (jortel@redhat.com)
- Added method to delete bundles for a repo. (jason.dobies@redhat.com)
- Allow a single item in the cert bundle to be written.
  (jason.dobies@redhat.com)

* Fri Mar 18 2011 John Matthews <jmatthew@redhat.com> 0.0.153-1
- Testing builds of pulp in RHEL-6-CLOUDE for brew (jmatthew@redhat.com)
- Added write cert bundle methods and test cases (jason.dobies@redhat.com)
- Started to extract out repo cert bundle related functionality and add test
  cases. (jason.dobies@redhat.com)
- 688938 - Added missing protocol prefix. (jason.dobies@redhat.com)
- Scope secret file within gofer dir. (jortel@redhat.com)
- CDS: add shared secret authentication. (jortel@redhat.com)
- Renamed test_api to test_repo_api since all tests were related to the repo
  api (jason.dobies@redhat.com)
- newly generated docs for controller modules (jconnor@redhat.com)
- Add in mod_python and enable auth handler hooks when building on Fedora.
  (jason.dobies@redhat.com)
- Formatting cleanup and truncated changelog (jason.dobies@redhat.com)
- added package_count as a default field (jconnor@redhat.com)
- added pycharm configuration to git ignore (jconnor@redhat.com)
- removed python binary and update copyright (jconnor@redhat.com)
- more wiki documentation for controllers (jconnor@redhat.com)
- fixed a bug in ordered dict that allowed duplicate keys (jconnor@redhat.com)
- fixed key error bug in ordered dict (jconnor@redhat.com)
- added module level doc string support (jconnor@redhat.com)
- first commit of new wiki rest documentation (jconnor@redhat.com)
- community release: 9. (jortel@redhat.com)
- Updated user guide for community release 9 (jason.dobies@redhat.com)
- Removing u' from filter names and added additional checking for valid regexes
  (skarmark@redhat.com)
- 681551 - removing 'not an rpm' warning messages when uploading content
  (skarmark@redhat.com)
- 681551 - removing 'not an rpm' warning messages when uploading content
  (skarmark@redhat.com)
- 674901 - Adding a way to remove a repo from a group - 'repo update --rmgroup'
  (skarmark@redhat.com)

* Fri Mar 18 2011 John Matthews <jmatthew@redhat.com> 0.0.152-1
- Testing builds of pulp in RHEL-6-CLOUDE for brew (jmatthew@redhat.com)
- Added write cert bundle methods and test cases (jason.dobies@redhat.com)
- Started to extract out repo cert bundle related functionality and add test
  cases. (jason.dobies@redhat.com)
- 688938 - Added missing protocol prefix. (jason.dobies@redhat.com)
- Scope secret file within gofer dir. (jortel@redhat.com)
- CDS: add shared secret authentication. (jortel@redhat.com)
- newly generated docs for controller modules (jconnor@redhat.com)
- Add in mod_python and enable auth handler hooks when building on Fedora.
  (jason.dobies@redhat.com)
- added package_count as a default field (jconnor@redhat.com)
- added pycharm configuration to git ignore (jconnor@redhat.com)
- removed python binary and update copyright (jconnor@redhat.com)
- community release: 9. (jortel@redhat.com)
- Updated user guide for community release 9 (jason.dobies@redhat.com)
- Removing u' from filter names and added additional checking for valid regexes
  (skarmark@redhat.com)
- 681551 - removing 'not an rpm' warning messages when uploading content
  (skarmark@redhat.com)
- 681551 - removing 'not an rpm' warning messages when uploading content
  (skarmark@redhat.com)
- 674901 - Adding a way to remove a repo from a group - 'repo update --rmgroup'
  (skarmark@redhat.com)

* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.0.151-1
- Fix consumer list accessing uncollected heartbeat stats. (jortel@redhat.com)
* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.0.150-1
- 632277 - Update package install to check consumer availability.
  (jortel@redhat.com)
- Add agent heartbeat infrastructure. (jortel@redhat.com)

* Fri Mar 11 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.149-1
- Changed from symlink to goferd to its own init.d script so it can control
  httpd too. (jason.dobies@redhat.com)
- 684263 - [cdn] Specify version of python-simplejson in pulp.spec
  (jmatthews@redhat.com)
- fixed homebrewed @wraps decorator removed unused json and itertool.wraps
  imports from standard library (jconnor@redhat.com)
- Changed gofer config to look up from pulp conf file (jason.dobies@redhat.com)
- Added pulp branded CDS config file (jason.dobies@redhat.com)
- Automatic commit of package [pulp] release [0.0.148-1].
  (jason.dobies@redhat.com)
- changed revoke_all_permissions to use new permisssion update call
  (jconnor@redhat.com)
- Minor fixes in repo filter log messages and updating filter constructor
  (skarmark@redhat.com)
- 683861 - Feed type checking error message no longer says what the error is
  (jmatthews@redhat.com)
- fix package profile action logging cert errors when not registered.
  (jortel@redhat.com)
- changed show=errors_only filter to errors_only=true|yes|1
  (jconnor@redhat.com)

* Thu Mar 10 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.148-1
- Need to add file: prefix to keys listed in the .repo file.
  (jason.dobies@redhat.com)
- Updated relative path (jason.dobies@redhat.com)
- fix consumer delete. - broken during update semantics work. - uncomment
  BaseApi.delete(). (jortel@redhat.com)
- This isn't needed; the test override config now works
  (jason.dobies@redhat.com)
- Changed config import so it properly loads the test override.
  (jason.dobies@redhat.com)
- Fixes to be able to retrieve a list of CDS sync tasks
  (jason.dobies@redhat.com)
- Added ID to round robin collection to make sure multiple repos can be
  tracked. (jason.dobies@redhat.com)
- Automatic commit of package [pulp] release [0.0.147-1]. (jortel@redhat.com)
- second pass at restapi doc generation (jconnor@redhat.com)
- removed ensure indicies in the package api, as they are now in the Package
  model class (jconnor@redhat.com)
- Fix so associate_packages doesn't add a problem repo_id twice
  (jmatthews@redhat.com)
- update semantics: Update client for Api.update() signature change.
  (jortel@redhat.com)
- removed commented-out code. (jortel@redhat.com)
- update semantics: - converted remaining APIs - changed update(delta)
  signature to update(id,delta) - added explicit update() to APIs that relied
  on BaseApi.update() and BaseApi.delete() - converted to using mongo
  collection. (jortel@redhat.com)
- 683011 - package symlinks in repos should be relative (fix for
  repository/add_packages) (jmatthews@redhat.com)
- 681866 - adding packages to a repo is very slow (jmatthews@redhat.com)
-  680444 - exception during status api call - require grinder 0.86
  (jmatthews@redhat.com)
- converted audit controller over to rest api script formating
  (jconnor@redhat.com)
- initial pass at restapi script (jconnor@redhat.com)
- cloning filter regex and combined blacklist-whitelist filter support
  (skarmark@redhat.com)
- Reworded confirmation message (jason.dobies@redhat.com)
- 682226 - filename must be unique within a repo (jmatthew@redhat.com)
- 669759 - Package installations can be scheduled for the past
  (jmatthew@redhat.com)
- removed objectdb references from the tests (jconnor@redhat.com)
- renamed self.objectdb to self.collection in all api classes
  (jconnor@redhat.com)
- moved unique indicies from api to model (jconnor@redhat.com)
- Automatic commit of package [pulp] release [0.0.146-1]. (jortel@redhat.com)
- importing some of the code cleanup from the api-declassification branch
  (jconnor@redhat.com)
- removed config reading from contructor of user api (jconnor@redhat.com)
- Fix provides/requires on uploaded packages. (jortel@redhat.com)
- 682992 - tighten up parallel uploads. (jortel@redhat.com)
- bump to grinder 0.85 to fix relative path issue with symbolic links
  (jmatthews@redhat.com)
- 683011 - package symlinks in repos should be relative (jmatthews@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- implementation of filter add_package and remove_package api, cli and test;
  added logic for confining filters only to local repos (skarmark@redhat.com)
- added start to the monitoring thread (jconnor@redhat.com)
- pep8 changes (jconnor@redhat.com)
- changed the name of the flag file (jconnor@redhat.com)
- code organization (jconnor@redhat.com)
- added stacktrace dumping to application and configuration
  (jconnor@redhat.com)
- adding "debugging" module to dump stack traces of all active threads on
  command (jconnor@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jconnor@redhat.com)
- added wingide files to gitignore (jconnor@redhat.com)
- Fixed bug where both baseurl and mirrorlist could appear on a host URL update
  when moving from one to the other. (jason.dobies@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- Bunch of fixes for CDS binding. (jason.dobies@redhat.com)
- fixing a small bug in filter delete (skarmark@redhat.com)
- Adding force flag to filter delete api for removing associations with the
  repo (skarmark@redhat.com)
- Fixed typo (jason.dobies@redhat.com)
- Added method to keystore to load keys and contents without the full path.
  (jason.dobies@redhat.com)
- Another fix to config lookup (jason.dobies@redhat.com)
- Updated to send full keys (jason.dobies@redhat.com)
- Need to load the config so the DB gets reinitialized to make sure it's
  actually using the unit test DB. (jason.dobies@redhat.com)
- Fixes for GPG key messages out to consumers on add/remove key.
  (jason.dobies@redhat.com)
- Fixed incorrect config value lookups (jason.dobies@redhat.com)
- Fixed name for gpg key lookup (jason.dobies@redhat.com)
- Restructured how the repo API sends repo updates to consumers and renamed the
  gpg keys parameter to reflect it is the keys, not just the URLs.
  (jason.dobies@redhat.com)
- Flushed out repo update unit tests and fixed bugs they uncovered.
  (jason.dobies@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- Updated with repo update semantics. (jason.dobies@redhat.com)
- Reworked bind to handle GPG key contents sent from the server.
  (jason.dobies@redhat.com)
- Added object representation of a repo's keys and methods for manipulating the
  files for those keys on the filesystem. (jason.dobies@redhat.com)
- Still rethinking the mock approach. Flushed it out with a factory so I can
  keep track of calls to one consumer v. another. (jason.dobies@redhat.com)
- Need this import to initialize the database so the test can be run on its
  own. (jason.dobies@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- Moved consumer_utils to same directory as other utils.
  (jason.dobies@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- Pulled out mock repo proxy so it can be reused across tests.
  (jason.dobies@redhat.com)
- Finished test cases (jason.dobies@redhat.com)
- Added a web service call for redistribute and hooks to auto-redistribute on a
  CDS repo association. (jason.dobies@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- Merge branch 'master' into cds (jason.dobies@redhat.com)
- Implemented redistribute logic to balance consumers across all CDS instances
  for a repo. (jason.dobies@redhat.com)
- Pulled out bind data creation since it is used for sending out repo/host url
  updates as well. (jason.dobies@redhat.com)

* Thu Mar 10 2011 Jeff Ortel <jortel@redhat.com> 0.0.147-1
- Fix so associate_packages doesn't add a problem repo_id twice
  (jmatthews@redhat.com)
- 681866 - adding packages to a repo is very slow (jmatthews@redhat.com)
- 683011 - package symlinks in repos should be relative (fix for
  repository/add_packages) (jmatthews@redhat.com)

* Tue Mar 08 2011 Jeff Ortel <jortel@redhat.com> 0.0.146-1
- 682992 - tighten up parallel uploads. (jortel@redhat.com)
- Fix provides/requires on uploaded packages. (jortel@redhat.com)
- Bump to grinder 0.85 to fix relative path issue with symbolic links
  (jmatthews@redhat.com)
- 683011 - package symlinks in repos should be relative (jmatthews@redhat.com)

* Mon Mar 07 2011 Jeff Ortel <jortel@redhat.com> 0.0.145-1
- Remove old get_packages_by_nvera_original() (jmatthews@redhat.com)
- 681866 - Changed get_packages_by_nvera to use a mongo $or query
  (jmatthews@redhat.com)
- 681304 - repo sync failing with Type error, requires grinder 0.83
  (jmatthews@redhat.com)
- Fixing broken repo cloning unit test (skarmark@redhat.com)
- Added ability to specify multiple filters when associating with repo and cli
  changes for filter info (skarmark@redhat.com)
- adding a playpen script to try out WS services/associate/packages call
  (jmatthews@redhat.com)
- 681866/68226 - adding packages to a repo is very slow/filename must be unique
  within a repo (jmatthews@redhat.com)
- Add package/file (uploaded/deleted) events. (jortel@redhat.com)
- 682225 - Fixed typo in add-package error messaging (tsanders@redhat.com)
- 681659 - Fixing error messaging for content delete action
  (tsanders@redhat.com)
- 682294 - removed super() call from setup_parser() on import and export
  calls (dgao@redhat.com)
- 682232 - Fixing error messaging in add/remove actions for repositories.
  (tsanders@redhat.com)
- Removed test dependency on redhat vpn (skarmark@redhat.com)
- CLI for associating filters to a repo (skarmark@redhat.com)
- 681989 - fixing some typos in add/remove error messages (pkilambi@redhat.com)
- Model, api changes and unit tests for associating filters to a repo
  (skarmark@redhat.com)
- 680393 - prevent delete of referenced package. (jortel@redhat.com)
- 677695 -  adding some improvements from dmach to make checksum look ups
  faster (pkilambi@redhat.com)
- disable regex search for content add/deletes (pkilambi@redhat.com)
- 681804 -  fixing the uploads to ignore regex search and do a direct lookup
  (pkilambi@redhat.com)
- update file delete to use new location (pkilambi@redhat.com)
- storing files seperate to make lookup easier (pkilambi@redhat.com)
- bumping grinder version dep (pkilambi@redhat.com)
- 680366 - revamp the package storage path to be n/v/r/a/<hash>/.rpm. There is
  also a corresponding grinder change for yum syncs (pkilambi@redhat.com)

* Wed Mar 02 2011 Jeff Ortel <jortel@redhat.com> 0.0.144-1
- 681601 - fixing help for repo add/remove operations (pkilambi@redhat.com)
- 681545 - fixing error message (pkilambi@redhat.com)
- user validation must allow for passwords of None (jconnor@redhat.com)
- 681619 - use older style look up for older yums (pkilambi@redhat.com)
- Changing incorrect PUT request to POST for creating filters
  (skarmark@redhat.com)
- Adding cli and basic unit tests for cloning filters (skarmark@redhat.com)
- reverting back to using the user api (jconnor@redhat.com)
- Raise events when repo updated including content changes. (jortel@redhat.com)
- Adding new fields for errata * added rights, severity, sums, type * updated
  api/ws and cli * updated the add_errata to not require source repo
  (pkilambi@redhat.com)
- Beginnings of extracting out some consumer logic/queries to prevent circular
  API dependencies. (jason.dobies@redhat.com)
- Added hooks to associating a repo with a CDS to add the association into the
  host URL calculation. (jason.dobies@redhat.com)
- Added hooks from bind into CDS round-robin algorithm.
  (jason.dobies@redhat.com)
- Implemented generate and iterator functions. (jason.dobies@redhat.com)
- API update semantics: convert ConsumerApi. (jortel@redhat.com)
- API update semantics: convert ErrataApi. (jortel@redhat.com)
- API update semantics: convert UserApi. (jortel@redhat.com)
- API update semantics: convert RepoApi. (jortel@redhat.com)
- 681016 - log the warning and remove the errata (pkilambi@redhat.com)
- 677695 - calls to lookup checksums for packages/files (pkilambi@redhat.com)
- fix encoding while displaying the comps data (pkilambi@redhat.com)
- The lock eagerly creates the file, so shift the default lock instantiation to
  only if it is needed. (jason.dobies@redhat.com)
- updating default config to match new relative path /pulp/repos
  (jconnor@redhat.com)
- 680868 - minor fix to import help options (pkilambi@redhat.com)
- Fixed DB migration code to work with new collection APIs.
  (jason.dobies@redhat.com)
- added comment explaining how to setup get_collections for Model class
  (jconnor@redhat.com)
- 674902 - Fix repo.update() of ca/cert/key. (jortel@redhat.com)
- Support to Import/Export comps.xml (pkilambi@redhat.com)
- Wired up new client/server bind and unbind APIs to new client repolib logic.
  (jason.dobies@redhat.com)
- Added factory methods for consumer repo proxy (more still need to be added
  and APIs refactored to use them). (jason.dobies@redhat.com)
- Added logging calls (jason.dobies@redhat.com)
- Added test to verify adding an existing repo functionality.
  (jason.dobies@redhat.com)
- Added pretty important doc that bind is for both add and update.
  (jason.dobies@redhat.com)
- Modified repolib.bind to work in both add and update cases.
  (jason.dobies@redhat.com)
- Removed unnecessary ActionLock class. (jason.dobies@redhat.com)
- Finished implementing tests and bug fixes found by them.
  (jason.dobies@redhat.com)
- Added comment to indicate the test needs to check for mirror list entry
  order. (jason.dobies@redhat.com)
- Big refactor of repolib to remove coupling to the server and work on the data
  no matter how it came into the consumer.  (jason.dobies@redhat.com)
- Added repo file location as a config value. (jason.dobies@redhat.com)
- Added safe load and add_entries methods for repos. (jason.dobies@redhat.com)
- Added support for writing mirror lists, including in the repo configuration.
  (jason.dobies@redhat.com)

* Fri Feb 25 2011 Jeff Ortel <jortel@redhat.com> 0.0.143-1
- added collection caching to Model base class (jconnor@redhat.com)
- 680462 - filter out empty lines from csv (pkilambi@redhat.com)
- changed data model versioning to use the new Model.get_collection()
  (jconnor@redhat.com)
- strip any white spaces while reading the csv entries (pkilambi@redhat.com)
- changing help desc to note optional (pkilambi@redhat.com)
- 678119 - Requiring updated grinder and adding integration test for yum sync
  (jmatthews@redhat.com)
- 678119 - Fix local sync portion for missing fields in repo sync status
  (jmatthews@redhat.com)
- adding a check to make sure package object was retrieved if not skip the
  package (pkilambi@redhat.com)
- retry chunk upload on network/ssl errors. (jortel@redhat.com)
- 680079 - python 2.4 compat: custom wrapper instead of bytearray.
  (jortel@redhat.com)

* Wed Feb 23 2011 Jeff Ortel <jortel@redhat.com> 0.0.142-1
- updating unit tests as duplicatekey is caucht at the api level
  (pkilambi@redhat.com)
- Errata cli crud operations (pkilambi@redhat.com)
- 679889 - use bytearray instead of bytes. (jortel@redhat.com)
- adding a catch for DuplicateKeyError and return the existing file object
  (pkilambi@redhat.com)
- Refactored out repo file so we can more easily plug in different approaches
  for CDS binding. Removed hardcoded filename limitation so we can test and
  later allow multiple consumers per machine. (jason.dobies@redhat.com)

* Wed Feb 23 2011 Jeff Ortel <jortel@redhat.com> 0.0.141-1
- 679800 - handle POST/PUT body othen than dict but still handle binary.
  (jortel@redhat.com)
- 677738 - fixing local sync checksum type to use sha256 (skarmark@redhat.com)
- added the split of the server-side traceback out when raising a server
  request error (jconnor@redhat.com)
- Make uuid optional to resume upload. (jortel@redhat.com)
- 679692 - check for signature before extracting the metadata. This should save
  some cpu for unsigned packages to be skipped (pkilambi@redhat.com)
- added status service at /services/status that returns the # of times the
  service has been called, the current db data model in use, and the length of
  time it took to calculate all that as a GET call that does not require auth
  credentials all courtesy of Lukas Zapletal <lzap+fed@redhat.com>
  (jconnor@redhat.com)
- Add optional checksum to UploadAPI.upload(). (jortel@redhat.com)
- Only write upload momento on keyboard interupt. (jortel@redhat.com)
- Repo delete enhancements: * purge packages by default.
  (pkilambi@redhat.com)
- Change from base64 encoded to binary uploads.  (jortel@redhat.com)
- 669779 - fixed bug in exception serialization (jconnor@redhat.com)
- removing purge-file option on remove_file; remove_file is more a selective
  sync operation, so instead move the puirge logic to delete repo. repo
  remove_file will only remove the file reference from repo[files] like it
  should. (pkilambi@redhat.com)
- Adding support for pulp-admin content delete (pkilambi@redhat.com)
- 669209, 669213 - Raising PulpException when trying to add a consumer with
  conflicting keyvalues (skarmark@redhat.com)
- Adding a new command, * pulp-admin content * moving upload and list to
  content command * adding a call to list orphaned files (pkilambi@redhat.com)
- 669209, 669213 - Raising PulpException when trying to add a consumer with
  conflicting keyvalues (skarmark@redhat.com)
- 679501 - If no orphaned packages, print a message (pkilambi@redhat.com)
- adding default list instead of None (jconnor@redhat.com)
- correcting bad super class constructor call (jconnor@redhat.com)
- 679461 - Change the associations message to be more generic
  (pkilambi@redhat.com)
- 679441 - return error codes based on the output (pkilambi@redhat.com)
- Configurable checksum type on repo: * db model change to include
  checksum_type * migration changes * api/ws changes * cli option on repo
  create (pkilambi@redhat.com)

* Tue Feb 22 2011 Jeff Ortel <jortel@redhat.com> 0.0.140-1
- Refactor client connections into API classes that miror API classes
  in the server.api package.
- Refactor connections base into server module.
- remove the allow_upload option on repos and allow all uploads by default
  (pkilambi@redhat.com)
- only attempt to remove files if they are not part of other repos
  (pkilambi@redhat.com)
- added fields filter to packages deferred field to enable limiting of package
  fields passed back by api (jconnor@redhat.com)
- 669802 - consumergroup list now presents key-value attributes the same way as
  consumer list presents them (skarmark@redhat.com)
- Adding a keep_files option to remove_files and --purge-files to cli
  (pkilambi@redhat.com)
- list repo packages in csv format (pkilambi@redhat.com)
- cleaning up the content ws and adding a delete call (pkilambi@redhat.com)
- Adding orphaned packages lookp on the client to show in csv type format
  (pkilambi@redhat.com)
- remove restrictions on rpm type; allows any type of upload
  (pkilambi@redhat.com)
- Upload Enhancements: support non-rpms; chunked, interruptable upload.
  (pkilambi@redhat.com)
- 668097 - Added enumerated value set and checking for arch when creating a
  repo. (jason.dobies@redhat.com)
- fixed types parameter from query in errata (jconnor@redhat.com)
- removed the list_errata action and changed the client to use the errata
  deferred field (jconnor@redhat.com)
- experiment with map/reduce for computing orphaned_packages
  (jmatthews@redhat.com)
- 678658- Fix client refactoring & auth issues. (jortel@redhat.com)
- Adding packages.orphaned_packages() returns list of packages not associated
  to any repository (jmatthews@redhat.com)
- Add chunksize to (client) UploadAPI.upload(). (jortel@redhat.com)
- removing checksum type from csv and have it default to sha256
  (pkilambi@redhat.com)
- Fix upload file validity testing. (jortel@redhat.com)
- Production location /var/lib/pulp and updated docs. (jortel@redhat.com)
- Add generic file upload service. (jortel@redhat.com)
- Ability to restrict uploading unsigned packages. --nosig to allow unsigned
  uploads (pkilambi@redhat.com)
- changed all username password signature to make password optional
  (jconnor@redhat.com)
- Restrict package associations to NVREA. If package with same nvrea exists
  add_package will log the message and skip the associations
  (pkilambi@redhat.com)
- * Adding csv and checksum lookup support for add/remove operations
  (pkilambi@redhat.com)
- replaced the connection objects with new api objects (jconnor@redhat.com)
- changed cli to use new global server added simpler, more stream lined
  credential handling (jconnor@redhat.com)
- storing active server in server module (jconnor@redhat.com)
- changed out restlib exception to new server request error
  (jconnor@redhat.com)
- changed all server calls made by the api to take into account that server
  requests now return a tuple of (status, body) instead of just body
  (jconnor@redhat.com)
- added lazy setting of the server to the called action (jconnor@redhat.com)
- added code in server to default to using basic auth over ssl credentials
  (jconnor@redhat.com)

* Wed Feb 16 2011 Jeff Ortel <jortel@redhat.com> 0.0.139-1
- added try/except for handling of certs other than admin in check_user_cert
  (jconnor@redhat.com)
- added check_consumer_cert (jconnor@redhat.com)
- changed ssl cert check call in prep for differenciating between user and
  consumer certs (jconnor@redhat.com)
- fixed typo that causes a traceback during exception handling when pkg already
  exists (dgao@redhat.com)
