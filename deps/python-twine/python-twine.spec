%global srcname twine

Name:           python-%{srcname}
Version:        1.6.5
Release:        1%{?dist}
Summary:        Collection of utilities for interacting with PyPI

License:        ASL 2.0
URL:            https://github.com/pypa/%{srcname}
Source0:        %{url}/archive/%{version}/%{srcname}-%{version}.tar.gz
# There's a shebang in twine/__main__.py which generates rpmlint warnings.
Patch0:         0001-Remove-shebang-from-__main__.py.patch

BuildArch:      noarch
Requires:       python-pkginfo >= 1.0
Requires:       python-requests >= 2.3.0
Requires:       python-requests-toolbelt >= 0.5.1
Requires:       python-setuptools >= 0.7.0

BuildRequires:  python-setuptools

%description
Twine is a utility for interacting with PyPI.
Currently it only supports registering projects and uploading distributions.

%prep
%setup -q -n %{srcname}-%{version}

%patch0 -p1

%build
%{__python} setup.py build

%install
%{__python} setup.py install --skip-build --root %{buildroot}
ln -s %{_bindir}/twine %{buildroot}%{_bindir}/twine-%{python_version}
ln -s %{_bindir}/twine-%{python_version} %{buildroot}%{_bindir}/twine-2

%files -n python-%{srcname}
%doc README.rst AUTHORS
%{python_sitelib}/*
%{_bindir}/twine
%{_bindir}/twine-2
%{_bindir}/twine-%{python_version}


%changelog
* Fri Sep 23 2016 Ina Panova <ipanova@redhat.com> 1.6.5-1
- package version built 1.6.5-1

* Mon Aug 08 2016 Jeremy Cline <jcline@redhat.com> - 1.6.5-1
- Initial commit
