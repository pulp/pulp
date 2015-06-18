%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

# Fix private-shared-object-provides error
%{?filter_setup:
%filter_provides_in %{python_sitearch}.*\.so$
%filter_setup
}

%define srcname pymongo

Name:           python-%{srcname}
Version:        2.7.2
Release:        1%{?dist}
Summary:        Python driver for MongoDB

Group:          Development/Languages
# All code is ASL 2.0 except bson/time64*.{c,h} which is MIT
License:        ASL 2.0 and MIT
URL:            http://api.mongodb.org/python
Source0:        %{srcname}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       python-bson = %{version}-%{release}

Provides:       pymongo = %{version}-%{release}
Obsoletes:      pymongo <= 2.1.1-4

BuildRequires:  python2-devel
BuildRequires:  python-nose
BuildRequires:  python-setuptools

# Mongodb must run on a little-endian CPU (see bug #630898)
ExcludeArch:    ppc ppc64 %{sparc} s390 s390x

%description
The Python driver for MongoDB.


%package gridfs
Summary:        Python GridFS driver for MongoDB
Group:          Development/Libraries
Requires:       %{name}%{?_isa} = %{version}-%{release}
Provides:       pymongo-gridfs = %{version}-%{release}
Obsoletes:      pymongo-gridfs <= 2.1.1-4

%description gridfs
GridFS is a storage specification for large objects in MongoDB.


%package -n python-bson
Summary:        Python bson library
Group:          Development/Libraries

%description -n python-bson
BSON is a binary-encoded serialization of JSON-like documents. BSON is designed
to be lightweight, traversable, and efficient. BSON, like JSON, supports the
embedding of objects and arrays within other objects and arrays.


%prep
%setup -q -n mongo-python-driver-%{version}
rm -rf pymongo.egg-info

%build
CFLAGS="%{optflags}" %{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE README.rst doc
%{python_sitearch}/pymongo
%{python_sitearch}/pymongo-%{version}-*.egg-info

%files gridfs
%defattr(-,root,root,-)
%doc LICENSE README.rst doc
%{python_sitearch}/gridfs

%files -n python-bson
%defattr(-,root,root,-)
%doc LICENSE README.rst doc
%{python_sitearch}/bson

%check
# Exclude tests that require an active MongoDB connection
exclude='(^test_auth_from_uri$'
exclude+='|^test_auto_auth_login$'
exclude+='|^test_auto_reconnect_exception_when_read_preference_is_secondary$'
exclude+='|^test_auto_start_request$'
exclude+='|^test_binary$'
exclude+='|^test_client$'
exclude+='|^test_client_generated_upsert_id$'
exclude+='|^test_collection$'
exclude+='|^test_common$'
exclude+='|^test_connect$'
exclude+='|^test_connection$'
exclude+='|^test_copy_db$'
exclude+='|^test_cursor$'
exclude+='|^test_database$'
exclude+='|^test_database_names$'
exclude+='|^test_delegated_auth$'
exclude+='|^test_disconnect$'
exclude+='|^test_document_class$'
exclude+='|^test_drop_database$'
exclude+='|^test_empty$'
exclude+='|^test_failover$'
exclude+='|^test_find$'
exclude+='|^test_fork$'
exclude+='|^test_fsync_and_j$'
exclude+='|^test_get_db$'
exclude+='|^test_grid_file$'
exclude+='|^test_gridfs$'
exclude+='|^test_insert$'
exclude+='|^test_insert_check_keys$'
exclude+='|^test_interrupt_signal$'
exclude+='|^test_ipv6$'
exclude+='|^test_iteration$'
exclude+='|^test_json_util$'
exclude+='|^test_kill_cursor_explicit_primary$'
exclude+='|^test_kill_cursor_explicit_secondary$'
exclude+='|^test_large_inserts_ordered$'
exclude+='|^test_large_inserts_unordered$'
exclude+='|^test_lazy_connect$'
exclude+='|^test_master_slave_connection$'
exclude+='|^test_multiple_error_ordered_batch$'
exclude+='|^test_multiple_error_unordered_batch$'
exclude+='|^test_multiple_execution$'
exclude+='|^test_nested_request$'
exclude+='|^test_network_timeout$'
exclude+='|^test_network_timeout_validation$'
exclude+='|^test_no_remove$'
exclude+='|^test_no_results_ordered_failure$'
exclude+='|^test_no_results_ordered_success$'
exclude+='|^test_no_results_unordered_failure$'
exclude+='|^test_no_results_unordered_success$'
exclude+='|^test_numerous_inserts$'
exclude+='|^test_operation_failure_with_request$'
exclude+='|^test_operation_failure_without_request$'
exclude+='|^test_operations$'
exclude+='|^test_pinned_member$'
exclude+='|^test_pooling$'
exclude+='|^test_pooling_gevent$'
exclude+='|^test_properties$'
exclude+='|^test_pymongo$'
exclude+='|^test_readonly$'
exclude+='|^test_read_preferences$'
exclude+='|^test_reconnect$'
exclude+='|^test_remove$'
exclude+='|^test_remove_one$'
exclude+='|^test_replace_one$'
exclude+='|^test_replica_set_client$'
exclude+='|^test_replica_set_connection$'
exclude+='|^test_replica_set_connection_alias$'
exclude+='|^test_safe_insert$'
exclude+='|^test_safe_update$'
exclude+='|^test_server_disconnect$'
exclude+='|^test_single_error_ordered_batch$'
exclude+='|^test_single_error_unordered_batch$'
exclude+='|^test_single_ordered_batch$'
exclude+='|^test_single_unordered_batch$'
exclude+='|^test_son_manipulator$'
exclude+='|^test_threading$'
exclude+='|^test_timeouts$'
exclude+='|^test_update$'
exclude+='|^test_upsert$'
exclude+='|^test_upsert_large$'
exclude+='|^test_update_one$'
exclude+='|^test_uri_options$'
exclude+='|^test_write_concern_failure_ordered$'
exclude+='|^test_write_concern_failure_unordered$'
exclude+=')'
pushd test
nosetests --exclude="$exclude"
popd

%changelog
* Fri Jun 19 2015 Brian Bouterse <bbouters@redhat.com> - 2.7.2-1
- Update to pymongo 2.7.2
- Updated the tests exclude test list for building 2.7.2

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.5.2-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.5.2-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.5.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed May 14 2014 Bohuslav Kabrda <bkabrda@redhat.com> - 2.5.2-4
- Rebuilt for https://fedoraproject.org/wiki/Changes/Python_3.4

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.5.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu Jun 13 2013 Andrew McNabb <amcnabb@mcnabbs.org> - 2.5.2-2
- Bump the obsoletes version for pymongo-gridfs

* Wed Jun 12 2013 Andrew McNabb <amcnabb@mcnabbs.org> - 2.5.2-1
- Update to pymongo 2.5.2

* Tue Jun 11 2013 Andrew McNabb <amcnabb@mcnabbs.org> - 2.5-5
- Bump the obsoletes version

* Wed Apr 24 2013 Andrew McNabb <amcnabb@mcnabbs.org> - 2.5-4
- Fix the test running procedure

* Wed Apr 24 2013 Andrew McNabb <amcnabb@mcnabbs.org> - 2.5-3
- Exclude tests in pymongo 2.5 that depend on MongoDB

* Mon Apr 22 2013 Andrew McNabb <amcnabb@mcnabbs.org> - 2.5-1
- Update to PyMongo 2.5 (bug #954152)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Sat Jan  5 2013 Andrew McNabb <amcnabb@mcnabbs.org> - 2.3-6
- Fix dependency of python3-pymongo-gridfs (bug #892214)

* Tue Nov 27 2012 Andrew McNabb <amcnabb@mcnabbs.org> - 2.3-5
- Fix the name of the python-pymongo-gridfs subpackage

* Tue Nov 27 2012 Andrew McNabb <amcnabb@mcnabbs.org> - 2.3-4
- Fix obsoletes for python-pymongo-gridfs subpackage

* Tue Nov 27 2012 Andrew McNabb <amcnabb@mcnabbs.org> - 2.3-3
- Fix requires to include the arch, and add docs to all subpackages

* Tue Nov 27 2012 Andrew McNabb <amcnabb@mcnabbs.org> - 2.3-2
- Remove preexisting egg-info

* Mon Nov 26 2012 Andrew McNabb <amcnabb@mcnabbs.org> - 2.3-1
- Rename, update to 2.3, and add support for Python 3

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Apr 10 2012 Silas Sewell <silas@sewell.org> - 2.1.1-1
- Update to 2.1.1

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.11-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Sun Jul 24 2011 Silas Sewell <silas@sewell.org> - 1.11-1
- Update to 1.11

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.9-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Thu Nov 18 2010 Dan Horák <dan[at]danny.cz> - 1.9-5
- add ExcludeArch to match mongodb package

* Tue Oct 26 2010 Silas Sewell <silas@sewell.ch> - 1.9-4
- Add comment about multi-license

* Thu Oct 21 2010 Silas Sewell <silas@sewell.ch> - 1.9-3
- Fixed tests so they actually run
- Change python-devel to python2-devel

* Wed Oct 20 2010 Silas Sewell <silas@sewell.ch> - 1.9-2
- Add check section
- Use correct .so filter
- Added python3 stuff (although disabled)

* Tue Sep 28 2010 Silas Sewell <silas@sewell.ch> - 1.9-1
- Update to 1.9

* Tue Sep 28 2010 Silas Sewell <silas@sewell.ch> - 1.8.1-1
- Update to 1.8.1

* Sat Dec 05 2009 Silas Sewell <silas@sewell.ch> - 1.1.2-1
- Initial build
