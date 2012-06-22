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

Name: pulp-rpm
Version: 0.0.307
Release: 1%{?dist}
Summary: Support for RPM content in the Pulp platform
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
handlers that provide RPM support.

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
mkdir -p %{buildroot}/%{_var}/lib/pulp/published
mkdir -p %{buildroot}/%{_usr}/lib/yum-plugins/
mkdir -p %{buildroot}/%{_var}/www

# Configuration
cp -R etc/* %{buildroot}/%{_sysconfdir}

# WSGI
cp -R srv %{buildroot}

# WWW
ln -s %{_var}/lib/pulp/published %{buildroot}/%{_var}/www/pub

# Extensions
cp -R extensions/admin/* %{buildroot}/%{_usr}/lib/pulp/admin/extensions
cp -R extensions/consumer/* %{buildroot}/%{_usr}/lib/pulp/consumer/extensions

# Agent Handlers
cp handlers/* %{buildroot}/%{_usr}/lib/pulp/agent/handlers

# Plugins
cp -R plugins/* %{buildroot}/%{_usr}/lib/pulp/plugins

# Yum (plugins)
cp -R usr/lib/yum-plugins %{buildroot}/%{_usr}/lib

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/*.egg-info

%clean
rm -rf %{buildroot}


# ---- Plugins -----------------------------------------------------------------

%package plugins
Summary: Pulp RPM plugins
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-server = %{version}

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide RPM specific support.

%files plugins
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/pulp/repo_auth.conf
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_rpm.conf
%{_usr}/lib/pulp/plugins/types/rpm_support.json
%{_usr}/lib/pulp/plugins/importers/yum_importer/
%{_usr}/lib/pulp/plugins/distributors/yum_distributor/
%defattr(-,apache,apache,-)
%{_var}/www/pub
/srv/pulp/repo_auth.wsgi
%doc


# ---- RPM Common --------------------------------------------------------------

%package -n python-pulp-rpm-common
Summary: Pulp RPM support common library
Group: Development/Languages
Requires: python-pulp-common = %{version}

%description -n python-pulp-rpm-common
A collection of components share between RPM plugins, extensions and handlers.

%files -n python-pulp-rpm-common
%defattr(-,root,root,-)
%{python_sitelib}/pulp_rpm/
%doc


# ---- Admin (builtin) Extensions ----------------------------------------------

%package admin-extensions
Summary: The RPM admin client extensions
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-admin-client = %{version}

%description admin-extensions
A collection of extensions that supplement and override generic admin
client capabilites with RPM specific features.


%files admin-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/admin/extensions/rpm_admin_consumer/
%{_usr}/lib/pulp/admin/extensions/rpm_repo/
%{_usr}/lib/pulp/admin/extensions/rpm_sync/
%{_usr}/lib/pulp/admin/extensions/rpm_units_copy/
%{_usr}/lib/pulp/admin/extensions/rpm_units_search/
%{_usr}/lib/pulp/admin/extensions/rpm_upload/
%doc


# ---- Consumer (builtin) Extensions -------------------------------------------

%package consumer-extensions
Summary: The RPM consumer client extensions
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-consumer-client = %{version}

%description consumer-extensions
A collection of extensions that supplement and override generic consumer
client capabilites with RPM specific features.

%files consumer-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/consumer/extensions/rpm_consumer/
%doc


# ---- Agent Handlers ----------------------------------------------------------

%package handlers
Summary: Pulp agent rpm handlers
Requires: python-pulp-rpm-common = %{version}
Requires: python-pulp-agent-lib = %{version}

%description handlers
A collection of handlers that provide both Linux and RPM specific
functionality within the Pulp agent.  This includes RPM install, update,
uninstall; RPM profile reporting; binding through yum repository
management and Linux specific commands such as system reboot.


%files handlers
%defattr(-,root,root,-)
%{_sysconfdir}/pulp/agent/conf.d/bind.conf
%{_sysconfdir}/pulp/agent/conf.d/linux.conf
%{_sysconfdir}/pulp/agent/conf.d/rpm.conf
%{_usr}/lib/pulp/agent/handlers/bind.py*
%{_usr}/lib/pulp/agent/handlers/linux.py*
%{_usr}/lib/pulp/agent/handlers/rpm.py*
%doc


# ---- YUM Plugins -------------------------------------------------------------

%package yumplugins
Summary: Yum plugins supplementing in Pulp consumer operations
Requires: python-pulp-rpm-common = %{version}
Requires: pulp-server = %{version}

%description yumplugins
A collection of yum plugins supplementing Pulp consumer operations.

%files yumplugins
%defattr(-,root,root,-)
%{_sysconfdir}/yum/pluginconf.d/pulp-profile-update.conf
%{_usr}/lib/yum-plugins/pulp-profile-update.py*
%doc





%changelog
* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.307-1
- 

* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.306-1
- Changed setup.py to use find packages to try to fix the rpm common RPM's
  issues with including python files (jason.dobies@redhat.com)

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.305-1
- Still trying to fix this note thing (jason.dobies@redhat.com)
- Fixed repo update (jason.dobies@redhat.com)

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.304-1
- Removed unknown repo file (jason.dobies@redhat.com)

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.303-1
- 831781 - fix for supporting skipcontent types (pkilambi@redhat.com)
- YumDistributor: Adding generation of pkg groups to xml file
  (jmatthews@redhat.com)
- Don't think we need this (jason.dobies@redhat.com)

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.302-1
- 

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.301-1
- few more (jason.connor@gmail.com)
- YumImporter: unit test cleanup (jmatthews@redhat.com)
- Update test_errata to use RPM_TYPE_ID in link_errata test
  (jmatthews@redhat.com)
- Display name should be user-friendly (jason.dobies@redhat.com)
- YumImporter: Unit tests for sync of orphaned comps data
  (jmatthews@redhat.com)
- Updating base class for importer/distributor rpm related unit tests
  (jmatthews@redhat.com)
- Fix missing published/ and /var/www/pub. (jortel@redhat.com)
- Adjust dependancies after install testing. (jortel@redhat.com)

* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.300-1
- Align versions to: 300 (jortel@redhat.com)
- update test repo metadata to be compatible with el5 (pkilambi@redhat.com)
- Typo fix (jason.dobies@redhat.com)
- Changed base class for rpm unit tests from 'base' to 'rpm_support_base'
  (jmatthews@redhat.com)
- Fixed reference that I have no idea how it broke (jason.dobies@redhat.com)
- Updating unit test imports to work around failure seen with run_tests
  (jmatthews@redhat.com)
- YumImporter: configuring logging for yum importer unit tests
  (jmatthews@redhat.com)
- YumImporter: Cleaning up extra test dirs during tests & Adding configurable
  Retry logic for grinder (jmatthews@redhat.com)
- Better package summary/descriptions. (jortel@redhat.com)
- pulp-rpm spec build fixes. (jortel@redhat.com)

* Thu Jun 14 2012 Jeff Ortel <jortel@redhat.com> 0.0.296-1
- new package built with tito

* Fri Jun 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.295-1
- created.
