%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

Name:           python-ssl
Version:        1.15
Release:        4%{?dist}
Summary:        SSL wrapper for socket objects (2.3, 2.4, 2.5 compatible)

Group:          Development/Libraries
License:        Python
URL:            http://pypi.python.org/pypi/ssl
Source0:        http://pypi.python.org/packages/source/s/ssl/ssl-%{version}.tar.gz
Source1:        README.ssl
Patch0:         %{name}-64bit.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

# This package is never needed for python 2.6 since
# ssl module is already present.
Requires: python < 2.6
BuildRequires:  python-devel < 2.6
BuildRequires:  python-setuptools
BuildRequires:  openssl-devel

%description
SSL wrapper for socket objects (2.3, 2.4, 2.5 compatible)

The old socket.ssl() support for TLS over sockets is being superseded in 
Python 2.6 by a new 'ssl' module.  This package brings that module to older 
Python releases.

%prep
%setup -q -n ssl-%{version}
%patch0 -p1
cp -p %{SOURCE1} README


%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} -c 'import setuptools; execfile("setup.py")' build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --root $RPM_BUILD_ROOT
chmod 0755 $RPM_BUILD_ROOT%{python_sitearch}/ssl/_ssl2.so
rm -rf $RPM_BUILD_ROOT%{python_sitearch}/../test
 
%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc README
%{python_sitearch}/*

%changelog
* Thu May 27 2010 Jason L Connor <jconnor@redhat.com> 1.5-4
- added setuptools to build
* Thu Oct 15 2009 Steve Traylen <steve.traylen@cern.ch> 1.15-3
- Release bump due to my error.
* Tue Oct 13 2009 Steve Traylen <steve.traylen@cern.ch> 1.15-2
- Add -p to cp to preserve timestamps.
* Fri Oct 2 2009 Steve Traylen <steve.traylen@cern.ch> 1.15-1
- First Build


