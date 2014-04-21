%if 0%{?fedora} > 12 || 0%{?rhel} > 6
# We do not support Python 3, so we will not build the Python 3 package
%global with_python3 0
%else
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}
%endif

Name:           python-celery
Version:        3.1.11
Release:        1%{?dist}
Summary:        Distributed Task Queue

Group:          Development/Languages
License:        BSD
URL:            http://celeryproject.org
Source0:        http://pypi.python.org/packages/source/c/celery/celery-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
Requires:       python-anyjson
Requires:       python-dateutil
Requires:       python-kombu >= 3.0.15
Requires:       python-setuptools
Requires:       pyparsing
Requires:       python-billiard >= 3.3.0.17
Requires:       python-amqp
Requires:	pytz
%if ! (0%{?fedora} > 13 || 0%{?rhel} > 6)
Requires:       python-importlib
%endif
%if ! (0%{?fedora} > 13 || 0%{?rhel} > 5)
Requires:       python-uuid
%endif

%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
%endif # if with_python3


%description
An open source asynchronous task queue/job queue based on
distributed message passing. It is focused on real-time
operation, but supports scheduling as well.

The execution units, called tasks, are executed concurrently
on one or more worker nodes using multiprocessing, Eventlet
or gevent. Tasks can execute asynchronously (in the background)
or synchronously (wait until ready).

Celery is used in production systems to process millions of
tasks a day.

Celery is written in Python, but the protocol can be implemented
in any language. It can also operate with other languages using
webhooks.

The recommended message broker is RabbitMQ, but limited support
for Redis, Beanstalk, MongoDB, CouchDB and databases
(using SQLAlchemy or the Django ORM) is also available.

%if 0%{?with_python3}
%package -n python3-celery
Summary:        Distributed Task Queue
Group:          Development/Languages

Requires:       python3
Requires:       python3-kombu >= 3.0.15
Requires:       python3-pytz
Requires:       python3-dateutil
Requires:       python3-billiard >= 3.3.0.17
Requires:       python3-amqp
%description -n python3-celery
An open source asynchronous task queue/job queue based on
distributed message passing. It is focused on real-time
operation, but supports scheduling as well.

The execution units, called tasks, are executed concurrently
on one or more worker nodes using multiprocessing, Eventlet
or gevent. Tasks can execute asynchronously (in the background)
or synchronously (wait until ready).

Celery is used in production systems to process millions of
tasks a day.

Celery is written in Python, but the protocol can be implemented
in any language. It can also operate with other languages using
webhooks.

The recommended message broker is RabbitMQ, but limited support
for Redis, Beanstalk, MongoDB, CouchDB and databases
(using SQLAlchemy or the Django ORM) is also available.

%endif # with_python3


%prep
%setup -q -n celery-%{version}

%if 0%{?with_python3}
cp -a . %{py3dir}
%endif


%build
%{__python} setup.py build
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py build
popd
%endif # with_python3


%install
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root %{buildroot}
# rename py3 binary
for i in celerybeat celeryd celeryd-multi celery; do
  mv %{buildroot}%{_bindir}/$i %{buildroot}%{_bindir}/py3-$i
done
popd
%endif # with_python3
%{__python} setup.py install -O1 --skip-build --root %{buildroot}


%files
%doc LICENSE README.rst TODO CONTRIBUTORS.txt docs examples
%{python_sitelib}/*
%{_bindir}/celery
%{_bindir}/celerybeat
%{_bindir}/celeryd
%{_bindir}/celeryd-multi

%if 0%{?with_python3}
%files -n python3-celery
%doc LICENSE README.rst TODO CONTRIBUTORS.txt docs examples
%{_bindir}/py3-celery
%{_bindir}/py3-celerybeat
%{_bindir}/py3-celeryd
%{_bindir}/py3-celeryd-multi
%{python3_sitelib}/*
%endif # with_python3


%changelog
* Mon Apr 21 2014 Randy Barlow <rbarlow@redhat.com> 3.1.11-1
- Upgrade to celery-3.1.11. (rbarlow@redhat.com)

* Fri Apr 11 2014 Brian Bouterse <bmbouter@gmail.com> 3.1.9-2.pulp
- Add patch manifest to python-celery spec file. (bmbouter@gmail.com)
- Updating patches for python-celery and python-kombu. (bmbouter@gmail.com)
- Remove python-okaara since a newer version is in epel and add a dist_list.txt
  file with the list of distributions each dependency should be built for
  (bcourt@redhat.com)
- Update dependency READMEs. (rbarlow@redhat.com)
- updating info about dependencies we build (mhrivnak@redhat.com)

* Thu Feb 20 2014 Randy Barlow <rbarlow@redhat.com> 3.1.9-1
- Raise Celery to version 3.1.9. (rbarlow@redhat.com)
- Merge pull request #787 from pulp/mhrivnak-deps (mhrivnak@hrivnak.org)
- Deleting dependencies we no longer need and adding README files to explain
  why we are keeping the others. (mhrivnak@redhat.com)
- Don't build Python 3 versions of Celery and deps. (rbarlow@redhat.com)

* Mon Jan 27 2014 Randy Barlow <rbarlow@redhat.com> 3.1.7-1
- new package built with tito

* Tue Jan 07 2014 Randy Barlow <rbarlow@redhat.com> - 3.1.7-1
- update to 3.1.7, add dependency on pytz, and adapt for Pulp usage.

* Mon Oct 14 2013 Matthias Runge <mrunge@redhat.com> - 3.0.24-1
- update to 3.0.24 (rhbz#1018596)

* Fri Sep 27 2013 Matthias Runge <mrunge@redhat.com> - 3.0.23-1
- update to 3.0.23 (rhbz#979595)

* Fri Sep 27 2013 Matthias Runge <mrunge@redhat.com> - 3.0.19-4
- add python-amqp to deps
- add requirement python-amqp
- fix requirements: python3-kombu, python3-pytz, python3-dateutil and billiard
- separate binaries for py3 and py (fixes rhbz#1000750)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.0.19-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Apr 23 2013 Matthias Runge <mrunge@redhat.com> - 3.0.19-1
- update to celery-3.0.19 (rhbz#919560)

* Fri Feb 15 2013 Matthias Runge <mrunge@redhat.com> - 3.0.15-1
- update to celery-3.0.15 (rhbz#909919)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.0.13-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Thu Jan 17 2013 Matthias Runge <mrunge@redhat.com> - 3.0.13-1
- update to upstream version 3.0.13 (rhbz#892923)

* Wed Nov 14 2012 Matthias Runge <mrunge@redhat.com> - 3.0.12-1
- update to upstream version 3.0.12

* Tue Oct 16 2012 Matthias Runge <mrunge@redhat.com> - 3.0.11-1
- update to upstream version 3.0.11

* Sun Aug 26 2012 Matthias Runge <mrunge@matthias-runge.de> - 3.0.7-1
- update to upstream version 3.0.7

* Thu Aug 23 2012 Matthias Runge <mrunge@matthias-runge.de> - 3.0.6-1
- update to upstream version 3.0.6

* Fri Aug 03 2012 Matthias Runge <mrunge@matthias-runge.de> - 3.0.5-1
- update to version 3.0.5
- enable python3 support

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.8-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.8-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Mon Nov 28 2011 Andrew Colin Kissa <andrew@topdog.za.net> - 2.2.8-1
- Security FIX CELERYSA-0001

* Fri Jul 15 2011 Andrew Colin Kissa <andrew@topdog.za.net> - 2.2.7-3
- Fix rpmlint errors
- Fix dependencies

* Sat Jun 25 2011 Andrew Colin Kissa <andrew@topdog.za.net> 2.2.7-2
- Update for RHEL6

* Tue Jun 21 2011 Andrew Colin Kissa <andrew@topdog.za.net> 2.2.7-1
- Initial package
