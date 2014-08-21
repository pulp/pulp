%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from %distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-nectar
Version:        1.3.1
Release:        1%{?dist}
Summary:        A download library that separates workflow from implementation details

Group:          Development/Tools
License:        GPLv2
URL:            https://github.com/pulp/nectar
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch

BuildRequires:  python-setuptools

Requires:       python-isodate >= 0.4.9
Requires:       python-requests >= 2.2.1

%description
Nectar is a download library that abstracts the workflow of making and tracking
download requests away from the mechanics of how those requests are carried
out. It allows multiple downloaders to exist with different implementations,
such as the default "threaded" downloader, which uses the "requests" library
with multiple threads. Other experimental downloaders have used tools like
pycurl and eventlets.

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
%doc COPYRIGHT LICENSE.txt README.rst

%changelog
* Thu Aug 21 2014 Barnaby Court <bcourt@redhat.com> 1.3.1-1
- 1127298 - Canceling a download causes hang in ThreadedDownloader (bcourt@redhat.com)

* Thu Aug 07 2014 Jeff Ortel <jortel@redhat.com> 1.3.0-1
- Updated API to support synchronous downloading of a single file.

* Thu Aug 07 2014 Jeff Ortel <jortel@redhat.com> 1.2.2-1
- 1126083 - no longer logging a failed download at ERROR level
  (mhrivnak@redhat.com)
* Fri Mar 28 2014 Jeff Ortel <jortel@redhat.com> 1.2.1-1
- 1078945 - Canceling a repo sync task does not seem to halt the
  rpm sync (bcourt@redhat.com)
- 965764 - DownloaderConfig is explicit. (rbarlow@redhat.com)
- 1078945 - Avoid use of thread join and Event.wait() so that we don't end up
  in C code that will block python signal handlers. (bcourt@redhat.com)

* Fri Mar 21 2014 Michael Hrivnak <mhrivnak@redhat.com> 1.2.0-1
- custom headers can now be specified on sessions and requests
  (mhrivnak@redhat.com)
- correcting typo in the python-requests version dep (skarmark@redhat.com)
- updating python-requests depedency version to 2.1.1 (skarmark@redhat.com)
- removing downloaders that we aren't using or supporting. Both are also known
  to have serious bugs. (mhrivnak@redhat.com)

* Mon Oct 28 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.6-1
- Merge pull request #13 from pulp/skarmark-1021662 (skarmark@redhat.com)
- 1021662 - adding proxy auth to proxy urls along with the headers
  (skarmark@redhat.com)

* Wed Oct 23 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.5-1
- minor update to the unit test (skarmark@redhat.com)
- adding a unit test to verify request headers when using
  HTTPBasicWithProxyAuth (skarmark@redhat.com)
- Moving HTTPBasicWithProxyAuth class to nectar.config and adding doc blocks
  (skarmark@redhat.com)
- 1021662 - adding a class which inherits requests.auth.AuthBase and sets up
  proxy and user basic authentication headers correctly instead of overwriting
  each other (skarmark@redhat.com)
- 1021662 - using HTTPProxyAuth when using proxy with authentication to
  populate correct field in the header (skarmark@redhat.com)

* Wed Oct 09 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.4-1
- adding dependency to python-requests >= 2.0.0 to support proxy with https
  (skarmark@redhat.com)

* Wed Oct 09 2013 Sayli Karmarkar <skarmark@redhat.com> 1.1.3-1
- updating revent downloader with the latest change in threaded downloader
  since it is generally maintained in lock-step with the threaded downloader
  (skarmark@redhat.com)
- we need to set both the 'http' and 'https' protocols to '://'.join((protocol,
  url)) (skarmark@redhat.com)
- removed workaround for no https proxy support, since we now carry python-
  requests-2.0.0 which includes updated urlllib3 and provides the https proxy
  support (skarmark@redhat.com)
- bumped docs version to match latest tag (jason.connor@gmail.com)

* Thu Sep 26 2013 Jason L Connor <jason.connor@gmail.com> 1.1.2-1
- added warnings about incomplete proxy support for the revent and threaded
  downloader (jason.connor@gmail.com)
- 1009078 - correctly set the proxies to supported protocols
  (jason.connor@gmail.com)
- always use http:// for proxy url (lars.sjostrom@svenskaspel.se)

* Tue Sep 03 2013 Jason L Connor <jason.connor@gmail.com> 1.1.1-1
- removed progress reporter thread due to race condition in the .join() with this queue and substituted it with thread-safe event firing and join()s on the worker threads (jason.connor@gmail.com)
- removed race condition between feeder thread and worker threads daemonized all spawned threads (jason.connor@gmail.com)

* Fri Aug 23 2013 Jason L Connor <jason.connor@gmail.com> 1.1.0-1
- new threaded downloader and unit tests (jason.connor@gmail.com)
- bumped nectar version to 1.1 (jason.connor@gmail.com)

* Wed Jul 31 2013 Jeff Ortel <jortel@redhat.com> 1.0.0-1
- got rid of fancy eventlet concurrency, regular os operations are faster;
  fixed bug where the report state was never started (jason.connor@gmail.com)
- fixed bug that sets mex_concurrent to None when max_concurrent is not
  provided (jason.connor@gmail.com)
- initial attempt at implementing an eventlet-based local file downloader
  (jason.connor@gmail.com)
* Wed Jul 03 2013 Jeff Ortel <jortel@redhat.com> 0.99-2
- 979582 - nectar now compensates for servers that send an incorrect content-
  encoding header for files that are gzipped. (mhrivnak@redhat.com)

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

