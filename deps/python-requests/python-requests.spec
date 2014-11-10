%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-requests
Version:        2.4.3
Release:        1%{?dist}
Summary:        HTTP library, written in Python, for human beings

Group:          Development/Tools
License:        ASL 2.0
URL:            http://pypi.python.org/pypi/requests
Source0:        http://pypi.python.org/packages/source/r/requests/requests-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch

BuildRequires:  python-setuptools

%description
Most existing Python modules for sending HTTP requests are extremely verbose and 
cumbersome. Python’s built-in urllib2 module provides most of the HTTP 
capabilities you should need, but the API is thoroughly broken. This library is 
designed to make HTTP requests easy for developers.

%prep
%setup -q -n requests-%{version}

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc NOTICE LICENSE README.rst HISTORY.rst
%{python_sitelib}/*.egg-info
%dir %{python_sitelib}/requests
%{python_sitelib}/requests/*

%changelog
* Mon Nov 10 2014 Chris Duryee <cduryee@redhat.com> 2.4.3-1
- 1160794 - update python-requests to 2.4.3 (cduryee@redhat.com)
- Build for EL 7. (rbarlow@redhat.com)

* Wed Apr 02 2014 Sayli Karmarkar <skarmark@redhat.com> 2.2.1-1
- correcting a couple of typos in the python-requests version
  (skarmark@redhat.com)
- updating nectar dependency on python-requests to version 2.1.1
  (skarmark@redhat.com)
- Automatic commit of package [python-requests] minor release [2.2.1-1].
  (skarmark@redhat.com)

* Fri Mar 14 2014 Sayli Karmarkar <skarmark@redhat.com> 2.2.1-1
- updating to the latest version 2.2.1 of python-requests dependency
* Fri Oct 04 2013 Sayli Karmarkar <skarmark@redhat.com> 2.0.0-1
- New package built with tito. This version vastly improves proxy support, 
including the CONNECT verb. This fixes https://bugzilla.redhat.com/show_bug.cgi?id=1014368.


