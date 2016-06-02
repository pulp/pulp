"""
This module contains utility code to be used by pulp.server.
"""
from contextlib import contextmanager
from gettext import gettext as _
import hashlib
import logging
import os
from shutil import copy, Error

from pulp.common import error_codes

from pulp.server.exceptions import PulpCodedException, PulpExecutionException


_logger = logging.getLogger(__name__)


# Number of bytes to read into RAM at a time when validating the checksum
CHECKSUM_CHUNK_SIZE = 8 * 1024 * 1024

# Constants to pass in as the checksum type in verify_checksum
TYPE_MD5 = hashlib.md5().name
TYPE_SHA = 'sha'
TYPE_SHA1 = hashlib.sha1().name
TYPE_SHA256 = hashlib.sha256().name

HASHLIB_ALGORITHMS = (TYPE_MD5, TYPE_SHA, TYPE_SHA1, TYPE_SHA256)

CHECKSUM_FUNCTIONS = {
    TYPE_MD5: hashlib.md5,
    TYPE_SHA: hashlib.sha1,
    TYPE_SHA1: hashlib.sha1,
    TYPE_SHA256: hashlib.sha256,
}


class InvalidChecksumType(ValueError):
    """
    Raised when the specified checksum isn't one of the supported TYPE_* constants.
    """
    pass


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


@contextmanager
def deleting(path):
    """
    Remove the file at path if possible, but don't let any exceptions bubble up. This is useful
    when you want to do something with a file, and delete it afterward no matter what. Example:

    with util.deleting(path):
        unit = MyUnit.from_file(path)
        unit.save()

    Like contextlib.closing, but more fun!

    :param path:    full path to a file that should be deleted
    :type  path:    basestring
    """
    yield
    try:
        os.remove(path)
    except Exception as e:
        _logger.warning(_('Could not remove file from location: {0}').format(e))


def sanitize_checksum_type(checksum_type):
    """
    Sanitize and validate the checksum type.

    This function will always return the given checksum_type in lower case, unless it is sha, in
    which case it will return "sha1". SHA and SHA-1 are the same algorithm, and so we prefer to use
    "sha1", since it is a more specific name. For some unit types (such as RPM), this can cause
    conflicts inside of Pulp when repos or uploads use a mix of sha and sha1. See
    https://bugzilla.redhat.com/show_bug.cgi?id=1165355

    This function also validates that the checksum_type is a recognized one from the list of known
    hashing algorithms.

    :param checksum_type: The checksum type we are sanitizing
    :type  checksum_type: basestring

    :return: A sanitized checksum type, converting "sha" to "sha1", otherwise returning the given
             checksum_type in lowercase.
    :rtype:  basestring

    :raises PulpCodedException: if the checksum type is not recognized
    """
    lowercase_checksum_type = checksum_type.lower()
    if lowercase_checksum_type == "sha":
        lowercase_checksum_type = "sha1"
    if lowercase_checksum_type not in HASHLIB_ALGORITHMS:
        raise PulpCodedException(error_code=error_codes.PLP1005, checksum_type=checksum_type)
    return lowercase_checksum_type


def calculate_checksums(file_object, checksum_types):
    """
    Calculate multiple checksums for the contents of an open file.

    :param file_object: an open file
    :type  file_object: file
    :param checksum_types: list of checksum types. Must be in CHECKSUM_FUNCTIONS.
    :type  checksum_types: list

    :return:    dict where keys are checksum types and values are checksum values.
    :rtype:     dict
    """
    hashers = {}
    for checksum_type in checksum_types:
        try:
            hashers[checksum_type] = CHECKSUM_FUNCTIONS[checksum_type]()
        except KeyError:
            raise InvalidChecksumType('Unknown checksum type [%s]' % checksum_type)

    file_object.seek(0)
    bits = file_object.read(CHECKSUM_CHUNK_SIZE)
    while bits:
        for hasher in hashers.values():
            hasher.update(bits)
        bits = file_object.read(CHECKSUM_CHUNK_SIZE)

    return dict((checksum_type, hasher.hexdigest()) for checksum_type, hasher in hashers.items())
