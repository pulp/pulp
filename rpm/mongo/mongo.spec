Name: mongo
Version: 1.4.4
Release: 0%{?dist}
Summary: mongo client shell and tools
License: AGPLv3
URL: http://www.mongodb.org
Group: Applications/Databases

Source0: mongodb-src-r%{version}.tar.gz
#Source0: http://downloads.mongodb.org/src/mongodb-src-r%{version}.tar.gz
Patch0: mongodb-lib32.patch
BuildRoot: %{_tmppath}/mongo-%{version}-%{release}-root
BuildRequires: js-devel, readline-devel, boost-devel, pcre-devel
BuildRequires: gcc-c++, scons

%description
Mongo (from "huMONGOus") is a schema-free document-oriented database.
It features dynamic profileable queries, full indexing, replication
and fail-over support, efficient storage of large binary data objects,
and auto-sharding.

This package provides the mongo shell, import/export tools, and other
client utilities.

%package server
Summary: mongo server, sharding server, and support scripts
Group: Applications/Databases
Requires: mongo

%description server
Mongo (from "huMONGOus") is a schema-free document-oriented database.

This package provides the mongo server software, mongo sharding server
softwware, default configuration files, and init.d scripts.

%package devel
Summary: Headers and libraries for mongo development. 
Group: Applications/Databases

%description devel
Mongo (from "huMONGOus") is a schema-free document-oriented database.

This package provides the mongo static library and header files needed
to develop mongo client software.

%prep



%setup -q -n mongodb-src-r%{version}
patch -p0 <  %{PATCH0}

%build
%ifarch i686
scons --prefix=$RPM_BUILD_ROOT/usr --32  all
%else
scons --prefix=$RPM_BUILD_ROOT/usr  all
%endif

# XXX really should have shared library here

%install
scons --prefix=$RPM_BUILD_ROOT/usr install
mkdir -p $RPM_BUILD_ROOT/usr/share/man/man1
cp debian/*.1 $RPM_BUILD_ROOT/usr/share/man/man1/
mkdir -p $RPM_BUILD_ROOT/etc/rc.d/init.d
cp rpm/init.d-mongod $RPM_BUILD_ROOT/etc/rc.d/init.d/mongod
chmod a+x $RPM_BUILD_ROOT/etc/rc.d/init.d/mongod
mkdir -p $RPM_BUILD_ROOT/etc
cp rpm/mongod.conf $RPM_BUILD_ROOT/etc/mongod.conf
mkdir -p $RPM_BUILD_ROOT/etc/sysconfig
cp rpm/mongod.sysconfig $RPM_BUILD_ROOT/etc/sysconfig/mongod
mkdir -p $RPM_BUILD_ROOT/var/lib/mongo
mkdir -p $RPM_BUILD_ROOT/var/log/mongo
#touch $RPM_BUILD_ROOT/var/log/mongo/mongod.log

%clean
scons -c
rm -rf $RPM_BUILD_ROOT

%pre server

/usr/sbin/groupadd -g 71 -o -r mongod >/dev/null 2>&1 || :
/usr/sbin/useradd -M -g mongod -o -r -d /var/lib/mongo -s /bin/bash \
	-c "MongoDB Server" -u 71 mongod >/dev/null 2>&1 || :

%post server
if test $1 = 1
then
  /sbin/chkconfig --add mongod
fi

%preun server
if test $1 = 0
then
  /sbin/service mongod stop >/dev/null 2>&1
  /sbin/chkconfig --del mongod
fi


%files
%defattr(-,root,root,-)
%doc README GNU-AGPL-3.0.txt

%{_bindir}/mongo
%{_bindir}/mongodump
%{_bindir}/mongoexport
%{_bindir}/mongofiles
%{_bindir}/mongoimport
%{_bindir}/mongorestore
%{_bindir}/mongostat

%{_mandir}/man1/mongo.1*
%{_mandir}/man1/mongod.1*
%{_mandir}/man1/mongodump.1*
%{_mandir}/man1/mongoexport.1*
%{_mandir}/man1/mongofiles.1*
%{_mandir}/man1/mongoimport.1*
%{_mandir}/man1/mongosniff.1*
%{_mandir}/man1/mongostat.1*
%{_mandir}/man1/mongorestore.1*

%files server
%defattr(-,root,root,-)
%config(noreplace) /etc/mongod.conf
%{_bindir}/mongod
%{_bindir}/mongos
#%{_mandir}/man1/mongod.1*
%{_mandir}/man1/mongos.1*
/etc/rc.d/init.d/mongod
/etc/sysconfig/mongod
#/etc/rc.d/init.d/mongos
%attr(0755,mongod,mongod) %dir /var/log/mongo
%attr(0755,mongod,mongod) %dir /var/lib/mongo
#%attr(0640,mongod,mongod) %config(noreplace) %verify(not md5 size mtime) /var/log/mongo/mongod.log

%files devel
/usr/include/mongo
%{_libdir}/libmongoclient.a
#%{_libdir}/libmongotestfiles.a



%changelog
* Thu Jul 08 2010 Mike McCune <mmccune@redhat.com> 1.4.4-0
- upgrading to 1.4.4 (mmccune@redhat.com)

* Thu Jun 03 2010 Mike McCune <mmccune@redhat.com> 1.4.2-7
- seeing if i can get tito to build this

* Thu May 27 2010 Jason L Connor <jconnor@redhat.com> - 1.4.2-6
- removed -N option to useradd, which isn't supported by rhel5 shadow-utils

* Wed May 26 2010 Adam Young <ayoung@redhat.com> - 1.4.2-5
- Cleaned up rpmlint complaints
- No longer trying to manage the log or remove the mongod user IAW Fedora 
  guidelines

* Mon May 24 2010 Jason L Connor <jconnor@redhat.com> - 1.4.2-3
- added %preunistall directives

* Mon May 24 2010 Jason L Connor <jconnor@redhat.com> - 1.4.2-2
- added %unistall directives
- added user and group cleanup on uninstall to mongo's spec file

* Fri May 21 2010 Adam Young <ayoung@redhat.com> - 1.4.2-2
- Removed The -U option which is not supporteed  RHEL5 shadow-utils.  It is not needed on F12 or later

* Fri May 7 2010 Jason L Connor <jconnor@redhat.com> - 1.4.2
- changed spec to use with default naming of source tarball
- updated to version 1.4.2

* Thu Jan 28 2010 Richard M Kreuter <richard@10gen.com>
- Minor fixes.

* Sat Oct 24 2009 Joe Miklojcik <jmiklojcik@shopwiki.com> - 
- Wrote mongo.spec.
