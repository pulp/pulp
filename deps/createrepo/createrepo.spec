%{!?python_sitelib: %define python_sitelib %(python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Creates a common metadata repository
Name: createrepo
Version: 0.9.8
Release: 4%{?dist}
License: GPLv2
Group: System Environment/Base
Source: %{name}-%{version}.tar.gz
Patch0: ten-changelog-limit.patch
Patch1: createrepo-drpm.patch
Patch2: createrepo-fixdrpm.patch
URL: http://createrepo.baseurl.org/
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArchitectures: noarch
Requires: python >= 2.1, rpm-python, rpm >= 4.1.1, libxml2-python
Requires: yum-metadata-parser, yum >= 3.2.22-20, python-deltarpm, deltarpm
BuildRequires: python

%description
This utility will generate a common metadata repository from a directory of rpm
packages.

%prep
%setup -q
%patch0 -p0
%patch1 -p1
%patch2 -p1

%build

%install
rm -rf $RPM_BUILD_ROOT
make DESTDIR=$RPM_BUILD_ROOT install

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-, root, root,-)
%doc ChangeLog README COPYING
%{_datadir}/%{name}/
%{_bindir}/createrepo
%{_bindir}/modifyrepo
%{_bindir}/mergerepo
%{_mandir}/*/*
%{python_sitelib}/createrepo

%changelog
* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.9.8-4
- Renamed dependency RPMs (jason.dobies@redhat.com)

* Thu Jun 16 2011 Pradeep Kilambi <pkilambi@redhat.com> 0.9.8-3
- new package built with tito

* Mon Jan  3 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.8-3
- add another drpm patch to fix up drpms being passed to wrong process :(

* Thu Sep  3 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.8-2
- add drpm patch from https://bugzilla.redhat.com/show_bug.cgi?id=518658


* Fri Aug 28 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.8-1
- bump yum requires version
- remove head patch
- bump to 0.9.8 upstream

* Tue Aug 18 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.7-15
- update HEAD patch to include fix from mbonnet for typo'd PRAGMA in the filelists setup

* Tue Aug  4 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.7-14
- minor fix for rh bug 512610

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.7-13
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Jun 17 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.7-11
- more profile output for deltarpms

* Tue Jun 16 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.7-8
- more patches from head
- speed up generating prestodelta, massively

* Tue May  5 2009 Seth Vidal <skvidal at fedoraproject.org>
- more head fixes - theoretically solving ALL of the sha1/sha silliness

* Wed Apr 15 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.7-2
- fix 495845 and other presto issues

* Tue Mar 24 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.7-1
- 0.9.7
- require yum 3.2.22

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.6-12
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Tue Feb 10 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.6-11
- change the order of deltarpms

* Wed Feb  4 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.6-10
- working mergerepo again

* Tue Feb  3 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.6-9
- fix normal createrepo'ing w/o the presto patches :(

* Mon Feb  2 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.6-7
- add deltarpm requirement for making presto metadata

* Tue Jan 27 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.6-6
- one more patch set to make sure modifyrepo works with sha256's, too

* Mon Jan 26 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.6-5
- add patch from upstream head for sha256 support

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 0.9.6-4
- Rebuild for Python 2.6

* Tue Oct 28 2008 Seth Vidal <skvidal at fedoraproject.org> - 0.9.6-1
- 0.9.6-1
- add mergerepo

* Thu Oct  9 2008 James Antill <james@fedoraproject.org> - 0.9.5-5
- Do atomic updates to the cachedir, for parallel runs
- Fix the patch

* Fri Feb 22 2008 Seth Vidal <skvidal at fedoraproject.org> - 0.9.5-2
- patch for the mistake in the raise for an empty pkgid

* Tue Feb 19 2008 Seth Vidal <skvidal at fedoraproject.org> - 0.9.5-1
- 0.9.5
- ten-changelog-limit patch by default in fedora

* Thu Jan 31 2008 Seth Vidal <skvidal at fedoraproject.org> - 0.9.4-3
- skip if no old metadata and --update was called.

* Wed Jan 30 2008 Seth Vidal <skvidal at fedoraproject.org> - 0.9.4-1
- 0.9.4

* Tue Jan 22 2008 Seth Vidal <skvidal at fedoraproject.org> - 0.9.3
- 0.9.3

* Thu Jan 17 2008 Seth Vidal <skvidal at fedoraproject.org> - 0.9.2-1
- remove all other patches - 0.9.2 

* Tue Jan 15 2008 Seth Vidal <skvidal at fedoraproject.org> 0.9.1-3
- more patches - almost 0.9.2 but not quite

* Thu Jan 10 2008 Seth Vidal <skvidal at fedoraproject.org> 0.9.1-2
- patch to fix bug until 0.9.2

* Wed Jan  9 2008 Seth Vidal <skvidal at fedoraproject.org> 0.9.1-1
- 0.9.1 

* Mon Jan  7 2008 Seth Vidal <skvidal at fedoraproject.org> 0.9-1
- 0.9
- add yum dep


* Mon Nov 26 2007 Luke Macken <lmacken@redhat.com> - 0.4.11-1
- Update to 0.4.11
- Include COPYING file and change License to GPLv2

* Thu Jun 07 2007 Paul Nasrat <pnasrat@redhat.com> - 0.4.10-1
- Update to 0.4.10

* Wed May 16 2007 Paul Nasrat <pnasrat@redhat.com> - 0.4.9-1
- Update to 0.4.9

* Tue May 15 2007 Jeremy Katz <katzj@redhat.com> - 0.4.8-4
- fix the last patch

* Tue May 15 2007 Jeremy Katz <katzj@redhat.com> - 0.4.8-3
- use dbversion given by yum-metadata-parser instead of hardcoded 
  value (#239938)

* Wed Mar 14 2007 Paul Nasrat <pnasrat@redhat.com> - 0.4.8-2
- Remove requires (#227680)

* Wed Feb 21 2007 Jeremy Katz <katzj@redhat.com> - 0.4.8-1
- update to 0.4.8

* Mon Feb 12 2007 Jesse Keating <jkeating@redhat.com> - 0.4.7-3
- Require yum-metadata-parser.

* Thu Feb  8 2007 Jeremy Katz <katzj@redhat.com> - 0.4.7-2
- add modifyrepo to the file list

* Thu Feb  8 2007 Jeremy Katz <katzj@redhat.com> - 0.4.7-1
- update to 0.4.7

* Mon Feb 05 2007 Paul Nasrat <pnasrat@redhat.com> - 0.4.6-2
- Packaging guidelines (#225661)

* Thu Nov 09 2006 Paul Nasrat <pnasrat@redhat.com> - 0.4.6-1
- Upgrade to latest release
- Fix requires (#214388)

* Wed Jul 19 2006 Paul Nasrat <pnasrat@redhat.com> - 0.4.4-2
- Fixup relative paths (#199228)

* Wed Jul 12 2006 Jesse Keating <jkeating@redhat.com> - 0.4.4-1.1
- rebuild

* Mon Apr 17 2006 Paul Nasrat <pnasrat@redhat.com> - 0.4.4-1
- Update to latest upstream

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Fri Nov 18 2005 Paul Nasrat <pnasrat@redhat.com> - 0.4.3-5
- Fix split with normalised directories

* Fri Nov 18 2005 Paul Nasrat <pnasrat@redhat.com> - 0.4.3-4
- Another typo fix
- Normalise directories

* Thu Nov 17 2005 Paul Nasrat <pnasrat@redhat.com> - 0.4.3-3.1
- really fix them 

* Thu Nov 17 2005 Paul Nasrat <pnasrat@redhat.com> - 0.4.3-3
- Fix regressions for absolute/relative paths

* Sun Nov 13 2005 Paul Nasrat <pnasrat@redhat.com> - 0.4.3-2
- Sync upto HEAD 
- Split media support

* Thu Jul 14 2005 Paul Nasrat <pnasrat@redhat.com> - 0.4.3-1
- New upstream version 0.4.3 (cachedir support)

* Tue Jan 18 2005 Jeremy Katz <katzj@redhat.com> - 0.4.2-2
- add the manpage

* Tue Jan 18 2005 Jeremy Katz <katzj@redhat.com> - 0.4.2-1
- 0.4.2

* Thu Oct 21 2004 Paul Nasrat <pnasrat@redhat.com>
- 0.4.1, fixes #136613
- matched ghosts not being added into primary.xml files

* Mon Oct 18 2004 Bill Nottingham <notting@redhat.com>
- 0.4.0, fixes #134776

* Thu Sep 30 2004 Paul Nasrat <pnasrat@redhat.com>
- Rebuild new upstream release - 0.3.9

* Thu Sep 30 2004 Seth Vidal <skvidal@phy.duke.edu>
- 0.3.9
- fix for groups checksum creation

* Sat Sep 11 2004 Seth Vidal <skvidal@phy.duke.edu>
- 0.3.8

* Wed Sep  1 2004 Seth Vidal <skvidal@phy.duke.edu>
- 0.3.7

* Fri Jul 23 2004 Seth Vidal <skvidal@phy.duke.edu>
- make filelists right <sigh>


* Fri Jul 23 2004 Seth Vidal <skvidal@phy.duke.edu>
- fix for broken filelists

* Mon Jul 19 2004 Seth Vidal <skvidal@phy.duke.edu>
- re-enable groups
- update num to 0.3.4

* Tue Jun  8 2004 Seth Vidal <skvidal@phy.duke.edu>
- update to the format
- versioned deps
- package counts
- uncompressed checksum in repomd.xml


* Fri Apr 16 2004 Seth Vidal <skvidal@phy.duke.edu>
- 0.3.2 - small addition of -p flag

* Sun Jan 18 2004 Seth Vidal <skvidal@phy.duke.edu>
- I'm an idiot

* Sun Jan 18 2004 Seth Vidal <skvidal@phy.duke.edu>
- 0.3

* Tue Jan 13 2004 Seth Vidal <skvidal@phy.duke.edu>
- 0.2 - 

* Sat Jan 10 2004 Seth Vidal <skvidal@phy.duke.edu>
- first packaging

