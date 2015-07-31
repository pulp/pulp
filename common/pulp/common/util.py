def encode_unicode(path):
    """
    Check if given path is a unicode and if yes, return utf-8 encoded path
    """
    if type(path) is unicode:
        path = path.encode('utf-8')
    return path


def decode_unicode(path):
    """
    Check if given path is of type str and if yes, convert it to unicode
    """
    if type(path) is str:
        path = path.decode('utf-8')
    return path


def ensure_utf_8(s):
    """
    Ensure any string passed in is properly encoded to utf-8
    Simply returns the parameter if it is not an instance of basestring,
    otherwise it attempts to decode the string from latin-1, if it's already
    an instance of unicode, and then encode it to utf-8.

    @param s: string to ensure utf-8 encoding on
    @return: encoded string or original parameter if not a string
    """
    if not isinstance(s, basestring):
        return s
    if isinstance(s, str):
        s = s.decode('iso-8859-1')
    u = s.encode('utf-8')
    return u


def partial(func, *args, **kwds):
    """
    Python 2.4 doesn't provide functools so provide our own version of the partial method
    """
    return lambda *fargs, **fkwds: func(*(args + fargs), **dict(kwds, **fkwds))
