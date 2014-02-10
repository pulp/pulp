%if 0%{?fedora} > 12 || 0%{?rhel} > 6
# We don't want to build Python 3 versions of our dependencies, since we would not QE them
%global with_python3 0
%else
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}
%endif

%global srcname anyjson

Name:           python-%{srcname}
Version:        0.3.3
Release:        4%{?dist}
Summary:        Wraps the best available JSON implementation available

Group:          Development/Languages
License:        BSD
URL:            http://pypi.python.org/pypi/anyjson
Source0:        http://pypi.python.org/packages/source/a/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools

%description
Anyjson loads whichever is the fastest JSON module installed and
provides a uniform API regardless of which JSON implementation is used.

%if 0%{?with_python3}
%package -n python3-%{srcname}
Summary:        Wraps the best available JSON implementation available
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%description -n python3-%{srcname}
Anyjson loads whichever is the fastest JSON module installed and
provides a uniform API regardless of which JSON implementation is used.
%endif

%prep
%setup -q -n %{srcname}-%{version}
%if 0%{?with_python3}
cp -a . %{py3dir}
%endif

%build
%{__python} setup.py build
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py build
popd
%endif

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root %{buildroot}
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root %{buildroot}
popd
%endif
 
%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc CHANGELOG LICENSE README
%{python_sitelib}/%{srcname}/
%{python_sitelib}/%{srcname}*.egg-info

%if 0%{?with_python3}
%files -n python3-%{srcname}
%doc CHANGELOG LICENSE README
%{python3_sitelib}/%{srcname}/
%{python3_sitelib}/%{srcname}*.egg-info
%endif

%changelog
* Mon Jan 27 2014 Randy Barlow <rbarlow@redhat.com> 0.3.3-4
- new package built with tito

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.3-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Sat Aug 04 2012 David Malcolm <dmalcolm@redhat.com> - 0.3.3-2
- rebuild for https://fedoraproject.org/wiki/Features/Python_3.3

* Fri Aug 03 2012 Matthias Runge <mrunge@matthias-runge.de> - 0.3.3-1
- update to 0.3.3

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jan 31 2012 Fabian Affolter <mail@fabian-affolter.ch> - 0.3.1-3
- Minor py3 fixes

* Sun Jan 29 2012 Haïkel Guémar <hguemar@fedoraproject.org> - 0.3.1-2
- add python3 variant

* Sun Apr 03 2011 Fabian Affolter <fabian@bernewireless.net> - 0.3.1-1
- Updated to new upstream version 0.3.1

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Thu Jan 27 2011 Fabian Affolter <fabian@bernewireless.net> - 0.3-1
- Updated to new upstream version 0.3

* Sat Jul 31 2010 Orcan Ogetbil <oget[dot]fedora[at]gmail[dot]com> - 0.2.4-2
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Sat Jul 03 2010 Fabian Affolter <fabian@bernewireless.net> - 0.2.4-1
- Initial package
