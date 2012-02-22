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
Version:        0.0.263
Release:        9%{?dist}
Summary:        An application for managing software content

Group:          Development/Languages
License:        GPLv2
URL:            https://fedorahosted.org/pulp/
Source0:        https://fedorahosted.org/releases/p/u/pulp/%{name}-%{version}.tar.gz
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
Requires: grinder >= 0.0.136
Requires: httpd
Requires: mod_ssl
Requires: openssl
Requires: python-ldap
Requires: python-gofer >= 0.64
Requires: crontabs
Requires: acl
Requires: mod_wsgi >= 3.3-1.pulp%{?dist}
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
Requires:       gofer >= 0.64
Requires:       gofer-package >= 0.64
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
Requires:       gofer >= 0.64
Requires:       grinder >= 0.0.136
Requires:       httpd
Requires:       mod_wsgi >= 3.3-1.pulp%{?dist}
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
mkdir -p %{buildroot}/etc/pki/pulp/consumer
cp etc/pki/pulp/* %{buildroot}/etc/pki/pulp

mkdir -p %{buildroot}/etc/pki/pulp/content

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
mkdir -p %{buildroot}/%{_usr}/lib/yum-plugins/
cp etc/yum/pluginconf.d/*.conf %{buildroot}/etc/yum/pluginconf.d/
cp src/pulp/client/consumer/yumplugin/pulp-profile-update.py %{buildroot}/%{_usr}/lib/yum-plugins/

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
#chown -R apache:apache /etc/pki/pulp/content/
# -- post - pulp cds ---------------------------------------------------------

%post cds
#chown -R apache:apache /etc/pki/pulp/content/

# Create the cluster related files and give them Apache ownership;
# both httpd (apache) and gofer (root) will write to them, so to prevent
# permissions issues put them under apache
touch /var/lib/pulp-cds/.cluster-members-lock
touch /var/lib/pulp-cds/.cluster-members

chown apache:apache /var/lib/pulp-cds/.cluster-members-lock
chown apache:apache /var/lib/pulp-cds/.cluster-members

# -- post - pulp consumer ------------------------------------------------------

%post consumer
if [ "$1" = "1" ]; then
  ln -s %{_sysconfdir}/rc.d/init.d/goferd %{_sysconfdir}/rc.d/init.d/pulp-agent
fi
#######################################################################
# MOVE THE OLD CERT LOCATION
# THIS SHOULD BE REMOVED AROUND VER: 0.260
# NOTE: THIS ONLY WORKS FOR DEFAULT CERT LOCATION SO IF USER CHANGES
#       IN THE consumer.conf, THIS WONT WORK.
#######################################################################
CERT="cert.pem"
OLDDIR="/etc/pki/consumer/pulp/"
NEWDIR="/etc/pki/pulp/consumer/"
if [ -d $OLDDIR ]
then
  cd $OLDDIR
  if [ -f $CERT ]
  then
    if [ ! -e $NEWDIR ]
    then
      mkdir -p $NEWDIR
    fi
    mv $CERT $NEWDIR
    rmdir --ignore-fail-on-non-empty $OLDDIR
  fi
fi
#######################################################################


%if %{pulp_selinux}
%post selinux-server
# Enable SELinux policy modules
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/enable.sh %{_datadir}
fi

# restorcecon wasn't reading new file contexts we added when running under 'post' so moved to 'posttrans'
# Spacewalk saw same issue and filed BZ here: https://bugzilla.redhat.com/show_bug.cgi?id=505066
%posttrans selinux-server
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/relabel.sh %{_datadir}
fi

%preun selinux-server
# Clean up after package removal
if [ $1 -eq 0 ]; then
%{_datadir}/pulp/selinux/server/uninstall.sh
%{_datadir}/pulp/selinux/server/relabel.sh
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
%defattr(-,apache,apache,-)
%doc
# For noarch packages: sitelib
%attr(-, root, root) %{python_sitelib}/pulp/server/
%attr(-, root, root) %{python_sitelib}/pulp/repo_auth/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp.conf
%config(noreplace) %{_sysconfdir}/pulp
%ghost %{_sysconfdir}/yum.repos.d/pulp.repo
%attr(-, apache, apache) /srv/pulp/webservices.wsgi
%attr(-, apache, apache) /srv/pulp/repo_auth.wsgi
/var/lib/pulp
/var/www/pub
/var/log/pulp
%config(noreplace) %{_sysconfdir}/pki/pulp
%attr(755, root, root) %{_sysconfdir}/rc.d/init.d/pulp-server
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
%{_usr}/lib/yum-plugins/pulp-profile-update.py*
%{_sysconfdir}/gofer/plugins/pulpplugin.conf
%{_sysconfdir}/gofer/plugins/consumer.conf
%{_sysconfdir}/yum/pluginconf.d/pulp-profile-update.conf
%attr(755,root,root) %{_sysconfdir}/pki/pulp/consumer/
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
%defattr(-,apache,apache,-)
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
%attr(775, apache, apache) %{_sysconfdir}/pki/pulp
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
* Wed Feb 22 2012 James Slagle <jslagle@redhat.com> 0.0.263-9
- 784280 - SELinux denials during system cli test (jmatthews@redhat.com)

* Mon Feb 20 2012 James Slagle <jslagle@redhat.com> 0.0.263-8
- 795570 Fix repo auth oid substitution when the oid ends with a yum variable
  (jslagle@redhat.com)
- Forget to add test data dir in prior commit (jmatthews@redhat.com)

* Wed Feb 15 2012 James Slagle <jslagle@redhat.com> 0.0.263-7
- 788565 - fix selinux relabel of files from CDS rpm install
  (jmatthews@redhat.com)

* Wed Feb 08 2012 James Slagle <jslagle@redhat.com> 0.0.263-6
- Made max num of certs supported in a chain a config option
  (jmatthews@redhat.com)
- Changed logic in repo_cert_utils to avoid potential for inifite loop and
  support a max num of certs in a chain (jmatthews@redhat.com)
- repo_cert_utils if our patch is missing limit the tests we will run
  (jmatthews@redhat.com)
- Fix bad merge resulting from when we switched to using openssl to do CA
  verification in RHUI (jslagle@redhat.com)
- 712065 - limit the logging when we upload/associate packages
  (pkilambi@redhat.com)

* Fri Feb 03 2012 James Slagle <jslagle@redhat.com> 0.0.263-5
- Fix bad merge that resulted in 2 class Package definitions
  (jslagle@redhat.com)

* Thu Feb 02 2012 James Slagle <jslagle@redhat.com> 0.0.263-4
- Fix import for pulp client refactoring (jslagle@redhat.com)


* Tue Jan 31 2012 James Slagle <jslagle@redhat.com> 0.0.263-3
- Add releasers.conf (jslagle@redhat.com)
- Merge with pulp-0.0.263-1 (jslagle@redhat.com)
- no need to generate updateinfo.xml if metadata is preserved
  (pkilambi@redhat.com)

* Fri Jan 27 2012 Jeff Ortel <jortel@redhat.com> 0.0.263-1
- fix depsolver to include file based deps (pkilambi@redhat.com)
- 783251 - Implements support for i18n ids for entities like repo, user,
  filter, consumer group etc. Also includes unit tests to avoid regressions
  related to unicode handling. (skarmark@redhat.com)
- Revert "783251 - reverting previous fix to add a more effficient fix with
  less code" (skarmark@redhat.com)
- "783251 - reverting part of the fix for i18n ids" (skarmark@redhat.com)
- 784724 - fix add package to use the correct package object when setting the
  repo id  value (pkilambi@redhat.com)
- 773752 - pulp-admin packagegroup add_package does not add pkg to repo
  (jmatthews@redhat.com)

* Thu Jan 26 2012 Jeff Ortel <jortel@redhat.com> 0.0.262-1
- dep solver on el5 picks up some false positives as search provides in yum
  only uses name. Adding a CheckProc to verify if the po is indeed providing
  the dep (pkilambi@redhat.com)
- Fix to skip metadata update on re-promotions if the repo has a parent
  associated (pkilambi@redhat.com)
- Add importer/distributor information to retrieve repo calls
  (jason.dobies@redhat.com)
- 782128 - Add support to repo auth code to verify requests against a CA chain
  file (jmatthews@redhat.com)
- 783251 - added support to be able to create pulp entities(except consumers)
  with i18n id (skarmark@redhat.com)
- 783251 - added support to be able to create pulp entities(except consumers)
  with i18n id (skarmark@redhat.com)
- Added ability to update notes in repo update (jason.dobies@redhat.com)
- added docstring (jconnor@redhat.com)
- fixed bug in bug fix that would erroniously compare None and datetime
  instances (jconnor@redhat.com)
- changing reliance on ordering of sync tasks from server to actually find the
  latest task (jconnor@redhat.com)
- 782128 - Add support to repo auth code to verify requests against a CA chain
  file (jmatthews@redhat.com)
* Mon Jan 23 2012 Jeff Ortel <jortel@redhat.com> 0.0.261-1
- 784098 - make 'capabilities' optional in consumer registration as intended.
  (jortel@redhat.com)
- trigger metadata update if a filter alters the repo state during clone
  (pkilambi@redhat.com)
- 783499 - fixing key error when selective syncing (pkilambi@redhat.com)
- Examples of CA Certificate Chain verification (jmatthews@redhat.com)

* Mon Jan 23 2012 James Slagle <jslagle@redhat.com> 0.0.260-1
- Automatic commit of package [mod_wsgi] minor release [3.3-2.pulp].
  (jslagle@redhat.com)

* Fri Jan 20 2012 Jeff Ortel <jortel@redhat.com> 0.0.259-1
- 760601 - Added missing CancelException during removal of packages and errata
  that no longer exist in the sync task (skarmark@redhat.com)
- 782109 added better error handling for UnscheduledTaskException in
  async.enqueue (jconnor@redhat.com)
- 781559 changed from using kwargs to args to that the uniqueness detection in
  the tasking subsystem will recognize different repo deletes as unique
  (jconnor@redhat.com)
- 782844 - fix the or query to check if the query is empty before woring on or
  query; also fix the cli to not make an api call to lookup deps if deps are
  empty (pkilambi@redhat.com)
- Automatic commit of package [m2crypto] minor release [0.21.1.pulp-7].
  (jmatthews@redhat.com)
- Bumping M2Crypto.spec to include getLastUpdate/getNextUpdate CRL support as
  well as M2Crypto unit tests (jmatthews@redhat.com)
- Added getLastUpdate, getNextUpdate to M2Crypto CRL wrapper plus M2Crypto
  tests (jmatthews@redhat.com)
- 782877 - fix the file syncs to use the default checksum; also fixed empty
  files default to null in mongo causing metadata parse errors
  (pkilambi@redhat.com)
- Fix unit tests. (jortel@redhat.com)
- 782480 - private key no longer stored; shared secret updated; consumer
  capabilities added; database version 36 (jortel@redhat.com)
- Update for location of temp CA&CRL combination (jmatthews@redhat.com)
- 782841 - fixing the package upload with no repoids (pkilambi@redhat.com)
- Updated generation of CRL/CA/Cert data for m2crypto unit tests
  (jmatthews@redhat.com)
- 773439 - enhanced GET /consumers/applicable_errata_in_repos/ api to accept
  send_only_applicable_errata flag and return more information about errata
  (skarmark@redhat.com)
- 757825 assure the kwargs is a dict (jconnor@redhat.com)
- 757825 add only copies of the task to the history so that editing them does
  not edit the task (jconnor@redhat.com)
- 772660 Update requires on mod_wsgi in pulp.spec (jslagle@redhat.com)
- 772660 Remove KeyError patch from mod_wsgi build, it is already included in
  version 3.3 (jslagle@redhat.com)
- 772660 Bump mod_wsgi version to 3.3 (jslagle@redhat.com)
* Mon Jan 16 2012 Jeff Ortel <jortel@redhat.com> 0.0.258-1
- Add support for enabled repository reporting; add support for soft bind.
  (jortel@redhat.com)
- updating publish help and adding response examples to distro api
  (pkilambi@redhat.com)
- 760601 - updated code for adding distribution and files to catch
  CancelException in case of cancel_clone or cancel_sync (skarmark@redhat.com)
- 773344 - fixed repo delete failure for non existing clone ids by adding
  exception handling (skarmark@redhat.com)
- Adding publish option to repo create and clone api calls
  (pkilambi@redhat.com)
- file objects dont currently have repoids (pkilambi@redhat.com)
- changed auditing interval to use local timezone (jconnor@redhat.com)
- 707884 fixed both comsumer history and auditing initialization to start in
  the future (jconnor@redhat.com)
- 773375 - fix for syncs to set the repoids directly instead of post pkg object
  creation (pkilambi@redhat.com)
- 772282 removed schedule update options from repogroup update
  (jconnor@redhat.com)
- 767763 changed util to until... (jconnor@redhat.com)
- 772072 - must use _usr/lib/ instead of _libdir macro for yum plugins.
  (jortel@redhat.com)
- Removed about half a year's changelog entries; it needed some pruning.
  (jason.dobies@redhat.com)

* Mon Jan 09 2012 Jeff Ortel <jortel@redhat.com> 0.0.257-1
- Refit for upstream agent API changes; requires gofer 0.64.
  (jortel@redhat.com)
- 772707 - fix to handle checksum mismatch when a sync uses sha va sha256
  (pkilambi@redhat.com)
- Update example responses for package group/categories (jmatthews@redhat.com)
- 772711 - fixing the repoids field in package objects (pkilambi@redhat.com)
- removing superfluous error: prefixes (jconnor@redhat.com)
- 767763 removing superfluous and weird client-side check for running sync
  (jconnor@redhat.com)
- 767763 - changed the clone action to return a conflict if the parent repo is
  syncing (jconnor@redhat.com)
- 772350 - fixed improper handling of None progress (jconnor@redhat.com)
- expose repoids when quering repo errata (pkilambi@redhat.com)
- 772348 - added missing command at the end of valid_filters to get a list
  instead of string of repoids as input to the api (skarmark@redhat.com)
- 761653 - adding package groups to repo broken (jmatthews@redhat.com)
- Change to logging for unittest code, logs in unittest drivers will
  additionally log to their own file, /tmp/pulp_unittests_only.log
  (jmatthews@redhat.com)
- Refactored out a base distributor conduit (jason.dobies@redhat.com)
- Refactored out some base functionality for importer conduits
  (jason.dobies@redhat.com)
- Added support for unit association to test harness (jason.dobies@redhat.com)
- Fixed call into conduit to use the repo transfer object
  (jason.dobies@redhat.com)
- Added associate_from_repo REST call and unit tests (jason.dobies@redhat.com)
- These are not expected to be strings but rather serialized exceptions. The
  methods themselves need to be cleaned up, but for now removing the type
  indicator from the docstring so it's not flagged as a warning when passing in
  a serialized error dict. (jason.dobies@redhat.com)
- Minor changes to consumer webservices to fix return codes
  (skarmark@redhat.com)
- Minor consumer api fixes correcting return codes (skarmark@redhat.com)
* Wed Jan 04 2012 Jeff Ortel <jortel@redhat.com> 0.0.256-1
- Fix job list. (jortel@redhat.com)
- Move consumer cert to: /etc/pki/pulp/consumer/ (jortel@redhat.com)
- fixed bug the wrongfully required user on permission grant
  (jconnor@redhat.com)
- added do not edit header to genereated wiki pages (jconnor@redhat.com)
- Refactored out the unit association query stuff into its own manager, it was
  getting way too big. (jason.dobies@redhat.com)
- changed resource description to be less confusing (jconnor@redhat.com)
- added correct failure reponse to show permissions (jconnor@redhat.com)
- Untested implementation of association from repo. Need to refactor out query
  stuff from that manager to reduce the noise before I write the tests.
  (jason.dobies@redhat.com)
- Removed unused import (jason.dobies@redhat.com)
- re-ran restapi.py (jconnor@redhat.com)
- added example key, preformatted formatted :), and required list entries
  (jconnor@redhat.com)
- Moved logic for differentiating between get_units_* calls into the manager
  (jason.dobies@redhat.com)
- Changed reporting output in the test harness (jason.dobies@redhat.com)
- Renamed get_units to get_units_across_types to make room for a syntactic
  sugar get_units method that makes the appropriate differentiation
  (jason.dobies@redhat.com)
- Bump grinder to 0.136 (jmatthews@redhat.com)
- 710153 - Fixed incorrect parsing of intervals in sync schedules. Added
  iso8601 format examples to --help. (jason.dobies@redhat.com)
- Changing return codes for some of the consumer group apis for more restful
  approach (skarmark@redhat.com)
- fix migrate script to use right collection (pkilambi@redhat.com)
- add cloned repoid to packages during the clone process (pkilambi@redhat.com)
- 765849 - RFE: include repoids reference in packages and errata * db change to
  include repoid for packages and errata * migration script * manager layer
  changes * client updates * unit test updates (pkilambi@redhat.com)
- Added association query support to the v2 harness (jason.dobies@redhat.com)
- 750847 Expose next sync time on repo schedule and sync status
  (jslagle@redhat.com)
- 760172 Change consumer history logging from consumer created/deleted to
  registered/unregistered (jslagle@redhat.com)
- Add RHEL-6-SE to list of commented out brew tags that are used
  (jslagle@redhat.com)
- 713576 Check for write permission to correct paths before attempting consumer
  register, unregister, bind, or unbind. (jslagle@redhat.com)
- 760717 Add info subcommand to pulp-admin repo command. (jslagle@redhat.com)
- Brought the conduits in line with new unit association query functionality
  (jason.dobies@redhat.com)
- improving the package import step during clone (pkilambi@redhat.com)
- Implemented unit association advanced query (jason.dobies@redhat.com)
- Made it easier to use mock objects in the manager factory
  (jason.dobies@redhat.com)
- Added validation and integrity logic to Criteria (jason.dobies@redhat.com)
- Adding some performance enhancements to cloning rpms step
  (pkilambi@redhat.com)
- Added regex example for filter value (jason.dobies@redhat.com)
- Working around for unittests since rhel5 has a problem syncing our f16 repos
  (jmatthews@redhat.com)
- Added ability to control the returned fields (jason.dobies@redhat.com)
- Greatly cleaned up criteria objects (jason.dobies@redhat.com)
- Fixed unfinished refactoring; offset doesn't have to be a parameter
  (jason.dobies@redhat.com)
- Having been the dev to come up with the name "content unit", you'd think I
  wouldn't accidentally call it "user" half the time. (jason.dobies@redhat.com)
- rpmlint fix for anything under /etc being marked as config
  (jmatthews@redhat.com)
- SELinux fix for cds httpd mod_wsgi configuration (jmatthews@redhat.com)
- rpmlint: removing zero-length file (jmatthews@redhat.com)
- rpmlint adjustments for permissions (jmatthews@redhat.com)
- rpmlint fixes to get ready for Fedora submission (jmatthews@redhat.com)
-  747661 - more pulp.spec changes (jmatthews@redhat.com)
- 747661 - Content Certificate permission errors in an AWS guest
  (jmatthews@redhat.com)
- 760683 - Move location of certs away from /etc/pki/content to a Pulp specific
  directory (jmatthews@redhat.com)
- 768126 - fix typo in pulp-admin errata install. (jortel@redhat.com)
- Flushed out get_units_by_type tests and starting on stress tests.
  (jason.dobies@redhat.com)
- 761173 - SELinux related: Move grinder usage of /tmp/grinder to
  /var/run/grinder (jmatthews@redhat.com)
- Massive work towards unit association queries. Still need some cleaning up
  and to write the tests for get_units_by_type, but this is enough work that I
  really wanted it backed up. (jason.dobies@redhat.com)
- Added webservice controllers to v2 test script (jason.dobies@redhat.com)
- Added script to run tests and coverage numbers for v2 code
  (jason.dobies@redhat.com)
- Propagated owner API changes to the sync conduit (jason.dobies@redhat.com)
- Association manager changes to accomodate association owner
  (jason.dobies@redhat.com)
- Added owner and timestamp information to unit association
  (jason.dobies@redhat.com)

* Thu Dec 15 2011 Jeff Ortel <jortel@redhat.com> 0.0.255-1
- Bump grinder to 0.133 (jmatthews@redhat.com)
- 766944 - exposing all fields when querying consumer errata
  (pkilambi@redhat.com)
- 745142 - changing delete filter api to more restful DELETE on
  /filters/filter_id and removing 'force' delete option (skarmark@redhat.com)
- 767618 - Fixed error when uploading content to a repo with filter
  (skarmark@redhat.com)
- 767246 - decompress metadata passed to modifyrepo to work around the f16
  modifyrepo issues (pkilambi@redhat.com)
- 729760 - Repo Sync - seems to be hung and status is confusing
  (jmatthews@redhat.com)
- 760458 - add makedirs() that fixes http://bugs.python.org/issue1675.
  (jortel@redhat.com)
- ran restapi.py (jconnor@redhat.com)
- 752803 added detailed list of parameters that can be updated to wiki doc
  (jconnor@redhat.com)
- 761039 - Task.exception = str(exception); more complete exception
  information. (jortel@redhat.com)
- 760777 added examples provided by mmccune :) (jconnor@redhat.com)
- 750302 added generic error exit for required append options along with
  utilization in users for permission grant (jconnor@redhat.com)
- 747975 made repo delete async (jconnor@redhat.com)
- 766705 - fixing UnboundLocalError when uploading a file due to filters
  (pkilambi@redhat.com)
- 765853 fixing race condition between task snapshot and setting of progress
  callback for repo clone and sync (jconnor@redhat.com)
- fist pass at /tasks/ controller testing (jconnor@redhat.com)
- added archived tasks to /tasks/ collection iff state=archived is passed in
  (jconnor@redhat.com)
- added id as valid filter on /tasks/ (jconnor@redhat.com)
- 765874 - Fixed amqp event handler loading. (jortel@redhat.com)
- Refinements to the relative path validation logic (jason.dobies@redhat.com)
- Automatic commit of package [python-isodate] minor release [0.4.4-4.pulp].
  (jslagle@redhat.com)
- removing yum_repo_grinder_lock from YumSynchronizer (skarmark@redhat.com)
- 760673 - Fix consumer group package install; Add support for remote class
  constuctor args. (jortel@redhat.com)
- 761205 - Nested relative paths are no longer allowed by Pulp
  (jason.dobies@redhat.com)
- Removing instantiation of repoapi from RepoCloneTask which can cause pickling
  of threading lock issue (skarmark@redhat.com)
- 742320 - fix group logicwhen running createrepo to use tyep.ext instead of
  whole filename causing file name too long errors (pkilambi@redhat.com)
- requires gofer 0.63; bump for project alignment. (jortel@redhat.com)
- SELinux: relabel files when rpm is uninstalled (jmatthews@redhat.com)
- 761232 - fix applied to pulp-cds for F16 compat. (jortel@redhat.com)
- SELinux: Change pulp log files to httpd_sys_content_rw_t
  (jmatthews@redhat.com)
- 761232 - replace /etc/init.d/ references to use /sbin/service instead for F16
  compat. (jortel@redhat.com)
- 760958 - Fixing DB validation error (skarmark@redhat.com)
- SELinux: quiet output from uninstall (jmatthews@redhat.com)
- 760310 - fix cloning a empty repo to handle gracefully (pkilambi@redhat.com)
- SELinux: fix for pulp_cert_t (jmatthews@redhat.com)
- 760766 - Updated content upload cli to parse new return format for
  repo.add_packages() with filters correctly (skarmark@redhat.com)
- SELinux: move setsebool to enable script to be executed during post
  (jmatthews@redhat.com)
- SELinux: rewrite rules to be based off of httpd content
  (jmatthews@redhat.com)
- Fixed 8 typos in the word "omitting" (jason.dobies@redhat.com)
- 710153 - Significant reworking of CDS status CLI command. Brought in line
  with the work done in this area on RHUI 2.0. (jason.dobies@redhat.com)
- SELinux: add file context for initrc script pulp-server
  (jmatthews@redhat.com)
- SELinux: changes for certs pulp creates, pulp_certs_t (jmatthews@redhat.com)
- 760745 - The CLI should pass None for consumer client bundle if no entries
  are present. (jason.dobies@redhat.com)
- Added updated count to harness display (jason.dobies@redhat.com)
- SELinux: leveraging apache_content_template(pulp) macro to simplify rules
  Updates for developer setup/uninstall scripts (jmatthews@redhat.com)
- SELinux: added error checking to making a policy (jmatthews@redhat.com)
- SELinux:  Adding bools to allow http to network and execute tmp files
  (jmatthews@redhat.com)
- SELinux rules update to leverage apache_content_template macro
  (jmatthews@redhat.com)
- Adding filtering capability for manually uploaded packages and custom errata
  (skarmark@redhat.com)
- 760607 - fixing the pkg list param (pkilambi@redhat.com)
- 745458 - Separated asynchronous operations in cloning process from
  synchronous operations such that clone task can be reloaded from db from a
  saved state in case pulp-server dies during cloning (skarmark@redhat.com)
* Fri Dec 02 2011 Jeff Ortel <jortel@redhat.com> 0.0.254-1
- fixing the clone to accoutn for el5 type metadata paths causing missing
  imports (pkilambi@redhat.com)
- SELinux update developer scripts, added a developer uninstall, fixed possible
  issue with grinder (jmatthews@redhat.com)
- Moved api_responses config from admin.conf to environment variables
  (skarmark@redhat.com)
- 756417 - ignore foreground option for group exports and let the server bad
  requests pass to clients (pkilambi@redhat.com)
- Added conduit utility method for building the publish report
  (jason.dobies@redhat.com)
- Renamed terminology in the managers to reflect referenced instead of
  parent/child units (jason.dobies@redhat.com)
- Parser and database changes for changing unique indexes to unit key.
  (jason.dobies@redhat.com)
- Updating bash completion script for latest changes (skarmark@redhat.com)
- Making pulp 'eval' free and updating repo list --note to accept a note in
  key:value format instead of dictionary (skarmark@redhat.com)
- 759153 - Add INI file validation. (jortel@redhat.com)
- README files to instruct on how to use the v2 plugins
  (jason.dobies@redhat.com)
- Added conduit syntactic sugar method for building sync reports.
  (jason.dobies@redhat.com)
- Added updated_count and split out summary and detail logs in plugin reports
  (jason.dobies@redhat.com)
- Added ability to override scenario properties at command line
  (jason.dobies@redhat.com)
- Made the delete repo not fail on an HTTP error code (jason.dobies@redhat.com)
- 756454 - Fixed package search with --repoids and removed eval
  (skarmark@redhat.com)

* Thu Oct 27 2011 James Slagle <jslagle@redhat.com> 0.0.214-8
- 737584 Switch remove_old_packages back to false.  Since we're not
  regenerating repo metadata on sync, the packages we don't keep will 404 for
  both CDS's and clients. (jslagle@redhat.com)
- 747725 Strip off initial and trailing slash from OID url.  Some content certs
  may have them where others do not. (jslagle@redhat.com)

* Mon Oct 24 2011 James Slagle <jslagle@redhat.com> 0.0.214-7
- 748555 Default remove_old_packages to true so that old packages beyond the 2
  most recent versions are pruned from the filesystem (jslagle@redhat.com)

* Mon Oct 24 2011 James Slagle <jslagle@redhat.com> 0.0.214-6
- 747725 Fix regular expression during oid validation and add a test that uses
  wildcard oid urls (jslagle@redhat.com)
- Bump grinder to 0.122 (jmatthews@redhat.com)
- Update since grinder no longer has a yum lock (jmatthews@redhat.com)
- 747880 Allow for custom repos to have no sync schedule (jslagle@redhat.com)

* Thu Oct 20 2011 James Slagle <jslagle@redhat.com> 0.0.214-4
- Remove setgid root and sticky bit from our init scripts (jslagle@redhat.com)

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

