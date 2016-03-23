"""
Contains functions related to working with the Nectar downloading library.
"""
import copy
from functools import partial

from nectar.config import DownloaderConfig

from pulp.common.plugins import importer_constants as constants
from pulp.server.managers.repo import _common as common_utils


# Mapping of importer config key to downloader config key
IMPORTER_DOWNLADER_CONFIG_MAP = (
    (constants.KEY_SSL_CA_CERT, 'ssl_ca_cert'),
    (constants.KEY_SSL_VALIDATION, 'ssl_validation'),
    (constants.KEY_SSL_CLIENT_CERT, 'ssl_client_cert'),
    (constants.KEY_SSL_CLIENT_KEY, 'ssl_client_key'),

    (constants.KEY_PROXY_HOST, 'proxy_url'),
    (constants.KEY_PROXY_PORT, 'proxy_port'),
    (constants.KEY_PROXY_USER, 'proxy_username'),
    (constants.KEY_PROXY_PASS, 'proxy_password'),

    (constants.KEY_BASIC_AUTH_USER, 'basic_auth_username'),
    (constants.KEY_BASIC_AUTH_PASS, 'basic_auth_password'),

    (constants.KEY_MAX_DOWNLOADS, 'max_concurrent'),
    (constants.KEY_MAX_SPEED, 'max_speed'),
)


def importer_to_nectar_config(importer, working_dir=None):
    """
    Translates a Pulp Importer into a DownloaderConfig instance.

    This function replaces importer_config_to_nectar_config. The primary difference is that it
    requires the database Importer model and is able to use that to configure Nectar to use the
    permanently stored TLS certificates and key rather than having Nectar write them out as
    temporary files. For now, this function uses the deprected function to avoid duplicating code.
    Once we have confirmed that the other function is no longer used by anything outside of this
    module it can be removed and its functionality can be moved here.

    :param importer:    The Importer that has a config to be translated to a Nectar config.
    :type  importer:    pulp.server.db.model.Importer
    :param working_dir: Allow the caller to override the working directory used
    :type  working_dir: str

    :rtype: nectar.config.DownloaderConfig
    """
    download_config_kwargs = {}

    # If the Importer config has TLS certificates and keys, we need to remove them and configure
    # nectar to use the permanently stored paths on the filesystem.
    config = copy.copy(importer.config)
    if constants.KEY_SSL_CA_CERT in config:
        del config[constants.KEY_SSL_CA_CERT]
        download_config_kwargs['ssl_ca_cert_path'] = importer.tls_ca_cert_path
    if constants.KEY_SSL_CLIENT_CERT in config:
        del config[constants.KEY_SSL_CLIENT_CERT]
        download_config_kwargs['ssl_client_cert_path'] = importer.tls_client_cert_path
    if constants.KEY_SSL_CLIENT_KEY in config:
        del config[constants.KEY_SSL_CLIENT_KEY]
        download_config_kwargs['ssl_client_key_path'] = importer.tls_client_key_path

    return importer_config_to_nectar_config(config, working_dir, download_config_kwargs)


def importer_config_to_nectar_config(importer_config, working_dir=None,
                                     download_config_kwargs=None):
    """
    DEPRECATED. Use importer_to_nectar_config instead.

    Translates the Pulp standard importer configuration into a DownloaderConfig instance.

    :param importer_config:        use the PluginCallConfiguration.flatten method to retrieve a
                                   single dict view on the configuration
    :type  importer_config:        dict
    :param working_dir:            Allow the caller to override the working directory used
    :type  working_dir:            str
    :param download_config_kwargs: Any additional keyword arguments you would like to include in the
                                   download config.
    :type  download_config_kwargs: dict

    :rtype: nectar.config.DownloaderConfig
    """
    if download_config_kwargs is None:
        download_config_kwargs = {}

    if working_dir is None:
        working_dir = common_utils.get_working_directory()

    download_config_kwargs['working_dir'] = working_dir
    adder = partial(_safe_add_arg, importer_config, download_config_kwargs)
    map(adder, IMPORTER_DOWNLADER_CONFIG_MAP)

    download_config = DownloaderConfig(**download_config_kwargs)
    return download_config


def _safe_add_arg(importer_config, dl_config, keys_tuple):
    """
    Utility to only set values in the downloader config if they are present in the importer's
    config.

    :type importer_config: dict
    :type dl_config: dict
    :param keys_tuple: tuple of importer key to download config key
    :type  keys_tuple: (str, str)
    """
    if keys_tuple[0] in importer_config:
        dl_config[keys_tuple[1]] = importer_config[keys_tuple[0]]
