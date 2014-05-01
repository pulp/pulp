from xml.etree import ElementTree

from pulp.server.exceptions import PulpCodedValidationException


def assert_validation_exception(method, error_codes, *args, **kwargs):
    """
    Test that the given method raises a validation exception with the given error codes
    as child exceptions

    :param method: The method to execute
    :type method: method
    :param error_codes: list of error codes that should be contained in the validation error
    :type error_codes: list of pulp.common.error_codes.Error
    :param args: Any positional arguments to pass through to the method
    :type args: list
    :param kwargs: Any keyword arguments that should be passed through to the method
    :type kwargs: dict
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
        for code in error_codes:
            errors_expected.add(code.code)

        expected_errors_missing = errors_expected.difference(errors_raised)
        if expected_errors_missing:
            raise AssertionError("The following errors were specified but not raised: %s"  %
                                 str(expected_errors_missing))
        errors_raised_unexpectedly = errors_raised.difference(errors_expected)
        if errors_raised_unexpectedly:
            raise AssertionError("The following errors were not specified but were raised: %s" %
                                 str(errors_raised_unexpectedly))
    else:
        raise AssertionError("A validation exception was not raised")


def compare_element(source, target):
    """
    Utility method to recursively compare two etree elements

    :param source: The source element to compare against the target
    :type source: xml.etree.ElementTree.Element
    :param target: The target element to compare against the source
    :type target: xml.etree.ElementTree.Element
    :raise AssertionError: if the elements do not match
    """
    if not ElementTree.iselement(source):
        raise AssertionError("Source is not an element")
    if not ElementTree.iselement(target):
        raise AssertionError("Target is not an element")

    if source.tag != target.tag:
        raise AssertionError("elements do not match.  Tags are different %s != %s" %
                             (source.tag, target.tag))

    #test keys
    source_keys = set(source.keys())
    target_keys = set(target.keys())

    if source_keys != target_keys:
        raise AssertionError("elements do not match.  Keys are different")

    for key in source_keys:
        if source.get(key) != target.get(key):
            raise AssertionError("Key values do not match.  Value mismatch for key %s: %s != %s" %
                                 (key, source.get(key), target.get(key)))

    if source.text != target.text:
        raise AssertionError("elements do not match.  Text is different\n%s\n%s" % (source.text,
                                                                                    target.text))

    #Use the deprecated getchildren method for python 2.6 support
    source_children = list(source.getchildren())
    target_children = list(target.getchildren())
    if len(source_children) != len(target_children):
        raise AssertionError("elements do not match.  Unequal number of child elements")

    for source_child, target_child in zip(source_children, target_children):
        compare_element(source_child, target_child)
