# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

%define srcname mongoengine

Name:           python-%{srcname}
Version:        0.9.0
Release:        1%{?dist}
Summary:        A Python Document-Object Mapper for working with MongoDB

Group:          Development/Libraries
License:        MIT
URL:            https://github.com/MongoEngine/mongoengine
Source0:        %{srcname}-%{version}.tar.gz

Patch0:         remove-Pillow-as-test-requirement.patch

BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-sphinx
BuildRequires:  python-dateutil
BuildRequires:  python-pymongo
BuildRequires:  python-pymongo-gridfs
BuildRequires:  mongodb-server
BuildRequires:  mongodb
BuildRequires:  python-blinker
BuildRequires:  python-coverage
BuildRequires:  python-nose

%if 0%{?rhel} == 6
BuildRequires:  Django14
%else
BuildRequires:  python-django
%endif

Requires:       python-pymongo >= 2.7.1
Requires:       python-pymongo-gridfs >= 2.7.1
Requires:       python-blinker


%description
MongoEngine is an ORM-like layer on top of PyMongo.

%prep
%setup -q -n %{srcname}-%{version}
%patch0 -p1


%build
# Remove CFLAGS=... for noarch packages (unneeded)
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc docs AUTHORS LICENSE README.rst
# For noarch packages: sitelib
 %{python_sitelib}/*
# For arch-specific packages: sitearch
# %{python_sitearch}/*

%changelog
* Thu Jun 18 2015 Brian Bouterse <bbouters@redhat.com> - 0.9.0-1
- Updated to mongoengine to 0.9.0
- Created new patch to remove Pillow as a test requirement

* Wed Feb 18 2015 Yohan Graterol <yohangraterol92@gmail.com> - 0.8.4-3
- Built for EPEL7
* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.4-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Mon Aug 26 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.8.4-1
- New Version
* Mon Aug 12 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.8.3-1
- New version
* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.9-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Wed Mar 13 2013 Eduardo Echeverria  <echevemaster@gmail.com> - 0.7.9-5
- Fix setup.py (add python-pillow instead python-imaging)

* Mon Jan 28 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.7.9-4
- Add Requires: pymongo, python-gridfs for f17
- Add Requires: python-pymongo, python-pymongo-gridfs for f18+
- Add Requires: python-blinker, python-imaging

* Sun Jan 27 2013 Yohan Graterol <yohangraterol92@gamil.com> - 0.7.9-3
- Built and included test
- Add BuildRequires: python-django >= 1.3

* Sun Jan 27 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.7.9-2
- Built and included sphinx docs
- Add BuildRequires: python-sphinx, python-pymongo, pymongo-gridfs
- Add BuildRequires: python-coverage, python-nose

* Thu Jan 17 2013 Yohan Graterol <yohangraterol92@gmail.com> - 0.7.9-1
- Initial packaging