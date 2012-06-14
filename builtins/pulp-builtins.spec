
Name: pulp-builtins
Version: 0.0.296
Release: 1%{?dist}
Summary: Pulp builtin extensions
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/pulp-builtins/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose
BuildRequires:  rpm-python

%description
The pulp project provided generic extensions.

%prep
%setup -q

%build

%install

# Directories
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/consumer/extensions


# Extensions
cp -R extensions/admin/* %{buildroot}/%{_usr}/lib/%{name}/admin/extensions
cp -R extensions/consumer/* %{buildroot}/%{_usr}/lib/%{name}/consumer/extensions

%clean
rm -rf %{buildroot}


################################################################################
# Admin (builtin) Extensions
################################################################################

%package admin-extensions
Summary: The builtin admin client extensions
Requires: %{name}-admin-client = %{version}

%description admin-extensions
A tool used to administer a pulp consumer.

%files admin-extensions
%defattr(-,root,root,-)
%{_usr}/lib/%{name}/admin/extensions/pulp_admin_auth/
%{_usr}/lib/%{name}/admin/extensions/pulp_admin_consumer/
%{_usr}/lib/%{name}/admin/extensions/pulp_repo/
%{_usr}/lib/%{name}/admin/extensions/pulp_server_info/
%{_usr}/lib/%{name}/admin/extensions/pulp_tasks/
%doc


################################################################################
# Consumer (builtin) Extensions
################################################################################

%package consumer-extensions
Summary: The builtin consumer client extensions
Requires: %{name}-consumer-client = %{version}

%description consumer-extensions
A tool used to administer a pulp consumer.

%files consumer-extensions
%defattr(-,root,root,-)
%{_usr}/lib/%{name}/consumer/extensions/pulp_consumer/
%doc


################################################################################

%changelog
* Thu Jun 14 2012 Jeff Ortel <jortel@redhat.com> 0.0.296-1
- new package built with tito

* Fri Jun 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.295-1
- created.
