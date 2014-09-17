import json

import yaml

# Expected configuration sections
CONFIG_STRUCTURE = 'structure'
CONFIG_OS1_CREDENTIALS = 'os1_credentials'
CONFIG_PULP_TESTER = 'pulp_tester'

# Keywords in the configuration dictionary that can apply globally
DISTRIBUTION = 'distribution'
SECURITY_GROUP = 'security_group'
FLAVOR = 'flavor'
OS1_KEY = 'keypair_name'
PRIVATE_KEY = 'private_key'
CLOUD_CONFIG = 'cloud_config'
REPOSITORY_URL = 'repository'
TESTS_DESTINATION = 'test_result_destination'
TEST_SUITE_BRANCH = 'test_suite_branch'

GLOBAL_CONFIG_KEYWORDS = [DISTRIBUTION, SECURITY_GROUP, FLAVOR, OS1_KEY, PRIVATE_KEY, CLOUD_CONFIG,
                          REPOSITORY_URL, TESTS_DESTINATION, TEST_SUITE_BRANCH]

# Keywords that might be specified in each instance declaration
CHILDREN = 'children'
INSTANCE_NAME = 'instance_name'
ROLE = 'role'
HOSTNAME = 'hostname'

# Keywords added to the configuration dictionary during the deployment process
HOST_STRING = 'host_string'
SYSTEM_USER = 'user'
NOVA_SERVER = 'server'

# This is the bare minimum an instance configuration can contain
INSTANCE_CONFIG_KEYWORDS = [DISTRIBUTION, INSTANCE_NAME, SECURITY_GROUP, FLAVOR, OS1_KEY,
                            PRIVATE_KEY, CLOUD_CONFIG, REPOSITORY_URL, ROLE]

# Default location of the pickled configuration document
DEFAULT_FILE_PATH = 'environment.json'


def parse_and_validate_config_files(config_path, override_repo=None, override_test_branch=None):
    """
    Parse the given configuration file into a python dictionary

    :param config_path: the absolute path to the configuration file
    :type  config_path: str

    :return: A dictionary representation of the configuration file
    :rtype:  dict

    """
    if isinstance(config_path, str):
        config_path = [config_path]

    config = {}
    for config_file in config_path:
        with open(config_file, 'r') as conf:
            config = dict(config.items() + yaml.load(conf).items())

    # Collect the defaults from the configuration
    defaults = {}
    for key in GLOBAL_CONFIG_KEYWORDS:
        if key in config:
            defaults[key] = config.pop(key)

    if override_repo:
        defaults[REPOSITORY_URL] = override_repo
    if override_test_branch:
        defaults[TEST_SUITE_BRANCH] = override_test_branch

    if CONFIG_PULP_TESTER in config:
        config[CONFIG_STRUCTURE] = [config[CONFIG_STRUCTURE], config[CONFIG_PULP_TESTER]]

    # Validate all the required keys exist, and if they don't, apply the defaults
    _validate_instance_structure(config, defaults)

    return config


def config_generator(global_config):
    """
    Create a generator to iterate through the instance configurations

    :param global_config: The configuration dictionary that was parsed by parse_config_file
    :type  global_config: dict

    :return: An iterable that yields instance configuration dictionaries
    """
    configuration = global_config[CONFIG_STRUCTURE]
    if isinstance(configuration, dict):
        configuration = [configuration]

    child_configurations = []
    while configuration is not None:
        for instance_config in configuration:
            yield instance_config
            if CHILDREN in instance_config:
                child_configurations += instance_config[CHILDREN]
        if child_configurations:
            configuration = child_configurations
            child_configurations = []
        else:
            configuration = None


def _validate_instance_structure(config, defaults):
    """
    Validates that the given configuration does not contain any instance configurations with missing
    keys. If a key is missing and a default is provided, this is inserted into the dictionary. If it
    doesn't have a default, an exception is raised.

    :param config:      The configuration to validate
    :type  config:      dict
    :param defaults:    A dictionary of defaults to use if an instance config keyword is missing
    :type  defaults:    dict

    :raises ValueError: If a key in INSTANCE_CONFIG_KEYWORDS is missing and there is no default.
    """
    for instance_config in config_generator(config):
        missing_keys = []
        for key in INSTANCE_CONFIG_KEYWORDS:
            if key not in instance_config:
                # Apply the default if it exists
                if key in defaults:
                    instance_config[key] = defaults[key]
                else:
                    missing_keys.append(key)
            if missing_keys:
                msg = 'Missing %(key)s in %(config)s' % {'key': repr(missing_keys), 'config': repr(instance_config)}
                raise ValueError(msg)

        # Use the instance name as the hostname if it's not specified
        if HOSTNAME not in instance_config:
            instance_config[HOSTNAME] = instance_config[INSTANCE_NAME]


def get_parent_config(instance_name, global_config):
    """
    Retrieve the configuration of the given instance's parent

    :param instance_name: The instance name to find the parent of
    :type  instance_name: str
    :param global_config: The configuration dictionary returned from parse_config_file
    :type  global_config: dict

    :return: A dictionary containing the parent configuration, or None
    :rtype:  dict
    """
    for instance in config_generator(global_config):
        if CHILDREN in instance:
            for child in instance[CHILDREN]:
                if child[INSTANCE_NAME] == instance_name:
                    return instance


def get_instance_config(instance_name, global_config):
    """
    Get the configuration for the given instance name

    :param instance_name: The name of the instance to get the configuration for
    :type  instance_name: str
    :param global_config: The configuration dictionary returned from parse_config_file
    :type  global_config: dict

    :return: The instance configuration if it exists, otherwise None
    :rtype:  dict
    """
    for instance in config_generator(global_config):
        if instance[INSTANCE_NAME] == instance_name:
            return instance


def flatten_structure(global_config):
    """
    Flatten the structure dictionary to a list of dictionaries, where each dictionary contains
    an instance's configuration. This does not create a copy of global_config, so any changes
    made to the dictionaries applies to global_config

    :param global_config: The configuration dictionary to flatten.
    :type  global_config: dict

    :return: A list of dictionaries representing the instances
    :rtype:  list
    """
    flattened_structure = []
    for instance in config_generator(global_config):
        flattened_structure.append(instance)
    return flattened_structure


def save_config(global_config, file_path=None):
    """
    Save the configuration file to the given file path.

    :param global_config:
    :param file_path:
    :return:
    """
    file_path = file_path or DEFAULT_FILE_PATH
    with open(file_path, 'w') as config_file:
        json.dump(global_config, config_file)


def load_config(file_path=None):
    """

    :param file_path:
    :return:
    """
    file_path = file_path or DEFAULT_FILE_PATH
    with open(file_path, 'r') as config_file:
        return json.load(config_file)
