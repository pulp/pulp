# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0


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

# ---- Pulp Platform -----------------------------------------------------------

Name: pulp
Version: 0.0.313
Release: 2%{?dist}
Summary: An application for managing software content
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: python-nose
BuildRequires: rpm-python

%description
Pulp provides replication, access, and accounting for software repositories.

%prep
%setup -q

%build
pushd src
%{__python} setup.py build
popd
%if %{pulp_selinux}
# SELinux Configuration
cd selinux/server
sed -i "s/policy_module(pulp-server,[0-9]*.[0-9]*.[0-9]*)/policy_module(pulp-server,%{version})/" pulp-server.te
./build.sh
cd -
%endif

%install
rm -rf %{buildroot}
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

# Directories
mkdir -p /srv
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/admin
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/admin/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/consumer
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/consumer/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/agent
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/agent/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/pki/%{name}
mkdir -p %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer
mkdir -p %{buildroot}/%{_sysconfdir}/gofer/plugins
mkdir -p %{buildroot}/%{_sysconfdir}/rc.d/init.d
mkdir -p %{buildroot}/%{_sysconfdir}/httpd/conf.d/
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/plugins
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/plugins/distributors
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/plugins/importers
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/plugins/profilers
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/plugins/types
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/admin
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/consumer
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/consumer/extensions
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/agent
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/agent/handlers
mkdir -p %{buildroot}/%{_var}/lib/%{name}/
mkdir -p %{buildroot}/%{_var}/lib/%{name}/uploads
mkdir -p %{buildroot}/%{_var}/lib/%{name}/repos
mkdir -p %{buildroot}/%{_var}/lib/%{name}/packages
mkdir -p %{buildroot}/%{_var}/lib/%{name}/published
mkdir -p %{buildroot}/%{_var}/lib/%{name}/published/http
mkdir -p %{buildroot}/%{_var}/lib/%{name}/published/https
mkdir -p %{buildroot}/%{_var}/log/%{name}/
mkdir -p %{buildroot}/%{_libdir}/gofer/plugins
mkdir -p %{buildroot}/%{_bindir}

# Configuration
cp -R etc/pulp/* %{buildroot}/%{_sysconfdir}/%{name}

# Apache Configuration
cp etc/httpd/conf.d/pulp.conf %{buildroot}/%{_sysconfdir}/httpd/conf.d/

# Pulp Web Services
cp -R srv %{buildroot}

# PKI
cp etc/pki/pulp/* %{buildroot}/%{_sysconfdir}/pki/%{name}

# Agent
cp etc/gofer/plugins/pulp.conf %{buildroot}/%{_sysconfdir}/gofer/plugins
cp -R src/pulp/agent/gofer/pulp.py %{buildroot}/%{_libdir}/gofer/plugins
ln -s %{_sysconfdir}/rc.d/init.d/goferd %{buildroot}/%{_sysconfdir}/rc.d/init.d/pulp-agent

# Tools
cp bin/* %{buildroot}/%{_bindir}

# Init (init.d)
cp etc/rc.d/init.d/* %{buildroot}/%{_sysconfdir}/rc.d/init.d/

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/*.egg-info

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


# ---- Server ------------------------------------------------------------------

%package server
Summary: The pulp platform server
Group: Development/Languages
Requires: python-%{name}-common = %{version}
Requires: pymongo >= 1.9
Requires: python-setuptools
Requires: python-webpy
Requires: python-simplejson >= 2.0.9
Requires: python-oauth2 >= 1.5.170-2.pulp
Requires: python-httplib2
Requires: python-isodate >= 0.4.4-3.pulp
Requires: python-BeautifulSoup
Requires: grinder >= 0.1.5-1
Requires: httpd
Requires: mod_ssl
Requires: openssl
Requires: python-ldap
Requires: python-gofer >= 0.70
Requires: crontabs
Requires: acl
Requires: mod_wsgi >= 3.3-3.pulp
Requires: mongodb
Requires: mongodb-server
Requires: qpid-cpp-server
# RHEL5
%if 0%{?rhel} == 5
Group: Development/Languages
Requires: m2crypto
Requires: python-uuid
Requires: python-ssl
Requires: python-ctypes
Requires: python-hashlib
Requires: createrepo = 0.9.8-3
Requires: mkisofs
# RHEL6 & FEDORA
%else
Requires: m2crypto >= 0.21.1.pulp-7
Requires: genisoimage
%endif
# RHEL6 ONLY
%if 0%{?rhel} == 6
Requires: python-ctypes
Requires: python-hashlib
Requires: nss >= 3.12.9
Requires: curl => 7.19.7
%endif
Obsoletes: pulp

%description server
Pulp provides replication, access, and accounting for software repositories.

%files server
# root
%defattr(-,root,root,-)
%{python_sitelib}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/server.conf
%config(noreplace) %{_sysconfdir}/%{name}/logging/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%config(noreplace) %{_sysconfdir}/pki/%{name}
%{_sysconfdir}/rc.d/init.d/pulp-server
%{_bindir}/pulp-migrate
# apache
%defattr(-,apache,apache,-)
%dir /srv/%{name}
%dir %{_var}/log/%{name}
/srv/%{name}/webservices.wsgi
%{_var}/lib/%{name}/
%{_usr}/lib/pulp/plugins/distributors
%{_usr}/lib/pulp/plugins/importers
%{_usr}/lib/pulp/plugins/profilers
%{_usr}/lib/pulp/plugins/types
%doc


# ---- Common ------------------------------------------------------------------

%package -n python-pulp-common
Summary: Pulp common python packages
Group: Development/Languages
Obsoletes: pulp-common

%description -n python-pulp-common
A collection of components that are common between the pulp server and client.

%files -n python-pulp-common
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/__init__.*
%{python_sitelib}/%{name}/common/
%dir %{_usr}/lib/%{name}
%doc


# ---- Client Bindings ---------------------------------------------------------

%package -n python-pulp-bindings
Summary: Pulp REST bindings for python
Group: Development/Languages

%description -n python-pulp-bindings
The Pulp REST API bindings for python.

%files -n python-pulp-bindings
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/bindings/
%doc


# ---- Client Extension Framework -----------------------------------------------------

%package -n python-pulp-client-lib
Summary: Pulp client extensions framework
Group: Development/Languages
Requires: python-%{name}-common = %{version}
Requires: python-okaara >= 1.0.18
Obsoletes: pulp-client-lib

%description -n python-pulp-client-lib
A framework for loading Pulp client extensions.

%files -n python-pulp-client-lib
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/client/
%doc


# ---- Agent Handler Framework -------------------------------------------------

%package -n python-pulp-agent-lib
Summary: Pulp agent handler framework
Group: Development/Languages
Requires: python-%{name}-common = %{version}

%description -n python-pulp-agent-lib
A framework for loading agent handlers that provide support
for content, bind and system specific operations.

%files -n python-pulp-agent-lib
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/agent/*.py
%{python_sitelib}/%{name}/agent/lib/
%dir %{_sysconfdir}/%{name}/agent
%dir %{_sysconfdir}/%{name}/agent/conf.d
%dir %{_usr}/lib/%{name}/agent
%doc


# ---- Admin Client (CLI) ------------------------------------------------------

%package admin-client
Summary: Admin tool to administer the pulp server
Group: Development/Languages
Requires: python-%{name}-common = %{version}
Requires: python-%{name}-bindings = %{version}
Requires: python-%{name}-client-lib = %{version}
Requires: %{name}-builtins-admin-extensions = %{version}
Obsoletes: pulp-client
Obsoletes: pulp-admin

%description admin-client
A tool used to administer the pulp server, such as repo creation and
synching, and to kick off remote actions on consumers.

%files admin-client
%defattr(-,root,root,-)
%dir %{_sysconfdir}/%{name}/admin
%dir %{_sysconfdir}/%{name}/admin/conf.d
%dir %{_usr}/lib/%{name}/admin/extensions/
%config(noreplace) %{_sysconfdir}/%{name}/admin/admin.conf
%{_bindir}/%{name}-admin
%doc


# ---- Consumer Client (CLI) ---------------------------------------------------

%package consumer-client
Summary: Consumer tool to administer the pulp consumer.
Group: Development/Languages
Requires: python-%{name}-common = %{version}
Requires: python-%{name}-bindings = %{version}
Requires: python-%{name}-client-lib = %{version}
Requires: %{name}-builtins-consumer-extensions = %{version}
Obsoletes: pulp-consumer

%description consumer-client
A tool used to administer a pulp consumer.

%files consumer-client
%defattr(-,root,root,-)
%dir %{_sysconfdir}/%{name}/consumer
%dir %{_sysconfdir}/%{name}/consumer/conf.d
%dir %{_usr}/lib/%{name}/consumer/extensions/
%config(noreplace) %{_sysconfdir}/%{name}/consumer/consumer.conf
%config(noreplace) %{_sysconfdir}/pki/%{name}/consumer
%{_bindir}/%{name}-consumer
%doc


# ---- Agent -------------------------------------------------------------------

%package agent
Summary: The Pulp agent
Group: Development/Languages
Requires: python-%{name}-bindings = %{version}
Requires: python-%{name}-agent-lib = %{version}
Requires: gofer >= 0.70

%description agent
The pulp agent, used to provide remote command & control and
scheduled actions such as reporting installed content profiles
on a defined interval.

%files agent
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/%{name}/agent/agent.conf
%{_sysconfdir}/gofer/plugins/pulp.conf
%{_libdir}/gofer/plugins/pulp.*
%{_sysconfdir}/rc.d/init.d/pulp-agent
%doc

# --- Selinux ---------------------------------------------------------------------

%if %{pulp_selinux}
%package        selinux
Summary:        Pulp SELinux policy for pulp components.
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

%description    selinux
SELinux policy for Pulp's components

%post selinux
# Enable SELinux policy modules
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/enable.sh %{_datadir}
fi

# restorcecon wasn't reading new file contexts we added when running under 'post' so moved to 'posttrans'
# Spacewalk saw same issue and filed BZ here: https://bugzilla.redhat.com/show_bug.cgi?id=505066
%posttrans selinux
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/relabel.sh %{_datadir}
fi

%preun selinux
# Clean up after package removal
if [ $1 -eq 0 ]; then
%{_datadir}/pulp/selinux/server/uninstall.sh
%{_datadir}/pulp/selinux/server/relabel.sh
fi
exit 0

%files selinux
%defattr(-,root,root,-)
%doc selinux/server/pulp-server.fc selinux/server/pulp-server.if selinux/server/pulp-server.te
%{_datadir}/pulp/selinux/server/*
%{_datadir}/selinux/*/pulp-server.pp
%{_datadir}/selinux/devel/include/%{moduletype}/pulp-server.if

%endif

%changelog
* Thu Jul 12 2012 Jeff Ortel <jortel@redhat.com> 0.0.313-1
- - Move the repo working dirs under "repos" to make room for the group
  working dirs (jason.dobies@redhat.com)
- Moved repo group related managers under a group subpackage
  (jason.dobies@redhat.com)
- Added plugin base classes and data types for group plugins
  (jason.dobies@redhat.com)
- fixed multiple bugs in deletion of on-disk orphaned content
  (jason.connor@gmail.com)
- TA51977 Pulled generic Criteria-based search features out of the repository
  controller and into a generic SearchController. (mhrivnak@redhat.com)

* Tue Jul 10 2012 Jeff Ortel <jortel@redhat.com> 0.0.312-1
- minor fix to user manager functions (skarmark@redhat.com)
- user admin extensions (skarmark@redhat.com)
- fixing return of associate & unassociate (jason.connor@gmail.com)
- fixing rest api (jason.connor@gmail.com)
- finished adding doctrings (jason.connor@gmail.com)
- added some docstrings (jason.connor@gmail.com)
- moving manager factory initialization up immediately after db initialization
  (skarmark@redhat.com)
- updating copyright date (mhrivnak@redhat.com)
- Added unit tests for REST API notifier (jason.dobies@redhat.com)
- BZ 827204 moved the 'serialize' method to the 'serialization.consumer' module
  (mhrivnak@redhat.com)
- BZ 827619 ConsumerResource controller now adds '_href' attribute to return
  values for GET and PUT requests. (mhrivnak@redhat.com)
- Implementation of the REST API notifier (jason.dobies@redhat.com)
- using a different query for unassociate, hopefully one that is friendlier for
  pymongo 1.9 (jason.connor@gmail.com)
- BZ 827619 Removing uses of a deprecated method. Also documenting that method
  as deprecated and removing its duplicate code. (mhrivnak@redhat.com)
- Modifying two tests to not use the 'assertIsInstance' method, which isn't
  available in all of our environments. (mhrivnak@redhat.com)
- BZ 827619 Removing use of a deprecated method. (mhrivnak@redhat.com)
  (mhrivnak@redhat.com)
- Modifying two tests to not use the 'assertIsInstance' method, which isn't
  available in all of our environments. (mhrivnak@redhat.com)
- Wired up publish events (jason.dobies@redhat.com)
- Wired repo sync started/finished events into the manager execution
  (jason.dobies@redhat.com)
- Minor tweaks to group/category upload CLI (jason.dobies@redhat.com)
- repo group tests (jason.connor@gmail.com)
- fixed associate query (jason.connor@gmail.com)
- added more robust note management for repo groups (jason.connor@gmail.com)
- changed repod_ids to always be an array, even an empty one
  (jason.connor@gmail.com)
- Revert "changed to dict access instead of Model" (jason.connor@gmail.com)
- added missing collection name (jason.connor@gmail.com)
- skeleton tests (jason.connor@gmail.com)
- start of repo group unit tests (jason.connor@gmail.com)
- fixed bug in action tag generation (jason.connor@gmail.com)
- initial pass at repo groups controllers (jason.connor@gmail.com)
- added call to remove repo from all groups to repo delete
  (jason.connor@gmail.com)
- added group manager to factory (jason.connor@gmail.com)
- removed unused add repo and converted remove to batch remove a repo from
  multiple (or even all) associated groups (jason.connor@gmail.com)
- added returns of repo group for create and update (jason.connor@gmail.com)
- added repo groups resource (jason.connor@gmail.com)
- added i18n test (jason.connor@gmail.com)
- more advanced associate and unassociate methods for batch adding/removing
  repos using the new criteria model (jason.connor@gmail.com)
- some reminders from the deep dive (jason.connor@gmail.com)
- changed to dict access instead of Model (jason.connor@gmail.com)
- removed comment as Jay answered the question pertaining to it
  (jason.connor@gmail.com)
- fixing upload to include get units and needed summary info
  (pkilambi@redhat.com)
- Cleanup how we change the version identifier in our selinux module
  (jmatthews@redhat.com)
- Allow client upload of a unit with no file data, allows creation of unit with
  just unit_key/metadata (jmatthews@redhat.com)
- BZ 827617: content upload API no longer returns empty dictionaries as a
  response body, but instead returns None. (mhrivnak@redhat.com)
- updating grinder to include fix for #828447 (pkilambi@redhat.com)
- adding additional documentation to the advanced repository searching method
  (mhrivnak@redhat.com)
- Adding advanced repo searching to the REST API. (mhrivnak@redhat.com)
- fixing wrong manager module import before the initialization of factory
  (skarmark@redhat.com)
- Using factory.managers instead of importing user_manager separately
  (skarmark@redhat.com)
- Fixed a bug where the related object merging method assumed that the list of
  related objects would have a 'repo_id' attribute, which turned out to be
  incorrect since objects fresh out of the database are basically just dicts.
  The method now accesses the 'repo_id' key on the object with dict-style
  access notation. (mhrivnak@redhat.com)
- Modified the REST API for repo queries to accept new query parameters
  'importers' and 'distributors', which simply split the work of the
  previously-implemented 'details' parameter. (mhrivnak@redhat.com)
- added tests to verify current functionality of CLI repo requests. Also added
  the ability to pass query parameters to the REST API when making the CLI code
  makes a repositories request. (mhrivnak@redhat.com)
  (mhrivnak@redhat.com)
- Adding unit tests, improving existing tests, and adding documentation (while
  fixing a couple of typos). This is all to help me understand how this system
  works before changing it. (mhrivnak@redhat.com)
- BZ 827223 Fetching an individual repository now includes the _href attribute.
  Expanded existing tests to verify its presence. (mhrivnak@redhat.com)
- Added a query parameter "details" to the queries for a specific repo by ID or
  all repos, which signifies if importers and distributors should be included.
  Also added tests and updated API docs. (mhrivnak@redhat.com)

* Tue Jul 03 2012 wes hayutin <whayutin@redhat.com> 0.0.311-1
- 837406 need to add yum groups to pulp spec for rhel5 to build
  (whayutin@redhat.com)
- test_repo_manager fails on rhel5 due to the way the data is passed to magic
  mock (whayutin@redhat.com)

* Tue Jul 03 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.310-1
- Unit tests for event listener update (jason.dobies@redhat.com)
- Added event listener REST APIs (jason.dobies@redhat.com)
- fixing error in user update when updating roles which was causing admin
  permission error in the latest qe build (skarmark@redhat.com)
- Fixed incorrect state comparison (jason.dobies@redhat.com)
- Removed deepcopy call which was hosing up pymongo on RHEL6
  (jason.dobies@redhat.com)

* Fri Jun 29 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.309-1
- Wired up unit copy to be able to copy dependencies too
  (jason.dobies@redhat.com)
- Fixing broken user auth related unit tests (skarmark@redhat.com)
- User functionality in v2, cleaning up v1 user apis and fixing unit tests
  (skarmark@redhat.com)
- Made the task timeout configurable in the request (jason.dobies@redhat.com)
- Added dependency resolution REST API (jason.dobies@redhat.com)
- Implementation and unit tests for dependency resolution manager
  (jason.dobies@redhat.com)

* Thu Jun 28 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.308-1
- wrap profiler exceptions in a PulpExecutionException. (jortel@redhat.com)
- Involve profiler in unit install flow. (jortel@redhat.com)
- Fix unresolved merge conflict. (jortel@redhat.com)
- update agent to use new binding to report package profiles.
  (jortel@redhat.com)
- handle changes in consumer.conf. (jortel@redhat.com)
- IDE lookup works better if you spell the @rtype package correctly
  (jason.dobies@redhat.com)
- Basics of the dependency manager and conduit (jason.dobies@redhat.com)
- I have no idea how our unit tests ever ran before this change
  (jason.dobies@redhat.com)
- Fixed reference to removed class (jason.dobies@redhat.com)
- V2 Users model changes, manager functions and rest api with unit tests
  (skarmark@redhat.com)
- removed unused constant (jason.connor@gmail.com)
- compensate for order that is already an integer (jason.connor@gmail.com)
- custom PulpCollection query method that utilizes the Criteria model
  (jason.connor@gmail.com)
- preliminary implementation of Criteria model (jason.connor@gmail.com)
- added validation to group delete for a more informative delete operation
  (jason.connor@gmail.com)
- removed auto publish from group distributors (jason.connor@gmail.com)
- add profile controller and unit tests. (jortel@redhat.com)
- Removed duplicate conduit and reference to pointless base class
  (jason.dobies@redhat.com)
- Broke out conduit functionality into mixin paradigm (jason.dobies@redhat.com)
- updated epydocs. (jortel@redhat.com)
- add missing consumer test. (jortel@redhat.com)
- Add profiler manager unit tests. (jortel@redhat.com)
- test renamed. (jortel@redhat.com)
- split profiler conduit into separate module. (jortel@redhat.com)
- Expand ProfilerConduit; add conduit unit tests. (jortel@redhat.com)
- Merge branch 'master' into event (jason.dobies@redhat.com)
- Implementation of the event fire manager (jason.dobies@redhat.com)
- Merge branch 'master' into event (jason.dobies@redhat.com)
- Finished up event CRUD manager (jason.dobies@redhat.com)
- SELinux spec update add missing 'fi' in %%post (jmatthews@redhat.com)
- Add profiler tests to plugin loader & manager; Don't think ProfilerManager is
  needed. (jortel@redhat.com)
- Initial profiler API, conduit, managers and model. (jortel@redhat.com)
- US21173: Adding a 'content_unit_count' attribute to the Repo model and the
  logic to keep it up to date as units become associated and disassociated.
  Also added lots of tests. (mhrivnak@redhat.com)
- This test was failing sometimes because mongo was returning data in an order
  we didn't expect. This small change puts the data into the expected order
  before any assertions happen. (mhrivnak@redhat.com)
- removed superfluous double instantiation of repo group pymongo collection
  objects (jason.connor@gmail.com)
- initial implementation of repo group manager (jason.connor@gmail.com)
- added docstrings (jason.connor@gmail.com)
- added unique and search indices to db models (jason.connor@gmail.com)
- added models for repo groups and group-wide distributors
  (jason.connor@gmail.com)
- adding selinux packaging to pulp spec (pkilambi@redhat.com)
- SELinux: Removing old developer setup scripts (jmatthews@redhat.com)
- 827201 - fixing consumer_history to use start_date and end_date filters in
  iso8601 format and history tests (skarmark@redhat.com)
- 827211 - Running unbind through coordinator to keep any of the required
  resources from being deleted in the middle of the operation
  (skarmark@redhat.com)
- Merge branch 'master' into event (jason.dobies@redhat.com)
- Implementation of the listener CRUD and notification structure
  (jason.dobies@redhat.com)
- SELinux: Update labels to account for layout changes (jmatthews@redhat.com)

* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.307-1
- The server needs to explicitly create the plugins/* dirs
  (jason.dobies@redhat.com)

* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.306-1
- Fixed incorrect instance check when parsing criteria
  (jason.dobies@redhat.com)
- 827210 - fixed consumer call request tags to be generated using
  pulp.common.tags methods (skarmark@redhat.com)
- changed cancel to return bool or None (jason.connor@gmail.com)
- added comment about task state/taskqueue race condition
  (jason.connor@gmail.com)
- renamed ignored state to skipped (jason.connor@gmail.com)
- Revert "renamed ignored state to skipped" (jason.connor@gmail.com)
- renamed ignored state to skipped (jason.connor@gmail.com)
- Fixing consumer authorization problem because of no associated users with the
  consumers (like in v1) and minor fixed to consumer config parsing
  (skarmark@redhat.com)

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.305-1
- Updated the code to match where the RPM wants the plugins
  (jason.dobies@redhat.com)
- added test for proper creation of blocking tasks from user-defined
  dependencies (jason.connor@gmail.com)
- unittests for user-defined dependencies and topological sotr
  (jason.connor@gmail.com)

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.304-1
- 

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.303-1
- added user-defined dependency analysis to execute_multiple_calls
  (jason.connor@gmail.com)
- added more to docstring to clarify behaviour of sort (jason.connor@gmail.com)
- raising a more targeted exception upon cycle detection
  (jason.connor@gmail.com)
- comment (jason.connor@gmail.com)
- added None dependencies to scheduled call requests (jason.connor@gmail.com)
- initial implementation of topological sort algorithm (jason.connor@gmail.com)
- placeholder of user-defined dependency analsys (jason.connor@gmail.com)
- changed field from group_dependencies to just dependencies
  (jason.connor@gmail.com)
- added new group dependencies field and convenience api
  (jason.connor@gmail.com)
- added ignore method to utilize new ignored state (jason.connor@gmail.com)
- added new task states (jason.connor@gmail.com)
- docstring and comment changes (jason.connor@gmail.com)

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.302-1
- Fixed crashing if no override is present (jason.dobies@redhat.com)

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.301-1
- some job->task_group conversions I missed (jason.connor@gmail.com)
- changed "job" to "task_group" to elimnate any semantic confusion between task
  and job (jason.connor@gmail.com)
- changed repo resource controllers to not use deprecated execution module
  methods (jason.connor@gmail.com)
- moved state change, thread kick-off, and life cycle callback execution to a
  wrapper for task run to elliminate a race condition when canceling tasks in a
  ready state (jason.connor@gmail.com)
- changed task.cancel to automatically allow the cancellation of waiting tasks
  (jason.connor@gmail.com)
- Directory ownership tweaking in packageing. (jortel@redhat.com)
- On admin-client, consumer-client:  add Requires on builtin extensions.
  (jortel@redhat.com)
- Fix missing published/ and /var/www/pub. (jortel@redhat.com)
- Adjust Obsoletes: in refactored .spec. (jortel@redhat.com)
- Adjust dependancies after install testing. (jortel@redhat.com)
- adding call request id to corresponding call report (jason.connor@gmail.com)
- better argument formatting for call requests __str__ (jason.connor@gmail.com)
- added resource management convenience methods to make dealing with call
  request resources more bearable (jason.connor@gmail.com)
- added unique, generated, id for call requests (jason.connor@gmail.com)
- remove all "not implemented" controllers from content rest api
  (jason.connor@gmail.com)

* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.300-1
- Align versions to: 300 (jortel@redhat.com)
- Added specific error message for expired certificates
  (jason.dobies@redhat.com)
- not making the same mistake again of version one, two, three, four, etc
  (jason.connor@gmail.com)
- moved http_response dict to compat (jason.connor@gmail.com)
- moved digestmod import into compat (jason.connor@gmail.com)
- using compat module instead of try/except imports (jason.connor@gmail.com)
- cleaned up imports (jason.connor@gmail.com)
- moved all try/except ImportError blocks to compat (jason.connor@gmail.com)
- removed unused value parsing function (jason.connor@gmail.com)
- Add Obsoletes: for platform .spec. (jortel@redhat.com)
- deleted v1 tasking from code base (jason.connor@gmail.com)
- removed old task to dict output from web controllers (jason.connor@gmail.com)
- removed tasking.task from unittests (jason.connor@gmail.com)
- remove auditing logging (jason.connor@gmail.com)
- removed all unused cruft and added new header (jason.connor@gmail.com)
- removed sections from default config and config file that are no longer used
  (jason.connor@gmail.com)
- removed derived class OPTIONS method for contents cotrollers
  (jason.connor@gmail.com)
- added OPTIONS method handler to controller base class
  (jason.connor@gmail.com)
- removed unused v2 api controller (jason.connor@gmail.com)
- added finalize to dispatch factory and replaced unittest cleanup with it
  (jason.connor@gmail.com)
- YumImporter: Cleaning up extra test dirs during tests & Adding configurable
  Retry logic for grinder (jmatthews@redhat.com)
- Better package summary/descriptions. (jortel@redhat.com)
- pulp-rpm spec build fixes. (jortel@redhat.com)
- Changed super reference in exception because python is weird.
  (jason.dobies@redhat.com)
- Changed setUpClass super references for python compatibility
  (jason.dobies@redhat.com)
- Add copyright and fix (name) macro usage. (jortel@redhat.com)
- Move pulp.spec under platform; Add pulp-builtins.spec and entry in rel-eng/.
  (jortel@redhat.com)
- Migrated clients to pulp common config abstraction (jason.dobies@redhat.com)
- Moved selinux under platform (jason.dobies@redhat.com)
- Fixed override ability in common config (jason.dobies@redhat.com)
- 828256 - replaced ordering comparison with equality comparison as the former
  are not allowed with Duration instances (jason.connor@gmail.com)
- added comments (jason.connor@gmail.com)
- Fixed LDAPConnection reference (jason.dobies@redhat.com)
- Restructured pulp-consumer commands and fixed broken unregister
  (jason.dobies@redhat.com)
- purge v1 gofer plugins. (jortel@redhat.com)
- Corrected logging filename (jason.dobies@redhat.com)
- Fixed the name of override files (jason.dobies@redhat.com)
- Changed database collection names to remove gc prefix
  (jason.dobies@redhat.com)
- Removed v1 tasking stuff (jason.dobies@redhat.com)
- Clean up from pulp.server (jason.dobies@redhat.com)
- Refactored pulp.spec to match git/package reorganization. (jortel@redhat.com)
- Removed v1 domain models (jason.dobies@redhat.com)
- Changed name/location of plugins code (jason.dobies@redhat.com)
- Removed dead CDS code (jason.dobies@redhat.com)
- No longer needed (jason.dobies@redhat.com)
- Deleted v1 API classes (jason.dobies@redhat.com)
- Stripped v2-ness from v2 controllers (jason.dobies@redhat.com)
- Finished deleting v1 controllers (jason.dobies@redhat.com)
- Purging of v1 controllers (jason.dobies@redhat.com)
- Refit handlers to work with new common/config; fix handler unit test.
  (jortel@redhat.com)
- Round of unit test fixes (jason.dobies@redhat.com)
- Last batch of unit test fixes (jason.dobies@redhat.com)
- More unit test fixes (jason.dobies@redhat.com)
- Next batch of refactored unit tests (jason.dobies@redhat.com)
- Moved repolib tests (after figuring out which of the two nearly identical
  files was correct) into rpm_support (jason.dobies@redhat.com)
- Moved repo auth tests into rpm_support (jason.dobies@redhat.com)
- Deleted a bunch of unused files in the test dir (jason.dobies@redhat.com)
- git refactor: fix gofer plugin imports. (jortel@redhat.com)
- Continued unit test clean up (jason.dobies@redhat.com)
- Split up uber consumer manager test file into multiple files by manager
  (jason.dobies@redhat.com)
- Continued work on unit test cleanup (jason.dobies@redhat.com)
- Cleanup of Pulp test base classes (jason.dobies@redhat.com)
- Moved extensions under /usr/lib/pulp (jason.dobies@redhat.com)
- Work towards fixing rpm plugin unit tests (jason.dobies@redhat.com)
- Removed dead CDS code (jason.dobies@redhat.com)
- Started work towards correcting the certificate issues for consumers (more to
  do) (jason.dobies@redhat.com)
- Simplified setup.py until we figure out how we want to use it
  (jason.dobies@redhat.com)
- Fixes for config consolidation (jason.dobies@redhat.com)
- Updated pulp-dev for platform subproject (jason.dobies@redhat.com)
- Moved bin, srv, and test under platform (jason.dobies@redhat.com)
- Moved etc and src under platform subproject (jason.dobies@redhat.com)

* Fri Jun 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.295-1
- bump to gofer 0.69. (jortel@redhat.com)
- Add support for linking rpms units referenced with in a errata
  (pkilambi@redhat.com)
- Automatic commit of package [gofer] minor release [0.69-1].
  (jortel@redhat.com)
- Copying comps_util.py from pulp.server to pulp.yum_plugin so YumImporter may
  use this (jmatthews@redhat.com)
- YumImporter: test data for a simple repo with no comps (jmatthews@redhat.com)
- Added a warning in pulp-dev for when a dir exists but we expected it to be a
  symlink (jmatthews@redhat.com)
- Added unit copy extension to the RPM (jason.dobies@redhat.com)
- YumImporter/YumDistributor update unit tests to configure logger and redirect
  output from console to log file (jmatthews@redhat.com)
* Mon Jun 04 2012 Jeff Ortel <jortel@redhat.com> 0.0.294-1
- updated copyright information (jason.connor@gmail.com)
- Hide the auth ca cert, just show if one is present (jason.dobies@redhat.com)
- Changed triggers for consistency across the UI (jason.dobies@redhat.com)
- consumer cli extension for bind, unbind and minor re-structuring of
  consumerid function (skarmark@redhat.com)
- Changing order of consumer history result and removing unwanted _id
  (skarmark@redhat.com)
- removing consumer id validation from consumer history querying to allow
  querying for unregistered consumer as well (skarmark@redhat.com)
- Fixing unbind client extension error (skarmark@redhat.com)
- Update .gitignore to ignore test coverage output files (jmatthews@redhat.com)
- YumImporter:  Change 'fileName' to 'filename' for drpm (jmatthews@redhat.com)
- added deprecated notice to doctring (jason.connor@gmail.com)
- Fixed async response handling (jason.dobies@redhat.com)
- YumDistributor:  Added check to see if createrepo pid is running before
  canceling (jmatthews@redhat.com)
- YumDistributor: continue to debug errors from running with jenkins
  (jmatthews@redhat.com)
- Python 2.4 compatibility change for determining if Iterable
  (jmatthews@redhat.com)
- YumDistributor, debugging intermittent test failure when run from jenkins
  (jmatthews@redhat.com)
- YumImporter:  removed filename from srpm unit key (jmatthews@redhat.com)
- Fix for rhel5 unit tests, collections.Iterable doesn't exist
  (jmatthews@redhat.com)
- Fixed to use correct link call (jason.dobies@redhat.com)
- Revert "idempotent misspelled" (jason.connor@gmail.com)
- Revert "removed not_implemented() controllers" (jason.connor@gmail.com)
- Revert "removed unnecessary quotes around controller class names"
  (jason.connor@gmail.com)
- Revert "added _href fields to resources in repositories collection"
  (jason.connor@gmail.com)
- Revert "added _href field to new created repository" (jason.connor@gmail.com)
- Revert "added _href for repo resources" (jason.connor@gmail.com)
- added _href for repo resources (jason.connor@gmail.com)
- added _href field to new created repository (jason.connor@gmail.com)
- added _href fields to resources in repositories collection
  (jason.connor@gmail.com)
- changed sync overrides to a keyword argument (jason.connor@gmail.com)
- removed unnecessary quotes around controller class names
  (jason.connor@gmail.com)
- removed not_implemented() controllers (jason.connor@gmail.com)
- idempotent misspelled (jason.connor@gmail.com)
- changed task lookups to use new task_queue factory instead of accessing it
  via the coordinator (jason.connor@gmail.com)
- 827221 - Added individual resource GET methods and hrefs to resources
  (jason.dobies@redhat.com)
- 827220 - Removed old error_handler directives (jason.dobies@redhat.com)
- YumDistributor:  cancel_publish implementation and unit tests
  (jmatthews@redhat.com)
- Test data for simulating a long running createrepo process
  (jmatthews@redhat.com)
- added cleanup of mocked-out factory functions (jason.connor@gmail.com)
- fixed consumer controller entry (jason.connor@gmail.com)
- Delete the upload request if its rejected (jason.dobies@redhat.com)
- fix relativepath of the rpm during upload (pkilambi@redhat.com)
- Updated user guide for 1.1 (jason.dobies@redhat.com)
- utilized new factory access to move complete lifecycle callback out of
  scheduler class to a stand-alone function (jason.connor@gmail.com)
- changed tests to reflect changes in scheduler (jason.connor@gmail.com)
- remoced collection instance from scheduler as well (jason.connor@gmail.com)
- while I was at it I eliminated the task resource collection as state as well
  and instead use the get_collection factory method that is a part of every
  Model class (jason.connor@gmail.com)
- changed unit tests to reflect changes in coordinator (jason.connor@gmail.com)
- changed initialization of scheduler and coordinator to reflect changes in
  constructors (jason.connor@gmail.com)
- removed task queue as internal state and instead access it through the
  dispatch factory (jason.connor@gmail.com)
- added task queue factory function and updated the return types of the factory
  functions while I was at it (jason.connor@gmail.com)
- updated unittests to reflect changes in scheduler (jason.connor@gmail.com)
- removed the coordinator as state and instead use the factory to access it
  (jason.connor@gmail.com)
- removed unused imports (jason.connor@gmail.com)
- removed unused import (jason.connor@gmail.com)
- moved all imports into initialization methods to avoid circulary imports this
  will allow the different modules of the dispatch package to access each other
  via the factory in order keep the amount of state (read: references to each
  other) to a minimum (jason.connor@gmail.com)
- added super setup/teardown of old mocked async to keep clean happy
  (jason.connor@gmail.com)
- cleaned up imports and future proofed json_util import
  (jason.connor@gmail.com)
- moved exception handling into loop for better reporting
  (jason.connor@gmail.com)
- change mkdir to makedirs for better parental supervision
  (jason.connor@gmail.com)
- Added handling for async responses when importing units
  (jason.dobies@redhat.com)
- Added UG for repo tasks (jason.dobies@redhat.com)
- Added UG section for describing postponed and rejected tasks
  (jason.dobies@redhat.com)
- Fixed incongruences in the sync user guide (jason.dobies@redhat.com)
- Added user guide entry for repo publish (jason.dobies@redhat.com)
- User guide for package upload (jason.dobies@redhat.com)
- remove filename from rpm unit key (pkilambi@redhat.com)
- Cleanup for the consumer packages section of the user guide
  (jason.dobies@redhat.com)
- Corrected handling/display for operations postponed by the coordinator
  (jason.dobies@redhat.com)
- Refactored out bool conversion so it can be used directly
  (jason.dobies@redhat.com)
- Added publish schedule support to the RPM CLI extensions
  (jason.dobies@redhat.com)
- Added direct publish support (jason.dobies@redhat.com)
- Added enabled/disabled support for all RPM extensions
  (jason.dobies@redhat.com)

* Fri May 25 2012 Jeff Ortel <jortel@redhat.com> 0.0.293-1
- Fix .spec for moving agent handlers. (jortel@redhat.com)
- Add comments with Config usage and examples. (jortel@redhat.com)

* Fri May 25 2012 Jeff Ortel <jortel@redhat.com> 0.0.292-1
- Better section filtering in gc_config. (jortel@redhat.com)
- YumImporter:  Added cancel sync (jmatthews@redhat.com)
- Implement upload_unit in yum importer (pkilambi@redhat.com)
- Final code clean up and tweaks (jason.dobies@redhat.com)
- Removed delete call from import, it doesn't belong there
  (jason.dobies@redhat.com)
- Don't return the report, it will be stuffed into history instead
  (jason.dobies@redhat.com)
- Added upload extension to the RPM (jason.dobies@redhat.com)
- Added filename to unit key temporarily (jason.dobies@redhat.com)
- Wrong call to import the unit (jason.dobies@redhat.com)
- Default the relative URL to repo ID for feedless repos
  (jason.dobies@redhat.com)
- Turned on the import step (jason.dobies@redhat.com)
- admin consumer bind and unbind extension (skarmark@redhat.com)
- Fix agent unregistered(), delete of consumer cert. (jortel@redhat.com)
- Rename (distributor) handler role to: (bind). (jortel@redhat.com)
- Move GC agent handlers to: /etc/pulp/agent & /usr/lib/pulp/agent.
  (jortel@redhat.com)
- Fix epydoc typos. (jortel@redhat.com)
- Initial working version of the upload CLI (jason.dobies@redhat.com)
- Remove default {} from report signatures; fix epydoc. (jortel@redhat.com)
- Add linux system handler to git. (jortel@redhat.com)
- Add a ton of missing GC packages and tests. (jortel@redhat.com)
- Fixing syntax error at the end of params in the api doc (skarmark@redhat.com)
- GC agent: add (system) role and refactor reboot(). (jortel@redhat.com)
- Fix title for consistency (jason.dobies@redhat.com)
- Another minor rendering fix for consumer history api doc (3rd time's the
  charm) (skarmark@redhat.com)
- Minor rendering fix for consumer history api doc (skarmark@redhat.com)
- updated docstring (jason.connor@gmail.com)
- Fixing title of consumer history api doc (skarmark@redhat.com)
- In GC agent, add initial mapping for package group installs.
  (jortel@redhat.com)
- Update epydocs. (jortel@redhat.com)
- Refactor Handler interface for clarity.  Fix bind handler using
  ConsumerConfig. (jortel@redhat.com)

* Thu May 24 2012 Jeff Ortel <jortel@redhat.com> 0.0.291-1
- yum_importer proxy fix to force config values to be in ascii
  (jmatthews@redhat.com)
- minor fix in consumer history retrieval (skarmark@redhat.com)
- converting consumer history query call to GET from POST (skarmark@redhat.com)
- added skeleton Profiler loading support (jason.connor@gmail.com)
- added skeleton Profiler class (jason.connor@gmail.com)
- Added sample response for retrieving a single consumer api
  (skarmark@redhat.com)
- Removing importer retrieval doc pasted by mistake in consumer docs
  (skarmark@redhat.com)
- For consistency, use repo-id in all cases (jason.dobies@redhat.com)
- updating display_name argument coming from client extension to display-name
  and updating argument to MissingResource exception (skarmark@redhat.com)
- removing (optional) from cli arguments (skarmark@redhat.com)
- Add the repo to the upload_unit API (jason.dobies@redhat.com)
- Fixing minor errors in consumer extensions and correcting rendering methods
  for failure cases (skarmark@redhat.com)
- Remove unused files from gc_client/. (jortel@redhat.com)
- Factor out references to: credentials/config in: gc_client/consumer and
  gc_client/lib. (jortel@redhat.com)
- Added call report example (jason.dobies@redhat.com)
- Added client upload manager and unit tests (jason.dobies@redhat.com)
- added tags to delete operations (jason.connor@gmail.com)
- changed field names and provided sample request (jason.connor@gmail.com)
- remove unicode indicators from sample response (jason.connor@gmail.com)
- changed content_type to content_type_id and content_id to unit_id for
  consistency across apis (jason.connor@gmail.com)
- moved key checking to manager (jason.connor@gmail.com)
- updated copyright (jason.connor@gmail.com)
- changed new schedules to always have their "first run" in the future
  (jason.connor@gmail.com)
- moved schedule validation out of db model (jason.connor@gmail.com)
- much more comprehensive parameter validation in for additions and updates
  (jason.connor@gmail.com)
- added unsupported value exception class (jason.connor@gmail.com)
- Using consumer config loaded by launcher instead of using hardcoded config in
  ConsumerBundle and ConsumerConfig classes (skarmark@redhat.com)
- move heartbeat and registration detection to GC agent (jortel@redhat.com)
- Add rpm admin consumer extension unit test. (jortel@redhat.com)
- Add package install UG pages. (jortel@redhat.com)
- combining all consumer history record and query invalid values together to
  raise an exception with a list of all invalid values instead of separate
  exceptions for each invalid value (skarmark@redhat.com)
- Changing consumer history query extension arguments from '_' to '-' according
  to v2 coding standard; updating input to MissingResource exceptions
  (skarmark@redhat.com)
- support veriety of input on construction. (jortel@redhat.com)
- Fixed incorrect lookup for display-name in update (jason.dobies@redhat.com)
- adding new fields to publish report (pkilambi@redhat.com)
- Display remaining runs for a schedule (jason.dobies@redhat.com)
- Added middleware support for arg parsing exception (jason.dobies@redhat.com)
- Add strict vs. non-strict flag on config graph. (jortel@redhat.com)
- Add dict-like configuration object and updated validation.
  (jortel@redhat.com)
- Added repo sync schedule user guide documentation (jason.dobies@redhat.com)
- Load content handlers on gofer plugin loading. (jortel@redhat.com)
- validation placeholders (jason.connor@gmail.com)
- couple of tweaks (jason.connor@gmail.com)
- orphan rest api docs (jason.connor@gmail.com)
- added schedule validation for updates (jason.connor@gmail.com)
- moved scheduler constants back into scheduler module and absolutely no one
  else uses them... (jason.connor@gmail.com)
- added missing coordinator reponses for updated and delete sync/publish
  schedules (jason.connor@gmail.com)
- bz 798281 add status call to service pulp-cds (whayutin@redhat.com)
- 821041 - packagegroup install of custom groups seems to be failing
  (jmatthews@redhat.com)
- Flushed out date/time conventions in the user guide (jason.dobies@redhat.com)
- Added cleaner message when no schedules are present (jason.dobies@redhat.com)
- mod auth token prototype (pkilambi@redhat.com)
- Added generic schedule commands and repo sync schedule usage of them
  (jason.dobies@redhat.com)
- re-captured isodate parsing and raising InvalidValue error instead for proper
  handling in the middleware (jason.connor@gmail.com)
- re-introduced v1 task queue feature of caching completed tasks
  (jason.connor@gmail.com)
- added orphan manager unittests (jason.connor@gmail.com)

* Fri May 18 2012 Jeff Ortel <jortel@redhat.com> 0.0.290-1
- Fix broken GC package install CLI. (jortel@redhat.com)
- Utilities for handling CLI argument conventions (jason.dobies@redhat.com)
- removing checks to support no pulishing (pkilambi@redhat.com)
- GC bind: hook up handler and repolib. (jortel@redhat.com)
- Upgraded okaara to 1.0.18 (jason.dobies@redhat.com)
- Updated base command class to use okaara's option description prefixing
  (jason.dobies@redhat.com)
- temp disablement of task archival task until race condition can be resolved
  (jason.connor@gmail.com)
- Disable all tasks view by default (enabled in .conf)
  (jason.dobies@redhat.com)
- orphan manager unit tests (jason.connor@gmail.com)
- fixed missing .items() while iterating over dictionary
  (jason.connor@gmail.com)
- removed unused options argument to collection constructor which just went
  away in pymongo 2.2 anyway (jason.connor@gmail.com)
- place running tasks before waiting tasks when returning all tasks to maintain
  a closer representation of the enqueue time total ordering on the task set
  (jason.connor@gmail.com)
- added archive to all delete requests (jason.connor@gmail.com)
- added auth_required decorators to all orphan controllers
  (jason.connor@gmail.com)
- added mac special dir to ignore (jason.connor@gmail.com)
- moved archival test to task queue tests (jason.connor@gmail.com)
- removed archival from task tests (jason.connor@gmail.com)
- moved call archival from task into task queue to prevent race condition in
  task queries (jason.connor@gmail.com)
- converted to _id for unit ids (jason.connor@gmail.com)
- initial implementation of delete orphans action (jason.connor@gmail.com)
- utilizing changed field names (jason.connor@gmail.com)
- changed fields to more managable content_type and content_id
  (jason.connor@gmail.com)
- initial implementation of orphan collections and resources
  (jason.connor@gmail.com)
- added get_orphan method (jason.connor@gmail.com)
- added orphan manager to factory (jason.connor@gmail.com)
- added comment (jason.connor@gmail.com)
- Add yum repo (bind) handler; more bind plumbing. (jortel@redhat.com)
- Update mock distributor bind payload. (jortel@redhat.com)
- Updated bind (GET) to include distributor payload. (jortel@redhat.com)
- updating payload info (pkilambi@redhat.com)
- Last docs tweak for today, I swear (jason.dobies@redhat.com)
- Added background functionality to repo sync run (jason.dobies@redhat.com)
- fix for updating the state when a distribution symlink step fails
  (pkilambi@redhat.com)
- Consumer history manager layer, controller and adminclient extension
  (skarmark@redhat.com)
- Added a status call to the repo to see if it is synccing
  (jason.dobies@redhat.com)
- Added ability to resume tracking an in progress sync and refactored extension
  to separate sync running and scheduling commands (jason.dobies@redhat.com)
- Fixed tags lookup from query parameters (jason.dobies@redhat.com)
- Tasks extension unit tests and code cleanup (jason.dobies@redhat.com)
- Update GC content handler framework to support bind(). (jortel@redhat.com)
- Implementation of task list, details, and delete commands
  (jason.dobies@redhat.com)
- Flushed out client-side task API (jason.dobies@redhat.com)
- Refactored response object structure in client API (jason.dobies@redhat.com)
- Updated 404 exception handling to handle new data dict format
  (jason.dobies@redhat.com)
- moved log file to get full path into message (jason.connor@gmail.com)
- implementation of orphan manager (jason.connor@gmail.com)
- fixed some spelling errors (jason.connor@gmail.com)
- Move GC agent lib under (lib); Add pulp bindings to agent.
  (jortel@redhat.com)
- Update RPM handler and gofer plugin for GC agent move to gc_client.
  (jortel@redhat.com)
- Update pulp.spec for GC agent moved to gc_client. (jortel@redhat.com)
- Move GC agent under gc_client. (jortel@redhat.com)
- Add bindings query by consumer/repo in API; Add binding query to GC client
  API. (jortel@redhat.com)
- adding host_urls and renaming few keys in payload (pkilambi@redhat.com)
- minor changes to payload structure (pkilambi@redhat.com)
- implement the consumer payload in distributor (pkilambi@redhat.com)
- Fix GC agent & rpm handler reboot logic; support update ALL.
  (jortel@redhat.com)
- Ported v1 protected repositories into the v2 documentation
  (jason.dobies@redhat.com)
* Fri May 11 2012 Jeff Ortel <jortel@redhat.com> 0.0.289-1
- Updated to correct importer/distributor config values
  (jason.dobies@redhat.com)
- Corrected _ to - in the user guide (jason.dobies@redhat.com)
- Unit tests for unit copy (jason.dobies@redhat.com)
- Added gt, gte, lt, lte, after, and before functionality to unit copy
  (jason.dobies@redhat.com)
- Added unit copy API to client bindings (jason.dobies@redhat.com)
- fix test districutor to use mock (pkilambi@redhat.com)
- fix tests to use a mock object (pkilambi@redhat.com)
- Initial implementation of the unit copy extension (jason.dobies@redhat.com)
- Protected Repos: - support for writing consumer cert to specific location
  based on repo_auth.conf - update protected_repo_listings file - implement
  distributor_remove hook to clean up on repo delete (pkilambi@redhat.com)
- Renamed underscore CLI flags to use the hyphens convention
  (jason.dobies@redhat.com)
- added cross references for asynchronous call reports and the task dispatch
  api (jason.connor@gmail.com)
- initial placeholder for orphan manager (jason.connor@gmail.com)
- added dispatch to index (jason.connor@gmail.com)
- start of dispatch apis (jason.connor@gmail.com)

* Tue May 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.288-1
- 819589 - casting all kwarg keys to str (jason.connor@gmail.com)
- removed cast to timedelta from isodate.Duration (jason.connor@gmail.com)
- Consumer 'rpm' extension replaces generic 'content' extension when installed.
  (jortel@redhat.com)
- some json v python corrections and start of new section on iso8601
  (jason.connor@gmail.com)
- Add --no-commit to GC content extension. (jortel@redhat.com)
- Changed handling of http/https flags so they are only defaulted in create
  (jason.dobies@redhat.com)
- changed _do_request to allow multiple polls to be sent to task url
  (jason.connor@gmail.com)
- changed aynchronous support to only set success or failure if the task is
  actually running changed asynchronous support to guaruntee only 1 call into
  coordinator changed asynchronous support to allow multiple calls into
  controllers per unittest so long as set_success or set_failure is called
  before each asynchronous controller is called (jason.connor@gmail.com)
- Unit metadata is optional for unit import (jason.dobies@redhat.com)
- Create the necessary directories for content uploads
  (jason.dobies@redhat.com)
- convert the ssl certs queried from mongo to utf8 before passing to m2crypto
  (pkilambi@redhat.com)
- GC agent; enable authorization. (jortel@redhat.com)
- CallRequest(asynchronous=True); Simulate agent reply in GC consumer
  controller unit test. (jortel@redhat.com)
- make --importkeys a flag. (jortel@redhat.com)
- removed generic scheduled tag and added schedule resource tag
  (jason.connor@gmail.com)

* Thu May 03 2012 Jeff Ortel <jortel@redhat.com> 0.0.287-2
- move gc_client to client-lib. (jortel@redhat.com)

* Thu May 03 2012 Jeff Ortel <jortel@redhat.com> 0.0.287-1
- Support -n alias for GC content install CLI. (jortel@redhat.com)
- Add support for str|list|tuple tracebacks. (jortel@redhat.com)
- Enhanced gc & rpm content install CLI. (jortel@redhat.com)
- Better error handling in generic content install CLI. (jortel@redhat.com)
- Refactor admin cli to split generic content unit vs. rpm install.
  (jortel@redhat.com)
- YumImporter:  Fix for rhel5 issue with itertools.chain.from_iterable
  (jmatthews@redhat.com)
- Added REST APIs for content upload (jason.dobies@redhat.com)
- publish added to index (jason.connor@gmail.com)
- publish api documentation (jason.connor@gmail.com)
- corrected a number of typos (jason.connor@gmail.com)
- fixes to sync doc (jconnor@redhat.com)
- no longer recording duplicate reasons for postponed and rejected
  (jconnor@redhat.com)
- updated tags to use new resource_tag generation (jconnor@redhat.com)
- replaced spaces in resource types with underscores (jconnor@redhat.com)
- removed leading underscores for scheduled call object fields
  (jconnor@redhat.com)
- removed superfluous part of child path for sync/publish schedules
  (jconnor@redhat.com)
- fixed typo in docstring (jconnor@redhat.com)
- Render content install,update,uninstall results. (jortel@redhat.com)
- YumDistributor:  Update to remove http/https link if no longer set to True in
  config (jmatthews@redhat.com)
- convert the cert strings to utf-8 before passing to grinder; also fixed
  default sslverify value if not specified (pkilambi@redhat.com)
- Differentiate association owner for uploaded v. syncced units
  (jason.dobies@redhat.com)
- YumImporter:  First pass at handling sync of a protected repo
  (jmatthews@redhat.com)
- Added distribution support for repo units display (jason.dobies@redhat.com)
- Docs cleanup (jason.dobies@redhat.com)
- YumDistributor:  Fix for unicode relative_url validation
  (jmatthews@redhat.com)
- forgot to use $set, so I was completely overwriting the fields instead of
  just setting a sub-set of them (jason.connor@gmail.com)
- fixed too short underline (jason.connor@gmail.com)
- repo sync documentation (jason.connor@gmail.com)
- fixed up scheduled call serialization (jason.connor@gmail.com)
- added sync to index (jason.connor@gmail.com)
- changed all scheduled sync and publish controllers to use new serialization
  (jason.connor@gmail.com)
- added specific serialization for scheduled sync and publish
  (jason.connor@gmail.com)
- fixed comment typo (jason.connor@gmail.com)
- added more fields to call report (jason.connor@gmail.com)
- removed assumptions and generalized scheduled call object
  (jason.connor@gmail.com)
- added iso8601 interval to gloassary (jason.connor@gmail.com)
- added call report to glossary (jason.connor@gmail.com)
- Added publish progress support to sync status. (jason.dobies@redhat.com)
- Adding multiple content unit install support (skarmark@redhat.com)
- Ensure report contains 'details' on exceptoin as well. (jortel@redhat.com)
- Refactored out the progress report rendering (jason.dobies@redhat.com)
- client extension for a consumer content unit install (skarmark@redhat.com)
- Docs cleanup (jason.dobies@redhat.com)
- including http/https publish progress info in report (pkilambi@redhat.com)
- Implementation of v2 storage of uploaded files (jason.dobies@redhat.com)
- YumDistributor:  Implementation of 'http' publishing option
  (jmatthews@redhat.com)
- Added 'keys()' method to return a set of all keys available from the
  underlying dicts (jmatthews@redhat.com)
- YumImporter:  Made feed_url optional and ensure we invoke progress report for
  NOT_STARTED as first step (jmatthews@redhat.com)
- Client bindings for consumer content unit install (skarmark@redhat.com)
- updating doc strings to  include progress callback description
  (pkilambi@redhat.com)
- default progress arg to None (pkilambi@redhat.com)
- first pass at changes to support Yum Distributor publish progress reporting
  (pkilambi@redhat.com)
- Base unit addition/linking conduit (jason.dobies@redhat.com)
- Refactored out base unit add conduit support to better scope the upload
  conduit (jason.dobies@redhat.com)
- Adding consumer credential support from v1 to v2 (skarmark@redhat.com)
- Added ability to store consumer cert bundle for v2 consumers
  (skarmark@redhat.com)
- schedule creation using configured create_weight (jconnor@redhat.com)
- converted all tags to use new generic tags functions (jconnor@redhat.com)
- adding tag generating functions to common (jconnor@redhat.com)
- changed scheduled sync/publish to use controller (jason.connor@gmail.com)
- re-implementation of sync and publish schedule controllers using schedule
  manager (jason.connor@gmail.com)
- added schedule_manager to managers factory (jason.connor@gmail.com)
- fixed override config keyword argument publish schedule update fixed schedule
  update keyword arguments (jason.connor@gmail.com)
- added return of schedule_id to publish create (jason.connor@gmail.com)
- fixed schedule update keyword arguments fixed repo importer manager
  constructor arguments (jason.connor@gmail.com)
- converting _id to string in schedule report (jason.connor@gmail.com)
- removed _id that needed more processing, added failure_threshold
  (jason.connor@gmail.com)
- fixed check for schedule (jason.connor@gmail.com)
- added required flag for dict validation (jconnor@redhat.com)
- add/remove/list publish schedule functionality (jconnor@redhat.com)
- add/remove/list sync schedule functionality (jconnor@redhat.com)
- finished implementation of scheduled sync/publish cud operations
  (jconnor@redhat.com)
- removed old import (jconnor@redhat.com)
- schedule managers skeletons (jconnor@redhat.com)
- sync schedule method place holders (jconnor@redhat.com)
- sync schedule collection list (jconnor@redhat.com)
- Add TODO: in consumer controller. (jortel@redhat.com)
- Initial add of repo sync 'schedule' subsection. (jortel@redhat.com)
- Added importer API for upload and manager to call into it
  (jason.dobies@redhat.com)
- Updated epydocs. (jortel@redhat.com)
- YumImporter:  implementation for import_units (jmatthews@redhat.com)
- YumDistributor:  Reduce logging output (jmatthews@redhat.com)
- Correct API docs. (jortel@redhat.com)
