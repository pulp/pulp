from pulp.server.auth import authorization


def _assert_auth_decorator_general(required_operation):
    """
    Returns a method that asserts a future call to the returned method uses
    the required_operation specified here.

    This is a helper method to make it easier to mock the @auth_required
    decorator. The returned function should be used to mock the
    pulp.server.webservices.controllers.decorators._verify_auth function
    which is called as part of the @auth_required decorator codepath.

    An AssertionError will be raised if the @auth_required decorator is not
    called with the required_operation specified. required_operation may also
    be None to specify no authorization operations but require authentication.

    NOTE: This side-steps authorization and authentication altogether.
    Since this is to be used exclusively by the unit tests that is OK.

    :type required_operation: int or None
    :param required_operation: An operation from
                               pulp.server.auth.authorization that needs to
                               be used in a future call to @auth_required.
                               The operation can also be None.

    :return: A function that can be used to mock the _verify_auth method. An
             AssertionError will be raised if the @auth_required decorator
             does not have the correct authorization. The returned function
             causes authorization and authentication to be skipped completely.
    """
    def _specific_auth_assertions(self, operation, super_user_only, method,
                                  *args, **kwargs):
        if required_operation != operation:
            _lookup = authorization._lookup_operation_name
            msg = "Expected authorization requirement of %s, but instead " \
                  "got %s"
            try:
                required_name = _lookup(required_operation)
            except KeyError:
                required_name = None
            try:
                actual_name = _lookup(operation)
            except KeyError:
                actual_name = None
            raise AssertionError(msg % (required_name, actual_name))
        return method(self, *args, **kwargs)
    return _specific_auth_assertions


def assert_auth_CREATE():
    """
    Customizes the _assert_auth_decorator_general to be CREATE specific.

    :return: The function returned by _assert_auth_decorator_general
    """
    return _assert_auth_decorator_general(authorization.CREATE)


def assert_auth_READ():
    """
    Customizes the _assert_auth_decorator_general to be READ specific.

    :return: The function returned by _assert_auth_decorator_general
    """
    return _assert_auth_decorator_general(authorization.READ)


def assert_auth_UPDATE():
    """
    Customizes the _assert_auth_decorator_general to be UPDATE specific.

    :return: The function returned by _assert_auth_decorator_general
    """
    return _assert_auth_decorator_general(authorization.UPDATE)


def assert_auth_DELETE():
    """
    Customizes the _assert_auth_decorator_general to be DELETE specific.

    :return: The function returned by _assert_auth_decorator_general
    """
    return _assert_auth_decorator_general(authorization.DELETE)


def assert_auth_EXECUTE():
    """
    Customizes the _assert_auth_decorator_general to be EXECUTE specific.

    :return: The function returned by _assert_auth_decorator_general
    """
    return _assert_auth_decorator_general(authorization.EXECUTE)


def assert_auth_NONE():
    """
    Customizes the _assert_auth_decorator_general to use no operation.

    :return: The function returned by _assert_auth_decorator_general
    """
    return _assert_auth_decorator_general(None)
