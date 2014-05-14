import os


def compare_dict(source, target):
    """
    Utility method to compare dictionaries since python 2.6 doesn't support assertDictEquals

    :param source: The source dictionary to compare against the target
    :type source: dict
    :param target: The target dictionary to compare against the source
    :type target: dict
    :raise AssertionError: if the dictionaries do not match
    """
    if not isinstance(source, dict):
        raise AssertionError("Source is not a dictionary")
    if not isinstance(target, dict):
        raise AssertionError("Target is not a dictionary")

    #test keys
    source_keys = set(source.keys())
    target_keys = set(target.keys())

    if source_keys != target_keys:
        source_keys_str = ', '.join(map(str, source_keys.difference(target_keys)))
        target_keys_str = ', '.join(map(str, target_keys.difference(source_keys)))

        msg = "Dictionaries do not match. "
        if source_keys_str:
            msg += "The following keys are in the source but not the target: [%s]. " % \
                source_keys_str
        if target_keys_str:
            msg += "The following keys are in the target but not the source: [%s]. " % \
                target_keys_str
        raise AssertionError(msg)

    for key in source_keys:
        if source[key] != target[key]:
            raise AssertionError("Dictionaries do not match.  Value mismatch for key %(key)s.  "
                                 "%(value1)s is not equal to %(value2)s" %
                                 {'key': key, 'value1': source[key], 'value2': target[key]})


def assert_body_matches_async_task(body, task):
    assert body['spawned_tasks'][0]['task_id'] == task.id


def touch(path):
    """
    Create a file at the specified path.  If the path does not exist already,
    create the parent directories for the file specified

    :param path: The canonical file path to create
    :type path: str
    """
    parent = os.path.dirname(path)

    if not os.path.exists(parent):
        os.makedirs(parent)

    file_handle = open(path, 'w')
    file_handle.close()
