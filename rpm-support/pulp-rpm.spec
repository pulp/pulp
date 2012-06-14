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


################################################################################
# Pulp
################################################################################

Name: pulp-rpm
Version: 0.0.296
Release: 1%{?dist}
Summary: RPM support for the Pulp platform.
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
Provides RPM support for the Pulp platform.

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
mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins
mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/consumer/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/agent/handlers

# Configuration
cp -R etc/* %{buildroot}/%{_sysconfdir}

# Apache
cp -R srv %{buildroot}

# Extensions
cp -R extensions/admin/* %{buildroot}/%{_usr}/lib/pulp/admin/extensions
cp -R extensions/consumer/* %{buildroot}/%{_usr}/lib/pulp/consumer/extensions

# Agent Handlers
cp handlers/* %{buildroot}/%{_usr}/lib/pulp/handlers

# Plugins
cp -R plugins/* %{_usr}/lib/pulp/plugins

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/*.egg-info

%clean
rm -rf %{buildroot}


################################################################################
# RPM Common
################################################################################

%package -n python-pulp-rpm-common
Summary: Pulp rpm support common library
Group: Development/Languages
Requires: python-pulp-common = %{version}

%description -n python-pulp-rpm-common
The Pulp rpm support common libraries.

%files -n python-pulp-rpm-common
%defattr(-,root,root,-)
%{python_sitelib}/pulp_rpm/
%doc


################################################################################
# Admin (builtin) Extensions
################################################################################

%package admin-extensions
Summary: The rpm admin client extensions
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-admin-client = %{version}

%description admin-extensions
The rpm extensions for the pulp admin client.

%files admin-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/admin/extensions/rpm_admin_consumer/
%{_usr}/lib/pulp/admin/extensions/rpm_repo/
%{_usr}/lib/pulp/admin/extensions/rpm_sync/
%{_usr}/lib/pulp/admin/extensions/rpm_units_copy/
%{_usr}/lib/pulp/admin/extensions/rpm_units_search/
%{_usr}/lib/pulp/admin/extensions/rpm_upload/
%doc


################################################################################
# Consumer (builtin) Extensions
################################################################################

%package consumer-extensions
Summary: The rpm consumer client extensions
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-consumer-client = %{version}

%description consumer-extensions
The rpm extensions for the pulp consumer client.

%files consumer-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/consumer/extensions/rpm_consumer/
%doc


################################################################################
# Plugins
################################################################################

%package plugins
Summary: Pulp rpm plugins
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-server = %{version}

%description plugins
The Pulp platform plugins.

%files plugins
%defattr(-,root,root,-)
%{_usr}/lib/pulp/plugins/types/rpm_support.json
%{_usr}/lib/pulp/plugins/importers/yum_importer/
%{_usr}/lib/pulp/plugins/distributors/yum_distributor/
%doc


################################################################################
# Agent Handlers
################################################################################

%package handlers
Summary: Pulp agent rpm handlers
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-server = %{version}

%description handlers
The Pulp agent rpm handlers.

%files handlers
%defattr(-,root,root,-)
%{_sysconfdir}/pulp/agent/conf.d/bind.conf
%{_sysconfdir}/pulp/agent/conf.d/linux.conf
%{_sysconfdir}/pulp/agent/conf.d/rpm.conf
%{_usr}/lib/pulp/agent/handlers/bind.py
%{_usr}/lib/pulp/agent/handlers/linux.py
%{_usr}/lib/pulp/agent/handlers/rpm.py
%doc


################################################################################

%changelog
* Thu Jun 14 2012 Jeff Ortel <jortel@redhat.com> 0.0.296-1
- new package built with tito

* Fri Jun 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.295-1
- created.
