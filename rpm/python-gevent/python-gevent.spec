%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif


Name:           python-gevent
Version:        0.12.2
Release:        3%{?dist}
Summary:        Python network library that uses greenlet and libevent for easy and scalable concurrency
Group:          Development/Libraries
License:        MIT
URL:            http://www.gevent.org/
Source0:        gevent-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  python-devel
BuildRequires:  python-setuptools
BuildRequires:  libevent-devel

Requires:       libevent
Requires:       python-greenlet

%description
gevent is a coroutine_-based Python_ networking library that uses greenlet_ to 
provide
a high-level synchronous API on top of libevent_ event loop.

Features include:

* convenient API around greenlets (gevent.Greenlet)
* familiar synchronization primitives (gevent.event, gevent.queue)
* socket module that cooperates (gevent.socket)
* WSGI server on top of libevent-http (gevent.wsgi)
* DNS requests done through libevent-dns
* monkey patching utility to get pure Python modules to cooperate 
* (gevent.monkey)


%prep
%setup -q -n gevent-%{version}


%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build


%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
 
%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc doc examples LICENSE* README.rst TODO
%{python_sitearch}/gevent*


%changelog
* Thu May 20 2010 Adam Young  <ayoung@redhat.com> - 0.12.2-3
- Fixed files line that was breaking in EPEL build


* Fri Apr 30 2010 Jason L Connor <jconnor@redhat.com> - 0.12.2
- Added python-greenlet dependency

* Fri Apr 30 2010 Jason L Connor <jconnor@redhat.com> - 0.12.2
- Initial package version.
