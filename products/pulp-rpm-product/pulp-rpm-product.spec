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


# ---- Pulp (plus) RPM Product---------------------------------------------------------

Name: pulp-rpm-product
Version: 0.0.305
Release: 1%{?dist}
License: GPLv2
Summary: Pulp (plus) RPM product metapackage
Group: Virtual groups/Pulp
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildArch: noarch

%description
The Pulp (plus) RPM product metapackage.

%prep
%setup -q

%build

%install

%post
rpm -e %{name}

%clean



# ---- Pulp (plus) RPM Server --------------------------------------------------

%package -n pulp-rpm-server
Summary: The Pulp (plus) RPM server metapackage
Requires: pulp-server = %{version}
Requires: pulp-rpm-plugins = %{version}

%description -n pulp-rpm-server
The Pulp (plus) RPM metapackage used to install packages needed
to provide the Pulp platform (plus) RPM support packages.

%files -n pulp-rpm-server


# ---- Pulp (plus) RPM Admin Client --------------------------------------------

%package -n pulp-rpm-admin-client
Summary: The Pulp (plus) RPM admin client metapackage
Requires: pulp-admin-client = %{version}
Requires: pulp-rpm-admin-extensions = %{version}

%description -n pulp-rpm-admin-client
The Pulp (plus) RPM metapackage used to install packages needed
to provide the Pulp admin client (plus) RPM extensions.

%files -n pulp-rpm-admin-client


# ---- Pulp (plus) RPM Admin Client --------------------------------------------

%package -n pulp-rpm-consumer-client
Summary: The Pulp (plus) RPM consumer client metapackage
Requires: pulp-consumer-client = %{version}
Requires: pulp-rpm-consumer-extensions = %{version}

%description -n pulp-rpm-consumer-client
The Pulp (plus) RPM metapackage used to install packages needed
to provide the Pulp consumer client (plus) RPM extensions.

%files -n pulp-rpm-consumer-client


# ---- Pulp (plus) RPM Agent ---------------------------------------------------

%package -n pulp-rpm-agent
Summary: The Pulp (plus) RPM agent metapackage
Requires: pulp-agent = %{version}
Requires: pulp-rpm-handlers = %{version}

%description -n pulp-rpm-agent
The Pulp (plus) RPM metapackage used to install packages needed
to provide the Pulp agent (plus) RPM handlers.

%files -n pulp-rpm-agent



%changelog
* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.305-1
- 

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.304-1
- 

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.303-1
- 

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.302-1
- 

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.301-1
- 

* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.300-1
- Align versions to: 300 (jortel@redhat.com)
- product .spec build fixes. (jortel@redhat.com)

* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.298-1
- Add pulp (plus) rpm product metapackage. (jortel@redhat.com)

* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.297-1
- new package built with tito
