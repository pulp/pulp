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


# ---- Pulp Builtins -----------------------------------------------------------

Name: pulp-builtins
Version: 0.0.307
Release: 1%{?dist}
Summary: Pulp builtin extensions
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: rpm-python

%description
The pulp project provided generic extensions.

%prep
%setup -q

%build

%install

# Directories
mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/consumer/extensions


# Extensions
cp -R extensions/admin/* %{buildroot}/%{_usr}/lib/pulp/admin/extensions
cp -R extensions/consumer/* %{buildroot}/%{_usr}/lib/pulp/consumer/extensions

%clean
rm -rf %{buildroot}


# ---- Admin (client) Extensions -----------------------------------------------

%package admin-extensions
Summary: The builtin admin client extensions
Requires: pulp-admin-client = %{version}

%description admin-extensions
A collection of extensions used to provide generic consumer
client capabilites.

%files admin-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/admin/extensions/pulp_admin_auth/
%{_usr}/lib/pulp/admin/extensions/pulp_admin_consumer/
%{_usr}/lib/pulp/admin/extensions/pulp_repo/
%{_usr}/lib/pulp/admin/extensions/pulp_server_info/
%{_usr}/lib/pulp/admin/extensions/pulp_tasks/
%doc


# ---- Consumer (client) Extensions --------------------------------------------

%package consumer-extensions
Summary: The builtin consumer client extensions
Requires: pulp-consumer-client = %{version}

%description consumer-extensions
A collection of extensions used to provide generic admin
client capabilites.

%files consumer-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/consumer/extensions/pulp_consumer/
%doc




%changelog
* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.307-1
- 

* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.306-1
- Fixing consumer authorization problem because of no associated users with the
  consumers (like in v1) and minor fixed to consumer config parsing
  (skarmark@redhat.com)

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.305-1
- 

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.304-1
- 

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.303-1
- 

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.302-1
- 

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.301-1
- few more (jason.connor@gmail.com)

* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.300-1
- Align versions to: 300 (jortel@redhat.com)
- Renamed builtins base for uniqueness across subprojects, relevant for the
  single test suite at root (jason.dobies@redhat.com)
- Better package summary/descriptions. (jortel@redhat.com)
- Add copyright and fix (name) macro usage. (jortel@redhat.com)
- pulp-builtins, fine tuning. (jortel@redhat.com)

* Thu Jun 14 2012 Jeff Ortel <jortel@redhat.com> 0.0.296-1
- new package built with tito

* Fri Jun 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.295-1
- created.
