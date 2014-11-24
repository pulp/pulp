%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}


# ---- Pulp Nodes -------------------------------------------------------------

Name: pulp-nodes
Version: 2.6.0
Release: 0.1.alpha%{?dist}
Summary: Support for pulp nodes
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://github.com/pulp/pulp/archive/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: rpm-python

%description
Provides a collection of platform plugins, client extensions and agent
handlers that provide nodes support.  Nodes provides the ability for
a child Pulp server to synchronize repositories and content with a
parent Pulp server to which it has registered as a consumer.

%prep
%setup -q

%build
pushd common
%{__python} setup.py build
popd
pushd parent
%{__python} setup.py build
popd
pushd child
%{__python} setup.py build
popd
pushd extensions/admin
%{__python} setup.py build
popd
pushd extensions/consumer
%{__python} setup.py build
popd

%install
rm -rf %{buildroot}
pushd common
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
pushd parent
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
pushd child
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
pushd extensions/admin
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
pushd extensions/consumer
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

# Directories
mkdir -p /srv
mkdir -p %{buildroot}/%{_sysconfdir}/pulp
mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins/types
mkdir -p %{buildroot}/%{_var}/lib/pulp/nodes/published/http
mkdir -p %{buildroot}/%{_var}/lib/pulp/nodes/published/https
mkdir -p %{buildroot}/%{_var}/www/pulp/nodes
mkdir -p %{buildroot}/%{_bindir}

# Configuration
pushd common
cp -R etc/pulp %{buildroot}/%{_sysconfdir}
popd
pushd parent
cp -R etc/httpd %{buildroot}/%{_sysconfdir}
cp -R etc/pulp %{buildroot}/%{_sysconfdir}
popd
pushd child
cp -R etc/pulp %{buildroot}/%{_sysconfdir}
popd

# Scripts
pushd common
cp bin/* %{buildroot}/%{_bindir}
popd

# Types
cp -R child/pulp_node/importers/types/* %{buildroot}/%{_usr}/lib/pulp/plugins/types/

# WWW
ln -s %{_var}/lib/pulp/nodes/published/http %{buildroot}/%{_var}/www/pulp/nodes
ln -s %{_var}/lib/pulp/nodes/published/https %{buildroot}/%{_var}/www/pulp/nodes

%clean
rm -rf %{buildroot}


# --- macros -----------------------------------------------------------------


# define required pulp platform version.
%global pulp_version %{version}

# ---- Common ----------------------------------------------------------------

%package common
Summary: Pulp nodes common modules
Group: Development/Languages
Requires: %{name}-common = %{version}
Requires: pulp-server = %{pulp_version}
Requires: python-pulp-bindings = %{pulp_version}

%description common
Pulp nodes common modules.

%files common
%defattr(-,root,root,-)
%dir %{python_sitelib}/pulp_node
%dir %{python_sitelib}/pulp_node/extensions
%{_bindir}/pulp-gen-nodes-certificate
%{python_sitelib}/pulp_node/extensions/__init__.py*
%{python_sitelib}/pulp_node/*.py*
%{python_sitelib}/pulp_node_common*.egg-info
%defattr(640,root,apache,-)
# The nodes.conf file contains OAuth secrets, so we don't want it to be world readable
%config(noreplace) %{_sysconfdir}/pulp/nodes.conf
%defattr(-,root,root,-)
%doc

%post common
# Generate the certificate used to access the local server.
pulp-gen-nodes-certificate

%postun common
# clean up the nodes certificate.
if [ $1 -eq 0 ]; then
  rm -rf /etc/pki/pulp/nodes
fi


# ---- Parent Nodes ----------------------------------------------------------

%package parent
Summary: Pulp parent nodes support
Group: Development/Languages
Requires: %{name}-common = %{version}
Requires: pulp-server = %{pulp_version}

%description parent
Pulp parent nodes support.

%files parent
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_nodes.conf
%{_sysconfdir}/pulp/server/plugins.conf.d/nodes/distributor/
%{python_sitelib}/pulp_node/profilers/
%{python_sitelib}/pulp_node/distributors/
%{python_sitelib}/pulp_node_parent*.egg-info
%defattr(-,apache,apache,-)
%{_var}/lib/pulp/nodes
%{_var}/www/pulp/nodes
%defattr(-,root,root,-)
%doc


# ---- Child Nodes -----------------------------------------------------------

%package child
Summary: Pulp child nodes support
Group: Development/Languages
Requires: %{name}-common = %{version}
Requires: pulp-server = %{pulp_version}
Requires: python-pulp-agent-lib = %{pulp_version}
Requires: python-nectar >= 1.1.2

%description child
Pulp child nodes support.

%files child
%defattr(-,root,root,-)
%dir %{_sysconfdir}/pulp/server/plugins.conf.d/nodes/importer
%{python_sitelib}/pulp_node/importers/
%{python_sitelib}/pulp_node/handlers/
%{python_sitelib}/pulp_node_child*.egg-info
%{_usr}/lib/pulp/plugins/types/nodes.json
%{_sysconfdir}/pulp/agent/conf.d/nodes.conf
%defattr(640,root,apache,-)
# We don't want the importer config to be world readable, since it can contain proxy passwords
%{_sysconfdir}/pulp/server/plugins.conf.d/nodes/importer/*
%defattr(-,root,root,-)
%doc


# ---- Admin Extensions ------------------------------------------------------

%package admin-extensions
Summary: Pulp admin client extensions
Group: Development/Languages
Requires: %{name}-common = %{version}
Requires: pulp-admin-client = %{pulp_version}

%description admin-extensions
Pulp nodes admin client extensions.

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/pulp_node/extensions/admin/
%{python_sitelib}/pulp_node_admin_extensions*.egg-info
%doc


# ---- Consumer Extensions ---------------------------------------------------

%package consumer-extensions
Summary: Pulp consumer client extensions
Group: Development/Languages
Requires: %{name}-common = %{version}
Requires: pulp-consumer-client = %{pulp_version}

%description consumer-extensions
Pulp nodes consumer client extensions.

%files consumer-extensions
%defattr(-,root,root,-)
%{python_sitelib}/pulp_node/extensions/consumer/
%{python_sitelib}/pulp_node_consumer_extensions*.egg-info
%doc


# ----------------------------------------------------------------------------


%changelog
* Fri Nov 21 2014 Chris Duryee <cduryee@redhat.com> 2.6.0-0.1.alpha
- 1161205 - Adds comments to conf files about value of defaults
  (bmbouter@gmail.com)
- 1135589 - move PRIMARY_ID definition (cduryee@redhat.com)
- 1142304 - remove extraneous errors during unit test runs (cduryee@redhat.com)
- 1095483 - fix message to not refer to pulp.log (cduryee@redhat.com)

* Fri Nov 21 2014 Austin Macdonald <asmacdo@gmail.com> 2.5.0-1
- 1150297 - Update versions from 2.4.x to 2.5.0. (rbarlow@redhat.com)

* Thu Jul 31 2014 Randy Barlow <rbarlow@redhat.com> 2.4.0-1
- 1125030 - Handle both styles of certificate stores. (rbarlow@redhat.com)
- 1113590 - Nodes requires Pulp's cert to be trusted 1112906 - pulp-admin
  requires Pulp's cert to be trusted 1112904 - pulp-consumer requires Pulp's
  cert to be trusted (rbarlow@redhat.com)
- 1005899 - support 'message' reported during node sync. (jortel@redhat.com)
- 1096931 - improving repo update command to better detect spawned tasks
  (mhrivnak@redhat.com)
- 1091530 - fix rendering a progress report = None. (jortel@redhat.com)
- 1087863 - Fix progress reporting in node sync command. (jortel@redhat.com)
- 1085545 - Fix permissions on /etc/pulp/server/plugins.conf.d/nodes/importer.
  (jortel@redhat.com)
- 1073154 - Do not log newlines or long messages. (rbarlow@redhat.com)
- 921743 - Adjust ownership and permissions for a variety of the RPM paths.
  (rbarlow@redhat.com)
- 1005899 - report errors fetching bindings from the parent in the report.
  (jortel@redhat.com)
- 995076 - make sure to call finalize on the nectar config object
  (jason.connor@gmail.com)
- 1029057 - have nodes replicate the repository scratchpad. (jortel@redhat.com)
- 1022646 - remove units_path; in 2.3, it's method. (jortel@redhat.com)

* Wed Nov 06 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-1
- 1022646 - migration_0 needs to add units_size=0. (jortel@redhat.com)
- 1022646 - fix migration of nodes 2.2 => 2.3 manifests. (jortel@redhat.com)
- 1020549 - tar the content of the distribution directory instead of the
  directory. (jortel@redhat.com)
- 1017924 - unzip the units.json instead of reading/seeking using gzip.
  (jortel@redhat.com)
- 1013097 - permit (.) in node IDs. (jortel@redhat.com)
- 965751 - migrate nodes to use threaded downloader. (jortel@redhat.com)
- 1004346 - deal with bindings w (None) as binding_config. (jortel@redhat.com)
- 1005898 - Remove unnecessary dependency on gofer in pulp-nodes.spec file
  (bcourt@redhat.com)
- 1003285 - fixed an attribute access for an attribute that doesn't exist in
  python 2.6. (mhrivnak@redhat.com)
- 915330 - Fix performance degradation of importer and distributor
  configuration validation as the number of repositories increased
  (bcourt@redhat.com)
- nodes support updated content units. (jortel@redhat.com)
- 991201 - use plugin specific attribute for type_id. (jortel@redhat.com)
- 989627 - dont use rstrip() to remove a file suffix. (jortel@redhat.com)
- 988913 - mirror (node) strategy only affect specified repos when units
  type_id=repository. (jortel@redhat.com)
- 977948 - fix distributor updating during node sync. (jortel@redhat.com)
- purge changelog
- 924832 - check if node is already activated. (jortel@redhat.com)

* Tue Jun 04 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-1
- 968543 - remove conditional in pulp_version macro. (jortel@redhat.com)
- 955356 - pulp-nodes-child requires: pulp-agent. (jortel@redhat.com)
- 922229 - fix progress rendering. rendering depends on bindings processed in a
  determined order.  Perhaps fragile and should revisit progress rendering.
  (jortel@redhat.com)
- 919118 - use succeeded flag to render success message or not.
  (jortel@redhat.com)
- 919134 - Add explaination to BadRequest raised when distributor not
  installed. (jortel@redhat.com)
- 919200 - move node level update strategy to consumer note.
  (jortel@redhat.com)
- 919177 - display bindings collated by strategy. (jortel@redhat.com)
- 921159 - Better description of --auto-publish. (jortel@redhat.com)
- 921107 - Fix grammatical error in node activate message. (jortel@redhat.com)
- 921104 - Fix variable substitution in message. (jortel@redhat.com)

* Mon Mar 04 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-1
- 916345 - SSLCACertificateFile not supported with <Directory/> in apache 2.4
  (jortel@redhat.com)
- new package built with tito
