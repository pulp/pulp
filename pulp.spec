# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           pulp
Version:        0.0.3
Release:        1%{?dist}
Summary:        An application for managing software content

Group:          Development/Languages
License:        GPLv2
URL:            https://fedorahosted.org/pulp/
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools

%description
Pulp provides replication, access, and accounting for software repositories.

%prep
%setup -q


%build
pushd src
%{__python} setup.py build
popd


%install
rm -rf %{buildroot}
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

find %{buildroot} -name \*.py | xargs sed -i -e '/^#!\/usr\/bin\/env python/d' -e '/^#!\/usr\/bin\/python/d' 

# RHEL 5 packages don't have egg-info files, so remove the requires.txt
# It isn't needed, because RPM will guarantee the dependency itself
%if 0%{?rhel} > 0
%if 0%{?rhel} <= 5
rm -f %{buildroot}/%{python_sitelib}/%{name}*.egg-info/requires.txt
%endif
%endif

%check
pushd  %{buildroot}/%{python_sitelib}/%{name}
nosetests
popd
 
%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc
# For noarch packages: sitelib
%{python_sitelib}/*
%{_bindir}/juicer

%changelog

* Thu May 20 2010 Mike McCune <ayoung@redhat.com> 0.0.3-1
- fixed call to setup to install all files

* Thu May 20 2010 Mike McCune <mmccune@redhat.com> 0.0.2-1
- tito tagging


* Thu May 20 2010 Adam Young 0.0.3-1
- Use macro for file entry for juicer
- strip leading line from files that are not supposed to be scripts 

* Wed May 19 2010 Adam Young  <ayoung@redhat.com> - 0.0.1
- Initial specfile
