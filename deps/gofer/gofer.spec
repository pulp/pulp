%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?ruby_sitelib: %global ruby_sitelib %(ruby -rrbconfig  -e 'puts Config::CONFIG["sitelibdir"]')}

Name: gofer
Version: 0.70
Release: 1%{?dist}
Summary: A lightweight, extensible python agent
Group:   Development/Languages
License: LGPLv2
URL: https://fedorahosted.org/gofer/
Source0: https://fedorahosted.org/releases/g/o/gofer/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: rpm-python
Requires: python-%{name} = %{version}
Requires: python-iniparse
%description
Gofer provides an extensible, light weight, universal python agent.
The gofer core agent is a python daemon (service) that provides
infrastructure for exposing a remote API and for running Recurring
Actions. The APIs contributed by plug-ins are accessible by Remote
Method Invocation (RMI). The transport for RMI is AMQP using the
QPID message broker. Actions are also provided by plug-ins and are
executed at the specified interval.

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
pushd ruby
mkdir -p %{buildroot}/%{ruby_sitelib}/%{name}/rmi
mkdir -p %{buildroot}/%{ruby_sitelib}/%{name}/messaging
cp %{name}.rb %{buildroot}/%{ruby_sitelib}
pushd %{name}
cp *.rb %{buildroot}/%{ruby_sitelib}/%{name}
pushd rmi
cp *.rb %{buildroot}/%{ruby_sitelib}/%{name}/rmi
popd
pushd messaging
cp *.rb %{buildroot}/%{ruby_sitelib}/%{name}/messaging
popd
popd
popd
popd

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/plugins
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}/conf.d
mkdir -p %{buildroot}/%{_sysconfdir}/init.d
mkdir -p %{buildroot}/%{_var}/log/%{name}
mkdir -p %{buildroot}/%{_var}/lib/%{name}/journal/watchdog
mkdir -p %{buildroot}/%{_libdir}/%{name}/plugins

cp bin/%{name}d %{buildroot}/usr/bin
cp etc/init.d/%{name}d %{buildroot}/%{_sysconfdir}/init.d
cp etc/%{name}/*.conf %{buildroot}/%{_sysconfdir}/%{name}
cp etc/%{name}/plugins/*.conf %{buildroot}/%{_sysconfdir}/%{name}/plugins
cp src/plugins/*.py %{buildroot}/%{_libdir}/%{name}/plugins

rm -rf %{buildroot}/%{python_sitelib}/%{name}*.egg-info

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%dir %{_sysconfdir}/%{name}/conf.d/
%{python_sitelib}/%{name}/agent/
%{_bindir}/%{name}d
%attr(755,root,root) %{_sysconfdir}/init.d/%{name}d
%config(noreplace) %{_sysconfdir}/%{name}/agent.conf
%config(noreplace) %{_sysconfdir}/%{name}/plugins/builtin.conf
%{_libdir}/%{name}/plugins/builtin.*
%{_var}/log/%{name}
%doc LICENSE

%post
chkconfig --add %{name}d

%preun
if [ $1 = 0 ] ; then
   /sbin/service %{name}d stop >/dev/null 2>&1
   /sbin/chkconfig --del %{name}d
fi


###############################################################################
# python lib
###############################################################################

%package -n python-%{name}
Summary: Gofer python lib modules
Group: Development/Languages
Obsoletes: %{name}-lib
BuildRequires: python
Requires: python-simplejson
Requires: python-qpid >= 0.7
Requires: PyPAM
%if 0%{?rhel} && 0%{?rhel} < 6
Requires: python-hashlib
Requires: python-uuid
Requires: python-ssl
%endif

%description -n python-%{name}
Contains gofer python lib modules.

%files -n python-%{name}
%defattr(-,root,root,-)
%{python_sitelib}/%{name}/*.py*
%{python_sitelib}/%{name}/rmi/
%{python_sitelib}/%{name}/messaging/
%doc LICENSE

###############################################################################
# ruby lib
###############################################################################

%package -n ruby-%{name}
Summary: Gofer ruby lib modules
Group: Development/Languages
BuildRequires: ruby
Requires: ruby-qpid
Requires: rubygems
Requires: rubygem(json)

%description -n ruby-%{name}
Contains gofer ruby lib modules.

%files -n ruby-%{name}
%defattr(-,root,root,-)
%{ruby_sitelib}/%{name}.rb
%{ruby_sitelib}/%{name}/*.rb
%{ruby_sitelib}/%{name}/rmi/
%{ruby_sitelib}/%{name}/messaging/
%doc LICENSE


###############################################################################
# plugin: system
###############################################################################

%package -n gofer-system
Summary: The system plug-in
Group: Development/Languages
BuildRequires: python
Requires: %{name} >= %{version}

%description -n gofer-system
Contains the system plug-in.
The system plug-in provides system functionality.

%files -n gofer-system
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/%{name}/plugins/system.conf
%{_libdir}/%{name}/plugins/system.*
%doc LICENSE


###############################################################################
# plugin: watchdog
###############################################################################

%package -n gofer-watchdog
Summary: The watchdog plug-in
Group: Development/Languages
BuildRequires: python
Requires: %{name} >= %{version}

%description -n gofer-watchdog
Contains the watchdog plug-in.
This plug-in is used to support time out
for asynchronous RMI calls.

%files -n gofer-watchdog
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/%{name}/plugins/watchdog.conf
%{_libdir}/%{name}/plugins/watchdog.*
%{_var}/lib/%{name}/journal/watchdog
%doc LICENSE


###############################################################################
# plugin: virt
###############################################################################

%package -n gofer-virt
Summary: The virtualization plugin
Group: Development/Languages
BuildRequires: python
Requires: libvirt-python
Requires: %{name} >= %{version}

%description -n gofer-virt
Contains the virtualization plugin.
This plug-in provides RMI access to libvirt functionality.

%files -n gofer-virt
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/%{name}/plugins/virt.conf
%{_libdir}/%{name}/plugins/virt.*
%doc LICENSE


###############################################################################
# plugin: package
###############################################################################

%package -n gofer-package
Summary: The package (RPM) plugin
Group: Development/Languages
BuildRequires: python
Requires: yum
Requires: %{name} >= %{version}

%description -n gofer-package
Contains the package plugin.
This plug-in provides RMI access to package (RPM) management.

%files -n gofer-package
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/%{name}/plugins/package.conf
%{_libdir}/%{name}/plugins/package.*
%doc LICENSE



%changelog
* Tue Jun 12 2012 Jeff Ortel <jortel@redhat.com> 0.70-1
- bump gofer to: 0.70 (jortel@redhat.com)
- Renamed dependency RPMs (jason.dobies@redhat.com)

* Tue Jun 12 2012 Jeff Ortel <jortel@redhat.com> 0.70-1
- Refit mocks for reparent of Envelope & Options to (object).
  (jortel@redhat.com)

* Fri Jun 08 2012 Jeff Ortel <jortel@redhat.com> 0.69-1
- 829767 - fix simplejons 2.2+ issue (fedora 17). Envelope/Options rebased on
  object rather than dict. (jortel@redhat.com)
- Add whiteboard. (jortel@redhat.com)
- Fixed 'Undefined variable (s) in XBindings.__bindings(). (jortel@redhat.com)

* Thu Apr 26 2012 Jeff Ortel <jortel@redhat.com> 0.68-1
- Refit watchdog plugin; set journal location; skip directories in journal dir.
  (jortel@redhat.com)
- Make the watchdog journal directory configurable. (jortel@redhat.com)
- Add Broker.touch() and rename Topic.binding(). (jortel@redhat.com)
- Better support for durable topic subscription.  Queue bindings to specified
  exchanges. (jortel@redhat.com)
* Fri Mar 16 2012 Jeff Ortel <jortel@redhat.com> 0.67-1
- Add (trace) attribute to propagated exceptions. (jortel@redhat.com)
- Add traceback info to propagated exceptions as: Exception.trace.
  (jortel@redhat.com)
- Add support for __getitem__ in container and stub. (jortel@redhat.com)
- Refactor to crypto (delegate) interface. (jortel@redhat.com)
- Support multiple security decorators. (jortel@redhat.com)
- perf: asynchronous ack(); tcp_nodelay. (jortel@redhat.com)
- Rename 'delayed/trigger' policy property to match option. (jortel@redhat.com)
- Rename 'delayed' option to: 'trigger'. (jortel@redhat.com)
- option 'delayed' implies asynchronous RMI. (jortel@redhat.com)
- fix for tito compat. (jortel@redhat.com)
- bridge: clean debug prints; make gateway a thread. (jortel@redhat.com)
- Add tcp bridge (experimental). (jortel@redhat.com)
- Add support for delayed trigger asynchronous RMI. (jortel@redhat.com)
- Add fedora releaser. (jortel@redhat.com)
- support setting producer uuid; HMAC enhancements. (jortel@redhat.com)
- rel-eng: rename redhat releaser. (jortel@redhat.com)

* Tue Feb 21 2012 Jeff Ortel <jortel@redhat.com> 0.66-1
- Add DistGit releaser. (jortel@redhat.com)
- Add deps: python-iniparse; python-hashlib (rhel5). (jortel@redhat.com)

* Fri Feb 03 2012 Jeff Ortel <jortel@redhat.com> 0.65-1
- Initial add of hmac classes; add synchronized decorator. (jortel@redhat.com)
- python 2.4 compat for __import__(). (jortel@redhat.com)
- Enhanced monitoring, use sha256 in addition to mtime. (jortel@redhat.com)
- Add support for dynamic plugin URL in addition to UUID. (jortel@redhat.com)

* Mon Jan 09 2012 Jeff Ortel <jortel@redhat.com> 0.64-1
- Enhanced package (plugin) API. (jortel@redhat.com)
* Wed Nov 30 2011 Jeff Ortel <jortel@redhat.com> 0.63-1
- Mitigate systemd issues on F15. (jortel@redhat.com)

* Wed Nov 30 2011 Jeff Ortel <jortel@redhat.com> 0.62-1
- plugin: package; extra monkey business with yum optparser to support
  INTERACTIVE yum plugins. (jortel@redhat.com)

* Wed Nov 23 2011 Jeff Ortel <jortel@redhat.com> 0.61-1
- mocks: add support for mock constructors. (jortel@redhat.com)
- plugin: package; Fix problem of yum interactive plugins accessing contributed
  options. (jortel@redhat.com)

* Fri Nov 18 2011 Jeff Ortel <jortel@redhat.com> 0.60-1
- plugin: package; revise API for constructors; add Yum wrapper class.
  (jortel@redhat.com)
- Support remote class constructor arguments. (jortel@redhat.com)

* Wed Nov 16 2011 Jeff Ortel <jortel@redhat.com> 0.59-1
- plugin: package; Initialize yum plugins. (jortel@redhat.com)

* Wed Nov 16 2011 Jeff Ortel <jortel@redhat.com> 0.58-1
- Add 'apply' flag on Pacakge.update(); handle obsoletes; better return info.
  (jortel@redhat.com)
- Test commit for SSH key changed. (jortel@redhat.com)
- Better handling of corrupted files in pending store. (jortel@redhat.com)
- Fix bug in non-eager plugin loading. (jortel@redhat.com)

* Thu Nov 10 2011 Jeff Ortel <jortel@redhat.com> 0.57-1
- Impl plugin: System, rename shutdown() to: halt(); add cancel().
  (jortel@redhat.com)

* Thu Nov 10 2011 Jeff Ortel <jortel@redhat.com> 0.56-1
- Impl plugin: Package.update(). (jortel@redhat.com)
- Impl plugin: system.shutdown() & reboot(). (jortel@redhat.com)

* Thu Nov 10 2011 Jeff Ortel <jortel@redhat.com> 0.55-1
- change to 'importkeys' semantics; add importkeys to group installs.
  (jortel@redhat.com)
- Restrict Plugin.export() to class|function; split test agent & plugin.
  (jortel@redhat.com)
- Add tools. (jortel@redhat.com)

* Thu Oct 27 2011 Jeff Ortel <jortel@redhat.com> 0.54-1
- Refactor pmon, separate threading. (jortel@redhat.com)

* Thu Oct 27 2011 Jeff Ortel <jortel@redhat.com> 0.53-1
- Remove testing code in pmon.py left in by mistake. (jortel@redhat.com)

* Thu Oct 27 2011 Jeff Ortel <jortel@redhat.com> 0.52-1
- Add pmon utility. (jortel@redhat.com)

* Fri Oct 21 2011 Jeff Ortel <jortel@redhat.com> 0.51-1
- Better semantics: replace Plugin.__getitem__() w/ Plugin.export().
  (jortel@redhat.com)
- Optional plugins disabled by default. (jortel@redhat.com)
- Provide for plugin inheritance.   - add [loader].eager property   - switched
  to model where disabled plugins loaded but not started to support sharing.
  - add support for plugin load order specified by [main].requires.   - actions
  stored on plugins. (jortel@redhat.com)
- Add the package plugin. (jortel@redhat.com)
- Change system plugin to use subprocess. (jortel@redhat.com)

* Fri Sep 30 2011 Jeff Ortel <jortel@redhat.com> 0.50-1
- Fix epydocs. (jortel@redhat.com)

* Tue Sep 27 2011 Jeff Ortel <jortel@redhat.com> 0.49-3
- Discontinue 'pam' option and just go with user=, password=.
  (jortel@redhat.com)

* Tue Sep 27 2011 Jeff Ortel <jortel@redhat.com> 0.49-2
- mitigate rpmlint perms error on /var/log/gofer. (jortel@redhat.com)

* Tue Sep 27 2011 Jeff Ortel <jortel@redhat.com> 0.49-1
- Reader inject subject into the envelope like Consumer. (jortel@redhat.com)
- Make installed plugins, enabled. (jortel@redhat.com)
- Fix default PAM service. (jortel@redhat.com)
- Fix virt plugin; add libvirt dep. (jortel@redhat.com)
- Organize spec by pacakge/subpackage. (jortel@redhat.com)
- set facl on journal/watchdog. (jortel@redhat.com)
- Add authentication/authorization unit tests. (jortel@redhat.com)
- Finer grained auth exceptions. (jortel@redhat.com)
- package plugins; split shell into system plugin. (jortel@redhat.com)
- Split watchdog and thread objects for better performance. (jortel@redhat.com)
- Create watchdog journal directory on-demand. (jortel@redhat.com)
- Add PyPAM dep; change perms /var/log/gofer/ to 700. (jortel@redhat.com)
- Make default PAM service configurable. (jortel@redhat.com)
- Add PAM authentication and decorators; change Shell.run() to run as
  authenticated user. (jortel@redhat.com)
- FHS guidelines, move the journal back to /var/lib/gofer/journal. See: http://
  www.pathname.com/fhs/pub/fhs-2.3.html#USRSHAREARCHITECTUREINDEPENDENTDATA
  (jortel@redhat.com)

* Tue Sep 13 2011 Jeff Ortel <jortel@redhat.com> 0.48-3
- Fix tito tagging problem. (jortel@redhat.com)

* Tue Sep 13 2011 Jeff Ortel <jortel@redhat.com> 0.48-2
- bump to release: 2. (jortel@redhat.com)
- Move journal to /usr/share; hunt for plugins in path: /usr/lib/gofer/plugins,
  /usr/lib64/gofer/plugins, /opt/gofer/plugins. (jortel@redhat.com)

* Fri Sep 09 2011 Jeff Ortel <jortel@redhat.com> 0.48-1
- Use rpm _var macro; use global instead of define rpm macro; fix perms on
  agent.conf. (jortel@redhat.com)
- Fix builtin.Admin.help(). (jortel@redhat.com)

* Tue Aug 23 2011 Jeff Ortel <jortel@redhat.com> 0.47-1
- Fix macros in changelog. (jortel@redhat.com)
- Fix cp etc/xx replaced with macro my mistake in build section of spec.
  (jortel@redhat.com)
- upload spec file. (jortel@redhat.com)

* Mon Aug 22 2011 Jeff Ortel <jortel@redhat.com> 0.46-1
- Fix duplicate ruby files. (jortel@redhat.com)
- Add /var/log/gofer to %%files. (jortel@redhat.com)
- Fix rpmlink complaints. (jortel@redhat.com)
- Point Source0: at fedorahosted. (jortel@redhat.com)
- Fix rpmlint complaints. (jortel@redhat.com)
- Add LICENSE and reference in %%doc. (jortel@redhat.com)

* Fri Aug 12 2011 Jeff Ortel <jortel@redhat.com> 0.45-1
- ruby: align with python impl. (jortel@redhat.com)
- Rework dispatcher flow. Move most of the RMI modules to a new (rmi) package.
  Dispatch everything to the PendingQueue which has been greatly optimized. Fix
  ThreadPool worker allocation. Add scheduler to process PendingQueue and queue
  messages to appropriate plugin's thread pool. Add TTL processing throughout
  the dispatch flow. Commit individual messages grabbed off the PendingQueue.
  (jortel@redhat.com)

* Wed Aug 03 2011 Jeff Ortel <jortel@redhat.com> 0.44-1
- Fix RHEL (python 2.4) macro. (jortel@redhat.com)
- Add watchdog plugin. (jortel@redhat.com)
- Add journal & watchdog. (jortel@redhat.com)

* Fri Jul 22 2011 Jeff Ortel <jortel@redhat.com> 0.43-1
- Propigate json exception of return and raised exception values back to
  caller. (jortel@redhat.com)
- Fix topic queue leak that causes: Enqueue capacity threshold exceeded on
  queue. (jortel@redhat.com)
- Add atexit hook to close endpoints. (jortel@redhat.com)
- Fix epydocs. (jortel@redhat.com)

* Wed Jun 22 2011 Jeff Ortel <jortel@redhat.com> 0.42-1
- Simplified thread pool. (jortel@redhat.com)

* Thu Jun 16 2011 Jeff Ortel <jortel@redhat.com> 0.41-1
- python-qpid 0.10 API compat. Specifically on EL6, the Transport.__init__()
  constructor/factory gets called with (con, host, port) instead of (host,
  port) in < 0.10. The 0.10 in F14 still called with (host, port).
  (jortel@redhat.com)

* Thu Jun 16 2011 Jeff Ortel <jortel@redhat.com> 0.40-1
- License as: LGPLv2. (jortel@redhat.com)

* Tue Jun 14 2011 Jeff Ortel <jortel@redhat.com> 0.39-1
- Increase logging in policy. (jortel@redhat.com)
- Add session pool & fix receiver leak in policy. (jortel@redhat.com)
- Testing: enhanced thread pool testing. (jortel@redhat.com)

* Fri May 27 2011 Jeff Ortel <jortel@redhat.com> 0.38-1
- Skip comments when processing config macros. (jortel@redhat.com)
- Queue exceptions caught in the threadpool. (jortel@redhat.com)

* Fri May 13 2011 Jeff Ortel <jortel@redhat.com> 0.37-1
- Fix broker singleton lookup. (jortel@redhat.com)
- Mock call object enhancements. (jortel@redhat.com)

* Mon May 09 2011 Jeff Ortel <jortel@redhat.com> 0.36-1
- Stop receiver thread before closing session. (jortel@redhat.com)
* Tue May 03 2011 Jeff Ortel <jortel@redhat.com> 0.35-1
- Additional concurrency protection; move qpid receiver to ReceiverThread.
  (jortel@redhat.com)
- python 2.4 compat: Queue. (jortel@redhat.com)

* Mon May 02 2011 Jeff Ortel <jortel@redhat.com> 0.34-1
- More robust (receiver) management. (jortel@redhat.com)
- Support getting a list of all mock agent (proxies). (jortel@redhat.com)
- proxy.Agent deprecated. (jortel@redhat.com)
- close() called by __del__() can have AttributeError when consumer never
  started. (jortel@redhat.com)
- Provide means to detect number of proxies. (jortel@redhat.com)
- Singleton enhancements. (jortel@redhat.com)
- Move url translated into producer to proxy.Agent. (jortel@redhat.com)
- add mock.reset(). (jortel@redhat.com)
- Revised and simplified mocks. (jortel@redhat.com)

* Wed Apr 20 2011 Jeff Ortel <jortel@redhat.com> 0.33-1
- Mock history enhancements. (jortel@redhat.com)
- support 'threads' in agent.conf. (jortel@redhat.com)

* Wed Apr 13 2011 Jeff Ortel <jortel@redhat.com> 0.32-1
- Add messaging.theads (cfg) property. (jortel@redhat.com)
- Add support for concurrent RMI dispatching. (jortel@redhat.com)

* Mon Apr 11 2011 Jeff Ortel <jortel@redhat.com> 0.31-1
- Default timeout in specific policies. (jortel@redhat.com)
- Manage invocation policy in stub instead of agent proxy. This provides for
  timeout, async and other flags to be passed in stub constructor.
  (jortel@redhat.com)

* Mon Apr 11 2011 Jeff Ortel <jortel@redhat.com> 0.30-1
- Fix @import of whole sections on machines w/ old versions of iniparse.
  (jortel@redhat.com)

* Wed Apr 06 2011 Jeff Ortel <jortel@redhat.com> 0.29-1
- Refactor mocks; fix NotPermitted. (jortel@redhat.com)
- Mock enhancements. (jortel@redhat.com)
- Fix lockfile. (jortel@redhat.com)
- Stop logging shared secret at INFO. (jortel@redhat.com)

* Wed Mar 30 2011 Jeff Ortel <jortel@redhat.com> 0.28-1
- plugin descriptor & qpid error handling. (jortel@redhat.com)

* Mon Mar 28 2011 Jeff Ortel <jortel@redhat.com> 0.27-1
- Change to yappi profiler. (jortel@redhat.com)
- factor Reader.__fetch() and catch/log fetch exceptions. (jortel@redhat.com)
- Add missing import sleep(). (jortel@redhat.com)

* Thu Mar 24 2011 Jeff Ortel <jortel@redhat.com> 0.26-1
- close sender, huge performance gain. (jortel@redhat.com)
- Add stub Factory. (jortel@redhat.com)

* Tue Mar 22 2011 Jeff Ortel <jortel@redhat.com> 0.25-1
- Use {el5} macro. (jortel@redhat.com)
- Reduce log clutter. (jortel@redhat.com)

* Fri Mar 18 2011 Jeff Ortel <jortel@redhat.com> 0.24-1
- Update secret in options epydoc; fix options override in stub().
  (jortel@redhat.com)
- Add code profiling option. (jortel@redhat.com)
- Add mutex to Broker. (jortel@redhat.com)

* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.23-1
- Change receiver READY message to debug. (jortel@redhat.com)

* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.22-1
- Change message send/recv to DEBUG. (jortel@redhat.com)

* Fri Mar 11 2011 Jeff Ortel <jortel@redhat.com> 0.21-1
- URL not defined in builtin & main configurations. (jortel@redhat.com)
- Test action every 36 hours. (jortel@redhat.com)
- Start plugin monitor only when URL defined. (jortel@redhat.com)
- Make references to properties on undefined sections safe. (jortel@redhat.com)

* Wed Feb 16 2011 Jeff Ortel <jortel@redhat.com> 0.20-1
- shared in remote decorator may be callable. (jortel@redhat.com)
- Update @remote to support (shared,secret). shared = (0|1): indicates method
  may be shared with other plugins   and called via other uuid's. secret =
  (None, str): A shared secret that must be presented by   the caller and
  included in the RMI request for authentication. The defaults (shared=1,
  secret=None). (jortel@redhat.com)

* Thu Feb 10 2011 Jeff Ortel <jortel@redhat.com> 0.19-1
- ruby: ruby & c++ API expect ttl as miliseconds. (jortel@redhat.com)
- ruby: make non-durable queues auto_delete; make all queues exclusive.
  (jortel@redhat.com)

* Wed Feb 09 2011 Jeff Ortel <jortel@redhat.com> 0.18-1
- Make sure plugins directory exists. (jortel@redhat.com)
- Make file paths portable; fix usage. (jortel@redhat.com)

* Wed Feb 02 2011 Jeff Ortel <jortel@redhat.com> 0.17-1
- Add Obsoletes: gofer-lib. (jortel@redhat.com)
- ruby: Move url/producer options handling to Container. (jortel@redhat.com)
- ruby: replace (puts) with logging. (jortel@redhat.com)

* Tue Feb 01 2011 Jeff Ortel <jortel@redhat.com> 0.16-1
- Fix build requires. (jortel@redhat.com)

* Mon Jan 31 2011 Jeff Ortel <jortel@redhat.com> 0.15-1
- ruby: symbolize JSON key names; Fix proxy constructor. (jortel@redhat.com)
- Add timeout support using Timeout since ruby-qpid does not support
  Queue.get() w/ timeout arg. (jortel@redhat.com)
- Replace stub() method w/ StubFactory(). (jortel@redhat.com)
- Add keyword (options) to Stub pseudo constructor. Supports Eg: dog =
  agent.Dog(window=mywin, any=100). Update async test to use ctag = XYZ.
  (jortel@redhat.com)
- Fix & simplify inherited messaging properties. Name ReplyConsumer properly.
  (jortel@redhat.com)
- Add ruby packaging. (jortel@redhat.com)
- Make messaging completely centric. * Add [messaging] section to plugin
  descriptor. * Remove messaging.enabled property. * Refactor plugin monitor
  thread to be 1 thread/plugin. * Clean up decorated /Remote/ functions when
  plugin fails to load. (jortel@redhat.com)
- Add ruby (client) API bindings. (jortel@redhat.com)

* Thu Jan 20 2011 Jeff Ortel <jortel@redhat.com> 0.14-1
- Fix conditional for pkgs required on RHEL. (jortel@redhat.com)

* Wed Jan 12 2011 Jeff Ortel <jortel@redhat.com> 0.13-1
- Make Broker a smart singleton. (jortel@redhat.com)
- py 2.4 compat: replace @singleton class decorator with __metaclass__
  Singleton. (jortel@redhat.com)
- Log dispatch exceptions. (jortel@redhat.com)

* Wed Jan 05 2011 Jeff Ortel <jortel@redhat.com> 0.12-1
- Adjust sleep times & correct log messages. (jortel@redhat.com)
- Make logging (level) configurable. (jortel@redhat.com)
- Remove @identity decorator. (jortel@redhat.com)

* Tue Jan 04 2011 Jeff Ortel <jortel@redhat.com> 0.11-1
- Quiet logged Endpoint.close() not checking for already closed.
  (jortel@redhat.com)
- Replace builtin variables with macros (format=%%{macro}). (jortel@redhat.com)
- make Config a singleton; Make PluginDescriptor a 'Base' config.
  (jortel@redhat.com)
- Add support for @import directive. (jortel@redhat.com)
- The server test needs to use the correct uuid. (jortel@redhat.com)

* Wed Dec 15 2010 Jeff Ortel <jortel@redhat.com> 0.10-1
- session.stop() not supported in python-qpid 0.7. (jortel@redhat.com)
- Remove unused catch. (jortel@redhat.com)
- Make worker threads daemons. (jortel@redhat.com)

* Mon Dec 13 2010 Jeff Ortel <jortel@redhat.com> 0.9-1
- Set AMQP message TTL=timeout for synchronous RMI. (jortel@redhat.com)

* Thu Dec 09 2010 Jeff Ortel <jortel@redhat.com> 0.8-1
- Fix RHEL requires. (jortel@redhat.com)
- Enable module (level) access to plugin descriptor (conf). (jortel@redhat.com)

* Wed Dec 08 2010 Jeff Ortel <jortel@redhat.com> 0.7-1
- Support timeout as tuple. (jortel@redhat.com)
- Enhanced exception propagation. (jortel@redhat.com)
- Fix testings. (jortel@redhat.com)

* Fri Dec 03 2010 Jeff Ortel <jortel@redhat.com> 0.6-1
- Reverse presidence of uuid: plugin descriptor now overrides @identity
  function/method. (jortel@redhat.com)

* Thu Dec 02 2010 Jeff Ortel <jortel@redhat.com> 0.5-1
- python 2.4 (& RHEL 5) compatibility. (jortel@redhat.com)

* Thu Dec 02 2010 Jeff Ortel <jortel@redhat.com> 0.4-1
- Modify builtin (generated) uuid to be persistent. (jortel@redhat.com)
- Use hostname for 'builtin' plugin's uuid. Use the hostname unless it is non-
  unique such as 'localhost' or 'localhost.localdomain'. (jortel@redhat.com)

* Thu Dec 02 2010 Jeff Ortel <jortel@redhat.com> 0.3-1
- Set 'builtin' plugin back to uuid=123. (jortel@redhat.com)
- Re-specify exclusive queue subscription; filter plugin descriptors by ext.
  (jortel@redhat.com)
- Add support for each plugin to specify a messaging consumer (uuid).
  (jortel@redhat.com)
- Rename builtin AgentAdmin to just Admin. (jortel@redhat.com)
- Replace class decorators for python 2.4 compat. (jortel@redhat.com)
- Fix cvs tags. (jortel@redhat.com)
- Automatic commit of package [gofer] release [0.2-1]. (jortel@redhat.com)
- Add brew build informaton. (jortel@redhat.com)

* Fri Nov 19 2010 Jeff Ortel <jortel@redhat.com> 0.2-1
- Add brew build informaton. (jortel@redhat.com)
- Fix test. (jortel@redhat.com)

* Mon Nov 08 2010 Jeff Ortel <jortel@redhat.com> 0.1-1
- new package built with tito

* Thu Sep 30 2010 Jeff Ortel <jortel@redhat.com> 0.1-1
- 0.1
