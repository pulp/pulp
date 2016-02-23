# pulp coverage

In this directory, there is a `sitecustomize.py` module, which turns on coverage tracking for all
python interpreters started after its installation in a hosts's site-packages dir. Alongside that
module is a script, `coverage_hook`, which is capable of installing and uninstalling the
sitecustomize coverage hook, as well as a requirements file, which contains all the packages
depended on by `coverage_hook` and `sitecustomize.py` that are not already provided by Pulp or any
of its plugins.

`coverage_hook` has several subcommands and options; consult that script's help for more detailed
usage information. Of particular note, the 'report' subcommand allows for additionally generating
html and xml report types.

Because `coverage_hook` copies files to (and removes files from) python's site-wide packages dir,
and must be able to read coverage data by any user, _root privileges are required_.

## The workflow

To generate a coverage report for Pulp usage, here are the steps to take:

- Stop all running Pulp processes (including all workers and https WSGI daemons)
- Install the coverage hook (`sudo ./coverage_hook install`)
- Start up Pulp, workers/httpd/etc.
- Use Pulp (e.g. run the `pulp-smash` against it)
- Stop all running Pulp processes, which now causes them to write out their coverage data
- Generate a coverage report (`sudo ./coverage_hook report /path/to/report/dir`)

*(optional)*

- If no longer generating reports, uninstall the coverage hook (`sudo ./coverage_hook uninstall`)
  Remember to restart all Pulp processes after uninstalling.

## The details

Coverage recording is done by the [coverage.py](https://coverage.readthedocs.org/en/latest/)
plugin. The sitecustomize hook method used to start the coverage engine is based on the method
described [in the coverage docs](https://coverage.readthedocs.org/en/latest/subprocess.html),
but is specifically tailored to tracking coverage in Pulp, Pulp plugins, and Pulp-related
dependencies only. Not all python modules load the sitecustomize hook by default, WSGI scripts,
for example. Those python modules are patched to explicitly import sitecustomize and start the
coverage engine before importing any other code.

The coverage hook management script was created to make it reasonably simple for someone testing
Pulp to enable, disable, and report on pulp coverage tracking, while providing a minimal user
interface to allow for changing the functionality without having to break scripts that may use the
hook manager.

By default, coverage data is written to `/srv/pulp_coverage`. This directory is created with
the same permissions that `/tmp` normally has, allowing all processes to write their coverage data
there. This can be overridden by setting the `PULP_COVERAGE_ROOT` environment var to the desired
coverage data dir. This environment var must be set system-wide (e.g. in `/etc/environment`) before
the coverage hook is installed to have any effect, and all pulp services must be started/restarted
after installation. `/srv` is used instead of `/tmp` because `mod_wsgi` or apache itself appears
to handle `/tmp` specially, with the result that the coverage reporting data is not written to the
filesystem when a directory in `/tmp` is used as the coverage root.

The coverage engine is configured to add a unique suffix to each data file,
including the hostname of the system on which coverage was run, the pid of the process recording
coverage, and a random string to further prevent filename collisions. When generating reports,
these files are all combined before reporting, and can optionally be erased after the reports
are created.

If desired, data files from other coverage runs can be manually added to this directory. As long
as they conform to the naming scheme used by the files already there, they will also be included
in the final report when the coverage data is combined.

## SELinux

At the time of this writing, this has not yet been tested with SELinux set to Enforcing.
