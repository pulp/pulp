"""
This module contains utility code to be used by pulp.server.
"""
import os
from shutil import copy, Error

from gettext import gettext as _

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


class TopologicalSortError(PulpExecutionException):

    def __init__(self, vertex):
        PulpExecutionException.__init__(self, vertex)
        self.vertex = vertex

    def __str__(self):
        pass

    def data_dict(self):
        return {'vertex': self.vertex}


class CycleExists(TopologicalSortError):
    """
    Raised when no topological ordering exists on a directed graph.
    """

    def __str__(self):
        msg = _('Cycle at vertex: %(v)s' % {'v': str(self.vertex)})
        return msg.encode('utf-8')


class MalformedGraph(TopologicalSortError):
    """
    Raised when a graph has an edge (v1, v2) and v2 does not have a
    corresponding adjacency list.
    """

    def __str__(self):
        msg = _('Vertex missing from graph: %(v)s' % {'v': str(self.vertex)})
        return msg.encode('utf-8')


def topological_sort(graph):
    """
    NOTE: This does not seem to be used by any part of pulp

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
            # vertex and its subtree are already sorted
            return

        if vertex in discovered_vertices:
            # we've run into an ancestor, which means a cycle
            raise CycleExists(vertex)

        if vertex not in graph:
            # we've run into an edge to nowhere
            raise MalformedGraph(vertex)

        discovered_vertices.add(vertex)

        for adjacent in graph[vertex]:
            _recursive_topological_sort(adjacent)

        discovered_vertices.discard(vertex)
        completed_vertices.add(vertex)
        sorted_vertices.append(vertex)

    for vertex in graph:
        _recursive_topological_sort(vertex)

    return sorted_vertices


class Delta(dict):
    """
    The delta of a model object.
    Contains the primary key and keys/values specified in the filter.
    """

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, obj, filter=()):
        """
        @param obj: A model object (dict).
        @type obj: Model|dict
        @param filter: A list of dictionary keys to include
                       in the delta.
        @type filter: str|list
        """
        dict.__init__(self)
        if isinstance(filter, basestring):
            filter = (filter,)
        for k, v in obj.items():
            if k in filter:
                self[k] = v


def copytree(src, dst, symlinks=False, ignore=None):
    """
    Copies src tree to dst

    shutil.copytree method uses copy2() and copystat() to perform the recursive copy of a
    directory. Both of these methods copy the attributes associated with the files. When copying
    files from /var/cache/pulp to /var/lib/pulp, we don't want to copy the SELinux security context
    labels.

    After 100 errors, this function gives up and raises shutil.Error

    :param src: Source directory rooted at src
    :type  src: basestring
    :param dst: Destination directory, a new directory and any parent directories are created if
                any are missing
    :type  dst: basestring
    :param symlinks: If true, symlinks are copied as symlinks and metadata of original links is not
                     copied. If false, the contents and metadata of symlinks is copied to the new
                     tree.
    :type  symlinks: boolean
    :param ignore: If provided, it receives as its arguments the directory being visited by
                   copytree and the content of directory as returned by os.listdir(). The callable
                   must return a sequence of directory and file names relative to the current
                   directory (i.e. a subset of the items in its second argument); these names will
                   then be ignored in the copy process.
    :type  ignore: Callable

    :raises shutil.Error:   If there are one or more errors copying files. After 100 errors, the
                            operation aborts and raises this exception with those errors.
    """

    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore)
            else:
                # Don't need to copy attributes
                copy(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
        # give up if there have been too many errors
        if len(errors) >= 100:
            break
    if errors:
        raise Error(errors)
