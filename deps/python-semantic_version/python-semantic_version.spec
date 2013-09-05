%define name semantic_version
%define version 2.2.0
%define unmangled_version 2.2.0
%define release 1.pulp

Name: python-%{name}
Version: %{version}
Release: %{release}
Summary: A library implementing the 'SemVer' scheme.

License: BSD
URL: http://github.com/rbarrois/python-semanticversion
Source0: v%{version}.tar.gz

BuildRequires: python2-devel
BuildArch: noarch

%description
This small python library provides a few tools to handle SemVer
(http://semver.org) in Python. It follows strictly the 2.0.0-rc1 version of the
SemVer scheme.

%prep
%setup -q -n python-semanticversion-%{unmangled_version}

%check
%{__python} setup.py test

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --root=$RPM_BUILD_ROOT


%files
%{python_sitelib}/semantic_version
%{python_sitelib}/semantic_version*.egg-info
%defattr(-,root,root)
%doc README LICENSE


%changelog
