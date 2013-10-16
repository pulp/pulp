# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains utilities for validating a Pulp standard importer config.
"""

from gettext import gettext as _

from pulp.common.plugins import importer_constants


class InvalidConfig(Exception):
    """
    Raised if the importer config fails validation for one or more properties. All
    values will be checked regardless of whether or not one is found to be invalid.
    The raised exception will contain all of the properties that failed along with
    the given value for each.
    """

    def __init__(self):
        super(InvalidConfig, self).__init__()

        self.failure_messages = [] # running list of all i18n'd failure messages encountered

    def add_failure_message(self, msg):
        self.failure_messages.append(msg)

    def has_errors(self):
        return len(self.failure_messages) > 0


def validate_config(config):
    """
    Validates all standard importer configuration options in the given configuration. All
    validations are performed regardless of whether or not an error is encountered. If a failure
    occurs, an exception is raised containing a list of all failure messages.

    :param config: the configuration object being validated
    :type  config: pulp.plugins.config.PluginCallConfiguration

    :raises InvalidConfig: if one or more validation tests fails
    """

    potential_exception = InvalidConfig()
    for v in VALIDATIONS:
        try:
            v(config)
        except ValueError, e:
            potential_exception.add_failure_message(e[0])

    if potential_exception.has_errors():
        raise potential_exception


def validate_feed_requirement(config):
    """
    Ensures the feed URL is a string if specified.

    This validation does not check the integrity of the feed URL.
    """
    feed_url = config.get(importer_constants.KEY_FEED)
    if feed_url and not isinstance(feed_url, basestring):
        msg = _('<%(feed_url)s> must be a string.')
        msg = msg % {'feed_url': importer_constants.KEY_FEED}
        raise ValueError(msg)


def validate_ssl_validation_flag(config):
    """
    Make sure the SSL validation enabled flag is a boolean.

    :param config: The configuration object that we are validating.
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    _run_validate_is_non_required_bool(config, importer_constants.KEY_SSL_VALIDATION)


def validate_ssl_ca_cert(config):
    """
    Make sure the ssl_ca_cert is a string if it is set.

    :param config: The configuration object that we are validating.
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    ssl_ca_cert = config.get(importer_constants.KEY_SSL_CA_CERT)
    if ssl_ca_cert is None:
        return  # optional
    if not isinstance(ssl_ca_cert, basestring):
        msg = _('The configuration parameter <%(name)s> should be a string, but it was %(type)s.')
        msg = msg % {'name': importer_constants.KEY_SSL_CA_CERT, 'type': type(ssl_ca_cert)}
        raise ValueError(msg)


def validate_ssl_client_cert(config):
    """
    Make sure the client certificte is a string if it is set.
    """
    ssl_client_cert = config.get(importer_constants.KEY_SSL_CLIENT_CERT)
    if ssl_client_cert is None and config.get(importer_constants.KEY_SSL_CLIENT_KEY) is None:
        return  # optional
    elif ssl_client_cert is None:
        # If the key is set, we should also have a cert
        msg = _('The configuration parameter <%(key_name)s> requires the <%(cert_name)s> parameter to also '
                'be set.')
        msg = msg % {'key_name': importer_constants.KEY_SSL_CLIENT_KEY, 'cert_name': importer_constants.KEY_SSL_CLIENT_CERT}
        raise ValueError(msg)

    if not isinstance(ssl_client_cert, basestring):
        msg = _('The configuration parameter <%(name)s> should be a string, but it was %(type)s.')
        msg = msg % {'name': importer_constants.KEY_SSL_CLIENT_CERT, 'type': type(ssl_client_cert)}
        raise ValueError(msg)


def validate_ssl_client_key(config):
    """
    Make sure the ssl_client_key is a string and that the cert is also provided, if the key is set.
    """
    ssl_client_key = config.get(importer_constants.KEY_SSL_CLIENT_KEY)
    if ssl_client_key is None:
        return  # optional

    if not isinstance(ssl_client_key, basestring):
        msg = _('The configuration parameter <%(name)s> should be a string, but it was %(type)s.')
        msg = msg % {'name': importer_constants.KEY_SSL_CLIENT_KEY, 'type': type(ssl_client_key)}
        raise ValueError(msg)


def validate_max_speed(config):
    """
    Make sure the max speed can be cast to a number, if it is defined.
    """
    max_speed = config.get(importer_constants.KEY_MAX_SPEED)
    if max_speed is None:
        return # optional

    try:
        max_speed = float(max_speed)
        if max_speed <= 0:
            raise ValueError()
    except ValueError:
        msg = _('The configuration parameter <%(max_speed_name)s> must be set to a positive numerical value, '
                'but is currently set to <%(max_speed_value)s>.')
        msg = msg % {'max_speed_name': importer_constants.KEY_MAX_SPEED, 'max_speed_value': max_speed}
        raise ValueError(msg)


def validate_max_downloads(config):
    """
    Make sure the maximum downloads value is a positive integer if it is set.
    """
    max_downloads = config.get(importer_constants.KEY_MAX_DOWNLOADS)
    if max_downloads is None:
        return # optional

    try:
        max_downloads = _cast_to_int_without_allowing_floats(max_downloads)
        if max_downloads < 1:
            raise ValueError()
    except ValueError:
        msg = _('The configuration parameter <%(num_threads_name)s> must be set to a positive integer, but '
                'is currently set to <%(num_threads)s>.')
        msg = msg % {'num_threads_name': importer_constants.KEY_MAX_DOWNLOADS, 'num_threads': max_downloads}
        raise ValueError(msg)


def validate_proxy_host(config):
    """
    Make sure the proxy host is a string if it is set.

    :param config: The configuration object that we are validating.
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    dependencies = [importer_constants.KEY_PROXY_PASS, importer_constants.KEY_PROXY_PORT,
                    importer_constants.KEY_PROXY_USER]
    proxy_url = config.get(importer_constants.KEY_PROXY_HOST)
    if proxy_url is None and all([config.get(parameter) is None for parameter in dependencies]):
        return # optional
    elif proxy_url is None:
        msg = _('The configuration parameter <%(name)s> is required when any of the following other '
                'parameters are defined: ' + ', '.join(dependencies) + '.')
        msg = msg % {'name': importer_constants.KEY_PROXY_HOST}
        raise ValueError(msg)

    if not isinstance(proxy_url, basestring):
        msg = _('The configuration parameter <%(name)s> should be a string, but it was %(type)s.')
        msg = msg % {'name': importer_constants.KEY_PROXY_HOST, 'type': type(proxy_url)}
        raise ValueError(msg)


def validate_proxy_port(config):
    """
    The proxy_port is optional. If it is set, this will make sure the proxy_url is also set, and that the port
    is a positive integer.

    :param config: The configuration object that we are validating.
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    proxy_port = config.get(importer_constants.KEY_PROXY_PORT)
    if proxy_port is None:
        return  # optional

    try:
        proxy_port = _cast_to_int_without_allowing_floats(proxy_port)
        if proxy_port < 1:
            raise ValueError()
    except ValueError:
        msg = _('The configuration parameter <%(name)s> must be set to a positive integer, but is currently '
                'set to <%(value)s>.')
        msg = msg % {'name': importer_constants.KEY_PROXY_PORT, 'value': proxy_port}
        raise ValueError(msg)


def validate_proxy_username(config):
    """
    The proxy_username is optional. If it is set, this method will ensure that it is a string, and it will
    also ensure that the proxy_password and proxy_url settings are set.

    :param config: The configuration object that we are validating.
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    proxy_username = config.get(importer_constants.KEY_PROXY_USER)
    # Proxy username is not required unless the password is set
    if proxy_username is None and config.get(importer_constants.KEY_PROXY_PASS) is None:
        return
    elif proxy_username is None:
        # If proxy_password is set, proxy_username must also be set
        msg = _('The configuration parameter <%(password_name)s> requires the <%(username_name)s> parameter '
                'to also be set.')
        msg = msg % {'password_name': importer_constants.KEY_PROXY_PASS,
                     'username_name': importer_constants.KEY_PROXY_USER}
        raise ValueError(msg)

    if not isinstance(proxy_username, basestring):
        msg = _('The configuration parameter <%(name)s> should be a string, but it was %(type)s.')
        msg = msg % {'name': importer_constants.KEY_PROXY_USER, 'type': type(proxy_username)}
        raise ValueError(msg)


def validate_proxy_password(config):
    """
    The proxy password setting is optional. However, if it is set, it must be a string. Also, if it
    is set, user must also be set.

    :param config: The configuration object that we are validating.
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    proxy_password = config.get(importer_constants.KEY_PROXY_PASS)
    if proxy_password is None and config.get(importer_constants.KEY_PROXY_USER) is None:
        return  # optional
    elif proxy_password is None:
        # If proxy_password is set, proxy_username must also be set
        msg = _('The configuration parameter <%(username_name)s> requires the <%(password_name)s> '
                'parameter to also be set.')
        msg = msg % {'password_name': importer_constants.KEY_PROXY_PASS,
                     'username_name': importer_constants.KEY_PROXY_USER}
        raise ValueError(msg)

    if not isinstance(proxy_password, basestring):
        msg = _('The configuration parameter <%(proxy_password_name)s> should be a string, but it was '
                '%(type)s.')
        msg = msg % {'proxy_password_name': importer_constants.KEY_PROXY_PASS,
                     'type': type(proxy_password)}
        raise ValueError(msg)


def validate_validate_downloads(config):
    """
    This (humorously named) method will validate the optional config option called
    "validate_downloads". If it is set, it must be a boolean, otherwise it may be None.

    :param config: the config to be validated
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    _run_validate_is_non_required_bool(config, importer_constants.KEY_VALIDATE)


def validate_remove_missing(config):
    """
    This method will validate the optional config setting called "remove_missing_units". If it is set, it must
    be a boolean, otherwise it may be None.

    :param config: the config to be validated
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    _run_validate_is_non_required_bool(config, importer_constants.KEY_UNITS_REMOVE_MISSING)


def validate_retain_old_count(config):
    """
    Makes sure the number of old units to retain is a number greater than or equal to 0.

    :param config: the config to be validated
    :type config: pulp.plugins.config.PluginCallConfiguration
    """
    retain_old_count = config.get(importer_constants.KEY_UNITS_RETAIN_OLD_COUNT)
    if retain_old_count is None:
        return # optional

    try:
        retain_old_count = _cast_to_int_without_allowing_floats(retain_old_count)
        if retain_old_count < 0:
            raise ValueError()
    except ValueError:
        msg = _('The configuration parameter <%(old_count_name)s> must be set to an integer greater '
                'than or equal to zero, but is currently set to <%(old_count)s>.')
        msg = msg % {'old_count_name': importer_constants.KEY_UNITS_RETAIN_OLD_COUNT,
                     'old_count': retain_old_count}
        raise ValueError(msg)


# -- utilities ----------------------------------------------------------------

def _cast_to_int_without_allowing_floats(value):
    """
    Attempt to return an int of the value, without allowing any floating point values. This is useful to
    ensure that you get an int type out of value, while allowing a string representation of the value. If
    there are any non numerical characters in value, this will raise ValueError.

    :param value: The value you want to validate
    :type value: int or basestring
    :return: The integer representation of value
    :rtype: int
    """
    if isinstance(value, basestring):
        # We don't want to allow floating point values
        if not value.isdigit():
            raise ValueError()
        # Interpret num_threads as an integer
        value = int(value)
    if not isinstance(value, int):
        raise ValueError()
    return value


def _run_validate_is_non_required_bool(config, setting_name):
    """
    Validate that the bool represented in the config by setting_name is either not set, or if it is set that
    it is a boolean value.

    :param config: the config to be validated
    :type config: pulp.plugins.config.PluginCallConfiguration
    :param setting_name: The name of the setting we wish to validate in the config
    :type setting_name: str
    """
    original_setting = setting = config.get(setting_name)
    if setting is None:
        # We don't require any settings
        return
    if isinstance(setting, basestring):
        setting = config.get_boolean(setting_name)
    if isinstance(setting, bool):
        return
    msg = _('The configuration parameter <%(name)s> must be set to a boolean value, but is '
            'currently set to <%(value)s>.')
    msg = msg % {'name': setting_name, 'value': original_setting}
    raise ValueError(msg)


VALIDATIONS = (
    validate_feed_requirement,
    validate_ssl_validation_flag,
    validate_ssl_ca_cert,
    validate_ssl_client_cert,
    validate_ssl_client_key,
    validate_max_speed,
    validate_max_downloads,
    validate_proxy_host,
    validate_proxy_port,
    validate_proxy_username,
    validate_proxy_password,
    validate_validate_downloads,
    validate_remove_missing,
    validate_retain_old_count,
)
