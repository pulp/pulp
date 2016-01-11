"""
This script removes empty directory structure from the pulp content directory. This is intended
to clean up incomplete orphan removal that was present in Pulp < 2.8.0. The script will need to be
run as the `apache` user.
"""
import os
import re

from pulp.server import config as pulp_config


storage_dir = pulp_config.config.get('server', 'storage_dir')
content_dir = os.path.join(storage_dir, 'content')
root_content_regex = re.compile(os.path.join(storage_dir, 'content', '[^/]+/?$'))


def rm_dir_leaf(path):
    """
    Removes an empty directory (leaf). If this call produces a new leaf, it will also be removed.

    Guarantees that path that is passed and all of its subpaths (down to one level up from the
    content directory) are not leafs or removed.

    :param path: a directory to be removed if it is a leaf
    :type  path: basestring
    :param basedir: directory that contains all content, should remain even if empty
    :type  basedir: basestring
    """
    if root_content_regex.match(path):
        return
    contents = os.listdir(path)
    if contents:
        return
    if not os.access(path, os.W_OK):
        return
    os.rmdir(path)

    path = os.path.dirname(path)
    print "Removed empty dir: {0}".format(path)
    rm_dir_leaf(path)


if __name__ == "__main__":

    for path, subdirs, files in os.walk(content_dir, topdown=False):
        if not (subdirs or files):
            rm_dir_leaf(path)
