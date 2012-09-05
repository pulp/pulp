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


# ---- Pulp --------------------------------------------------------------------

Name: pulp-citrus
Version: 0.0.325
Release: 2%{?dist}
Summary: Support for pulp citrus
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
handlers that provide citrus support.  Citrus provides the ability for
downstream Pulp server to synchronize repositories and content with the
upstream server to which it has registered as a consumer.

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
mkdir -p /srv
mkdir -p %{buildroot}/%{_sysconfdir}/pulp
mkdir -p %{buildroot}/%{_usr}/lib
mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins
mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/consumer/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/agent/handlers

# Configuration
cp -R etc/pulp %{buildroot}/%{_sysconfdir}
cp -R etc/httpd %{buildroot}/%{_sysconfdir}

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


# ---- Plugins -----------------------------------------------------------------

%package plugins
Summary: Pulp citrus support plugins
Group: Development/Languages
Requires: pulp-server >= %{version}

%description plugins
Plugins to provide citrus support.

%files plugins
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_citrus.conf
%{_usr}/lib/pulp/plugins/importers/citrus_importer/
%{_usr}/lib/pulp/plugins/distributors/citrus_distributor/
%doc

# ---- Admin (builtin) Extensions ----------------------------------------------

%package admin-extensions
Summary: The citrus admin client extensions
Group: Development/Languages
Requires: pulp-admin-client >= %{version}

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with citrus specific features.


%files admin-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/admin/extensions/pulp_admin_citrus/
%doc

# ---- Agent Handlers ----------------------------------------------------------

%package handlers
Summary: Pulp agent rpm handlers
Group: Development/Languages
Requires: python-pulp-agent-lib >= %{version}

%description handlers
Pulp citrus handlers.

%files handlers
%defattr(-,root,root,-)
%{_sysconfdir}/pulp/agent/conf.d/citrus.conf
%{_usr}/lib/pulp/agent/handlers/citrus.py*
%doc


%changelog
* Wed Sep 05 2012 Jeff Ortel <jortel@redhat.com> 0.0.325-1
- new package built with tito
