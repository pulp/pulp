Debugging
=========

.. _runtime_permormance:

Runtime Performance Analysis
----------------------------

The Python standard library provides a `cProfile` module to assist developers in collecting a set
of statistics that describes how often and for how long various parts of the program executed. Full
documentation for this module can be found `here <https://docs.python.org/2/library/profile.htm>`_.
To capture information about all function calls, add the following lines of code before the code
you are interested in analyzing::

    import cProfile
    pr = cProfile.Profile()
    pr.enable()

After the code that is of interest, add the following two lines::

    pr.disable()
    pr.dump_stats('/var/lib/pulp/profile_stats_dump')

.. note::
  The file should be written to somewhere the application has write access. `/tmp` does not seem to
  work for this use case. `/var/lib/pulp/` is guaranteed to provide Pulp write access.

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
into a dot graph. Make sure `graphviz <http://www.graphviz.org/Download.php>`_ is installed by yum or dnf before using
this tool. Then you can get statistics graph by installing `gprof2dot` from PyPi and running it::

    $ sudo pip install gprof2dot
    $ gprof2dot -f pstats ~/devel/profile_stats_dump | dot -Tpng -o output.png
