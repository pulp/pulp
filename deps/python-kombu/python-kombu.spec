%if 0%{?fedora} > 12 || 0%{?rhel} > 6
# Pulp does not support Python 3, so we will not build the Python 3 package
%global with_python3 0
%else
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}
%endif

%global srcname kombu

Name:           python-%{srcname}
Version:        3.0.12
Release:        1%{?dist}
Summary:        AMQP Messaging Framework for Python

Group:          Development/Languages
# utils/functional.py contains a header that says Python
License:        BSD and Python
URL:            http://pypi.python.org/pypi/%{srcname}
Source0:        http://pypi.python.org/packages/source/k/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python2-devel
%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-nose
BuildRequires:  python3-setuptools
BuildRequires:  python3-anyjson
# for python3 tests. These require setuptools >= 0.7, so they cannot be run in F18
%if 0%{?fedora} > 18
BuildRequires:  python3-mock
BuildRequires:  python3-nose-cover3
BuildRequires:  python3-coverage
BuildRequires:  python3-nose
BuildRequires:  python3-mock
%endif
%endif # if with_python3

BuildRequires:  python-setuptools
BuildRequires:  python-nose
BuildRequires:  python-anyjson

# required for tests:
BuildRequires: python-unittest2
BuildRequires: python-mock
BuildRequires: python-simplejson
BuildRequires: PyYAML
BuildRequires: python-msgpack
BuildRequires: python-amqp >= 1.4.3

%if 0%{?with_python3}
BuildRequires: python3-amqp >= 1.4.3
%endif

# For documentation
#BuildRequires:  pymongo python-sphinx
#This causes tests error, needs fixing upstream. Incompatible with python > 2.7
#BuildRequires:  python-couchdb
Requires: python-amqp >= 1.4.3
Requires: python-amqp < 2.0
Requires: python-anyjson >= 0.3.3

%description
AMQP is the Advanced Message Queuing Protocol, an open standard protocol
for message orientation, queuing, routing, reliability and security.

One of the most popular implementations of AMQP is RabbitMQ.

The aim of Kombu is to make messaging in Python as easy as possible by
providing an idiomatic high-level interface for the AMQP protocol, and
also provide proven and tested solutions to common messaging problems.

%if 0%{?with_python3}
%package -n python3-kombu
Summary:        AMQP Messaging Framework for Python3
Group:          Development/Languages

Requires:       python3
Requires:       python3-amqp >= 1.4.3

%description -n python3-kombu
AMQP is the Advanced Message Queuing Protocol, an open standard protocol
for message orientation, queuing, routing, reliability and security.

One of the most popular implementations of AMQP is RabbitMQ.

The aim of Kombu is to make messaging in Python as easy as possible by
providing an idiomatic high-level interface for the AMQP protocol, and
also provide proven and tested solutions to common messaging problems.

This subpackage is for python3
%endif # with_python3

%prep
%setup -q -n %{srcname}-%{version}

# manage requirements on rpm base
sed -i 's/>=1.0.13,<1.1.0/>=1.3.0/' requirements/default.txt

%if 0%{?with_python3}
cp -a . %{py3dir}
%endif

%build
%{__python} setup.py build

# build python3-kombu
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

# Documentation in docs folder is not useful without doing a make
# Seems to have a circular dependency.  Not building for now
#cd docs && make html
#cd - && mv docs/.build/html htmldocs
#rm -rf docs
#rm -f htmldocs/.buildinfo

# sadly, tests don't succeed, yet
%check
%{__python} setup.py test
# tests with py3 are failing currently
%if 0%{?with_python3} && 0%{?fedora} > 18
pushd %{py3dir}
%{__python3} setup.py test
popd
%endif # with_python3

%files
%doc AUTHORS Changelog FAQ LICENSE READ* THANKS TODO examples/
%{python_sitelib}/%{srcname}/
%{python_sitelib}/%{srcname}*.egg-info

%if 0%{?with_python3}
%files -n python3-kombu
%doc AUTHORS Changelog FAQ LICENSE READ* THANKS TODO examples/
%{python3_sitelib}/*
%endif # with_python3

%changelog
* Mon Jan 27 2014 Randy Barlow <rbarlow@redhat.com> 3.0.8-1
- new package built with tito

* Tue Jan 07 2014 Randy Barlow <rbarlow@redhat.com> - 3.0.8-1
- update to 3.0.8.

* Fri Nov 22 2013 Matthias Runge <mrunge@redhat.com> - 3.0.6-1
- update to 3.0.6 and enable tests for py3 as well 

* Sun Nov 17 2013 Fabian Affolter <mail@fabian-affolter.ch> - 3.0.5-1
- Updated to latest upstream version 3.0.5 (rhbz#1024916)

* Sat Nov 16 2013 Fabian Affolter <mail@fabian-affolter.ch> - 3.0.4-1
- Updated to latest upstream version 3.0.4 (rhbz#1024916)

* Fri Nov 15 2013 Fabian Affolter <mail@fabian-affolter.ch> - 3.0.3-1
- Updated to latest upstream version 3.0.3 (rhbz#1024916)

* Sun Nov 03 2013 Fabian Affolter <mail@fabian-affolter.ch> - 3.0.2-1
- Updated to latest upstream version 3.0.2 (rhbz#1024916)

* Mon Oct 28 2013 Fabian Affolter <mail@fabian-affolter.ch> - 3.0.1-1
- Updated to latest upstream version 3.0.1 (rhbz#1019148)

* Mon Oct 14 2013 Matthias Runge <mrunge@redhat.com> - 2.5.15-2
- enable tests for python2

* Mon Oct 14 2013 Matthias Runge <mrunge@redhat.com> - 2.5.15-1
- updated to 2.5.15 (rhbz#1016271)

* Sun Aug 25 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.5.14-1
- Updated to latest upstream version 2.5.14 (rhbz#1000696)

* Wed Aug 21 2013 Matthias Runge <mrunge@redhat.com> - 2.5.13-1
- updated to latest upstream version 2.5.13 (rhbz#998104)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.5.12-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Sat Jun 29 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.5.12-1
- Updated to latest upstream version 2.5.12

* Mon Jun 24 2013 Rahul Sundaram <sundaram@fedoraproject.org> - 2.5.10-2
- add requires on python-amqp/python3-amqp. resolves rhbz#974684
- fix rpmlint warnings about macro in comments

* Sun Apr 21 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.5.10-1
- Updated to latest upstream version 2.5.10

* Sat Mar 23 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.5.8-1
- Updated to latest upstream version 2.5.8

* Sat Mar 09 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.5.7-1
- Updated to latest upstream version 2.5.7

* Mon Feb 11 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.5.6-1
- Updated to latest upstream version 2.5.6

* Sat Feb 09 2013 Fabian Affolter <mail@fabian-affolter.ch> - 2.5.5-1
- Updated to latest upstream version 2.5.5

* Thu Dec 13 2012 Matthias Runge <mrunge@redhat.com> - 2.5.4-1
- Update to upstream version 2.5.4 (rhbz#886001)

* Tue Dec 04 2012 Matthias Runge <mrunge@redhat.com> - 2.5.3-1
- Update to latest upstream version 2.5.3

* Mon Nov 26 2012 Matthias Runge <mrunge@redhat.com> - 2.4.10-1
- Update to latest upstream version 2.4.10

* Tue Nov 06 2012 Matthias Runge <mrunge@redhat.com> - 2.4.8-1
- update to new upstream version 2.4.8

* Thu Sep 20 2012 Matthias Runge <mrunge@redhat.com> - 2.4.7-1
- Update to new upstream version 2.4.7

* Sun Aug 26 2012 Matthias Runge <mrunge@matthias-runge.de> - 2.4.3-1
- Update to new upstream version 2.4.3

* Thu Aug 23 2012 Matthias Runge <mrunge@matthias-runge.de> - 2.4.0-1
- update to new upstream version 2.4.0

* Fri Aug 03 2012 Matthias Runge <mrunge@matthias-runge.de> - 2.3.2-1
- update to version 2.3.2
- enable tests
- require python2 and/or python3

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.1.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.1.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Fri Jul 15 2011 Rahul Sundaram <sundaram@fedoraproject.org> - 1.1.3-1
- initial spec.  
- derived from the one written by Fabian Affolter
- spec patch from Lakshmi Narasimhan

