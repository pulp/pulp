Name: pulp-dot-2.0-test
Version: 0.1.2
Release: 1%{?dist}
Summary: Test package to see how we deal with packages with dots in the name

Group: Development/Libraries
License: MIT
URL: https://fedorahosted.org/pulp/		
Source0: %{name}-%{version}.tar.gz
BuildRoot:	%{_tmppath}/%{name}

# BuildRequires:	
# Requires:	

%description
Test package to see how we deal with packages with dots in the name


%prep
%setup -q

%build


%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/etc/
cp  $RPM_BUILD_DIR/%{name}-%{version}/pulp-dot-test.txt $RPM_BUILD_ROOT/etc/

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%config %{_sysconfdir}/pulp-dot-test.txt


%changelog
* Wed Jun 23 2010 Mike McCune <mmccune@redhat.com> 0.1.2-1
- new package

* Wed May 05 2010 Mike McCune <mmccune@redhat.com> 0.3.1-1
- new package

* Wed May 05 2010 <mmccune@redhat.com> - 0.1.1
- Initial rev


