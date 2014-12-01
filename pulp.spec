%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

%if 0%{?rhel} == 5
%define pulp_admin 0
%define pulp_client_oauth 0
%define pulp_server 0
%else
%define pulp_admin 1
%define pulp_client_oauth 1
%define pulp_server 1
%endif

%if %{pulp_server}
#SELinux
%define selinux_variants mls strict targeted
%define selinux_policyver %(sed -e 's,.*selinux-policy-\\([^/]*\\)/.*,\\1,' /usr/share/selinux/devel/policyhelp 2> /dev/null)
%define moduletype apps
%endif

# Determine whether we should target Upstart or systemd for this build
%if 0%{?rhel} >= 7 || 0%{?fedora} >= 15
%define pulp_systemd 1
%else
%define pulp_systemd 0
%endif

# ---- Pulp Platform -----------------------------------------------------------

Name: pulp
Version: 2.6.0
Release: 0.1.alpha%{?dist}
Summary: An application for managing software content
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://github.com/%{name}/%{name}/archive/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
# do not include either of these on rhel 5
%if 0%{?rhel} == 6
BuildRequires: python-sphinx10 >= 1.0.8
%endif
%if 0%{?rhel} >= 7 || 0%{?fedora} >= 19
BuildRequires: python-sphinx >= 1.0.8
%endif
BuildRequires: rpm-python

%description
Pulp provides replication, access, and accounting for software repositories.

%prep
%setup -q

%build
for directory in agent bindings client_consumer client_lib common
do
    pushd $directory
    %{__python} setup.py build
    popd
done

# pulp-admin build block
%if %{pulp_admin}
pushd client_admin
%{__python} setup.py build
popd
%endif # End pulp-admin build block

%if %{pulp_server}
pushd server
%{__python} setup.py build
popd

# SELinux Configuration
cd server/selinux/server
%if 0%{?rhel} >= 6
    distver=rhel%{rhel}
%endif
%if 0%{?fedora} >= 18
    distver=fedora%{fedora}
%endif
sed -i "s/policy_module(pulp-server, [0-9]*.[0-9]*.[0-9]*)/policy_module(pulp-server, %{version})/" pulp-server.te
sed -i "s/policy_module(pulp-celery, [0-9]*.[0-9]*.[0-9]*)/policy_module(pulp-celery, %{version})/" pulp-celery.te
./build.sh ${distver}
cd -
%endif

# build man pages if we are able
pushd docs
%if 0%{?rhel} == 6
make man SPHINXBUILD=sphinx-1.0-build
%endif
%if 0%{?rhel} >= 7 || 0%{?fedora} >= 19
make man
%endif
popd docs

%install
rm -rf %{buildroot}
for directory in agent bindings client_consumer client_lib common
do
    pushd $directory
    %{__python} setup.py install -O1 --skip-build --root %{buildroot}
    popd
done

# Directories
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/agent
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/agent/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/consumer
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/consumer/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/gofer/plugins
mkdir -p %{buildroot}/%{_sysconfdir}/pki/%{name}
mkdir -p %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer
mkdir -p %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer/server
mkdir -p %{buildroot}/%{_sysconfdir}/rc.d/init.d
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/consumer
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/consumer/extensions
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/agent
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/agent/handlers
mkdir -p %{buildroot}/%{_var}/log/%{name}/
mkdir -p %{buildroot}/%{_libdir}/gofer/plugins
mkdir -p %{buildroot}/%{_bindir}
%if 0%{?rhel} >= 6 || 0%{?fedora} >= 19
mkdir -p %{buildroot}/%{_mandir}/man1
%endif

# pulp-admin installation
%if %{pulp_admin}
pushd client_admin
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/admin
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/admin/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/bash_completion.d
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/admin
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/admin/extensions

cp -R client_admin/etc/pulp/admin/admin.conf %{buildroot}/%{_sysconfdir}/%{name}/admin/
cp client_admin/etc/bash_completion.d/pulp-admin %{buildroot}/%{_sysconfdir}/bash_completion.d/
# pulp-admin man page (no need to fence this against el5 again)
cp docs/_build/man/pulp-admin.1 %{buildroot}/%{_mandir}/man1/
%endif # End pulp_admin installation block

# Server installation
%if %{pulp_server}
pushd server
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd

# These directories are specific to the server
mkdir -p %{buildroot}/srv
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/content/sources/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/server
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/server/plugins.conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/vhosts80
mkdir -p %{buildroot}/%{_sysconfdir}/default/
mkdir -p %{buildroot}/%{_sysconfdir}/httpd/conf.d/
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/plugins
mkdir -p %{buildroot}/%{_usr}/lib/%{name}/plugins/types
mkdir -p %{buildroot}/%{_var}/lib/%{name}/celery
mkdir -p %{buildroot}/%{_var}/lib/%{name}/uploads
mkdir -p %{buildroot}/%{_var}/lib/%{name}/published
mkdir -p %{buildroot}/%{_var}/lib/%{name}/static
mkdir -p %{buildroot}/%{_var}/www

# Configuration
cp -R server/etc/pulp/* %{buildroot}/%{_sysconfdir}/%{name}

# Apache Configuration
%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
cp server/etc/httpd/conf.d/pulp_apache_24.conf %{buildroot}/%{_sysconfdir}/httpd/conf.d/pulp.conf
%else
cp server/etc/httpd/conf.d/pulp_apache_22.conf %{buildroot}/%{_sysconfdir}/httpd/conf.d/pulp.conf
%endif

# Server init scripts/unit files and environment files
%if %{pulp_systemd} == 0
cp server/etc/default/upstart_pulp_celerybeat %{buildroot}/%{_sysconfdir}/default/pulp_celerybeat
cp server/etc/default/upstart_pulp_resource_manager %{buildroot}/%{_sysconfdir}/default/pulp_resource_manager
cp server/etc/default/upstart_pulp_workers %{buildroot}/%{_sysconfdir}/default/pulp_workers
cp -d server/etc/rc.d/init.d/* %{buildroot}/%{_initddir}/
# We don't want to install pulp-manage-workers in upstart systems
rm -rf %{buildroot}/%{_libexecdir}
%else
cp server/etc/default/systemd_pulp_celerybeat %{buildroot}/%{_sysconfdir}/default/pulp_celerybeat
cp server/etc/default/systemd_pulp_resource_manager %{buildroot}/%{_sysconfdir}/default/pulp_resource_manager
cp server/etc/default/systemd_pulp_workers %{buildroot}/%{_sysconfdir}/default/pulp_workers
mkdir -p %{buildroot}/%{_usr}/lib/systemd/system/
cp server/usr/lib/systemd/system/* %{buildroot}/%{_usr}/lib/systemd/system/
%endif

# Pulp Web Services
cp -R server/srv %{buildroot}

# Web Content
ln -s %{_var}/lib/pulp/published %{buildroot}/%{_var}/www/pub

# Tools
cp server/bin/* %{buildroot}/%{_bindir}

# Ghost
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/ca.key
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/ca.crt
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/rsa.key
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/rsa_pub.key

# Install SELinux policy modules
pushd server/selinux/server
./install.sh %{buildroot}%{_datadir}
mkdir -p %{buildroot}%{_datadir}/pulp/selinux/server
cp enable.sh %{buildroot}%{_datadir}/pulp/selinux/server
cp uninstall.sh %{buildroot}%{_datadir}/pulp/selinux/server
cp relabel.sh %{buildroot}%{_datadir}/pulp/selinux/server
popd
%endif # End server installation block

# Everything else installation

# Ghost
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer/rsa.key
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer/rsa_pub.key
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer/server/rsa_pub.key

# Configuration
cp -R agent/etc/pulp/agent/agent.conf %{buildroot}/%{_sysconfdir}/%{name}/agent/
cp -R client_consumer/etc/pulp/consumer/consumer.conf %{buildroot}/%{_sysconfdir}/%{name}/consumer/
%if 0%{?rhel} >= 6 || 0%{?fedora} >= 19
cp client_consumer/etc/bash_completion.d/pulp-consumer %{buildroot}/%{_sysconfdir}/bash_completion.d/
%endif

# Agent
rm -rf %{buildroot}/%{python_sitelib}/%{name}/agent/gofer
cp agent/etc/gofer/plugins/pulpplugin.conf %{buildroot}/%{_sysconfdir}/gofer/plugins
cp -R agent/pulp/agent/gofer/pulpplugin.py %{buildroot}/%{_libdir}/gofer/plugins

# Ghost
touch %{buildroot}/%{_sysconfdir}/pki/%{name}/consumer/consumer-cert.pem

# pulp-consumer man page
%if 0%{?rhel} >= 6 || 0%{?fedora} >= 19
cp docs/_build/man/pulp-consumer.1 %{buildroot}/%{_mandir}/man1
%endif

%clean
rm -rf %{buildroot}


# define required pulp platform version.
%global pulp_version %{version}


# ---- Server ------------------------------------------------------------------
%if %{pulp_server}
%package server
Summary: The pulp platform server
Group: Development/Languages
Requires: python-%{name}-common = %{pulp_version}
Requires: python-celery >= 3.1.0
Requires: python-celery < 3.2.0
Requires: python-pymongo >= 2.5.2
Requires: python-mongoengine >= 0.7.10
Requires: python-setuptools
Requires: python-webpy
Requires: python-okaara >= 1.0.32
Requires: python-oauth2 >= 1.5.211
Requires: python-httplib2
Requires: python-isodate >= 0.5.0-1.pulp
Requires: python-BeautifulSoup
Requires: python-qpid
Requires: python-nectar >= 1.1.6
Requires: httpd
Requires: mod_ssl
Requires: openssl
Requires: nss-tools
Requires: python-ldap
Requires: python-gofer >= 1.4.0
Requires: python-gofer-qpid >= 1.4.0
Requires: crontabs
Requires: acl
Requires: mod_wsgi >= 3.4-1.pulp
Requires: m2crypto
Requires: genisoimage
# RHEL6 ONLY
%if 0%{?rhel} == 6
Requires: nss >= 3.12.9
%endif
%if %{pulp_systemd} == 1
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%endif
Obsoletes: pulp

%description server
Pulp provides replication, access, and accounting for software repositories.

%files server
# - root:root
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/default/pulp_celerybeat
%config(noreplace) %{_sysconfdir}/default/pulp_workers
%config(noreplace) %{_sysconfdir}/default/pulp_resource_manager
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%dir %{_sysconfdir}/pki/%{name}
%dir %{_sysconfdir}/%{name}/content/sources/conf.d
%dir %{_sysconfdir}/%{name}/server
%dir %{_sysconfdir}/%{name}/server/plugins.conf.d
%dir %{_sysconfdir}/%{name}/vhosts80
%dir /srv/%{name}
/srv/%{name}/webservices.wsgi
%{_bindir}/pulp-manage-db
%{_bindir}/pulp-qpid-ssl-cfg
%{_bindir}/pulp-gen-ca-certificate
%{_usr}/lib/%{name}/plugins/types
%{python_sitelib}/%{name}/server/
%{python_sitelib}/%{name}/plugins/
%{python_sitelib}/pulp_server*.egg-info
%if %{pulp_systemd} == 0
# Install the init scripts
%defattr(755,root,root,-)
%config %{_initddir}/pulp_celerybeat
%config %{_initddir}/pulp_workers
%config %{_initddir}/pulp_resource_manager
%else
# Install the systemd unit files
%defattr(-,root,root,-)
%{_usr}/lib/systemd/system/*
%defattr(755,root,root,-)
%{_libexecdir}/pulp-manage-workers
%endif
# 640 root:apache
%defattr(640,root,apache,-)
%ghost %{_sysconfdir}/pki/%{name}/ca.key
%ghost %{_sysconfdir}/pki/%{name}/ca.crt
%ghost %{_sysconfdir}/pki/%{name}/rsa.key
%ghost %{_sysconfdir}/pki/%{name}/rsa_pub.key
%config(noreplace) %{_sysconfdir}/%{name}/server.conf
# - apache:apache
%defattr(-,apache,apache,-)
%{_var}/lib/%{name}/
%dir %{_var}/log/%{name}
%{_var}/www/pub
# Install the docs
%defattr(-,root,root,-)
%doc README LICENSE COPYRIGHT

%post server

# RSA key pair
KEY_DIR="%{_sysconfdir}/pki/%{name}"
KEY_PATH="$KEY_DIR/rsa.key"
KEY_PATH_PUB="$KEY_DIR/rsa_pub.key"
if [ ! -f $KEY_PATH ]
then
  openssl genrsa -out $KEY_PATH 2048 &> /dev/null
  openssl rsa -in $KEY_PATH -pubout > $KEY_PATH_PUB 2> /dev/null
fi
chmod 640 $KEY_PATH
chmod 644 $KEY_PATH_PUB
chown root:apache $KEY_PATH
chown root:apache $KEY_PATH_PUB
ln -fs $KEY_PATH_PUB %{_var}/lib/%{name}/static

# CA certificate
if [ $1 -eq 1 ]; # not an upgrade
then
  pulp-gen-ca-certificate
fi

%if %{pulp_systemd} == 1
%postun server
%systemd_postun
%endif
%endif # End pulp_server if block


# ---- Common ------------------------------------------------------------------

%package -n python-pulp-common
Summary: Pulp common python packages
Group: Development/Languages
Obsoletes: pulp-common
Requires: python-isodate >= 0.5.0-1.pulp
Requires: python-iniparse
# RHEL5 ONLY
%if 0%{?rhel} == 5
Requires: python-simplejson
%endif

%description -n python-pulp-common
A collection of components that are common between the pulp server and client.

%files -n python-pulp-common
%defattr(-,root,root,-)
%dir %{_usr}/lib/%{name}
%dir %{python_sitelib}/%{name}
%{python_sitelib}/%{name}/__init__.*
%{python_sitelib}/%{name}/common/
%{python_sitelib}/pulp_common*.egg-info
%doc README LICENSE COPYRIGHT


# ---- Client Bindings ---------------------------------------------------------

%package -n python-pulp-bindings
Summary: Pulp REST bindings for python
Group: Development/Languages
Requires: python-%{name}-common = %{pulp_version}
%if %{pulp_client_oauth}
Requires: python-oauth2 >= 1.5.170-2.pulp
%endif
Requires: m2crypto

%description -n python-pulp-bindings
The Pulp REST API bindings for python.

%files -n python-pulp-bindings
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/bindings/
%{python_sitelib}/pulp_bindings*.egg-info
%doc README LICENSE COPYRIGHT


# ---- Client Extension Framework -----------------------------------------------------

%package -n python-pulp-client-lib
Summary: Pulp client extensions framework
Group: Development/Languages
Requires: m2crypto
Requires: python-%{name}-common = %{pulp_version}
Requires: python-okaara >= 1.0.32
Requires: python-isodate >= 0.5.0-1.pulp
Requires: python-setuptools
Obsoletes: pulp-client-lib

%description -n python-pulp-client-lib
A framework for loading Pulp client extensions.

%files -n python-pulp-client-lib
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/client/commands/
%{python_sitelib}/%{name}/client/extensions/
%{python_sitelib}/%{name}/client/upload/
%{python_sitelib}/%{name}/client/*.py
%{python_sitelib}/%{name}/client/*.pyc
%{python_sitelib}/%{name}/client/*.pyo
%{python_sitelib}/pulp_client_lib*.egg-info
%doc README LICENSE COPYRIGHT


# ---- Agent Handler Framework -------------------------------------------------

%package -n python-pulp-agent-lib
Summary: Pulp agent handler framework
Group: Development/Languages
Requires: python-%{name}-common = %{pulp_version}

%description -n python-pulp-agent-lib
A framework for loading agent handlers that provide support
for content, bind and system specific operations.

%files -n python-pulp-agent-lib
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/agent/
%{python_sitelib}/pulp_agent*.egg-info
%dir %{_sysconfdir}/%{name}/agent
%dir %{_sysconfdir}/%{name}/agent/conf.d
%dir %{_usr}/lib/%{name}/agent
%doc README LICENSE COPYRIGHT


# ---- Admin Client (CLI) ------------------------------------------------------
%if %{pulp_admin}
%package admin-client
Summary: Admin tool to administer the pulp server
Group: Development/Languages
Requires: python >= 2.6
Requires: python-okaara >= 1.0.32
Requires: python-%{name}-common = %{pulp_version}
Requires: python-%{name}-bindings = %{pulp_version}
Requires: python-%{name}-client-lib = %{pulp_version}
Obsoletes: pulp-admin
Obsoletes: pulp-builtins-admin-extensions <= %{pulp_version}

%description admin-client
A tool used to administer the pulp server, such as repo creation and
synching, and to kick off remote actions on consumers.

%files admin-client
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/client/admin/
%{python_sitelib}/pulp_client_admin*.egg-info
%dir %{_sysconfdir}/%{name}/admin
%dir %{_sysconfdir}/%{name}/admin/conf.d
%{_sysconfdir}/bash_completion.d/pulp-admin
%dir %{_usr}/lib/%{name}/admin/extensions/
%config(noreplace) %{_sysconfdir}/%{name}/admin/admin.conf
%{_bindir}/%{name}-admin
%doc README LICENSE COPYRIGHT
%endif # End of pulp_admin if block


# ---- Consumer Client (CLI) ---------------------------------------------------

%package consumer-client
Summary: Consumer tool to administer the pulp consumer.
Group: Development/Languages
Requires: python-%{name}-common = %{pulp_version}
Requires: python-%{name}-bindings = %{pulp_version}
Requires: python-%{name}-client-lib = %{pulp_version}
Obsoletes: pulp-consumer
Obsoletes: pulp-builtins-consumer-extensions <= %{pulp_version}

%description consumer-client
A tool used to administer a pulp consumer.

%files consumer-client
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/client/consumer/
%{python_sitelib}/pulp_client_consumer*.egg-info
%dir %{_sysconfdir}/%{name}/consumer
%dir %{_sysconfdir}/%{name}/consumer/conf.d
%dir %{_sysconfdir}/pki/%{name}/consumer/
%dir %{_usr}/lib/%{name}/consumer/extensions/
%config(noreplace) %{_sysconfdir}/%{name}/consumer/consumer.conf
%{_bindir}/%{name}-consumer
%ghost %{_sysconfdir}/pki/%{name}/consumer/rsa.key
%ghost %{_sysconfdir}/pki/%{name}/consumer/rsa_pub.key
%ghost %{_sysconfdir}/pki/%{name}/consumer/server/rsa_pub.key
%ghost %{_sysconfdir}/pki/%{name}/consumer/consumer-cert.pem
%doc README LICENSE COPYRIGHT
%if 0%{?rhel} >= 6 || 0%{?fedora} >= 19
%{_sysconfdir}/bash_completion.d/pulp-consumer
%doc %{_mandir}/man1/pulp-consumer.1*
%endif


%post consumer-client

# RSA key pair
KEY_DIR="%{_sysconfdir}/pki/%{name}/consumer/"
KEY_PATH="$KEY_DIR/rsa.key"
KEY_PATH_PUB="$KEY_DIR/rsa_pub.key"
if [ ! -f $KEY_PATH ]
then
  openssl genrsa -out $KEY_PATH 2048 &> /dev/null
  openssl rsa -in $KEY_PATH -pubout > $KEY_PATH_PUB 2> /dev/null
fi
chmod 640 $KEY_PATH


# ---- Agent -------------------------------------------------------------------

%package agent
Summary: The Pulp agent
Group: Development/Languages
Requires: python-%{name}-bindings = %{pulp_version}
Requires: python-%{name}-agent-lib = %{pulp_version}
Requires: %{name}-consumer-client = %{pulp_version}
Requires: python-gofer >= 1.4.0
Requires: python-gofer-qpid >= 1.4.0
Requires: gofer >= 1.4.0
Requires: m2crypto

%description agent
The pulp agent, used to provide remote command & control and
scheduled actions such as reporting installed content profiles
on a defined interval.

%files agent
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/%{name}/agent/agent.conf
%{_sysconfdir}/gofer/plugins/pulpplugin.conf
%{_libdir}/gofer/plugins/pulpplugin.*
%doc README LICENSE COPYRIGHT

# --- Selinux ---------------------------------------------------------------------

%if %{pulp_server}
%package        selinux
Summary:        Pulp SELinux policy for pulp components.
Group:          Development/Languages
BuildRequires:  rpm-python
BuildRequires:  make
BuildRequires:  checkpolicy
BuildRequires:  selinux-policy-devel
BuildRequires:  hardlink
Obsoletes: pulp-selinux-server

%if "%{selinux_policyver}" != ""
Requires: selinux-policy >= %{selinux_policyver}
%endif
%if 0%{?fedora} == 19
Requires(post): selinux-policy-targeted >= 3.12.1-74
%endif
Requires(post): policycoreutils-python
Requires(post): /usr/sbin/semodule, /sbin/fixfiles, /usr/sbin/semanage
Requires(postun): /usr/sbin/semodule

%description    selinux
SELinux policy for Pulp's components

%post selinux
# Enable SELinux policy modules
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/enable.sh %{_datadir}
fi

# restorcecon wasn't reading new file contexts we added when running under 'post' so moved to 'posttrans'
# Spacewalk saw same issue and filed BZ here: https://bugzilla.redhat.com/show_bug.cgi?id=505066
%posttrans selinux
if /usr/sbin/selinuxenabled ; then
 %{_datadir}/pulp/selinux/server/relabel.sh %{_datadir}
fi

%preun selinux
# Clean up after package removal
if [ $1 -eq 0 ]; then
%{_datadir}/pulp/selinux/server/uninstall.sh
%{_datadir}/pulp/selinux/server/relabel.sh
fi
exit 0

%files selinux
%defattr(-,root,root,-)
%doc README LICENSE COPYRIGHT
%{_datadir}/pulp/selinux/server/*
%{_datadir}/selinux/*/pulp-server.pp
%{_datadir}/selinux/*/pulp-celery.pp
%{_datadir}/selinux/devel/include/%{moduletype}/pulp-server.if
%{_datadir}/selinux/devel/include/%{moduletype}/pulp-celery.if

%endif # End selinux if block

%changelog
* Fri Nov 21 2014 Chris Duryee <cduryee@redhat.com> 2.6.0-0.1.alpha
- 1162820 - Clarify SSL configuration settings. (rbarlow@redhat.com)
- 1116825 - Adding a non-existent user to a role now returns HTTP 400 instead
  of 404. (jcline@redhat.com)
- 1004623 - References to old collection names and content_unit_count needs to
  be updated (ipanova@redhat.com)
- 1021970 - Add an example how to retrieve permissions for a particular
  resource. (ipanova@redhat.com)
- 1128226 - Adjusting 'Repository Content Behavior' section name
  (ipanova@redhat.com)
- 1161205 - Adds comments to conf files about value of defaults
  (bmbouter@gmail.com)
- 1021579 - document unexpected behavior in unassociate api
  (cduryee@redhat.com)
- 1081534 - Added /v2 and trailing / to the permissions docs
  (dkliban@redhat.com)
- 1165271 - Adds 2.5.0 deprecation release note about _ns attribute
  (bmbouter@gmail.com)
- 1111261 - document single event listener retrieval (bcourt@redhat.com)
- 1161690 - Add release note for RabbitMQ support. (rbarlow@redhat.com)
- 1132663 - pulp-manage-db now has a --dry-run flag. (jcline@redhat.com)
- 721314 - add man pages for pulp-admin and pulp-consumer (cduryee@redhat.com)
- 1159067 - Read user cred from config (vijaykumar.jain@nomura.com)
- 1148928 - 404 is returned when publishing a nonexistent repo group
  (asmacdo@gmail.com)
- 1079511 - better relative url collision prevention (asmacdo@gmail.com)
- 1155513 - Search for package in all consumers (contact@andreagiardini.com)
- 1146294 - do not require pulp.bindings.server to access DEFAULT_CA_PATH
  (cduryee@redhat.com)
- 1121102 - support unordered agent replies. (jortel@redhat.com)
- 1160794 - update python-requests to 2.4.3 (cduryee@redhat.com)
- 1145734 - more correct error message when apache fails (asmacdo@gmail.com)
- 1127817 - return a 404 for consumer history request if consumer id does not
  exist (asmacdo@gmail.com)
- 1135589 - move PRIMARY_ID definition (cduryee@redhat.com)
- 1145723 - log startup message in Celery logs (cduryee@redhat.com)
- 1148919 - remove traceback from log if user enters incorrect password
  (asmacdo@gmail.com)
- 1148796 - pulp-admin tab completion follows plugin structure
  (igulina@redhat.com)
- 1132458 - cont - test now works outside of terminal (asmacdo@gmail.com)
- 1120671 - missing operation from reaper and monthly tasks
  (dkliban@redhat.com)
- 1129828 - split stack traces into separate log records. (jortel@redhat.com)
- 1142304 - remove extraneous errors during unit test runs (cduryee@redhat.com)
- 1139703 - update pickled schedule on schedule updates (cduryee@redhat.com)
- 1142376 - use valid default certificate pack path (cduryee@redhat.com)
- 1136504 - added tab completion for file paths (igulina@redhat.com)
- 1124589 - python-kombu does not work with Qpid unless the user adjusts
  qpidd.conf (cduryee@redhat.com)
- 1133953 - check Mongo version during startup (cduryee@redhat.com)
- 1095483 - fix message to not refer to pulp.log (cduryee@redhat.com)
- 1133939 - tab completion for short options (igulina@redhat.com)

* Mon Nov 17 2014 asmacdo <asmacdo@gmail.com> 2.5.0-0.19.rc
* Fri Nov 21 2014 Austin Macdonald <asmacdo@gmail.com> 2.5.0-1
- 1129488 - Adjusts mongoDB auto-reconnect to never stop attempting
  (bmbouter@gmail.com)
- 1160796 - Allow TCP connections to all hosts and ports (bmbouter@gmail.com)
- 1111228 - Fix API doc typo. (rbarlow@redhat.com)
- 1153344 - verify_ssl default to true. (rbarlow@redhat.com)
- 1153344 - Support Mongo SSL on the result backend. (rbarlow@redhat.com)
- 1153344 - Allow Mongo connections over SSL. (rbarlow@redhat.com)
- 1145701 - bump release to allow a koji rebuild (cduryee@redhat.com)
- 1117512 - Fix formatting of last_unit_added & last_unit_removed fields
  (bcourt@redhat.com)
- 1153054 - pulp.bindings refuse to do SSLv3. (rbarlow@redhat.com)
- 1102269 - Added documentation about deprecation of task_type
  (dkliban@redhat.com)
- 1150297 - Update versions from 2.4.x to 2.5.0. (rbarlow@redhat.com)
- 1060752 - Add sample output for repo import_upload (bcourt@redhat.com)
- 1146680 - Stop pulp_workers services with SIGQUIT. (rbarlow@redhat.com)
- 1131260 - Shell out to for certificate validation. (rbarlow@redhat.com)

* Mon Oct 20 2014 Randy Barlow <rbarlow@redhat.com> 2.4.3-1
- 1153054 - pulp.bindings refuse to do SSLv3. (rbarlow@redhat.com)

* Mon Oct 13 2014 Chris Duryee <cduryee@redhat.com> 2.4.2-1
- 1138356 - adding docs on how to backup pulp (mhrivnak@redhat.com)
- 1122987 - Adds troubleshooting note around Qpid scalability limits
  (bmbouter@gmail.com)
- 1066472 - Removed 409 response codes in docs for permission api calls
  (dkliban@redhat.com)
- 1103232 - Document common proxy config options. (rbarlow@redhat.com)
- 1081518 - Add help documentation for retrieving a single distributor or
  importer (bcourt@redhat.com)
- 1064150 - Creates a troubleshooting page that mentions inconsistency with
  trailing slashes (asmacdo@gmail.com)
- 1148555 - removes doubled 2.4.1 rest api changes from release notes
  (asmacdo@gmail.com)
- 1022188 - Docs about repos binding to nodes which were activated after
  deactivation (dkliban@redhat.com)
- 1145320 - document running pulp-manage-db after installation.
  (jortel@redhat.com)
- 1129489 - Document Apache CRLs. (rbarlow@redhat.com)
- 1096294 - Document the rsyslog log level settings. (rbarlow@redhat.com)
- 1087997 - add link to release note (cduryee@redhat.com)
- 1009429 - Move pulp_manage_puppet bool 2 celery_t. (rbarlow@redhat.com)
- 1134972 - remove calls to mongo flush (cduryee@redhat.com)
- 1132609 - celery result backend gets mongo username correctly
  (mhrivnak@redhat.com)
- 1131632 - Remove notes to disable SELinux in EL 5. (rbarlow@redhat.com)
- 1130119 - do not add full task info to spawned_tasks (cduryee@redhat.com)
- 1131509 - remove quotes from ca_path (cduryee@redhat.com)
- 1130153 - Fixed regression with consumer binding retrieval.
  (jcline@redhat.com)
- 1103914 - Pulp exceptions no longer log a traceback by default
  (jcline@redhat.com)
- 1128329 - Add warnings about admin.conf to docs. (rbarlow@redhat.com)
- 1128222 - Fixed a formatting issue in the installation docs
  (jcline@redhat.com)
- 1128831 - Restore python-rhsm-1.8.0. (rbarlow@redhat.com)
- 1094470 - Canceling a task that was already in a completed state now results
  in a 200 code instead of a 500 (jcline@redhat.com)
- 1110418 - Added documentation on publishing repository groups
  (jcline@redhat.com)
- 1111228 - Removed jdob from the event listener sample return
  (jcline@redhat.com)
- 1111197 - Fixed a typo in the sample request in event listeners docs
  (jcline@redhat.com)
- 1110449 - Fixed typos in context applicability documentation
  (jcline@redhat.com)
- 1094256 - Updated the consumer binding docs to make it clear a 200 can be
  returned (jcline@redhat.com)
- 1083522 - Updated the repo publish documentation to correct the schedule path
  (jcline@redhat.com)
- 1079445 - Updated the repo sync documentation to correct the schedule path
  (jcline@redhat.com)
- 1078348 - Updated the docs for updating an importer to make it clear that the
  task report contains the results (jcline@redhat.com)
- 1022553 - pulp-admin unbind commands will now return a user-friendly error
  message if the consumer or repository given don't exist. (jcline@redhat.com)
- 1112663 - Allows schedules with monthly or yearly intervals
  (jcline@redhat.com)
- 1109870 - fixed typo in passing tags when creating a task for deleting orphan
  by type (skarmark@redhat.com)
- 1092450 - Retrieving orphans by content type now returns a 404 if the content
  type does not exist (jcline@redhat.com)
- 1115414 - updated get consumer profiles api to return 404 in case of non-
  existing consumer (skarmark@redhat.com)
- 1115391 - removing duplicate unit test and updating one to detect 405 return
  code for consumer group bindings GET calls (skarmark@redhat.com)
- 1115385 - Removing GET methods on consumer group bindings since consumer
  group bind and unbind are merely used as group operations and are not stored
  on the consumer group permanently (skarmark@redhat.com)
- 1117512 - Convert timestamps saved for tracking distributor publishes &
  importer syncs to UTC instead of timezone offset (bcourt@redhat.com)
- 1100805 - Fixing consumer group bind and unbind and moving tasks from
  tasks/consumer_group.py to consumer group cud manager (skarmark@redhat.com)

* Tue Sep 23 2014 Randy Barlow <rbarlow@redhat.com> 2.4.1-1
- 1136883 - Fixed incorrect tags for applicability in the docs
  (jcline@redhat.com)
- 1131260 - Shell out to for certificate validation. (rbarlow@redhat.com)
- 1129719 - Raise the certificate validation depth. (rbarlow@redhat.com)
- 1131260 - relax version requirement. (jortel@redhat.com)
- 1130312 - Fix bug query for 2.4.1. (rbarlow@redhat.com)
- 1130312 - Add upgrade instructions for 2.4.1. (rbarlow@redhat.com)
- 1108306 - Update nectar to fix hang on canceling downloads of large numbers
  of files. (bcourt@redhat.com)
- 1093760 - pulp-manage-db now halts if a migration fails (jcline@redhat.com)

* Sat Aug 09 2014 Randy Barlow <rbarlow@redhat.com> 2.4.0-1
- 1125030 - Handle both styles of certificate stores. (rbarlow@redhat.com)
- 1113590 - Nodes requires Pulp's cert to be trusted 1112906 - pulp-admin
  requires Pulp's cert to be trusted 1112904 - pulp-consumer requires Pulp's
  cert to be trusted (rbarlow@redhat.com)
- 1110893 - adding a trailing slash to an API path (mhrivnak@redhat.com)
- 1115631 - discard disabled sources before doing is_valid check.
  (jortel@redhat.com)
- 1005899 - support 'message' reported during node sync. (jortel@redhat.com)
- 1113590 - Adding documentation about adding ca cert to the system trusted
  certs for pulp-admin and pulp-consumer and adding bindings unit tests
  (skarmark@redhat.com)
- 1112906 - adding SSL CA cert validation to the bindings (skarmark@redhat.com)
- 1112905 - updating pulp-gen-ca-certificate script to create pulp ssl
  certificates (skarmark@redhat.com)
- 1112904 - adding configuration for pulp ssl certificates
  (skarmark@redhat.com)
- 1110668 - updated consumer group binding documentation to refect the actual
  behaviour (jcline@redhat.com)
- 1117060 - added umask setting to celery worker command line, since the
  default of 0 is unsafe. (mhrivnak@redhat.com)
- 1116438 - use apache httpd type and not typealias (lzap+git@redhat.com)
- 1115715 - syslog handler works with string formatting tokens in tracebacks.
  (jortel@redhat.com)
- 1115631 - disabled content sources discarded before validity check performed.
  (jortel@redhat.com)
- 1115129 - update rsa_pub as part of consumer updates. (jortel@redhat.com)
- 1093871 - sorting tasks by default according to when they were created.
  (mhrivnak@redhat.com)
- 1100638 - Update task search API to match the serialization used for task
  collection & task get APIs (bcourt@redhat.com)
- 1110674 - A 400 Bad Request is returned when attempting to bind a consumer
  group to an invalid repo or distributor id (jcline@redhat.com)
- 1104654 - Don't require python-oauth2 on RHEL 5. (rbarlow@redhat.com)
- 1020912 - add pulp_manage_puppet selinux boolean (lzap+git@redhat.com)
- 1110668 - consumer group binding calls now return 404 when invalid group,
  repo, or distributor ids are given (jcline@redhat.com)
- 1074426 - Updated the repository group API docs to reflect actual DELETE
  behaviour (jcline@redhat.com)
- 1109430 - goferd supporting systemd. (jortel@redhat.com)
- 1105636 - saving a unit through a conduit now fails over to adding or
  updating if a unit appears or disappears unexpectedly (mhrivnak@redhat.com)
- 1094286 - failing to include 'options' or 'units' during content
  install/update/uninstall calls on consumers now results in a 400 code
  (jcline@redhat.com)
- 1100805 - Fixing consumer group bind and unbind and moving tasks from
  tasks/consumer_group.py to consumer group cud manager (skarmark@redhat.com)
- 1094264 - Retrieving bindings by consumer and repository now returns 404 if
  the consumer or repository ids are invalid. (jcline@redhat.com)
- 1060866 - The Repository Group Distributors API is now documented
  (jcline@redhat.com)
- 1097781 - Indicate that consumer bind fails when it does.
  (rbarlow@redhat.com)
- 1107782 - fixed in gofer 1.2.1. (jortel@redhat.com)
- 1102393 - Rework how we select the queue for new reservations.
  (rbarlow@redhat.com)
- 1100892 - check if filename exists before printing (cduryee@redhat.com)
- 1100330 - Improve error message and documentation. (rbarlow@redhat.com)
- 1102236 - pass the authenticator to the reply consumer. (jortel@redhat.com)
- 1099272 - bump mongodb version requirement in docs (cduryee@redhat.com)
- 1098620 - Report NoAvailableQueues as a coded Exception. (rbarlow@redhat.com)
- 1101598 - returns the correct data type when copy matches 0 units
  (mhrivnak@redhat.com)
- 1097247 - Add status to pulp_celerybeat script. (rbarlow@redhat.com)
- 1100084 - read consumer.conf during setup_plugin(). (jortel@redhat.com)
- 1099945 - use correct serializer when publishing http events
  (cduryee@redhat.com)
- 1096931 - improving repo update command to better detect spawned tasks
  (mhrivnak@redhat.com)
- 1051700 - Don't build pulp-admin on RHEL 5. (rbarlow@redhat.com)
- 1096822 - Don't set a canceled Task to finished. (rbarlow@redhat.com)
- 1099168 - move %%postun block inside pulp_server if block
  (cduryee@redhat.com)
- 1096935 - Adds info about qpid-cpp-server-store package to docs
  (bmbouter@gmail.com)
- 1091980 - Update install and upgrade docs with qpid client deps
  (bmbouter@gmail.com)
- 1096968 - return created profile; log reported profiles at debug in the
  agent. (jortel@redhat.com)
- 1094647 - GET of consumer schedule that doesn't exist now returns 404
  (mhrivnak@redhat.com)
- 1097817 - agent SSL properties applied. (jortel@redhat.com)
- 1093870 - Use far less RAM during publish. (rbarlow@redhat.com)
- 1093009 - Don't use symlinks for init scripts. (rbarlow@redhat.com)
- 1091348 - Always perform distributor updates asyncronously.
  (rbarlow@redhat.com)
- 1094825 - bind/unbind return call_report; 200/202 based on spawned tasks.
  (jortel@redhat.com)
- 1095691 - Adding cleanup of Celery Task Results to Reaper
  (bmbouter@gmail.com)
- 1093429 - Changing repo create API to match documented key name.
  (mhrivnak@redhat.com)
- 1094637 - fixing consumer schedule API urls in the documentation
  (mhrivnak@redhat.com)
- 1094653 - correctly handling the case where an invalid schedule ID is
  provided to the REST API (mhrivnak@redhat.com)
- 1087514 - correct dev-guide for create/update user. (jortel@redhat.com)
- 1091922  - Fix _delete_queue() traceback. (bmbouter@gmail.com)
- 1093417 - propagate transport configuration property. (jortel@redhat.com)
- 1086278 - Convert upload into a polling command. (rbarlow@redhat.com)
- 1091919 - agent load rsa keys on demand. (jortel@redhat.com)
- 1090570 - Fix content commands handling of returned call report.
  (jortel@redhat.com)
- 1073065 - Better document task cancellations. (rbarlow@redhat.com)
- 1072955 - Create TaskStatuses with all attributes. (rbarlow@redhat.com)
- 1087015 - Capture warnings with the pulp logger (bmbouter@gmail.com)
- 1091530 - fix rendering a progress report = None. (jortel@redhat.com)
- 1091090 - alt-content sources updated to work with nectar 1.2.1.
  (jortel@redhat.com)
- 1073999 - removing result from task list and adding it to the task details
  (skarmark@redhat.com)
- 1069909 - Don't run server code on EL5 for pulp-dev.py. (rbarlow@redhat.com)
- 1074670 - Save initialize & finalize in step processing even if no units are
  processed. (bcourt@redhat.com)
- 1080609 - pulp-manage-db now ensures the admin. (rbarlow@redhat.com)
- 1087863 - Fix progress reporting in node sync command. (jortel@redhat.com)
- 1087633 - Fix bind task to support node binding. (jortel@redhat.com)
- 1084716 - Register with Celery's setup_logging. (rbarlow@redhat.com)
- 1086437 - Fixes consumer reregistration. (jortel@redhat.com)
- 1065450 - updating repo delete api docs for responses (skarmark@redhat.com)
- 1080647 - added validation that a unit profile is not None before requesting
  applicability regeneration by repos (skarmark@redhat.com)
- 1061783 - added missing example for the consumer group update api
  documentation (skarmark@redhat.com)
- 1074668 - updated consumer group update api docs to remove consumer_ids from
  acceptable parameters (skarmark@redhat.com)
- 1073997 - adding validation to repo group create call to check for valid repo
  ids (skarmark@redhat.com)
- 1085545 - Fix permissions on /etc/pulp/server/plugins.conf.d/nodes/importer.
  (jortel@redhat.com)
- 1082130 - Update progress only when task_id != None. (jortel@redhat.com)
- 1082064 - task status created with state=WAITING when None is passed.
  (jortel@redhat.com)
- 1080642 - updated consumer unbind task to mark the binding deleted before
  notifying agent (skarmark@redhat.com)
- 1080626 - updated agent manager to return no exception when converting server
  bindings to agent bindings in case distributor is already deleted on the
  server (skarmark@redhat.com)
- 1080626 - fixing error in the error code description preventing to complete
  repo delete on the server (skarmark@redhat.com)
- 965764 - Fix a test for the DownloaderConfig API. (rbarlow@redhat.com)
- 1015583 - added a new api so that consumers can request applicability
  generation for themselves (skarmark@redhat.com)
- 1078335 - Add import statements for missing tasks. (rbarlow@redhat.com)
- 1073154 - Do not log newlines or long messages. (rbarlow@redhat.com)
- 1074661 - Raise a validation error if non-existant consumers are specified
  during creation of a consumer group (bcourt@redhat.com)
- 1078305 - Repo update not reporting errors properly.  Fix error response for
  repo update and incorrect documentation for the udpate call.
  (bcourt@redhat.com)
- 1076225 - Update docs to include information about the result value of the
  Task Report as opposed to the Call Report (bcourt@redhat.com)
- 1076628 - Fix base class for unassociate task and update test case for unit
  deletion (bcourt@redhat.com)
- 1018183 - Include _href's on tasks during GET all. (rbarlow@redhat.com)
- 1075701 - Re-enable Celery log capturing. (rbarlow@redhat.com)
- 1071960 - Support message authentication. Port pulp to gofer 1.0. Removed
  timeouts for agent related tasks. (jortel@redhat.com)
- 1066040 - removing 'permissions' from valid update keywords for role update,
  moving manager functionality out of authorization.py, removing duplicate
  declaration of permission operation constants in permission.py and adding
  missing unit tests (skarmark@redhat.com)
- 980150 - support broker host that is different than pulp host.
  (jortel@redhat.com)
- 1058835 - Fix documentation of URL path for deletion of upload requests.
  (bcourt@redhat.com)
- 1042932 - Fix listings bug & enable export repo group support for celery
  (bcourt@redhat.com)
- 1046160 - taking ownership of /var/lib/pulp/published (mhrivnak@redhat.com)
- 1051700 - Documenting that pulp-admin is not supported on RHEL5
  (mhrivnak@redhat.com)
- 1051700 - adding an explicit requirement for python 2.6 to pulp-admin-client
  (mhrivnak@redhat.com)
- 1048297 - pulp-dev.py sets the CA cert and key world readable.
  (rbarlow@redhat.com)
- 921743 - Adjust ownership and permissions for a variety of the RPM paths.
  (rbarlow@redhat.com)
- 1034978 - Add visible errors to the unit associate and unassociate commands
  and move formatting the cli output to the base class instead of each plugin
  having to work independently (bcourt@redhat.com)
- 1039619 - update output to account for qpidd.conf location changing in qpid
  0.24 (jortel@redhat.com)
- 1005899 - report errors fetching bindings from the parent in the report.
  (jortel@redhat.com)
- 1031220 - raising an AttributeError when an attribute is missing on a Model
  (mhrivnak@redhat.com)
- Add support for alternate content sources. (jortel@redhat.com)
- 995076 - make sure to call finalize on the nectar config object
  (jason.connor@gmail.com)
- 1032189 - fixed use of gettext with multiple substitutions
  (mhrivnak@redhat.com)
- 1020300 - Prevent hashed password from being returned by the get user
  command. (bcourt@redhat.com)
- 1019155 - added logic to correctly set the URL when called from any
  /bindings/ URLs (jason.connor@gmail.com)
- 1029057 - have nodes replicate the repository scratchpad. (jortel@redhat.com)
- 1022646 - remove units_path; in 2.3, it's method. (jortel@redhat.com)
- 1026606 - Added docs for get unit REST API (jason.dobies@redhat.com)
- 996606 - Check to see if a repo exists before starting upload process
  (jason.dobies@redhat.com)

* Wed Nov 06 2013 Jeff Ortel <jortel@redhat.com> 2.3.0-1
- 1027500 - init python-gofer before agent and tasking services started.
  (jortel@redhat.com)
- 1022646 - migration_0 needs to add units_size=0. (jortel@redhat.com)
- 1023056 - fix SSL on f19 by using qpid builtin SSL transport.
  (jortel@redhat.com)
- 1022646 - fix migration of nodes 2.2 => 2.3 manifests. (jortel@redhat.com)
- 1022621 - Failed reports are now successful tasks and the report indicates
  the failure (jason.dobies@redhat.com)
- 1022621 - Fixed communication between publish manager and tasking
  (jason.dobies@redhat.com)
- 1017587 - Added a list of possible task states to the docs.
  (rbarlow@redhat.com)
- 1017865 - Corrected task response docs (jason.dobies@redhat.com)
- 1021116 - Convert info level log messages that include Task arguments into
  debug level messages. (rbarlow@redhat.com)
- 1017253 - Removed v1 attribute that no longer exists
  (jason.dobies@redhat.com)
- 1019909 - Added replica set support (jason.dobies@redhat.com)
- 1020549 - tar the content of the distribution directory instead of the
  directory. (jortel@redhat.com)
- 1019455 - Loosened validation checks on the presence of the feed for certain
  configuration parameters (jason.dobies@redhat.com)
- 1011716 - updated spec file to add selinux-policy-targeted dependency for f19
  and removing wrong version dependency on policycoreutils-python
  (skarmark@redhat.com)
- 973678 - Add support for reporting unit upload statuses to the API and CLI.
  (rbarlow@lemonade.usersys.redhat.com)
- 975503 - Add status command to iso publish (bcourt@redhat.com)
- 1017924 - unzip the units.json instead of reading/seeking using gzip.
  (jortel@redhat.com)
- 1017815 - Added logging about publish success and failure
  (mhrivnak@redhat.com)
- 965283 - Document the response for a repo importer delete (bcourt@redhat.com)
- 1014368 - added python-requests-2.0.0 package to pulp dependencies in order
  to support proxy with https (skarmark@redhat.com)
- 1009617 - limit options for repo sync and publish history now states the
  default limit is 5 (einecline@gmail.com)
- 965283 - updating the REST API docs for repo updates as they pertain to
  importers and distributors (mhrivnak@redhat.com)
- 1004805 - pulp-dev.py now looks at the apache version instead of the linux
  distribution version when deciding which config file to install, since the
  apache version is really what matters. (mhrivnak@redhat.com)
- 1014660 - Add command line parsers for numerics & booleans that return empty
  strings for empty values because None is interpreted by the rest api as
  having the value not specified (bcourt@redhat.com)
- 999129 - removing loading of tracker files at the time of initializing upload
  manager and adding it when listing remaining uploads (skarmark@redhat.com)
- 1010292 - serialize _last_modified only when it exists. (jortel@redhat.com)
- 1010016 - blacklist options; require gofer 0.77 which logs messages at DEBUG.
  (jortel@redhat.com)
- 1011972 - fixed in nectar 1.1.2. (jortel@redhat.com)
- 952748 - adding documentation about how to use a UnitAssociationCriteria with
  the REST API. (mhrivnak@redhat.com)
- 1009926 - Fix Exception thrown on applicability generation
  (bcourt@redhat.com)
- 1013097 - permit (.) in node IDs. (jortel@redhat.com)
- 1011268 - Add support for SHA hash which is an alias for SHA1
  (bcourt@redhat.com)
- 721314 - including the README and LICENSE files in all platform packages.
  Also tweaked the README. (mhrivnak@redhat.com)
- 988119 - Convert Python types (list,dict) to JSON types (array, object) in
  api documentation (bcourt@redhat.com)
- 1011053 - Add a from_dict() method to the Criteria model.
  (rbarlow@redhat.com)
- 1012636 - fix post script. (jortel@redhat.com)
- 976435 - load puppet importer config from a file using a common method.
  (bcourt@redhat.com)
- 1004559 - python-simplejson is now required by pulp-common on rhel5. this
  also removes any direct imports of simplejson from outside the pulp-common
  package. (mhrivnak@redhat.com)
- 1011728 - encode unicode values in oauth header. (jortel@redhat.com)
- 975980 - When a repository is updated, push an udpate to all of the
  distributors that depend on the repo. (bcourt@redhat.com)
- 1009912 - removing pymongo dependency for consumers by using actual constants
  instead of importing pymongo in common/constants.py (skarmark@redhat.com)
- 1003326 - generate pulp CA on initial install. (jortel@redhat.com)
- 906039 - do not allow the running weigt to drop below 0
  (jason.connor@gmail.com)
- 1009617 - Fixed the limit option in 'pulp-admin repo history publish'
  (einecline@gmail.com)
- 965751 - migrate nodes to use threaded downloader. (jortel@redhat.com)
- 1009118 - bindings require python-oauth. (jortel@redhat.com)
- 1004346 - deal with bindings w (None) as binding_config. (jortel@redhat.com)
- 995528 - Remove legacy usage of AutoReference as it has a significant
  performance impact on queries of larger repositories and is no longer being
  used. (bcourt@redhat.com)
- 1004790 - Remove legacy dependency on Grinder that is no longer required.
  (bcourt@redhat.com)
- 993424 - forced unbind when bindings have notify_agent=False
  (jortel@redhat.com)
- 959031 - 968524 - rewritten scheduler that fixes bug in subsequent schedule
  runs and allows next_run to be updated when upating the schedule of a
  scheduled_call (jason.connor@gmail.com)
- 1005898 - Remove unnecessary dependency on gofer in pulp-nodes.spec file
  (bcourt@redhat.com)
- 1003285 - fixed an attribute access for an attribute that doesn't exist in
  python 2.6. (mhrivnak@redhat.com)
- 1004897 - Fix bug where distributor validate_config is finding relative path
  conflicts with the repository that is being updated (bcourt@redhat.com)
- 952737 - updated repo creation documentation with parameters to configure
  importers and distributors (skarmark@redhat.com)
- 915330 - Fix performance degradation of importer and distributor
  configuration validation as the number of repositories increased
  (bcourt@redhat.com)
- 956711 - Raise an error to the client if an attempt is made to install an
  errata that does not exist in a repository bound to the consumer
  (bcourt@redhat.com)
- 991500 - updating get_repo_units conduit call to return plugin units instead
  of dictionary (skarmark@redhat.com)
- 976561 - updated the list of decorated collection methods to match the
  Collection object in 2.1.1 (jason.connor@gmail.com)
- 976561 - removed superfluous re-fetching of collection we already have a
  handle to (jason.connor@gmail.com)
- 976561 - added and explicit pool size for the socket "pool" added a new
  decorator around the query methods that calls end_request in order to manage
  the sockets automagically (jason.connor@gmail.com)
- 981736 - when a sync fails, pulp-admin's exit code is now 1 instead of 0.
  (mhrivnak@redhat.com)
- 977948 - fix distributor updating during node sync. (jortel@redhat.com)
- purge changelog
- 973402 - Handle CallReport.progress with value of {} or None.
  (jortel@redhat.com)
- 927216  - remove reference to CDS in the server.conf security section.
  (jortel@redhat.com)
- 928413 - fix query used to determine of bind has pending actions.
  (jortel@redhat.com)
- 970741 - Upgraded nectar for error_msg support (jason.dobies@redhat.com)
- 968012 - Replaced grinder logging config with nectar logging config
  (jason.dobies@redhat.com)

* Tue Jun 04 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-1
- 947445 - allowing consumer ids to allow dots (skarmark@redhat.com)
- 906420 - update storing of resources used by each task in the taskqueue to
  allow dots in the repo id (skarmark@redhat.com)
- 906420 - update storing of resources used by each task in the taskqueue to
  allow dots in the repo id (skarmark@redhat.com)
- 968543 - remove conditional in pulp_version macro. (jortel@redhat.com)
- 927033 - added missing consumer group associate and unassociate webservices
  tests (skarmark@redhat.com)
- 927033 - updating consumer group associate and unassociate calls to return a
  list of all consumers similar to repo group membership instead of just those
  who fulfil the search criteria, updating unit tests and documentation
  (skarmark@redhat.com)
- 965743 - Changed help text to reflect the actual units
  (jason.dobies@redhat.com)
- 963823 - Made the feed SSL options group name a bit more accurate
  (jason.dobies@redhat.com)
- 913670 - fix consumer group bind/unbind. (jortel@redhat.com)
- 878234 - use correct method on coordinator. (jortel@redhat.com)
- 966202 - Change the config options to use the optional parsers.
  (jason.dobies@redhat.com)
- 923796 - Changed example to not cite a specific command
  (jason.dobies@redhat.com)
- 952775 - Fixed broken unit filter application when sorted by association
  (jason.dobies@redhat.com)
- 913171 - using get method instead of dict lookup (skarmark@redhat.com)
- 915473 - fixing login api to return a json document with key and certificate
  (skarmark@redhat.com)
- 913171 - fixed repo details to display list of actual schedules instead of
  schedule ids and unit tests (skarmark@redhat.com)
- 957890 - removing duplicate units in case when consumer is bound to copies of
  same repo (skarmark@redhat.com)
- 957890 - fixed duplicate unit listing in the applicability report and
  performance improvement fix to avoid loading unnecessary units
  (skarmark@redhat.com)
- 954038 - updating applicability api to send unit ids instead of translated
  plugin unit objects to profilers and fixing a couple of performance issues
  (skarmark@redhat.com)
- 924778 - Added hook for a subclass to manipulate the file bundle list after
  the metadata is generated (jason.dobies@redhat.com)
- 916729 - Fixed auth failures to return JSON documents containing a
  programmatic error code and added client-side exception middleware support
  for displaying the proper user message based on the error.
  (jason.dobies@redhat.com)
- 887000 - removed dispatch lookups in sync to determine canceled state
  (jason.connor@gmail.com)
- 927244 - unit association log blacklist criteria (jason.connor@gmail.com)
- 903414 - handle malformed queued calls (jason.connor@gmail.com)
- 927216 - remove CDS section from server.conf. (jortel@redhat.com)
- 953665 - added ability for copy commands to specify the fields of their units
  that should be fetched, so as to avoid loading the entirety of every unit in
  the source repository into RAM. Also added the ability to provide a custom
  "override_config" based on CLI options. (mhrivnak@redhat.com)
- 952310 - support file:// urls. (jortel@redhat.com)
- 949174 - Use a single boolean setting for whether the downloaders should
  validate SSL hosts. (rbarlow@redhat.com)
- 950632 - added unit_id search index on the repo_content_units collection
  (jason.connor@gmail.com)
- 928081 - Take note of HTTP status codes when downloading files.
  (rbarlow@redhat.com)
- 947927 - This call should support both the homogeneous and heterogeneous
  cases (jason.dobies@redhat.com)
- 928509 - Platform changes to support override config in applicability
  (jason.dobies@redhat.com)
- 949186 - Removed the curl TIMEOUT setting and replaced it with a low speed
  limit. (rbarlow@redhat.com)
- 928087 - serialized call request replaced in archival with string
  representation of the call request (jason.connor@gmail.com)
- 924327 - Make sure to run the groups/categories upgrades in the aggregate
  (jason.dobies@redhat.com)
- 918160 - changed --summary flag to *only* display the  summary
  (jason.connor@gmail.com)
- 916794 - 918160 - 920792 - new generator approach to orphan management to
  keep us from stomping on memory (jason.connor@gmail.com)
- 923402 - Clarifications to the help text in logging config files
  (jason.dobies@redhat.com)
- 923402 - Reduce logging level from DEBUG to INFO (jason.dobies@redhat.com)
- 923406 - fixing typo in repo copy bindings causing recursive copy to never
  run (skarmark@redhat.com)
- 922214 - adding selinux context for all files under /srv/pulp instead of
  individual files (skarmark@redhat.com)
- 919155 - Added better test assertions (jason.dobies@redhat.com)
- 919155 - Added handling for connection refused errors
  (jason.dobies@redhat.com)
- 918782 - render warning messages as normal colored text. (jortel@redhat.com)
- 911166 - Use pulp_version macro for consistency and conditional requires on
  both version and release for pre-release packages only. (jortel@redhat.com)
- 908934 - Fix /etc/pki/pulp and /etc/pki/pulp/consumer ownership.
  (jortel@redhat.com)
- 918600 - _content_type_id wasn't being set for erratum and drpm
  (jason.dobies@redhat.com)

* Mon Mar 04 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-1
- 855053 - repository unit counts are now tracked per-unit-type. Also wrote a
  migration that will convert previously-created repositories to have the new
  style of unit counts. (mhrivnak@redhat.com)
- 902514 - removing NameVirtualHost because we weren't using it, and adding one
  authoritative <VirtualHost *:80> block for all plugins to use, since apache
  will only let us use one. (mhrivnak@redhat.com)
- 873782 - added non-authenticate status resource at /v2/status/
  (jason.connor@gmail.com)
- 860089 - added ability to filter tasks using ?id=...&id=...
  (jason.connor@gmail.com)
- 915795 - Fix logging import statemet in pulp-manage-db. (rbarlow@redhat.com)
- 908676 - adding pulp-v1-upgrade-selinux script to enable new selinux policy
  and relabel filesystem after v1 upgrade (skarmark@redhat.com)
- 908676 - adding obsoletes back again for pulp-selinux-server since pulp v1
  has a dependency on this package (skarmark@redhat.com)
- 909493 - adding a separate apache2.4 compatible pulp apache conf file for F18
  (skarmark@redhat.com)
- 909493 - adding a different httpd2.4 compatible pulp config file for f18
  build (skarmark@redhat.com)
- 908676 - make pulp-selinux conflict with pulp-selinux-server instead of
  obsoleting pulp-selinux-server (skarmark@redhat.com)
- 913205 - Removed config options if they aren't relevant
  (jason.dobies@redhat.com)
- 913205 - Corrected storage of feed certificates on upgrade
  (jason.dobies@redhat.com)
- 910419 - added *args and **kwargs to OPTIONS signature to handle regular
  expressions in the url path (jason.connor@gmail.com)
- 906426 - Create the upload directory if someone deletes it
  (jason.dobies@redhat.com)
- 910540 - fix file overlaps in platform packaging. (jortel@redhat.com)
- 908510 - Corrected imports to use compat layer (jason.dobies@redhat.com)
- 908082 - updated SSLRenegBufferSize in apache config to 1MB
  (skarmark@redhat.com)
- 903797 - Corrected docstring for import_units (jason.dobies@redhat.com)
- 905588 - Adding "puppet_module" as an example unit type. This should not
  become a list of every possible unit type, but it's not unreasonable here to
  include some mention of puppet modules. (mhrivnak@redhat.com)
- 880780 - Added config parsing exception to convey more information in the
  event the conf file isn't valid JSON (jason.dobies@redhat.com)
- 905548 - fix handler loading; imp.load_source() supports .py files only.
  (jortel@redhat.com)
- 903387 - remove /var/lib/pulp/(packages|repos) and /var/lib/pulp/published
  (jortel@redhat.com)
- 878234 - added consumer group itineraries and updated group content install
  apis to return a list of call requests, also added unit tests
  (skarmark@redhat.com)
- 888058 - Changed model for the client-side exception handler to be overridden
  and specified to the launcher, allowing an individual client (admin,
  consumer, future other) to customize error messages where relevant.
  (jason.dobies@redhat.com)
- 891423 - Added conduit calls to be able to create units on copy
  (jason.dobies@redhat.com)
- 894467 - Parser methods need to return the value, not just validate it
  (jason.dobies@redhat.com)
- 889893 - added detection of still queued scheduled calls and skip re-
  enqueueing with log message (jason.connor@gmail.com)
- 883938 - Bumped required version of okaara in the spec
  (jason.dobies@redhat.com)
- 885128 - Altered two more files to use the 'db' logger. (rbarlow@redhat.com)
- 885128 - pulp.plugins.loader.api should use the "db" logger.
  (rbarlow@redhat.com)
- 891423 - Added conduit calls to be able to create units on copy
  (jason.dobies@redhat.com)
- 891760 - added importer and distributor configs to kwargs and
  kwargs_blacklist to prevent logging of sensitive data
  (jason.connor@gmail.com)
- 889320 - updating relabel script to run restorecon on /var/www/pulp_puppet
  (skarmark@redhat.com)
- 889320 - adding httpd_sys_content_rw_t context to /var/www/pulp_puppet
  (skarmark@redhat.com)
- 887959 - Removing NameVirtualHost entries from plugin httpd conf files and
  adding it only at one place in main pulp.conf (skarmark@redhat.com)
- 886547 - added check for deleted schedule in scheduled call complete callback
  (jason.connor@gmail.com)
- 882412 - Re-raising PulpException upon upload error instead of always
  replacing exceptions with PulpExecutionException, the latter of which results
  in an undesirable 500 HTTP response. (mhrivnak@redhat.com)
- 875843 - added post sync/publish callbacks to cleanup importer and
  distributor instances before calls are archived (jason.connor@gmail.com)
- 769381 - Fixed delete confirmation message to be task centric
  (jason.dobies@redhat.com)
- 856762 - removing scratchpads from repo search queries (skarmark@redhat.com)
- 886148 - used new result masking to keep full consumer package profiles from
  showing up in the task list and log file (jason.connor@gmail.com)
- 856762 - removing scratchpad from the repo list --details commmand for repo,
  importer and distributor (skarmark@redhat.com)
- 883899 - added conflict detection for call request groups in the webservices
  execution wrapper module (jason.connor@gmail.com)
- 876158 - Removed unused configuration values and cleaned up wording and
  formatting of the remaining options (jason.dobies@redhat.com)
- 882403 - Flushed out the task state to user display mapping as was always the
  intention but never actually came to fruition. (jason.dobies@redhat.com)
- 882422 - added the distributor_list keyword argument to the call requets
  kwarg_blacklist to prevent it from being logged (jason.connor@gmail.com)
- 885229 - add requires: nss-tools. (jortel@redhat.com)
- 885098 - Use a separate logging config for pulp-manage-db.
  (rbarlow@redhat.com)
- 885134 - Added check to not parse an apache error as if it has the Pulp
  structure and handling in the exception middleware for it
  (jason.dobies@redhat.com)
- 867464 - Renaming modules to units and a fixing a few minor output errors
  (skarmark@redhat.com)
- 882421 - moving unit remove command into the platform from RPM extensions so
  it can be used by other extension families (mhrivnak@redhat.com)
- 877147 - added check for path type when removing orphans
  (jason.connor@gmail.com)
- 882423 - fix upload in repo controller. (jortel@redhat.com)
- 883568 - Reworded portion about recurrences (jason.dobies@redhat.com)
- 883754 - The notes option was changed to have a parser, but some code using
  it was continuing to manually parse it again, which would tank.
  (jason.dobies@redhat.com)
- 866996 - Added ability to hide the details link on association commands when
  it isn't a search. (jason.dobies@redhat.com)
- 877797 - successful call of canceling a task now returns a call report
  through the rest api (jason.connor@gmail.com)
- 867464 - updating general module upload command output (skarmark@redhat.com)
- 882424 - only have 1 task, presumedly the "main" one, in a task group update
  the last_run field (jason.connor@gmail.com)
- 883059 - update server.conf to make server_name optional
  (skarmark@redhat.com)
- 883059 - updating default server config to lookup server hostname
  (skarmark@redhat.com)
- 862187 /var/log/pulp/db.log now includes timestamps. (rbarlow@redhat.com)
- 883025 - Display note to copy qpid certificates to each consumer.
  (jortel@redhat.com)
- 880441 - Fixed call to a method that was renamed (jason.dobies@redhat.com)
- 881120 - utilized new serialize_result call report flag to hide consumer key
  when reporting the task information (jason.connor@gmail.com)
- 882428 - utilizing new call report serialize_result flag to prevent the call
  reports from being serialized and reported over the rest api
  (jason.connor@gmail.com)
- 882401 - added skipped as a recognized state to the cli parser
  (jason.connor@gmail.com)
- 862290 - Added documentation for the new ListRepositoriesCommand methods
  (jason.dobies@redhat.com)
- 881639 - more programmatic. (jortel@redhat.com)
- 881389 - fixed rpm consumer bind to raise an error on non existing repos
  (skarmark@redhat.com)
- 827620 - updated repo, repo_group, consumer and user apis to use execute
  instead of execute_ok (skarmark@redhat.com)
- 878620 - fixed task group resource to return only tasks in the group instead
  of all tasks ever run... :P (jason.connor@gmail.com)
- 866491 - Change the source repo ID validation to be a 400, not 404
  (jason.dobies@redhat.com)
- 866491 - Check for repo existence and raise a 404 if not found instead of
  leaving the task to do it (jason.dobies@redhat.com)
- 881120 - strip the private key from returned consumer object.
  (jortel@redhat.com)
- 862290 - Added support in generic list repos command for listing other
  repositories (jason.dobies@redhat.com)
- 877914 - updating old file links from selinux installation and un-
  installation (skarmark@redhat.com)
- 873786 - updating enable.sh for correct amqp ports (skarmark@redhat.com)
- 878654 - fixed error message when revoking permission from a non-existing
  user and added unit tests (skarmark@redhat.com)
- added database collection reaper system that will wake up periodically and
  remove old documents from configured collections (jason.connor@gmail.com)
- 876662 - Added middleware exception handling for when the client cannot
  resolve the server hostname (jason.dobies@redhat.com)
- 753680 - Taking this opportunity to quiet the logs a bit too
  (jason.dobies@redhat.com)
- 753680 - Increased the logging clarity and location for initialization errors
  (jason.dobies@redhat.com)
- 871858 - Implemented sync and publish status commands
  (jason.dobies@redhat.com)
- 873421 - changed a wait-time message to be more appropriate, and added a bit
  of function parameter documentation. (mhrivnak@redhat.com)
- 877170 - Added ability to ID validator to handle multiple inputs
  (jason.dobies@redhat.com)
- 877435 - Pulled the filters/order to constants and use in search
  (jason.dobies@redhat.com)
- 875606 - Added isodate and python-setuptools deps. Rolled into a quick audit
  of all the requirements and changed quite a few. There were several missing
  and several no longer applicaple. Also removed a stray import of okaara from
  within the bindings package. (mhrivnak@redhat.com)
- 874243 - return 404 when profile does not exist. (jortel@redhat.com)
- 876662 - Added pretty error message when the incorrect server hostname is
  used (jason.dobies@redhat.com)
- 876332 - add missing tags to bind itinerary. (jortel@redhat.com)

* Thu Dec 20 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-1
- 887959 - Removing NameVirtualHost entries from plugin httpd conf files and
  adding it only at one place in main pulp.conf (skarmark@redhat.com)
- 886547 - added check for deleted schedule in scheduled call complete callback
  (jason.connor@gmail.com)
- 882412 - Re-raising PulpException upon upload error instead of always
  replacing exceptions with PulpExecutionException, the latter of which results
  in an undesirable 500 HTTP response. (mhrivnak@redhat.com)
- 875843 - added post sync/publish callbacks to cleanup importer and
  distributor instances before calls are archived (jason.connor@gmail.com)
- 769381 - Fixed delete confirmation message to be task centric
  (jason.dobies@redhat.com)
- 856762 - removing scratchpads from repo search queries (skarmark@redhat.com)
- 886148 - used new result masking to keep full consumer package profiles from
  showing up in the task list and log file (jason.connor@gmail.com)
- 856762 - removing scratchpad from the repo list --details commmand for repo,
  importer and distributor (skarmark@redhat.com)
- 883899 - added conflict detection for call request groups in the webservices
  execution wrapper module (jason.connor@gmail.com)
- 876158 - Removed unused configuration values and cleaned up wording and
  formatting of the remaining options (jason.dobies@redhat.com)
- 882403 - Flushed out the task state to user display mapping as was always the
  intention but never actually came to fruition. (jason.dobies@redhat.com)
- 882422 - added the distributor_list keyword argument to the call requets
  kwarg_blacklist to prevent it from being logged (jason.connor@gmail.com)
- 885229 - add requires: nss-tools. (jortel@redhat.com)
- 885098 - Use a separate logging config for pulp-manage-db.
  (rbarlow@redhat.com)
- 885134 - Added check to not parse an apache error as if it has the Pulp
  structure and handling in the exception middleware for it
  (jason.dobies@redhat.com)
- 867464 - Renaming modules to units and a fixing a few minor output errors
  (skarmark@redhat.com)
- 882421 - moving unit remove command into the platform from RPM extensions so
  it can be used by other extension families (mhrivnak@redhat.com)
- 877147 - added check for path type when removing orphans
  (jason.connor@gmail.com)
- 882423 - fix upload in repo controller. (jortel@redhat.com)
- 883568 - Reworded portion about recurrences (jason.dobies@redhat.com)
- 883754 - The notes option was changed to have a parser, but some code using
  it was continuing to manually parse it again, which would tank.
  (jason.dobies@redhat.com)
- 866996 - Added ability to hide the details link on association commands when
  it isn't a search. (jason.dobies@redhat.com)
- 877797 - successful call of canceling a task now returns a call report
  through the rest api (jason.connor@gmail.com)
- 867464 - updating general module upload command output (skarmark@redhat.com)
- 882424 - only have 1 task, presumedly the "main" one, in a task group update
  the last_run field (jason.connor@gmail.com)
- 883059 - update server.conf to make server_name optional
  (skarmark@redhat.com)
- 883059 - updating default server config to lookup server hostname
  (skarmark@redhat.com)
- 862187 /var/log/pulp/db.log now includes timestamps. (rbarlow@redhat.com)
- 883025 - Display note to copy qpid certificates to each consumer.
  (jortel@redhat.com)
- 880441 - Fixed call to a method that was renamed (jason.dobies@redhat.com)
- 881120 - utilized new serialize_result call report flag to hide consumer key
  when reporting the task information (jason.connor@gmail.com)
- 882428 - utilizing new call report serialize_result flag to prevent the call
  reports from being serialized and reported over the rest api
  (jason.connor@gmail.com)
- 882401 - added skipped as a recognized state to the cli parser
  (jason.connor@gmail.com)
- 862290 - Added documentation for the new ListRepositoriesCommand methods
  (jason.dobies@redhat.com)
- 881639 - more programmatic. (jortel@redhat.com)
- 881389 - fixed rpm consumer bind to raise an error on non existing repos
  (skarmark@redhat.com)
- 827620 - updated repo, repo_group, consumer and user apis to use execute
  instead of execute_ok (skarmark@redhat.com)
- 878620 - fixed task group resource to return only tasks in the group instead
  of all tasks ever run... :P (jason.connor@gmail.com)
- 866491 - Change the source repo ID validation to be a 400, not 404
  (jason.dobies@redhat.com)
- 866491 - Check for repo existence and raise a 404 if not found instead of
  leaving the task to do it (jason.dobies@redhat.com)
- 881120 - strip the private key from returned consumer object.
  (jortel@redhat.com)
- 862290 - Added support in generic list repos command for listing other
  repositories (jason.dobies@redhat.com)
- 877914 - updating old file links from selinux installation and un-
  installation (skarmark@redhat.com)
- 873786 - updating enable.sh for correct amqp ports (skarmark@redhat.com)
- 878654 - fixed error message when revoking permission from a non-existing
  user and added unit tests (skarmark@redhat.com)
- added database collection reaper system that will wake up periodically and
  remove old documents from configured collections (jason.connor@gmail.com)
- 876662 - Added middleware exception handling for when the client cannot
  resolve the server hostname (jason.dobies@redhat.com)
- 753680 - Taking this opportunity to quiet the logs a bit too
  (jason.dobies@redhat.com)
- 753680 - Increased the logging clarity and location for initialization errors
  (jason.dobies@redhat.com)
- 871858 - Implemented sync and publish status commands
  (jason.dobies@redhat.com)
- 873421 - changed a wait-time message to be more appropriate, and added a bit
  of function parameter documentation. (mhrivnak@redhat.com)
- 877170 - Added ability to ID validator to handle multiple inputs
  (jason.dobies@redhat.com)
- 877435 - Pulled the filters/order to constants and use in search
  (jason.dobies@redhat.com)
- 875606 - Added isodate and python-setuptools deps. Rolled into a quick audit
  of all the requirements and changed quite a few. There were several missing
  and several no longer applicaple. Also removed a stray import of okaara from
  within the bindings package. (mhrivnak@redhat.com)
- 874243 - return 404 when profile does not exist. (jortel@redhat.com)
- 876662 - Added pretty error message when the incorrect server hostname is
  used (jason.dobies@redhat.com)
- 876332 - add missing tags to bind itinerary. (jortel@redhat.com)
