Name: pulp-test-package
Version: 0.4.1	
Release: 1%{?dist}
Summary: Test package	

Group: Development/Libraries
License: MIT
URL: https://fedorahosted.org/pulp/		
Source0: %{name}-%{version}.tar.gz
BuildRoot:	%{_tmppath}/%{name}
BuildArch:  noarch

# BuildRequires:	
# Requires:	

%description
Test package.  Nothing to see here.


%prep
%setup -q


%build


%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/etc/
cp  $RPM_BUILD_DIR/%{name}-%{version}/pulp-test-file.txt $RPM_BUILD_ROOT/etc/

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%config %{_sysconfdir}/pulp-test-file.txt


%changelog
* Tue Jul 13 2010 Mike McCune <mmccune@redhat.com> 0.4.1-1
- forcing noarch (mmccune@redhat.com)
* Wed May 05 2010 Mike McCune <mmccune@redhat.com> 0.3.1-1
- new package

* Wed May 05 2010 <mmccune@redhat.com> - 0.1.1
- Initial rev


