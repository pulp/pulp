%global contentdir /var/www

Summary: An embedded Python interpreter for the Apache HTTP Server
Name: mod_python
Version: 3.3.1
Release: 14%{?dist}.3
Source: http://www.apache.org/dist/httpd/modpython/%{name}-%{version}.tgz
Source1: python.conf
Patch1: mod_python-3.1.3-ldflags.patch
Patch2: mod_python-3.1.4-cflags.patch
Patch3: mod_python-3.3.1-buckets.patch

URL: http://www.modpython.org/
License: ASL 2.0
Group: System Environment/Daemons
BuildRequires: httpd-devel >= 2.0.40-6, python-devel
Requires: httpd-mmn = %(cat %{_includedir}/httpd/.mmn || echo missing)
Requires: httpd >= 2.0.40

%description
Mod_python is a module that embeds the Python language interpreter within
the server, allowing Apache handlers to be written in Python.

Mod_python brings together the versatility of Python and the power of
the Apache Web server for a considerable boost in flexibility and
performance over the traditional CGI approach.

%prep
%setup -q
%patch1 -p1 -b .ldflags
%patch2 -p1 -b .cflags
%patch3 -p1 -b .buckets

# Convert to utf-8
for file in CREDITS NEWS; do
    iconv -f ISO-8859-1 -t UTF-8 -o $file.new $file && \
    touch -r $file $file.new && \
    mv $file.new $file
done

%build
%configure --with-apxs=%{_sbindir}/apxs --with-max-locks=4
make %{?_smp_mflags} APXS_CFLAGS="-Wc,-fno-strict-aliasing"

%install
mkdir -p $RPM_BUILD_ROOT%{_libdir}/httpd/modules
make install DESTDIR=$RPM_BUILD_ROOT INSTALL="install -p"

# Install the config file
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d
install -p -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d/

# Install the manual.
mkdir -p $RPM_BUILD_ROOT%{contentdir}/manual/mod/mod_python
cp -a doc-html/* $RPM_BUILD_ROOT%{contentdir}/manual/mod/mod_python/

%files
%defattr(-,root,root,-)
%doc README NEWS CREDITS LICENSE NOTICE
%{contentdir}/manual/mod/mod_python
%{_libdir}/httpd/modules/mod_python.so
%config(noreplace) %{_sysconfdir}/httpd/conf.d/*.conf
%{python_sitearch}/mod_python*

%changelog
* Wed Jun 08 2011 John Matthews <jmatthew@redhat.com> 3.3.1-14.3
- 

* Tue Jun 07 2011 John Matthews <jmatthews@redhat.com> 3.3.1-14.2
- new package built with tito

* Sat Dec 4 2010 Lubomir Rintel <lkundrak@v3.sk> - 3.3.1-14.1
- Drop the pycapsule patch for el6

* Tue Nov 2 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 3.3.1-14
- Apply patch to fix the PyCObject/PyCapsule crash:
  https://bugzilla.redhat.com/show_bug.cgi?id=640432
- Add dist tag (also mentioned in 640432)

* Mon Sep 06 2010 Parag Nemade <paragn AT fedoraproject.org> - 3.3.1-13
- Merge Review cleanup (#226156)

* Wed Jul 21 2010 David Malcolm <dmalcolm@redhat.com> - 3.3.1-12
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.3.1-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.3.1-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 3.3.1-9
- Rebuild for Python 2.6

* Tue Oct  7 2008 Joe Orton <jorton@redhat.com> 3.3.1-8
- fix build failure, thanks to Tomo Vuckovic (#465246)

* Tue Feb 19 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 3.3.1-7
- Autorebuild for GCC 4.3

* Fri Jan  4 2008 Joe Orton <jorton@redhat.com> 3.3.1-6
- fix rebuild failure due to new egg-info directory

* Sun Sep  2 2007 Joe Orton <jorton@redhat.com> 3.3.1-5
- rebuild for fixed 32-bit APR

* Tue Aug 21 2007 Joe Orton <jorton@redhat.com> 3.3.1-4
- fix License

* Mon Feb 19 2007 Jeremy Katz <katzj@redhat.com> - 3.3.1-3
- don't use legacy python-abi requires syntax

* Fri Feb 16 2007 Joe Orton <jorton@redhat.com> 3.3.1-2
- update to 3.3.1
- fix BuildRoot, Summary, drop BR for autoconf

* Thu Dec  7 2006 Jeremy Katz <katzj@redhat.com> - 3.2.10-4
- rebuild against python 2.5

* Tue Nov 21 2006 Joe Orton <jorton@redhat.com> 3.2.10-3
- update to 3.2.10

* Wed Jul 12 2006 Jesse Keating <jkeating@redhat.com>
- rebuild

* Mon Feb 27 2006 Joe Orton <jorton@redhat.com> 3.2.8-3
- remove use of apr_sockaddr_port_get

* Mon Feb 27 2006 Joe Orton <jorton@redhat.com> 3.2.8-2
- update to 3.2.8

* Mon Feb 13 2006 Joe Orton <jorton@redhat.com> 3.1.4-4
- fix configure syntax error with bash 3.1 (#180731)

* Fri Feb 10 2006 Jesse Keating <jkeating@redhat.com> - 3.1.4-3.2.1
- bump again for double-long bug on ppc(64)

* Tue Feb 07 2006 Jesse Keating <jkeating@redhat.com> - 3.1.4-3.2
- rebuilt for new gcc4.1 snapshot and glibc changes

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Fri Dec  2 2005 Joe Orton <jorton@redhat.com> 3.1.4-3
- rebuild for httpd 2.2
- build with -fno-strict-aliasing
- don't use deprecated APR_STATUS_IS_SUCCESS() macro

* Fri Mar  4 2005 Joe Orton <jorton@redhat.com> 3.1.4-2
- rebuild

* Thu Feb 10 2005 Joe Orton <jorton@redhat.com> 3.1.4-1
- update to 3.1.4

* Tue Feb  1 2005 Joe Orton <jorton@redhat.com> 3.1.3-8
- link against shared libpython (#129019)
- add python.conf comment on using PSP (#121212)

* Thu Nov 18 2004 Joe Orton <jorton@redhat.com> 3.1.3-7
- require python-abi

* Thu Nov 18 2004 Joe Orton <jorton@redhat.com> 3.1.3-6
- rebuild for Python 2.4

* Tue Oct 12 2004 Joe Orton <jorton@redhat.com> 3.1.3-5
- include LICENSE and NOTICE

* Tue Oct 12 2004 Joe Orton <jorton@redhat.com> 3.1.3-4
- use a maximum of four semaphores by default

* Tue Jul 13 2004 Nils Philippsen <nphilipp@redhat.com>
- set default-handler for manual files to fix #127622

* Tue Jun 15 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Mon Mar  8 2004 Mihai Ibanescu <misa@redhat.com> 3.1.3-0.1
- upgrade to 3.1.3

* Tue Mar 02 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Fri Feb 13 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Tue Feb  3 2004 Gary Benson <gbenson@redhat.com> 3.0.4-1
- upgrade to 3.0.4 (fixes CVE CAN-2003-0973)

* Fri Nov  7 2003 Joe Orton <jorton@redhat.com> 3.0.3-4
- rebuild for python 2.3.2

* Thu Jul  3 2003 Gary Benson <gbenson@redhat.com> 3.0.3-3
- fix license (#98245)

* Wed Jun 04 2003 Elliot Lee <sopwith@redhat.com> 3.0.3-2
- rebuilt

* Tue May 13 2003 Gary Benson <gbenson@redhat.com> 3.0.3-1
- upgrade to 3.0.3.

* Thu Feb 20 2003 Gary Benson <gbenson@redhat.com> 3.0.1-3
- call PyOS_AfterFork() after forking (#84610)

* Wed Jan 22 2003 Tim Powers <timp@redhat.com> 3.0.1-2
- rebuilt

* Mon Dec  9 2002 Gary Benson <gbenson@redhat.com> 3.0.1-1
- upgrade to 3.0.1.

* Mon Nov 18 2002 Gary Benson <gbenson@redhat.com> 3.0.0-12
- upgrade to beta4.

* Wed Nov  6 2002 Gary Benson <gbenson@redhat.com> 3.0.0-11
- install libraries in lib64 when pertinent.

* Fri Sep 13 2002 Gary Benson <gbenson@redhat.com>
- add a filter example to /etc/httpd/conf.d/python.conf

* Wed Sep 11 2002 Gary Benson <gbenson@redhat.com>
- undisable filters (#73825)
- fix filter lookup breakage

* Mon Sep  2 2002 Joe Orton <jorton@redhat.com> 3.0.0-10
- require httpd-mmn for module ABI compatibility

* Tue Aug 28 2002 Gary Benson <gbenson@redhat.com> 3.0.0-9
- remove empty files from the generated manual

* Fri Aug 23 2002 Gary Benson <gbenson@redhat.com> 3.0.0-8
- add built manual to snapshot tarball and install it (#69361)
- add some examples to /etc/httpd/conf.d/python.conf (#71316)

* Mon Aug 12 2002 Gary Benson <gbenson@redhat.com> 3.0.0-7
- rebuild against httpd-2.0.40

* Mon Jul 22 2002 Gary Benson <gbenson@redhat.com> 3.0.0-6
- upgrade to latest CVS

* Tue Jul  9 2002 Gary Benson <gbenson@redhat.com> 3.0.0-5
- bring input filter API in line with 2.0.36 (#66566)

* Wed Jun 26 2002 Gary Benson <gbenson@redhat.com> 3.0.0-4
- upgrade to latest CVS

* Fri Jun 21 2002 Gary Benson <gbenson@redhat.com>
- move /etc/httpd2 back to /etc/httpd

* Fri Jun 21 2002 Tim Powers <timp@redhat.com> 3.0.0-3
- automated rebuild

* Mon Jun 10 2002 Gary Benson <gbenson@redhat.com> 3.0.0-2
- drop the CVS date from the release

* Mon Jun 10 2002 Gary Benson <gbenson@redhat.com> 3.0.0-1.20020610
- upgrade to latest CVS

* Mon May 27 2002 Gary Benson <gbenson@redhat.com> 3.0.0-1.20020527
- upgrade to latest CVS and change paths for httpd-2.0
- make it build with 2.0.36
- add the config file.

* Fri May 17 2002 Nalin Dahyabhai <nalin@redhat.com> 2.7.8-2
- rebuild in new environment

* Mon Apr 22 2002 Nalin Dahyabhai <nalin@redhat.com> 2.7.8-1
- update for RHSA-2002:070

* Thu Feb 28 2002 Nalin Dahyabhai <nalin@redhat.com> 2.7.6-5
- add patch for cleanups (#57232)

* Fri Feb 22 2002 Nalin Dahyabhai <nalin@redhat.com> 2.7.6-4
- rebuild with python 1.5

* Wed Jan 09 2002 Tim Powers <timp@redhat.com>
- automated rebuild

* Fri Jan 04 2002 Florian La Roche <Florian.LaRoche@redhat.de>
- change for python 2.2

* Thu Aug  9 2001 Nalin Dahyabhai <nalin@redhat.com>
- update to 2.7.6

* Mon Jun 25 2001 Nalin Dahyabhai <nalin@redhat.com>
- update to 2.7.5
- add URL
- move docs so that they live under %%{contentdir}

* Thu May 31 2001 Nalin Dahyabhai <nalin@redhat.com>
- update to 2.7.3

* Tue Jan 16 2001 Cristian Gafton <gafton@redhat.com>
- fix module compilation paths
- build first package for RHN
