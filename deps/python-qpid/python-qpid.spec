%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_version: %global python_version %(%{__python} -c "from distutils.sysconfig import get_python_version; print get_python_version()")}

Name:           python-qpid
Version:        0.7.946106
Release:        2%{?dist}
Summary:        Python client library for AMQP

Group:          Development/Python
License:        ASL 2.0
URL:            http://qpid.apache.org
Source0:        %{name}-%{version}.tar.gz
# svn export -r<rev> http://svn.apache.org/repos/asf/qpid/trunk/qpid/python python-qpid-0.7.<rev>
# tar czf python-qpid-0.7.<rev>.tar.gz python-qpid-0.7.<rev>

Patch0:         0001-BZ-597066.patch
Patch1:         0002-Bug-538188-Fixed-connection.start-hangs-if-connectio.patch
Patch2:         0003-Bug-597149-Fixed-qpid-python-high-level-API-clients-.patch
Patch3:         0004-BZ-567249-added-back-values-method-for-backwards-com.patch
Patch4:         0005-BZ-567249-fix-for-python-2.3.patch
Patch5:         0006-BZ-596677-performance-tweaks-for-receive-added-confi.patch
Patch6:         0007-BZ-574817-don-t-always-set-the-sync-bit-on-send.patch
Patch7:         0008-BZ-604836-reset-reconnect-delay-after-successful-con.patch
Patch8:         0009-BZ-560707-added-full-support-for-unreliable-at-least.patch
Patch9:         0010-BZ-569515-added-optional-timeouts-to-connection-sess.patch
Patch10:        0011-BZ-608118-added-support-for-x-amqp-0-10.-app-id-cont.patch
Patch11:        0012-BZ-608118-make-sure-we-initialize-properties-even-if.patch
Patch12:        0013-BZ-569515-fix-timeout-tests-to-not-leave-queues-lyin.patch
Patch13:        0014-BZ-607798-add-uuid-prefix-to-addresses-beginning-wit.patch
Patch14:        0015-BZ-607798-fix-mangling-for-addresses-that-are-None.patch
Patch15:        0016-BZ-608807-fixed-concurrent-close.patch
Patch16:        0017-BZ-609258-added-accessor-for-auth_username.patch
Patch17:        0018-BZ-609258-fixed-auth-username-for-sasl.patch
Patch18:        0019-Bug-611543-Assertion-when-raising-a-link-established.patch
Patch19:        0020-BZ-612615-convert-ttl-from-seconds-to-milliseconds.patch
Patch20:        0021-BZ-613216-fixed-payload-of-None-for-text-plain-messa.patch
Patch21:        0022-removed-old-python-examples.patch
Patch22:        0023-BZ-613912-fixed-missign-import-and-added-test-case-f.patch
Patch23:        0024-BZ-614054-eliminate-spurious-error-logging-and-recon.patch
Patch24:        0025-BZ-614054-fixed-parsing-of-failover-URLs-fixed-drive.patch
Patch25:        0026-BZ-614344-default-ports-for-reconnect_urls.patch

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

BuildRequires:  python-devel

%description
The Apache Qpid Python client library for AMQP.

%prep
%setup -q
%patch0 -p3
%patch1 -p3
%patch2 -p3
%patch3 -p3
%patch4 -p3
%patch5 -p3
%patch6 -p3
%patch7 -p3
%patch8 -p3
%patch9 -p3
%patch10 -p3
%patch11 -p3
%patch12 -p3
%patch13 -p3
%patch14 -p3
%patch15 -p3
%patch16 -p3
%patch17 -p3
%patch18 -p3
%patch19 -p3
%patch20 -p3
%patch21 -p3
%patch22 -p3
%patch23 -p3
%patch24 -p3
%patch25 -p3

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{python_sitelib}/mllib
%{python_sitelib}/qpid
%{_bindir}/qpid-python-test
%doc LICENSE.txt NOTICE.txt README.txt examples/

%if "%{python_version}" >= "2.6"
%{python_sitelib}/qpid_python-*.egg-info
%endif

%changelog
* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.7.946106-2
- Renamed dependency RPMs (jason.dobies@redhat.com)

* Thu Jul 22 2010 Mike McCune <mmccune@redhat.com> 0.7.946106-1
- switching to orig (mmccune@redhat.com)

* Wed Jul 14 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-9
- Fix for bz614344

* Wed Jul 14 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-8
- Related to bz614054

* Tue Jul 13 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-7
- Related: bz614132

* Mon Jul 12 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-6
- Resolves: bz613647

* Fri Jul  9 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-5
- Related: bz612632

* Wed Jun 30 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-4
- Related: bz608807

* Mon Jun 28 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-3
- Patches for: BZ-560707 BZ-569515 BZ-608118 BZ-607798

* Thu Jun 17 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.946106-2
- Patches for: BZ-597066 BZ-538188 BZ-597149 BZ-567249 BZ-567249
-   BZ-596677 BZ-574817 BZ-604836

* Wed May 19 2010 Nuno Santos <nsantos@redhat.com> - 0.7.946106-1
- Rebased to svn rev 949106
- Related: rhbz574881

* Mon Apr 19 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.934605-1
- Rebased to svn rev 934605.

* Thu Apr  1 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.930108-1
- Rebased to svn rev 930108.

* Wed Mar  3 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.917557-4
- Changed defines to globals and moved to top.
- Removed unnecessary python Requires/BuildRequires.

* Mon Mar  1 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.917557-3
- Conditionalize egg-info on python version.

* Mon Mar  1 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.917557-2
- Removed unused amqp_spec_dir define.

* Mon Mar  1 2010 Rafael Schloming <rafaels@redhat.com> - 0.7.917557-1
- Rebased to svn rev 917557.

* Fri Jan 29 2010 Rafael Schloming <rafaels@redhat.com> - 0.5.904641-1
- Rebased to svn rev 904641 and use supplied Makefile for install

* Tue Sep 29 2009 Nuno Santos <nsantos@redhat.com> - 0.5.819819-1
- Rebased to svn rev 819819 for Fedora 12 beta

* Fri Sep 25 2009 Nuno Santos <nsantos@redhat.com> - 0.5.818599-1
- Rebased to svn rev 818599

* Fri Sep 18 2009 Nuno Santos <nsantos@redhat.com> - 0.5.816781-1
- Rebased to svn rev 816781

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.5.790661-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Jul  2 2009 Nuno Santos <nsantos@redhat.com> - 0.5.790661-1
- Rebased to svn rev 790661

* Fri Jun 26 2009 Nuno Santos <nsantos@redhat.com> - 0.5.788782-1
- Rebased to svn rev 788782

* Mon Jun 22 2009 Nuno Santos <nsantos@redhat.com> - 0.5.787286-1
- Rebased to svn rev 787286

* Thu Mar 19 2009 Nuno Santos <nsantos@redhat.com> - 0.5.752600-1
- Rebased to svn rev 752600

* Thu Feb 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.4.738618-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Wed Jan 28 2009 Nuno Santos <nsantos@redhat.com> - 0.4.738618-1
- Rebased to svn rev 738618

* Wed Jan 14 2009 Nuno Santos <nsantos@redhat.com> - 0.4.734452-1
- Rebased to svn rev 734452
- BZ 478467: include examples

* Thu Jan  8 2009 Nuno Santos <nsantos@redhat.com> - 0.4.728142-3
- BZ 479212: add qmf dirs

* Tue Dec 23 2008 Nuno Santos <nsantos@redhat.com> - 0.4.728142-1
- Rebased to svn rev 728142

* Thu Dec 04 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 0.3.722557-2
- Rebuild for Python 2.6

* Tue Dec  2 2008 Nuno Santos <nsantos@redhat.com> - 0.3.722557-1
- Rebased to svn rev 722557

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 0.3.720585-2
- Rebuild for Python 2.6

* Tue Nov 25 2008 Nuno Santos <nsantos@redhat.com> - 0.3.720585-1
- Rebased to svn rev 720585

* Tue Nov 18 2008 Nuno Santos <nsantos@redhat.com> - 0.3.718718-1
- Rebased to svn rev 718718

* Thu Oct 16 2008 Nuno Santos <nsantos@redhat.com> - 0.3.705289-1
- Rebased to svn rev 705289

* Thu Oct  2 2008 Nuno Santos <nsantos@redhat.com> - 0.3.700546-1
- Rebased to svn revision 700546

* Mon Sep  8 2008 Nuno Santos <nsantos@redhat.com> - 0.3.693140-1
- Update for Fedora 10

* Wed Sep  3 2008 Tom "spot" Callaway <tcallawa@redhat.com> - 0.2.668378-2
- fix license tag

* Mon Jun 16 2008 Rafael Schloming <rafaels@redhat.com> - 0.2.668378-1
- Source update for MRG RC1

* Mon Jun 16 2008 Rafael Schloming <rafaels@redhat.com> - 0.2.668345-1
- Source update for MRG RC1

* Tue Jun 10 2008 Rafael Schloming <rafaels@redhat.com> - 0.2.666398-12
- Source update for MRG RC1

* Mon Jun  9 2008 Rafael Schloming <rafaels@redhat.com> - 0.2.665776-12
- Source update for MRG RC1

* Fri May 16 2008 Rafael Schloming <rafaels@redhat.com> - 0.2.657115-12
- Imported new source tarball for MRG Beta 4

* Tue May 13 2008 Rafael Schloming <rafaels@redhat.com> - 0.2.656025-12
- Updated the amqp dependency

* Mon May 12 2008 Rafael Schloming <rafaels@redhat.com> - 0.2-11
- Install the scripts from the commands directory, update the source
  tarball, and include the svn revision number in the version.

* Mon May 12 2008 Rafael Schloming <rafaels@redhat.com> - 0.2-10
- Updated the source tarball for MRG Beta 4

* Mon Feb 11 2008  <rafaels@redhat.com> - 0.2-9
- bumped for Beta 3

* Thu Jan 24 2008 Nuno Santos <nsantos@redhat.com> - 0.1-8
- Move test script to /usr/bin

* Thu Jan 24 2008 Nuno Santos <nsantos@redhat.com> - 0.1-7
- Testrunner fixes

* Thu Jan 24 2008 Nuno Santos <nsantos@redhat.com> - 0.1-6
- Include generic tests

* Wed Jan 23 2008 Nuno Santos <nsantos@redhat.com> - 0.1-5
- Include tests for AMQP 0-10

* Mon Jan 21 2008 Gordon Sim <gsim@redhat.com> - 0.1-3
- Bumped revision

* Thu Mar 22 2007 Rafael Schloming <rafaels@redhat.com> - 0.1-1
- Initial build.
- Comply with Fedora packaging guidelines
