# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           pulp
Version:        0.0.68
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

Requires: pulp-common = %{version}
Requires: python-pymongo
Requires: python-setuptools
Requires: python-webpy
Requires: python-simplejson
Requires: grinder >= 0.0.59
Requires: httpd
Requires: mod_wsgi
Requires: mod_python
Requires: mod_ssl
Requires: mongo
Requires: mongo-server
Requires: m2crypto
Requires: openssl
Requires: qpidd
Requires: qpidd-ssl
%if 0%{?fedora} < 13
Requires: rhm-cpp-server-store
%else:
Requires: qpid-cpp-server-store
%endif
# newer pulp builds should require same client version
Requires: %{name}-client >= %{version}

%if 0%{?rhel} > 5
Requires: python-hashlib
%endif


%description
Pulp provides replication, access, and accounting for software repositories.


%package common
Summary:        Pulp common modules.
Group:          Development/Languages
BuildRequires:  rpm-python
Requires: python-simplejson
Requires: python-qpid >= 0.7

%description common
Contains modules common to the Pulp server and client.


%package client
Summary:        Client side tools for managing content on pulp server
Group:          Development/Languages
BuildRequires:  rpm-python
Requires: pulp-common = %{version}
Requires: python-simplejson
Requires: m2crypto

%if 0%{?rhel} > 5
Requires: python-hashlib
%endif

%description client
A collection of tools to interact and perform content specific operations such as repo management, 
package profile updates etc.
 

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

# Pulp Configuration
mkdir -p %{buildroot}/etc/pulp
cp etc/pulp/* %{buildroot}/etc/pulp

mkdir -p %{buildroot}/var/log/pulp

# Apache Configuration
mkdir -p %{buildroot}/etc/httpd/conf.d/
cp etc/httpd/conf.d/pulp.conf %{buildroot}/etc/httpd/conf.d/

cp -R srv %{buildroot}

mkdir -p %{buildroot}/etc/pki/pulp
mkdir -p %{buildroot}/etc/pki/consumer
cp etc/pki/pulp/* %{buildroot}/etc/pki/pulp

mkdir -p %{buildroot}/etc/pki/content

mkdir -p %{buildroot}/var/lib/pulp
mkdir -p %{buildroot}/var/www
ln -s /var/lib/pulp %{buildroot}/var/www/pub

# Pulp Agent
mkdir -p %{buildroot}/usr/bin
cp bin/pulpd %{buildroot}/usr/bin

mkdir -p %{buildroot}/etc/init.d
cp etc/init.d/pulpd %{buildroot}/etc/init.d

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/%{name}*.egg-info

%clean
rm -rf %{buildroot}

%post
setfacl -m u:apache:rwx /etc/pki/content/

%files
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/server/
%config(noreplace) /etc/pulp/pulp.conf
%config(noreplace) /etc/httpd/conf.d/pulp.conf
%attr(775, apache, apache) /etc/pulp
%attr(775, apache, apache) /srv/pulp
%attr(750, apache, apache) /srv/pulp/webservices.wsgi
%attr(750, apache, apache) /srv/pulp/bootstrap.wsgi
%attr(3775, apache, apache) /var/lib/pulp
%attr(3775, apache, apache) /var/www/pub
%attr(3775, apache, apache) /var/log/pulp
%attr(3775, root, root) /etc/pki/content
/etc/pki/pulp/ca.key
/etc/pki/pulp/ca.crt


%files common
%defattr(-,root,root,-)
%doc
%{python_sitelib}/pulp/*.py*
%{python_sitelib}/pulp/messaging/


%files client
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/pulp/client/
%{_bindir}/pulp-admin
%{_bindir}/pulp-client
%{_bindir}/pulpd
%attr(755,root,root) %{_sysconfdir}/init.d/pulpd
%attr(755,root,root) %{_sysconfdir}/pki/consumer/
%config(noreplace) /etc/pulp/client.conf

%post client
chkconfig --add pulpd

%preun client
if [ $1 = 0 ] ; then
   /sbin/service pulpd stop >/dev/null 2>&1
   /sbin/chkconfig --del pulpd
fi


%changelog
* Fri Sep 24 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.68-1
- 635803 - Fixed repo sync schedule to use the existing model (for auditing and
  consumer history reapers) for the cron entries. (jason.dobies@redhat.com)
- fixing delete repos to nuke the repo from DB as well as filesystem
  (pkilambi@redhat.com)
* Wed Sep 22 2010 Mike McCune <mmccune@redhat.com> 0.0.67-1
- 634705 - suppress receiving locally published events. (jortel@redhat.com)

* Wed Sep 22 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.66-1
- Ensure complete_callback invoked in failure cases. (jortel@redhat.com)
- 619077 - make the feed check handle not being in the dict
  (mmccune@redhat.com)
- 619077 - implement repo update from CLI (mmccune@redhat.com)
- This commit includes: * Support call for product.deleted event handler to
  look for deleted action on the bus * API call to perform delete action on
  candidate/synced repos * product driver delete call (pkilambi@redhat.com)
- Enhance async API plumbing and refit installpackages(). (jortel@redhat.com)
- 626459 - The temporary yum file should be placed in the /tmp directory.
  (jason.dobies@redhat.com)
- Refactored consumer originator event detection to be done in the consumer
  history API, using the principal to determine if the request is made by an
  admin or consumer. (jason.dobies@redhat.com)
- Consumergroup api and cli changes for key-value attributes
  (skarmark@redhat.com)
- Adding consumer listing by key_value_pairs (skarmark@redhat.com)
- Adding indexes for key_value_pairs (skarmark@redhat.com)
- server-side support for last sync repo field (jconnor@redhat.com)
- merge of repo status command (jconnor@redhat.com)
- organized imports and globals addedd/fixed gettext internationalizaion on all
  print statements used print_header (jconnor@redhat.com)
- 623969 - add unit test for bug (mmccune@redhat.com)
- 623969 - make sure we convert the unicode pass to a string before hmac
  (mmccune@redhat.com)
- Added ability to disable the consumer history purge (jason.dobies@redhat.com)
- Added appropriate indices (jason.dobies@redhat.com)
- changed progress out to use sys.stdout.write instead of print reduced
  foreground sleep time to 1/4 second reduced progress bar size to accomodate
  repos w/ 100,000-999,999 packages (jconnor@redhat.com)
- 636135 - fix string format error (pkilambi@redhat.com)
- Fix SSL char * error (jesusr@redhat.com)
- added sleep back into foreground sync (jconnor@redhat.com)
- adding check for whether key exists before updating it (skarmark@redhat.com)
- adding consumerid for admin functions (skarmark@redhat.com)
- delete_keyvalue should pass in only key information (skarmark@redhat.com)
- Adding cli and api functions for adding and deleting key-value pairs
  (skarmark@redhat.com)
- Adding key_value_pairs in consumer default_fields (skarmark@redhat.com)
- Removing key_value_pairs from ConsumerDeferredFields (skarmark@redhat.com)
- merge of foreground and background sync methods (jconnor@redhat.com)
- fixed internationalization gettext calls (jconnor@redhat.com)
- Adding consumer api and cli changes for adding key-value attributes for
  consumer (skarmark@redhat.com)
- Fixing wrong package name in test_comps.py (skarmark@redhat.com)
- 629987 - Adding a check for existing package in a repo before adding or
  deleting from package group (skarmark@redhat.com)
- 629720 - delete consumer now takes care of deleting consumerid from
  consumergroups as well (skarmark@redhat.com)
- start of GET method handler for repository actions (jconnor@redhat.com)

* Fri Sep 17 2010 Mike McCune <mmccune@gmail.com> 0.0.65-1
- fixing conditonal else statement (mmccune@gmail.com)

* Fri Sep 17 2010 Mike McCune <mmccune@gmail.com> 0.0.64-1
- fedora conditional install of qpid libs (mmccune@gmail.com)

* Fri Sep 17 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.63-1
- Changing the product.created to match envelope on the bus
  (pkilambi@redhat.com)
- add a groupid filter to only display repos by groups (pkilambi@redhat.com)
- Set PendingQueue.ROOT to accessible location for unit tests.
  (jortel@redhat.com)
- Validate file imports if they exist before importing (pkilambi@redhat.com)
- 623900 - Fixed consumer delete call to pymongo to use the correct parameter
  (jason.dobies@redhat.com)
- Adding file/image sync support for local syncs (pkilambi@redhat.com)
- adding qpidd requires since we actually do require these (mmccune@gmail.com)

* Thu Sep 16 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.62-1
- Including files as a sub document in repo collection and send down file count
  per repo on repo list (pkilambi@redhat.com)
- Increase the buffsersize to 2G so we can upload larger files to pulp server
  (pkilambi@redhat.com)
- add close() to Consumer. (jortel@redhat.com)
- removed async sync calls from comps as well (jconnor@redhat.com)
- pushed async support for repo.sync down into api later added list_syncs
  methods for a given repo (jconnor@redhat.com)
- changed the display to replace the packages url with the package count
  instead of a new field (jconnor@redhat.com)
- added package count to client repo list output (jconnor@redhat.com)
- added package_count field to repository information returned by web services
  (jconnor@redhat.com)
- added package_count method to repository api (jconnor@redhat.com)
- fixed a bug where I was creating a weak reference to a weak reference
  (jconnor@redhat.com)
- converted async controllers to use new async api and handle lists of tasks
  being returned by the find call (jconnor@redhat.com)
- changed queue find to return a list of tasks instead of just the first,
  newest one found (jconnor@redhat.com)
- moved canonical server-side queue async module and implemented simple api for
  it (jconnor@redhat.com)
- changed _thread_dict to use weak references so that it no longer needs
  exlicit cleanup (jconnor@redhat.com)
- replaced deprecated call into task thread (jconnor@redhat.com)

* Fri Sep 10 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.61-1
- Added errata install and package profile entries to consumer history.
  (jason.dobies@redhat.com)
- Added defaults to pulp.conf to make the config file more self-documenting.
  This way users can look at a single location for information needed to change
  pulp behavior. (jason.dobies@redhat.com)
- consoldated exception types in thread interruption api to keep me from
  catching an exception that I do not mean to found bug in monkey patch, cut-
  copy-paster error in TaskThread.raise_exception (jconnor@redhat.com)
- use existing repositories method with fields and spec to query repos by group
  instead of a separate method (pkilambi@redhat.com)
- changing product reference to group (pkilambi@redhat.com)
- Added cron tab addition and hook so the cull will be run periodically.
  (jason.dobies@redhat.com)
- Added API call for culling consumer history older than a certain number of
  days. (jason.dobies@redhat.com)
- Adding support for relative_path and groupid when doing a repo create
  (pkilambi@redhat.com)
- include checksum in package store path (pkilambi@redhat.com)
- On demand stub creation for better plugin support. (jortel@redhat.com)
- added tracked thread and made task thread inherit from it monkey patching
  tasking.Thread wit tracked thread added look to task thread raise exception
  to deliver the same exception to all descendant threads (jconnor@redhat.com)

* Tue Sep 07 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.60-1
- Setup callbacks only for repos with source set. A feedless repo can have a
  source as None (pkilambi@redhat.com)
- fixing arch based pkg installs to pass in tuple to yum instead of str
  (pkilambi@redhat.com)
- Added date and limit support to the CLI consumer history queries
  (jason.dobies@redhat.com)
- fixes needed from rename of add_packages_to_group (jmatthew@redhat.com)
- Fixed check for consumer's existence to not rely on the consumer API.
  (jason.dobies@redhat.com)
- Added parser call for handling JSON datetime encodings.
  (jason.dobies@redhat.com)
- 618820 - Fixing indentation error (skarmark@redhat.com)
- 618820 - Adding multiple package support for packagegroup add_package
  (skarmark@redhat.com)
- adding apache perms to /src/pulp so lock files dont complain about perms
  error (pkilambi@redhat.com)
- Wired in consumer history calls to consumer API (jason.dobies@redhat.com)
- 629718 - more defensive code if we have no default locale
  (mmccune@redhat.com)
- Centralized Package Location Feature: (pkilambi@redhat.com)
- Mark messages as persistent. (jortel@redhat.com)
- adding pulpd as a script (mmccune@redhat.com)
- adding pulpd to setup script and making it executable (mmccune@redhat.com)
- 629075 - Return complete NVRE for installed packages. (jortel@redhat.com)
- Added sorting and date range query functionality (jason.dobies@redhat.com)
- Adding a dir for curl scripts to help test ws api (jmatthew@redhat.com)
- Protect against bind to repo that does not exist. (jortel@redhat.com)
- Package re-sync, if a package is deleted from the source it will be removed
  from the repo (jmatthew@redhat.com)
- Add relative_path to repo default fields. (jortel@redhat.com)
- Remove dead file & update repolib to use repo.relative_path instead of repo
  id. (jortel@redhat.com)
- make relativepath default to repoid for non product repos. This should make
  the full path basepath + <repoid> (pkilambi@redhat.com)

* Wed Sep 01 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.59-1
- adding productid to default fields and query ability (mmccune@redhat.com)
- Refine how re-raised (inbound) events are suppressed. (jortel@redhat.com)
- add builtin support for: ~/.pulp/client.conf (jortel@redhat.com)
- Fix for Errata Re-Sync updating info in an existing errata
  (jmatthew@redhat.com)
- Minor changes to event based repos (pkilambi@redhat.com)
- Fix bootstrap startup in wsgi so wont do foreach thread. (jortel@redhat.com)
- expand log format and make start_loggin() idempotent. (jortel@redhat.com)
- add bootstrap to start event listener. (jortel@redhat.com)
- update for errata sync, partial check-in adds fix for removed errata to be
  disassociated with the repo needs fix for updating an existing errata needs
  fix for deleting an errata if no repos are associated to it
  (jmatthew@redhat.com)
- if no relative path, user repoid (pkilambi@redhat.com)
- Invoke API before and only send event on succeeded. (jortel@redhat.com)
- convert the status path to string from unicode before doing a GET
  (pkilambi@redhat.com)
- Adding API call to look up repos by product and unit tests
  (pkilambi@redhat.com)
- fix relativepaths to certs (pkilambi@redhat.com)
- Use relative paths when syncing content to store on filesystem instead of
  repoid. This should help validate the client requests for content via cert
  validation (pkilambi@redhat.com)
- Correcting error in string conversion of argument (skarmark@redhat.com)
- fix product handler import. (jortel@redhat.com)
- Fix method not found exception syntax. (jortel@redhat.com)
- Replace noevent pseudo argument with thread data. (jortel@redhat.com)
- Add stubbed product event hanlder. (jortel@redhat.com)
- Add pulp event framework. (jortel@redhat.com)
- "Printing task id at the time of sync" (skarmark@redhat.com)
- Revert "Reverting cancel sync change to check whether this commit cause json
  errors" Verified that JSON errors were not because of this commit. This
  reverts commit 983791a517a85dd84b4df7197eef207b7e100489.
  (skarmark@redhat.com)

* Fri Aug 27 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.58-1
- Make sure to include the user's home directory in the destination
  (jason.dobies@redhat.com)
- Added hook to use the admin certificate if one is found.
  (jason.dobies@redhat.com)
- Fix the consumer help to list usage correctly (pkilambi@redhat.com)
- Merge branch 'master' of git+ssh://git.fedorahosted.org/git/pulp
  (pkilambi@redhat.com)
- fixing regression where we add list instead of str to install list of there
  is no arch (pkilambi@redhat.com)
- Added CLI hooks for admin login/logout. (jason.dobies@redhat.com)
- Refactored so we have access to the user object to store as the principal if
  the user is authenticated. (jason.dobies@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jconnor@redhat.com)
- implemented progress callbacks for rhn and yum repo syncs this includes a
  "pass-through" callback in tasks, that take a callback argument name and the
  callback function then passes in its own callback wrapper which executes the
  callback and assigns it to a progress field added callback parameters to all
  repo sync methods modified jmathews callback to return a dictionary
  (jconnor@redhat.com)
- Added webservice calls for admin auth certificates (jason.dobies@redhat.com)
- Added API for retrieving an admin certificate for the currently logged in
  user (jason.dobies@redhat.com)
- Merge config writes to alt config when specified. (jortel@redhat.com)
- Renamed to reflect it's an API test (jason.dobies@redhat.com)
- Added return type docs (jason.dobies@redhat.com)
- Removed plain text echo of the user's password (jason.dobies@redhat.com)
- Merge branch 'master' of ssh://git.fedorahosted.org/git/pulp
  (jconnor@redhat.com)
- Revert "Reverting cancel sync change to check whether this commit cause json
  errors" Confirmed that JSON errors were not because of this commit This
  reverts commit 983791a517a85dd84b4df7197eef207b7e100489.
  (skarmark@redhat.com)
- Reverting cancel sync change to check whether this commit cause json errors
  (skarmark@redhat.com)
- Not printing task id at the time of sync (skarmark@redhat.com)
- Adding cancel sync and sync status to cli (skarmark@redhat.com)
- shortten environment var. (jortel@redhat.com)
- Add certlib (work in progress) (jortel@redhat.com)
- Default key and cert. (jortel@redhat.com)
- Add PULP_CLIENT_ALTCONF envrionment var to specify alt conf to be merged.
  (jortel@redhat.com)
- changing client.conf to point to localhost and not guardian
  (skarmark@redhat.com)
- repo sync timeout changes (skarmark@redhat.com)
- repo sync timeout changes (skarmark@redhat.com)
- adding productid identifier as an optional reference to tie candlepin product
  to repos (pkilambi@redhat.com)
- some re-organization (jconnor@redhat.com)

* Wed Aug 25 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.57-1
- Missed an entry in the package refactor (jason.dobies@redhat.com)

* Wed Aug 25 2010 Mike McCune <mmccune@redhat.com> 0.0.56-1
- rebuild
* Wed Aug 25 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.55-1
- Release 0.1 build
* Fri Aug 20 2010 Mike McCune <mmccune@redhat.com> 0.0.54-1
- rebuild
* Fri Aug 20 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.53-1
- Missed a server import rename (jason.dobies@redhat.com)
- Merge branch 'master' into code-reorganization (jason.dobies@redhat.com)
- Discontinue installing the egg into site-packages. (jortel@redhat.com)
- Fix .spec problem with pulp-* egg. (jortel@redhat.com)
- Update spec to match code refactoring. (jortel@redhat.com)
- Update spec to match code refactoring. (jortel@redhat.com)
- Update imports for refactoring. (jortel@redhat.com)
- Updated for new package structure and cleaned up unused imports
  (jason.dobies@redhat.com)
- Updated imports for new structure (jason.dobies@redhat.com)
- quiet the logging (mmccune@redhat.com)
- Move pulptools to: pulp.client.  Update pmf imports. (jortel@redhat.com)
- update section names pmf->messaging. (jortel@redhat.com)
- moved to server where it belongs.  Updated imports and .conf section.
  (jortel@redhat.com)
- moved pmf to: pulp.messaging. (jortel@redhat.com)
- First steps in major package refactoring: just shuffling files into the
  proper directories (jason.dobies@redhat.com)
- added unicode cast to principal (jconnor@redhat.com)
- reset does not need to manage a queue managed resource (jconnor@redhat.com)
- check if packages exist before computing the length (pkilambi@redhat.com)
- set the exception to jus message instead of an object so its serializable
  (pkilambi@redhat.com)
- removing bad attributes on Task objects causing tracebacks
  (pkilambi@redhat.com)

* Wed Aug 18 2010 Mike McCune <mmccune@redhat.com> 0.0.52-1
- rebuild

* Mon Aug 16 2010 Jeff Ortel <jortel@redhat.com> 0.0.50-1
- rebuild
* Thu Aug 12 2010 Mike McCune <mmccune@redhat.com> 0.0.49-1
- rebuild
* Fri Aug 06 2010 Mike McCune <mmccune@redhat.com> 0.0.48-1
- rebuild

* Wed Aug 04 2010 Mike McCune <mmccune@redhat.com> 0.0.47-1
- rebuild
* Fri Jul 30 2010 Mike McCune <mmccune@redhat.com> 0.0.46-1
- rebuild
* Thu Jul 29 2010 Mike McCune <mmccune@redhat.com> 0.0.44-1
- rebuild

* Tue Jul 27 2010 Jason L Connor <jconnor@redhat.com> 0.0.43-1
- tio tag
* Tue Jul 27 2010 Jason L Connoe <jconnor@redhat.com> 0.0.42-1
- added gid and sticky bit to /var/[lib,log,www]/pulp directories

* Fri Jul 23 2010 Mike McCune <mmccune@redhat.com> 0.0.41-1
- rebuild
* Thu Jul 22 2010 Jason L Connor <jconnor@redhat.com> 0.0.40-1
- removed juicer from configuration

* Fri Jul 16 2010 Mike McCune <mmccune@redhat.com> 0.0.39-1
- rebuild
* Thu Jul 15 2010 Sayli Karmarkar <skarmark@redhat.com> 0.0.37-1
- Turned off client side SSL cert checking (jason.dobies@redhat.com)
- changed string index to find so that the logic will work (jconnor@redhat.com)
- added auditing to users api (jconnor@redhat.com)
- added spec and fields to users api some code clean up added check for neither
  id or certificate in create (jconnor@redhat.com)
- added auditing to packages api (jconnor@redhat.com)
- added auditing to consumer api (jconnor@redhat.com)
- added auditing to the repo api (jconnor@redhat.com)
- fixed bug in copy that doesnt return a list (jconnor@redhat.com)
- finished general code review and cleanup added _get_existing_repo to
  standardize exception message and reduce cut-copy-paste code
  (jconnor@redhat.com)

* Thu Jul 15 2010 Mike McCune <mmccune@redhat.com> 0.0.36-1
- rebuild
* Thu Jul 01 2010 Mike McCune <mmccune@redhat.com> 0.0.35-1
- rebuild

* Thu Jul 01 2010 Jay Dobies <jason.dobies@redhat.com> 0.0.34-1
- Removed unncessary line; ownership of /var/log/pulp is given to apache in
  %post (jason.dobies@redhat.com)

* Wed Jun 30 2010 Mike McCune <mmccune@redhat.com> 0.0.33-1
- rebuild
* Mon Jun 28 2010 Mike McCune <mmccune@redhat.com> 0.0.31-1
- rebuild
* Wed Jun 23 2010 Mike McCune <mmccune@redhat.com> 0.0.28-1
- rebuild
* Mon Jun 21 2010 Mike McCune <mmccune@redhat.com> 0.0.26-1
- Weekly rebuild.  See SCM for history

* Wed Jun 16 2010 Mike McCune <mmccune@redhat.com> 0.0.24-1
- massive amounts of changes from the last few weeks

* Wed Jun 09 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.23-1
- inlcude only pulp and juicer for pulp rpm (pkilambi@redhat.com)
- Adding pulp-tools as a new subrpm (pkilambi@redhat.com)
- Change pythonpath to new client location. (jortel@redhat.com)
- Fix test_consumerwithpackage() in WS unit tests. Add
  juicer/controllers/base.py.params() to get passed parameters.
  (jortel@redhat.com)
- rename client to pulp-tools (pkilambi@redhat.com)
- removing accidental log entry (pkilambi@redhat.com)
- moving client under src for packaging (pkilambi@prad.rdu.redhat.com)
- Add consumer update() in WS. (jortel@redhat.com)
- Assign model object._id in constructor. (jortel@redhat.com)
- Another dumb mistake (jason.dobies@redhat.com)
- Fat fingered the signature (jason.dobies@redhat.com)
- streamline bind/unbind params. (jortel@redhat.com)
- Client side web service implementation for packages (jason.dobies@redhat.com)
- switching to an insert vs append so we always use src in git tree
  (mmccune@redhat.com)
- Add basic web service API tests. (jortel@redhat.com)
- Typo (jason.dobies@redhat.com)
- Initial work on packages API (jason.dobies@redhat.com)
- Added web service hook to consumer clean (jason.dobies@redhat.com)
- Added web service hook to repository clean (jason.dobies@redhat.com)
- Cleaned up for PEP8 format (jason.dobies@redhat.com)
- Cleaning up for PEP8 format (jason.dobies@redhat.com)
- Cleaning up for PEP8 format (jason.dobies@redhat.com)
- Cleaning up for PEP8 format (jason.dobies@redhat.com)
- Fixed broken config test (jason.dobies@redhat.com)
- Docs (jason.dobies@redhat.com)
- Oops, forgot to remove debug info (jason.dobies@redhat.com)
- Fixed logic for importing packages to make sure the package version doesn't
  already exist (jason.dobies@redhat.com)
- Moved non-unit test to common area (jason.dobies@redhat.com)
- Removed unsupported test file (jason.dobies@redhat.com)
- the proxy call's signature matches api (pkilambi@redhat.com)
- Added test case for RHN sync (jason.dobies@redhat.com)

* Wed Jun 09 2010 Pradeep Kilambi <pkilambi@redhat.com>
- Adding pulp-tools as a sub rpm to pulp

* Mon Jun 07 2010 Mike McCune <mmccune@redhat.com> 0.0.22-1
- Renamed method (jason.dobies@redhat.com)
- Refactored out common test utilities (jason.dobies@redhat.com)
- Removed temporary logging message (jason.dobies@redhat.com)

* Mon Jun 07 2010 Pradeep Kilambi <pkilambi@redhat.com> 0.0.20-1
- reflect the subscribed repos in list (pkilambi@redhat.com)
- Adding bind and unbind support for the cli (pkilambi@redhat.com)
- If repo dir doesnt exist create it before storing the file and adding some
  logging (pkilambi@redhat.com)

* Fri Jun 04 2010 Mike McCune <mmccune@redhat.com> 0.0.18-1
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
