# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           python-greenlet
Version:        0.3.1
Release:        2%{?dist}
Summary:        Lightweight in-process concurrent programming
Group:          Development/Libraries
License:        MIT
URL:            http://pypi.python.org/pypi/greenlet
Source0:        http://pypi.python.org/packages/source/g/greenlet/greenlet-%{version}.tar.gz
#Source0:        greenlet-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  python-devel
BuildRequires:  python-setuptools

%description
The greenlet package is a spin-off of Stackless, a version of CPython
that supports micro-threads called "tasklets". Tasklets run
pseudo-concurrently (typically in a single or a few OS-level threads)
and are synchronized with data exchanges on "channels".

%package devel
Summary:        C development headers for python-greenlet
Group:          Development/Libraries
Requires:       %{name} = %{version}-%{release}

%description devel
This package contains header files required for C modules development.

%prep
%setup -q -n greenlet-%{version}

%build
#CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build
#%{__python} setup.py build
chmod 644 benchmarks/*.py

%install
rm -rf %{buildroot}
#%{__python} setup.py install -O1 --skip-build --root %{buildroot}
%{__python} setup.py install -O1 --root %{buildroot}
 
%clean
#rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc doc/greenlet.txt README benchmarks AUTHORS NEWS
%{python_sitearch}/greenlet.so
%{python_sitearch}/greenlet*.egg-info

%files devel
%defattr(-,root,root,-)
%{_includedir}/python*/greenlet

%changelog
* Wed Apr 14 2010 Lev Shamardin <shamardin@gmail.com> - 0.3.1-2
- Splitted headers into a -devel package.

* Fri Apr 09 2010 Lev Shamardin <shamardin@gmail.com> - 0.3.1-1
- Initial package version.
