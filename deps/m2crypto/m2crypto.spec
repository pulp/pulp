%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif


# Keep this value in sync with the definition in openssl.spec.
%global multilib_arches %{ix86} ia64 ppc ppc64 s390 s390x x86_64 sparc sparcv9 sparc64

Summary: Support for using OpenSSL in python scripts
Name: m2crypto
Version: 0.21.1.pulp
Release: 7%{?dist}
Source0: http://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-%{version}.tar.gz
# https://bugzilla.osafoundation.org/show_bug.cgi?id=2341
Patch0: m2crypto-0.21.1-timeouts.patch

# This is only precautionary, it does fix anything - not sent upstream
Patch1: m2crypto-0.21.1-gcc_macros.patch
# https://bugzilla.osafoundation.org/show_bug.cgi?id=12972
Patch2: m2crypto-0.20.2-fips.patch
# https://bugzilla.osafoundation.org/show_bug.cgi?id=12973
Patch3: m2crypto-0.20.2-check.patch
# https://bugzilla.osafoundation.org/show_bug.cgi?id=13005
# https://bugzilla.redhat.com/show_bug.cgi?id=739555
# We saw issues with the timeouts.patch in el6
#Patch4: m2crypto-0.21.1-memoryview.patch

# https://bugzilla.osafoundation.org/show_bug.cgi?id=13020
Patch4: m2crypto-0.21.1-smime-doc.patch
# ISSUE Link to be filed
Patch5: m2crypto-0.21.1-x509_crl.patch
License: MIT
Group: System Environment/Libraries
URL: http://wiki.osafoundation.org/bin/view/Projects/MeTooCrypto
BuildRequires: openssl-devel, python2-devel
BuildRequires: perl, pkgconfig, swig, which


# we don't want to provide private python extension libs
%{?filter_setup:
%filter_provides_in %{python_sitearch}/M2Crypto/__m2crypto.so
%filter_setup
}

%description
This package allows you to call OpenSSL functions from python scripts.

%prep
%setup -q -n M2Crypto-%{version}
%patch0 -p1 -b .timeouts
%patch1 -p1 -b .gcc_macros
%patch2 -p1 -b .fips
%patch3 -p1 -b .check
#%patch4 -p1 -b .memoryview
%patch4 -p0
%patch5 -p1 -b .x509_crl

# Red Hat opensslconf.h #includes an architecture-specific file, but SWIG
# doesn't follow the #include.

# Determine which arch opensslconf.h is going to try to #include.
basearch=%{_arch}
%ifarch %{ix86}
basearch=i386
%endif
%ifarch sparcv9
basearch=sparc
%endif
%ifarch %{multilib_arches}
for i in SWIG/_ec.i SWIG/_evp.i; do
	sed -i -e "s/opensslconf/opensslconf-${basearch}/" "$i"
done
%endif

gcc -E -dM - < /dev/null | grep -v __STDC__ \
	| sed 's/^\(#define \([^ ]*\) .*\)$/#undef \2\n\1/' > SWIG/gcc_macros.h

%build
CFLAGS="$RPM_OPT_FLAGS" ; export CFLAGS
if pkg-config openssl ; then
	CFLAGS="$CFLAGS `pkg-config --cflags openssl`" ; export CFLAGS
	LDFLAGS="$LDFLAGS`pkg-config --libs-only-L openssl`" ; export LDFLAGS
fi

# -cpperraswarn is necessary for including opensslconf-${basearch} directly
SWIG_FEATURES=-cpperraswarn %{__python} setup.py build

%install
CFLAGS="$RPM_OPT_FLAGS" ; export CFLAGS
if pkg-config openssl ; then
	CFLAGS="$CFLAGS `pkg-config --cflags openssl`" ; export CFLAGS
	LDFLAGS="$LDFLAGS`pkg-config --libs-only-L openssl`" ; export LDFLAGS
fi

%{__python} setup.py install --root=$RPM_BUILD_ROOT

for i in medusa medusa054; do
	sed -i -e '1s,#! /usr/local/bin/python,#! %{__python},' \
		demo/$i/http_server.py
done

# Windows-only
rm demo/Zope/starts.bat
# Fix up documentation permissions
find demo tests -type f -perm -111 -print0 | xargs -0 chmod a-x

grep -rl '/usr/bin/env python' demo tests \
	| xargs sed -i "s,/usr/bin/env python,%{__python},"

rm tests/*.py.* # Patch backup files

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc CHANGES LICENCE README demo tests
%{python_sitearch}/M2Crypto
%{python_sitearch}/M2Crypto-*.egg-info

%changelog
* Thu Jan 19 2012 John Matthews <jmatthews@redhat.com> 0.21.1.pulp-7
- Bumping M2Crypto.spec to include getLastUpdate/getNextUpdate CRL support as
  well as M2Crypto unit tests (jmatthews@redhat.com)

* Wed Sep 21 2011 John Matthews <jmatthews@redhat.com> 0.21.1.pulp-5
- 739555 - m2crypto spec update, remove patch for memoryview, conflicts with
  el6 (jmatthews@redhat.com)

* Wed Aug 31 2011 John Matthews <jmatthews@redhat.com> 0.21.1.pulp-3
- WIP for M2Crypto rpm to build with tito (jmatthews@redhat.com)

* Wed Aug 31 2011 John Matthews <jmatthews@redhat.com> 0.21.1.pulp-2
- new package built with tito

* Mon Aug 29 2011 John Matthews <jmatthews@redhat.com> - 0.21.1.pulp-1
- Adding patch for CRL verification through X509_Store_Context
- Changing default X509_NAME_hash from using old version to current
  this allows python code to match same hash reported from openssl CLI

* Mon Mar 28 2011 Miloslav Trmač <mitr@volny.cz> - 0.21.1-3
- Fix S/MIME documentation and examples
  Resolves: #618500

* Wed Feb 23 2011 Garrett Holmstrom <gholms@fedoraproject.org> - 0.21.1-3
- Use the %%__python macro for Python calls and locations
  Patch by Garrett Holmstrom <gholms@fedoraproject.org>

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.21.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Tue Jan 18 2011 Miloslav Trmač <mitr@redhat.com> - 0.21.1-1
- Update to m2crypto-0.21.1
- Make the test suite pass with Python 2.7

* Wed Jul 21 2010 David Malcolm <dmalcolm@redhat.com> - 0.20.2-9
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Fri Jul  9 2010 Miloslav Trmač <mitr@redhat.com> - 0.20.2-8
- Allow overriding SSL.Connection.postConnectionCheck from m2urllib2
  Resolves: #610906

* Wed May 19 2010 Miloslav Trmač <mitr@redhat.com> - 0.20.2-7
- Make test suite pass in FIPS mode
  Resolves: #565662

* Thu Mar  4 2010 Miloslav Trmač <mitr@redhat.com> - 0.20.2-6
- Filter out bogus Provides: __m2crypto.so
- Drop explicit Requires: python

* Mon Feb 15 2010 Miloslav Trmač <mitr@redhat.com> - 0.20.2-5
- Make test suite pass with OpenSSL 1.0.0
- Don't ship patch backup files in %%doc

* Tue Jan  5 2010 Miloslav Trmač <mitr@redhat.com> - 0.20.2-4
- s/%%define/%%global/

* Mon Dec  7 2009 Miloslav Trmač <mitr@redhat.com> - 0.20.2-3
- Don't use '!# /usr/bin/env python'
  Resolves: #521887

* Thu Oct 15 2009 Miloslav Trmač <mitr@redhat.com> - 0.20.2-2
- Add a dist tag.

* Wed Oct  7 2009 Miloslav Trmač <mitr@redhat.com> - 0.20.2-1
- Update to m2crypto-0.20.2
- Drop BuildRoot: and cleaning it at start of %%install

* Sun Aug 30 2009 Miloslav Trmač <mitr@redhat.com> - 0.20.1-1
- Update to m2crypto-0.20.1
- Add upstream patch to build with OpenSSL 1.0.0

* Fri Aug 21 2009 Tomas Mraz <tmraz@redhat.com> - 0.20-2
- rebuilt with new openssl

* Tue Aug 11 2009 Miloslav Trmač <mitr@volny.cz> - 0.20-1
- Update to m2crypto-0.20
- Fix incorrect merge in HTTPS CONNNECT proxy support

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.19.1-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Jun 24 2009 Miloslav Trmač <mitr@redhat.com> - 0.19.1-9
- Fix OpenSSL locking callback
  Resolves: #507903

* Wed Jun 10 2009 Miloslav Trmač <mitr@redhat.com> - 0.19.1-8
- Don't reject certificates with subjectAltName that does not contain a dNSName
  Resolves: #504060

* Wed Jun  3 2009 Miloslav Trmač <mitr@redhat.com> - 0.19.1-7
- Only send the selector in SSL HTTP requests.  Patch by James Bowes
  <jbowes@redhat.com>.
  Resolves: #491674

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.19.1-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Wed Feb  4 2009 Miloslav Trmač <mitr@redhat.com> - 0.19.1-5
- Close the connection when an m2urllib2 response is closed
  Resolves: #460692
- Work around conflicts between macros defined by gcc and swig

* Sat Jan 17 2009 Tomas Mraz <tmraz@redhat.com> - 0.19.1-4
- rebuild with new openssl

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 0.19.1-3
- Rebuild for Python 2.6

* Mon Nov 10 2008 Miloslav Trmač <mitr@redhat.com> - 0.19.1-2
- Import all gcc-defined macros into SWIG (recommended by Adam Tkac)

* Mon Oct 13 2008 Miloslav Trmač <mitr@redhat.com> - 0.19.1-1
- Update to m2crypto-0.19.1

* Mon Oct  6 2008 Miloslav Trmač <mitr@redhat.com> - 0.19-1
- Update to m2crypto-0.19
- Fix some rpmlint warnings

* Thu Sep 18 2008 Dennis Gilmore <dennis@ausil.us> - 0.18.2-8
- enable sparc arches

* Wed Jun 11 2008 Miloslav Trmač <mitr@redhat.com> - 0.18.2-7
- Update m2urllib2 to match the Python 2.5 code instead

* Sun Jun  8 2008 Miloslav Trmač <mitr@redhat.com> - 0.18.2-6
- Don't remove the User-Agent header from proxied requests
  Related: #448858
- Update m2urllib2.py to work with Python 2.5

* Sat Jun  7 2008 Miloslav Trmač <mitr@redhat.com> - 0.18.2-5
- Use User-Agent in HTTP proxy CONNECT requests
  Related: #448858

* Tue Feb 19 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 0.18.2-4
- Autorebuild for GCC 4.3

* Fri Jan 11 2008 Miloslav Trmač <mitr@redhat.com> - 0.18.2-3
- Ship Python egg information

* Tue Dec  4 2007 Miloslav Trmač <mitr@redhat.com> - 0.18.2-2
- Rebuild with openssl-0.9.8g

* Fri Oct 26 2007 Miloslav Trmač <mitr@redhat.com> - 0.18.2-1
- Update to m2crypto-0.18.2
- Remove BuildRequires: unzip

* Sun Sep 23 2007 Miloslav Trmač <mitr@redhat.com> - 0.18-2
- Add missing Host: header to CONNECT requests (patch by Karl Grindley)
  Resolves: #239034
- Fix License:

* Wed Aug  1 2007 Miloslav Trmač <mitr@redhat.com> - 0.18-1
- Update to m2crypto-0.18

* Wed Jul 11 2007 Miloslav Trmač <mitr@redhat.com> - 0.17-3
- Try to fix build on Alpha
  Resolves: #246828

* Fri Apr 27 2007 Miloslav Trmac <mitr@redhat.com> - 0.17-2
- Make m2xmlrpclib work with Python 2.5
  Resolves: #237902

* Wed Jan 17 2007 Miloslav Trmac <mitr@redhat.com> - 0.17-1
- Update to m2crypto-0.17
- Update for Python 2.5

* Thu Dec  7 2006 Miloslav Trmac <mitr@redhat.com> - 0.16-8
- Rebuild with updated build tools to avoid DT_TEXTREL on s390x
  Resolves: #218578

* Thu Dec  7 2006 Jeremy Katz <katzj@redhat.com> - 0.16-7
- rebuild against python 2.5

* Mon Oct 23 2006 Miloslav Trmac <mitr@redhat.com> - 0.16-6
- Add support for SSL socket timeouts (based on a patch by James Bowes
  <jbowes@redhat.com>)
  Resolves: #219966

* Fri Oct 20 2006 Miloslav Trmac <mitr@redhat.com> - 0.16-5
- Backport the urllib2 wrapper (code by James Bowes <jbowes@redhat.com>)
  Resolves: #210956
- Add proxy support for https using CONNECT (original patch by James Bowes
  <jbowes@redhat.com>)
  Resolves: #210963

* Tue Sep 26 2006 Miloslav Trmac <mitr@redhat.com> - 0.16-4
- Drop Obsoletes: openssl-python, openssl-python was last shipped in RHL 7.1
- Fix interpreter paths in demos

* Sat Sep 23 2006 Miloslav Trmac <mitr@redhat.com> - 0.16-3
- Make more compliant with Fedora guidelines
- Update URL:

* Wed Jul 12 2006 Jesse Keating <jkeating@redhat.com> - 0.16-2.1
- rebuild

* Thu Jul  6 2006 Miloslav Trmac <mitr@redhat.com> - 0.16-2
- Fix build with rawhide swig

* Thu Jul  6 2006 Miloslav Trmac <mitr@redhat.com> - 0.16-1
- Update to m2crypto-0.16

* Wed Apr 19 2006 Miloslav Trmac <mitr@redhat.com> - 0.15-4
- Fix SSL.Connection.accept (#188742)

* Fri Feb 10 2006 Jesse Keating <jkeating@redhat.com> - 0.15-3.2
- bump again for double-long bug on ppc(64)

* Tue Feb 07 2006 Jesse Keating <jkeating@redhat.com> - 0.15-3.1
- rebuilt for new gcc4.1 snapshot and glibc changes

* Tue Jan  3 2006 Miloslav Trmac <mitr@redhat.com> - 0.15-3
- Add BuildRequires: swig

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Wed Nov  9 2005 Miloslav Trmac <mitr@redhat.com> - 0.15-2
- Rebuild with newer openssl

* Mon Aug 29 2005 Miloslav Trmac <mitr@redhat.com> - 0.15-1
- Update to m2crypto-0.15
- Drop bundled swig

* Tue Jun 14 2005 Miloslav Trmac <mitr@redhat.com> - 0.13-5
- Better fix for #159898, by Dan Williams

* Thu Jun  9 2005 Miloslav Trmac <mitr@redhat.com> - 0.13-4
- Fix invalid handle_error override in SSL.SSLServer (#159898, patch by Dan
  Williams)

* Tue May 31 2005 Miloslav Trmac <mitr@redhat.com> - 0.13-3
- Fix invalid Python version comparisons in M2Crypto.httpslib (#156979)
- Don't ship obsolete xmlrpclib.py.patch
- Clean up the build process a bit

* Wed Mar 16 2005 Nalin Dahyabhai <nalin@redhat.com> 0.13-2
- rebuild

* Tue Nov 23 2004 Karsten Hopp <karsten@redhat.de> 0.13-1
- update, remove now obsolete patches

* Mon Nov 22 2004 Karsten Hopp <karsten@redhat.de> 0.09-7
- changed pythonver from 2.3 to 2.4

* Tue Jun 15 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Tue Mar 02 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Tue Feb 24 2004 Harald Hoyer <harald@redhat.com> - 0.09-5
- changed pythonver from 2.2 to 2.3
- patched setup.py to cope with include path

* Fri Feb 13 2004 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Wed Jun 04 2003 Elliot Lee <sopwith@redhat.com>
- rebuilt

* Wed Jan 22 2003 Tim Powers <timp@redhat.com>
- rebuilt

* Tue Jan 14 2003 Nalin Dahyabhai <nalin@redhat.com> 0.09-1
- Update to version 0.09
- Build using bundled copy of SWIG
- Pick up additional CFLAGS and LDFLAGS from OpenSSL's pkgconfig data, if
  there is any
- Handle const changes in new OpenSSL
- Remove unnecessary ldconfig calls in post/postun

* Thu Dec 12 2002 Elliot Lee <sopwith@redhat.com> 0.07_snap3-2
- Update to version 0.07_snap3

* Fri Jun 21 2002 Tim Powers <timp@redhat.com>
- automated rebuild

* Sun May 26 2002 Tim Powers <timp@redhat.com>
- automated rebuild

* Mon May 20 2002 Nalin Dahyabhai <nalin@redhat.com> 0.05_snap4-4
- rebuild with Python 2.2

* Wed Apr 24 2002 Nalin Dahyabhai <nalin@redhat.com> 0.05_snap4-3
- remove a stray -L at link-time which prevented linking with libssl (#59985)

* Thu Aug 23 2001 Nalin Dahyabhai <nalin@redhat.com> 0.05_snap4-2
- drop patch which isn't needed because we know swig is installed

* Mon Apr  9 2001 Nalin Dahyabhai <nalin@redhat.com> 0.05_snap4-1
- break off from openssl-python
