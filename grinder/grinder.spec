%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name: grinder
Version: 0.0.44
Release: 1%{?dist}
Summary: A tool synching content

Group: Development/Tools
License: GPLv2
URL: http://github.com/mccun934/grinder
Source0: http://mmccune.fedorapeople.org/grinder/grinder-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch: noarch
BuildRequires: python-setuptools
Requires:      createrepo, python >= 2.4
Requires:      PyYAML
Requires:      python-pycurl
Requires:      python-hashlib
%description
A tool for synching content from the Red Hat Network.

%prep
%setup -q -n grinder-%{version}


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
rm -f $RPM_BUILD_ROOT%{python_sitelib}/*egg-info/requires.txt

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc README COPYING
%{_bindir}/grinder
%dir %{python_sitelib}/grinder
%{python_sitelib}/grinder/*
%{python_sitelib}/grinder-*.egg-info
%config(noreplace) %{_sysconfdir}/grinder/grinder.yml


%changelog
* Tue May 18 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.44-1
- 593304 - Minor issue, visible python errors at the end of a kickstart sync
  (jwmatthews@gmail.com)
- adding a prefix of "grinder." to our logger instances (jwmatthews@gmail.com)
- 593074 - set the relative path based on primary xml (pkilambi@redhat.com)

* Mon May 17 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.43-1
- 

* Fri May 14 2010 John Matthews <jwmatthews@gmail.com> 0.0.42-1
- Updates for Package/Kickstart fetch to work with changes in BaseFetch Note:
  RHN comm to https is currently broken, http is working (jwmatthews@gmail.com)
- Refactor BaseFtech to use pycurl so RHN and yum fetch use the same logic to
  fetch and validate downloads (pkilambi@redhat.com)
- refactor, remove rhncomm from BaseFetch (jwmatthews@gmail.com)
- Fix for kickstarts, need to keep filename same as what RHN uses (don't use
  epoch in filename) (jwmatthews@gmail.com)

* Thu May 13 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.40-1
- Adding python-hashlib dependency to grinder (pkilambi@redhat.com)
- Adding validation for drpms fetch

* Wed May 12 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.38-1
- log tracebacks for debug purposes (pkilambi@redhat.com)
- RepoFecth now validates existing packages and only fetches new ones. Added a
  new utils module for common calls (pkilambi@redhat.com)
- fix typo for 'packages' instead of 'kickstarts' (jwmatthews@gmail.com)
- bz591120 - running grinder with -k and -K results in error
  (jwmatthews@gmail.com)
- move 'removeold' functionality to BaseSync, add in CLI option for 'removeold'
  (jwmatthews@gmail.com)

* Mon May 10 2010 John Matthews <jwmatthews@gmail.com> 0.0.37-1
- fix for basePath being used when set in config file and cleanup of unused
  "main" method (jwmatthews@gmail.com)

* Thu May 06 2010 John Matthews <jwmatthews@gmail.com> 0.0.36-1
- add createRepo/updateRepo calls to syncPackages() (jwmatthews@gmail.com)

* Thu May 06 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.35-1
- Adding support to fetch content by passing in ssl ca and content certs via
  yum for metadata and pycurl to fetch the bits (pkilambi@redhat.com)

* Wed May 05 2010 Mike McCune <mmccune@redhat.com> 0.0.33-1
- copy repomd.xml to the repodata directory (pkilambi@redhat.com)
- update for kickstart syncs (jwmatthews@gmail.com)
- add check for systemid and ensure we cleanup test cert/systemid
  (jwmatthews@gmail.com)
- adding unittests for RHNSync parsing configfile and reading options from
  command line (jwmatthews@gmail.com)
- rename RHNContent to RHNFetch (jwmatthews@gmail.com)
- adding 'rhn' operation to GrinderCLI  - options are initialized in order of
  Defaults, Config File, CLI  - basic package syncing has been tested  - needs
  exhaustive testing with different option combinations (jwmatthews@gmail.com)
- minor fixes after testing presto stuff (pkilambi@redhat.com)
- Support to sync down delta rpms metadata and corresponding binaries for a
  given repo if available. (pkilambi@redhat.com)
- Fetch the repodata generically so we can support presto metadata if available
  (pkilambi@redhat.com)
- some useful logging info on fetch (pkilambi@redhat.com)
- including logrotate in logger class (pkilambi@redhat.com)
- new Grinder CLI architecture with yum repo sync cli integrated and functional
  (pkilambi@redhat.com)
- clean up (pkilambi@redhat.com)
- Adding a module to support content fetch from a yum repo url. CLI integration
  follows (pkilambi@redhat.com)

* Thu Apr 08 2010 John Matthews <jwmatthews@gmail.com> 0.0.32-1
- fixing typeError in log statement cauusing createrepo to fail
  (pkilambi@redhat.com)

* Wed Apr 07 2010 John Matthews <jwmatthews@gmail.com> 0.0.31-1
- 580082 - grinder -b /tmp/syncdir is not syncing channel to specified
  basepath. (jwmatthews@gmail.com)

* Tue Apr 06 2010 John Matthews <jwmatthews@gmail.com> 0.0.29-1
- wip for kickstart fetching (jwmatthews@gmail.com)
- Refactor ParallelFetch/PackageFetch code to get ready for Kickstart fetching
  (jwmatthews@gmail.com)
- add fetch of metadata for kickstarts (jwmatthews@gmail.com)
- add method for returning filtered channel labels (jwmatthews@gmail.com)
- bz572639 - add debug output for removeold and numOldPkgsKeep
  (jwmatthews@gmail.com)
- corrected typo (jconnor@satellite.localdomain)

* Mon Mar 29 2010 John Matthews <jwmatthews@gmail.com> 0.0.28-1
- small typo change (jwmatthews@gmail.com)

* Fri Mar 26 2010 Mike McCune <mmccune@redhat.com> 0.0.27-1
- fixing condition when channel has no comps or update data
  (mmccune@redhat.com)
- Support for updateinfo.xml fetch and munge with existing createrepo data.
  This is to make the errata data work in conjunction with yum security plugin
  (pkilambi@redhat.com)

* Tue Mar 23 2010 Mike McCune <mmccune@redhat.com> 0.0.25-1
- adding SyncReport to show # downloads, errors, etc.. (mmccune@redhat.com)
- add fetching of comps.xml to support yum "group" operations
  (jwmatthews@gmail.com)

* Mon Mar 22 2010 Mike McCune <mmccune@redhat.com> 0.0.21-1
- 572663 - grinder command line arg "-P one" should throw non int exception for
  parallel (jwmatthews@gmail.com)
- 572657 - please remove username password from grinder config
  (jwmatthews@gmail.com)

* Thu Mar 11 2010 Mike McCune <mmccune@redhat.com> 0.0.20-1
- 572565 - Running grinder gives a Unable to parse config file message
  (jwmatthews@gmail.com)
- updating comment in config for how many previous packages to store
  (jwmatthews@gmail.com)
- typo fix (jwmatthews@gmail.com)
- Keep a configurable number of old packages & bz572327 fix bz572327 Running
  grinder for a specific channel syncs that channel and the channels specified
  in the config (jwmatthews@gmail.com)

* Wed Mar 10 2010 Mike McCune <mmccune@redhat.com> 0.0.18-1
- fixing spacing (mmccune@redhat.com)
- 571452 - ParallelFetch create channel directory should be silent if the
  directory already exists (jwmatthews@gmail.com)

* Thu Mar 04 2010 Mike McCune <mmccune@redhat.com> 0.0.17-1
- add log statement to show if/where removeold package is working from
  (jmatthews@virtguest-rhq-server.localdomain)
- add option to remove old RPMs from disk (jmatthews@virtguest-rhq-
  server.localdomain)

* Wed Mar 03 2010 Mike McCune <mmccune@redhat.com> 0.0.16-1
- update dir name for /etc/grinder (jmatthews@virtguest-rhq-server.localdomain)
- add PyYAML to grinder.spec (jmatthews@virtguest-rhq-server.localdomain)
- add yaml configuration file to setuptools (jmatthews@virtguest-rhq-
  server.localdomain)
- adding yaml configuration file/parsing to grinder (jmatthews@virtguest-rhq-
  server.localdomain)
- fixing paths and moving a bit forward (mmccune@redhat.com)

* Tue Mar 02 2010 Mike McCune <mmccune@redhat.com> 0.0.14-1
- 569963 - Adding dependency on createrepo (skarmark@redhat.com)
- adding test hook (mmccune)
- Adding error handling for a system trying to run grinder without activating
  (skarmark@redhat.com)

* Fri Feb 26 2010 Mike McCune <mmccune@redhat.com> 0.0.11-1
- Initial creation of RPM/specfile 

