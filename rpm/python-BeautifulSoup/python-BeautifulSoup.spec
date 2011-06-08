%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %global pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

%define oname   BeautifulSoup

Name:           python-BeautifulSoup
Epoch:          1
Version:        3.0.8.1
Release:        3%{?dist}
Summary:        HTML/XML parser for quick-turnaround applications like screen-scraping

Group:          Development/Languages
License:        BSD
URL:            http://www.crummy.com/software/BeautifulSoup/
Source0:        http://www.crummy.com/software/BeautifulSoup/download/3.x/BeautifulSoup-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel

%description
Beautiful Soup is a Python HTML/XML parser designed for quick
turnaround projects like screen-scraping. Three features make it
powerful:

Beautiful Soup won't choke if you give it bad markup.

Beautiful Soup provides a few simple methods and Pythonic idioms for
navigating, searching, and modifying a parse tree.

Beautiful Soup automatically converts incoming documents to Unicode
and outgoing documents to UTF-8.

Beautiful Soup parses anything you give it.

Valuable data that was once locked up in poorly-designed websites is
now within your reach. Projects that would have taken hours take only
minutes with Beautiful Soup.


%prep
%setup -q -n %{oname}-%{version}


%build
%{__python} setup.py build
%{__python} -c 'import %{oname} as bs; print bs.__doc__' > COPYING
touch -r %{oname}.py COPYING


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

#Files installed by error
rm -rf $RPM_BUILD_ROOT%{_bindir}

 
%clean
rm -rf $RPM_BUILD_ROOT


%check
%{__python} BeautifulSoupTests.py


%files
%defattr(-,root,root,-)
%doc COPYING
%{python_sitelib}/%{oname}.py*
%exclude %{python_sitelib}/%{oname}Tests.py*
%if 0%{?fedora} >= 9 || 0%{?rhel} >= 6
%{python_sitelib}/%{oname}-%{version}-py%{pyver}.egg-info
%endif

%changelog
* Wed Jun 08 2011 John Matthews <jmatthew@redhat.com> 3.0.8.1-3
- 

* Tue Jun 07 2011 John Matthews <jmatthews@redhat.com> 3.0.8.1-2
- new package built with tito

* Sun Jun 20 2010 Terje Rosten <terje.rosten@ntnu.no> - 1:3.0.8.1-1
- 3.0.8.1

* Sun Dec  6 2009 Terje Rosten <terje.rosten@ntnu.no> - 1:3.0.8-1
- 3.0.8
- Fix source url

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:3.0.7a-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Jun 10 2009 kwizart < kwizart at gmail.com > - 1:3.0.7a-1
- Revert to 3.0.7a and bump Epoch - Fix #505043
  http://www.crummy.com/software/BeautifulSoup/3.1-problems.html

* Thu Feb 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.1.0.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Mon Jan 12 2009 kwizart < kwizart at gmail.com > - 3.1.0.1-2
- Fix installed files.

* Mon Jan 12 2009 kwizart < kwizart at gmail.com > - 3.1.0.1-1
- Update to 3.1.0.1

* Thu Dec  4 2008 kwizart < kwizart at gmail.com > - 3.0.7a-3
- ReTag

* Sat Nov 29 2008 Ignacio Vazquez-Abrams <ivazqueznet+rpm@gmail.com> - 3.0.7a-2
- Rebuild for Python 2.6

* Wed Oct 15 2008 kwizart < kwizart at gmail.com > - 3.0.7a-1
- Update to 3.0.7a

* Mon Jun 30 2008 Terje Rosten <terje.rosten@ntnu.no> - 3.0.7-2
- Rebuild

* Mon Jun 23 2008 Michel Alexandre Salim <salimma@fedoraproject.org> - 3.0.7-1
- Update to 3.0.7

* Tue Feb  5 2008 Terje Rosten <terje.rosten@ntnu.no> - 3.0.5-3
- Fix typo

* Tue Feb  5 2008 Terje Rosten <terje.rosten@ntnu.no> - 3.0.5-2
- Handle egg info
- Bump release

* Tue Feb  5 2008 Terje Rosten <terje.rosten@ntnu.no> - 3.0.5-1
- Update to 3.0.5
- Minor tweaks to spec file

* Wed Apr 18 2007 kwizart < kwizart at gmail.com > - 3.0.4-1
- Update to 3.0.4

* Wed Nov 29 2006 TC Wan <tcwan@cs.usm.my>
- Initial SPEC file for Fedora Core 5
