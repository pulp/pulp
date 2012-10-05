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


# ---- Pulp (puppet) -----------------------------------------------------------

Name: pulp-puppet
Version: 0.0.331
Release: 1%{?dist}
Summary: Support for Puppet content in the Pulp platform
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose
BuildRequires:  rpm-python

%description
Provides a collection of platform plugins, client extensions and agent
handlers that provide Puppet support.

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

# Directories
mkdir -p %{buildroot}/%{_sysconfdir}/pulp
mkdir -p %{buildroot}/%{_usr}/lib
mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins
mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/agent/handlers
mkdir -p %{buildroot}/%{_var}/www/pulp_puppet

# Configuration
cp -R etc/httpd %{buildroot}/%{_sysconfdir}
cp -R etc/pulp %{buildroot}/%{_sysconfdir}

# Extensions
cp -R extensions/admin/* %{buildroot}/%{_usr}/lib/pulp/admin/extensions

# Agent Handlers
cp handlers/* %{buildroot}/%{_usr}/lib/pulp/agent/handlers

# Plugins
cp -R plugins/* %{buildroot}/%{_usr}/lib/pulp/plugins

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/*.egg-info

%clean
rm -rf %{buildroot}



# ---- Puppet Common -----------------------------------------------------------

%package -n python-pulp-puppet-common
Summary: Pulp Puppet support common library
Group: Development/Languages
Requires: python-pulp-common = %{version}

%description -n python-pulp-puppet-common
A collection of modules shared among all Puppet components.

%files -n python-pulp-puppet-common
%defattr(-,root,root,-)
%{python_sitelib}/pulp_puppet
%{python_sitelib}/pulp_puppet/__init__.py*
%{python_sitelib}/pulp_puppet/common/
%doc


# ---- Puppet Extension Common ----------------------------------------------------

%package -n python-pulp-puppet-extension
Summary: The Puppet extension common library
Group: Development/Languages
Requires: python-pulp-puppet-common = %{version}

%description -n python-pulp-puppet-extension
A collection of components shared among Puppet extensions.

%files -n python-pulp-puppet-extension
%defattr(-,root,root,-)
%{python_sitelib}/pulp_puppet/extension/
%doc


# ---- Plugins -----------------------------------------------------------------

%package plugins
Summary: Pulp Puppet plugins
Group: Development/Languages
Requires: python-pulp-puppet-common = %{version}
Requires: pulp-server = %{version}

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Puppet specific support.

%files plugins
%defattr(-,root,root,-)
%{python_sitelib}/pulp_puppet/importer/
%{python_sitelib}/pulp_puppet/distributor/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_puppet.conf
%{_usr}/lib/pulp/plugins/types/puppet.json
%{_usr}/lib/pulp/plugins/importers/puppet_importer/
%{_usr}/lib/pulp/plugins/distributors/puppet_distributor/
%{_var}/www/pulp_puppet/
%doc


# ---- Admin Extensions --------------------------------------------------------

%package admin-extensions
Summary: The Puppet admin client extensions
Group: Development/Languages
Requires: python-pulp-puppet-extension = %{version}
Requires: pulp-admin-client = %{version}

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with Puppet specific features.

%files admin-extensions
%defattr(-,root,root,-)
%{_sysconfdir}/pulp/admin/conf.d/puppet.conf
%{_usr}/lib/pulp/admin/extensions/puppet_repo/
%doc


# ---- Agent Handlers ----------------------------------------------------------

%package handlers
Summary: Pulp agent puppet handlers
Group: Development/Languages
Requires: python-rhsm
Requires: python-pulp-rpm-common = %{version}
Requires: python-pulp-agent-lib = %{version}

%description handlers
A collection of handlers that provide both Linux and Puppet specific
functionality within the Pulp agent.  This includes Puppet install, update,
uninstall; Puppet profile reporting; binding through yum repository
management and Linux specific commands such as system reboot.

%files handlers
%defattr(-,root,root,-)
%{python_sitelib}/pulp_puppet/handler/
%{_sysconfdir}/pulp/agent/conf.d/puppet.conf
%{_usr}/lib/pulp/agent/handlers/puppet.py*
%doc


%changelog
* Fri Oct 05 2012 Jeff Ortel <jortel@redhat.com> 0.0.331-1
- 860408 - repo group member adding and removing now honors the --repo-id
  option, includes a new --all flag, and fails if no matching options are
  passed. (mhrivnak@redhat.com)

* Tue Oct 02 2012 Jeff Ortel <jortel@redhat.com> 0.0.330-1
- Version alignment.

* Sun Sep 30 2012 Jeff Ortel <jortel@redhat.com> 0.0.329-1
- Version alignment.

* Fri Sep 21 2012 Jeff Ortel <jortel@redhat.com> 0.0.328-1
- Version alignment.

* Thu Sep 20 2012 Jeff Ortel <jortel@redhat.com> 0.0.327-2
- Fix build errors.

* Thu Sep 20 2012 Jeff Ortel <jortel@redhat.com> 0.0.327-1
- new package built with tito
