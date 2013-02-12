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


# ---- Pulp Citrus -------------------------------------------------------------

Name: pulp-citrus
Version: 2.1.0
Release: 0.5.alpha
Summary: Support for pulp citrus
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
mkdir -p %{buildroot}/%{_usr}/lib/pulp/agent/handlers
mkdir -p %{buildroot}/%{_var}/lib/pulp/citrus/published/http
mkdir -p %{buildroot}/%{_var}/lib/pulp/citrus/published/https
mkdir -p %{buildroot}/%{_var}/www/pulp/citrus

# Configuration
cp -R etc/pulp %{buildroot}/%{_sysconfdir}
cp -R etc/httpd %{buildroot}/%{_sysconfdir}

# Agent Handlers
cp handlers/* %{buildroot}/%{_usr}/lib/pulp/agent/handlers

# Plugins
cp -R plugins/* %{buildroot}/%{_usr}/lib/pulp/plugins

# WWW
ln -s %{_var}/lib/pulp/citrus/published/http %{buildroot}/%{_var}/www/pulp/citrus
ln -s %{_var}/lib/pulp/citrus/published/https %{buildroot}/%{_var}/www/pulp/citrus

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/*.egg-info

%clean
rm -rf %{buildroot}

%files
%{python_sitelib}/pulp_citrus/
%doc


# define required pulp platform version.
# pre-release package packages have dependencies based on both
# version and release.
%if %(echo %release | cut -f1 -d'.') < 1
%global pulp_version %{version}-%{release}
%else
%global pulp_version %{version}
%endif


# ---- Plugins -----------------------------------------------------------------

%package plugins
Summary: Pulp citrus support plugins
Group: Development/Languages
Requires: %{name} = %{version}
Requires: pulp-server = %{pulp_version}

%description plugins
Plugins to provide citrus support.

%files plugins
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_citrus.conf
%{_usr}/lib/pulp/plugins/types/citrus.json
%{_usr}/lib/pulp/plugins/importers/citrus_http_importer/
%{_usr}/lib/pulp/plugins/distributors/citrus_http_distributor/
%defattr(-,apache,apache,-)
%{_var}/lib/pulp/citrus
%{_var}/www/pulp/citrus
%doc

# ---- Agent Handlers ----------------------------------------------------------

%package handlers
Summary: Pulp agent rpm handlers
Group: Development/Languages
Requires: %{name} = %{version}
Requires: python-pulp-agent-lib = %{pulp_version}

%description handlers
Pulp citrus handlers.

%files handlers
%defattr(-,root,root,-)
%{_sysconfdir}/pulp/agent/conf.d/citrus.conf
%{_usr}/lib/pulp/agent/handlers/citrus.py*
%doc

%post
# Generate the certificate used to access the local server.

PKI=/etc/pki/pulp
PKI_CITRUS=$PKI/citrus
CA_KEY=$PKI/ca.key
CA_CRT=$PKI/ca.crt
BASE='citrus'
TMP=/tmp/$RANDOM
CN='admin:admin:0'
ORG='PULP'
ORG_UNIT='CITRUS'

mkdir -p $TMP
mkdir -p $PKI_CITRUS

# create client key
openssl genrsa -out $TMP/$BASE.key 2048 &> /dev/null

# create signing request for client
openssl req \
  -new \
  -key $TMP/$BASE.key \
  -out $TMP/$BASE.req \
  -subj "/CN=$CN/O=$ORG/OU=$ORG_UNIT" &> /dev/null

# sign server request w/ CA key and gen x.509 cert.
openssl x509 \
  -req  \
  -in $TMP/$BASE.req \
  -out $TMP/$BASE.xx \
  -sha1 \
  -CA $CA_CRT \
  -CAkey $CA_KEY \
  -CAcreateserial \
  -set_serial $RANDOM \
  -days 3650 &> /dev/null

# bundle
cat $TMP/$BASE.key $TMP/$BASE.xx > $PKI_CITRUS/local.crt

# clean
rm -rf $TMP

%postun
# clean up the citrus certificate.
if [ $1 -eq 0 ]; then
  rm /etc/pki/pulp/citrus/local.crt
fi


%changelog
* Tue Feb 12 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.5.alpha
- 

* Tue Feb 12 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.4.alpha
- 

* Tue Feb 05 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.3.alpha
- 

* Tue Feb 05 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.2.alpha
- 

* Mon Feb 04 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.1.alpha
- new package built with tito

