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

from gettext import gettext as _

from pulp.client import parsers
from pulp.client import arg_utils
from pulp.client.extensions.extensions import PulpCliOption, PulpCliOptionGroup, PulpCliCommand

# -- group names --------------------------------------------------------------

GROUP_NAME_THROTTLING = _('Throttling')
GROUP_NAME_SSL = _('Feed Authentication')
GROUP_NAME_PROXY = _('Feed Proxy')

# -- proxy options ------------------------------------------------------------

d = _('hostname of the proxy server to use')
OPT_PROXY_HOST = PulpCliOption('--proxy-host', d, required=False)

d = _('port on the proxy server to make requests')
OPT_PROXY_PORT = PulpCliOption('--proxy-port', d, required=False, parse_func=parsers.parse_positive_int)

d = _('username used to authenticate with the proxy server')
OPT_PROXY_USER = PulpCliOption('--proxy-user', d, required=False)

d = _('password used to authenticate with the proxy server')
OPT_PROXY_PASS = PulpCliOption('--proxy-pass', d, required=False)

# -- throttling options -------------------------------------------------------

d = _('maximum bandwidth used per download thread, in KB/sec, when '
      'synchronizing the repo')
OPT_MAX_SPEED = PulpCliOption('--max-speed', d, required=False, parse_func=parsers.parse_positive_int)

d = _('maximum number of downloads that will run concurrently')
OPT_MAX_DOWNLOADS = PulpCliOption('--max-downloads', d, required=False, parse_func=parsers.parse_positive_int)

# -- ssl options --------------------------------------------------------------

d = _('full path to the CA certificate that should be used to verify the '
      'external repo server\'s SSL certificate')
OPT_FEED_CA_CERT = PulpCliOption('--feed-ca-cert', d, required=False)

d = _('if "true", the feed\'s SSL certificate will be verified against the '
      'feed_ca_cert; defaults to true')
OPT_VERIFY_FEED_SSL = PulpCliOption('--verify-feed-ssl', d, required=False, parse_func=parsers.parse_boolean)

d = _('full path to the certificate to use for authentication when '
      'accessing the external feed')
OPT_FEED_CERT = PulpCliOption('--feed-cert', d, required=False)

d = _('full path to the private key for feed_cert')
OPT_FEED_KEY = PulpCliOption('--feed-key', d, required=False)

# -- classes ------------------------------------------------------------------

class DownloaderConfigMixin(object):
    """
    Mixin to add to a command that will provide options on the CLI to accept the standard
    configuration values for a Pulp downloader. This mixing also provides a method to parse
    the submitted user input and generate a config dict containing all of the downloader
    config values. That method should be called as the basis for creating the configuration for
    an importer using one of the Pulp downloaders.

    Touch points are provided to manipulate the options created by this mixin for each group
    (the populate_* methods). If options are added through overridden versions of those methods,
    the corresponding parse_* method should be updated to read those
    The option groups are also stored as instance variables, further allowing the subclass
    the ability to manipulate them.

    This mixin must be used in a class that subclasses PulpCliCommand as well. The usage is as
    follows:

    * Define a class that extends both PulpCliCommand and DownloaderConfigMixin.
    * Call the DownloaderConfigMixin.__init__ method in its constructor. This will add the
      necessary options to the command.
    * In the execution method of the command, run parse_user_input(), passing in the args
      parsed from the user input. The result of that is a dict that can be used server-side
      to configure a downloader. It's up to the plugin writer to dictate how to store that
      in the importer's configuration.
    """

    def __init__(self, include_ssl=True, include_proxy=True, include_throttling=True):
        # Created now, but won't be added to the command until the include_* flags are checked.
        # Stored as instance variables so a class using this mixin can further manipulate them.
        self.ssl_group = PulpCliOptionGroup(GROUP_NAME_SSL)
        self.proxy_group = PulpCliOptionGroup(GROUP_NAME_PROXY)
        self.throttling_group = PulpCliOptionGroup(GROUP_NAME_THROTTLING)

        if include_ssl:
            self.populate_ssl_group()
            self.add_option_group(self.ssl_group)

        if include_proxy:
            self.populate_proxy_group()
            self.add_option_group(self.proxy_group)

        if include_throttling:
            self.populate_throttling_group()
            self.add_option_group(self.throttling_group)

    def populate_ssl_group(self):
        """
        Adds options to the SSL group. This is only called if the include_ssl flag is
        set to True in the constructor.
        """
        self.ssl_group.add_option(OPT_FEED_CA_CERT)
        self.ssl_group.add_option(OPT_VERIFY_FEED_SSL)
        self.ssl_group.add_option(OPT_FEED_CERT)
        self.ssl_group.add_option(OPT_FEED_KEY)

    def populate_proxy_group(self):
        """
        Adds options to the proxy group. This is only called if the include_proxy flag is
        set to True in the constructor.
        """
        self.proxy_group.add_option(OPT_PROXY_HOST)
        self.proxy_group.add_option(OPT_PROXY_PORT)
        self.proxy_group.add_option(OPT_PROXY_USER)
        self.proxy_group.add_option(OPT_PROXY_PASS)

    def populate_throttling_group(self):
        """
        Adds options to the throttling group. This is only called if the include_throttling flag is
        set to True in the constructor.
        """
        self.throttling_group.add_option(OPT_MAX_DOWNLOADS)
        self.throttling_group.add_option(OPT_MAX_SPEED)

    def parse_user_input(self, user_input):
        """
        Reads the user input for any specified values that correspond to the downloader config
        and returns a suitable dict for passing the importer that it can then use as the downloader
        configuration. As the values are read, they will be removed from the supplied user_input
        dict.

        The supplied user input should already have the arg_utils.convert_removed_options method
        run on it to properly strip out unset values and convert empty strings into None values for
        keys that should explicitly have a null value.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the downloader config that can be stored on the repo
        :rtype:  dict
        """
        config = {}
        config.update(self.parse_ssl_group(user_input))
        config.update(self.parse_proxy_group(user_input))
        config.update(self.parse_throttling_group(user_input))
        return config

    @staticmethod
    def parse_ssl_group(user_input):
        """
        Reads any SSL-related config options from the user input and packages them into the
        format expected by the plugin-side parse to convert into a usable downloader config.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the config that can be stored on the repo
        :rtype:  dict
        """
        key_tuples = (
            ('ssl_ca_cert', OPT_FEED_CA_CERT.keyword),
            ('ssl_validation', OPT_VERIFY_FEED_SSL.keyword),
            ('ssl_client_cert', OPT_FEED_CERT.keyword),
            ('ssl_client_key', OPT_FEED_KEY.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            _safe_parse(user_input, config, input_key, config_key)

        arg_utils.convert_file_contents(('ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key'), config)

        return config

    @staticmethod
    def parse_proxy_group(user_input):
        """
        Reads any proxy-related config options from the user input and packages them into the
        format expected by the plugin-side parse to convert into a usable downloader config.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the config that can be stored on the repo
        :rtype:  dict
        """
        key_tuples = (
            ('proxy_host', OPT_PROXY_HOST.keyword),
            ('proxy_port', OPT_PROXY_PORT.keyword),
            ('proxy_username', OPT_PROXY_USER.keyword),
            ('proxy_password', OPT_PROXY_PASS.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            _safe_parse(user_input, config, input_key, config_key)
        return config

    @staticmethod
    def parse_throttling_group(user_input):
        """
        Reads any throttling-related config options from the user input and packages them into the
        format expected by the plugin-side parse to convert into a usable downloader config.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the config that can be stored on the repo
        :rtype:  dict
        """
        key_tuples = (
            ('max_downloads', OPT_MAX_DOWNLOADS.keyword),
            ('max_speed', OPT_MAX_SPEED.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            _safe_parse(user_input, config, input_key, config_key)
        return config


def _safe_parse(user_input, config, input_keyword, config_keyword):
    """
    Prior to calling the parse methods in this class, the user input should have been pre-scrubbed
    to remove keys whose value were None (see parse_user_input docs). We can't simply pop with
    a default of None on all the potential keys since it will add them back in when we really
    want to omit them and let the plugin default them.

    This method is called for each key that could be parsed from the user input. It will only
    add the key to the config if it's present in the user input.

    :param user_input: dict parsed by the CLI framework
    :type  user_input: dict
    :param config: running configuration that is being populated by the parse call; the key/value
           checked by this method will be stored in here if applicable
    :type  config: dict
    :param input_keyword: key the user will have used to indicate a particular value
    :type  input_keyword: str
    :param config_keyword: key the value should be stored at in the configuration
    :type  config_keyword: str
    """
    if input_keyword in user_input:
        config[config_keyword] = user_input[input_keyword]
