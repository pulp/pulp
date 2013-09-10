Name: python-semantic-version
Version: 2.2.0
Release: 1%{?dist}
Summary: A library implementing the 'SemVer' scheme.

License: BSD
URL: http://github.com/rbarrois/python-semanticversion
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: python2-devel

BuildArch: noarch

%description
This small python library provides a few tools to handle SemVer
(http://semver.org) in Python. It follows strictly the 2.0.0-rc1 version of the
SemVer scheme.

%prep
%setup -q -n python-semanticversion-%{version}

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
* Tue Sep 10 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-1
- new package built with tito



