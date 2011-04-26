Name: REPLACE_NAME
Version: REPLACE_VERSION
Release: 1%{?dist}
Summary: Test package	

Group: Development/Libraries
License: MIT
URL: https://fedorahosted.org/pulp/		
#Source0: %{name}-%{version}.tar.gz
#BuildRoot:	%{_tmppath}/%{name}
BuildArch:  REPLACE_ARCH

# BuildRequires:	
# Requires:	

%description
Test package.  Nothing to see here.


%prep
#%setup -q


%build


%install
rm -rf $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)


%changelog
* Tue Apr 26 2011 John Matthews <jmatthew@redhat.com> 
- Test package
