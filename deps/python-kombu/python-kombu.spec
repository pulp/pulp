%if 0%{?fedora} > 12 || 0%{?rhel} > 6
# Pulp does not support Python 3, so we will not build the Python 3 package
%global with_python3 0
%else
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}
%endif

%global srcname kombu

Name:           python-%{srcname}
# The Fedora package is using epoch 1, so we need to also do that to make sure ours gets installed
Epoch:          1
Version:        3.0.33
Release:        3.pulp%{?dist}
Summary:        AMQP Messaging Framework for Python

Group:          Development/Languages
# utils/functional.py contains a header that says Python
License:        BSD and Python
URL:            http://pypi.python.org/pypi/%{srcname}
Source0:        http://pypi.python.org/packages/source/k/%{srcname}/%{srcname}-%{version}.tar.gz
Patch0:         563.patch
Patch1:         1212200.patch
Patch2:         569.patch
BuildArch:      noarch

BuildRequires:  python2-devel
%if 0%{?rhel} == 6
BuildRequires:  python-ordereddict
BuildRequires:  python-importlib
%endif
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

BuildRequires:  python-anyjson
BuildRequires:  python-nose
BuildRequires:  python-setuptools

# required for tests:
BuildRequires: python-amqp >= 1.4.9
BuildRequires: python-mock
BuildRequires: python-msgpack
BuildRequires: python-qpid
BuildRequires: python-qpid-qmf
BuildRequires: qpid-tools
BuildRequires: python-simplejson
%if 0%{?fedora} >= 21
# require the newer python-unittest2 if we are building on fedora 21 or greater
BuildRequires: python-unittest2 >= 0.8.0
%else
BuildRequires: python-unittest2
%endif
BuildRequires: PyYAML

%if 0%{?with_python3}
BuildRequires: python3-amqp >= 1.4.9
%endif

# For documentation
#BuildRequires:  pymongo python-sphinx
#This causes tests error, needs fixing upstream. Incompatible with python > 2.7
#BuildRequires:  python-couchdb
Requires: python-amqp >= 1.4.9
Requires: python-amqp < 2.0
Requires: python-anyjson >= 0.3.3
%if 0%{?rhel} == 6
Requires:  python-ordereddict
%endif

%description
AMQP is the Advanced Message Queuing Protocol, an open standard protocol
for message orientation, queuing, routing, reliability and security.

One of the most popular implementations of AMQP is RabbitMQ.

The aim of Kombu is to make messaging in Python as easy as possible by
providing an idiomatic high-level interface for the AMQP protocol, and
also provide proven and tested solutions to common messaging problems.

%if 0%{?with_python3}
%package -n python3-kombu
Epoch:          1
Summary:        AMQP Messaging Framework for Python3
Group:          Development/Languages

Requires:       python3
Requires:       python3-amqp >= 1.4.9

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

%if 0%{?rhel} == 6
%patch1 -p1
%endif

%patch0 -p1
%patch2 -p1

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
* Tue Feb 09 2016 Patrick Creech <pcreech@redhat.com> 3.0.33-3.pulp
- Add kombu patch for reconnect issue (pcreech@redhat.com)

* Mon Feb 08 2016 Patrick Creech <pcreech@redhat.com> 3.0.33-2.pulp
- Add patch back to kombu (pcreech@redhat.com)

* Wed Feb 03 2016 Patrick Creech <pcreech@redhat.com> 3.0.33-1.pulp
- Upgrade python-kombu dep to 3.0.33 (pcreech@redhat.com)

* Mon Jan 25 2016 Brian Bouterse <bbouters@redhat.com> 3.0.24-11.pulp
- Upgrades kombu to 3.0.24-11 (bbouters@redhat.com)
- Adds upstream equivalent patch for kombu/celery#563
- Adds fc23 to dist_list.txt config and removes fc21. (dkliban@redhat.com)
- Upgrades kombu to 3.0.24-10 (bbouters@redhat.com)
- Patches downstream Kombu with login_method support (bbouters@redhat.com)
- Adjusts Qpid broker string and includes Kombu SASL fixes.
  (bbouters@redhat.com)
- Remove FC20 from dist_lists.txt (dkliban@redhat.com)
- Added fc22 to dist_list.txt for pulp and dependencies (dkliban@redhat.com)
- Removed F22 from dist_list (dkliban@redhat.com)
- Fixes 917 and 1006 by stopping an thread that should have exited
  (bbouters@redhat.com)
- Added Fedora 22 to the dist list (dkliban@redhat.com)
- Fixes a file descriptor leak in python-kombu (bbouters@redhat.com)
- Kombu SASL connection, connection closing, and python dep fixes
  (bbouters@redhat.com)

* Tue Feb 03 2015 Brian Bouterse 3.0.24-5.pulp
- 1174361 - Revert patch introduced with b0f2319. It is not needed.
  (bbouters@redhat.com)

* Fri Jan 16 2015 Chris Duryee <cduryee@redhat.com> 3.0.24-4.pulp
- 1182322 - handle case where PLAIN is used with saslwrapper
  (cduryee@redhat.com)

* Wed Jan 14 2015 Chris Duryee <cduryee@redhat.com> 3.0.24-4.pulp
- add a patch for RHBZ #1182322

* Mon Jan 05 2015 Chris Duryee <cduryee@redhat.com> 3.0.24-3.pulp
- Conditionally require python-unittest2 >= 0.8.0 (cduryee@redhat.com)

* Tue Dec 23 2014 Chris Duryee <cduryee@redhat.com> 3.0.24-2.pulp
- Adds fix for 1174361 to python-kombu and bumps release (bmbouter@gmail.com)
- Build updates for Fedora 21. (cduryee@redhat.com)

* Thu Dec 11 2014 Brian Bouterse 3.0.24-1
- Updates python-kombu to 3.0.24 (bbouters@redhat.com)

* Fri Sep 19 2014 Chris Duryee <cduryee@redhat.com> 3.0.15-13.pulp
- 1124589 - python-kombu does not work with Qpid unless the user adjusts
  qpidd.conf (cduryee@redhat.com)

* Tue Aug 05 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.15-12.pulp
- Adds qpid-tools as a build dep for all environments. (bmbouter@gmail.com)

* Thu Jul 10 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.15-11.pulp
- Release 11 of python-kombu includes BZ fixes for 1096539 and 1105195.
  (bmbouter@gmail.com)

* Fri Jun 06 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.15-10.pulp
- Removing PropertyMock from test code. (bmbouter@gmail.com)

* Fri Jun 06 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.15-9.pulp
- Testing build of python-kombu-3.0.15-9.pulp (bmbouter@gmail.com)
- Remove the Requires on python-qpid-qmf from our Kombu package.
  (rbarlow@redhat.com)

* Tue May 27 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.15-8.pulp
- Fix test compatability for Python 2.6 (bmbouter@gmail.com)

* Tue May 27 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.15-7.pulp
- Adds new qpid patch for synchronous transport, and bumps spec file.
  (bmbouter@gmail.com)

* Fri May 23 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.15-6.pulp
- Testing new Patch for Kombu that may fix NoAvailableQueues issue.
  (bmbouter@gmail.com)
- Build for EL 7. (rbarlow@redhat.com)

* Wed May 07 2014 Randy Barlow <rbarlow@redhat.com> 3.0.15-5.pulp
- Update to the latest qpid patch. (rbarlow@redhat.com)

* Thu Apr 24 2014 Randy Barlow <rbarlow@redhat.com> 3.0.15-4.pulp
- Add a BuildRequires on python-qpid. (rbarlow@redhat.com)

* Thu Apr 24 2014 Randy Barlow <rbarlow@redhat.com> 3.0.15-3.pulp
- Update the qpid_transport.patch. (rbarlow@redhat.com)

* Mon Apr 21 2014 Randy Barlow <rbarlow@redhat.com> 3.0.15-2.pulp
- Added a patch to skip some Redis tests. (rbarlow@redhat.com)

* Mon Apr 21 2014 Randy Barlow <rbarlow@redhat.com> 3.0.15-1.pulp
- Upgrade to kombu-3.0.15. (rbarlow@redhat.com)
- New qpid patch for kombu and bump release. (bmbouter@gmail.com)

* Fri Apr 11 2014 Brian Bouterse <bmbouter@gmail.com> 3.0.13-3.pulp
- Disabling two tests temporarily to get tito to build successfully.
  (bmbouter@gmail.com)
- Updating patches for python-celery and python-kombu. (bmbouter@gmail.com)
- Added latest qpid patch to python-kombu and bumped the release.
  (bmbouter@gmail.com)

* Wed Mar 12 2014 Barnaby Court <bcourt@redhat.com> 3.0.13-1.pulp
- Updating with latest stable qpid patch (bmbouter@gmail.com)
- Bump the Release of python-kombu to match the previously built version
  (bcourt@redhat.com)
- Automatic commit of package [python-kombu] minor release [3.0.12-4].
  (bcourt@redhat.com)
- add python-importlib to build requirements for rhel6 (bcourt@redhat.com)
- Update to include requirement of python-ordereddict on rhel6 which has python
  2.6 installed (bcourt@redhat.com)
- Automatic commit of package [python-kombu] minor release [3.0.12-3].
  (bcourt@redhat.com)
- Bump release and add epoch to sub package (bcourt@redhat.com)
- Bumped kombu version to 3.0.13 (bmbouter@gmail.com)
- Merge branch 'bmbouter-kombu-qpid' (bmbouter@gmail.com)
- Added pulp to release field of python-kombu (bmbouter@gmail.com)
- Updating python-kombu README (bmbouter@gmail.com)
- changing name based on review (mhrivnak@redhat.com)
- updating info about dependencies we build (mhrivnak@redhat.com)

* Tue Mar 11 2014 Barnaby Court <bcourt@redhat.com> 3.0.12-4
- add python-importlib to build requirements for rhel6 (bcourt@redhat.com)
- Update for rhel6 mock builder support (bcourt@redhat.com)
- Update for rhel6 mock builder support (bcourt@redhat.com)
- Update for rhel6 mock builder support (bcourt@redhat.com)
- Update to include requirement of python-ordereddict on rhel6 which has python
  2.6 installed (bcourt@redhat.com)

* Tue Mar 11 2014 Barnaby Court <bcourt@redhat.com> 3.0.12-3
- Update for to add epoch (bcourt@redhat.com)
- Bump release and add epoch to sub package (bcourt@redhat.com)
- changing name based on review (mhrivnak@redhat.com)
- updating info about dependencies we build (mhrivnak@redhat.com)
- Remove duplicate entries from python-kombu.spec's changelog.
  (rbarlow@redhat.com)
- Automatic commit of package [python-kombu] minor release [3.0.12-1].
  (rbarlow@redhat.com)
- Raise the python-kombu epoch to 1 to match the Fedora package's epoch.
  (rbarlow@redhat.com)

* Tue Mar 11 2014 Barnaby Court <bcourt@redhat.com>
- Bump release and add epoch to sub package (bcourt@redhat.com)
- changing name based on review (mhrivnak@redhat.com)
- updating info about dependencies we build (mhrivnak@redhat.com)
- Remove duplicate entries from python-kombu.spec's changelog.
  (rbarlow@redhat.com)
- Automatic commit of package [python-kombu] minor release [3.0.12-1].
  (rbarlow@redhat.com)
- Raise the python-kombu epoch to 1 to match the Fedora package's epoch.
  (rbarlow@redhat.com)

* Thu Mar 06 2014 Randy Barlow <rbarlow@redhat.com> 3.0.12-2
- Patch python-kombu for qpid support. (rbarlow@redhat.com)
- removing Travis section from diff (bmbouter@gmail.com)
- Adding patch that adds Qpid support to Kombu (bmbouter@gmail.com)
- Remove duplicate entries from python-kombu.spec's changelog.
  (rbarlow@redhat.com)

* Mon Feb 24 2014 Randy Barlow <rbarlow@redhat.com> 3.0.12-1
- Raise the python-kombu epoch to 1 to match the Fedora package's epoch.
  (rbarlow@redhat.com)
- Automatic commit of package [python-kombu] minor release [3.0.12-1].
  (rbarlow@redhat.com)
- Raise Kombu to version 3.0.12. (rbarlow@redhat.com)
- Merge pull request #787 from pulp/mhrivnak-deps (mhrivnak@hrivnak.org)
- Deleting dependencies we no longer need and adding README files to explain
  why we are keeping the others. (mhrivnak@redhat.com)
- Don't build Python 3 versions of Celery and deps. (rbarlow@redhat.com)
- Merge branch 'distributed-tasks' into rbarlow-package_distributed_tasks
  (rbarlow@redhat.com)

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

