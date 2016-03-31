"""
This migration inspects all the Importers and writes any TLS certificates or keys they have to local
storage, as required by the streamer.
"""
import errno
import os

from pulp.server.db import connection


LOCAL_STORAGE = os.path.join('/', 'var', 'lib', 'pulp')


def migrate():
    """
    Write the TLS certificates and keys for each Importer to local storage.
    """
    for importer in connection._DATABASE.repo_importers.find():
        pki_path = _pki_path(importer['repo_id'], importer['importer_type_id'])
        pem_key_paths = (
            ('ssl_ca_cert', 'ca.crt'),
            ('ssl_client_cert', 'client.crt'),
            ('ssl_client_key', 'client.key'))
        for key, filename in pem_key_paths:
            _write_pem_file(pki_path, importer['config'], key, filename)


def _mkdir(path):
    """
    Create the specified directory, ignoring if the path exists.

    :param path: The absolute path to the directory.
    :type  path: str
    """
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise


def _pki_path(repo_id, importer_type_id):
    """
    Return the path where an importer's PKI data should be written to disk.

    :param repo_id:          The repo_id that the importer is attached to.
    :type  repo_id:          basestring
    :param importer_type_id: The importer_type_id of the importer
    :type  importer_type_id: basestring
    :return:                 A path to the folder that the pki data should be written to.
    :rtype:                  basestring
    """
    return os.path.join(
        LOCAL_STORAGE, 'importers',
        '{0}-{1}'.format(repo_id, importer_type_id), 'pki')


def _write_pem_file(pki_path, config, config_key, filename):
    """
    Write the PEM data from config[config_key] to the given path, if the key is defined and
    is "truthy".

    :param pki_path:   The base path where the pem file should be written.
    :type  pki_path:   basestring
    :param config:     The dictionary found in an importer's config.
    :type  config:     dict
    :param config_key: The key corresponding to a value in self.config to write to path.
    :type  config_key: basestring
    :param filename:   The filename to write the PEM data to.
    :type  filename:   basestring
    """
    if config_key in config and config[config_key]:
        if not os.path.exists(pki_path):
            _mkdir(os.path.dirname(pki_path))
            os.mkdir(pki_path, 0700)
        with os.fdopen(
                os.open(os.path.join(pki_path, filename), os.O_WRONLY | os.O_CREAT, 0600),
                'w') as pem_file:
            pem_file.write(config[config_key])
