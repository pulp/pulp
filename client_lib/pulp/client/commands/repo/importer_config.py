from gettext import gettext as _

from pulp.client import parsers
from pulp.client import arg_utils
from pulp.client.extensions.extensions import PulpCliOption, PulpCliOptionGroup
from pulp.common.plugins import importer_constants as constants


GROUP_NAME_SYNC = _('Synchronization')
GROUP_NAME_THROTTLING = _('Throttling')
GROUP_NAME_SSL = _('Feed SSL')
GROUP_NAME_PROXY = _('Feed Proxy')
GROUP_NAME_UNIT_POLICY = _('Repository Content Behavior')


class OptionsBundle(object):
    """
    Contains all of the option instances that will be used to populate the
    ImporterConfigMixin. In most cases, this can be instantiated and used
    with no changes. In the event that a command using the mixin wishes to
    customize the default options, such as to change a description or
    to make an option required, the option instances in this class can be
    edited as appropriate.
    """

    def __init__(self):
        # -- synchronization options --------------------------------------------------

        d = _('URL of the external source repository to sync')
        self.opt_feed = PulpCliOption('--feed', d, required=False)

        d = _('if "true", the size and checksum of each synchronized file will be verified against '
              'the repo metadata')
        self.opt_validate = PulpCliOption('--validate', d, required=False,
                                          parse_func=parsers.pulp_parse_optional_boolean)

        # -- proxy options ------------------------------------------------------------

        d = _('proxy server url to use')
        self.opt_proxy_host = PulpCliOption('--proxy-host', d, required=False)

        d = _('port on the proxy server to make requests')
        self.opt_proxy_port = PulpCliOption('--proxy-port', d, required=False,
                                            parse_func=parsers.pulp_parse_optional_positive_int)

        d = _('username used to authenticate with the proxy server')
        self.opt_proxy_user = PulpCliOption('--proxy-user', d, required=False)

        d = _('password used to authenticate with the proxy server')
        self.opt_proxy_pass = PulpCliOption('--proxy-pass', d, required=False)

        # -- throttling options -------------------------------------------------------

        d = _('maximum bandwidth used per download thread, in bytes/sec, when '
              'synchronizing the repo')
        self.opt_max_speed = PulpCliOption('--max-speed', d, required=False,
                                           parse_func=parsers.pulp_parse_optional_positive_int)

        d = _('maximum number of downloads that will run concurrently')
        self.opt_max_downloads = PulpCliOption('--max-downloads', d, required=False,
                                               parse_func=parsers.pulp_parse_optional_positive_int)

        # -- ssl options --------------------------------------------------------------

        d = _('full path to the CA certificate that should be used to verify the '
              'external repo server\'s SSL certificate')
        self.opt_feed_ca_cert = PulpCliOption('--feed-ca-cert', d, required=False)

        d = _('if "true", the feed\'s SSL certificate will be verified against the '
              'feed_ca_cert')
        self.opt_verify_feed_ssl = PulpCliOption('--verify-feed-ssl', d, required=False,
                                                 parse_func=parsers.pulp_parse_optional_boolean)

        d = _('full path to the certificate to use for authorization when accessing the external '
              'feed')
        self.opt_feed_cert = PulpCliOption('--feed-cert', d, required=False)

        d = _('full path to the private key for feed_cert')
        self.opt_feed_key = PulpCliOption('--feed-key', d, required=False)

        # -- unit policy --------------------------------------------------------------

        d = _('if "true", units that were previously in the external feed but are no longer '
              'found will be removed from the repository')
        self.opt_remove_missing = PulpCliOption('--remove-missing', d, required=False,
                                                parse_func=parsers.pulp_parse_optional_boolean)

        d = _('count indicating how many non-latest versions of a unit to keep in a repository')
        self.opt_retain_old_count = PulpCliOption(
            '--retain-old-count',
            d, required=False,
            parse_func=parsers.pulp_parse_optional_nonnegative_int
        )


class ImporterConfigMixin(object):
    """
    Mixin to add to a command that will provide options on the CLI to accept the standard
    configuration values for a Pulp importer. This mixin also provides a method to parse
    the submitted user input and generate a config dict suitable for an importer
    config values. The produced configuration uses the keys in
    pulp.common.plugins.importer_constants.

    Touch points are provided to manipulate the options created by this mixin for each group
    (the populate_* methods). If options are added through overridden versions of those methods,
    the corresponding parse_* method should be updated to read those.
    The option groups are also stored as instance variables, further allowing the subclass
    the ability to manipulate them.

    The option instances that will be used in this mixin are contained in an OptionsBundle
    instance. If no changes to the option defaults are required, this can be omitted from
    this object's instantiation. If tweaks to the options are required, they should be done
    in an instance of OptionsBundle and then passed to this class at instantiation.

    This mixin must be used in a class that subclasses PulpCliCommand as well. The usage is as
    follows:

    * Define a class that extends both PulpCliCommand and ImporterConfigMixin.
    * Call the ImporterConfigMixin.__init__ method in its constructor. This will add the
      necessary options to the command.
    * In the execution method of the command, run parse_user_input(), passing in the args
      parsed from the user input. The result of that is a dict that can be used server-side
      to configure an importer.
    """

    def __init__(self,
                 options_bundle=None,
                 include_sync=True,
                 include_ssl=True,
                 include_proxy=True,
                 include_throttling=True,
                 include_unit_policy=True):

        # If the caller didn't dork with any of the options, instantiate one with the defaults
        self.options_bundle = options_bundle or OptionsBundle()

        # Created now, but won't be added to the command until the include_* flags are checked.
        # Stored as instance variables so a class using this mixin can further manipulate them.
        self.sync_group = PulpCliOptionGroup(GROUP_NAME_SYNC)
        self.ssl_group = PulpCliOptionGroup(GROUP_NAME_SSL)
        self.proxy_group = PulpCliOptionGroup(GROUP_NAME_PROXY)
        self.throttling_group = PulpCliOptionGroup(GROUP_NAME_THROTTLING)
        self.unit_policy_group = PulpCliOptionGroup(GROUP_NAME_UNIT_POLICY)

        if include_sync:
            self.populate_sync_group()
            self.add_option_group(self.sync_group)

        if include_ssl:
            self.populate_ssl_group()
            self.add_option_group(self.ssl_group)

        if include_proxy:
            self.populate_proxy_group()
            self.add_option_group(self.proxy_group)

        if include_throttling:
            self.populate_throttling_group()
            self.add_option_group(self.throttling_group)

        if include_unit_policy:
            self.populate_unit_policy()
            self.add_option_group(self.unit_policy_group)

    def populate_sync_group(self):
        """
        Adds options to the synchronization group. This is only called if the include_sync flag is
        set to True in the constructor.
        """
        self.sync_group.add_option(self.options_bundle.opt_feed)
        self.sync_group.add_option(self.options_bundle.opt_validate)

    def populate_ssl_group(self):
        """
        Adds options to the SSL group. This is only called if the include_ssl flag is
        set to True in the constructor.
        """
        self.ssl_group.add_option(self.options_bundle.opt_feed_ca_cert)
        self.ssl_group.add_option(self.options_bundle.opt_verify_feed_ssl)
        self.ssl_group.add_option(self.options_bundle.opt_feed_cert)
        self.ssl_group.add_option(self.options_bundle.opt_feed_key)

    def populate_proxy_group(self):
        """
        Adds options to the proxy group. This is only called if the include_proxy flag is
        set to True in the constructor.
        """
        self.proxy_group.add_option(self.options_bundle.opt_proxy_host)
        self.proxy_group.add_option(self.options_bundle.opt_proxy_port)
        self.proxy_group.add_option(self.options_bundle.opt_proxy_user)
        self.proxy_group.add_option(self.options_bundle.opt_proxy_pass)

    def populate_throttling_group(self):
        """
        Adds options to the throttling group. This is only called if the include_throttling flag is
        set to True in the constructor.
        """
        self.throttling_group.add_option(self.options_bundle.opt_max_downloads)
        self.throttling_group.add_option(self.options_bundle.opt_max_speed)

    def populate_unit_policy(self):
        """
        Adds options to the unit policy group. This is only called if the include_unit_policy flag
        is set to True in the constructor.
        """
        self.unit_policy_group.add_option(self.options_bundle.opt_remove_missing)
        self.unit_policy_group.add_option(self.options_bundle.opt_retain_old_count)

    def parse_user_input(self, user_input):
        """
        Reads the user input for any specified values that correspond to the importer config
        and returns a suitable dict for passing the importer as its configuration. As the values
        are read, they will be removed from the supplied user_input dict.

        The supplied user input should already have the arg_utils.convert_removed_options method
        run on it to properly strip out unset values and convert empty strings into None values for
        keys that should explicitly have a null value.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the importer config that can be stored on the repo
        :rtype:  dict
        """
        config = {}
        config.update(self.parse_sync_group(user_input))
        config.update(self.parse_ssl_group(user_input))
        config.update(self.parse_proxy_group(user_input))
        config.update(self.parse_throttling_group(user_input))
        config.update(self.parse_unit_policy(user_input))
        return config

    def parse_sync_group(self, user_input):
        """
        Reads any basic synchronization config options from the user input and packages them into
        the Pulp standard importer config format.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the config that can be stored on the repo
        :rtype:  dict
        """
        key_tuples = (
            (constants.KEY_FEED, self.options_bundle.opt_feed.keyword),
            (constants.KEY_VALIDATE, self.options_bundle.opt_validate.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            safe_parse(user_input, config, input_key, config_key)

        return config

    def parse_ssl_group(self, user_input):
        """
        Reads any SSL-related config options from the user input and packages them into
        the Pulp standard importer config format.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the config that can be stored on the repo
        :rtype:  dict
        """
        key_tuples = (
            (constants.KEY_SSL_CA_CERT, self.options_bundle.opt_feed_ca_cert.keyword),
            (constants.KEY_SSL_VALIDATION, self.options_bundle.opt_verify_feed_ssl.keyword),
            (constants.KEY_SSL_CLIENT_CERT, self.options_bundle.opt_feed_cert.keyword),
            (constants.KEY_SSL_CLIENT_KEY, self.options_bundle.opt_feed_key.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            safe_parse(user_input, config, input_key, config_key)

        arg_utils.convert_file_contents(('ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key'),
                                        config)

        return config

    def parse_proxy_group(self, user_input):
        """
        Reads any proxy-related config options from the user input and packages them into
        the Pulp standard importer config format.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the config that can be stored on the repo
        :rtype:  dict
        """
        key_tuples = (
            (constants.KEY_PROXY_HOST, self.options_bundle.opt_proxy_host.keyword),
            (constants.KEY_PROXY_PORT, self.options_bundle.opt_proxy_port.keyword),
            (constants.KEY_PROXY_USER, self.options_bundle.opt_proxy_user.keyword),
            (constants.KEY_PROXY_PASS, self.options_bundle.opt_proxy_pass.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            safe_parse(user_input, config, input_key, config_key)
        return config

    def parse_throttling_group(self, user_input):
        """
        Reads any throttling-related config options from the user input and packages them into
        the Pulp standard importer config format.

        :param user_input: keyword arguments from the CLI framework containing user input
        :type  user_input: dict

        :return: suitable representation of the config that can be stored on the repo
        :rtype:  dict
        """
        key_tuples = (
            (constants.KEY_MAX_DOWNLOADS, self.options_bundle.opt_max_downloads.keyword),
            (constants.KEY_MAX_SPEED, self.options_bundle.opt_max_speed.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            safe_parse(user_input, config, input_key, config_key)
        return config

    def parse_unit_policy(self, user_input):
        """
        Reads any unit policy-related config options from the user input and packages them into
        the Pulp standard importer config format.
        """
        key_tuples = (
            (constants.KEY_UNITS_REMOVE_MISSING, self.options_bundle.opt_remove_missing.keyword),
            (constants.KEY_UNITS_RETAIN_OLD_COUNT, self.options_bundle.opt_retain_old_count.keyword),
        )

        config = {}
        for config_key, input_key in key_tuples:
            safe_parse(user_input, config, input_key, config_key)
        return config


def safe_parse(user_input, config, input_keyword, config_keyword):
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
