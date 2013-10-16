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


# ---- Pulp Nodes -------------------------------------------------------------

Name: pulp-nodes
Version: 2.3.0
Release: 0.22.beta%{?dist}
Summary: Support for pulp nodes
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: python-nose
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
%config(noreplace) %{_sysconfdir}/pulp/nodes.conf
%{python_sitelib}/pulp_node/extensions/__init__.py*
%{python_sitelib}/pulp_node/*.py*
%{python_sitelib}/pulp_node_common*.egg-info
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
%{_sysconfdir}/pulp/server/plugins.conf.d/nodes/distributor/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_nodes.conf
%defattr(-,apache,apache,-)
%{python_sitelib}/pulp_node/profilers/
%{python_sitelib}/pulp_node/distributors/
%{python_sitelib}/pulp_node_parent*.egg-info
%{_var}/lib/pulp/nodes
%{_var}/www/pulp/nodes
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
%{python_sitelib}/pulp_node/importers/
%{python_sitelib}/pulp_node/handlers/
%{python_sitelib}/pulp_node_child*.egg-info
%{_usr}/lib/pulp/plugins/types/nodes.json
%{_sysconfdir}/pulp/agent/conf.d/nodes.conf
%{_sysconfdir}/pulp/server/plugins.conf.d/nodes/importer/
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
* Wed Oct 16 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.22.beta
- Pulp rebuild

* Tue Oct 15 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.21.beta
- Pulp rebuild

* Mon Oct 14 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.20.beta
- Pulp rebuild

* Fri Oct 11 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.19.beta
- 1017924 - unzip the units.json instead of reading/seeking using gzip.
  (jortel@redhat.com)

* Thu Oct 10 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.18.beta
- Pulp rebuild

* Wed Oct 02 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.17.beta
- 1013097 - permit (.) in node IDs. (jortel@redhat.com)

* Thu Sep 26 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.16.alpha
- Pulp rebuild

* Thu Sep 26 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.15.alpha
- Pulp rebuild

* Wed Sep 18 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.14.alpha
- Pulp rebuild

* Wed Sep 18 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.13.alpha
- 965751 - migrate nodes to use threaded downloader. (jortel@redhat.com)
- 1004346 - deal with bindings w (None) as binding_config. (jortel@redhat.com)

* Fri Sep 13 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.12.alpha
- Pulp rebuild

* Thu Sep 12 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.11.alpha
- Pulp rebuild

* Thu Sep 12 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.10.alpha
- 1005898 - Remove unnecessary dependency on gofer in pulp-nodes.spec file
  (bcourt@redhat.com)
- 1003285 - fixed an attribute access for an attribute that doesn't exist in
  python 2.6. (mhrivnak@redhat.com)

* Tue Sep 10 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.9.alpha
- Pulp rebuild

* Fri Sep 06 2013 Barnaby Court <bcourt@redhat.com> 2.3.0-0.8.alpha
- 915330 - Fix performance degradation of importer and distributor
  configuration validation as the number of repositories increased
  (bcourt@redhat.com)

* Fri Aug 30 2013 Barnaby Court <bcourt@redhat.com> 2.3.0-0.7.alpha
- Pulp rebuild

* Thu Aug 29 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.6.alpha
- nodes support updated content units. (jortel@redhat.com)

* Thu Aug 29 2013 Barnaby Court <bcourt@redhat.com> 2.3.0-0.5.alpha
- Pulp rebuild

* Tue Aug 27 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.4.alpha
- Pulp rebuild

* Tue Aug 27 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.3.alpha
- 991201 - use plugin specific attribute for type_id. (jortel@redhat.com)
- 989627 - dont use rstrip() to remove a file suffix. (jortel@redhat.com)

* Thu Aug 01 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.2.alpha
- Pulp rebuild

* Thu Aug 01 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-0.1.alpha
- 988913 - mirror (node) strategy only affect specified repos when units
  type_id=repository. (jortel@redhat.com)
- 977948 - fix distributor updating during node sync. (jortel@redhat.com)
- purge changelog
- 924832 - check if node is already activated. (jortel@redhat.com)

* Tue Jun 04 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.16.alpha
- 968543 - remove conditional in pulp_version macro. (jortel@redhat.com)

* Thu May 30 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.15.alpha
- Pulp rebuild

* Fri May 24 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.14.alpha
- Pulp rebuild

* Thu May 23 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.13.alpha
- Pulp rebuild

* Thu May 23 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.12.alpha
- Pulp rebuild

* Tue May 21 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.11.alpha
- Pulp rebuild

* Mon May 20 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.10.alpha
- Pulp rebuild

* Mon May 20 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.9.alpha
- Pulp rebuild

* Fri May 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.8.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.5.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.3.alpha
- 955356 - pulp-nodes-child requires: pulp-agent. (jortel@redhat.com)

* Fri Apr 19 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.2.alpha
- Pulp rebuild

* Fri Apr 12 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.1.alpha
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

* Mon Mar 04 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.19.alpha
- 916345 - SSLCACertificateFile not supported with <Directory/> in apache 2.4
  (jortel@redhat.com)

* Tue Feb 26 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.18.alpha
- Pulp rebuild

* Tue Feb 26 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.17.alpha
- Pulp rebuild

* Mon Feb 25 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.16.alpha
- Pulp rebuild

* Mon Feb 25 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.15.alpha
- Pulp rebuild

* Fri Feb 22 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.14.alpha
- Pulp rebuild

* Thu Feb 21 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.13.alpha
- Pulp rebuild

* Tue Feb 19 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.12.alpha
- Pulp rebuild

* Thu Feb 14 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.7.alpha
- new package built with tito



