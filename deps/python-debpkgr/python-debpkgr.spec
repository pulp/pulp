%global srcname debpkgr

%if 0%{?fedora}
%global with_python3 1
%global python2_prefix python2
%endif

%if 0%{?rhel}
%global python2_prefix python
%endif

Summary: "Debian/Ubuntu .deb pkg utils"
Name: python-%{srcname}
Version: 1.0.1
Release: 1%{?dist}
Source0: https://files.pythonhosted.org/packages/source/d/%{srcname}/%{srcname}-%{version}.tar.gz
Patch0: fix-dependencies.patch

License: ASL 2.0
Group: Development/Libraries
BuildArch: noarch
Vendor: Brett Smith <bc.smith@sas.com>
Url: https://github.com/sassoftware/python-debpkgr

%description
Pure Python implementation of Debian/Ubuntu packaging and repository utilities.

The allows one to perform various Debian-specific operations on
non-Debian systems, in the absence of typical system-provided
utilities (e.g. apt).

%package -n python2-%{srcname}
Summary: "Debian/Ubuntu .deb pkg utils"
Requires: python-debian
Requires: %{python2_prefix}-six
BuildRequires: %{python2_prefix}-devel
BuildRequires: %{python2_prefix}-setuptools
BuildRequires: %{python2_prefix}-pbr
%{?python_provide:%python_provide python2-%{srcname}}
%{?rhel:Provides: python-%{srcname}}


%description -n python2-%{srcname}
Pure Python implementation of Debian/Ubuntu packaging and repository utilities.

The allows one to perform various Debian-specific operations on
non-Debian systems, in the absence of typical system-provided
utilities (e.g. apt).

%if 0%{?with_python3}
%package -n python3-%{srcname}
Summary: "Debian/Ubuntu .deb pkg utils"
Requires: python3-debian
Requires: python3-six
BuildRequires: python3-devel
BuildRequires: python3-setuptools
BuildRequires: python3-pbr
%{?python_provide:%python_provide python3-%{srcname}}

%description -n python3-%{srcname}
Pure Python implementation of Debian/Ubuntu packaging and repository utilities.

The allows one to perform various Debian-specific operations on
non-Debian systems, in the absence of typical system-provided
utilities (e.g. apt).

%endif

%prep
%setup -q -n %{srcname}-%{version}
%patch0 -p1

%build
%{__python2} setup.py build

%if 0%{?with_python3}
%{__python3} setup.py build
%endif

%install
%{__python2} setup.py install --root=$RPM_BUILD_ROOT

%if 0%{?with_python3}
%{__python3} setup.py install --root=$RPM_BUILD_ROOT
%endif

%files -n python2-%{srcname}
%license LICENSE
%doc AUTHORS ChangeLog README.rst TODO
%{python2_sitelib}/%{srcname}/
%{python2_sitelib}/%{srcname}*.egg-info

%if 0%{?with_python3}
%files -n python3-%{srcname}
%license LICENSE
%doc AUTHORS ChangeLog README.rst TODO
%{python3_sitelib}/%{srcname}/
%{python3_sitelib}/%{srcname}*.egg-info
%endif

%changelog
* Fri Jul 07 2017 Patrick Creech <pcreech@redhat.com> - 1.0.1-1
- Initial build for pulp


