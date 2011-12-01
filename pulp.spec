# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

%if 0%{?rhel} == 5
%define pulp_selinux 0
%else
%define pulp_selinux 1
%endif

%if %{pulp_selinux}
#SELinux
%define selinux_variants mls strict targeted
%define selinux_policyver %(sed -e 's,.*selinux-policy-\\([^/]*\\)/.*,\\1,' /usr/share/selinux/devel/policyhelp 2> /dev/null)
%define moduletype apps
%endif

# -- headers - pulp server ---------------------------------------------------

Name:           pulp
Version:        0.0.253
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
Requires: python-oauth2 >= 1.5.170-2.pulp%{?dist}
Requires: python-httplib2
Requires: python-isodate >= 0.4.4-3.pulp%{?dist}
Requires: python-BeautifulSoup
Requires: grinder >= 0.0.128
Requires: httpd
Requires: mod_ssl
Requires: openssl
Requires: python-ldap
Requires: python-gofer >= 0.60
Requires: crontabs
Requires: acl
Requires: mod_wsgi >= 3.2-4.pulp%{?dist}
Requires: mongodb
Requires: mongodb-server
Requires: qpid-cpp-server
%if 0%{?rhel} == 5
Requires: m2crypto
%else
Requires: m2crypto = 0.21.1.pulp
%endif

%if %{pulp_selinux}
Requires: %{name}-selinux-server = %{version}
%endif

%if 0%{?rhel} == 5
# RHEL-5
Requires: python-uuid
Requires: python-ssl
Requires: python-ctypes
Requires: python-hashlib
Requires: createrepo = 0.9.8-3
%endif
%if 0%{?rhel} == 6
# RHEL-6
Requires: python-ctypes
Requires: python-hashlib
Requires: nss >= 3.12.9
Requires: curl => 7.19.7
%endif

# Both attempt to serve content at the same apache alias, so don't
# allow them to be installed at the same time.
Conflicts:      pulp-cds

%description
Pulp provides replication, access, and accounting for software repositories.

# -- headers - pulp client lib ---------------------------------------------------

%package client-lib
Summary:        Client side libraries pulp client tools
Group:          Development/Languages
BuildRequires:  rpm-python
Requires:       python-simplejson
Requires:       python-isodate >= 0.4.4
Requires:       m2crypto
Requires:       %{name}-common = %{version}
Requires:       gofer >= 0.60
Requires:       gofer-package >= 0.60
%if !0%{?fedora}
# RHEL
Requires:       python-hashlib
%endif
Requires:       python-rhsm >= 0.96.4
Obsoletes:      pulp-client <= 0.218

%description client-lib
A collection of libraries used by by the pulp client tools.

# -- headers - pulp client ---------------------------------------------------

%package consumer
Summary:        Client side tool for pulp consumers
Group:          Development/Languages
Requires:       %{name}-client-lib = %{version}
Obsoletes:      pulp-client <= 0.218

%description consumer
A client tool used on pulp consumers to do things such as consumer
registration, and repository binding.

# -- headers - pulp admin ---------------------------------------------------

%package admin
Summary:        Admin tool to administer the pulp server
Group:          Development/Languages
Requires:       %{name}-client-lib = %{version}
Obsoletes:      pulp-client <= 0.218

%description admin
A tool used to administer the pulp server, such as repo creation and synching,
and to kick off remote actions on consumers.

# -- headers - pulp common ---------------------------------------------------

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
Requires:       gofer >= 0.60
Requires:       grinder >= 0.0.126
Requires:       httpd
Requires:       mod_wsgi >= 3.2-4.pulp%{?dist}
Requires:       mod_ssl
%if 0%{?rhel} == 5
Requires: m2crypto
%else
Requires: m2crypto = 0.21.1.pulp
%endif
%if %{pulp_selinux}
Requires: %{name}-selinux-server = %{version}
%endif
BuildRequires:  rpm-python
# Both attempt to serve content at the same apache alias, so don't
# allow them to be installed at the same time.
Conflicts:      pulp

%description cds
Tools necessary to interact synchronize content from a pulp server and serve that content
to clients.

# -- headers - pulp-selinux-server ---------------------------------------------------
%if %{pulp_selinux}
%package        selinux-server
Summary:        Pulp SELinux policy for server components.
Group:          Development/Languages
BuildRequires:  rpm-python
BuildRequires:  make
BuildRequires:  checkpolicy
BuildRequires:  selinux-policy-devel
BuildRequires:  hardlink

%if "%{selinux_policyver}" != ""
Requires: selinux-policy >= %{selinux_policyver}
%endif
Requires(post): /usr/sbin/semodule, /sbin/fixfiles
Requires(postun): /usr/sbin/semodule

%description    selinux-server
SELinux policy for Pulp's server components
%endif

# -- build -------------------------------------------------------------------

%prep
%setup -q

%build
pushd src
%{__python} setup.py build
popd
%if %{pulp_selinux}
# SELinux Configuration
cd selinux/server
perl -i -pe 'BEGIN { $VER = join ".", grep /^\d+$/, split /\./, "%{version}.%{release}"; } s!0.0.0!$VER!g;' pulp-server.te
./build.sh
cd -
%endif

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
mkdir -p %{buildroot}/var/lib/pulp/plugins
mkdir -p %{buildroot}/var/lib/pulp/plugins/distributors
mkdir -p %{buildroot}/var/lib/pulp/plugins/importers
mkdir -p %{buildroot}/var/lib/pulp/plugins/profilers
mkdir -p %{buildroot}/var/lib/pulp/plugins/types
mkdir -p %{buildroot}/var/lib/pulp/published
mkdir -p %{buildroot}/var/www
ln -s /var/lib/pulp/published %{buildroot}/var/www/pub

# Client and CDS Gofer Plugins
mkdir -p %{buildroot}/etc/gofer/plugins
mkdir -p %{buildroot}/%{_libdir}/gofer/plugins
cp etc/gofer/plugins/*.conf %{buildroot}/etc/gofer/plugins
cp -R src/pulp/client/consumer/goferplugins/*.py %{buildroot}/%{_libdir}/gofer/plugins
cp src/pulp/cds/gofer/cdsplugin.py %{buildroot}/%{_libdir}/gofer/plugins

# profile plugin
mkdir -p %{buildroot}/etc/yum/pluginconf.d/
mkdir -p %{buildroot}/%{_libdir}/yum-plugins/
cp etc/yum/pluginconf.d/*.conf %{buildroot}/etc/yum/pluginconf.d/
cp src/pulp/client/consumer/yumplugin/pulp-profile-update.py %{buildroot}/%{_libdir}/yum-plugins/

# Pulp and CDS init.d
mkdir -p %{buildroot}/etc/rc.d/init.d
cp etc/rc.d/init.d/* %{buildroot}/etc/rc.d/init.d/
if [ ! -e %{buildroot}/etc/rc.d/init.d/pulp-agent ]
then
    ln -s etc/rc.d/init.d/goferd %{buildroot}/etc/rc.d/init.d/pulp-agent
fi

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

%if %{pulp_selinux}
# Install SELinux policy modules
cd selinux/server
./install.sh %{buildroot}%{_datadir}
mkdir -p %{buildroot}%{_datadir}/pulp/selinux/server
cp enable.sh %{buildroot}%{_datadir}/pulp/selinux/server
cp uninstall.sh %{buildroot}%{_datadir}/pulp/selinux/server
cp relabel.sh %{buildroot}%{_datadir}/pulp/selinux/server
cd -
%endif


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

#%if %{pulp_selinux}
# Enable SELinux policy modules
#%{_datadir}/pulp/selinux/server/enable.sh %{_datadir}
#%endif
# -- post - pulp consumer ------------------------------------------------------

%post consumer
if [ "$1" = "1" ]; then
  ln -s %{_sysconfdir}/rc.d/init.d/goferd %{_sysconfdir}/rc.d/init.d/pulp-agent
fi

%if %{pulp_selinux}
%post selinux-server
# Enable SELinux policy modules
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/enable.sh %{_datadir}
fi

# restorcecon wasn't reading new file contexts we added when running under %post so moved to %posttrans
# Spacewalk saw same issue and filed BZ here: https://bugzilla.redhat.com/show_bug.cgi?id=505066
%posttrans
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/relabel.sh %{_datadir}
fi

%preun selinux-server
# Clean up after package removal
if [ $1 -eq 0 ]; then
%{_datadir}/pulp/selinux/server/uninstall.sh
fi
exit 0
%endif

%postun consumer
if [ "$1" = "0" ]; then
  rm -f %{_sysconfdir}/rc.d/init.d/pulp-agent
fi

%postun cds
# Clean up after package removal

# -- files - pulp server -----------------------------------------------------

%files
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/server/
%{python_sitelib}/pulp/repo_auth/
%config(noreplace) %{_sysconfdir}/pulp/pulp.conf
%config(noreplace) %{_sysconfdir}/pulp/repo_auth.conf
%config(noreplace) %{_sysconfdir}/pulp/logging
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
%{_bindir}/pulp-migrate
# -- files - common ----------------------------------------------------------

%files common
%defattr(-,root,root,-)
%doc
%{python_sitelib}/pulp/__init__.*
%{python_sitelib}/pulp/common/

# -- files - pulp client lib -----------------------------------------------------

%files client-lib
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/client/api
%{python_sitelib}/pulp/client/lib
%{python_sitelib}/pulp/client/pluginlib
%{python_sitelib}/pulp/client/plugins
%{python_sitelib}/pulp/client/*.py*

# -- files - pulp client -----------------------------------------------------

%files consumer
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/client/consumer
%{_bindir}/pulp-consumer
%{_libdir}/gofer/plugins/*.py*
%{_libdir}/yum-plugins/pulp-profile-update.py*
%{_sysconfdir}/gofer/plugins/pulpplugin.conf
%{_sysconfdir}/gofer/plugins/consumer.conf
%{_sysconfdir}/yum/pluginconf.d/pulp-profile-update.conf
%attr(755,root,root) %{_sysconfdir}/pki/consumer/
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/yum/pluginconf.d/pulp-profile-update.conf
%config(noreplace) %{_sysconfdir}/pulp/consumer/consumer.conf
%ghost %{_sysconfdir}/rc.d/init.d/pulp-agent

# -- files - pulp admin -----------------------------------------------------

%files admin
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/client/admin
%{_bindir}/pulp-admin
%config(noreplace) %{_sysconfdir}/pulp/admin/admin.conf
%config(noreplace) %{_sysconfdir}/pulp/admin/task.conf
%config(noreplace) %{_sysconfdir}/pulp/admin/job.conf

# -- files - pulp cds --------------------------------------------------------

%files cds
%defattr(-,root,root,-)
%doc
%{python_sitelib}/pulp/cds/
%{python_sitelib}/pulp/repo_auth/
%{_sysconfdir}/gofer/plugins/cdsplugin.conf
%{_libdir}/gofer/plugins/cdsplugin.*
%attr(775, apache, apache) /srv/pulp
%attr(750, apache, apache) /srv/pulp/cds.wsgi
%config %{_sysconfdir}/httpd/conf.d/pulp-cds.conf
%config(noreplace) %{_sysconfdir}/pulp/cds.conf
%config(noreplace) %{_sysconfdir}/pulp/repo_auth.conf
%attr(3775, root, root) %{_sysconfdir}/pki/content
%attr(775, root, root) %{_sysconfdir}/rc.d/init.d/pulp-cds
%attr(3775, apache, apache) /var/lib/pulp-cds
%attr(3775, apache, apache) /var/lib/pulp-cds/repos
%attr(3775, apache, apache) /var/lib/pulp-cds/packages
%attr(3775, apache, apache) /var/log/pulp-cds

%if %{pulp_selinux}
%files selinux-server
%defattr(-,root,root,-)
%doc selinux/server/pulp-server.fc selinux/server/pulp-server.if selinux/server/pulp-server.te
%{_datadir}/pulp/selinux/server/*
%{_datadir}/selinux/*/pulp-server.pp
%{_datadir}/selinux/devel/include/%{moduletype}/pulp-server.if
%endif

# -- changelog ---------------------------------------------------------------

%changelog
* Wed Nov 30 2011 Jeff Ortel <jortel@redhat.com> 0.0.253-1
- Comment out API response logging in the client(s). (jortel@redhat.com)
- Pass the response to be logged back into the json module to let it format it
  nicely (jason.dobies@redhat.com)
- 758723 - removed pulp-client-lib's dependency on pulp-consumer by adding
  response configuration to admin.conf (skarmark@redhat.com)
- Added logging to better indicate why HTTP error codes are being returned
  (jason.dobies@redhat.com)
- Cleaned up pulp.spec and removed older commented out selinux lines
  (jmatthews@redhat.com)
- Cloning Improvements * fix the content duplication by reusing the real link
  from source repo * fix the distribution clone to account for the relativepath
  and sub directories and use real path * fix package imports during clone to
  lookup package from pulp instead of trying to create and lookup * unit tests
  to validate clone calls these changes should considerably enhance the cloning
  performance and resolve duplication issues (pkilambi@redhat.com)
- Updated the publish conduit and added unit tests (jason.dobies@redhat.com)
- Added slow sync simulation script (jason.dobies@redhat.com)
- Added usage of the importer scratchpad (jason.dobies@redhat.com)
- All conduit calls should return a wrapped exception (jason.dobies@redhat.com)
- SELinux rewrite: creating separate rpm pulp-server-selinux
  (jmatthews@redhat.com)
- SELinux rewrite: developer setup script (jmatthews@redhat.com)
- SELinux rewrite: Update pulp.spec to call enable.sh (jmatthews@redhat.com)
- SELinux cleanup of .te rules and fix for getattr on pulp-migrate
  (jmatthews@redhat.com)
- SELinux rules: cleaning up unused type (jmatthews@redhat.com)
- SELinux rewrite: allow httpd to unlink log files for logrotate functionality
  (jmatthews@redhat.com)
- SELinux rewrite: update pulp_certs_t rule to allow basic file permissions for
  git checkout (jmatthews@redhat.com)
- SELinux rewrite: repo delete working (jmatthews@redhat.com)
- SELinux rewrite: pulp-admin auth login & repo list are working
  (jmatthews@redhat.com)
- Rewriting SELinux rules:  rules allow httpd restart (jmatthews@redhat.com)
- Added functionality to log api request and response details when running cli
  so it can be added to api documentation (skarmark@redhat.com)
- Added support for removing units in the harness importer
  (jason.dobies@redhat.com)
- Added call to show sync history (jason.dobies@redhat.com)
- Fixing broken rhel5 tests because of fix for 756132 (skarmark@redhat.com)
- Added in a default script and call timing support (jason.dobies@redhat.com)
- First pass at harness for running plugin commands (jason.dobies@redhat.com)
- Removed ability to use numbers in type IDs (messes up mongo)
  (jason.dobies@redhat.com)
- 756132 - Fixed traceback when deleting a filter (skarmark@redhat.com)
- Updated test (forgot I had one that tested numbers) (jason.dobies@redhat.com)
- First pass at v2 live server test harness (jason.dobies@redhat.com)
- Add cloned repo ids to the list on associated distributions.
  (jslagle@redhat.com)

* Mon Nov 28 2011 Jeff Ortel <jortel@redhat.com> 0.0.252-1
- Automatic commit of package [python-oauth2] minor release [1.5.170-2.pulp].
  (jmatthews@redhat.com)
- Automatic commit of package [python-isodate] minor release [0.4.4-3.pulp].
  (jmatthews@redhat.com)
- removed old sources (jconnor@redhat.com)
- 747336 Change filter parameter from id to repoid for consistency
  (jslagle@redhat.com)
- Clean up usage of singular/plural for bulk apis for consistency
  (jslagle@redhat.com)
- 747336 Add bulk API for repository sync history. (jslagle@redhat.com)
- Remove the expectation that log in a report will be a string; no reason the
  plugin can't serialize anything they want in there (jason.dobies@redhat.com)
- Renamed plugin "data" module to "model" (jason.dobies@redhat.com)
- Fixed bug in retrieving the unit ID (jason.dobies@redhat.com)
- 747336 Add a list of repoids to the distribution model (jslagle@redhat.com)
- First draft at new repo sync conduit APIs (jason.dobies@redhat.com)
- Progress on new conduit APIs (jason.dobies@redhat.com)
- Renamed exceptions module (jason.dobies@redhat.com)
- Added get_units call to the unit association manager
  (jason.dobies@redhat.com)
- 747336 Add tests. (jslagle@redhat.com)
- 747336 Add GET handler for /statuses and fix the way task search was working
  (jslagle@redhat.com)
- Fix initialization of items_remaining->items_left (jslagle@redhat.com)
- 747336 Add rollup call for repository sync status and bulk call for sync
  status (jslagle@redhat.com)
- updated for latest isodate and oauth2 modules (jconnor@redhat.com)
- 755625 - Non-existent filter now replies with a 404 (skarmark@redhat.com)
- latest oauth2 with patch (jconnor@redhat.com)
- Raise AMQP events when repo sync task dequeued. (jortel@redhat.com)
- changing the distro cli proxy to use new rest path (pkilambi@redhat.com)
- Wired up distributor history REST APIs (jason.dobies@redhat.com)
- Added publish history tracking and manager-level retrieval calls
  (jason.dobies@redhat.com)
- curl example for using clone API (jmatthews@redhat.com)
* Fri Nov 18 2011 Jeff Ortel <jortel@redhat.com> 0.0.251-1
- 754807 - Added filter application step when importing packages as it is now
  separated from fetch_content while syncing a local repository
  (skarmark@redhat.com)
- Added sync history retrieval to manager layer (jason.dobies@redhat.com)
- updatinf functional test to get filename from pkg object
  (pkilambi@redhat.com)
- Added sync history tracking (jason.dobies@redhat.com)

* Fri Nov 18 2011 Jeff Ortel <jortel@redhat.com> 0.0.250-1
- fixing the clones to use the checksum value from source metadata and not
  recompute checksum (pkilambi@redhat.com)
- 754809 - Added validation for trying to add filters when cloning a repo with
  origin feed (skarmark@redhat.com)
- 754743 - added validation for feed when cloning a repository
  (skarmark@redhat.com)
- Brought publish manager up to speed with new APIs (jason.dobies@redhat.com)
- Refactored out sync manager exceptions to common module
  (jason.dobies@redhat.com)
- Brought sync manager up to speed with new plugin APIs
  (jason.dobies@redhat.com)
- Finished distributor-related unit tests (jason.dobies@redhat.com)
- Renamed "auto_distribute" to "auto_publish" (jason.dobies@redhat.com)
- Adding distributor unit tests (jason.dobies@redhat.com)
- Enforcing relativepath to be unique in pulp's repo collection * Db and
  migration to ensure unique index. If there are pre existing documents with
  non unique paths, we drop all except one. * APi changes to handle duplicate
  error * unit test updates (pkilambi@redhat.com)
- The application setup is a bit costly, so reduce it to once per class instead
  of each test itself. (jason.dobies@redhat.com)
- The application setup is a bit costly, so reduce it to once per class instead
  of each test itself. (jason.dobies@redhat.com)
- Initial work on repo controller test (jason.dobies@redhat.com)
- Changed importer create to return the importer (jason.dobies@redhat.com)
- Changed update repo to return the newly updated repo
  (jason.dobies@redhat.com)
- Added resource-level GET for single repo retrieval (jason.dobies@redhat.com)
- Added web service controller test base class (jason.dobies@redhat.com)
- Wired up GET on importer/distributors (jason.dobies@redhat.com)
- Added both resource and sub-collection style APIs for get_importer*
  (jason.dobies@redhat.com)
- Added get_distributor and get_distributors funcitonality
  (jason.dobies@redhat.com)
- Implemented get_importer call (jason.dobies@redhat.com)
- Refactored out all repo manager exceptions to reduce coupling
  (jason.dobies@redhat.com)
- Flushed out repo distributor REST APIs with proper error codes
  (jason.dobies@redhat.com)
- Put this return in the wrong module. Need. More. Coffee.
  (jason.dobies@redhat.com)
- Added a second mock distributor plugin to the mix (jason.dobies@redhat.com)
- Flushed out REST APIs for repo and importer calls. (jason.dobies@redhat.com)
- Changed behavior of repo delete to error if the ID is invalid
  (jason.dobies@redhat.com)
- Progress towards repo v2 REST API clean up (jason.dobies@redhat.com)
- Added more checks to ensure the right values are passed to the plugins
  (jason.dobies@redhat.com)
- Flushed out repo distributor unit tests (jason.dobies@redhat.com)
- Flushed out repo importer manager unit tests (jason.dobies@redhat.com)
- Added update repo unit tests (jason.dobies@redhat.com)
- Refactored out distributor manager unit tests (jason.dobies@redhat.com)
- Refactored out importer manager tests into its own test case
  (jason.dobies@redhat.com)
- Refactored out the MissingRepo exception to common (jason.dobies@redhat.com)
- Refactored importer and distributor handling from the repo manager because
  the module was getting entirely too long. Still haven't updated the unit
  tests which at this point are so incorrect it's almost comical.
  (jason.dobies@redhat.com)
- Added common functions module to repo managers (jason.dobies@redhat.com)
- Flushed out repo delete with calls to clean up plugins and delete the working
  directory (jason.dobies@redhat.com)
- Flushed out distributor lifecycle APIs and added docs
  (jason.dobies@redhat.com)
- Encapsulated unit data into a transfer object (jason.dobies@redhat.com)
- Added module for plugin transfer objects (jason.dobies@redhat.com)
- Added config wrapper to simplify plugin APIs by doing the heavy lifting of
  config location resolution (jason.dobies@redhat.com)

* Wed Nov 16 2011 Jeff Ortel <jortel@redhat.com> 0.0.249-1
- Add support in REST/manager layers for package update. (jortel@redhat.com)
- Params needs to be empty not None (jason.dobies@redhat.com)
- added get access to last_sync to prevent key error: no idea why its not
  getting initialized (jconnor@redhat.com)
- using utc timezone for timestamps instead of local (jconnor@redhat.com)
- standardized our api sync calls on skip instead of skip_dict
  (jconnor@redhat.com)
- 752961 - Add Packages.update() support in the agent. (jortel@redhat.com)
- Add jobs REST API page. (jortel@redhat.com)
- 750580 - Adding eval on client side so that api can accept list instead of
  str(list) (skarmark@redhat.com)
- 750580 - RFE made search packages filterable by repositories
  (skarmark@redhat.com)
- Add job cancel. (jortel@redhat.com)
- Added convention for the plugin writer to be able to define their own plugin
  base class that is itself a subclass of our plugin classes.
  (jason.dobies@redhat.com)
- Fixed bug that prevented multiple importer/distributor classes to be defined
  in the same plugin. (jason.dobies@redhat.com)
- minor change in get_consumers_applicable_errata api and added extra comments
  (skarmark@redhat.com)
- Adding support for updating checksum type for a repository
  (pkilambi@redhat.com)
- Moved SElinux build/install steps from RPM to separate scripts
  (jmatthews@redhat.com)
- 751836 - inform user to use job command when trying group status
  (pkilambi@redhat.com)
- 752791, 749526 - changing the distribution api to be plural /distributions/
  consistant with others. Also fix the return code to be a 404 if the
  distribution is not found (pkilambi@redhat.com)
- Adding ability to apply filter to manually uploaded content, Changed return
  types of repository add_package api and cli changes to display a summary of
  associates packages with filtered package count (skarmark@redhat.com)
- scheduling package and scheduler module (jconnor@redhat.com)

* Fri Nov 11 2011 Jeff Ortel <jortel@redhat.com> 0.0.248-1
- disregard reboot in agent when no packages installed. (jortel@redhat.com)
- Adjust for rhel5 not being able to sync f16 metadata unless it uses
  --compress-type bz2 (jmatthews@redhat.com)
- bumping grinder version to 0.0.128 (pkilambi@redhat.com)
- exposing distribution arch info from cli (pkilambi@redhat.com)
- Updated agent Packages.install() API; replaced 'assumeyes' w/ 'importkeys'
  for clarity. (jortel@redhat.com)
- 735091 - Added SYSTEMCTL_SKIP_REDIRECT=1 to mitigate systemd issues.
  (jortel@redhat.com)
- fixing the repo distribution associate to include subdirectories while
  symlinking (pkilambi@redhat.com)
- fix the symlink path to include subdirectories from distro location in local
  syncs (pkilambi@redhat.com)
- Distribution Enahncements * Adding new arch field to distribution model +
  migration * sync and api changes * unit tests updates * changing ditro url to
  be http (pkilambi@redhat.com)
- Adding total size in MB to pulp repo sync CLI output (jmatthews@redhat.com)

* Wed Nov 09 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.247-1
- 752187 - use the newest task when showing the metadata status
  (pkilambi@redhat.com)
- 752195 - dont need to check preserver flag during associations. This is needs
  to continue even when preserve metadata is set. (pkilambi@redhat.com)
- 751460 using _id instead (jconnor@redhat.com)
- started on oauth support in pic (jconnor@redhat.com)
- simplifying return of _skip_dict (jconnor@redhat.com)
- website index for CR18. (jortel@redhat.com)
- Fixed incorrect docs (jason.dobies@redhat.com)
- updating grinder version (pkilambi@redhat.com)
- Added return codes where missing in this API (jason.dobies@redhat.com)
- relaxing requirement and validation on consumer group description
  (jconnor@redhat.com)
- re-ran doc generation (jconnor@redhat.com)
- fixed wiki doc processing macro that was causing wiki docs to not get
  generated for repo sync history (jconnor@redhat.com)
- fixed bug that could cause notes to be None (jconnor@redhat.com)
- adding checksum type to packageinfo object during uploads
  (pkilambi@redhat.com)
- The /v2 REST discovery URL is breaking all of the /v2 URLs.
  (jason.dobies@redhat.com)
- Add gofer plugin requires: package to ensure proper plugin loading order.
  (jortel@redhat.com)
- 745751 - use relativepath when constructing download urls for repo packages
  (pkilambi@redhat.com)
- Refit pulpplugin to leverage gofer-package. (jortel@redhat.com)
- no need to generate updateinfo.xml if metadata is preserved
  (pkilambi@redhat.com)

* Wed Nov 02 2011 Jeff Ortel <jortel@redhat.com> 0.0.246-1
- 750913,750915 - Fix CLI package uninstall help and error messages.
  (jortel@redhat.com)
- Bump grinder to 0.126 (jmatthews@redhat.com)
- updating file synchronizer to match new grinder changes (pkilambi@redhat.com)
- bug specifying interval without start time always results in error
  (jconnor@redhat.com)
- Automatic commit of package [pulp] release [0.0.245-1]. (jslagle@redhat.com)
- Update requires on mod_wsgi (jslagle@redhat.com)
- updating the docs for dependency resolver call and exposing make_tree option
  (pkilambi@redhat.com)
- adding distribution selective sync calls to bash completion script
  (pkilambi@redhat.com)
- 741635 - Errata summary enhancement for katello dashboard
  (skarmark@redhat.com)
- fixing ISE for repo update and delete notes (skarmark@redhat.com)

* Mon Oct 31 2011 James Slagle <jslagle@redhat.com> 0.0.245-1
- Update requires on mod_wsgi (jslagle@redhat.com)
- 747026 - When removing a CDS/repo association, remove the association
  document if no more CDSes are assigned for the given repo.
  (jason.dobies@redhat.com)
- adding repo notes cli and symlink changes to bash completion script
  (skarmark@redhat.com)

* Fri Oct 28 2011 Jeff Ortel <jortel@redhat.com> 0.0.244-1
- Requires gofer 0.54. (jortel@redhat.com)
- 734126 - make consumer certificate path configurable. (jortel@redhat.com)
- fixed bug when specifying --runs for a schedule (jconnor@redhat.com)
- 749821 waaaaaay nicer output formatting of repo schedule (jconnor@redhat.com)
- 749821 only returning skip dict if it is non-empty (jconnor@redhat.com)
- 744587 - removed use_symlinks flag from db and symlinks flag from pulp api
  and cli (skarmark@redhat.com)
- 747094 - fixing the task polling on discovery to report num of url. Also
  uniquify the discovery task by url to avoid task conflicts
  (pkilambi@redhat.com)
- 749811 added content_types to the fields fetched from the database
  (jconnor@redhat.com)
- 735159 - post run script in the rpm raising error on uninstall
  (jmatthews@redhat.com)
- 743372 - Fixed origin feed syncing from origin at the clone time instead of
  parent (skarmark@redhat.com)
- add a noop update method to file synchronizer (pkilambi@redhat.com)
- 712496 - adding server-side check for existence of user (jconnor@redhat.com)
- adding check for existing user before attempting update (jconnor@redhat.com)
- added db version 27 to fix 26 mistake (jconnor@redhat.com)
- 742240 Change our config files to %config(noreplace) in the spec file.
  (jslagle@redhat.com)
- Sync Enhancements for #744021, #749289 * import the pkg and file information
  before metadata is regenerated * modify the checksum to use the pkg checksum
  from metadata * rewrote local sync metadata to import all the metadata under
  repodata * new method call update_metadata to regenerate metadata if
  preserve_metadata is set (pkilambi@redhat.com)
- 743713 - Wrong error message when running packagegroup install without
  consumerid/consumergroupid (jmatthews@redhat.com)
* Thu Oct 27 2011 Jeff Ortel <jortel@redhat.com> 0.0.243-1
- 747725 Strip off initial and trailing slash from OID url.  Some content certs
  may have them where others do not. (jslagle@redhat.com)
- Fix macro changes for x86_64. (jortel@redhat.com)
- re-vamped titles to schedule rest api (jconnor@redhat.com)
- re-worked limit <-> max_speed hack (jconnor@redhat.com)
- added error: prefix to system_exit when code not == os.EX_OK
  (jconnor@redhat.com)
- limit option maps to max_speed argument (jconnor@redhat.com)
- forgot to remove options when removing sync schedule (jconnor@redhat.com)
- needed to add sync_options to default fields as well (jconnor@redhat.com)
- adding db version 26 that adds sync_options field to Repo model
  (jconnor@redhat.com)
- re-added sync_schedule into default fields as create and update were not the
  only commands using it (jconnor@redhat.com)
- setting sync options in db and using them in scheduled sync updates
  (jconnor@redhat.com)
- added sync_options to the Repo model (jconnor@redhat.com)
- added --skip and --no-skip options to build skip_dict (jconnor@redhat.com)
- more thorough error reporting for iso8601 parsing (jconnor@redhat.com)
- adding some output to schedule change (jconnor@redhat.com)
- fetching source field for repo as it is needed to change the sync schedule
  (jconnor@redhat.com)
- removed sync_schedule from repo create (jconnor@redhat.com)
- renamed controller classes according to own standards :P (jconnor@redhat.com)
- removed sync_schedule from default fields (jconnor@redhat.com)
- moved repo sync logic out of repo update and into repo schedule
  (jconnor@redhat.com)
- added sync schedule methods to RepositoryAPI (jconnor@redhat.com)
- changed db update of repo sync_schedule field to use atomic $set operation
  instead of save (jconnor@redhat.com)
- added schedules sub-collection for repo sync schedule management
  (jconnor@redhat.com)
- removed schedule changes from repo update and create (jconnor@redhat.com)
* Wed Oct 26 2011 Jeff Ortel <jortel@redhat.com> 0.0.242-1
- 672569 - Changed hard coded directories to macros to appease rpmlint
  (jason.dobies@redhat.com)
- 749230 - validate local treeinfo checksum before copying
  (pkilambi@redhat.com)
- 690902 - Since the sync runs in an async task, we need to add a check for
  hostname validity before triggering the task so we can inform the caller that
  the invocation was invalid (jason.dobies@redhat.com)
- 745561 - fixing race condition of resource permission creation
  (jconnor@redhat.com)
- 748889 - fixing expection text to be consistant (pkilambi@redhat.com)
- 748944 - changing the remove distro to unassociate and orphan the distro and
  delete from filesystem if associated repo is deleted (pkilambi@redhat.com)
- 688983 - Call to unassociate each repo from a CDS before unregistering it so
  that all of the unassociate steps take place (jason.dobies@redhat.com)
- 688631 - Change handling of CDS errors to raise up to the normal CLI
  handling, only reminding the user about the CDS packages and service in the
  process (jason.dobies@redhat.com)
- 688288 - For a conflict, give the user a custom error message
  (jason.dobies@redhat.com)
- Renaming RepoNotesAdd and RepoNotesUpdateDelete to RepoNotesCollection and
  RepoNotes (skarmark@redhat.com)
- 712523 - Split missing auth into its own exception (previously it was bundled
  in with server-side errors). Changed the CDS register code to only catch
  server exceptions and let the auth ones bubble up. (jason.dobies@redhat.com)
- 747725 Fix regular expression during oid validation and add a test that uses
  wildcard oid urls (jslagle@redhat.com)
- 674651 - Added translation layer between grinder programmatic keys and user-
  friendly text (jason.dobies@redhat.com)
- Bump grinder to 0.122 (jmatthews@redhat.com)
- Load test config prior to webservices.application init Fixes problem with
  permission denied on log dir if run as non root (jmatthews@redhat.com)
- Update playpen script for displaying memory usage (jmatthews@redhat.com)
- Update since grinder no longer has a yum lock (jmatthews@redhat.com)
- fixing broken errata list --repoid with type filter (skarmark@redhat.com)
- 748324 - Fixed pulp-admin errata list not checking for non-existing consumer
  (skarmark@redhat.com)
- 748324 - Fixed pulp-admin errata list not checking for non-existing consumer
  (skarmark@redhat.com)

* Fri Oct 21 2011 Jeff Ortel <jortel@redhat.com> 0.0.241-1
- wrapping group export into a task job. * Adding client side changes to
  support group exports * adding a status flag to check status for background
  exports * adding a --foreground flag to invoke export and default to bg by
  default (pkilambi@redhat.com)
- fixing the rapi.errata usage to lookup id (pkilambi@redhat.com)
- supporting multiple queries params (pkilambi@redhat.com)
- Exposing severity as a filter on errata at repo api level
  (pkilambi@redhat.com)
- fixing logic to skip distros if there is no images dir. (pkilambi@redhat.com)
- Remove setgid root and sticky bit from our init scripts (jslagle@redhat.com)
- 727311 Unbind a consumer from all its repos before deleting it.
  (jslagle@redhat.com)
- 747283 - added missing auth_required decorator for delete_filter api
  (skarmark@redhat.com)
- 747151 - Added api and cli to add, update and delete a key-value pair to
  repository notes along with wiki documentation for api and unit tests
  (skarmark@redhat.com)

* Wed Oct 19 2011 Jeff Ortel <jortel@redhat.com> 0.0.240-1
- Adding new web service calls in services handler to export repo and repo
  groups (pkilambi@redhat.com)
- Add: package & group uninstall CLI; fix associated bugs in flow.
  (jortel@redhat.com)
- Add package & group uninstall in WS layer. (jortel@redhat.com)
- Add package & group uninstall in API (manager) layer. (jortel@redhat.com)
- Update agent mocks w/ package & group uninstall(). (jortel@redhat.com)
- adding more filters to errata lookup (pkilambi@redhat.com)
- Adding a warning message to pulp-migrate to validate repo relativepaths and
  warn user to remove repos (pkilambi@redhat.com)
- Update the version of mod_wsgi that pulp requires (jslagle@redhat.com)
- Add patch for mod_wsgi to stop KeyError exception on python interpreter
  shutdown in apache (jslagle@redhat.com)
- fixing help on distro add/remove (pkilambi@redhat.com)
- Add package, package group uninstall in agent. (jortel@redhat.com)
- fixing auto populated timestamp to match iso8601 format (pkilambi@redhat.com)
-  Distribution enhancements (contd): * adding a timestamp field to
  distribution model * logic to parse timestamp from treeinfo if none use
  current time * change relativepath to be path of the distro * changing the
  distro url to use repo relativepath and show multiple urls on clients * unit
  test updates (pkilambi@redhat.com)
- Added automatic permissions for tasks (jconnor@redhat.com)
- changed grant/revoke funtors so that they are now picklable
  (jconnor@redhat.com)
- changed dispatcher loop so that dispatcher does not exit (jconnor@redhat.com)
- 746726 - fix the errata imports during syncs to account for severity and
  other fields (pkilambi@redhat.com)
- 669422 - Fixed repo sync not validating timeout input after recent isodate
  changes. Also added validation for repo clone timeout and fixed a typo
  (skarmark@redhat.com)
- Distribution Enhancements: * Store distributions in a central location and
  associate to repos(requires new grinder) * updating yum syncs to use new
  storage path and pass it to grinder * rewriting local syncs to copy ks files
  to new location and link to repo paths * adding new selective sync calls to
  add and remove distributions * webservices and  cli changes and unittest
  updates (pkilambi@redhat.com)
* Fri Oct 14 2011 Jeff Ortel <jortel@redhat.com> 0.0.239-1
- added granting and revoking of tasks in async.enque do not circumvent
  async.enqueue or async.run_async if you want the permissions to be
  dynamically adjusted (jconnor@redhat.com)
- added add/remove hooks test (jconnor@redhat.com)
- added grant and remove functors for task resource permissions
  (jconnor@redhat.com)
- added hooks to pickled fields (jconnor@redhat.com)
- added execution of task hooks into task queue (jconnor@redhat.com)
- added general hooks and enque/deque hook management (jconnor@redhat.com)
- move the repo.updated event raise to generate_metadata call. thats when the
  repo is truly considered updated (pkilambi@redhat.com)

* Wed Oct 12 2011 Jeff Ortel <jortel@redhat.com> 0.0.238-1
- 740628 - using new task weights to keep AsyncTask instances from plugging up
  tasking with tasks that are not actually running on the server
  (jconnor@redhat.com)
- weighted task - using new task weights to determine the number of tasks that
  can execute concurrently instead of simply a number of tastks, see wiki for
  details (jconnor@redhat.com)
- adding drpm support to exports (pkilambi@redhat.com)
- CR17 UG and REST API changes. (jortel@redhat.com)
- changing the manifest name to match cdn (pkilambi@redhat.com)
- 743416 for scheduled syncs, using last_sync as the start_time if no
  start_time is provided (jconnor@redhat.com)
- 740300 changed search criteris to more accurately idenitfy which task to
  cancel (jconnor@redhat.com)
- 740083 added check for months or years in the timeout for clone
  (jconnor@redhat.com)
- 705410 - added conversion of ValueErrors from isodata to isdate.ISO8601Error
  instances, which the command line handles (jconnor@redhat.com)
- invoke repodata generation when content is uploaded and associated to a repo
  (pkilambi@redhat.com)
- Remove unused, unauthenticated invocation of shell commands as root.
  (jortel@redhat.com)
- 744206 - removed password field from all returned user instances
  (jconnor@redhat.com)
- if repo metadata is set to be preserved, do not generate initial metadata.
  Also including a unit test (pkilambi@redhat.com)
- 734782 - DuplicateKeyError: E11000 duplicate key error index (from import
  package) Adding retry logic to work around an infrequent timing issue seen
  with mongoDB (jmatthews@redhat.com)
- Add memory usage info to grinder script under playpen (jmatthews@redhat.com)
- Update playpen script for standalone memory leak reproducer
  (jmatthews@redhat.com)
- Script to sync a list of repos in a standalone mode, Pulp runs outside of
  Apache (jmatthews@redhat.com)
- grouping files into a directory (jconnor@redhat.com)
- added some pictures (jconnor@redhat.com)
- added more dividers (jconnor@redhat.com)
- finished first pass at coordinator write up (jconnor@redhat.com)
- 722543 - adding checks to see if consumer exists before registering a new
  one, user needs to unregister existing consumer before registering
  (pkilambi@redhat.com)
- patch from jlaska to remove bootstrap from the rpm spec (jconnor@redhat.com)
- added a root level collection discovery for the v2 rest api
  (jconnor@redhat.com)
- Add pulp-admin bash completion script (jslagle@redhat.com)
- tried to remove autoloading of configuration, but tests too reliant on the
  behavior (jconnor@redhat.com)
- no longer using bootstrap.wsgi, removeing (jconnor@redhat.com)
- 743413 - moved all of pulp initialization into application module and pointed
  wsgiimportscript to webservices.wsgi (jconnor@redhat.com)
- 738657 - changing add/remove operations to not invoke createrepo and let
  users call generate_metadata (pkilambi@redhat.com)
- exposing preserve metadata info on the client (pkilambi@redhat.com)
- 743185 - if variant/family or version is not part of treeinfo, defaults to
  None with a message in the log (pkilambi@redhat.com)
- added error handling wsgi middleware to application stack removed error
  handler decorator from v2 content rest api (jconnor@redhat.com)
- serialization is all rest api v2, adding v1_ prefix to exceptions
  (jconnor@redhat.com)
- converted generic content content controllers to use new content and link
  serialization modules (jconnor@redhat.com)
- added db serialization module for removing/munging mongodb specific fields
  (jconnor@redhat.com)
- made link serialzation an automatic import (jconnor@redhat.com)
- adding discovery support for local filepath based yum repos
  (pkilambi@redhat.com)
- fixed uri generation for repos with feeds (jconnor@redhat.com)
- fixed repo uri path prefix (jconnor@redhat.com)
- adde repo url to output of repo list commands (jconnor@redhat.com)
- 735435 - added uri field for the repository uri in both the collection and
  individual resource (jconnor@redhat.com)
- changed httpd to utilize new constants and utility function
  (jconnor@redhat.com)
- moved timeout validation into validation package (jconnor@redhat.com)
- changed timeout validation to use new base validation error class
  (jconnor@redhat.com)
- moved common uri utilities into http module (jconnor@redhat.com)
- added validation step for linking of child types (jconnor@redhat.com)
- simplified sub uri (jconnor@redhat.com)
- 707633 - Addition of repo cancel_clone command to cancel running clone
  gracefully (skarmark@redhat.com)
- changed error handling middleware to use new error serialization
  (jconnor@redhat.com)
- new queries package with start of repo reference implementation
  (jconnor@redhat.com)
- added error serialization module (jconnor@redhat.com)
- uri and href implmentations for repo serialization (jconnor@redhat.com)
- adding content and repo serialization modules (jconnor@redhat.com)
- adding serialization and validation packages to webservices
  (jconnor@redhat.com)
- added missing exit codes (jconnor@redhat.com)
- 737180 - added check in schedules for months and years in interval without a
  start time (jconnor@redhat.com)
- 729496 - added check in sync timeouts for year and month values
  (jconnor@redhat.com)
* Fri Sep 30 2011 Jeff Ortel <jortel@redhat.com> 0.0.237-1
- Require gofer 0.50. (jortel@redhat.com)
- removing the module imports causing the coverage module to get confused and
  keeping things simple and load from a static class list (pkilambi@redhat.com)
- Requires grinder: 0.118 for API compat. (jortel@redhat.com)
- Delete associations on repo delete (jason.dobies@redhat.com)
* Thu Sep 29 2011 Jeff Ortel <jortel@redhat.com> 0.0.236-1
- first pass at all query controllers (jconnor@redhat.com)
- added type definition query (jconnor@redhat.com)
- added db query to get type definition (jconnor@redhat.com)
- placeholder module for manipulating link objects (jconnor@redhat.com)
- added some logic to avoid a failure_threshold of 0 bug (jconnor@redhat.com)
- Script to use grinder with meliae and track down memory usage
  (jmatthews@redhat.com)
- Changed to use new plugin loader APIs (jason.dobies@redhat.com)
- changed importer validation to use new metadata return (jconnor@redhat.com)
- made metadata call, insteal of direct accesst (jconnor@redhat.com)
- added ability to list content types (jconnor@redhat.com)
- added http not implemented error to responses (jconnor@redhat.com)
- adding new fields to info option (pkilambi@redhat.com)
- added associate/unassociate of child content unit(s) (jconnor@redhat.com)
- Filter repo sync tasks by repo id when fetching history (jslagle@redhat.com)

* Wed Sep 28 2011 Jeff Ortel <jortel@redhat.com> 0.0.235-1
- Fix 'release non-acquired lock' error from repo sync (jmatthews@redhat.com)
- pushed loading of metadata all the way down into _PluginMap
  (jconnor@redhat.com)
- added failsafe to improperly formatted actions dict entries
  (jconnor@redhat.com)
- mounting generic contents rest api at /contents (jconnor@redhat.com)
- mounting content units under units as the whole thing will be mounted under
  content (jconnor@redhat.com)
- skeleton generic contents module (jconnor@redhat.com)
- 740310 - added message for repo --list_keys when there are no gpg keys in the
  repository (skarmark@redhat.com)
- 733705 - Added better error handling when trying to add a filter to a file
  repo (skarmark@redhat.com)
- idea at hacking wsgi middleware start_response (jconnor@redhat.com)
- first pass at error handling middleware (jconnor@redhat.com)
- new middleware package to house wsgi middleware (jconnor@redhat.com)
- added additional base error classes (jconnor@redhat.com)
- start of new exception hierarchy (jconnor@redhat.com)
- 739099 - fixed error when displaying distribution info because of non-
  existing cds config section (skarmark@redhat.com)
- removing obsolete tests (pkilambi@redhat.com)
- fixing export loader to work on python2.4 as it doesnt support keyword
  arguments (pkilambi@redhat.com)
- removed uniqueness of types for importers and distributors changed
  get_X_by_type to return lists (jconnor@redhat.com)
- create temp export directory and clean it up after test completes
  (pkilambi@redhat.com)
- deduct items left count when done on distros and pkggrps
  (pkilambi@redhat.com)
- changed conduit creation to pass in new required managers
  (jconnor@redhat.com)
- implement get_content_units for repo_publish conduit (jconnor@redhat.com)
- added query to get content type ids for a given repo (jconnor@redhat.com)
- 736070 - Adding distribution family, variant and version info: * db changes *
  migration script * api changes * cli changes * unit test updates
  (pkilambi@redhat.com)
- Adding back DB initialize call since for some devs httpd seems to load this
  script before bootstrap (jason.dobies@redhat.com)
- moved snapshotting of task from task enqueue to task run (jconnor@redhat.com)
- Need DB reloads since the plugin may affect their state
  (jason.dobies@redhat.com)
- fixed exceptions with no message (jconnor@redhat.com)
- revamped add_or_update_content_unit to actually add or update the content
  unit (jconnor@redhat.com)
- Default inbound value for auto publish to false (jason.dobies@redhat.com)
- Make the plugin-specified relative path a little safer to work with
  (jason.dobies@redhat.com)
- Removed DB initialize (it's in bootstrap now) (jason.dobies@redhat.com)
- Added database and plugin manager initialization to bootstrap
  (jason.dobies@redhat.com)
- Integrate progress information on the client to display to the end user;
  adding cancel export support plus other fixes (pkilambi@redhat.com)
- added contents into content units root dir path (jconnor@redhat.com)
- Added call to retrieve type IDs (jason.dobies@redhat.com)
- Added temporary GC repo list web service (jason.dobies@redhat.com)
- integrate make isos to the exporter calls (pkilambi@redhat.com)
- Changed debug output to true so people can see what's happening. If it's
  false by default and they forget to pass it, then they lose the record of
  what happened on that run. If they try to run it again with debug, there's no
  guarantee the same changes will have been made. (jason.dobies@redhat.com)
- added plugin directories to developer and rpm installation
  (jconnor@redhat.com)
- changed loader to get plugin name from metadata and to fall back to the
  plugin class name if not provided (jconnor@redhat.com)
- added package detection for plugins (jconnor@redhat.com)
- added disabled plugin detection and skipping (jconnor@redhat.com)
- fixed old manager imports (jconnor@redhat.com)
- moved responsibility of config type consistency down into _load_plugin
  (jconnor@redhat.com)
- moved responsibility of config type consistency down into _load_plugin
  (jconnor@redhat.com)
- added validation checking changed all exceptions to use proper
  internatioalization practices added logging on successul load of plugins
  (jconnor@redhat.com)
- whole new implementation of plugin loader (jconnor@redhat.com)
- renamed "content manager" from plugin to loader (jconnor@redhat.com)
- moved importer and distributor plugins to plugins package
  (jconnor@redhat.com)
- making plugins package (jconnor@redhat.com)
- re-arranging content so that importers and distributors are not stored here
  and we are no longer calling it the content manger wich is confusing
  (jconnor@redhat.com)
- Fix for verify_options in cdslib (jmatthews@redhat.com)
- Adding verify_options of checksum/size for CDS sync (jmatthews@redhat.com)
- Added distributor validation of configs (jason.dobies@redhat.com)
- Updated for new importer APIs (jason.dobies@redhat.com)
- Added ability to ask the importer to validate a repo's configuration
  (jason.dobies@redhat.com)
- adding create iso to wrap exported content into cd or dvd isos
  (pkilambi@redhat.com)
* Fri Sep 23 2011 Jeff Ortel <jortel@redhat.com> 0.0.234-1
- Rename remove_old_packages to: remove_old_versions. (jortel@redhat.com)
- 740839 - adding ia64 to supported arches, also adding a unitest to validate
  all supported arches (pkilambi@redhat.com)
- Added repository storage directory for importers to use when synccing
  (jason.dobies@redhat.com)
- Del grinder object after a sync completes (jmatthews@redhat.com)
- changed the return type of get_content_unit_keys and get_content_unit_ids to
  (<tuple of ids>, <tuple of key dicts>) (jconnor@redhat.com)
- initial integration of content managers into repo sync conduit
  (jconnor@redhat.com)
* Wed Sep 21 2011 Jeff Ortel <jortel@redhat.com> 0.0.233-1
- Removing content manager init until the RPM changes are in
  (jason.dobies@redhat.com)
- if a repo has no comps, just log the message but dont treat it as an error
  (pkilambi@redhat.com)
- minor clean up on export api params (pkilambi@redhat.com)
- Adding progress callback and reporting to export task lookup and display the
  summary on client. (pkilambi@redhat.com)
- 740010 - use the checksum type when creating initial metadata
  (pkilambi@redhat.com)
- fixed bug that was causing reduce to puke when recieving an empty list
  (jconnor@redhat.com)
- fixed a bug in the re-setting of the progress callback after a snapshot
  (jconnor@redhat.com)
- Added plugin-related REST API calls (not fully tested yet)
  (jason.dobies@redhat.com)
- Added plugin manager to factory (jason.dobies@redhat.com)
- Added call to start content manager on bootstrap, though calls into it don't
  work yet (jason.dobies@redhat.com)
- Added manager-level operations for retrieving the server's plugin state
  (jason.dobies@redhat.com)
- Consolidating location of plugins (jason.dobies@redhat.com)
- moving the target path validation outside the controller sp exceptions
  propogate to ws layer (pkilambi@redhat.com)
- Added ability to retrieve all type definitions from the database
  (jason.dobies@redhat.com)
- 736140 - Add formatter to cds log handler. (jortel@redhat.com)
- Initialize the manager factory on bootstrap (jason.dobies@redhat.com)
- removed pickling of task scheduler and added immediate scheduler on re-
  creation from snapshot (jconnor@redhat.com)
- now creating snapshots for all task, not just un-scheduled ones will rely on
  conflicting task detection to resolve conflicts on startup
  (jconnor@redhat.com)

* Fri Sep 16 2011 Jeff Ortel <jortel@redhat.com> 0.0.232-1
- Added scratchpad support so importers/distributors can save information for a
  repo between runs. (jason.dobies@redhat.com)
- Config option for existing file checksum/size check (jmatthews@redhat.com)
- Added child types persistence for type definitions. (jason.dobies@redhat.com)
- Added child type support to type def parser (jason.dobies@redhat.com)

* Wed Sep 14 2011 Jeff Ortel <jortel@redhat.com> 0.0.231-1
- require gofer 0.48 for project alignment. (jortel@redhat.com)
- Removed clone ID from repo serialization (jason.dobies@redhat.com)
- Added support for tracking repo-wide metadata about its content
  (jason.dobies@redhat.com)
- Wired up bulk calls to the conduit (jason.dobies@redhat.com)
- Added bulk associate/unassociate calls (jason.dobies@redhat.com)
- Removed importer API methods we don't expect to be using
  (jason.dobies@redhat.com)
- 733508 - replaced old logic with new one to detect if sync for parent repo is
  in progress before starting repo clone (skarmark@redhat.com)
-  exporter changes: * export api to invoke repo exports in an async task * web
  services calls to expose export calls * client proxy updates * cli changes to
  support pulp-admin repo export (pkilambi@redhat.com)
- Fix unit test mocks for Consumer.deleted() renamed to Consumer.unregistered.
  (jortel@redhat.com)
- First pass at GC repo APIs (jason.dobies@redhat.com)
- 737531 - close YumRepository after getting package lists. (jortel@redhat.com)
- Flushed out manager retrieval methods and added unit tests for them.
  (jason.dobies@redhat.com)
- Added removal of importers/distributors on a repo delete
  (jason.dobies@redhat.com)
- adding progress callback to exporter modules (pkilambi@redhat.com)
- Added last_publish call to publish manager and conduit
  (jason.dobies@redhat.com)
- Added last_publish query (jason.dobies@redhat.com)
- Added the distributor ID to the conduit for tracking
  (jason.dobies@redhat.com)
- Updated publish conduit with results from design discussion
  (jason.dobies@redhat.com)
- Changed APIs to use IDs instead of keys (jason.dobies@redhat.com)
- Removed queries; these will live in the query manager
  (jason.dobies@redhat.com)
- Hooked up auto-publish to the end of repo sync (jason.dobies@redhat.com)
- cleaning up obsolete logic in exporter to fix server side api
  (pkilambi@redhat.com)
- added better error reporting for services using timeout wrapper
  (jconnor@redhat.com)
- 729496 - added timeout validation wrapper on the server side that disallows
  intervals containing months and years (jconnor@redhat.com)
- Implemented auto distributor publish logic (jason.dobies@redhat.com)
- renamed model fields: unique_indicies to unique_indices and other_indicies to
  search_indices (jconnor@redhat.com)
- 733716 - fixing add_package to lookup dependency list correctly
  (pkilambi@redhat.com)
- Changed spelling of "indices" to match what's in base
  (jason.dobies@redhat.com)
- Implementation of repo publish (jason.dobies@redhat.com)
- removing obsolete script from setup.py (pkilambi@redhat.com)
- removing obsolete export client (pkilambi@redhat.com)
- 714253 - Added safety in case the erratum being checked isn't there.
  (jason.dobies@redhat.com)
- 736855 - invoke agent (RMI) Consumer.unregistered() before consumer is
  deleted. (jortel@redhat.com)
- 733756 - Corrected capitalization (jason.dobies@redhat.com)
- 735393 - pulp package search via api fails with error (and solution isn't
  documented) (jmatthews@redhat.com)
- 728568 - We are modifying repo metadata of type 'group' and storing a gzipped
  file, instead of a plaintext file. (jmatthews@redhat.com)
- 735433 - Added similar fix for file based syncs as well (skarmark@redhat.com)
- 735433 - Added fix for cloning through API with relative_path not placing
  RPMs into the relative_path dir and added cli option for specifying
  relative_path while cloning (skarmark@redhat.com)
- Relax perms on (task) web services. (jortel@redhat.com)
- refactored query methods and exceptions out into their own modules
  (jconnor@redhat.com)
- make sure to sync treeinfo for distributions when doing alocal sync
  (pkilambi@redhat.com)
- Adding plugin priority to load modules in a priority sequence
  (pkilambi@redhat.com)
- use distro files for count (pkilambi@redhat.com)
- Updating exporter report with message (pkilambi@redhat.com)
- Tracking error in the progress report to inform user (pkilambi@redhat.com)
- Adding some progress reporting to exporter (pkilambi@redhat.com)
- Exporter: Adding custom metadata export support and some minor clean up
  (pkilambi@redhat.com)
- fixing yum plugin to use new consumerconfig (pkilambi@redhat.com)
- fixing pulp profile plugin that was broken with client refactor
  (pkilambi@redhat.com)
- Exporter: lookup plugins by glob; adding some more doc strings
  (pkilambi@redhat.com)
- Exporter: Adding more validation around target directory
  (pkilambi@redhat.com)
- Exporter: *  pulp-exporter wrapper to invoke the command * minor clean up and
  adding some docs (pkilambi@redhat.com)
- moving the modules to plugin dir and auto load the plugins
  (pkilambi@redhat.com)
-  Exporter: * Support for package group and category exports * adding some
  basic progress info (pkilambi@redhat.com)
-  Exporter: * Add a cli module to glue other exporter types * add errata
  package processing * add logging support to log export info to exporter.log
  (pkilambi@redhat.com)
- Exporter: * distribution export support * integration test script * minor
  clean up (pkilambi@redhat.com)
- Exporter: * Errata export support * enhance generate updateinfo for exporter
  (pkilambi@redhat.com)
* Fri Sep 02 2011 Jeff Ortel <jortel@redhat.com> 0.0.230-1
- bump gofer to: 0.47 for project alignment. (jortel@redhat.com)
- 704194 - Fix broken repo created events. (jortel@redhat.com)
- Move pulp-migrate to main 'pulp' package. (jortel@redhat.com)
- 734839 - Fixed errata list --consumerid to work without specifying type
  (skarmark@redhat.com)
- 734449 - fixed typo in help for filters (skarmark@redhat.com)
- Ensure a sync isn't already in progress before triggering another one
  (jason.dobies@redhat.com)
- 732540 - Validate errata IDs on --consumerid install as well.
  (jortel@redhat.com)

* Wed Aug 31 2011 Jeff Ortel <jortel@redhat.com> 0.0.229-1
- Added a check in bootstrap for what version of M2Crypto we are running
  (jmatthews@redhat.com)
- pylint cleanup (jconnor@redhat.com)
- renamed hooks to conduits (jconnor@redhat.com)
- Add requires for m2crypto 0.21.1.pulp to pulp.spec (for el6 & fedora only)
  (jmatthews@redhat.com)
- WIP for M2Crypto rpm to build with tito (jmatthews@redhat.com)
- Method name change, reverted back to validate_certificate
  (jmatthews@redhat.com)
- Repo auth config file change and data for unit tests (jmatthews@redhat.com)
- Repo auth fix for running without M2Crypto patch (jmatthews@redhat.com)
- Add CRL support to repo_cert_utils (jmatthews@redhat.com)
- M2Crypto patch: Add load CRL from PEM encoded string (jmatthews@redhat.com)
- Remove 'pulp' deps on pulp-admin and pulp-consumer. (jortel@redhat.com)
- Raise descriptive exception instead of AssertionError when bundle does not
  contain both key and cert. (jortel@redhat.com)
- Remove pushd/popd from %%post script. (jortel@redhat.com)
- M2Crypto patch: updating hash value for unit test (jmatthews@redhat.com)
- M2Crypto patch: updated X509_NAME_hash to match openssl CLI calls m2crypto
  was using X509_NAME_hash_old and defining it to X509_NAME_hash, thefore
  determining the issuer hash was not matching CLI tools.
  (jmatthews@redhat.com)
- M2Crypto patch: add get_issuer() to CRL (jmatthews@redhat.com)
- make sure to sync treeinfo for distributions when doing alocal sync
  (pkilambi@redhat.com)
- Changed m2crypto CRL example script to use the installed m2crypto
  (jmatthews@redhat.com)
- Adding m2crypto 0.21.1 with patch for certificate verification against a CA
  with CRLs (jmatthews@redhat.com)
- Update of M2Crypto patch, fixed crash with verify_cert()
  (jmatthews@redhat.com)

* Fri Aug 26 2011 Jeff Ortel <jortel@redhat.com> 0.0.228-1
- Added stub managers for repo clone and query (jason.dobies@redhat.com)
- Minor documentation updates and test refactoring (jason.dobies@redhat.com)
- Added remove_distributor call and ID validation to add_distributor
  (jason.dobies@redhat.com)
- 727564 - Send global cert content instead of file names. (jortel@redhat.com)
- 733312 - modified code to compare already synced packages in a pulp repo
  against unfiltered source packages instead of filtered code packages
  (skarmark@redhat.com)
- Added importer and distributor addition calls (jason.dobies@redhat.com)
- 732540 - Validate erratum IDs on install on consumer group.
  (jortel@redhat.com)
- 732522 - replaced system_exit() with utils.system_exit(). (jortel@redhat.com)
- fixing yum plugin to use new consumerconfig (pkilambi@redhat.com)
-  fixing pulp profile plugin that was broken with client refactor
  (pkilambi@redhat.com)
- Adding an alternate usage of OpenSSL C APIs, this is closer to what we are
  attempting with M2Crypto (jmatthews@redhat.com)
* Wed Aug 24 2011 Jeff Ortel <jortel@redhat.com> 0.0.227-1
- Website updates (jslagle@redhat.com)
- 728326 - list errata consumer web services call moved to GET instead of post
  and type field is optional (skarmark@redhat.com)
- Openssl C API example for verifying a revoked certification
  (jmatthews@redhat.com)
- 731159 - Fixed repo clone not setting gpg keys correctly because of change in
  location (skarmark@redhat.com)

* Fri Aug 19 2011 Jeff Ortel <jortel@redhat.com> 0.0.226-1
- Simplified openssl conf entries for revoking a cert (jmatthews@redhat.com)
- Simplify certs scripts, specify CN as -subj CLI option and limit need for
  custom openssl.conf (jmatthews@redhat.com)
- Changed test to better reflect that the content type collection is being
  updated (jason.dobies@redhat.com)
- Added note about possible performance issue found during deep dive
  (jason.dobies@redhat.com)
- Update cert scripts for el5 & add pyOpenSSL-0.12 to allow retrieval of
  'revoked_objects' from a CRL (jmatthews@redhat.com)
- Cleanup cert creation scripts (jmatthews@redhat.com)
- renamed constants in all caps, why did I ever stop doing that?
  (jconnor@redhat.com)
- added error and log messages for distributor loading (jconnor@redhat.com)
- consolidated exceptions and utils into manager module moved utility functions
  out of Manager class that do not touch internal state (jconnor@redhat.com)
- 726194 - prune repo object sent to the agent on bind(). (jortel@redhat.com)
- Fix errata install. (jortel@redhat.com)

* Wed Aug 17 2011 Jeff Ortel <jortel@redhat.com> 0.0.225-1
- 730118 - Add BuildRequires: make for SELinux. (jortel@redhat.com)
- Fix package group, create. (jortel@redhat.com)
- Enhance job/task GET(id) to search history when not found in the queue.
  (jortel@redhat.com)
- 730752 - when comparing feeds during update use relativepath of feed and not
  the repo tself (pkilambi@redhat.com)
- Updates while investigating CRL signature mismatch (jmatthews@redhat.com)
- CRL now using 'crl_ext' to add issuer and keyIdentifier, matches CRL from
  candlepin (jmatthews@redhat.com)
- adding example crl from candlepin for reference (jmatthews@redhat.com)
- Add support for: --when, --nowait to package group & errata install.
  (jortel@redhat.com)
- Update cert generation, create ca, server, client certs
  (jmatthews@redhat.com)
- Add support for package group install on consumer group. (jortel@redhat.com)
- Added public call to retrieve the database directly (jason.dobies@redhat.com)
- Scripts to revoke a cert and generate a CRL (jmatthews@redhat.com)
- Enable repo_auth (jmatthews@redhat.com)
- Updating openssl conf so it is closer to typical default settings
  (jmatthews@redhat.com)
- remove duplicate option in config file (jmatthews@redhat.com)
- Discontinue using status_path to query task status. Remove status_path from
  WS controllers. Update client plugins to use TaskAPI.info(). Rename
  initwait() -> startwait(). Move job and task state testing functions to the
  API classes. Replace one-off task cancel, method with TaskAPI.cancel() in
  client plugins. (jortel@redhat.com)
* Fri Aug 12 2011 Jeff Ortel <jortel@redhat.com> 0.0.224-1
- Align with gofer 0.45. (jortel@redhat.com)
- Update UG for CR15. (jortel@redhat.com)
- Update website to: CR15. (jortel@redhat.com)
- 717975 - discover urls with repodata as valid urls (pkilambi@redhat.com)
- if distribution is None dont set the url (pkilambi@redhat.com)
-  Remove Metadata: * util method to support modifyrepo --remove * api changes
  to support remove_metadata call * web services remove_metadata call * cli
  changes to support pulp-admin remove_metadata * unit tests
  (pkilambi@redhat.com)
- Bump grinder to 0.110 (jmatthews@redhat.com)
- 730102 - compute the kickstart url on server when showing the distribution
  list (pkilambi@redhat.com)
- Initial implementation of the type descriptors parser. Still need to flush
  out unit tests but I want to back it up now. (jason.dobies@redhat.com)
- 729099 - fixing help text for associate operations (pkilambi@redhat.com)
- Adding make tree option to dependency resolver (pkilambi@redhat.com)
- Disable deepcopy of self.cfg for now since it's completely unsupported on
  python 2.6 (jslagle@redhat.com)
- 721321 - Don't allow pulp and pulp-cds to be installed on the same box
  (jason.dobies@redhat.com)
- 691752 - Corrected the argument name in the error text
  (jason.dobies@redhat.com)
- Adding ability to set the create flag on collection retrieval.
  (jason.dobies@redhat.com)

* Mon Aug 08 2011 Jeff Ortel <jortel@redhat.com> 0.0.223-1
- Save args as self.args so when it gets modified in setup(), the change is
  preserved (jslagle@redhat.com)
- 727906 - Added input validation and error message with a correct format for
  notes input. (skarmark@redhat.com)
* Fri Aug 05 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.222-1
- bumping grinder requires (pkilambi@redhat.com)
- fixing file sync imports (pkilambi@redhat.com)
- 728579 - Fix errata install broken during jobs migration. (jortel@redhat.com)
- fix typo (jmatthews@redhat.com)
- Cancel sync enhancements for local sync as well as interrupting createrepo
  (jmatthews@redhat.com)
- Adding ability to cancel a running createrepo process (jmatthews@redhat.com)
- 642654 fix another reference to create (jslagle@redhat.com)
- 642654 Rename consumer create/delete to register/unregister
  (jslagle@redhat.com)
- Change wording about consumer creation and don't show it if the user is
  already running consumer create (jslagle@redhat.com)
- remove unused setup_client method (jslagle@redhat.com)

* Thu Aug 04 2011 Jeff Ortel <jortel@redhat.com> 0.0.221-1
- Update client (yum) code to make idempotent. Rewrite Package.install() so
  package install will not raise TransactionError when a package is already
  installed.  Also, changed API to no longer need (or accept) package names
  explicitly parsed into name, arch for arch specific matching.
  (jortel@redhat.com)
- Fix plugin directories in the configurations (jslagle@redhat.com)

* Wed Aug 03 2011 Jeff Ortel <jortel@redhat.com> 0.0.220-1
- Enqueue package install tasks, non-unique. (jortel@redhat.com)
- renamed file manifest to match cdn (pkilambi@redhat.com)
- 727900 - file status (pkilambi@redhat.com)

* Wed Aug 03 2011 Jeff Ortel <jortel@redhat.com> 0.0.219-1
- Requires gofer 0.44. (jortel@redhat.com)
- 695607 - Fix RHEL macros.  Clean up merge artifacts in changelog.
  (jortel@redhat.com)
- Add support for asynchronous RMI timeouts using gofer 0.44 watchdog.
  (jortel@redhat.com)
- 726706 - Error in repo sync schedule error message (jmatthews@redhat.com)
- Fix syntax error in if stmt (jslagle@redhat.com)
- Only link pulp-agent to goferd init script if it doesn't exist already
  (jslagle@redhat.com)
- 727666 - fixed unpickling of private methods (jconnor@redhat.com)
- 727666 - not a fix, added instrumentation to code that raises a
  SnapshotFailure exception when the lookup of a pickled method on a class
  occurs much more informative than the UnboundLocalError that was being raised
  (jconnor@redhat.com)
- Client refactoring to support generic content. (jslagle@redhat.com)
- Require grinder .109 for quicker cancel syncs (jmatthews@redhat.com)
- Rename gofer dir to goferplugins to avoid name conflict with the installed
  gofer module (jslagle@redhat.com)
- Fix current() task management in AsyncTask. (jortel@redhat.com)
- Add missing repository_api (jslagle@redhat.com)
- Bump obsoletes version of pulp-client to 218 (jslagle@redhat.com)
- More updates for client->consumer rename (jslagle@redhat.com)
- Rename pulp-client -> pulp-consumer (jslagle@redhat.com)
- Task plugin should be disabled by default (jslagle@redhat.com)
- 723663 - minor help fixes (pkilambi@redhat.com)
- SELinux changes for pulp-cds (jmatthews@redhat.com)
- pulp.spec will only install selinux files on fedora/el6
  (jmatthews@redhat.com)
- SELinux changes for RHEL-5 (jmatthews@redhat.com)
- 726782 - added missing arch update information to delta (skarmark@redhat.com)
- Update spec file for client refactoring packaging (jslagle@redhat.com)
- Wire up consumer commands as plugins (jslagle@redhat.com)
- Remove core module (jslagle@redhat.com)
- Merge core.utils and lib.utils into a single utils module
  (jslagle@redhat.com)
- Reorginazations: client.lib.plugin_lib -> client.pluginlib and
  client.lib.plugins -> client.plugins (jslagle@redhat.com)
- Admin refactorings to support plugins, add auth as first plugin
  (jslagle@redhat.com)
- Reorganize modules amoung admin/consumer clients (jslagle@redhat.com)

* Fri Jul 29 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.218-1
- changed the name of the timeout field to timeout_delta in _pickled_fields
  (jconnor@redhat.com)
- 679764 - added cloning status, if present along with sync status under repo
  status (skarmark@redhat.com)
- 726709 - Resolved name conflict between timeout field and timeout method of
  Task class (jconnor@redhat.com)
- manifest generate support for files (pkilambi@redhat.com)

* Thu Jul 28 2011 Jeff Ortel <jortel@redhat.com> 0.0.217-1
- Fix package install. (jortel@redhat.com)

* Wed Jul 27 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.216-1
- fixed typo (jconnor@redhat.com)

* Wed Jul 27 2011 Jeff Ortel <jortel@redhat.com> 0.0.215-1
- skip tag used on rhui branch. (jortel@redhat.com)
- Bump to gofer 0.43 for project alignment. (jortel@redhat.com)
- Fix printed summary on package install on consumer group. (jortel@redhat.com)
- Add job debugging CLI command to pulp-admin. (jortel@redhat.com)
- bumping grinder version (pkilambi@redhat.com)
- 713507 - API and cli changes for RFE: querying repos by notes field
  (skarmark@redhat.com)
- adding content type to repo list output (pkilambi@redhat.com)
- Refit package install/errata on consumer group to use jobs.
  (jortel@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (skarmark@redhat.com)
- moving content_type help out of schedule area (pkilambi@redhat.com)
- added logging for duplicate importers and distributors (jconnor@redhat.com)
- added support for per-plugin toggling of importers and distributors in the
  main pulp configuration file (jconnor@redhat.com)
- Repogroup update changes This change includes changes to repo update
  consolidating all parameters of update in delta instead of calling separate
  update calls. This also includes removing symlink update from repo update and
  repogroup update, fixing repo sync schedule update as well.
  (skarmark@redhat.com)

* Fri Jul 22 2011 Jeff Ortel <jortel@redhat.com> 0.0.213-1
- Change package & packagegroup install on consumer to synchronous RMI.
  (jortel@redhat.com)
- SElinux first steps, auth login/logout, repo create/sync/delete
  (jmatthews@redhat.com)
- Added Importer and Distributor base classes (jconnor@redhat.com)
- Moving the pushcount migration from 17 to 22 to account for latest fix
  (pkilambi@redhat.com)
- Added first pass at generic content plugin manager (jconnor@redhat.com)
- Skeleton for server-side content plugins and framework (jconnor@redhat.com)
- Fixing pushcount to convert to int before storing in db (pkilambi@redhat.com)
- 714046 - fixed error message for admin user deletion (skarmark@redhat.com)
- Fixing key-value attributes api bug when creating a consumer
  (skarmark@redhat.com)

* Wed Jul 20 2011 Jeff Ortel <jortel@redhat.com> 0.0.212-1
- Add Task.job_id to support job concept in task subsystem. (jortel@redhat.com)
- Pulp synchronizer implementation to support generic content types and file
  based sync support: (pkilambi@redhat.com)
- 719651 - fixing the ldap check during authentication (pkilambi@redhat.com)
- fixing selective sync to use updated depsolver api changes
  (pkilambi@redhat.com)
- fixing consumer create to use new put call (pkilambi@redhat.com)
- fixing pulp to pass in proxy settings correctly to grinder
  (pkilambi@redhat.com)
- turning the valid filters into a tuple (jconnor@redhat.com)
- moving the GET package profile call to same class to match the url requests
  (pkilambi@redhat.com)
- Changing the package profile update from POST to PUT (pkilambi@redhat.com)

* Fri Jul 15 2011 Jeff Ortel <jortel@redhat.com> 0.0.210-1
- 722521 change --wait option to --nowait to restore previous behavior
  (jslagle@redhat.com)
- Expose Heartbeat.send() on agent as RMI for debugging.
  (jortel@redhat.com)

* Thu Jul 14 2011 Jeff Ortel <jortel@redhat.com> 0.0.209-1
- typo in conf file (jconnor@redhat.com)
- added config option to toggle auditing (jconnor@redhat.com)
- Check for None auth before trying to remove emtpy basic http authorization
  (jslagle@redhat.com)
- Switch to using append option instead of merge.  merge is not available on
  rhel 5's apache (jslagle@redhat.com)
* Thu Jul 14 2011 Jeff Ortel <jortel@redhat.com> 0.0.208-1
- Incremented to match latest RHUI version (jortel@redhat.com)

* Thu Jul 14 2011 Jeff Ortel <jortel@redhat.com> 0.0.207-1
- Fix reference to field variable (jslagle@redhat.com)
- Adding script to display mongodb file space usage statistics
  (jmatthews@redhat.com)
- Updated pulpproject.org index to fix updated Pulp BZ Category -> Community
  (tsanders@tsanders-x201.(none))
- 709500 Add a command line option --wait that can specify if the user wants to
  wait for the package install to finish or not.  If the consumer is
  unavailable, confirm the wait option (jslagle@redhat.com)
- Bump website to CR14. (jortel@redhat.com)
- 721021 remove empty Basic auth from end of authorization header if specified
  (jslagle@redhat.com)
- Changing the result datastructure to be a dictionary of {dep:[pkgs]} fit
  katello's needs (pkilambi@redhat.com)

* Tue Jul 12 2011 Jeff Ortel <jortel@redhat.com> 0.0.206-1
- removing mongo 1.7.5 restriction on pulp f15 (pkilambi@redhat.com)
* Mon Jul 11 2011 Jeff Ortel <jortel@redhat.com> 0.0.205-1
- Fix check for basic auth (jslagle@redhat.com)
- Add a header that sets a blank Basic authorization for every request, needed
  for repo auth.  Remove the blank authorization when validating from the API
  side. (jslagle@redhat.com)
- changing local syncs to account for all metadata (pkilambi@redhat.com)
- Add dist to required relase for mod_wsgi (jslagle@redhat.com)
- Add required mod_wsgi to spec file (jslagle@redhat.com)
- Automatic commit of package [mod_wsgi] minor release [3.2-3.sslpatch].
  (jslagle@redhat.com)
- check metadata preservation when add/remove on repositories
  (pkilambi@redhat.com)
- Adding checks to see if repo has metadata preserved before regenerating
  (pkilambi@redhat.com)
- 719955 - log.info is trying to print an entire repo object instead of just
  the id spamming the pulp logs during delete (pkilambi@redhat.com)
- 703878 - RFE: Exposing the unresolved dependencies  in the package dependency
  result (pkilambi@redhat.com)
- Make same repo_auth changes for pulp cds (jslagle@redhat.com)
- Update pulp.spec to install repo_auth.wsgi correctly and no longer need to
  uncomment lines for mod_python (jslagle@redhat.com)
- Move repo_auth.wsgi to /srv (jslagle@redhat.com)
- 696669 fix unit tests for oid validation updates (jslagle@redhat.com)
- 696669 move repo auth to mod_wsgi access script handler and eliminate dep on
  mod_python (jslagle@redhat.com)
- fixing help (pkilambi@redhat.com)
- fixing exit messages to refer filetype as metadata type (pkilambi@redhat.com)
- Add missing wsgi.conf file (jslagle@redhat.com)
- Automatic commit of package [pulp] release [0.0.203-1]. (jslagle@redhat.com)
- Add mod_wsgi rpm build to pulp (jslagle@redhat.com)
- 669759 - typo, missing word "is" in schedule time is in past message
  (jmatthews@redhat.com)
- converted all auditing events to use utc (jconnor@redhat.com)
- added query parametes to GET method (jconnor@redhat.com)
- using $in for union and $all for intersection operations (jconnor@redhat.com)
- added collection query decorator (jconnor@redhat.com)
- gutted decorator to simply parse the query parameter and pass in a keyword
  filters argument (jconnor@redhat.com)
- added _ prefix to common query parameters (jconnor@redhat.com)
- fix issue downloading sqlite db metadata files (pkilambi@redhat.com)
- fixing help for download metadata (pkilambi@redhat.com)
- Add a helper mock function to testutil, also keeps track of all mocks to make
  sure everything is unmocked in tearDown (jslagle@redhat.com)
- make sure run_async gets unmocked (jslagle@redhat.com)
- Incremented to match latest rhui version (jason.dobies@redhat.com)
- 718287 - Pulp is inconsistent with what it stores in relative URL, so
  changing from a startswith to a find for the protected repo retrieval.
  (jason.dobies@redhat.com)
- Move towards using mock library for now since dingus has many python 2.4
  incompatibilities (jslagle@redhat.com)
- 715071 - lowering the log level during repo delete to debug
  (pkilambi@redhat.com)
- Update createrepo login in pulp to account for custom metadata; also rename
  the backup file before running modifyrepo to preserve the mdtype
  (pkilambi@redhat.com)
- renaming metadata call to generate_metadata (pkilambi@redhat.com)
- Custom Metadata support: (pkilambi@redhat.com)
- added args to returned serialized task (jconnor@redhat.com)
- converted timestamp to utc (jconnor@redhat.com)
- Refactor __del__ into a cancel_dispatcher method that is meant to be called
  (jslagle@redhat.com)
- Pulp now uses profile module from python-rhsm and requires it
  (pkilambi@redhat.com)
- added tzinfo to start and end dates (jconnor@redhat.com)
- added task cancel command (jconnor@redhat.com)
- changed cds history query to properly deal with iso8601 timestamps
  (jconnor@redhat.com)
- Importing python-rhsm source into pulp (pkilambi@redhat.com)
- 712083 - changing the error message to warnings (pkilambi@redhat.com)
- Adding a preserve metadata as an option at repo creation time. More info
  about feature  can be found at
  https://fedorahosted.org/pulp/wiki/PreserveMetadata (pkilambi@redhat.com)
- 715504 - Apache's error_log also generating pulp log messages
  (jmatthews@redhat.com)
- replacing query_by_bz and query_by_cve functions by advanced mongo queries
  for better performance and cleaner implementation (skarmark@redhat.com)
- Bump to gofer 0.42 (just to keep projects aligned). (jortel@redhat.com)
- added some ghetto date format validation (jconnor@redhat.com)
- converting expected iso8601 date string to datetime instance
  (jconnor@redhat.com)
- added iso8601 parsing and formating methods for date (only) instances
  (jconnor@redhat.com)
- errata enhancement api and cli changes for bugzilla and cve search
  (skarmark@redhat.com)
- 713742 - patch by Chris St. Pierre fixed improper rlock instance detection in
  get state for pickling (jconnor@redhat.com)
- 714046 - added login to string substitution (jconnor@redhat.com)
- added new controller for generic task cancelation (jconnor@redhat.com)
  (jason.dobies@redhat.com)
- Move repos under /var/lib/pulp-cds/repos so we don't serve packages straight
  up (jason.dobies@redhat.com)
- Tell grinder to use a single location for package storage.
  (jason.dobies@redhat.com)
- converting timedelta to duration in order to properly format it
  (jconnor@redhat.com)
- 706953, 707986 - allow updates to modify existing schedule instead of having
  to re-specify the schedule in its entirety (jconnor@redhat.com)
- 709488 Use keyword arg for timeout value, and fix help messages for timeout
  values (jslagle@redhat.com)
- Added CDS sync history to CDS CLI API (jason.dobies@redhat.com)
- Added CLI API call for repo sync history (jason.dobies@redhat.com)
- changed scheduled task behavior to reset task states on enqueue instead of on
  run (jconnor@redhat.com)
- added conditional to avoid calling release on garbage collected lock
  (jconnor@redhat.com)
- only release the lock in the dispatcher on exit as we are no longer killing
  the thread on errors (jconnor@redhat.com)
- 691962 - repo clone should not clone files along with packages and errata
  (skarmark@redhat.com)
- adding id to repo delete error message to find culprit repo
  (skarmark@redhat.com)
- 714745 - added initial parsing call for start and end dates of cds history so
  that we convert a datetime object to local tz instead of a string
  (jconnor@redhat.com)
- 714691 - fixed type that caused params to resolve to an instance method
  instead of a local variable (jconnor@redhat.com)
- Cast itertools.chain to tuple so that it can be iterated more than once, it
  happens in both from_snapshot and to_snapshot (jslagle@redhat.com)
- 713493 - fixed auth login to relogin new credentials; will just replace
  existing user certs with new ones (pkilambi@redhat.com)
- Bump website to CR13. (jortel@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jslagle@redhat.com)
- 709500 Fix scheduling of package install using --when parameter
  (jslagle@redhat.com)
- Adding mongo 1.7.5 as a requires for f15 pulp build (pkilambi@redhat.com)
- 707295 - removed relativepath from repo update; updated feed update logic to
  check if relative path matches before allowing update (pkilambi@redhat.com)
- In a consumer case, password can be none, let it return the user
  (pkilambi@redhat.com)
- updated log config for rhel5, remove spaces from 'handlers'
  (jmatthews@redhat.com)
- Fix to work around http://bugs.python.org/issue3136 in python 2.4
  (jmatthews@redhat.com)
- Updates for Python 2.4 logging configuration file (jmatthews@redhat.com)
- Pulp logging now uses configuration file from /etc/pulp/logging
  (jmatthews@redhat.com)
- adding new createrepo as a dependency for el5 builds (pkilambi@redhat.com)
- 709514 - error message for failed errata install for consumer and
  consumergroup corrected (skarmark@redhat.com)
- Adding newer version of createrepo for pulp on el5 (pkilambi@redhat.com)
- Tell systemctl to ignore deps so that our init script works correctly on
  Fedora 15 (jslagle@redhat.com)
- 713183 - python 2.4 compat patch (pkilambi@redhat.com)
-  Patch from Chris St. Pierre <chris.a.st.pierre@gmail.com> :
  (pkilambi@redhat.com)
- 713580 - fixing wrong list.remove in blacklist filter application logic in
  repo sync (skarmark@redhat.com)
- 669520 python 2.4 compat fix (jslagle@redhat.com)
- 713176 - Changed user certificate expirations to 1 week. Consumer certificate
  expirations, while configurable, remain at the default of 10 years.
  (jason.dobies@redhat.com)
- bz# 669520 handle exception during compilation of invalid regular expression
  so that we can show the user a helpful message (jslagle@redhat.com)

* Thu Jul 07 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.204-1
- Update pulp.spec to install repo_auth.wsgi correctly and no longer need to
  uncomment lines for mod_python (jslagle@redhat.com)
- Move repo_auth.wsgi to /srv (jslagle@redhat.com)
- 696669 fix unit tests for oid validation updates (jslagle@redhat.com)
- 696669 move repo auth to mod_wsgi access script handler and eliminate dep on
  mod_python (jslagle@redhat.com)

* Thu Jul 07 2011 James Slagle <jslagle@redhat.com> 0.0.203-1
- Add mod_wsgi rpm build to pulp (jslagle@redhat.com)

* Wed Jul 06 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.202-1
- 669759 - typo, missing word "is" in schedule time is in past message
  (jmatthews@redhat.com)
- converted all auditing events to use utc (jconnor@redhat.com)
- wrong line (jconnor@redhat.com)
- added debugging log output (jconnor@redhat.com)
- bug in query params generation (jconnor@redhat.com)
- added query parametes to GET method (jconnor@redhat.com)
- using $in for union and $all for intersection operations (jconnor@redhat.com)
- stubbed out spec doc building calls (jconnor@redhat.com)
- added collectio query decorator (jconnor@redhat.com)
- gutted decorator to simply parse the query parameter and pass in a keyword
  filters argument (jconnor@redhat.com)
- added _ prefix to common query parameters (jconnor@redhat.com)
- fix issue downloading sqlite db metadata files (pkilambi@redhat.com)
- fixing help for download metadata (pkilambi@redhat.com)
- Add a helper mock function to testutil, also keeps track of all mocks to make
  sure everything is unmocked in tearDown (jslagle@redhat.com)
- make sure run_async gets unmocked (jslagle@redhat.com)
- Incremented to match latest rhui version (jason.dobies@redhat.com)
- 718287 - Pulp is inconsistent with what it stores in relative URL, so
  changing from a startswith to a find for the protected repo retrieval.
  (jason.dobies@redhat.com)
- Move towards using mock library for now since dingus has many python 2.4
  incompatibilities (jslagle@redhat.com)
- Merge branch 'master' into test-refactor (jslagle@redhat.com)
- 715071 - lowering the log level during repo delete to debug
  (pkilambi@redhat.com)
- Merge branch 'master' into test-refactor (jslagle@redhat.com)
- Add missing import (jslagle@redhat.com)
- Make import path asbsolute, so tests can be run from any directory
  (jslagle@redhat.com)
- Move needed dir from data into functional test dir (jslagle@redhat.com)
- update for testutil changes (jslagle@redhat.com)
- Update createrepo login in pulp to account for custom metadata; also rename
  the backup file before running modifyrepo to preserve the mdtype
  (pkilambi@redhat.com)
- Merge with master (jslagle@redhat.com)
- Add a test for role api (jslagle@redhat.com)
- tweaks to error handling around the client (pkilambi@redhat.com)
- Use PulpTest as base class here (jslagle@redhat.com)
- Example unit test using dingus for repo_sync.py (jslagle@redhat.com)
- Move these 2 test modules to functional tests dir (jslagle@redhat.com)
- Make each test set path to the common dir (jslagle@redhat.com)
- Move test dir cleanup to tearDown instead of clean since clean also gets
  called from setUp (jslagle@redhat.com)
- Merge with master (jslagle@redhat.com)
- Refactor all tests to use common PulpAsyncTest base class
  (jslagle@redhat.com)
- Use dingus for mocking instead of mox (jslagle@redhat.com)
- Use PulpTest instead of PulpAsyncTest for this test (jslagle@redhat.com)
- More base class refactorings, make sure tests that use PulpAsyncTest,
  shutdown the task queue correctly, this should solve our threading exception
  problems (jslagle@redhat.com)
- Refactor __del__ into a cancel_dispatcher method that is meant to be called
  (jslagle@redhat.com)
- Refactoring some of the testutil setup into a common base class to avoid
  repetition in each test module (also fixes erroneous connection to
  pulp_database) (jslagle@redhat.com)

* Fri Jul 01 2011 Jay Dobies <jason.dobies@redhat.com> 0.0.201-1
- Bringing in line with latest Pulp build version (jason.dobies@redhat.com)

* Wed Jun 29 2011 Jeff Ortel <jortel@redhat.com> 0.0.200-1
- Custom Metadata Support (Continued): (pkilambi@redhat.com)
- fixing rhel5 issues in unit tests, disabled get test until I figure out an
  alternative to dump_xml on el5 (pkilambi@redhat.com)
- Custom Metadata support: (pkilambi@redhat.com)
- Temporarily remove the quick commands section until we decide how to best
  maintain it (jason.dobies@redhat.com)

* Fri Jun 24 2011 Jeff Ortel <jortel@redhat.com> 0.0.198-1
- added args to returned serialized task (jconnor@redhat.com)
- converted timestamp to utc (jconnor@redhat.com)
- Pulp now uses profile module from python-rhsm and requires it
  (pkilambi@redhat.com)
- removed test that fails due to bug in timezone support, 716243
  (jconnor@redhat.com)
- changed tests to insert iso8601 strings as time stamps (jconnor@redhat.com)
- added task cancel command (jconnor@redhat.com)
- added wiki comments and tied cancel task to a url (jconnor@redhat.com)
- changed cds history query to properly deal with iso8601 timestamps
  (jconnor@redhat.com)
- 712083 - changing the error message to warnings (pkilambi@redhat.com)
- Incremented to pass RHUI build (jason.dobies@redhat.com)
- Adding a preserve metadata as an option at repo creation time. More info
  about feature  can be found at
  https://fedorahosted.org/pulp/wiki/PreserveMetadata (pkilambi@redhat.com)
- 715504 - Apache's error_log also generating pulp log messages
  (jmatthews@redhat.com)
- replacing query_by_bz and query_by_cve functions by advanced mongo queries
  for better performance and cleaner implementation (skarmark@redhat.com)

* Wed Jun 22 2011 Jeff Ortel <jortel@redhat.com> 0.0.196-1
- Bump to gofer 0.42 (just to keep projects aligned). (jortel@redhat.com)
- Added some ghetto date format validation (jconnor@redhat.com)
- Converting expected iso8601 date string to datetime instance
  (jconnor@redhat.com)
- added iso8601 parsing and formating methods for date (only) instances
  (jconnor@redhat.com)

* Wed Jun 22 2011 Jeff Ortel <jortel@redhat.com> 0.0.195-1
- errata enhancement api and cli changes for bugzilla and cve search
  (skarmark@redhat.com)
- 713742 - patch by Chris St. Pierre fixed improper rlock instance detection in
  get state for pickling (jconnor@redhat.com)
- 714046 - added login to string substitution (jconnor@redhat.com)
- added new controller for generic task cancelation (jconnor@redhat.com)
- Automatic commit of package [pulp] release [0.0.194-1].
  (jason.dobies@redhat.com)
- Move repos under /var/lib/pulp-cds/repos so we don't serve packages straight
  up (jason.dobies@redhat.com)
- Merged in rhui version (jason.dobies@redhat.com)
- Tell grinder to use a single location for package storage.
  (jason.dobies@redhat.com)
- converting timedelta to duration in order to properly format it
  (jconnor@redhat.com)
- 706953, 707986 - allow updates to modify existing schedule instead of having
  to re-specify the schedule in its entirety (jconnor@redhat.com)
- 709488 - Use keyword arg for timeout value, and fix help messages for timeout
  values (jslagle@redhat.com)
- Added CDS sync history to CDS CLI API (jason.dobies@redhat.com)
- Remove unneeded log.error for translate_to_utf8 (jmatthews@redhat.com)
- Added CLI API call for repo sync history (jason.dobies@redhat.com)
- changed scheduled task behavior to reset task states on enqueue instead of on
  run (jconnor@redhat.com)
- 691962 - repo clone should not clone files along with packages and errata
  (skarmark@redhat.com)
- adding id to repo delete error message to find culprit repo
  (skarmark@redhat.com)
- 714745 - added initial parsing call for start and end dates of cds history so
  that we convert a datetime object to local tz instead of a string
  (jconnor@redhat.com)
- 714691 - fixed type that caused params to resolve to an instance method
  instead of a local variable (jconnor@redhat.com)
- Cast itertools.chain to tuple so that it can be iterated more than once, it
  happens in both from_snapshot and to_snapshot (jslagle@redhat.com)
- Automatic commit of package [pulp] release [0.0.192-1]. (jortel@redhat.com)
- 713493 - fixed auth login to relogin new credentials; will just replace
  existing user certs with new ones (pkilambi@redhat.com)
- Bump website to CR13. (jortel@redhat.com)
- 709500 Fix scheduling of package install using --when parameter
  (jslagle@redhat.com)
- Automatic commit of package [pulp] release [0.0.191-1]. (jortel@redhat.com)
- Adding mongo 1.7.5 as a requires for f15 pulp build (pkilambi@redhat.com)
- 707295 - removed relativepath from repo update; updated feed update logic to
  check if relative path matches before allowing update (pkilambi@redhat.com)
- updated log config for rhel5, remove spaces from 'handlers'
  (jmatthews@redhat.com)
- Fix to work around http://bugs.python.org/issue3136 in python 2.4
  (jmatthews@redhat.com)
- Pulp logging now uses configuration file from /etc/pulp/logging
  (jmatthews@redhat.com)
- adding new createrepo as a dependency for el5 builds (pkilambi@redhat.com)
- 709514 - error message for failed errata install for consumer and
  consumergroup corrected (skarmark@redhat.com)
- Automatic commit of package [createrepo] minor release [0.9.8-3].
  (pkilambi@redhat.com)
- Adding newer version of createrepo for pulp on el5 (pkilambi@redhat.com)
- Tell systemctl to ignore deps so that our init script works correctly on
  Fedora 15 (jslagle@redhat.com)
- 713183 - python 2.4 compat patch (pkilambi@redhat.com)
-  Patch from Chris St. Pierre <chris.a.st.pierre@gmail.com> :
  (pkilambi@redhat.com)
- 713580 - fixing wrong list.remove in blacklist filter application logic in
  repo sync (skarmark@redhat.com)
- 669520 python 2.4 compat fix (jslagle@redhat.com)
- 713176 - Changed user certificate expirations to 1 week. Consumer certificate
  expirations, while configurable, remain at the default of 10 years.
  (jason.dobies@redhat.com)
- 669520 - handle exception during compilation of invalid regular expression
  so that we can show the user a helpful message (jslagle@redhat.com)

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

 Jun 17 2011 Jeff Ortel <jortel@redhat.com> 0.0.192-1
- 713493 - fixed auth login to relogin new credentials; will just replace
  existing user certs with new ones (pkilambi@redhat.com)
- Bump website to CR13. (jortel@redhat.com)
- Automatic commit of package [pulp] release [0.0.191-1]. (jortel@redhat.com)
- Changed unit test logfile to /tmp/pulp_unittests.log, avoid log file being
  deleted when unit tests run (jmatthews@redhat.com)
- Adding mongo 1.7.5 as a requires for f15 pulp build (pkilambi@redhat.com)
- 707295 - removed relativepath from repo update; updated feed update logic to
  check if relative path matches before allowing update (pkilambi@redhat.com)
- In a consumer case, password can be none, let it return the user
  (pkilambi@redhat.com)
- updated log config for rhel5, remove spaces from 'handlers'
  (jmatthews@redhat.com)
- Disable console logging for unit tests (jmatthews@redhat.com)
- Fix to work around http://bugs.python.org/issue3136 in python 2.4
  (jmatthews@redhat.com)
- Updates for Python 2.4 logging configuration file (jmatthews@redhat.com)
- Pulp logging now uses configuration file from /etc/pulp/logging
  (jmatthews@redhat.com)
- adding new createrepo as a dependency for el5 builds (pkilambi@redhat.com)
- 709514 - error message for failed errata install for consumer and
  consumergroup corrected (skarmark@redhat.com)
- Automatic commit of package [createrepo] minor release [0.9.8-3].
  (pkilambi@redhat.com)
- Adding newer version of createrepo for pulp on el5 (pkilambi@redhat.com)
- Tell systemctl to ignore deps so that our init script works correctly on
  Fedora 15 (jslagle@redhat.com)
- 713183 - python 2.4 compat patch (pkilambi@redhat.com)
- Patch from Chris St. Pierre <chris.a.st.pierre@gmail.com> :
  (pkilambi@redhat.com)
- 713580 - fixing wrong list.remove in blacklist filter application logic in
  repo sync (skarmark@redhat.com)
- 669520 python 2.4 compat fix (jslagle@redhat.com)
- 713176 - Changed user certificate expirations to 1 week. Consumer certificate
  expirations, while configurable, remain at the default of 10 years.
  (jason.dobies@redhat.com)
- 669520 - handle exception during compilation of invalid regular expression
  so that we can show the user a helpful message (jslagle@redhat.com)
- Refactored auth_required and error_handler decorators out of JSONController
  base class and into their own module (jconnor@redhat.com)
- Eliminated AsyncController class (jconnor@redhat.com)
- Fixed bug in server class name and added raw request method
  (jconnor@redhat.com)
- Default to no debug in web.py (jconnor@redhat.com)
- Updated for CR 13 (jason.dobies@redhat.com)
- 709395 - Fix cull_history api to convert to iso8601 format
  (jslagle@redhat.com)
- 709395 - Update tests for consumer history events to populate test data in
  iso8601 format (jslagle@redhat.com)
- 709395 - Fix bug in parsing of start_date/end_date when querying for
  consumer history (jslagle@redhat.com)

* Fri Jun 17 2011 Jeff Ortel <jortel@redhat.com> 0.0.191-1
- Tell systemctl to ignore deps so that our init script works correctly on
  Fedora 15 (jslagle@redhat.com)
- Adding mongo 1.7.5 as a requires for f15 pulp build (pkilambi@redhat.com)

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
