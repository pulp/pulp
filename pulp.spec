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
Version:        0.0.257
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
%posttrans
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

