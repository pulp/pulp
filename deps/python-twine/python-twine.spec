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

%description
Twine is a utility for interacting with PyPI.
Currently it only supports registering projects and uploading distributions.


%package -n python2-%{srcname}
Summary:        %{summary}
Requires:       python-pkginfo >= 1.0
Requires:       python-requests >= 2.3.0
Requires:       python-requests-toolbelt >= 0.5.1
Requires:       python-setuptools >= 0.7.0
# Test requirements
BuildRequires:  python-devel
BuildRequires:  python-pkginfo >= 1.0
BuildRequires:  python-requests >= 2.3.0
BuildRequires:  python-requests-toolbelt >= 0.5.1
BuildRequires:  python-setuptools >= 0.7.0
%{?python_provide:%python_provide python2-%{srcname}}

%description -n python2-%{srcname}
Twine is a utility for interacting with PyPI.
Currently it only supports registering projects and uploading distributions.


%prep
%autosetup -p1 -n %{srcname}-%{version}


%build
%py2_build


%install
%py2_install
ln -s %{_bindir}/twine %{buildroot}%{_bindir}/twine-%{python2_version}
ln -s %{_bindir}/twine-%{python2_version} %{buildroot}%{_bindir}/twine-2


%check
%{__python2} setup.py test


%files -n python2-%{srcname}
%license LICENSE
%doc README.rst AUTHORS
%{python2_sitelib}/*
%{_bindir}/twine
%{_bindir}/twine-2
%{_bindir}/twine-%{python2_version}


%changelog
* Mon Aug 08 2016 Jeremy Cline <jcline@redhat.com> - 1.6.5-1
- Initial commit
