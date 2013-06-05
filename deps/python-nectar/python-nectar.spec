%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from %distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-nectar
Version:        0.99
Release:        1%{?dist}
Summary:        Performance tuned network download client library

Group:          Development/Tools
License:        GPLv2
URL:            https://github.com/pulp/nectar
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch

BuildRequires:  python-setuptools

Requires:       python-eventlet >= 0.9.17
Requires:       python-isodate >= 0.4.9
Requires:       python-pycurl >= 7.19.0
Requires:       python-requests >= 1.1.0
# RHEL6 ONLY
%if 0%{?rhel} == 6
Requires:       curl >= 7.19.0
%endif

%description
%{summary}

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%{python_sitelib}/nectar/
%{python_sitelib}/nectar*.egg-info
%doc LICENSE.txt

%changelog
* Wed Jun 05 2013 Jay Dobies <jason.dobies@redhat.com> 0.99-1
- 970741 - Upgraded nectar for error_msg support (jason.dobies@redhat.com)

* Wed Jun 05 2013 Jay Dobies <jason.dobies@redhat.com> 0.99-1
- Tweaking the version numbering until we come out with 1.0 to make it play
  nicer with tito (jason.dobies@redhat.com)

* Wed Jun 05 2013 Jay Dobies <jason.dobies@redhat.com> 0.97.1-1
- 970741 - Added error_msg field to the download report
  (jason.dobies@redhat.com)

* Mon Jun 03 2013 Jason L Connor <jason.connor@gmail.com> 0.97.0-1
- initial pass at leaky bucket throttling algorithm (jason.connor@gmail.com)

* Thu May 30 2013 Jason L Connor <jason.connor@gmail.com> 0.95.0-1
- 967939 - added kwarg processing for ssl file and data configuration options
  that make both available via the configuration instance
  (jason.connor@gmail.com)
* Mon May 20 2013 Jason L Connor <jason.connor@gmail.com> 0.90.3-2
- changed requires so for epel and fedora; commented out (for now) %%check
  (jason.connor@gmail.com)
- revent test script (jason.connor@gmail.com)
- no longer patching the thread module as it causes problems with threaded
  programs (jason.connor@gmail.com)
* Tue May 14 2013 Jason L Connor <jason.connor@gmail.com>
- new package built with tito

* Mon May 13 2013 Jason L Connor (jconnor@redhat.com) 0.90.0-1
- brought in new revent downloader to replace old eventlet downloader
- bumped version in preparation of 1.0.0 release

* Wed May 08 2013 Jason L Connor (jconnor@redhat.com) 0.0.90-1
- cut project from pulp
- initial spec file and setup.py

