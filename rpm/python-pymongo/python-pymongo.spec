# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name:           python-pymongo
Version:        1.6
Release:        5%{?dist}
Summary:        Python driver for MongoDB <http://www.mongodb.org>
Group:          Development/Libraries
License:        Apache License, version 2.0
URL:            http://api.mongodb.org/python/%{version}/index.html
Source0:        python-pymongo-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  gcc
BuildRequires:  python-devel
BuildRequires:  python-setuptools
BuildRequires:  python-nose
BuildRequires:  python-sphinx

#Requires:       

%description
The PyMongo distribution contains tools for interacting with MongoDB database from Python. The pymongo package is a native Python driver for MongoDB.

%prep
%setup -q -n pymongo-%{version}


%build
%{__python} setup.py build


%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
 
%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc doc test tools LICENSE README.rst
%{python_sitearch}/pymongo
%{python_sitearch}/gridfs
%{python_sitearch}/pymongo-*.egg-info


%changelog
* Thu Jun 03 2010 Mike McCune <mmccune@redhat.com> 1.6-5
- Titoification 

* Fri May 7 2010 Jason L Connor <jconnor@redhat.com> - 1.6
- Initial package version.
