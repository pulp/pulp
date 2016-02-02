%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-requests-toolbelt
Version:        0.6.0
Release:        1%{?dist}
Summary:        A toolbelt of useful classes and functions to be used with python-requests

Group:          Development/Tools
License:        ASL 2.0
URL:            http://pypi.python.org/pypi/requests-toolbelt
Source0:        https://pypi.python.org/packages/source/r/requests-toolbelt/requests-toolbelt-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch

BuildRequires:  python-setuptools
Requires:       python-requests

%description
A toolbelt of useful classes and functions to be used with python-requests

%prep
%setup -q -n requests-toolbelt-%{version}

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc LICENSE README.rst HISTORY.rst
%{python_sitelib}/requests_toolbelt
%{python_sitelib}/requests_toolbelt*.egg-info

%changelog
* Tue Feb 02 2016 Patrick Creech <pcreech@redhat.com> 0.6.0-1
- new package built with tito

* Tue Feb 02 2016 Patrick Creech <pcreech@redhat.com> 0.6.0-1
- Add requests-toolbelt dependency

