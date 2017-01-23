Debugging
=========

.. _runtime_permormance:

Task Performance Analysis
-------------------------

The Python standard library provides the `cProfile <https://docs.python.org/2/library/profile.htm>`_
module to assist developers in collecting statistics that describes how often and for how long which
parts of the program executed.

.. note::
    Enabling cProfiling may cause a reduction in performance. It is not recommended for production
    unless enabled temporarily.

There is built in support for profiling individual tasks. This can be enabled by editing the
`server.conf` file::

    [profiling]
    enabled: true

This will, by default, put task profile output into `/var/lib/pulp/c_profiles` named per task ID.
You can modify the location these profiles are stored::

    [profiling]
    enabled: true
    directory: /var/www/html/pub

.. note::
    The ``apache`` user must be able to write to the path specified by ``directory``.


Custom Runtime Performance Analysis
-----------------------------------

Custom code locations be analyzed as well. To capture information about all function calls, add the
following lines of code before the code you are interested in analyzing::

    import cProfile
    pr = cProfile.Profile()
    pr.enable()

After the code that is of interest, add the following two lines::

    pr.disable()
    pr.dump_stats('/var/lib/pulp/profile_stats_dump')

.. note::
  The file should be written to somewhere the application has write access. `/tmp` does not seem to
  work for this use case. `/var/lib/pulp/` is guaranteed to provide Pulp write access.


Analyzing Profiles
------------------

Once the captured statistics are written to a file, the file can be examined in two ways. Using
`pstats` module in the Python standard library or
`cprofilev <https://github.com/ymichael/cprofilev>`_. The following command will open the file
using `pstats`::

    $ python -m pstats /var/lib/pulp/profile_stats_dump

Once in `pstats`, view the list of available commands by running `help`. The `stats` command
outputs the list of all calls made while profiler was enabled. The `sort` command is used to sort
the data by different metrics.

`cprofilev` provides a web UI for interacting with the data. You can examine the set of statistics
by installing `cprofilev` from PyPi and running it::

    $ sudo pip install cprofilev
    $ cprofilev -f ~/devel/profile_stats_dump

At this point, browse to http://localhost:4000/ to view profiling information.

In addition, `gprof2dot <https://github.com/jrfonseca/gprof2dot>`_ can convert the profiling output
into a dot graph. Make sure `graphviz <http://www.graphviz.org/Download.php>`_ is installed by yum
or dnf before using this tool. Then you can get statistics graph by installing `gprof2dot` from PyPI
and running it::

    $ sudo pip install gprof2dot
    $ gprof2dot -f pstats ~/devel/profile_stats_dump | dot -Tpng -o output.png
