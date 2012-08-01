Name: test-package
Version: 0.1	
Release: 1%{?dist}
Summary: Test package	

Group: Development/Libraries
License: MIT
URL: https://fedorahosted.org/pulp/
Source0: test-package-data.txt
BuildRoot:	%{_tmppath}/%{name}
BuildArch:  noarch

# BuildRequires:	
# Requires:	

%description
Test package.  Nothing to see here.


%prep
#%setup -q

%build


%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/etc/
cp %{S:0} $RPM_BUILD_ROOT/etc

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%config %{_sysconfdir}/test-package-data.txt

%changelog
* Wed Aug 01 2012 John Matthews <jmatthews@redhat.com> 0.1-1
- Initial
