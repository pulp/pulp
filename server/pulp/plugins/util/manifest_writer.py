import csv
import hashlib
import os

from pulp.common.plugins.distributor_constants import MANIFEST_FILENAME


# not much science behind this
CHUNK_SIZE = 2 ** 16


def make_manifest_for_dir(path):
    """
    creates a PULP_MANIFEST file in the specified directory

    The file is CSV with three fields: filename, sha256 checksum value, and size in bytes

    :param path:    full path to the directory where the manifest should be created
    :type  path:    basestring
    """
    file_paths = [os.path.join(path, filename) for filename in os.listdir(path)
                  if filename != MANIFEST_FILENAME]
    with open(os.path.join(path, MANIFEST_FILENAME), 'w') as open_file:
        print dir(open_file)
        print open_file.closed
        writer = csv.writer(open_file)
        for fullpath in filter(os.path.isfile, file_paths):
            size = os.path.getsize(fullpath)
            filename = os.path.basename(fullpath)
            checksum = get_sha256_checksum(fullpath)

            writer.writerow([filename, checksum, size])


def get_sha256_checksum(path):
    """
    calculate and return the sha256 checksum of a file

    :param path:    full path to the file
    :type  path:    basestring

    :return:    sha256 checksum
    :rtype:     basestring
    """
    hasher = hashlib.sha256()
    with open(path) as open_file:
        chunk = open_file.read(CHUNK_SIZE)
        while chunk:
            hasher.update(chunk)
            chunk = open_file.read(CHUNK_SIZE)
    return hasher.hexdigest()
