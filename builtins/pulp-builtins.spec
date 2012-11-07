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
Version: 0.0.335
Release: 1%{?dist}
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


# ---- Admin (client) Extensions -----------------------------------------------

%package admin-extensions
Summary: The builtin admin client extensions
Group: Development/Languages
Requires: pulp-admin-client = %{version}

%description admin-extensions
A collection of extensions used to provide generic consumer
client capabilites.

%files admin-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/admin/extensions/pulp_admin_auth/
%{_usr}/lib/pulp/admin/extensions/pulp_admin_consumer/
%{_usr}/lib/pulp/admin/extensions/pulp_event/
%{_usr}/lib/pulp/admin/extensions/pulp_orphan/
%{_usr}/lib/pulp/admin/extensions/pulp_permission/
%{_usr}/lib/pulp/admin/extensions/pulp_role/
%{_usr}/lib/pulp/admin/extensions/pulp_repo/
%{_usr}/lib/pulp/admin/extensions/pulp_tasks/
%{_usr}/lib/pulp/admin/extensions/pulp_user/
%{_usr}/lib/pulp/admin/extensions/pulp_server_info/
%doc


# ---- Consumer (client) Extensions --------------------------------------------

%package consumer-extensions
Summary: The builtin consumer client extensions
Group: Development/Languages
Requires: pulp-consumer-client = %{version}

%description consumer-extensions
A collection of extensions used to provide generic admin
client capabilities.

%files consumer-extensions
%defattr(-,root,root,-)
%{_usr}/lib/pulp/consumer/extensions/pulp_consumer/
%doc




%changelog
* Tue Oct 30 2012 Jeff Ortel <jortel@redhat.com> 0.0.335-1
- 

* Mon Oct 29 2012 Jeff Ortel <jortel@redhat.com> 0.0.334-1
- version alignment

* Mon Oct 22 2012 Jeff Ortel <jortel@redhat.com> 0.0.333-1
- version alignment

* Wed Oct 17 2012 Jeff Ortel <jortel@redhat.com> 0.0.332-1
- Version alignment.

* Fri Oct 05 2012 Jeff Ortel <jortel@redhat.com> 0.0.331-1
- 860425 - fix consumer update() passing display-name instead of display_name.
  (jortel@redhat.com)

* Tue Oct 02 2012 Jeff Ortel <jortel@redhat.com> 0.0.330-1
- Version alignment.

* Sun Sep 30 2012 Jeff Ortel <jortel@redhat.com> 0.0.329-1
- Version alignment.

* Fri Sep 21 2012 Jeff Ortel <jortel@redhat.com> 0.0.328-2
- Remove pulp_upload extension. (jortel@redhat.com)

* Fri Sep 21 2012 Jeff Ortel <jortel@redhat.com> 0.0.328-1
- 854632 - added --password and -p options to user update command to update
  password in a non-interactive and interactive fashion respectively
  (skarmark@redhat.com)

* Fri Sep 07 2012 Jeff Ortel <jortel@redhat.com> 0.0.327-1
- Refactored upload commands to reusable package and implemented Puppet
  module upload (jason.dobies@redhat.com)

* Fri Aug 31 2012 Jeff Ortel <jortel@redhat.com> 0.0.326-1
- CLI for managing event listeners. (mhrivnak@redhat.com)
- Consumer Group support (james.slagle@gmail.com)

* Sun Aug 26 2012 Jeff Ortel <jortel@redhat.com> 0.0.325-1
- Refactored repo and repo group commands to the client package
  (jason.dobies@redhat.com)

* Thu Aug 16 2012 Jeff Ortel <jortel@redhat.com> 0.0.324-1
- 

* Sat Aug 11 2012 Jeff Ortel <jortel@redhat.com> 0.0.323-1
- 

* Wed Aug 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.322-1
- 845327 - changing basic consumer extension commands like unregister, update
  etc. to accept --consumer-id as an option instead of --id
  (skarmark@redhat.com)
- unit search within a repository through the CLI now used the standard
  criteria features. (mhrivnak@redhat.com)

* Fri Aug 03 2012 Jeff Ortel <jortel@redhat.com> 0.0.321-2
- packaging, add pulp_server_info extension. 

* Fri Aug 03 2012 Jeff Ortel <jortel@redhat.com> 0.0.321-1
- 

* Wed Aug 01 2012 Jeff Ortel <jortel@redhat.com> 0.0.320-1
-

* Mon Jul 30 2012 Jeff Ortel <jortel@redhat.com> 0.0.319-1
- 843618 - Added interactive prompt when the password isn't specified
  (jason.dobies@redhat.com)
- Adding CLI support for repository groups (mhrivnak@redhat.com)
- Repository Groups now have the criteria-based search REST API.
  (mhrivnak@redhat.com)
- 841584 - Temporarily turn the generic bind extension into RPM
  (jason.dobies@redhat.com)

* Thu Jul 12 2012 Jeff Ortel <jortel@redhat.com> 0.0.313-1
- Version alignment.
* Tue Jul 10 2012 Jeff Ortel <jortel@redhat.com> 0.0.312-3
- bump release. (jortel@redhat.com)
- Add Group: Development/Languages for RHEL5 builds. (jortel@redhat.com)

* Tue Jul 10 2012 Jeff Ortel <jortel@redhat.com> 0.0.312-2
- Add missing pulp_user extension. (jortel@redhat.com)

* Tue Jul 10 2012 Jeff Ortel <jortel@redhat.com> 0.0.312-1
- user admin extensions (skarmark@redhat.com)
- user admin extensions (skarmark@redhat.com)
- Allow client upload of a unit with no file data, allows creation of unit with
  just unit_key/metadata (jmatthews@redhat.com)
- Fixed typo where repo display_name was incorrectly referenced as 'display-
  name'. (mhrivnak@redhat.com)
- Merge branch 'master' into mhrivnak-repo-query (mhrivnak@redhat.com)
- Changed the repo CLI to request importers and distributors through the REST
  API only when desired. Added a test. (mhrivnak@redhat.com)
- added tests to verify current functionality of CLI repo requests. Also added
  the ability to pass query parameters to the REST API when making the CLI code
  makes a repositories request. (mhrivnak@redhat.com)
- Merge branch 'mhrivnak-repo-query' into mhrivnak-repo-cli
  (mhrivnak@redhat.com)
- Adding unit tests, improving existing tests, and adding documentation (while
  fixing a couple of typos). This is all to help me understand how this system
  works before changing it. (mhrivnak@redhat.com)

* Tue Jul 03 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.310-1
- Added pulp_upload extension to pulp-dev and the spec
  (jason.dobies@redhat.com)
- moving the common unit upload logic out of the rpm plugin into the builtins
  tree (dradez@redhat.com)

* Fri Jun 29 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.309-1
-

* Thu Jun 28 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.308-1
- 827201 - fixing consumer_history to use start_date and end_date filters in
  iso8601 format and history tests (skarmark@redhat.com)

* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.307-1
-

* Fri Jun 22 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.306-1
- Fixing consumer authorization problem because of no associated users with the
  consumers (like in v1) and minor fixed to consumer config parsing
  (skarmark@redhat.com)

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.305-1
-

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.304-1
-

* Thu Jun 21 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.303-1
-

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.302-1
-

* Tue Jun 19 2012 Jay Dobies <jason.dobies@redhat.com> 0.0.301-1
- few more (jason.connor@gmail.com)

* Fri Jun 15 2012 Jeff Ortel <jortel@redhat.com> 0.0.300-1
- Align versions to: 300 (jortel@redhat.com)
- Renamed builtins base for uniqueness across subprojects, relevant for the
  single test suite at root (jason.dobies@redhat.com)
- Better package summary/descriptions. (jortel@redhat.com)
- Add copyright and fix (name) macro usage. (jortel@redhat.com)
- pulp-builtins, fine tuning. (jortel@redhat.com)

* Thu Jun 14 2012 Jeff Ortel <jortel@redhat.com> 0.0.296-1
- new package built with tito

* Fri Jun 08 2012 Jeff Ortel <jortel@redhat.com> 0.0.295-1
- created.
