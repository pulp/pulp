%if 0%{?fedora} > 12 || 0%{?rhel} > 6
# Since we do not support Python 3, we will not build Python 3 packages
%global with_python3 0
%global sphinx_docs 1
%else
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}
%global sphinx_docs 0
# These Sphinx docs do not build with python-sphinx 0.6 (el6)
%endif

%global srcname amqp

Name:           python-%{srcname}
Version:        1.4.5
Release:        1%{?dist}
Summary:        Low-level AMQP client for Python (fork of amqplib)

Group:          Development/Languages
License:        LGPLv2+
URL:            http://pypi.python.org/pypi/amqp
Source0:        http://pypi.python.org/packages/source/a/%{srcname}/%{srcname}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose
%if 0%{?sphinx_docs}
BuildRequires:  python-sphinx >= 0.8
%endif


%description
Low-level AMQP client for Python

This is a fork of amqplib, maintained by the Celery project.

This library should be API compatible with librabbitmq.

%if 0%{?with_python3}
%package -n python3-%{srcname}
Summary:        Client library for AMQP
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-nose
%if 0%{?sphinx_docs}
BuildRequires:  python3-sphinx >= 0.8
%endif

%description -n python3-%{srcname}
Low-level AMQP client for Python

This is a fork of amqplib, maintained by the Celery project.

This library should be API compatible with librabbitmq.

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
%{__python} setup.py install --skip-build --root %{buildroot}
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root %{buildroot}
popd
%endif

# docs generation requires everything to be installed first
export PYTHONPATH="$( pwd ):$PYTHONPATH"

# Remove execute bit from example scripts (packaged as doc)
chmod -x demo/*.py

%if 0%{?sphinx_docs}
pushd docs

# Disable extensions to prevent intersphinx from accessing net during build.
# Other extensions listed are not used.
sed -i s/^extensions/disable_extensions/ conf.py

SPHINX_DEBUG=1 sphinx-build -b html . build/html
rm -rf build/html/.doctrees build/html/.buildinfo

popd
%endif

%files
%doc Changelog LICENSE README.rst
%{python_sitelib}/%{srcname}/
%{python_sitelib}/%{srcname}*.egg-info

%if 0%{?with_python3}
%files -n python3-%{srcname}
%doc Changelog LICENSE README.rst
%{python3_sitelib}/%{srcname}/
%{python3_sitelib}/%{srcname}*.egg-info
%endif

%package doc
Summary:        Documentation for python-amqp
Group:          Documentation
License:        LGPLv2+

Requires:       %{name} = %{version}-%{release}

%description doc
Documentation for python-amqp

%files doc
%doc LICENSE demo/
%if 0%{?sphinx_docs}
%doc docs/build/html docs/reference
%endif


%changelog
* Mon Apr 21 2014 Randy Barlow <rbarlow@redhat.com> 1.4.5-1
- Update to python-amqp-1.4.5. (rbarlow@redhat.com)

* Wed Mar 05 2014 Randy Barlow <rbarlow@redhat.com> 1.4.4-1
- Update to amqp-1.4.4. (rbarlow@redhat.com)
- Remove a duplicate block from the changelog on amqp. (rbarlow@redhat.com)

* Thu Feb 20 2014 Randy Barlow <rbarlow@redhat.com> 1.4.3-1
- Raise python-amqp to 1.4.3. (rbarlow@redhat.com)
- Merge pull request #787 from pulp/mhrivnak-deps (mhrivnak@hrivnak.org)
- Deleting dependencies we no longer need and adding README files to explain
  why we are keeping the others. (mhrivnak@redhat.com)
- Remove a stray space from python-amqp.spec (rbarlow@redhat.com)
- Don't build Python 3 versions of Celery and deps. (rbarlow@redhat.com)

* Mon Jan 27 2014 Randy Barlow <rbarlow@redhat.com> 1.3.3-1
- new package built with tito

* Fri Nov 15 2013 Eric Harney <eharney@redhat.com> - 1.3.3-1
- Update to 1.3.3

* Fri Oct 25 2013 Eric Harney <eharney@redhat.com> - 1.3.1-1
- Update to 1.3.1

* Tue Oct 08 2013 Eric Harney <eharney@redhat.com> - 1.3.0-1
- Update to 1.3.0

* Fri Sep 20 2013 Eric Harney <eharney@redhat.com> - 1.2.1-1
- Update to 1.2.1

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.11-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Fri Jun 21 2013 Eric Harney <eharney@redhat.com> - 1.0.11-1
- Initial package
