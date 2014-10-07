import itertools
import os


DEFAULT_PAGE_SIZE = 1000


def paginate(iterable, page_size=DEFAULT_PAGE_SIZE):
    """
    Takes any kind of iterable and chops it up into tuples of size "page_size".
    A generator is returned, so this can be an efficient way to chunk items from
    some other generator.

    :param iterable:    any iterable such as a list, tuple, or generator
    :type  iterable:    iterable
    :param page_size:   how many items should be in each returned tuple
    :type  page_size:   int

    :return:    generator of tuples, each including "page_size" number of items
                from "iterable", except the last tuple, which may contain
                fewer.
    :rtype:     generator
    """
    # this won't work properly if we give islice something that isn't a generator
    generator = (x for x in iterable)
    while True:
        page = tuple(itertools.islice(generator, 0, page_size))
        if not page:
            return
        yield page


def get_parent_directory(path):
    """
    Returns the path of the parent directory without a trailing slash on the end.

    Accepts a relative or absolute path to a file or directory, and returns the parent directory
    that contains the item specified by path. Using this method avoids issues introduced when
    os.path.dirname() is used with paths that include trailing slashes.

    The returned parent directory path does not include a trailing slash . The existence of the
    directory does not affect this functions behavior.

    :param path: file or directory path
    :type path: basestring

    :return: The path to the parent directory without a trailing slash
    :rtype: basestring
    """
    return os.path.dirname(path.rstrip(os.sep))
