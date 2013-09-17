Name: python-semantic-version
Version: 2.2.0
Release: 3%{?dist}
Summary: A library implementing the 'SemVer' scheme.

License: BSD
URL: http://github.com/rbarrois/python-semanticversion
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch

BuildRequires: python2-devel

%description
This small python library provides a few tools to handle SemVer
(http://semver.org) in Python. It follows strictly the 2.0.0-rc1 version of the
SemVer scheme.

%prep
%setup -q -n python-semanticversion-%{version}

# %check
# %{__python} setup.py test

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --root=$RPM_BUILD_ROOT


%files
%{python_sitelib}/semantic_version
%{python_sitelib}/semantic_version*.egg-info
%defattr(-,root,root)
%doc README LICENSE


%changelog
* Wed Sep 11 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-3
- comment out the unit tests in python-semantic-version. too much of a pain to
  add the dep in brew.  We can uncomment later. (jortel@redhat.com)

* Wed Sep 11 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-2
- add buildrequires: python-unittest2. (jortel@redhat.com)

* Tue Sep 10 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-1
- new package built with tito



