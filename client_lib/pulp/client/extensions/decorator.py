from pulp.client.extensions.loader import DEFAULT_PRIORITY, PRIORITY_VAR


def priority(value=DEFAULT_PRIORITY):
    """
    Use this to put a decorator on an "initialize" method for an extension, which
    will set that extension's priority level.

    :param value: priority value, which defaults to 5
    :type  value: int
    :return: decorator
    """
    def decorator(f):
        setattr(f, PRIORITY_VAR, value)
        return f
    return decorator
