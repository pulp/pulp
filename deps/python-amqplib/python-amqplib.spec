%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print (get_python_lib())")}

%global srcname amqplib

Name:           python-%{srcname}
Version:        1.0.2
Release:        7%{?dist}
Summary:        Client library for AMQP

Group:          Development/Languages
License:        LGPLv2+
URL:            http://pypi.python.org/pypi/amqplib
Source0:        http://pypi.python.org/packages/source/a/%{srcname}/%{srcname}-%{version}.tgz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose
Requires:       python-ssl

%description
Client library for AMQP (Advanced Message Queuing Protocol)

Supports the 0-8 AMQP spec, and has been tested with RabbitMQ
and Python's 2.4, 2.5, and 2.6.

%prep
%setup -q -n %{srcname}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root %{buildroot}
 
%clean
rm -rf %{buildroot}

%check
cd tests/client_0_8
nosetests run_all.py

%files
%defattr(-,root,root,-)
%doc CHANGES INSTALL LICENSE README TODO docs/ 
%{python_sitelib}/%{srcname}/
%{python_sitelib}/%{srcname}*.egg-info

%changelog
* Sat Aug 04 2012 David Malcolm <dmalcolm@redhat.com> - 1.0.2-6
- rebuild for https://fedoraproject.org/wiki/Features/Python_3.3

* Thu Aug  2 2012 David Malcolm <dmalcolm@redhat.com> - 1.0.2-5
- generalize nosetests reference to work with Python 3.*
- remove rhel logic from with_python3 conditional

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jan 31 2012 Fabian Affolter <mail@fabian-affolter.ch> - 1.0.2-3
- Added support for Python 3

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Sat Nov 26 2011 Fabian Affolter <mail@fabian-affolter.ch> - 1.0.2-1
- Updated to new upstream version 1.0.2

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Mon Nov 01 2010 Fabian Affolter <mail@fabian-affolter.ch> - 0.6.1-2
- Added python-nose as BR
- Remove old python stuff for Fedora 12

* Sat Jul 03 2010 Fabian Affolter <mail@fabian-affolter.ch> - 0.6.1-1
- Initial package
