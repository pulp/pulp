# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

# XXX this is not a dumping grounds for any random code. It is a place to put
# paradigm-changing code that allows you to get unique or more efficient behaviors

from pulp.server.exceptions import PulpExecutionException


class Singleton(type):
    """
    Singleton metaclass. To make a class instance a singleton, use this class
    as your class's metaclass as follows:

    class MyClass(object):
        __metaclass__ = Singleton

    Singletons are created by passing the exact same arguments to the
    constructor. For example:

    class T():
        __metaclass__ = Singleton

        def __init__(self, value=None):
            self.value = value

    t1 = T()
    t2 = T()
    t1 is t2
    True
    t3 = T(5)
    t4 = T(5)
    t3 is t4
    True
    t1 is t3
    False
    """

    def __init__(self, name, bases, ns):
        super(Singleton, self).__init__(name, bases, ns)
        self.instances = {}

    def __call__(self, *args, **kwargs):
        key = (tuple(args), tuple(sorted(kwargs.items())))
        return self.instances.setdefault(key, super(Singleton, self).__call__(*args, **kwargs))


class subdict(dict):
    """
    A dictionary that possesses a subset of the keys and related values from
    another dictionary.
    """

    def __init__(self, d, keys=()):
        """
        @param d: mapping type to be a subdict of
        @param keys: list of keys to copy from d
        """
        n = dict((k, v) for k, v in d.items() if k in keys)
        super(subdict, self).__init__(n)

# topological sorting ----------------------------------------------------------

class NoTopologicalOrderingExists(PulpExecutionException):
    """
    Raised when no topological ordering exists on a directed graph.
    """
    pass


def topological_sort(graph):
    """
    Perform a topological sort on a directed graph.
    The ordering returned is "sink-first". Think of the directed edges as a
    "greater-than" relation and the ordering would correspond to "ascending".
    v1 -> v2 == v1 > v2
    @param graph: directed graph represented as a dictionary
    @type  graph: dict
    @raise NoTopologicalOrderingExists: if no topological ordering exists
    @return: list of vertices of the graph in a topological ordering
    @rtype:  list
    """
    assert isinstance(graph, dict)
    discovered_vertices = set()
    completed_vertices = set()
    sorted_vertices = []

    def _recursive_topological_sort(vertex):
        # topological sort via depth-first-search
        if vertex in completed_vertices:
            # vertex and it's subtree is already sorted
            return
        if vertex in discovered_vertices:
            # we've run into an ancestor, which means a cycle
            raise NoTopologicalOrderingExists()
        discovered_vertices.add(vertex)
        for adjacent in graph[vertex]:
            _recursive_topological_sort(adjacent)
        discovered_vertices.discard(vertex)
        completed_vertices.add(vertex)
        sorted_vertices.append(vertex)

    for vertex in graph:
        _recursive_topological_sort(vertex)

    return sorted_vertices
