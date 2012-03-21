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
Version:        1.0.2
Release:        1%{?dist}
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
Requires: grinder >= 0.0.142
Requires: httpd
Requires: mod_ssl
Requires: openssl
Requires: python-ldap
Requires: python-gofer >= 0.66
Requires: crontabs
Requires: acl
Requires: mod_wsgi >= 3.3-3.pulp%{?dist}
Requires: mongodb
Requires: mongodb-server
Requires: qpid-cpp-server
%if 0%{?rhel} == 5
Requires: m2crypto
%else
Requires: m2crypto >= 0.21.1.pulp-7%{?dist}
%endif

%if %{pulp_selinux}
Requires: %{name}-selinux-server = %{version}-%{release}
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

%if 0%{?rhel} == 5
# RHEL-5
Requires: mkisofs
%else
# RHEL-6 & Fedora
Requires: genisoimage
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
Requires:       gofer >= 0.66
Requires:       gofer-package >= 0.66
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
Requires:       gofer >= 0.66
Requires:       grinder >= 0.0.142
Requires:       httpd
Requires:       mod_wsgi >= 3.3-3.pulp%{?dist}
Requires:       mod_ssl
%if 0%{?rhel} == 5
Requires: m2crypto
%else
Requires: m2crypto >= 0.21.1.pulp-7%{?dist}
%endif
%if %{pulp_selinux}
Requires: %{name}-selinux-server = %{version}-%{release}
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
Requires(post): policycoreutils-python 
Requires(post): selinux-policy-targeted
Requires(post): /usr/sbin/semodule, /sbin/fixfiles, /usr/sbin/semanage
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
%{_bindir}/pulp-package-migrate

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
* Mon Mar 12 2012 Jeff Ortel <jortel@redhat.com> 1.0.2-1
- 800468 Use collection.update instead of collection.save to avoid race
  condition (jslagle@redhat.com)
- 801161 Add missing db migration (jslagle@redhat.com)
- pulp migrate to add task weight to snapshots (jconnor@redhat.com)
- 799120 - Added package filtering at package import stage as well as it is
  processing packages from source dir and not destination dir
  (skarmark@redhat.com)

* Thu Mar 08 2012 Jeff Ortel <jortel@redhat.com> 1.0.1-1
- Reset version = 1.0.1-1 for v1 (testing). (jortel@redhat.com)
- 797929 add requirement on semanage command (jslagle@redhat.com)
- 790806 - Added utf-8 encoding of distribution file path when path contains
  non-ascii characters (skarmark@redhat.com)
- 796854 - Removing encode_unicode from task list as changes to tasking now
  converts all task information in unicode format (skarmark@redhat.com)
- Automatic commit of package [grinder] minor release [0.0.139-1].
  (jortel@redhat.com)
- rel-eng: add grinder under rpm/. (jortel@redhat.com)
- rel-eng: add gofer under rpm/. (jortel@redhat.com)
- Renamed okaara RPM (jason.dobies@redhat.com)
- Require grinder 0.139 (jmatthews@redhat.com)
- removing wiki tags from errata controller as api docs are updated manually
  (skarmark@redhat.com)
- 790806 - encoding repo cert filenames before trying to access them
  (skarmark@redhat.com)
- adding some safety checks before computing bytes (pkilambi@redhat.com)
- 795819 - account for the relativepath from the metadata location field
  (pkilambi@redhat.com)

* Thu Feb 23 2012 Jeff Ortel <jortel@redhat.com> 0.0.267-3
- bump release for v1 candidate build. (jortel@redhat.com)
- 790806 - Fixed encoding error thrown when repo cloning with unicode id,
  filters and relativepath (skarmark@redhat.com)
- 790806 - fixed client task list to not convert task args to str instead
  encode them with 'utf-8' (skarmark@redhat.com)
- 790806 - fixes to cancel_sync which was resulting in sync not found due to
  improper encoding of unicode ids (skarmark@redhat.com)
- 790806 - urlparse is not handling unicode urls correctly, so encoding them
  with utf-8 before parsing (skarmark@redhat.com)
- 790005 Require exact matching version and release of pulp-selinux-server for
  pulp (jslagle@redhat.com)
- Update requires on mod_wsgi (jslagle@redhat.com)
- Add requires for updated m2crypto (jmatthews@redhat.com)

* Tue Feb 21 2012 Jeff Ortel <jortel@redhat.com> 0.0.267-2
- bump release for build. (jortel@redhat.com)
- bump gofer 0.66 for gofer deps. (jortel@redhat.com)
- 790285 - fix the error message to be similar for both file and package
  deletes (pkilambi@redhat.com)
- 790806 - Changes to encode task args and kwargs to unicode before
  snapshotting (skarmark@redhat.com)

* Fri Feb 17 2012 Jeff Ortel <jortel@redhat.com> 0.0.267-1
- 733312 - Make sure sync does not remove already existing packages from a repo
  during filter operation (skarmark@redhat.com)
- 790157 override ssl_ca_cert config in unit test (jslagle@redhat.com)
- 790157 Fix variable reference (jslagle@redhat.com)
- 790157 Fix variable reference (jslagle@redhat.com)
- 790157 Only set cacert if the repo is protected (jslagle@redhat.com)
- 790005 SELinux fix for qpidd https (jslagle@redhat.com)
- 790157 Use ssl_ca_certificate config to send down for cacert to consumer
  during repo bind operation (jslagle@redhat.com)
- 790806 - Added handling for proper encoding of i18n relativepath with utf-8
  encoding (skarmark@redhat.com)
- 790198 - write the updated comps information to the repo
  (pkilambi@redhat.com)
- Update URLs in functional tests to use v1 testing (jmatthews@redhat.com)
- 790069 - pulp repo sync from mounted ISO - Permission denied:
  repodata.old/repomd.xml (jmatthews@redhat.com)
- 789083, 790838, 790791 - Added regex checking and validation error when repo
  id or relative path contains whitespace characters (skarmark@redhat.com)
- Adding a dependency on mkiosfs/genisoimage to pulp for iso generation on
  exports (pkilambi@redhat.com)
- 790602 assuring that if None is passed up from the client, we are not using
  it as the sync_options (jconnor@redhat.com)
- 790285 - adding a reference check to file with repo associate on delete
  (pkilambi@redhat.com)
- Moved pic under pulp.common (jason.dobies@redhat.com)
- 790140 added same check in grant for asserting that a user or a role is
  passed in (jconnor@redhat.com)
- 790141 added automatic permissions for newly created user that gives them the
  ability to read and update their own information as well as fetch their admin
  certificate so they can log in (jconnor@redhat.com)
- 790218 - adding fix to ensure urls with missing slash are discovered
  (pkilambi@redhat.com)
- 790015 - adding support for ppc arch on repos (pkilambi@redhat.com)
- Adding errata update support to cli and web services (pkilambi@redhat.com)
- 788565 - fix selinux relabel of files from CDS rpm install
  (jmatthews@redhat.com)
* Mon Feb 13 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.266-1
- 789505 - move encode_unicode() and decode_unicode() to common/utils.py
  functions referenced in repo_cert_utils.py which is used by the CDS.
  (jortel@redhat.com)
- Fixing conversion of task args and kwargs so as to handle unicode as well as
  other exception correctly (skarmark@redhat.com)
- Reduce concurrent sync tasks and number of threads (jmatthews@redhat.com)
- Added unit test runner script from RHEL test debugging
  (jason.dobies@redhat.com)
- 712065 - limit the logging when we upload/associate packages
  (pkilambi@redhat.com)

* Mon Feb 06 2012 Jeff Ortel <jortel@redhat.com> 0.0.265-1
- 787310 - fixing error during repo sync when trying to access a variable
  before assignment when failed to load repo-md data (skarmark@redhat.com)
- Not sure what changed, but unique is no longer in the returned data
  (jason.dobies@redhat.com)
- 761039 - fixed in gofer 0.65; python 2.4 compat. (jortel@redhat.com)
- 784876 - added handling for multiple checksums for same nvrea during 'content
  list' (skarmark@redhat.com)
- 784638 Bump required version of mod_wsgi to 3.3-3.pulp (jslagle@redhat.com)
- The inclusion of CDS instances into the URI creation is crippling for
  performance and I suspect incorrect in the first place. Commented it out and
  we can discuss again in the future. (jason.dobies@redhat.com)
- 787003 - silencing the test (jconnor@redhat.com)
- Refactored capabilities; improved consumer info|list CLI output.
  (jortel@redhat.com)
- Allow qpidd_t context to open files with the cert_t context
  (jslagle@redhat.com)
- Update qpidd_t debugging (jmatthews@redhat.com)
- Update example selinux rules, for qpid debugging (jmatthews@redhat.com)
- Playpen SELinux module to help debug SELinux problems (jmatthews@redhat.com)
- updating api doc strings (pkilambi@redhat.com)
- 785922 - lookup the checksum type of a feed repo from its metadata instead of
  defaulting to sha256; this should keep the metadata in sync with filesystem
  and db (pkilambi@redhat.com)

* Wed Feb 01 2012 Jeff Ortel <jortel@redhat.com> 0.0.264-1
- 784638 Update pulp apache config and repo auth to use WSGIAccessScript
  (jslagle@redhat.com)
- 784638 Add patch to mod_wsgi so that mod_ssl hook runs before
  WSGIAccessScript (jslagle@redhat.com)
- 784876 - fixing wrong checksum key in content list cli (skarmark@redhat.com)
- 772350 - had to write new plumping to actually remove completed tasks from
  the task queue (jconnor@redhat.com)
- 772350 - hopefully last fix pertaining to this bug added task and task
  history removal for tasks related to the repo being deleted god help us all
  (jconnor@redhat.com)
- Encapsulate agent capabilities in a common class and refit client/server.
  (jortel@redhat.com)
- Made max num of certs supported in a chain a config option
  (jmatthews@redhat.com)
- Changed logic in repo_cert_utils to avoid potential for inifite loop and
  support a max num of certs in a chain (jmatthews@redhat.com)
- repo_cert_utils if our patch is missing limit the tests we will run
  (jmatthews@redhat.com)
- 784280 - SELinux denials during system cli test (jmatthews@redhat.com)
- Add capabilities to agent status; leverage in CLI. (jortel@redhat.com)
- fix to improve dep solver performance (pkilambi@redhat.com)
- 784346 - fixing unpublish logic to remove empty directories after a repo is
  unlinked from published dir (pkilambi@redhat.com)

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

