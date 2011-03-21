%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%define pkgname webpy

Name:           python-webpy
Version:        0.32
Release:        8%{?dist}
Summary:        A simple web framework for Python
Group:          Development/Libraries

# The entire source code is Public Domain save for the following exceptions:
#   web/wsgiserver (CherryPy/BSD)
#     See LICENSE.wsgiserver.txt
#     See http://fedoraproject.org/wiki/Licensing:BSD#New_BSD_.28no_advertising.2C_3_clause.29
#   web/debugerror.py (Modified BSD)
#     This is from django
#     See http://code.djangoproject.com/browser/django/trunk/LICENSE
#   web/httpserver.py (Modified BSD)
#     This is from WSGIUtils/lib/wsgiutils/wsgiServer.py
#     See http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5
License:        Public Domain and BSD

URL:            http://webpy.org/
Source0:        web.py-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires:  python-devel
BuildRequires:  python-setuptools
BuildArch:      noarch
# https://bugs.launchpad.net/webpy/+bug/396789
Patch0:         web.utils-tests.patch

%description
web.py is a web framework for python that is as simple as it is
powerful. web.py is in the public domain; you can use it for whatever
purpose with absolutely no restrictions. 

%prep
%setup -q -n %{pkgname}
%patch0 -p1 -b .tests
# Remove shebang from non scripts.
%{__sed} -i '1d' web/utils.py
%{__sed} -i '1d' web/application.py
%{__sed} -i '1d' web/__init__.py
%{__cp} web/wsgiserver/LICENSE.txt LICENSE.wsgiserver.txt

%build
%{__python} -c 'import setuptools; execfile("setup.py")' build

%check
%{__python} test/application.py
%{__python} test/doctests.py

%install
%{__rm} -rf %{buildroot}
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --root %{buildroot}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE.txt LICENSE.wsgiserver.txt ChangeLog.txt
%{python_sitelib}/*

%changelog
* Mon Mar 21 2011 John Matthews <jmatthews@redhat.com> 0.32-8
- Bring python-webpy spec/tags back to version 0.32 (jmatthews@redhat.com)
- Automatic commit of package [python-webpy] release [0.34-1].
  (jmatthews@redhat.com)
- Automatic commit of package [python-webpy] release [0.33-1].
  (jmatthews@redhat.com)

* Mon Mar 21 2011 John Matthews <jmatthews@redhat.com> 0.32-7

* Thu Jun 03 2010 Mike McCune <mmccune@redhat.com> 0.32-6
- Titoification : http://rm-rf.ca/tito

* Thu May 27 2010 Jason L Connor <jconnor@redhat.com> - 0.32-5
- removed patch
- added import of setuptools directly in spec file

* Thu May 27 2010 Jason L Connor <jconnor@redhat.com> - 0.32-4
- added patch to convert from distools to setuptools
- added build dependency for same

* Tue Jul 07 2009 Ray Van Dolson <rayvd@fedoraproject.org> - 0.32-3
- Strip shebang from non-scripts
- Update license information
- Enable unit tests

* Thu Jul 02 2009 Ray Van Dolson <rayvd@fedoraproject.org> - 0.32-2
- Added python-devel BuildRequires
- Updated with multiple licensing annotations

* Wed Jul 01 2009 Ray Van Dolson <rayvd@fedoraproject.org> - 0.32-1
- Rebase to 0.32

* Mon Jun 01 2009 Ray Van Dolson <rayvd@fedoraproject.org> - 0.31-1
- Initial package
