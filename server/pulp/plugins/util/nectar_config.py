"""
Contains functions related to working with the Nectar downloading library.
"""

from functools import partial

from nectar.config import DownloaderConfig

from pulp.common.plugins import importer_constants as constants
from pulp.server.managers.repo import _common as common_utils


def importer_config_to_nectar_config(importer_config):
    """
    Translates the Pulp standard importer configuration into a DownloaderConfig instance.

    :param importer_config: use the PluginCallConfiguration.flatten method to retrieve a
           single dict view on the configuration
    :type  importer_config: dict

    :rtype: nectar.config.DownloaderConfig
    """

    # Mapping of importer config key to downloader config key
    translations = (
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

    download_config_kwargs = {'working_dir': common_utils.get_working_directory()}
    adder = partial(_safe_add_arg, importer_config, download_config_kwargs)
    map(adder, translations)

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
