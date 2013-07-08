%{!?python_sitelib: %define python_sitelib %(python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%if ! 0%{?rhel}
# we don't have this in rhel yet...
BuildRequires: bash-completion
%endif

# disable broken /usr/lib/rpm/brp-python-bytecompile
%define __os_install_post %{nil}
%define compdir %(pkg-config --variable=completionsdir bash-completion)
%if "%{compdir}" == ""
%define compdir "/etc/bash_completion.d"
%endif

Summary: Creates a common metadata repository
Name: createrepo
Version: 0.9.9
Release: 21.2.pulp%{?dist}
License: GPLv2
Group: System Environment/Base
Source: %{name}-%{version}.tar.gz
Patch0: createrepo-head.patch
Patch1: ten-changelog-limit.patch
URL: http://createrepo.baseurl.org/
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArchitectures: noarch
Requires: python >= 2.1, rpm-python, rpm >= 4.1.1, libxml2-python
Requires: yum-metadata-parser, yum >= 3.2.29-40, python-deltarpm, deltarpm, pyliblzma
BuildRequires: python

%description
This utility will generate a common metadata repository from a directory of rpm
packages.

%prep
%setup -q
%patch0 -p1
%patch1 -p0

%build

%install
rm -rf $RPM_BUILD_ROOT
make DESTDIR=$RPM_BUILD_ROOT sysconfdir=%{_sysconfdir} install

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-, root, root,-)
%doc ChangeLog README COPYING COPYING.lib
%(dirname %{compdir})
%{_datadir}/%{name}/
%{_bindir}/createrepo
%{_bindir}/modifyrepo
%{_bindir}/mergerepo
%{_mandir}/*/*
%{python_sitelib}/createrepo

%changelog
* Mon Jul 08 2013 Jeff Ortel <jortel@redhat.com> 0.9.9-21.2.pulp
- correct a typo in the changelog. (jortel@redhat.com)

* Mon Jul 08 2013 Jeff Ortel <jortel@redhat.com> 0.9.9-21.1.pulp
- 976568, 981676 - verified compat with version of yum included in RHEL 6.4;
  downgrading dependency. (jortel@redhat.com)

* Wed May 29 2013 Jeff Ortel <jortel@redhat.com> 0.9.9-21
- 968535 - rebase using version f18/f19 version; includes fix for bz:950724.
  (jortel@redhat.com)

* Tue May 14 2013 Zdenek Pavlas <zpavlas@redhat.com> - 0.9.9-21
- update to latest HEAD
- don't BuildRequire bash-completion in rhel
- Fail for bad compress-type options to modifyrepo, like createrepo. BZ 886589
- Fix options documentation. BZ 892657.
- modifyrepo: fix --compress option bug. BZ 950724
- modifyrepo: add --checksum and --{unique,simple}-md-filenames options

* Thu Mar 28 2013 Zdenek Pavlas <zpavlas@redhat.com> - 0.9.9-20
- package also %{compdir}'s parent

* Wed Mar 20 2013 Zdenek Pavlas <zpavlas@redhat.com> - 0.9.9-19
- add BuildRequires: bash-completion

* Wed Mar 20 2013 Zdenek Pavlas <zpavlas@redhat.com> - 0.9.9-18
- add bash-completion aliases, use pkg-config.

* Tue Mar 19 2013 Zdenek Pavlas <zpavlas@redhat.com> - 0.9.9-17
- move bash-completion scripts to /usr/share/  BZ 923001

* Wed Mar  6 2013 Zdenek Pavlas <zpavlas at redhat.com> - 0.9.9-16
- update to latest HEAD
- turn off stdout buffering in worker to prevent a deadlock
- modifyrepo: use integer timestamps

* Wed Feb 13 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.9-15
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Fri Dec 21 2012 Zdenek Pavlas <zpavlas at redhat.com> - 0.9.9-14
- update to latest HEAD
- Fix the deadlock issue.  BZ 856363
- Manually set the permmissions for tempfile created cachefiles. BZ 833350
- modifyrepo: use available compression only.  BZ 865845
- No baseurl means no baseurl.  BZ 875029
- Change the compress-type for modifyrepo to .gz for compat. BZ 874682.
- fix the --skip-symlinks option
- no repomd.xml && --checkts: skip .rpm timestamp checking.  BZ 877301
- new worker piping code (no tempfiles, should be faster)

* Thu Sep 13 2012 James Antill <james at fedoraproject.org> - 0.9.9-13
- update to latest head
- Fix for workers that output a lot.

* Wed Jul 18 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.9-12
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Thu Feb 16 2012 James Antill <james at fedoraproject.org> - 0.9.9-11
- update to latest head
- fix for lots of workers and not many rpms.

* Thu Jan  5 2012 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-10
- update to latest head
- fix for generating repos for rhel5 on fedora

* Fri Oct 28 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-9
- 3rd time is the charm
- fix it so prestodelta's get made with the right name and don't traceback

* Wed Oct 26 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-8
- change how compressOpen() defaults so mash doesn't break
- add requires for pyliblzma

* Mon Oct 24 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-7
- latest upstream
- --compress-type among other deals.

* Fri Jul 29 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-6
- latest upstream
- fixes bugs: 713747, 581632, 581628

* Wed Jul 20 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-5
- new patch to fix us breaking certain pungi configs

* Tue Jul 19 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-4
- latest upstream head
- change --update to use sqlite for old repodata

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.9-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Thu Jan 27 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-2
- make sure when a worker exits with a non-zero returncode we exit, too.

* Wed Jan 26 2011 Seth Vidal <skvidal at fedoraproject.org> - 0.9.9-1
- 0.9.9
- change yum requires to 3.2.29

* Wed Jul 21 2010 David Malcolm <dmalcolm@redhat.com> - 0.9.8-5
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Thu Jan  7 2010 Seth Vidal <skvidal at fedoraproject.org> - 0.9.8-4
- latest head with fixes for --update w/o --skipstat


* Tue Dec 22 2009 Seth Vidal <skvidal at fedoraproject.org> - 0.9.8-3
- patch to latest HEAD from upstream

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

