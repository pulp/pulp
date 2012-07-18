%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

# -- headers ------------------------------------------------------------------

Name:           python-okaara
Version:        1.0.22
Release:        2%{?dist}
Summary:        Python command line utilities

Group:          Development/Tools
License:        GPLv2
URL:            https://github.com/jdob/okaara
Source0:        http://jdob.fedorapeople.org/okaara-src/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-nose
BuildRequires:  python-setuptools
BuildRequires:  python2-devel

%description
Python library to facilitate the creation of command-line interfaces.

%prep
%setup -q

# -- build --------------------------------------------------------------------

%build
pushd src
%{__python} setup.py build
popd

# -- install ------------------------------------------------------------------

%install
rm -rf $RPM_BUILD_ROOT

# Python setup
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
rm -f $RPM_BUILD_ROOT%{python_sitelib}/rhui*egg-info/requires.txt

# -- check --------------------------------------------------------------------

%check
export PYTHONPATH=$RPM_BUILD_ROOT/%{python_sitelib}
pushd test
nosetests
popd

# -- clean --------------------------------------------------------------------

%clean
rm -rf $RPM_BUILD_ROOT

# -- files --------------------------------------------------------------------

%files
%{python_sitelib}/okaara/
%{python_sitelib}/okaara*.egg-info
%doc LICENSE

# -- changelog ----------------------------------------------------------------

%changelog
* Wed Jul 18 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.22-2
- Upgraded okaara to 1.0.22 (jason.dobies@redhat.com)

* Wed Jul 18 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.22-1
- converted to new-style classes so they are easier to subclass.
  (mhrivnak@redhat.com)
- Validate and parse functions are no longer applied to options for which the
  user did not supply any input. (mhrivnak@redhat.com)
 Added built in validate and parse functions on options
  (jason.dobies@redhat.com)
- Some refactoring to support subclasses better (jason.dobies@redhat.com)
- Added color support (naturally) (jason.dobies@redhat.com)

* Mon Jul 09 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.21-1
- Make sure src is in the python path so tests can run
  (jason.dobies@redhat.com)

* Sun Jul 08 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.20-1
- Removing the explicit python version requirement since it's not needed on
  Fedora (might still be needed on RHEL5). (jason.dobies@redhat.com)
- Added %check section and %files change for fedora packaging
  (jason.dobies@redhat.com)

* Wed May 23 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.19-1
- Changed RPM macro to adhere to Fedora packaging standards
  (jason.dobies@redhat.com)
- Work on the shell user docs (jason.dobies@redhat.com)
- Corrected incorrect docstrings (jason.dobies@redhat.com)
- More advanced usage for CLIs (jason.dobies@redhat.com)
- Significant work towards the CLI documentation (jason.dobies@redhat.com)

* Fri May 18 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.18-1
- Minor spec tweaks for Fedora packaging guidelines (jason.dobies@redhat.com)
- Added license copy and inclusion in the RPM (jason.dobies@redhat.com)
- Added ability to configure text to automatically prefix command option
  descriptions based on their required attribute (jason.dobies@redhat.com)

* Fri May 11 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.17-1
- Source file header clean up

* Fri May 11 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.16-1
- Corrections to the spec for fedora guidelines (jason.dobies@redhat.com)
- Cleanup of spec whitespace (jason.dobies@redhat.com)

* Fri May 04 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.15-1
- Renamed spec as per fedora packaging conventions (jason.dobies@redhat.com)

* Wed Apr 04 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.14-1
- Added create methods to CLI itself and default exit code for commands
  (jason.dobies@redhat.com)
- Sort sections/commands alphabetically by name on usage. Not perfect and
  eventually make customizable, but this works for now.
  (jason.dobies@redhat.com)
- Added exit code as the return value for CLI.run (jason.dobies@redhat.com)
- Added optional command description that is only displayed in the usage output
  (jason.dobies@redhat.com)
- Added syntactic sugar methods for create to section and command
  (jason.dobies@redhat.com)

* Wed Mar 28 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.13-1
- Added add/find command to root of the CLI (jason.dobies@redhat.com)
- Fixed bar rendering when prompt auto_wrap is enabled and the user supplies a
  multi-line message (jason.dobies@redhat.com)
- Refactoring to support better OO principles and make usage more flexible in
  subclasses (jason.dobies@redhat.com)

* Fri Mar 16 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.12-1
- Added support for default values on options (jason.dobies@redhat.com)

* Tue Mar 13 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.11-1
- Required check needs to run across all options, even those in groups
  (jason.dobies@redhat.com)
- Made option group output closer to OptionParser (jason.dobies@redhat.com)
- Added support for option groups (jason.dobies@redhat.com)
- Added in required/optional argument separation (totally gonna rip this out in
  a few minutes, but committing for archive purposes) (jason.dobies@redhat.com)
- This isn't the right place for that annotation (jason.dobies@redhat.com)

* Wed Mar 07 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.10-1
- Added parser implementation for common scenarios (jason.dobies@redhat.com)
- Upped docs version to match RPM version (jason.dobies@redhat.com)
- Max width calculation needs to take the color characters into account
  (jason.dobies@redhat.com)

* Fri Mar 02 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.9-1
- Added optional color for cli map output (jason.dobies@redhat.com)
- Hardened color command to handle None as the color (jason.dobies@redhat.com)

* Fri Mar 02 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.8-1
- Fixed infinite loop in small circumstances when remaining_line_indent is used
  (jason.dobies@redhat.com)
- Helps if you actually retain a handle to the parser (jason.dobies@redhat.com)
- Added timeout to threaded spinner (jason.dobies@redhat.com)
- Added ability to delete spinners/bars after they are finished
  (jason.dobies@redhat.com)
- Cleaned up the CLI map output (jason.dobies@redhat.com)
- Import clean up (jason.dobies@redhat.com)
- Cleaned up --help output (jason.dobies@redhat.com)

* Wed Feb 29 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.7-1
- Fixed for 2.4 compatibility (jason.dobies@redhat.com)

* Wed Feb 29 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.6-1
- new package built with tito

* Mon Feb 27 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.5-1
- Added remove section/command methods (jason.dobies@redhat.com)

* Mon Feb 27 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.4-1
- Added ThreadedSpinner class (jason.dobies@redhat.com)
- Added message support to Spinner (jason.dobies@redhat.com)
- Added parser override ability to bypass okaara abstraction. Added parser skip
  if no options are provided. (jason.dobies@redhat.com)
- kwargs passed to commands have the -- stripped. Added support for aliases in
  options. Added support for multiple values per option. Cleaned up usage
  message for invalid arguments. (jason.dobies@redhat.com)
- Max was doing alpha comparison instead of length (jason.dobies@redhat.com)
- Played with alignment in cli usage (jason.dobies@redhat.com)
- Abort-related fixes (jason.dobies@redhat.com)
- Fixed first pass logic on wrapping (jason.dobies@redhat.com)
- Don't strip off leading whitespace from the first line while wrapping; it's
  probably intended. After that, we can't really guarantee much
  (jason.dobies@redhat.com)
- Tweaked usage to be light years better (jason.dobies@redhat.com)
- Fixed usage output (jason.dobies@redhat.com)
- Corrected logic for prompt number (jason.dobies@redhat.com)
- Exposed find_section functionality in the CLI itself.
  (jason.dobies@redhat.com)
- No longer log non-tagged calls; it's too damn noisy (jason.dobies@redhat.com)
- Added tag support for progress bar and spinner (jason.dobies@redhat.com)
- Fix for the case where the progress bar's message wraps
  (jason.dobies@redhat.com)
- Call the content's __str__ in case the user is sloppy
  (jason.dobies@redhat.com)
- Made wrap functionality smart enough to not split words if possible
  (jason.dobies@redhat.com)
- Made wrap a first-class function and added center as an argument to write
  (jason.dobies@redhat.com)
- Added color to the progress widgets (jason.dobies@redhat.com)
- Syntax cleanup for 2.4 (jason.dobies@redhat.com)
- Small prompt clarifications (jason.dobies@redhat.com)
- Changed publish to use rsync to make it quicker (jason.dobies@redhat.com)
- Added better test example (jason.dobies@redhat.com)

* Mon Feb 06 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.3-1
- Added download links (jason.dobies@redhat.com)
- Added publish target (jason.dobies@redhat.com)
- Make the build noarch (jason.dobies@redhat.com)

* Mon Feb 06 2012 Jay Dobies <jason.dobies@redhat.com> 1.0.2-1
- Flushed out some unit tests (jason.dobies@redhat.com)
- Fixed typo (jason.dobies@redhat.com)
- Added interrupt simulation to the Script (jason.dobies@redhat.com)
- Ignoring PyCharm files and generated coverage reports
  (jason.dobies@redhat.com)
- Updated documentation for new approach to testing with prompts
  (jason.dobies@redhat.com)
- Added framework for shell documentation (jason.dobies@redhat.com)
- Tweaked testability classes (jason.dobies@redhat.com)
- Added prompt usage and examples (jason.dobies@redhat.com)
- These look better prefaced with get_ (jason.dobies@redhat.com)
- Added tag support for writes as well. Added utility methods to retrieve tags.
  (jason.dobies@redhat.com)
- Moved interruptable functionality to read method (jason.dobies@redhat.com)
- Added progress module usage documentation (jason.dobies@redhat.com)
- Use terminal size if not specified (jason.dobies@redhat.com)
- Overview page documentation (jason.dobies@redhat.com)
- Added shortcut to wrap from write() and terminal size calculation
  (jason.dobies@redhat.com)
- Updated copyright date and version (jason.dobies@redhat.com)
- Fixed documentation for ABORT (jason.dobies@redhat.com)
- More sphinx clean up (jason.dobies@redhat.com)
- Added wrapped iterator support to progress bar (jason.dobies@redhat.com)
- Migrated comments to rest syntax (jason.dobies@redhat.com)
- Updated docstrings for rest format (jason.dobies@redhat.com)
- Restructured docs index (jason.dobies@redhat.com)
- Removed generated docs from sphinx directory (jason.dobies@redhat.com)
- Initial implementation of sphinx documentation (jason.dobies@redhat.com)
- Fixed issue with usage rendering for sections (jason.dobies@redhat.com)
- Propagate flags to recursive call (jason.dobies@redhat.com)
- Module level docs (jason.dobies@redhat.com)
- Changed in place rendering technique to not use save/reset since it's not
  overly supported. (jason.dobies@redhat.com)
- Added spinner implementation (jason.dobies@redhat.com)
- Initial revision of the progress bar (jason.dobies@redhat.com)
- Added save/reset position calls (jason.dobies@redhat.com)
- Reworked clear behavior and added move command (jason.dobies@redhat.com)
- Added clear method and reordered file (jason.dobies@redhat.com)
- Added instance-level color disabling (jason.dobies@redhat.com)
- Changed default behavior to interruptable (jason.dobies@redhat.com)
- Added safe_start ability and enhanced rendering capabilities
  (jason.dobies@redhat.com)
- Added logic to calculate centering text (jason.dobies@redhat.com)
- Added auto-wrapping (jason.dobies@redhat.com)
- Added more colors (jason.dobies@redhat.com)
- Added first sample shell and made some fixes accordingly
  (jason.dobies@redhat.com)
- Continuing on prompt unit tests (jason.dobies@redhat.com)
