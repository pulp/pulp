%global srcname pkginfo
%global sum Query metadata from sdists / bdists / installed packages

Name:           python-%{srcname}
Version:        1.3.2
Release:        3%{?dist}
Summary:        %{sum}

# License is missing from the source repo: see https://bugs.launchpad.net/pkginfo/+bug/1591344
License:        Python
URL:            https://pypi.python.org/pypi/%{srcname}
Source0:        https://pypi.python.org/packages/bc/3e/046ec2439e233161f99d2f6cceb1ac49176612b6f6250cd6cb9919cda97a/pkginfo-1.3.2.tar.gz
# Upstream installs the test package, and we don't need to distribute that.
Patch0:         0001-Stop-installing-the-test-package.patch

BuildArch:      noarch
Requires:       python-setuptools
BuildRequires:  python2-devel
BuildRequires:  python-nose
BuildRequires:  python-sphinx10



%description
This package provides an API for querying the distutils metadata written in the
PKG-INFO file inside a source distribution (an sdist) or a binary distribution
(e.g., created by running bdist_egg). It can also query the EGG-INFO directory
of an installed distribution, and the *.egg-info stored in a "development
checkout" (e.g, created by running setup.py develop).


%package -n python-%{srcname}-doc
Summary:        Documentation for the python-%{srcname} packages

%description -n python-%{srcname}-doc
This package provides documentation for the Python pkginfo package. pkginfo
provides an API for querying the distutils metadata written in the PKG-INFO
file inside a source distribution (an sdist) or a binary distribution (e.g.,
created by running bdist_egg). It can also query the EGG-INFO directory of an
installed distribution, and the *.egg-info stored in a "development checkout"
(e.g, created by running setup.py develop).


%prep
%setup -q -n %{srcname}-%{version}
rm -rf *.egg-info

%patch0 -p1

%build
%{__python} setup.py build

cd docs
make %{?_smp_mflags} SPHINXBUILD=sphinx-1.0-build html

%install
%{__python} setup.py install --skip-build --root %{buildroot}
ln -s %{_bindir}/pkginfo %{buildroot}%{_bindir}/pkginfo-%{python_version}
ln -s %{_bindir}/pkginfo-%{python_version} %{buildroot}%{_bindir}/pkginfo-2

# Upstream ships a broken unit test: see https://bugs.launchpad.net/pkginfo/+bug/1591298
# Until that's fixed, skip testing.


%files -n python-%{srcname}
%doc README.txt CHANGES.txt
%{python_sitelib}/*
%{_bindir}/pkginfo
%{_bindir}/pkginfo-2
%{_bindir}/pkginfo-%{python_version}

%files -n python-%{srcname}-doc
%doc README.txt CHANGES.txt
%doc docs/.build/html/*

%changelog
* Fri Sep 23 2016 Ina Panova <ipanova@redhat.com> 1.3.2-3
- new package built version 1.3.2-3

* Wed Jul 20 2016 Jeremy Cline <jeremy@jcline.org> - 1.3.2-3
- Remove hard-coded Python y release versions in /usr/bin entries

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.3.2-2
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Thu Jun 09 2016 Jeremy Cline <jeremy@jcline.org> - 1.3.2-1
- Initial commit
