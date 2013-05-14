%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from %distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-nectar
Version:        0.90.0
Release:        1%{?dist}
Summary:        Performance tuned network download client library

Group:          Development/Tools
License:        GPLv2
URL:            https://github.com/pulp/nectar
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch

BuildRequires:  python-mock
BuildRequires:  python-nose
BuildRequires:  python-setuptools

Requires:       python-eventlet >= 0.12.0
Requires:       python-isodate >= 0.4.9
Requires:       python-pycurl >= 7.19.0
Requires:       python-requests >= 1.2.0
# RHEL6 ONLY
%if 0%{?rhel} == 6
Requires: curl => 7.19.0
%endif

%description
%{summary}

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%check
nosetests test/unit/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%{python_sitelib}/nectar/
%{python_sitelib}/nectar*.egg-info
%doc LICENSE.txt

%changelog
* Mon May 13 2013 Jason L Connor (jconnor@redhat.com) 0.90.0-1
- brought in new revent downloader to replace old eventlet downloader
- bumped version in preparation of 1.0.0 release

* Wed May 08 2013 Jason L Connor (jconnor@redhat.com) 0.0.90-1
- cut project from pulp
- initial spec file and setup.py

