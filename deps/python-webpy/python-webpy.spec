%global pkgname webpy
%global srcname web.py

Name:           python-%{pkgname}
Version:        0.37
Release:        3%{?dist}
Summary:        A simple web framework for Python
Group:          Development/Libraries

# The entire source code is Public Domain save for the following exceptions:
#   web/debugerror.py (Modified BSD)
#     This is from django
#     See http://code.djangoproject.com/browser/django/trunk/LICENSE
#   web/httpserver.py (Modified BSD)
#     This is from WSGIUtils/lib/wsgiutils/wsgiServer.py
#     See http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5
License:        Public Domain and BSD

URL:            http://webpy.org/
Source0:        http://webpy.org/static/%{srcname}-%{version}.tar.gz
BuildRequires:  python2-devel
BuildArch:      noarch
Requires:       python-cherrypy

%description
web.py is a web framework for python that is as simple as it is
powerful. web.py is in the public domain; you can use it for whatever
purpose with absolutely no restrictions. 

%prep
%setup -q -n web.py-%{version}
rm web/wsgiserver/ssl_builtin.py
rm web/wsgiserver/ssl_pyopenssl.py
rm web/wsgiserver/__init__.py
echo "from cherrypy.wsgiserver import *" >> web/wsgiserver/__init__.py

%build
%{__python} setup.py build

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}


%files
%doc PKG-INFO
%{python_sitelib}/web
%{python_sitelib}/%{srcname}-%{version}-py?.?.egg-info


%changelog
* Thu May 01 2014 Chris Duryee <cduryee@redhat.com> 0.37-3
- new package built with tito

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.37-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Wed Jun 27 2012 Matthias Runge <mrunge@matthias-runge.de> - 0.37-1
- update to 0.37
- minor spec cleanup

* Wed Mar 14 2012 Matthias Runge <mrunge@matthias-runge.de> - 0.36-2
- unbundle cherrypy-code

* Wed Jan 25 2012 Matthias Runge <mrunge@matthias-runge.de> - 0.36-1
- rebase to 0.36

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.32-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Thu Jul 22 2010 David Malcolm <dmalcolm@redhat.com> - 0.32-5
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.32-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

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
