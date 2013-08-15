# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0


# ---- Pulp Builtins -----------------------------------------------------------

Name: pulp-builtins
Version: 2.2.0
Release: 0.26.beta%{?dist}
Summary: Pulp builtin extensions
Group: Development/Languages
License: GPLv2
URL: https://fedorahosted.org/pulp/
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python2-devel
BuildRequires: rpm-python

%description
The pulp project provided generic extensions.

%prep
%setup -q

%build

%install

# Directories
mkdir -p %{buildroot}/%{_usr}/lib/pulp/admin/extensions
mkdir -p %{buildroot}/%{_usr}/lib/pulp/consumer/extensions


# Extensions
cp -R extensions/admin/* %{buildroot}/%{_usr}/lib/pulp/admin/extensions
cp -R extensions/consumer/* %{buildroot}/%{_usr}/lib/pulp/consumer/extensions

%clean
rm -rf %{buildroot}


# define required pulp platform version.
%global pulp_version %{version}


# ---- Admin (client) Extensions -----------------------------------------------

%package admin-extensions
Summary: The builtin admin client extensions
Group: Development/Languages
Requires: pulp-admin-client = %{pulp_version}

%description admin-extensions
A collection of extensions used to provide generic consumer
client capabilites.

%files admin-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/admin/extensions/pulp_admin_auth/
%{_usr}/lib/pulp/admin/extensions/pulp_admin_consumer/
%{_usr}/lib/pulp/admin/extensions/pulp_auth/
%{_usr}/lib/pulp/admin/extensions/pulp_event/
%{_usr}/lib/pulp/admin/extensions/pulp_orphan/
%{_usr}/lib/pulp/admin/extensions/pulp_repo/
%{_usr}/lib/pulp/admin/extensions/pulp_tasks/
%{_usr}/lib/pulp/admin/extensions/pulp_server_info/
%{_usr}/lib/pulp/admin/extensions/pulp_binding/
%doc


# ---- Consumer (client) Extensions --------------------------------------------

%package consumer-extensions
Summary: The builtin consumer client extensions
Group: Development/Languages
Requires: pulp-consumer-client = %{pulp_version}

%description consumer-extensions
A collection of extensions used to provide generic admin
client capabilities.

%files consumer-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/consumer/extensions/pulp_consumer/
%doc




%changelog
* Thu Aug 15 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.26.beta
- Pulp rebuild

* Mon Aug 12 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.25.beta
- Pulp rebuild

* Mon Aug 05 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.24.beta
- Pulp rebuild

* Thu Aug 01 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.23.beta
- Pulp rebuild

* Fri Jul 26 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.22.beta
- Pulp rebuild

* Mon Jul 15 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.21.beta
- Pulp rebuild

* Tue Jul 09 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.20.beta
- Pulp rebuild

* Mon Jul 08 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.19.beta
- Pulp rebuild

* Wed Jul 03 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.18.beta
- Pulp rebuild

* Wed Jul 03 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.17.beta
- purge changelog

* Thu Jun 20 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.5.beta
- 

* Mon Jun 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.4.beta
- Pulp rebuild

* Tue Jun 11 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.3.beta
- Pulp rebuild

* Thu Jun 06 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.2.beta
- Pulp rebuild

* Tue Jun 04 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.1.beta
- 947445 - allowing consumer ids to allow dots (skarmark@redhat.com)
- 968543 - remove conditional in pulp_version macro. (jortel@redhat.com)

* Thu May 30 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.15.alpha
- Pulp rebuild

* Fri May 24 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.14.alpha
- Pulp rebuild

* Thu May 23 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.13.alpha
- Pulp rebuild

* Thu May 23 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.12.alpha
- Pulp rebuild

* Tue May 21 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.11.alpha
- 950149 - Updated consumer section description after a bunch of stuff was
  moved to type root sections (jason.dobies@redhat.com)

* Mon May 20 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.10.alpha
- Pulp rebuild

* Mon May 20 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.9.alpha
- Pulp rebuild

* Fri May 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.8.alpha
- Pulp rebuild

* Fri May 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.7.alpha
- Pulp rebuild

* Fri May 17 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.6.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.5.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.4.alpha
- Pulp rebuild

* Mon May 13 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.3.alpha
- 915473 - fixing login api to return a json document with key and certificate
  (skarmark@redhat.com)

* Fri Apr 19 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.2.alpha
- Pulp rebuild

* Fri Apr 12 2013 Jeff Ortel <jortel@redhat.com> 2.2.0-0.1.alpha
- 902869 - more robust handling of --force unregistration. (jortel@redhat.com)

* Mon Mar 04 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.19.alpha
- Pulp rebuild

* Tue Feb 26 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.18.alpha
- Pulp rebuild

* Tue Feb 26 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.17.alpha
- 911704 - fixing a typo in the help text for the "event listener http create"
  command (mhrivnak@redhat.com)

* Mon Feb 25 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.16.alpha
- Pulp rebuild

* Mon Feb 25 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.15.alpha
- Pulp rebuild

* Fri Feb 22 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.14.alpha
- Pulp rebuild

* Thu Feb 21 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.13.alpha
- Pulp rebuild

* Tue Feb 19 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.12.alpha
- Pulp rebuild

* Tue Feb 19 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.11.alpha
- Pulp rebuild

* Thu Feb 14 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.10.alpha
- Pulp rebuild

* Thu Feb 14 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.9.alpha
- Pulp rebuild

* Wed Feb 13 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.8.alpha
- Pulp rebuild

* Wed Feb 13 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.7.alpha
- Pulp rebuild

* Wed Feb 13 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.6.alpha
- Pulp rebuild

* Tue Feb 12 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.5.alpha
- Pulp rebuild

* Tue Feb 12 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.4.alpha
- Pulp rebuild

* Tue Feb 05 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.3.alpha
- Pulp rebuild

* Tue Feb 05 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.2.alpha
- Pulp rebuild

* Sat Jan 19 2013 Jeff Ortel <jortel@redhat.com> 2.1.0-0.1.alpha
- 882403 - Flushed out the task state to user display mapping as was always the
  intention but never actually came to fruition. (jason.dobies@redhat.com)
- 861383 - more descriptive message on unregister when server does not exist on
  the server. (jortel@redhat.com)
- 883049 - check we have write permissions to cert dir before
  register/unregister. (jortel@redhat.com)
- 878632 - adding usage to permission grant and revoke commands to mention that
  both role-id and login cannot be used at the same time (skarmark@redhat.com)
- 862290 - Added support in generic list repos command for listing other
  repositories (jason.dobies@redhat.com)
- 878107 - consumer status now mentions which pulp server the consumer is
  registered to as well (skarmark@redhat.com)

* Thu Dec 20 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.19.rc
- Pulp rebuild

* Wed Dec 19 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.19.beta
- Pulp rebuild

* Tue Dec 18 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.18.beta
- Pulp rebuild

* Thu Dec 13 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.17.beta
- Pulp rebuild

* Thu Dec 13 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.15.beta
- 882403 - Flushed out the task state to user display mapping as was always the
  intention but never actually came to fruition. (jason.dobies@redhat.com)

* Mon Dec 10 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.14.beta
- Pulp rebuild

* Fri Dec 07 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.13.beta
- Pulp rebuild

* Thu Dec 06 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.12.beta
- 861383 - more descriptive message on unregister when server does not exist on
  the server. (jortel@redhat.com)
- 883049 - check we have write permissions to cert dir before
  register/unregister. (jortel@redhat.com)
- 878632 - adding usage to permission grant and revoke commands to mention that
  both role-id and login cannot be used at the same time (skarmark@redhat.com)

* Thu Nov 29 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.11.beta
- Pulp rebuild

* Thu Nov 29 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.10.beta
- 862290 - Added support in generic list repos command for listing other
  repositories (jason.dobies@redhat.com)

* Mon Nov 26 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.9.beta
- 878107 - consumer status now mentions which pulp server the consumer is
  registered to as well (skarmark@redhat.com)

* Wed Nov 21 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.8.beta
- Pulp rebuild

* Wed Nov 21 2012 Jay Dobies <jason.dobies@redhat.com> 2.0.6-0.7.beta
- Pulp rebuild

* Tue Nov 20 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.3.beta
- Pulp rebuild

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.2.beta
- Pulp rebuild

* Mon Nov 12 2012 Jeff Ortel <jortel@redhat.com> 2.0.6-0.1.beta
- Pulp rebuild
