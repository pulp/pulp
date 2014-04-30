%global srcname billiard

%if 0%{?fedora} > 12 || 0%{?rhel} > 6
# We do not support Python 3, so we will not build Python 3 packages.
%global with_python3 0
%else
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}
%endif

%if 0%{?fedora} || 0%{?rhel} >= 7
%define billiard_tests 1
%else
# RHEL 6 doesn't have python-nose-cover3, which is required to run the tests
%define billiard_tests 0
%endif

Name:           python-%{srcname}
Version:        3.3.0.17
Release:        1%{?dist}
# We need this to be 1 for Fedora systems, since the official Fedora billiards package is epoch 1. If we don't
# that package will always be considered "newer" than ours, even when our version string is greater.
Epoch:          1
Summary:        Multiprocessing Pool Extensions

Group:          Development/Languages
License:        BSD
URL:            http://pypi.python.org/pypi/billiard
Source0:        http://pypi.python.org/packages/source/b/%{srcname}/%{srcname}-%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-mock
BuildRequires:  python-unittest2
BuildRequires:  python-nose

%if %{billiard_tests}
BuildRequires:  python-nose-cover3
%endif

%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-mock
BuildRequires:  python3-nose
%endif

%description
This package contains extensions to the multiprocessing Pool.

%if 0%{?with_python3}
%package -n python3-billiard
Summary:        Multiprocessing Pool Extensions
Group:          Development/Languages
Requires:       python3
BuildArch:      noarch
%description -n python3-billiard
This package contains extensions to the multiprocessing Pool.

%endif

%prep
%setup -q -n %{srcname}-%{version}

%if 0%{?with_python3}
cp -a . %{py3dir}
%endif

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py build
popd
%endif # with_python3

%install
%{__python} setup.py install --skip-build --root %{buildroot}
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root %{buildroot}
popd
%endif # with_python3

%if %{billiard_tests}
%check
%{__python} setup.py test

%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py test
popd
%endif # with_python3
%endif # billiard_tests

%files
%doc CHANGES.txt LICENSE.txt README.rst
%{python_sitearch}/_billiard*
%{python_sitearch}/%{srcname}/
%{python_sitearch}/%{srcname}*.egg-info
%exclude %{python_sitearch}/funtests/

%if 0%{?with_python3}
%files -n python3-billiard
%doc CHANGES.txt LICENSE.txt README.rst
%{python3_sitelib}/%{srcname}
%{python3_sitelib}/%{srcname}*.egg-info
%exclude %{python3_sitelib}/funtests/
%endif # with_python3

%changelog
* Mon Apr 21 2014 Randy Barlow <rbarlow@redhat.com> 3.3.0.17-1
- Update to python-billiard-3.3.0.17. (rbarlow@redhat.com)

* Thu Mar 13 2014 Randy Barlow <rbarlow@redhat.com> 3.3.0.16-3
- Change the logic for whether to run billiard tests. (rbarlow@redhat.com)

* Wed Mar 12 2014 Barnaby Court <bcourt@redhat.com> 3.3.0.16-2
- Don't require nose-3 on rhel6 since that package doesn't exist and we are
  skipping the unit tests on that dist (bcourt@redhat.com)
- fix if block (bcourt@redhat.com)
- Update to skip running the billiard unit tests on the rhel 6 builder
  (bcourt@redhat.com)
- Remove python-okaara since a newer version is in epel and add a dist_list.txt
  file with the list of distributions each dependency should be built for
  (bcourt@redhat.com)
- Update billiard 3 spec to add python-nose-cover3 (bcourt@redhat.com)
- Update dependency READMEs. (rbarlow@redhat.com)
- updating info about dependencies we build (mhrivnak@redhat.com)

* Thu Feb 20 2014 Randy Barlow <rbarlow@redhat.com> 3.3.0.16-1
- Raise python-billiard to version 3.3.0.16. (rbarlow@redhat.com)
- Refactor all sync/publish commands to use a common query builder.
  (rbarlow@redhat.com)
- Merge pull request #787 from pulp/mhrivnak-deps (mhrivnak@hrivnak.org)
- Deleting dependencies we no longer need and adding README files to explain
  why we are keeping the others. (mhrivnak@redhat.com)
- Don't build Python 3 versions of Celery and deps. (rbarlow@redhat.com)

* Mon Jan 27 2014 Randy Barlow <rbarlow@redhat.com> 3.3.0.13-1
- new package built with tito

* Tue Jan 07 2014 Randy Barlow <rbarlow@redhat.com> - 3.3.0.13-1
- update to 3.3.0.13.

* Thu Nov 21 2013 Matthias Runge <mrunge@redhat.com> - 3.3.0.7-1
- update to 3.3.0.7 (rhbz#1026722)

* Sat Nov 09 2013 Fabian Affolter <mail@fabian-affolter.ch> - 3.3.0.1-1
- Updated to latest upstream version 3.3.0.1 (rhbz#1026722)

* Mon Oct 28 2013 Fabian Affolter <mail@fabian-affolter.ch> - 3.3.0.0-1
- Updated to latest upstream version 3.3.0.0 (rhbz#1019144)

* Mon Oct 14 2013 Matthias Runge <mrunge@redhat.com> - 2.7.34-1
- update to 2.7.34 (rhbz#1018595)
- enable tests

* Tue Oct 08 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.33-1
- Updated to latest upstream version 2.7.3.33

* Sat Aug 17 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.32-1
- Updated to latest upstream version 2.7.3.32

* Wed Jul 31 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.31-1
- Updated to latest upstream version 2.7.3.31

* Sat Jun 29 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.30-1
- Updated to latest upstream version 2.7.3.30

* Wed Apr 17 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.28-1
- Updated to latest upstream version 2.7.3.28

* Tue Mar 26 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.23-1
- Updated to latest upstream version 2.7.3.23

* Sat Mar 09 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.22-1
- Updated to latest upstream version 2.7.3.22

* Wed Feb 13 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.21-1
- Updated to latest upstream version 2.7.3.21

* Mon Feb 11 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.20-1
- Updated to latest upstream version 2.7.3.20

* Sun Dec 02 2012 Matthias Runge <mrunge@redhat.com> - 2.7.3.19-1
- update to upstream version 2.7.3.19

* Tue Nov 06 2012 Matthias Runge <mrunge@redhat.com> - 2.7.3.18-1
- update to upstream version 2.7.3.18

* Fri Sep 28 2012 Matthias Runge <mrunge@redhat.com> - 2.7.3.17-1
- update to upstream version 2.7.3.17

* Thu Sep 20 2012 Matthias Runge <mrunge@redhat.com> - 2.7.3.14-1
- update to upstream version 2.7.3.14

* Sun Aug 26 2012 Matthias Runge <mrunge@matthias-runge.de> - 2.7.3.12-1
- update to new upstream version 2.7.3.12
- provide python3 packages
- enable checks

* Fri Aug 03 2012 Matthias Runge <mrunge@matthias-runge.de> 2.7.3.11-1
- update to new upstream version 2.7.3.11

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.7.3.9-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jun 19 2012 Fabian Affolter <mail@fabian-affolter.ch> - 2.7.3.9-1
- Updated to new upstream version 2.7.3.9

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sat Aug 14 2010 Fabian Affolter <mail@fabian-affolter.ch> - 0.3.1-2
- TODO removed

* Sat Jul 03 2010 Fabian Affolter <mail@fabian-affolter.ch> - 0.3.1-1
- Initial package
