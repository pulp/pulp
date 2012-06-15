%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%define pkgname isodate

Name:           python-isodate
Version:        0.4.4
Release:        5.pulp%{?dist}
Summary:        An ISO 8601 date/time/duration parser and formater
Group:          Development/Libraries

License:        BSD

URL:            http://cheeseshop.python.org/pypi/isodate
Source0:        isodate-%{version}.tar.gz
Patch0:         isodate-tzinfo.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:  python-setuptools
BuildArch:      noarch

%description
This module implements ISO 8601 date, time and duration parsing.
The implementation follows ISO8601:2004 standard, and implements only
date/time representations mentioned in the standard. If something is not
mentioned there, then it is treated as non existent, and not as an allowed
option.

For instance, ISO8601:2004 never mentions 2 digit years. So, it is not
intended by this module to support 2 digit years. (while it may still
be valid as ISO date, because it is not explicitly forbidden.)
Another example is, when no time zone information is given for a time,
then it should be interpreted as local time, and not UTC.

As this module maps ISO 8601 dates/times to standard Python data types, like
*date*, *time*, *datetime* and *timedelta*, it is not possible to convert
all possible ISO 8601 dates/times. For instance, dates before 0001-01-01 are
not allowed by the Python *date* and *datetime* classes. Additionally
fractional seconds are limited to microseconds. That means if the parser finds
for instance nanoseconds it will round it to microseconds.

%prep
%setup -q -n %{pkgname}-%{version}
%patch0 -p1

%build
%{__python} setup.py build

%check

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc CHANGES.txt README.txt TODO.txt
%{python_sitelib}/*

%changelog
* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.4.4-5.pulp
- Renamed dependency RPMs (jason.dobies@redhat.com)

* Fri Dec 09 2011 James Slagle <jslagle@redhat.com> 0.4.4-4.pulp
- Bump so we can rebuild in brew.

* Mon Nov 28 2011 John Matthews <jmatthews@redhat.com> 0.4.4-3.pulp
- incremented build and added pulp (jconnor@redhat.com)

* Fri Jun 03 2011 John Matthews <jmatthew@redhat.com> 0.4.4-2
- Getting python-isodate built in brew (jmatthew@redhat.com)

* Tue May 10 2011 Jay Dobies <jason.dobies@redhat.com> 0.4.4-1
- Messed up the version number (jason.dobies@redhat.com)

* Tue May 10 2011 Jay Dobies <jason.dobies@redhat.com> 0.4.6-1
- Fixed source entry for tito compatibility (jason.dobies@redhat.com)

* Tue May 10 2011 Jay Dobies <jason.dobies@redhat.com> 0.4.5-1
- new package built with tito

* Tue Apr 26 2011 Jason L Connor <jconnor@redhat.com> 0.4.4-1
- Initial rpm spin
