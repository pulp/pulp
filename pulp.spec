# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           pulp
Version:        0.0.6
Release:        1%{?dist}
Summary:        An application for managing software content

Group:          Development/Languages
License:        GPLv2
URL:            https://fedorahosted.org/pulp/
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose	
BuildRequires:  rpm-python

Requires: python-gevent
Requires: python-pymongo
Requires: python-setuptools
Requires: python-webpy
Requires: grinder
Requires: httpd

%if 0%{?rhel} > 5
Requires: python-hashlib
%endif


%description
Pulp provides replication, access, and accounting for software repositories.

%prep
%setup -q


%build
pushd src
%{__python} setup.py build
popd


%install
rm -rf %{buildroot}
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

cp -R test  %{buildroot}/%{python_sitelib}/%{name}
mkdir %{buildroot}/etc
cp -R etc/juicer.ini %{buildroot}/etc
cp -R etc/pulp.ini %{buildroot}/etc

find %{buildroot} -name \*.py | xargs sed -i -e '/^#!\/usr\/bin\/env python/d' -e '/^#!\/usr\/bin\/python/d' 

# RHEL 5 packages don't have egg-info files, so remove the requires.txt
# It isn't needed, because RPM will guarantee the dependency itself
%if 0%{?rhel} > 0
%if 0%{?rhel} <= 5
rm -f %{buildroot}/%{python_sitelib}/%{name}*.egg-info/requires.txt
%endif
%endif

%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/*
%{_bindir}/juicer
%config(noreplace) /etc/juicer.ini
%config(noreplace) /etc/pulp.ini

%changelog
* Wed Jun 02 2010 Adam Young <ayoung@redhat.com> 0.0.6-1
- no change (jconnor@redhat.com)
- adding wsgi script and apache config file for apache deployment
  (jconnor@redhat.com)
- added full range of client methods to test uri in juuicer
  (jconnor@redhat.com)
- pulpcli a.k.a corkscrew with support for repo create, list and sync
  (pkilambi@redhat.com)
- Refactored the synchronization logic out of the API.
  (jason.dobies@redhat.com)
- add python-hashlib dep to spec and checksum to pulp.utils
  (jmatthew@redhat.com)
- updating unit tests to get ready to test importing 2 packages same NEVRA,
  different checksum (jmatthew@redhat.com)
- Disabled config usage until juicer loads configuration files properly
  (jason.dobies@redhat.com)
- added egg-info to gitignore (jconnor@redhat.com)
- removed my own thread class and converted tasks to use "fire and forget"
  threads i.e. spawn a new thread each time it runs altered Task.wait to
  account for new semantics removed Task.exit (no longer necessary) modified
  test_tasks.py to take into account new semantics (jconnor@redhat.com)
- adding test packages/dir structure for unit tests of repo syncs Will be
  adding a test 2 repos same nevra, same checksum 2 repos same nevra, different
  checksum (jmatthew@redhat.com)
- add note about changes to Package we might want to consider
  (jmatthew@redhat.com)
- update sync_repo.py for using pulp.util.loadConfig (jmatthew@redhat.com)
- add support for config file to large_load.py (jmatthew@redhat.com)
- update package lookup (jmatthew@redhat.com)
- Incorrect config retrieval format (jason.dobies@redhat.com)
- Changed to pull from config (jason.dobies@redhat.com)
- update in DELETE doc string (jconnor@redhat.com)
- Added pulp.ini to spec file (jason.dobies@redhat.com)
- Added configuration infrastructure to pulp API calls
  (jason.dobies@redhat.com)
- Added httpd as a requirement (it's used to serve repos)
  (jason.dobies@redhat.com)
- Add debug line to show which repo/package are being added to repo
  (jmatthew@redhat.com)
- testing failure (mmccune@redhat.com)
- unit test fixes (jmatthew@redhat.com)
- Added a sync_repo helper script, fixed a few issues preventing a repo sync
  import from working. Updated display_repo to work with 'master' as well as
  branch 'modelchanges' (jmatthew@redhat.com)
- instructing pymongo to use "safe" save calls, i.e. throw an exception on a
  problem, don't silently fail (jmatthew@redhat.com)
- Removing unused references (jmatthew@redhat.com)
- helper script to display repos and packages (jmatthew@redhat.com)
- update to be compatible with api refactoring (jmatthew@redhat.com)
- adding manual egg-info workaround for now (jconnor@localhost.localdomain)
- before creating a new package, check to see if one exists then reuse if it
  does (jmatthew@redhat.com)
- Add SON Manipulators to handle auto referencing/dereferencing for objects in
  different collections (jmatthew@redhat.com)
- added json import fallback of simplejson (jconnor@localhost.localdomain)
- changed import of json to look for simplejson as a fallback
  (jconnor@localhost.localdomain)
- removed -N option from useradd, which was causing it to fail on rhel5
  (jconnor@localhost.localdomain)
- added python-ssl rpm stuff to get egg info in (jconnor@localhost.localdomain)
- added dependency discovery based on python version
  (jconnor@localhost.localdomain)
- removed setuptools patch and just called setuptools directly in rpm spec file
  (jconnor@localhost.localdomain)
- adding modified web.py rpm for epel build (jconnor@localhost.localdomain)
- Adding a test to explore how mongo works with DBRefs (jmatthew@redhat.com)
- fix so unittests can run (jmatthew@redhat.com)
- Fixed src location (jason.dobies@redhat.com)
- Refactored api module into a package with multiple modules.
  (jason.dobies@redhat.com)
- Automatic commit of package [pulp] release [0.0.5-1]. (ayoung@redhat.com)
- Fix for package versions, we weren't storing 'requires' or 'provides' in
  mongo this info was saved on the 'package' object it was attached to, but was
  not saved in the 'packageversion' collection (jmatthew@redhat.com)
- adding extra data for Categories (jmatthew@redhat.com)

* Thu May 27 2010 Adam Young <ayoung@redhat.com> 0.0.5-1
- Updated Dirs in var (ayoung@redhat.com)
- Added a patch to build 32 bit on 64 bit RH systems (ayoung@redhat.com)
- Updated to the WsRepoApi (jason.dobies@redhat.com)
- First pass at web services tests (jason.dobies@redhat.com)
- Renamed RepoConnection methods to be the same as their RepoApi counterpart.
  This way, we can use the RepoConnection object as a web services proxy and
  pass it into the unit tests that make direct calls on the RepoApi object.
  (jason.dobies@redhat.com)
- moving sub calls to separate class (pkilambi@redhat.com)
- fixed typo in doc added id to repo_data for update (jconnor@redhat.com)
- spec file changes to get closer to Fedora compliance. (ayoung@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jason.dobies@redhat.com)
- Missing self reference (jason.dobies@redhat.com)
- added some task cleanup to tasks as well as the base queue class added
  cleanup calls to test_tasks (jconnor@redhat.com)
- fixed missing 'id' parameter to repository update (jconnor@redhat.com)
-  New project for pulp client. Initial commit includes: (pkilambi@redhat.com)
- removing authors (mmccune@redhat.com)
- minor cleanup (mmccune@redhat.com)
- fixed my regular expressions for repositories and test applications changed
  create repo from /repostiories/new/ to just /repositories/ in case someone
  wants a repo called 'new' updated doc to reflect change (jconnor@redhat.com)
- updated docs to reflect new id (jconnor@redhat.com)
- changing regex to accept any type of id (jconnor@redhat.com)
- added creat url to documentation (jconnor@redhat.com)
- added 'next' keyword some formatting cleanup (jconnor@redhat.com)
- create index in background and add more data to PackageGroup objects
  (jmatthew@redhat.com)
- deleting grinder.  now avail in its own git repo (mmccune@redhat.com)
- cleanup on setup and teardown (mmccune@redhat.com)
- Added grinder egg to ignore (jason.dobies@redhat.com)
- Refactored unit tests into their own directory (jason.dobies@redhat.com)
- add methods for listing package groups/categories from repo api
  (jmatthew@redhat.com)
- fixing randomString casing and making unit tests work without root
  (mmccune@redhat.com)
- adding the pulp repo file (jconnor@redhat.com)
- fixed my test_tasks for the fifo tests (jconnor@redhat.com)
- extensive regex construction for at time specifications added some
  documentation to at queues added place-holder persistent queue module
  (jconnor@redhat.com)
- Test update to see if I can commit (jason.dobies@redhat.com)
- adding object/api for PackageGroup and PackageGroupCategory to represent data
  in comps.xml (repodata). (jmatthew@redhat.com)
- mid-stream modifications of more powerful at time spec parser
  (jconnor@redhat.com)
- adding preuninstall to stop a currently running server adding forceful
  deletion of db lock to uninstall (jconnor@redhat.com)
- added user and group cleanup on uninstall to mongo's spec file
  (jconnor@redhat.com)

* Mon May 24 2010 Adam Young <ayoung@redhat.com> 0.0.4-1
- added dep for  setup-tools (ayoung@redhat.com)
- Removed the _U option that was breaking installs on epel. (ayoung@redhat.com)
- Removed build dep on pymongo, as it breaks a mock build. (ayoung@redhat.com)
- Added nosetest, with failing tests excluded. (ayoung@redhat.com)
- Corrected name in changelog (ayoung@redhat.com)
- Updated changelog. (ayoung@redhat.com)
- Updated to work with tito. (ayoung@redhat.com)
- Adding objects for PackageGroup & Category (jmatthew@redhat.com)
- removed duplicate 'consumers' definiton in ConsumerApi (jmatthew@redhat.com)
- adding unique index on all objects based on id (mmccune@redhat.com)
- pointing readme to wiki (mmccune@redhat.com)
- validate downloaded bits before status checks . this way we can clean up
  empty packages and the return error state (pkilambi@redhat.com)
- remove uneeded dir find code.  instead use magic __file__ attrib
  (mmccune@redhat.com)
- make it so we can run our tests from top level of project
  (mmccune@redhat.com)
- Automatic commit of package [grinder] release [0.0.49-1].
  (jmatthew@redhat.com)
- fix 'fetch' call to pass in hashType, this prob showed up during a long sync
  when auth data became stale we would refresh auth data, then re-call fetch.
  The call to fetch was missing hashType (jmatthew@redhat.com)
- Automatic commit of package [pulp] release [0.0.3-1]. (ayoung@redhat.com)
- adding mongo helper for json dumping (mmccune@redhat.com)
- Grinder: before fetching the repodata convert the url to ascii so urlgrabber
  doesnt freakout (pkilambi@redhat.com)
- encode urls to ascii to please urlgrabber (pkilambi@redhat.com)
- logging info change, as per QE request (jmatthew@redhat.com)

* Fri May 21 2010 Adam Young <ayoung@redhat.com> 0.0.3-2
- Added dependencies 
  
* Thu May 20 2010 Adam Young <ayoung@redhat.com> 0.0.3-1
- fixed call to setup to install all files

* Thu May 20 2010 Mike McCune <mmccune@redhat.com> 0.0.2-1
- tito tagging

* Thu May 20 2010 Adam Young 0.0.3-1
- Use macro for file entry for juicer
- strip leading line from files that are not supposed to be scripts 

* Wed May 19 2010 Adam Young  <ayoung@redhat.com> - 0.0.1
- Initial specfile
