%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name: grinder
Version: 0.1.5
Release: 1%{?dist}
Summary: A tool for synchronizing content from yum repositories

Group: Development/Tools
License: GPLv2
URL: http://git.fedorahosted.org/git/?p=grinder.git
Source0: https://fedorahosted.org/releases/g/r/%{name}/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch: noarch
BuildRequires:  python-setuptools
Requires:       createrepo, python >= 2.4
Requires:       PyYAML
Requires:       python-pycurl
%if 0%{?rhel} == 6
# RHEL-6, 
# Require updated nss/curl for BZ: https://bugzilla.redhat.com/show_bug.cgi?id=710455
Requires:       nss >= 3.12.9
Requires:       curl => 7.19.7
Requires:       python-hashlib
%endif


%description
A tool for synchronizing content such as packages, distributions, and 
errata from yum repositories.

%prep
%setup -q 


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
rm -f $RPM_BUILD_ROOT%{python_sitelib}/*egg-info/requires.txt
mkdir -p $RPM_BUILD_ROOT%{_mandir}/man8/
cp man/grinder.8 $RPM_BUILD_ROOT%{_mandir}/man8/grinder.8

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc README COPYING LICENSE
%{_bindir}/grinder
%dir %{python_sitelib}/grinder
%{python_sitelib}/grinder/*
%{python_sitelib}/grinder-*.egg-info
%config(noreplace) %{_sysconfdir}/grinder/grinder.yml
%{_mandir}/man8/grinder.8.gz


%changelog
* Thu Jul 05 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.1.5-1
- updating grinder to include fix for #828447 (pkilambi@redhat.com)

* Thu Jul 05 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.1.5-1
- 828447 - fix permissions on grinder tmpdir (pkilambi@redhat.com)

* Thu Jun 14 2012 John Matthews <jmatthews@redhat.com> 0.1.4-1
- Clean up temp dirs and Allow Retry attempts to be configurable
  (jmatthews@redhat.com)
- Adding retry attempts to fetching of Yum repodata (jmatthews@redhat.com)

* Thu Apr 26 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.1.3-1
- fixing unit tests (pkilambi@redhat.com)
- changing the skip from dict to a list and using new skip types
  (pkilambi@redhat.com)

* Tue Apr 24 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.1.2-1
- fix the filename in ksfiles to  include relativepath (pkilambi@redhat.com)
- Adding more details to distro info post preparing trees (pkilambi@redhat.com)
- 797880 - 'NaN' token in JSON response (jmatthews@redhat.com)
- Bump version to avoid confusion with pulp_v1.1 branch (jmatthews@redhat.com)

* Tue Apr 10 2012 John Matthews <jmatthews@redhat.com> 0.0.146-1
- Update error report (jmatthews@redhat.com)

* Mon Apr 09 2012 John Matthews <jmatthews@redhat.com> 0.0.145-1
- Adding a low speed limit threshold to recognize a hung connection and abort
  (jmatthews@redhat.com)
- change the drpm info to return new package keys (pkilambi@redhat.com)
- adding extra info to delta rpm fetch (pkilambi@redhat.com)
- Adding Filter.py from John Morris's Filter patch (john@zultron.com)
- Added a unit test for Filters, removed some older tests
  (jmatthews@redhat.com)
- Allows package filtering on RPM downloads Community contribution received
  through pulp-list on: March 22, 2012 2:28 AM (john@zultron.com)

* Fri Mar 23 2012 John Matthews <jmatthews@redhat.com> 0.0.144-1
- Fix for cleanup of temp .part file when pycurl throws an exception  - Also
  fix md5/size mismatch to have same format of error info reported.
  (jmatthews@redhat.com)

* Fri Mar 23 2012 John Matthews <jmatthews@redhat.com> 0.0.143-1
- Updating activeobject to raise the original exception (jmatthews@redhat.com)
- Reduce the output when an error occurs with activeobject
  (jmatthews@redhat.com)

* Wed Mar 21 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.0.142-1
- 805543 - adding an optional arg to force fetch files; this is useful for
  files like treeinfo that dont have checksum/size info for validation
  (pkilambi@redhat.com)

* Mon Mar 19 2012 John Matthews <jmatthews@redhat.com> 0.0.141-1
- Fix unit tests to reflect full checksum being used (jmatthews@redhat.com)
- Unit tests for local sync (jmatthews@redhat.com)

* Mon Mar 19 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.0.140-1
- Include the full checksum when creating package paths (pkilambi@redhat.com)
- Added support for local syncs, URLs using file:///  - Refactored Distribution
  Sync to reduce error messages logged to console on routine operations
  (jmatthews@redhat.com)
- Add filename to rpm data structure for Pulp v2 work (jmatthews@redhat.com)
- Update progress to reflect when we begin downloading packages, need to re-
  examine remove_old logic (jmatthews@redhat.com)
- setup tito releasers. (jortel@redhat.com)

* Mon Feb 27 2012 John Matthews <jmatthews@redhat.com> 0.0.139-1
- 797195 - Syncing multiple repos concurrently could cause missing symlinks
  (jmatthews@redhat.com)

* Thu Feb 23 2012 John Matthews <jmatthews@redhat.com> 0.0.138-1
- 

* Thu Feb 23 2012 John Matthews <jmatthews@redhat.com> 0.0.137-1
- Refactor grinder to support integration with Pulp's generic content approach
  (jmatthews@redhat.com)

* Thu Dec 15 2011 John Matthews <jmatthews@redhat.com> 0.0.136-1
- rpmlint updates (jmatthews@redhat.com)

* Thu Dec 15 2011 John Matthews <jmatthews@redhat.com> 0.0.135-1
- Update for fedora review (jmatthews@redhat.com)

* Thu Dec 15 2011 John Matthews <jmatthews@redhat.com> 0.0.134-1
- 761173 - SELinux related: Move grinder usage of /tmp/grinder to
  /var/run/grinder (jmatthews@redhat.com)

* Thu Dec 15 2011 John Matthews <jmatthews@redhat.com> 0.0.133-1
- 754787 - Disruption in Internet Connectivity leave a large number of sleeping
  grinder processes (jmatthews@redhat.com)
- 765930 - ProgressTracker: Issue when re-downloading a failed file, "Error
  Negative delat_bytes" (jmatthews@redhat.com)
- Allow 206 as successful status, fix for resuming a partial download
  (jmatthews@redhat.com)
- 767261 - better handling of RMI killed/aborted. (jortel@redhat.com)
- 752288 - Progress Reporting jumps from 99% to 88% when syncing with
  distribution files present Moved distro items to front of queue so size
  adjustment happens early in the sync progress. (jmatthews@redhat.com)

* Mon Dec 12 2011 John Matthews <jmatthews@redhat.com> 0.0.132-1
- Update man page (jmatthews@redhat.com)
- Rpmlint error fix to move python-hashlib from general requires to only
  required in el6 (jmatthews@redhat.com)
- Adding a makefile to handle scp'ing src tarball and spec to fedorahosted for
  each build (jmatthews@redhat.com)
- Removing proxy_password from log output (jmatthews@redhat.com)
- rpmlint update and added more logging output (jmatthews@redhat.com)

* Wed Nov 30 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.131-1
- 753940 - fix purge orphaned logic to use the actual file name written on
  filesystem (pkilambi@redhat.com)

* Fri Nov 18 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.130-1
- fixing typo (pkilambi@redhat.com)

* Wed Nov 16 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.129-1
- changing repofile path link to use new method for symlinks
  (pkilambi@redhat.com)
- 753805 - handle symlink exists exception when multiple concurrent processes
  try to create same link (pkilambi@redhat.com)

* Thu Nov 10 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.128-1
- 752784 - check treeinfo ddata for empty strings along with config existance
  (pkilambi@redhat.com)

* Mon Nov 07 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.127-1
- 751860 - fix for grinder to account for excludes passed in from pulp to skip
  packages or distributions (pkilambi@redhat.com)

* Tue Nov 01 2011 John Matthews <jmatthews@redhat.com> 0.0.126-1
- Added error details for checksum & size mismatches (jmatthews@redhat.com)

* Tue Nov 01 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.125-1
- changing the parse metadata to be a plain list to support same checksum
  different filename scenario (pkilambi@redhat.com)

* Tue Nov 01 2011 John Matthews <jmatthews@redhat.com> 0.0.124-1
- Update progress tracking to account for when actual file size is different
  than expected (jmatthews@redhat.com)
- 749902 - fixing lock validity to check existing lock (pkilambi@redhat.com)

* Fri Oct 28 2011 John Matthews <jmatthews@redhat.com> 0.0.123-1
- Enabling download progress per item (jmatthews@redhat.com)
- purge ParentMethod from __getstate__() result as well. (jortel@redhat.com)
- fix for traceback caused due to incorrect downloadurl construct
  (pkilambi@redhat.com)
- Fixed issue with update_progress resetting remaining_bytes to 0 incorrectly
  and added tests for ProgressTracker (jmatthews@redhat.com)
- WorkInProgress, reworking Sync Progress so we can accept incremental updates
  as an item is downloading (jmatthews@redhat.com)
- activeobject: remove support for 'parent' decorator. (jortel@redhat.com)
- Add support of Objects not in default python path. (jortel@redhat.com)

* Mon Oct 24 2011 John Matthews <jmatthews@redhat.com> 0.0.122-1
- Remove debugging log statement (jmatthews@redhat.com)
- Update to handle an empty repo (jmatthews@redhat.com)
- Add unit test for removal of existing old packages (jmatthews@redhat.com)
- 737523 - Move yum logic to ActiveObject to hide memory leak
  (jmatthews@redhat.com)
- Fix TmpDir.clean() Operation not permitted. (jortel@redhat.com)
- Add self cleaning TmpDir and use instead of tempfile.mkdtemp().
  (jortel@redhat.com)

* Fri Oct 14 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.121-1
- Add options to pass in optional central distribution location to store
  distros in a separate area and symlink to repos directory. Also adding a
  distribution label as a combination string with params from treeinfo. Pulp
  will use this to store distributions centrally. (pkilambi@redhat.com)
- Partial change for cleaning up grinderlock file descriptors
  (jmatthews@redhat.com)
- 737614 - glibc backtrace during repo sync (jmatthews@redhat.com)

* Tue Oct 11 2011 James Slagle <jslagle@redhat.com> 0.0.120-1
- 742351 - always clean up the yum cache (tmp) directory. (jortel@redhat.com)

* Tue Oct 11 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.119-1
- fixing the manifest to match cdn (pkilambi@redhat.com)

* Thu Sep 22 2011 James Slagle <jslagle@redhat.com> 0.0.118-1
- grinder doesnt clean up before retrying a 404'ed request, this causes the
  files with unknown size to pass the verify test as we ned up validating just
  the path (pkilambi@redhat.com)

* Tue Sep 20 2011 James Slagle <jslagle@redhat.com> 0.0.117-1
- patch activeobject memory leaks. use Popen.wait() to prevent Popen object's
  from being added to subprocess._active. remove atexit usage.  Don't think it
  was doing anything except preventing the activeobject from being garbage
  collected. (jortel@redhat.com)

* Fri Sep 16 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.116-1
- Adding a write lock when base fetch tries to download and write bits to the
  same location on the filesystem. (pkilambi@redhat.com)

* Thu Sep 15 2011 John Matthews <jmatthews@redhat.com> 0.0.115-1
- Allow checksum and size check on existing files to be optional
  (jmatthews@redhat.com)

* Wed Sep 14 2011 James Slagle <jslagle@redhat.com> 0.0.114-1
-  738306 - part file should now only try to rename if file isnt already closed
  by other concurrent processes (pkilambi@redhat.com)

* Tue Sep 13 2011 Jeff Ortel <jortel@redhat.com>
- 737531 - Close YumRepository object when finished with it.
  (jortel@redhat.com)

* Tue Sep 06 2011 Jeff Ortel <jortel@redhat.com> 0.0.112-1
- Fix pipe leak in activeobject. The leak was introduced when activeobject
  changed to be python 2.4 compat by killing the child process manually instead
  of using Popen.kill().  This method probably closed pipes.  So, when we
  discontinued using it, we needed to manually close the stdin & stdout pipes.
  (jortel@redhat.com)

* Thu Sep 01 2011 John Matthews <jmatthews@redhat.com> 0.0.111-1
- Explicit stop of ParallelFetch if an exception happens fetchYumRepo
  (jmatthews@redhat.com)
- Add support for callbacks in ActiveObject. (jortel@redhat.com)

* Fri Aug 05 2011 John Matthews <jmatthews@redhat.com> 0.0.110-1
- renamed file manifest to match cdn (pkilambi@redhat.com)
- getRepoData now checks if stop has been called before fetching next metadata
  file (jmatthews@redhat.com)
- 695607 - Fix RHEL macro. (jortel@redhat.com)
- Added test for immediate stop of downloading (jmatthews@redhat.com)

* Tue Aug 02 2011 John Matthews <jmatthews@redhat.com> 0.0.109-1
- Stop will now abort an activeobject method invocation and child processes
  will be killed (jmatthews@redhat.com)
- Log exception if we can't parse .treeinfo (jmatthews@redhat.com)
- adding unit test to validate write function (pkilambi@redhat.com)
- adding copyright header (pkilambi@redhat.com)
- Support to store and resume downloads in grinder. New Callback write function
  to track offsets and write files (pkilambi@redhat.com)
- Fix docstring. (jortel@redhat.com)

* Tue Jul 19 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.108-1
- fix metadata path (pkilambi@redhat.com)
- moving the parse metadata call to utils so pulp can reuse it
  (pkilambi@redhat.com)
- fixing central location file path (pkilambi@redhat.com)

* Thu Jul 14 2011 Jeff Ortel <jortel@redhat.com> 0.0.107-1
- Fix GrinderUtils import. (jortel@redhat.com)

* Thu Jul 14 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.106-1
- python 2.4 compat: Package qualify imports; Launch activeobject child using
  __file__. (jortel@redhat.com)
- python 2.4 compat; better abort support. (jortel@redhat.com)
- typo in comment (jmatthews@redhat.com)

* Wed Jul 06 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.105-1
- 712521 - If remoteurl is set as part of package object in primary use that
  for download else use relativepath with feed (pkilambi@redhat.com)

* Thu Jun 30 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.104-1
- Tunnel logging in child back to parent in activeobject. (jortel@redhat.com)
- Add state back-synchronization in ActiveObject. (jortel@redhat.com)
- Wrap parallel fetch in ActiveObject. (jortel@redhat.com)
- Disable 'split of PEM' certs, issue is a multithreading bug with NSS, split
  of cert doesn't impact it (jmatthews@redhat.com)
- 711329 - frequent crash syncing protected repos, added split of PEM to
  separate certs (jmatthews@redhat.com)

* Tue Jun 07 2011 John Matthews <jmatthew@redhat.com> 0.0.103-1
- 

* Tue Jun 07 2011 John Matthews <jmatthews@redhat.com> 0.0.102-1
- 710455 - Grinder cannot sync a Pulp protected repo (jmatthews@redhat.com)

* Mon Jun 06 2011 John Matthews <jmatthew@redhat.com> 0.0.101-1
- Remove requirement that all 3, cacert, cert, key must be specified at same
  time. (jmatthew@redhat.com)

* Tue May 31 2011 John Matthews <jmatthews@redhat.com> 0.0.100-1
- Added info about item type/name to progress callback details
  (jmatthews@redhat.com)
- re-license with more appropriate GPLv2 or later text (mmccune@redhat.com)

* Mon May 23 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.99-1
- Adding file sync to grinder CLI (pkilambi@redhat.com)
- File Sync support: * File based sync driver which parses the MANIFEST and
  fetches urls * unit tests (pkilambi@redhat.com)

* Tue May 17 2011 John Matthews <jmatthew@redhat.com> 0.0.98-1
- Adjust ssl cert usage so we can specify --cacert without a key/cert
  (jmatthews@redhat.com)

* Tue May 10 2011 John Matthews <jmatthews@redhat.com> 0.0.97-1
- Added log output to show total bytes transferred and time spent
  (jmatthews@redhat.com)

* Wed Apr 27 2011 John Matthews <jmatthews@redhat.com> 0.0.96-1
- 694578 - Grinder 'numOldPackages' should be improved to fetch less packages.
  (jmatthews@redhat.com)

* Tue Apr 26 2011 John Matthews <jmatthews@redhat.com> 0.0.95-1
- 698344 - sync status error details returns array of array of hashes
  (jmatthews@redhat.com)

* Wed Apr 13 2011 John Matthews <jmatthews@redhat.com> 0.0.94-1
- 695743 - Multiple concurrent calls to util.get_repo_packages() results in
  Segmentation fault (jmatthews@redhat.com)

* Mon Apr 11 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.93-1
- Adding ability to make purge orphaned packages optional. From pulp's
  standpoint, since we allow uploads to synced repos, it doesnt make sense to
  purge orphaned (pkilambi@redhat.com)

* Fri Apr 01 2011 John Matthews <jmatthews@redhat.com> 0.0.92-1
- Update ProgressReport to correctly state when Content Download is starting
  Prior to this change we marked the 'step' of downloading after the first
  package completed.  Now we mark it when the first package starts to download
  (jmatthews@redhat.com)
- Change to log type when a file can't be fetched - motivation was to quiet
  error statements when .treeinfo can't be found (jmatthews@redhat.com)

* Mon Mar 28 2011 John Matthews <jmatthew@redhat.com> 0.0.91-1
- Added ability to limit download bandwidth per thread (jmatthew@redhat.com)

* Fri Mar 25 2011 John Matthews <jmatthew@redhat.com> 0.0.90-1
- 

* Fri Mar 25 2011 John Matthews <jmatthews@redhat.com> 0.0.89-1
- 690157 - Sync'd Repository Structure does not match Feed Repo
  (jmatthews@redhat.com)

* Fri Mar 18 2011 John Matthews <jmatthew@redhat.com> 0.0.88-1
- 

* Fri Mar 18 2011 John Matthews <jmatthew@redhat.com> 0.0.87-1
- build in brew RHEL-6-CLOUDE (jmatthew@redhat.com)

* Wed Mar 09 2011 John Matthews <jmatthews@redhat.com> 0.0.86-1
- 680444 - exception during status api call (jmatthews@redhat.com)

* Tue Mar 08 2011 John Matthews <jmatthews@redhat.com> 0.0.85-1
- fix for getting relative path (jmatthews@redhat.com)

* Tue Mar 08 2011 John Matthews <jmatthews@redhat.com> 0.0.84-1
- 683011 - package symlinks in repos should be relative (jmatthews@redhat.com)

* Mon Mar 07 2011 John Matthews <jmatthews@redhat.com> 0.0.83-1
- 681304 - repo sync failing with Type error (jmatthews@redhat.com)

* Wed Mar 02 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.82-1
- moving the checksum as the last subdirectory to make package lookups easy
  (pkilambi@redhat.com)

* Thu Feb 24 2011 John Matthews <jmatthews@redhat.com> 0.0.81-1
- 678119 - Two fields from repo sync status are not being updated correctly
  (jmatthews@redhat.com)

* Thu Feb 17 2011 John Matthews <jmatthews@redhat.com> 0.0.80-1
- Fix for race condition with check dir then makedirs (jmatthew@redhat.com)
- update README to reflect we sync more than just packages now
  (jmatthews@redhat.com)

* Mon Feb 07 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.0.79-1
- Support for grinder to place the currently processing metadata in a temporary
  location until the sync completes and then move to final location. This
  should allow us to keep serving the existing content until the new metadata
  is ready to serve (pkilambi@redhat.com)
- 667753 - running repo sync with --no-packages option on a newly created repo
  fails (jmatthews@redhat.com)

* Fri Feb 04 2011 John Matthews <jmatthews@redhat.com> 0.0.78-1
- 670886 - repo sync error need to add more error information on a per "item"
  basis [yum sync changes] (jmatthews@redhat.com)

* Thu Jan 27 2011 John Matthews <jmatthews@redhat.com> 0.0.77-1
- Changed wording for download step (jmatthews@redhat.com)

* Thu Jan 27 2011 John Matthews <jmatthews@redhat.com> 0.0.76-1
- Change text for "Downloading Items" step to mention Verifying Existing items
  (jmatthews@redhat.com)

* Tue Jan 25 2011 John Matthews <jmatthews@redhat.com> 0.0.75-1
- fix for when no callback is passed into a sync (jmatthews@redhat.com)

* Mon Jan 24 2011 John Matthews <jmatthews@redhat.com> 0.0.74-1
- Adding per item type num_success/num_error (jmatthews@redhat.com)
- 670526 - Add more information to progress reporting (jmatthews@redhat.com)

* Thu Jan 20 2011 John Matthews <jmatthews@redhat.com> 0.0.73-1
- 

* Mon Jan 17 2011 John Matthews <jmatthew@redhat.com> 0.0.72-1
- 670283 - Yum Repo sync failing for fedora channels (jmatthew@redhat.com)

* Fri Jan 14 2011 John Matthews <jmatthews@redhat.com> 0.0.71-1
- 662744 - [RFE] Sync progress indicator need to show stats for all content
  types (pkgs, errata, files, distros, etc) (jmatthews@redhat.com)

* Fri Jan 07 2011 John Matthews <jmatthews@redhat.com> 0.0.70-1
- YumRepoFetch will block when stop() is called until all threads have
  finished. (jmatthews@redhat.com)

* Thu Jan 06 2011 John Matthews <jmatthew@redhat.com> 0.0.69-1
- 662760 - Failed repo sync still shows success (jmatthews@redhat.com)

* Wed Dec 22 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.68-1
- Fixed spec description (jason.dobies@redhat.com)

* Mon Dec 13 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.67-1
- makeing sslverify an option that can be passed to YumRepoGrinder api call as
  well as a cli option to pass in --nosslverify (pkilambi@redhat.com)
- fixing indentation (pkilambi@redhat.com)

* Thu Dec 02 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.66-1
- changing the skip check to use right value (pkilambi@redhat.com)
- Adding option to skip specific content types from syncs (pkilambi@redhat.com)

* Tue Nov 09 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.65-1
- Adding support for RepoFetch to pass in remove_old checks. CLean up print
  statements (pkilambi@redhat.com)

* Thu Oct 28 2010 John Matthews <jmatthew@redhat.com> 0.0.64-1
- 640448 - RHEL5 grinder build errors (jmatthew@redhat.com)
- set numOldPackage from param (pkilambi@redhat.com)
- Adding limit #.of old packages support for Grinder repo sync
  (pkilambi@redhat.com)

* Fri Sep 24 2010 John Matthews <jmatthew@redhat.com> 0.0.63-1
- 608672 - clearly state error when systemid/certifcate are unable to be read
  (jmatthew@redhat.com)

* Wed Sep 22 2010 John Matthews <jmatthew@redhat.com> 0.0.62-1
- fix for rhn sync (jmatthew@redhat.com)
- In certain case such as CDN, dotted files are not allowed. Try a treeinfo if
  .treeinfo fails before quitting (pkilambi@redhat.com)

* Fri Sep 17 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.61-1
- removes unused files key (pkilambi@redhat.com)
- Adding support to be able to sync down trees associated to the product repo
  (pkilambi@redhat.com)
- include checksum in package store path (pkilambi@redhat.com)

* Tue Sep 07 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.60-1
- Somtimes the package path could have directories, created the dirs before
  creating symlinks (pkilambi@redhat.com)

* Thu Sep 02 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.59-1
- Adding central package location support for grinder. Packages are synced to
  packages_location and symlined to repo directory. Default is repo directory
  unless packages_location is passed. DRPMS will be stored in individual repos
  as usual (pkilambi@redhat.com)
- purge orphaned packages that are not part of updated repodata
  (pkilambi@redhat.com)

* Tue Aug 24 2010 John Matthews <jmatthew@redhat.com> 0.0.58-1
- Adding a progress callback (jmatthew@redhat.com)
- RHN now expects the updateinfo fetch to use <checksum>-updateinfo.xml.gz as
  the request file, so we ask for repomd.xml, get the checksum for updateinfo
  and construct the request name to match RHN (pkilambi@redhat.com)

* Tue Aug 03 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.57-1
- 620791 - exclude epoch from the filename stored on disk (pkilambi@redhat.com)

* Mon Aug 02 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.56-1
- exposing the newest package download flag to YumRepoGrinder class
  (pkilambi@redhat.com)

* Mon Aug 02 2010 John Matthews <jmatthew@redhat.com> 0.0.55-1
- add proxy basic http user authentication to package fetch
  (jmatthew@redhat.com)

* Fri Jul 30 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.54-1
- 

* Fri Jul 30 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.53-1
- Adding http proxy support to grinder's yum repo fetches - user/password auth
  is not implemented for the pkg dowload yet (jmatthew@redhat.com)
- moving code authors to a separate AUTHORS file (pkilambi@redhat.com)
- 602243 - fixing the drpm path (pkilambi@redhat.com)
- 570887 - grinder, running grinder with -a option gives conflicting options
  specified error. If --all is specified on command line, disable removeold If
  --removeold is specified on command line, disable fetchall
  (jmatthew@redhat.com)
- 573138 - traceback when using a bad URL (jmatthew@redhat.com)
- adding a debug line to display what basepath is set to for yum fetches
  (jmatthew@redhat.com)

* Wed May 26 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.52-1
- copy repofiles to repodata dir instead of move so packagesack can use the
  primary (pkilambi@redhat.com)

* Wed May 26 2010 John Matthews <jmatthew@redhat.com> 0.0.51-1
- fix for activation, we dropped called to "activate" when porting to new CLI
  (jmatthew@redhat.com)

* Tue May 25 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.50-1
- set the primary_db to not retrieved so repo can refecth it for metadata dir
- 594496 - fix typos in help messages
- 572597 - updating grinder man page to include new options for yum
- 592316: making cli options for yuma nd rhn look close

* Fri May 21 2010 John Matthews <jmatthew@redhat.com> 0.0.49-1
- fix 'fetch' call to pass in hashType, this prob showed up during a long sync
  when auth data became stale we would refresh auth data, then re-call fetch.
  The call to fetch was missing hashType (jmatthew@redhat.com)
- Grinder: before fetching the repodata convert the url to ascii so urlgrabber
  doesnt freakout (pkilambi@redhat.com)
- logging info change, as per QE request (jmatthew@redhat.com)
- added web install requirement (jconnor@redhat.com)
- changed package_dir argument from 'grinder': 'src/grinder' to '': 'src' which
  tells disutils that the packages found by find_packages are under src/
  (jconnor@redhat.com)
- moving grinder tests from 'tests' to 'test', makes setup.py happy for develop
  install (jmatthew@redhat.com)
- Change --debug to be a True/False only, removed unused 'logging level'
  ability. (jmatthew@redhat.com)

* Wed May 19 2010 John Matthews <jmatthew@redhat.com> 0.0.48-1
- Adding extra log output to help QE in automation testing
  (jmatthew@redhat.com)

* Wed May 19 2010 Mike McCune <mmccune@redhat.com> 0.0.46-1
- import into pulp

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

