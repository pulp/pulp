# Copyright (c) 2010-2012 Red Hat, Inc.
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
Version: 2.3.0
Release: 0.2.alpha%{?dist}
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
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/server
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/server/plugins.conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/agent
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/agent/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/vhosts80
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
mkdir -p %{buildroot}/%{_var}/log/%{name}/
mkdir -p %{buildroot}/%{_libdir}/gofer/plugins
mkdir -p %{buildroot}/%{_bindir}

# Configuration
cp -R etc/pulp/* %{buildroot}/%{_sysconfdir}/%{name}

# Apache Configuration
%if 0%{?fedora} >= 18
cp etc/httpd/conf.d/pulp_f18.conf %{buildroot}/%{_sysconfdir}/httpd/conf.d/pulp.conf
%else
cp etc/httpd/conf.d/pulp.conf %{buildroot}/%{_sysconfdir}/httpd/conf.d/
%endif

# Pulp Web Services
cp -R srv %{buildroot}

# PKI
cp etc/pki/pulp/* %{buildroot}/%{_sysconfdir}/pki/%{name}

# Agent
rm -rf %{buildroot}/%{python_sitelib}/%{name}/agent/gofer
cp etc/gofer/plugins/pulpplugin.conf %{buildroot}/%{_sysconfdir}/gofer/plugins
cp -R src/pulp/agent/gofer/pulpplugin.py %{buildroot}/%{_libdir}/gofer/plugins
ln -s %{_sysconfdir}/rc.d/init.d/goferd %{buildroot}/%{_sysconfdir}/rc.d/init.d/pulp-agent

# Tools
cp bin/* %{buildroot}/%{_bindir}

# Ghost
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer/consumer-cert.pem

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


# define required pulp platform version.
%global pulp_version %{version}


# ---- Server ------------------------------------------------------------------

%package server
Summary: The pulp platform server
Group: Development/Languages
Requires: python-%{name}-common = %{pulp_version}
Requires: pymongo >= 2.1.1
Requires: python-setuptools
Requires: python-webpy
Requires: python-okaara >= 1.0.32
Requires: python-oauth2 >= 1.5.170-2.pulp
Requires: python-httplib2
Requires: python-isodate >= 0.5.0-1.pulp
Requires: python-BeautifulSoup
Requires: python-qpid
Requires: python-nectar >= 1.0.0
Requires: httpd
Requires: mod_ssl
Requires: openssl
Requires: nss-tools
Requires: python-ldap
Requires: python-gofer >= 0.76
Requires: crontabs
Requires: acl
Requires: mod_wsgi >= 3.4-1.pulp
Requires: mongodb
Requires: mongodb-server
Requires: qpid-cpp-server
Requires: m2crypto >= 0.21.1.pulp-7
Requires: genisoimage
# RHEL6 ONLY
%if 0%{?rhel} == 6
Requires: nss >= 3.12.9
%endif
Obsoletes: pulp

%description server
Pulp provides replication, access, and accounting for software repositories.

%files server
# root
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/server/
%{python_sitelib}/%{name}/plugins/
%config(noreplace) %{_sysconfdir}/%{name}/server.conf
%config(noreplace) %{_sysconfdir}/%{name}/logging/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%dir %{_sysconfdir}/%{name}/vhosts80
%dir %{_sysconfdir}/%{name}/server
%dir %{_sysconfdir}/%{name}/server/plugins.conf.d
%{_bindir}/pulp-manage-db
%{_bindir}/pulp-qpid-ssl-cfg
%{_bindir}/pulp-v1-upgrade
%{_bindir}/pulp-v1-upgrade-selinux
%{_bindir}/pulp-v1-upgrade-publish
# apache
%defattr(-,apache,apache,-)
%dir /srv/%{name}
%dir %{_var}/log/%{name}
%dir %{_sysconfdir}/pki/%{name}
%{_var}/lib/%{name}/
%{_usr}/lib/%{name}/plugins/distributors
%{_usr}/lib/%{name}/plugins/importers
%{_usr}/lib/%{name}/plugins/profilers
%{_usr}/lib/%{name}/plugins/types
%{_sysconfdir}/pki/%{name}/ca.key
%{_sysconfdir}/pki/%{name}/ca.crt
/srv/%{name}/webservices.wsgi
%doc

%post server
SECTION="oauth"
MATCH_SECTION="/^\[$SECTION\]$/"
KEY="oauth_key:"
SECRET="oauth_secret:"
function generate() {
  echo `< /dev/urandom tr -dc A-Z0-9 | head -c8`
}
sed -e "$MATCH_SECTION,/^$/s/^$KEY$/$KEY $(generate)/" \
    -e "$MATCH_SECTION,/^$/s/^$SECRET$/$SECRET $(generate)/" \
    -i %{_sysconfdir}/%{name}/server.conf


# ---- Common ------------------------------------------------------------------

%package -n python-pulp-common
Summary: Pulp common python packages
Group: Development/Languages
Obsoletes: pulp-common
Requires: python-isodate >= 0.5.0-1.pulp
Requires: python-iniparse

%description -n python-pulp-common
A collection of components that are common between the pulp server and client.

%files -n python-pulp-common
%defattr(-,root,root,-)
%dir %{_usr}/lib/%{name}
%dir %{python_sitelib}/%{name}
%{python_sitelib}/%{name}/__init__.*
%{python_sitelib}/%{name}/common/
%doc


# ---- Client Bindings ---------------------------------------------------------

%package -n python-pulp-bindings
Summary: Pulp REST bindings for python
Group: Development/Languages
Requires: python-%{name}-common = %{pulp_version}
Requires: m2crypto

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
Requires: m2crypto
Requires: python-%{name}-common = %{pulp_version}
Requires: python-okaara >= 1.0.32
Requires: python-isodate >= 0.5.0-1.pulp
Requires: python-setuptools
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
Requires: python-%{name}-common = %{pulp_version}

%description -n python-pulp-agent-lib
A framework for loading agent handlers that provide support
for content, bind and system specific operations.

%files -n python-pulp-agent-lib
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/agent/
%dir %{_sysconfdir}/%{name}/agent
%dir %{_sysconfdir}/%{name}/agent/conf.d
%dir %{_usr}/lib/%{name}/agent
%doc


# ---- Admin Client (CLI) ------------------------------------------------------

%package admin-client
Summary: Admin tool to administer the pulp server
Group: Development/Languages
Requires: python-okaara >= 1.0.32
Requires: python-%{name}-common = %{pulp_version}
Requires: python-%{name}-bindings = %{pulp_version}
Requires: python-%{name}-client-lib = %{pulp_version}
Requires: %{name}-builtins-admin-extensions = %{pulp_version}
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
Requires: python-%{name}-common = %{pulp_version}
Requires: python-%{name}-bindings = %{pulp_version}
Requires: python-%{name}-client-lib = %{pulp_version}
Requires: %{name}-builtins-consumer-extensions = %{pulp_version}
Obsoletes: pulp-consumer

%description consumer-client
A tool used to administer a pulp consumer.

%files consumer-client
%defattr(-,root,root,-)
%dir %{_sysconfdir}/%{name}/consumer
%dir %{_sysconfdir}/%{name}/consumer/conf.d
%dir %{_sysconfdir}/pki/%{name}/consumer/
%dir %{_usr}/lib/%{name}/consumer/extensions/
%config(noreplace) %{_sysconfdir}/%{name}/consumer/consumer.conf
%{_bindir}/%{name}-consumer
%ghost %{_sysconfdir}/pki/%{name}/consumer/consumer-cert.pem
%doc


# ---- Agent -------------------------------------------------------------------

%package agent
Summary: The Pulp agent
Group: Development/Languages
Requires: python-%{name}-bindings = %{pulp_version}
Requires: python-%{name}-agent-lib = %{pulp_version}
Requires: %{name}-consumer-client = %{pulp_version}
Requires: gofer >= 0.76

%description agent
The pulp agent, used to provide remote command & control and
scheduled actions such as reporting installed content profiles
on a defined interval.

%files agent
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/%{name}/agent/agent.conf
%{_sysconfdir}/gofer/plugins/pulpplugin.conf
%{_libdir}/gofer/plugins/pulpplugin.*
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
Obsoletes: pulp-selinux-server

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
* Thu Aug 01 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.2.alpha
- Pulp rebuild

* Thu Aug 01 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.1.alpha
- 976561 - added and explicit pool size for the socket "pool" added a new
  decorator around the query methods that calls end_request in order to manage
  the sockets automagically (jason.connor@gmail.com)
- 981736 - when a sync fails, pulp-admin's exit code is now 1 instead of 0.
  (mhrivnak@redhat.com)
- 977948 - fix distributor updating during node sync. (jortel@redhat.com)
- purge changelog
- 973402 - Handle CallReport.progress with value of {} or None.
  (jortel@redhat.com)
- 927216  - remove reference to CDS in the server.conf security section.
  (jortel@redhat.com)
- 928413 - fix query used to determine of bind has pending actions.
  (jortel@redhat.com)
- 970741 - Upgraded nectar for error_msg support (jason.dobies@redhat.com)
- 968012 - Replaced grinder logging config with nectar logging config
  (jason.dobies@redhat.com)

* Tue Jun 04 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.16.alpha
- 947445 - allowing consumer ids to allow dots (skarmark@redhat.com)
- 906420 - update storing of resources used by each task in the taskqueue to
  allow dots in the repo id (skarmark@redhat.com)
- 906420 - update storing of resources used by each task in the taskqueue to
  allow dots in the repo id (skarmark@redhat.com)
- 968543 - remove conditional in pulp_version macro. (jortel@redhat.com)
- 927033 - added missing consumer group associate and unassociate webservices
  tests (skarmark@redhat.com)
- 927033 - updating consumer group associate and unassociate calls to return a
  list of all consumers similar to repo group membership instead of just those
  who fulfil the search criteria, updating unit tests and documentation
  (skarmark@redhat.com)
- 965743 - Changed help text to reflect the actual units
  (jason.dobies@redhat.com)
- 963823 - Made the feed SSL options group name a bit more accurate
  (jason.dobies@redhat.com)

* Thu May 30 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.15.alpha
- 913670 - fix consumer group bind/unbind. (jortel@redhat.com)
- 878234 - use correct method on coordinator. (jortel@redhat.com)

* Fri May 24 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.14.alpha
- 966202 - Change the config options to use the optional parsers.
  (jason.dobies@redhat.com)

* Thu May 23 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.13.alpha
- Pulp rebuild

* Thu May 23 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.12.alpha
- Pulp rebuild

* Tue May 21 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.11.alpha
- 923796 - Changed example to not cite a specific command
  (jason.dobies@redhat.com)

* Mon May 20 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.10.alpha
- Pulp rebuild

* Mon May 20 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.9.alpha
- Pulp rebuild

* Fri May 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.8.alpha
- Pulp rebuild

* Fri May 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.7.alpha
- Pulp rebuild

* Fri May 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.6.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.5.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.4.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.3.alpha
- 952775 - Fixed broken unit filter application when sorted by association
  (jason.dobies@redhat.com)
- 913171 - using get method instead of dict lookup (skarmark@redhat.com)
- 915473 - fixing login api to return a json document with key and certificate
  (skarmark@redhat.com)
- 913171 - fixed repo details to display list of actual schedules instead of
  schedule ids and unit tests (skarmark@redhat.com)
- 957890 - removing duplicate units in case when consumer is bound to copies of
  same repo (skarmark@redhat.com)
- 957890 - fixed duplicate unit listing in the applicability report and
  performance improvement fix to avoid loading unnecessary units
  (skarmark@redhat.com)
- 954038 - updating applicability api to send unit ids instead of translated
  plugin unit objects to profilers and fixing a couple of performance issues
  (skarmark@redhat.com)
- 924778 - Added hook for a subclass to manipulate the file bundle list after
  the metadata is generated (jason.dobies@redhat.com)
- 916729 - Fixed auth failures to return JSON documents containing a
  programmatic error code and added client-side exception middleware support
  for displaying the proper user message based on the error.
  (jason.dobies@redhat.com)
- 887000 - removed dispatch lookups in sync to determine canceled state
  (jason.connor@gmail.com)
- 927244 - unit association log blacklist criteria (jason.connor@gmail.com)
- 903414 - handle malformed queued calls (jason.connor@gmail.com)
- 927216 - remove CDS section from server.conf. (jortel@redhat.com)

* Fri Apr 19 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.2.alpha
- 953665 - added ability for copy commands to specify the fields of their units
  that should be fetched, so as to avoid loading the entirety of every unit in
  the source repository into RAM. Also added the ability to provide a custom
  "override_config" based on CLI options. (mhrivnak@redhat.com)
- 952310 - support file:// urls. (jortel@redhat.com)
- 949174 - Use a single boolean setting for whether the downloaders should
  validate SSL hosts. (rbarlow@redhat.com)

* Fri Apr 12 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.1.alpha
- 950632 - added unit_id search index on the repo_content_units collection
  (jason.connor@gmail.com)
- 928081 - Take note of HTTP status codes when downloading files.
  (rbarlow@redhat.com)
- 947927 - This call should support both the homogeneous and heterogeneous
  cases (jason.dobies@redhat.com)
- 928509 - Platform changes to support override config in applicability
  (jason.dobies@redhat.com)
- 949186 - Removed the curl TIMEOUT setting and replaced it with a low speed
  limit. (rbarlow@redhat.com)
- 928087 - serialized call request replaced in archival with string
  representation of the call request (jason.connor@gmail.com)
- 924327 - Make sure to run the groups/categories upgrades in the aggregate
  (jason.dobies@redhat.com)
- 918160 - changed --summary flag to *only* display the  summary
  (jason.connor@gmail.com)
- 916794 - 918160 - 920792 - new generator approach to orphan management to
  keep us from stomping on memory (jason.connor@gmail.com)
- 923402 - Clarifications to the help text in logging config files
  (jason.dobies@redhat.com)
- 923402 - Reduce logging level from DEBUG to INFO (jason.dobies@redhat.com)
- 923406 - fixing typo in repo copy bindings causing recursive copy to never
  run (skarmark@redhat.com)
- 922214 - adding selinux context for all files under /srv/pulp instead of
  individual files (skarmark@redhat.com)
- 919155 - Added better test assertions (jason.dobies@redhat.com)
- 919155 - Added handling for connection refused errors
  (jason.dobies@redhat.com)
- 918782 - render warning messages as normal colored text. (jortel@redhat.com)
- 911166 - Use pulp_version macro for consistency and conditional requires on
  both version and release for pre-release packages only. (jortel@redhat.com)
- 908934 - Fix /etc/pki/pulp and /etc/pki/pulp/consumer ownership.
  (jortel@redhat.com)
- 918600 - _content_type_id wasn't being set for erratum and drpm
  (jason.dobies@redhat.com)

* Mon Mar 04 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.19.alpha
- 855053 - repository unit counts are now tracked per-unit-type. Also wrote a
  migration that will convert previously-created repositories to have the new
  style of unit counts. (mhrivnak@redhat.com)
- 902514 - removing NameVirtualHost because we weren't using it, and adding one
  authoritative <VirtualHost *:80> block for all plugins to use, since apache
  will only let us use one. (mhrivnak@redhat.com)
- 873782 - added non-authenticate status resource at /v2/status/
  (jason.connor@gmail.com)
- 860089 - added ability to filter tasks using ?id=...&id=...
  (jason.connor@gmail.com)

* Tue Feb 26 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.18.alpha
- Pulp rebuild

* Tue Feb 26 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.17.alpha
- 915795 - Fix logging import statemet in pulp-manage-db. (rbarlow@redhat.com)

* Mon Feb 25 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.16.alpha
- Pulp rebuild

* Mon Feb 25 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.15.alpha
- 908676 - adding pulp-v1-upgrade-selinux script to enable new selinux policy
  and relabel filesystem after v1 upgrade (skarmark@redhat.com)
- 908676 - adding obsoletes back again for pulp-selinux-server since pulp v1
  has a dependency on this package (skarmark@redhat.com)

* Fri Feb 22 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.14.alpha
- 909493 - adding a separate apache2.4 compatible pulp apache conf file for F18
  (skarmark@redhat.com)
- 909493 - adding a different httpd2.4 compatible pulp config file for f18
  build (skarmark@redhat.com)
- 908676 - make pulp-selinux conflict with pulp-selinux-server instead of
  obsoleting pulp-selinux-server (skarmark@redhat.com)

* Thu Feb 21 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.13.alpha
- 913205 - Removed config options if they aren't relevant
  (jason.dobies@redhat.com)
- 913205 - Corrected storage of feed certificates on upgrade
  (jason.dobies@redhat.com)

* Tue Feb 19 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.12.alpha
- Pulp rebuild

* Tue Feb 19 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.11.alpha
- 910419 - added *args and **kwargs to OPTIONS signature to handle regular
  expressions in the url path (jason.connor@gmail.com)

* Thu Feb 14 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.10.alpha
- Pulp rebuild

* Thu Feb 14 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.9.alpha
- 906426 - Create the upload directory if someone deletes it
  (jason.dobies@redhat.com)

* Wed Feb 13 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.8.alpha
- Pulp rebuild

* Wed Feb 13 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.7.alpha
- Pulp rebuild

* Wed Feb 13 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.6.alpha
- 910540 - fix file overlaps in platform packaging. (jortel@redhat.com)

* Tue Feb 12 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.5.alpha
- Pulp rebuild

* Tue Feb 12 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.4.alpha
- 908510 - Corrected imports to use compat layer (jason.dobies@redhat.com)
- 908082 - updated SSLRenegBufferSize in apache config to 1MB
  (skarmark@redhat.com)
- 903797 - Corrected docstring for import_units (jason.dobies@redhat.com)
- 905588 - Adding "puppet_module" as an example unit type. This should not
  become a list of every possible unit type, but it's not unreasonable here to
  include some mention of puppet modules. (mhrivnak@redhat.com)

* Tue Feb 05 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.3.alpha
- Pulp rebuild

* Tue Feb 05 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.2.alpha
- 880780 - Added config parsing exception to convey more information in the
  event the conf file isn't valid JSON (jason.dobies@redhat.com)
- 905548 - fix handler loading; imp.load_source() supports .py files only.
  (jortel@redhat.com)
- 903387 - remove /var/lib/pulp/(packages|repos) and /var/lib/pulp/published
  (jortel@redhat.com)
- 878234 - added consumer group itineraries and updated group content install
  apis to return a list of call requests, also added unit tests
  (skarmark@redhat.com)
- 888058 - Changed model for the client-side exception handler to be overridden
  and specified to the launcher, allowing an individual client (admin,
  consumer, future other) to customize error messages where relevant.
  (jason.dobies@redhat.com)

* Sat Jan 19 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.1.alpha
- 891423 - Added conduit calls to be able to create units on copy
  (jason.dobies@redhat.com)
- 894467 - Parser methods need to return the value, not just validate it
  (jason.dobies@redhat.com)
- 889893 - added detection of still queued scheduled calls and skip re-
  enqueueing with log message (jason.connor@gmail.com)
- 883938 - Bumped required version of okaara in the spec
  (jason.dobies@redhat.com)
- 885128 - Altered two more files to use the 'db' logger. (rbarlow@redhat.com)
- 885128 - pulp.plugins.loader.api should use the "db" logger.
  (rbarlow@redhat.com)
- 891423 - Added conduit calls to be able to create units on copy
  (jason.dobies@redhat.com)
- 891760 - added importer and distributor configs to kwargs and
  kwargs_blacklist to prevent logging of sensitive data
  (jason.connor@gmail.com)
- 889320 - updating relabel script to run restorecon on /var/www/pulp_puppet
  (skarmark@redhat.com)
- 889320 - adding httpd_sys_content_rw_t context to /var/www/pulp_puppet
  (skarmark@redhat.com)
- 887959 - Removing NameVirtualHost entries from plugin httpd conf files and
  adding it only at one place in main pulp.conf (skarmark@redhat.com)
- 886547 - added check for deleted schedule in scheduled call complete callback
  (jason.connor@gmail.com)
- 882412 - Re-raising PulpException upon upload error instead of always
  replacing exceptions with PulpExecutionException, the latter of which results
  in an undesirable 500 HTTP response. (mhrivnak@redhat.com)
- 875843 - added post sync/publish callbacks to cleanup importer and
  distributor instances before calls are archived (jason.connor@gmail.com)
- 769381 - Fixed delete confirmation message to be task centric
  (jason.dobies@redhat.com)
- 856762 - removing scratchpads from repo search queries (skarmark@redhat.com)
- 886148 - used new result masking to keep full consumer package profiles from
  showing up in the task list and log file (jason.connor@gmail.com)
- 856762 - removing scratchpad from the repo list --details commmand for repo,
  importer and distributor (skarmark@redhat.com)
- 883899 - added conflict detection for call request groups in the webservices
  execution wrapper module (jason.connor@gmail.com)
- 876158 - Removed unused configuration values and cleaned up wording and
  formatting of the remaining options (jason.dobies@redhat.com)
- 882403 - Flushed out the task state to user display mapping as was always the
  intention but never actually came to fruition. (jason.dobies@redhat.com)
- 882422 - added the distributor_list keyword argument to the call requets
  kwarg_blacklist to prevent it from being logged (jason.connor@gmail.com)
- 885229 - add requires: nss-tools. (jortel@redhat.com)
- 885098 - Use a separate logging config for pulp-manage-db.
  (rbarlow@redhat.com)
- 885134 - Added check to not parse an apache error as if it has the Pulp
  structure and handling in the exception middleware for it
  (jason.dobies@redhat.com)
- 867464 - Renaming modules to units and a fixing a few minor output errors
  (skarmark@redhat.com)
- 882421 - moving unit remove command into the platform from RPM extensions so
  it can be used by other extension families (mhrivnak@redhat.com)
- 877147 - added check for path type when removing orphans
  (jason.connor@gmail.com)
- 882423 - fix upload in repo controller. (jortel@redhat.com)
- 883568 - Reworded portion about recurrences (jason.dobies@redhat.com)
- 883754 - The notes option was changed to have a parser, but some code using
  it was continuing to manually parse it again, which would tank.
  (jason.dobies@redhat.com)
- 866996 - Added ability to hide the details link on association commands when
  it isn't a search. (jason.dobies@redhat.com)
- 877797 - successful call of canceling a task now returns a call report
  through the rest api (jason.connor@gmail.com)
- 867464 - updating general module upload command output (skarmark@redhat.com)
- 882424 - only have 1 task, presumedly the "main" one, in a task group update
  the last_run field (jason.connor@gmail.com)
- 883059 - update server.conf to make server_name optional
  (skarmark@redhat.com)
- 883059 - updating default server config to lookup server hostname
  (skarmark@redhat.com)
- 862187 /var/log/pulp/db.log now includes timestamps. (rbarlow@redhat.com)
- 883025 - Display note to copy qpid certificates to each consumer.
  (jortel@redhat.com)
- 880441 - Fixed call to a method that was renamed (jason.dobies@redhat.com)
- 881120 - utilized new serialize_result call report flag to hide consumer key
  when reporting the task information (jason.connor@gmail.com)
- 882428 - utilizing new call report serialize_result flag to prevent the call
  reports from being serialized and reported over the rest api
  (jason.connor@gmail.com)
- 882401 - added skipped as a recognized state to the cli parser
  (jason.connor@gmail.com)
- 862290 - Added documentation for the new ListRepositoriesCommand methods
  (jason.dobies@redhat.com)
- 881639 - more programmatic. (jortel@redhat.com)
- 881389 - fixed rpm consumer bind to raise an error on non existing repos
  (skarmark@redhat.com)
- 827620 - updated repo, repo_group, consumer and user apis to use execute
  instead of execute_ok (skarmark@redhat.com)
- 878620 - fixed task group resource to return only tasks in the group instead
  of all tasks ever run... :P (jason.connor@gmail.com)
- 866491 - Change the source repo ID validation to be a 400, not 404
  (jason.dobies@redhat.com)
- 866491 - Check for repo existence and raise a 404 if not found instead of
  leaving the task to do it (jason.dobies@redhat.com)
- 881120 - strip the private key from returned consumer object.
  (jortel@redhat.com)
- 862290 - Added support in generic list repos command for listing other
  repositories (jason.dobies@redhat.com)
- 877914 - updating old file links from selinux installation and un-
  installation (skarmark@redhat.com)
- 873786 - updating enable.sh for correct amqp ports (skarmark@redhat.com)
- 878654 - fixed error message when revoking permission from a non-existing
  user and added unit tests (skarmark@redhat.com)
- added database collection reaper system that will wake up periodically and
  remove old documents from configured collections (jason.connor@gmail.com)
- 876662 - Added middleware exception handling for when the client cannot
  resolve the server hostname (jason.dobies@redhat.com)
- 753680 - Taking this opportunity to quiet the logs a bit too
  (jason.dobies@redhat.com)
- 753680 - Increased the logging clarity and location for initialization errors
  (jason.dobies@redhat.com)
- 871858 - Implemented sync and publish status commands
  (jason.dobies@redhat.com)
- 873421 - changed a wait-time message to be more appropriate, and added a bit
  of function parameter documentation. (mhrivnak@redhat.com)
- 877170 - Added ability to ID validator to handle multiple inputs
  (jason.dobies@redhat.com)
- 877435 - Pulled the filters/order to constants and use in search
  (jason.dobies@redhat.com)
- 875606 - Added isodate and python-setuptools deps. Rolled into a quick audit
  of all the requirements and changed quite a few. There were several missing
  and several no longer applicaple. Also removed a stray import of okaara from
  within the bindings package. (mhrivnak@redhat.com)
- 874243 - return 404 when profile does not exist. (jortel@redhat.com)
- 876662 - Added pretty error message when the incorrect server hostname is
  used (jason.dobies@redhat.com)
- 876332 - add missing tags to bind itinerary. (jortel@redhat.com)

* Thu Dec 20 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.19.rc
- Pulp rebuild

* Wed Dec 19 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.19.beta
- Pulp rebuild

* Tue Dec 18 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.18.beta
- 887959 - Removing NameVirtualHost entries from plugin httpd conf files and
  adding it only at one place in main pulp.conf (skarmark@redhat.com)

* Thu Dec 13 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.17.beta
- Pulp rebuild

* Thu Dec 13 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.16.beta
- Pulp rebuild

* Thu Dec 13 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.15.beta
- 886547 - added check for deleted schedule in scheduled call complete callback
  (jason.connor@gmail.com)
- 882412 - Re-raising PulpException upon upload error instead of always
  replacing exceptions with PulpExecutionException, the latter of which results
  in an undesirable 500 HTTP response. (mhrivnak@redhat.com)
- 875843 - added post sync/publish callbacks to cleanup importer and
  distributor instances before calls are archived (jason.connor@gmail.com)
- 769381 - Fixed delete confirmation message to be task centric
  (jason.dobies@redhat.com)
- 856762 - removing scratchpads from repo search queries (skarmark@redhat.com)
- 886148 - used new result masking to keep full consumer package profiles from
  showing up in the task list and log file (jason.connor@gmail.com)
- 856762 - removing scratchpad from the repo list --details commmand for repo,
  importer and distributor (skarmark@redhat.com)
- 883899 - added conflict detection for call request groups in the webservices
  execution wrapper module (jason.connor@gmail.com)
- 876158 - Removed unused configuration values and cleaned up wording and
  formatting of the remaining options (jason.dobies@redhat.com)
- 882403 - Flushed out the task state to user display mapping as was always the
  intention but never actually came to fruition. (jason.dobies@redhat.com)
- 882422 - added the distributor_list keyword argument to the call requets
  kwarg_blacklist to prevent it from being logged (jason.connor@gmail.com)

* Mon Dec 10 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.14.beta
- 885229 - add requires: nss-tools. (jortel@redhat.com)

* Fri Dec 07 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.13.beta
- 885098 - Use a separate logging config for pulp-manage-db.
  (rbarlow@redhat.com)
- 885134 - Added check to not parse an apache error as if it has the Pulp
  structure and handling in the exception middleware for it
  (jason.dobies@redhat.com)

* Thu Dec 06 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.12.beta
- 867464 - Renaming modules to units and a fixing a few minor output errors
  (skarmark@redhat.com)
- 882421 - moving unit remove command into the platform from RPM extensions so
  it can be used by other extension families (mhrivnak@redhat.com)
- 877147 - added check for path type when removing orphans
  (jason.connor@gmail.com)
- 882423 - fix upload in repo controller. (jortel@redhat.com)
- 883568 - Reworded portion about recurrences (jason.dobies@redhat.com)
- 883754 - The notes option was changed to have a parser, but some code using
  it was continuing to manually parse it again, which would tank.
  (jason.dobies@redhat.com)
- 866996 - Added ability to hide the details link on association commands when
  it isn't a search. (jason.dobies@redhat.com)
- 877797 - successful call of canceling a task now returns a call report
  through the rest api (jason.connor@gmail.com)
- 867464 - updating general module upload command output (skarmark@redhat.com)
- 882424 - only have 1 task, presumedly the "main" one, in a task group update
  the last_run field (jason.connor@gmail.com)
- 883059 - update server.conf to make server_name optional
  (skarmark@redhat.com)
- 883059 - updating default server config to lookup server hostname
  (skarmark@redhat.com)
- 862187 /var/log/pulp/db.log now includes timestamps. (rbarlow@redhat.com)
- 883025 - Display note to copy qpid certificates to each consumer.
  (jortel@redhat.com)
- 880441 - Fixed call to a method that was renamed (jason.dobies@redhat.com)
- 881120 - utilized new serialize_result call report flag to hide consumer key
  when reporting the task information (jason.connor@gmail.com)
- 882428 - utilizing new call report serialize_result flag to prevent the call
  reports from being serialized and reported over the rest api
  (jason.connor@gmail.com)
- 882401 - added skipped as a recognized state to the cli parser
  (jason.connor@gmail.com)

* Thu Nov 29 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.11.beta
- Pulp rebuild

* Thu Nov 29 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.10.beta
- 862290 - Added documentation for the new ListRepositoriesCommand methods
  (jason.dobies@redhat.com)
- 881639 - more programmatic. (jortel@redhat.com)
- 881389 - fixed rpm consumer bind to raise an error on non existing repos
  (skarmark@redhat.com)
- 827620 - updated repo, repo_group, consumer and user apis to use execute
  instead of execute_ok (skarmark@redhat.com)
- 878620 - fixed task group resource to return only tasks in the group instead
  of all tasks ever run... :P (jason.connor@gmail.com)
- 866491 - Change the source repo ID validation to be a 400, not 404
  (jason.dobies@redhat.com)
- 866491 - Check for repo existence and raise a 404 if not found instead of
  leaving the task to do it (jason.dobies@redhat.com)
- 881120 - strip the private key from returned consumer object.
  (jortel@redhat.com)
- 862290 - Added support in generic list repos command for listing other
  repositories (jason.dobies@redhat.com)
- 877914 - updating old file links from selinux installation and un-
  installation (skarmark@redhat.com)
- 873786 - updating enable.sh for correct amqp ports (skarmark@redhat.com)
- 878654 - fixed error message when revoking permission from a non-existing
  user and added unit tests (skarmark@redhat.com)
- added database collection reaper system that will wake up periodically and
  remove old documents from configured collections (jason.connor@gmail.com)
- 876662 - Added middleware exception handling for when the client cannot
  resolve the server hostname (jason.dobies@redhat.com)

* Mon Nov 26 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.9.beta
- Pulp rebuild

* Wed Nov 21 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.8.beta
- Pulp rebuild

* Wed Nov 21 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.7.beta
- Pulp rebuild

* Wed Nov 21 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.6.beta
- Pulp rebuild

* Wed Nov 21 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.5.beta
- 753680 - Taking this opportunity to quiet the logs a bit too
  (jason.dobies@redhat.com)
- 753680 - Increased the logging clarity and location for initialization errors
  (jason.dobies@redhat.com)

* Wed Nov 21 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.4.beta
- Pulp rebuild

* Tue Nov 20 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.3.beta
- 871858 - Implemented sync and publish status commands
  (jason.dobies@redhat.com)
- 873421 - changed a wait-time message to be more appropriate, and added a bit
  of function parameter documentation. (mhrivnak@redhat.com)
- 877170 - Added ability to ID validator to handle multiple inputs
  (jason.dobies@redhat.com)
- 877435 - Pulled the filters/order to constants and use in search
  (jason.dobies@redhat.com)
- 875606 - Added isodate and python-setuptools deps. Rolled into a quick audit
  of all the requirements and changed quite a few. There were several missing
  and several no longer applicaple. Also removed a stray import of okaara from
  within the bindings package. (mhrivnak@redhat.com)
- 874243 - return 404 when profile does not exist. (jortel@redhat.com)
- 876662 - Added pretty error message when the incorrect server hostname is
  used (jason.dobies@redhat.com)
- 876332 - add missing tags to bind itinerary. (jortel@redhat.com)

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.2.beta
- Pulp rebuild

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.1.beta
- Pulp rebuild
