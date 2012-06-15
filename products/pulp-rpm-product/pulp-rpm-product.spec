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


# ---- Pulp+RPM Product---------------------------------------------------------

Name: pulp-rpm-product
Version: 0.0.297
Release: 1%{?dist}
License: GPLv2
Summary: Pulp+RPM product metapackage
URL: https://fedorahosted.org/pulp/
Requires: rpm-python

%description
The Pulp+RPM product metapackage

%prep

%build

%install

%clean

%post
rpm -e %{name}


# ---- Pulp+RPM Server ---------------------------------------------------------

%package -n pulp-rpm-server
Summary: The Pulp+RPM server metapackage
Requires: pulp-server = %{version}
Requires: pulp-rpm-plugins = %{version}

%description -n pulp-rpm-server
The Pulp+RPM metapackage used to install packages needed
to provide the Pulp platform (plus) RPM support packages.


# ---- Pulp+RPM Admin Client ---------------------------------------------------

%package -n pulp-rpm-admin-client
Summary: The Pulp+RPM admin client metapackage
Requires: pulp-admin-client = %{version}
Requires: pulp-rpm-admin-extensions = %{version}

%description -n pulp-rpm-admin-client
The Pulp+RPM metapackage used to install packages needed
to provide the Pulp admin client (plus) RPM extensions.


# ---- Pulp+RPM Admin Client ---------------------------------------------------

%package -n pulp-rpm-consumer-client
Summary: The Pulp+RPM consumer client metapackage
Requires: pulp-consumer-client = %{version}
Requires: pulp-rpm-consumer-extensions = %{version}

%description -n pulp-rpm-consumer-client
The Pulp+RPM metapackage used to install packages needed
to provide the Pulp consumer client (plus) RPM extensions.


# ---- Pulp+RPM Agent ---------------------------------------------------

%package -n pulp-rpm-agent
Summary: The Pulp+RPM agent metapackage
Requires: pulp-agent = %{version}
Requires: pulp-rpm-handlers = %{version}

%description -n pulp-rpm-agent
The Pulp+RPM metapackage used to install packages needed
to provide the Pulp agent (plus) RPM handlers.


%changelog
* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.297-1
- new package built with tito

