# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           pulp
Version:        0.0.12
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

Requires: python-pymongo
Requires: python-setuptools
Requires: python-webpy
Requires: grinder
Requires: httpd
Requires: mod_wsgi
Requires: mongo
Requires: mongo-server

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

cp -R test %{buildroot}/%{python_sitelib}/%{name}

mkdir -p %{buildroot}/etc/httpd/conf.d/
cp %{buildroot}/etc/httpd/conf.d/juicer.conf %{buildroot}/etc/httpd/conf.d/
cp -R srv %{buildroot}

mkdir -p %{buildroot}/etc/pulp
cp %{buildroot}/etc/pulp/juicer.ini %{buildroot}/etc/pulp
cp %{buildroot}/etc/pulp/pulp.ini %{buildroot}/etc/pulp

mkdir -p %{buildroot}/var/lib/pulp
chown apache:apache %{buildroot}/var/lib/pulp
mkdir -p %{buildroot}/var/www/html/
ln -s /var/lib/pulp %{buildroot}/var/www/html/pub

mkdir -p %{buildroot}/var/log/pulp
chown apache:apache %{buildroot}/var/log/pulp

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
%config(noreplace) /etc/juicer.ini
%config(noreplace) /etc/pulp.ini
%config(noreplace) /etc/httpd/conf.d/juicer.conf
/etc/pulp
/srv/juicer/juicer.wsgi
/var/lib/pulp
/var/www/html/pub
/var/log/pulp

%changelog
* Fri Jun 04 2010 Mike McCune <mmccune@redhat.com> 0.0.12-1
- rebuild
* Thu Jun 03 2010 Mike McCune <mmccune@redhat.com> 0.0.10-1
- large numbers of changes.  see git for list
* Thu Jun 03 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.7-1
- Link the grinder synchronized packages over to apache
  (jason.dobies@redhat.com)
- was missing an import, and CompsException needed to be fully qualified
  (jmatthew@redhat.com)
- make the imports absolute to the files running
  (mmccune@gibson.pdx.redhat.com)
- added pulps configuration to wsgi script (jconnor@redhat.com)
- changed the way juicer handles pulp's configuration at runtime
  (jconnor@redhat.com)
- added preliminary packages controllers cleanup in repositories and consumers
  controllers (jconnor@redhat.com)
- removing failed test (mmccune@gibson.pdx.redhat.com)
- fixing the help options to render based on the command (pkilambi@redhat.com)
- Adding consumer commands and actions to corkscrew (pkilambi@redhat.com)
- debugging and testing of pulp rpm spec for new apache deployment
  (jconnor@redhat.com)
- removing gevet daemon deployment and adding apache deployment
  (jconnor@redhat.com)
- moving the POST to consumers call (pkilambi@redhat.com)
- Adding webservices consumer calls based on available api.
  (pkilambi@redhat.com)
- pkg counts in cli reports and adding consumer connections
  (pkilambi@redhat.com)
- Temporary configuration loading (jason.dobies@redhat.com)

* Wed Jun 02 2010 Jason L Connor <jconnor@redhat.com> 0.0.6-1
- removed gevent deployment
- added apache deployment

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
