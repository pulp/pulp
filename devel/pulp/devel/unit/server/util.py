from pulp.server.exceptions import PulpCodedValidationException


def assert_validation_exception(method, error_codes, *args, **kwargs):
    """
    Test that the given method raises a validation exception with the given error codes
    as child exceptions

    :param method: The method to execute
    :type method: method
    :param error_codes: list of error codes that should be contained in the validation error
    :type error_codes: list of pulp.common.error_codes.Error
    """
    try:
        method(*args, **kwargs)
    except PulpCodedValidationException as e:
        # Make sure we have appropriate sub errors
        if not error_codes and e.child_exceptions:
            raise AssertionError("No error codes were specified but the validation exception "
                                 "contains child exceptions")
        if error_codes and not e.child_exceptions:
            raise AssertionError("Error codes were specified but no child exceptions were raised "
                                 "within the PulpCodedValidationException")
        if not error_codes and not e.child_exceptions:
            # We expect no child exceptions and none exist
            return

        # Test to ensure the errors specified were included
        errors_raised = set()
        for child in e.child_exceptions:
            errors_raised.add(child.error_code.code)
        errors_expected = set()
        if error_codes:
            for code in error_codes:
                errors_expected.add(code.code)

        excpected_errors_missing = errors_expected.difference(errors_raised)
        if excpected_errors_missing:
            raise AssertionError("The following errors were specified but not raised: %s"  %
                                 str(excpected_errors_missing))
        errors_raised_unexpectedly = errors_raised.difference(errors_expected)
        if errors_raised_unexpectedly:
            raise AssertionError("The following errors were not specified but were raised: %s" %
                                 str(errors_raised_unexpectedly))
    else:
        raise AssertionError("A validation exception was not raised")