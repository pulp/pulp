# If on Fedora 12 or RHEL 5 or earlier, we need to define these:
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif


Name: python-rhsm
Version: 1.8.0
Release: 2.pulp%{?dist}

Summary: A Python library to communicate with a Red Hat Unified Entitlement Platform
Group: Development/Libraries
License: GPLv2
# How to create the source tarball:
#
# git clone git://git.fedorahosted.org/git/python-rhsm.git/
# cd client/python-rhsm
# tito build --tag python-rhsm-$VERSION-$RELEASE --tgz
Source0: %{name}-%{version}.tar.gz
Patch0:  ignore-warnings.patch
URL: http://fedorahosted.org/candlepin
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires: m2crypto
Requires: python-simplejson
Requires: python-iniparse
Requires: rpm-python

BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: openssl-devel


%description
A small library for communicating with the REST interface of a Red Hat Unified
Entitlement Platform. This interface is used for the management of system
entitlements, certificates, and access to content.

%prep
%setup -q -n python-rhsm-%{version}
%patch0 -p1

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
mkdir -p %{buildroot}%{_sysconfdir}/rhsm/ca
install etc-conf/ca/*.pem %{buildroot}%{_sysconfdir}/rhsm/ca

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc README

%dir %{python_sitearch}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm
%attr(755,root,root) %dir %{_sysconfdir}/rhsm/ca

%{python_sitearch}/rhsm/*
%{python_sitearch}/rhsm-*.egg-info
%attr(640,root,root) %{_sysconfdir}/rhsm/ca/*.pem

%changelog
* Tue Aug 12 2014 Randy Barlow <rbarlow@redhat.com> 1.8.0-2.pulp
- new package built with tito

* Mon Aug 11 2014 Randy Barlow <rbarlow@redhat.com>
- new package built with tito

* Mon Dec 03 2012 Michael Hrivnak <mhrivnak@redhat.com> 1.8.0-1.pulp
- updating to latest and greatest python-rhsm (mhrivnak@redhat.com)

* Tue Nov 20 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.8.0-1
- Reversioning to 1.8.x stream.

* Mon Nov 19 2012 Adrian Likins <alikins@redhat.com> 1.1.6-1
- Making product and order info optional for a v3 EntitlementCertificate, since
  the server side will never have that data. (mhrivnak@redhat.com)
- Adding path authorization checking for both v1 and v3 entitlement
  certificates (mhrivnak@redhat.com)

* Fri Nov 16 2012 Adrian Likins <alikins@redhat.com> 1.1.5-1
- Added ram_limit to certificate Order (mstead@redhat.com)

* Thu Nov 01 2012 Adrian Likins <alikins@redhat.com> 1.1.4-1
- fixing a bug where certificates with carriage returns could not be parsed.
  (mhrivnak@redhat.com)
- 790481: Send up headers with the subscription-manager and python-rhsm version
  info. (bkearney@redhat.com)

* Wed Oct 10 2012 Adrian Likins <alikins@redhat.com> 1.1.3-1
- 863961: add test case for id cert default version (alikins@redhat.com)
- 857426: Do not pass None when body is empty collection (mstead@redhat.com)
- 863961: set a default version for id certs (alikins@redhat.com)
- 859652: Subscribe with service level being ignored (wpoteat@redhat.com)

* Tue Sep 25 2012 Adrian Likins <alikins@redhat.com> 1.1.2-1
- add 6.4 releaser (alikins@redhat.com)

* Wed Sep 19 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.1.1-1
- Read certv3 detached format (jbowes@redhat.com)
- Read file content types from certificates (mstead@redhat.com)

* Wed Aug 29 2012 Alex Wood <awood@redhat.com> 1.0.7-1
- 851644: Only use the cert file if it exists (bkearney@redhat.com)

* Tue Aug 28 2012 Alex Wood <awood@redhat.com> 1.0.6-1
- 848742: support arbitrary bit length serial numbers (jbowes@redhat.com)
- Stop doing F15 Fedora builds, add EL5 public builds. (dgoodwin@redhat.com)

* Thu Aug 09 2012 Alex Wood <awood@redhat.com> 1.0.5-1
- add versionlint, requires pyqver (alikins@redhat.com)
- Adding subject back to new certs (mstead@redhat.com)
- 842885: add __str__ to NetworkException, ala  #830767 (alikins@redhat.com)
- 830767: Add __str__ method to RemoteServerException. (awood@redhat.com)
- Fix None product architectures. (dgoodwin@redhat.com)
- Remove deprecated use of DateRange.has[Date|Now] (jbowes@redhat.com)
- mark hasDate as deprecated as well (alikins@redhat.com)

* Wed Jul 25 2012 Alex Wood <awood@redhat.com> 1.0.4-1
- Remove unused stub method. (dgoodwin@redhat.com)
- Cleanup entitlement cert keys on delete. (dgoodwin@redhat.com)
- Drop unused quantity and flex quantity from Content. (dgoodwin@redhat.com)
- Make CertFactory and Extensions2 classes private. (dgoodwin@redhat.com)
- RHEL5 syntax fixes. (dgoodwin@redhat.com)
- Handle empty pem strings when creating certs. (dgoodwin@redhat.com)
- Remove Base64 decoding. (dgoodwin@redhat.com)
- Fix failing subjectAltName nosetest (jbowes@redhat.com)
- Fix up remaining compiler warnings (jbowes@redhat.com)
- Fix up memory leaks (jbowes@redhat.com)
- clean up some C module compiler warnings (jbowes@redhat.com)
- Fix get_all_extensions (jbowes@redhat.com)
- C module formatting fixups (jbowes@redhat.com)
- Add as_pem method to C module (jbowes@redhat.com)
- Revert Extensions object to old state, add new sub-class.
  (dgoodwin@redhat.com)
- Spec file changes for C module (jbowes@redhat.com)
- Get nosetests running (jbowes@redhat.com)
- tell setup.py to use nose (jbowes@redhat.com)
- get certv2 tests passing (jbowes@redhat.com)
- Move methods onto X509 class in C cert reader (jbowes@redhat.com)
- Add method to get all extensions in a dict (jbowes@redhat.com)
- Add POC C based cert reader (jbowes@redhat.com)
- Remove use of str.format for RHEL5. (dgoodwin@redhat.com)
- Remove some python2.6'ism (trailing if's) (alikins@redhat.com)
- add "version_check" target that runs pyqver (alikins@redhat.com)
- Fix error reporting on bad certs. (dgoodwin@redhat.com)
- Remove number from order/account fields. (dgoodwin@redhat.com)
- Style fixes. (dgoodwin@redhat.com)
- Certv2 cleanup. (dgoodwin@redhat.com)
- Cleanup bad padding/header cert testing. (dgoodwin@redhat.com)
- New method of parsing X509 extensions. (dgoodwin@redhat.com)
- Better cert type detection. (dgoodwin@redhat.com)
- Deprecate the old certificate module classes. (dgoodwin@redhat.com)
- Rename order support level to service level. (dgoodwin@redhat.com)
- Convert product arch to multi-valued. (dgoodwin@redhat.com)
- Add factory methods to certificate module. (dgoodwin@redhat.com)
- Parse V2 entitlement certificates. (dgoodwin@redhat.com)
- Add missing os import. (dgoodwin@redhat.com)
- Improve certificate2 error handling. (dgoodwin@redhat.com)
- Remove V1 named classes. (dgoodwin@redhat.com)
- Add cert is_expired method. (dgoodwin@redhat.com)
- Fix cert path issue. (dgoodwin@redhat.com)
- Major/minor attributes not available in 5.4 (mstead@redhat.com)
- 834108: Set the default connection timeout to 1 min. (jbowes@redhat.com)
- Add default values to certificate2 Order class. (dgoodwin@redhat.com)
- Define identity certificates explicitly. (dgoodwin@redhat.com)
- Add identity cert support to certificate2 module. (dgoodwin@redhat.com)
- Add file writing/deleting for new certificates. (dgoodwin@redhat.com)
- Add product info to certificate2 module. (dgoodwin@redhat.com)
- Add content info to certificate2 module. (dgoodwin@redhat.com)
- Add order info to certificate2 module. (dgoodwin@redhat.com)
- Port basic certificate data into new module. (dgoodwin@redhat.com)
- Add certificate2 module and cert creation factory. (dgoodwin@redhat.com)

* Thu Jun 28 2012 Alex Wood <awood@redhat.com> 1.0.3-1
- Update copyright dates (jbowes@redhat.com)
- 825952: Error after deleting consumer at server (wpoteat@redhat.com)

* Thu Jun 07 2012 Alex Wood <awood@redhat.com> 1.0.2-1
- add upstream server var to version obj (cduryee@redhat.com)
- 822057: wrap ContentConnection port in safe_int (cduryee@redhat.com)
- 822965: subscription-manager release does not work with proxies
  (cduryee@redhat.com)
- 806958: BadCertificateException not displaying properly. (awood@redhat.com)
- 822965: release verb does not work with proxies (cduryee@redhat.com)
- Add config for "checkcommits" (alikins@redhat.com)
- Include various Makefile improvements from subscription-manager
  (alikins@redhat.com)
- Upload el6 yum packages to another dir for compatability.
  (dgoodwin@redhat.com)

* Wed May 16 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 1.0.1-1
- Add default constants for RHN connections. (dgoodwin@redhat.com)
- 813296: Remove check for candlepin_version (jbowes@redhat.com)
- Remove module scope eval of config properties (alikins@redhat.com)
- Add call to get Candlepin status. (awood@redhat.com)
- Added access to python-rhsm/sub-man versions. (mstead@redhat.com)

* Thu Apr 26 2012 Michael Stead <mstead@redhat.com> 1.0.0-1
- Updated version due to 6.3 branching. (mstead@redhat.com)

* Wed Apr 04 2012 Michael Stead <mstead@redhat.com> 0.99.8-1
- 807721: Setting missing default values (mstead@redhat.com)

* Fri Mar 23 2012 Michael Stead <mstead@redhat.com> 0.99.7-1
- 803773: quote international characters in activation keys before sending to
  server (cduryee@redhat.com)
- PEP8 fixes. (mstead@redhat.com)

* Wed Mar 14 2012 Michael Stead <mstead@redhat.com> 0.99.6-1
- Add ContentConnection to support rhsm "release" command (alikins@redhat.com)
- Allow unsetting the consumer service level. (dgoodwin@redhat.com)

* Tue Mar 06 2012 Michael Stead <mstead@redhat.com> 0.99.5-1
- 744654: Any bad value from the config file, when converting to an int, causes
  a traceback. (bkearney@redhat.com)
- Add support for dry-run autobind requests. (dgoodwin@redhat.com)
- Build for Fedora 17. (dgoodwin@redhat.com)

* Wed Feb 22 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.4-1
- Add support for updating consumer service level. (dgoodwin@redhat.com)
- Add call to list service levels for an org. (dgoodwin@redhat.com)
- Add GoneException for deleted consumers (jbowes@redhat.com)

* Fri Jan 27 2012 Michael Stead <mstead@redhat.com> 0.99.3-1
- 785247: Update releasers.conf for RHEL6.3 (mstead@redhat.com)
- Stop building for F14. (dgoodwin@redhat.com)

* Thu Jan 12 2012 Devan Goodwin <dgoodwin@rm-rf.ca> 0.99.2-1
- 768983: When consuming a future subsciption, the repos --list should be empty
  (wpoteat@redhat.com)
- 720360: Write *-key.pem files out with 0600 permissions. (awood@redhat.com)
- 754425: Remove grace period logic (cduryee@redhat.com)

* Mon Dec 12 2011 William Poteat <wpoteat@redhat.com> 0.98.7-1
- 766895: Added hypervisorCheckIn call to allow sending a mapping of host/guest ids for
  creation/update. (mstead@redhat.com)

* Tue Dec 06 2011 William Poteat <wpoteat@redhat.com> 0.98.5-1
- 754366: workaround a bug in httpslib.ProxyHttpsConnection
  (alikins@redhat.com)

* Thu Nov 17 2011 William Poteat <wpoteat@redhat.com> 0.98.3-1
- 752854: Fixing error in iniparser around unpacking of a dictionary for
  default values. (awood@redhat.com)
- 708362: remove entitlement keys on delete as well (alikins@redhat.com)
- 734114: registering with --org="foo bar" throws a NetworkException instead of
  a RestlibException (awood@redhat.com)

* Fri Oct 28 2011 William Poteat <wpoteat@redhat.com> 0.98.2-1
- 749853: backport new python-rhsm API calls present in 6.2 for 5.8
  (cduryee@redhat.com)
- rev python-rhsm version to match sub-mgr (cduryee@redhat.com)
- point master to rhel5 builder (cduryee@redhat.com)
- fix python syntax for older versions (jbowes@redhat.com)
- Fix yum repo location for EL6. (dgoodwin@redhat.com)

* Mon Oct 17 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.97.1-1
- 746241: UEPConnection.updateConsumer now passes empty list in POST request
  (mstead@redhat.com)
- 737935: overcome 255 char limit in uuid list (cduryee@redhat.com)
* Tue Sep 13 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.12-1
- Add makefile and targets for coverage and "stylish" checks
  (alikins@redhat.com)
- Add tests for config parsing (cduryee@redhat.com)
- 736166: move certs from subscription-manager to python-rhsm
  (cduryee@redhat.com)

* Wed Sep 07 2011 James Bowes <jbowes@redhat.com> 0.96.11-1
- add future date bind (jesusr@redhat.com)
- 735226: allow Keys to validate themselves (bkearney@redhat.com)
- Add getVirtOnly() (cduryee@redhat.com)

* Wed Aug 24 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.10-1
- Submit a Content-Length when body of request is empty. (dgoodwin@redhat.com)
- Support installed products when registering. (dgoodwin@redhat.com)
- Add ability to update a consumer's installed products list.
  (dgoodwin@redhat.com)
- Support for new bind method (cduryee@redhat.com)

* Wed Aug 17 2011 James Bowes <jbowes@redhat.com> 0.96.9-1
- self.sanitize, and add support for quote_plus. (cduryee@redhat.com)
- Enhance the insecure mode to not do peer checks. (bkearney@redhat.com)
- Wrap urllib.quote in a helper method to cast int to str as needed.
  (cduryee@redhat.com)
- 728266: Unsubscribe from subscription manager GUI is broken
  (cduryee@redhat.com)
- Remove quantity for bind by product. (dgoodwin@redhat.com)
* Wed Aug 03 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.8-1
- 719378: Encode whitespace in urls (bkearney@redhat.com)
- Change package profile upload url. (dgoodwin@redhat.com)

* Wed Jul 13 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.7-1
- Logging cleanup. (dgoodwin@redhat.com)
- Remove unused add_ssl_certs method. (dgoodwin@redhat.com)
- Load supported resources when UEPConnection is instantiated.
  (dgoodwin@redhat.com)
- Send package profile. (dgoodwin@redhat.com)
- Allow testing if package profiles equal one another. (dgoodwin@redhat.com)
- Support creating package profile from a file descriptor.
  (dgoodwin@redhat.com)
- Allow the attributes to be None for username and password in consumer
  selction. (bkearney@redhat.com)
- Add a Package object. (dgoodwin@redhat.com)

* Wed Jul 06 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.6-1
- Add support for new Katello error responses. (dgoodwin@redhat.com)
- Log the response when there's an issue parsing error JSON.
  (dgoodwin@redhat.com)
- Add support for registration to Katello environments. (dgoodwin@redhat.com)
- Don't send an http body if we don't have one. (jbowes@redhat.com)
- Add call to list environments. (dgoodwin@redhat.com)
- Do not load CA certs if in insecure mode. (dgoodwin@redhat.com)
- Cache supported resources after establishing connection.
  (dgoodwin@redhat.com)

* Fri Jun 24 2011 Devan Goodwin <dgoodwin@redhat.com> 0.96.5-1
- Fix backward compatability with old use of getPoolsList.
  (dgoodwin@redhat.com)
- Remove one built in type issue. (bkearney@redhat.com)
- Removed unused Bundle class (alikins@redhat.com)
- quantity for subscription (wottop@dhcp231-152.rdu.redhat.com)
- Add the activation key call, and remove subscription tokens
  (bkearney@redhat.com)
- Improve the doco, referencing the candlepin site. (bkearney@redhat.com)
- Improve the defualt values for the config (bkearney@redhat.com)
- Fix bug with owner specification during registration. (dgoodwin@redhat.com)

* Wed Jun 08 2011 Bryan Kearney <bkearney@redhat.com> 0.96.4-1
- Adding profile module and updating spec (pkilambi@redhat.com)
- Added stacking Id to the certificate (wottop@dhcp231-152.rdu.redhat.com)
- Changed call to CP for owner list (wottop@dhcp231-152.rdu.redhat.com)
- added getOwners function for use with 'list --owners'
  (wottop@dhcp231-152.rdu.redhat.com)
- change (wottop@dhcp231-152.rdu.redhat.com)
- Added the owner entered in the cli to the post for register
  (wottop@dhcp231-152.rdu.redhat.com)
- altered pool query to use both owner and consumer
  (wottop@dhcp231-152.rdu.redhat.com)
- Added getOwner(consumerid) function (wottop@dhcp231-152.rdu.redhat.com)

* Wed May 11 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.3-1
- 700601: Don't set the Accept-Language if we don't have a valid locale
  (alikins@redhat.com)
- 692210: remove a non critical warning message that is spamming the logs
  (alikins@redhat.com)
- 691788: Fix bad check for missing order info. (dgoodwin@redhat.com)
- Add a version of get_datetime from M2Crypto since it isnt avail on RHEL 5.7
  (alikins@redhat.com)
- Use older strptime call format (cduryee@redhat.com)
- 683550: fix parsing empty cert extensions (jbowes@redhat.com)
- Add support for content tagging. (dgoodwin@redhat.com)
- Use tlsv1 instead of sslv3, for fips compliance (cduryee@redhat.com)

* Mon Feb 14 2011 Devan Goodwin <dgoodwin@rm-rf.ca> 0.96.2-1
- Setup configuration for Fedora git builds. (dgoodwin@rm-rf.ca)

* Fri Feb 04 2011 Devan Goodwin <dgoodwin@redhat.com> 0.96.1-1
- 674078: send a full iso 8601 timestamp for activeOn pools query
  (jbowes@repl.ca)

* Tue Feb 01 2011 Devan Goodwin <dgoodwin@redhat.com> 0.95.2-1
- Add content metadata expire to certificate class. (dgoodwin@redhat.com)

* Fri Jan 28 2011 Chris Duryee (beav) <cduryee@redhat.com>
- Add new extensions to order (jbowes@redhat.com)
- remove shebang from certificate.py for rpmlint (jbowes@redhat.com)
- Adding activateMachine to connection api. (jharris@redhat.com)
- 668814: break out 404 and 500s into a different error (cduryee@redhat.com)
- Initialized to use tito. (jbowes@redhat.com)
- bump version (jbowes@redhat.com)

* Wed Jan 12 2011 jesus m. rodriguez <jesusr@redhat.com> 0.94.13-1
- 667829: handle proxy config options being absent from rhsm.conf (alikins@redhat.com)

* Fri Jan 07 2011 Devan Goodwin <dgoodwin@redhat.com> 0.94.12-1
- Related: #668006
- Remove a missed translation. (dgoodwin@redhat.com)
- Fix logger warning messages. (dgoodwin@redhat.com)


* Tue Dec 21 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.10-1
- Related: #661863
- Add certificate parsing library. (dgoodwin@redhat.com)
- Fix build on F12/RHEL5 and earlier. (dgoodwin@redhat.com)

* Fri Dec 17 2010 jesus m. rodriguez <jesusr@redhat.com> 0.94.9-1
- add comment on how to generate source tarball (jesusr@redhat.com)

* Fri Dec 17 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.8-1
- Adding GPLv2 license file. (dgoodwin@redhat.com)

* Fri Dec 17 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.7-1
- Related: #661863
- Add buildrequires for python-setuptools.

* Thu Dec 16 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.4-1
- Add python-rhsm tito.props. (dgoodwin@redhat.com)

* Thu Dec 16 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.3-1
- Refactor logging. (dgoodwin@redhat.com)
- Add a small README. (dgoodwin@redhat.com)

* Tue Dec 14 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.2-1
- Remove I18N code. (dgoodwin@redhat.com)
- Spec cleanup. (dgoodwin@redhat.com)
- Cleaning out unused log parsing functions (jharris@redhat.com)
- More tolerant with no rhsm.conf in place. (dgoodwin@redhat.com)
- Switch to python-iniparse. (alikins@redhat.com)

* Fri Dec 10 2010 Devan Goodwin <dgoodwin@redhat.com> 0.94.1-1
- Initial package tagging.

