import json
import os
import tempfile
import time

from fabric import network as fabric_network
from fabric.api import env, get, put, run, local, settings
from fabric.context_managers import hide
from fabric.exceptions import NetworkError
import yaml

from config_utils import HOSTNAME, HOST_STRING, INSTANCE_NAME, PRIVATE_KEY, ROLE, REPOSITORY_URL, TEST_SUITE_BRANCH
from config_utils import get_parent_config, get_instance_config, config_generator, flatten_structure

# Fabric configuration
env.connection_attempts = 4
env.timeout = 30
env.disable_known_hosts = True
env.abort_on_prompts = True
env.abort_exception = RuntimeError

# Locations of the puppet manifests
PULP_CONSUMER_MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'puppet/pulp-consumer.pp')
PULP_SERVER_MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'puppet/pulp-server.pp')

# The Puppet module dependencies
PUPPET_MODULES = [
    'puppetlabs-stdlib',
    'puppetlabs-mongodb',
    'dprince-qpid',
    'jcline-pulp'
]

# Puppet fact names
PULP_SERVER_FACT = 'pulp_server'
PULP_REPO_FACT = 'pulp_repo'

# List of currently supported roles
PULP_SERVER_ROLE = 'server'
PULP_CONSUMER_ROLE = 'consumer'
PULP_TESTER_ROLE = 'tester'

# Constants for pulp-automation YAML configuration
CONSUMER_YAML_KEY = 'consumers'
SERVER_YAML_KEY = 'pulp'
ROLES_KEY = 'ROLES'

# The dependencies for pulp-automation
PULP_AUTO_DEPS = [
    'gcc',
    'git',
    'm2crypto',
    'python-devel',
    'python-pip',
    'python-qpid'
]

# Configuration commands
TEMPORARY_MANIFEST_LOCATION = '/tmp/manifest.pp'
PUPPET_MODULE_INSTALL = 'sudo puppet module install --force %s'
YUM_INSTALL_TEMPLATE = 'sudo yum -y install %s'

# The version of gevent provided by Fedora/RHEL is too old, so force it to update here.
# It seems like setup.py needs to be run twice for now.
INSTALL_TEST_SUITE = 'git clone https://github.com/RedHatQE/pulp-automation.git && \
sudo pip install -U greenlet gevent requests stitches && \
cd pulp-automation && git checkout %s && sudo python ./setup.py install'

HOSTS_TEMPLATE = "echo '%(ip)s    %(hostname)s %(hostname)s.novalocal' | sudo tee -a /etc/hosts"


def configure_instances(global_config):
    """
    Configure the root instance and each decedent. Any configuration results are written to
    the given dictionary

    :param global_config: The instance structure dictionary from the configuration parser
    :type  global_config: dict
    """
    # This should eventually use multi-threading to configure independent machines concurrently
    for instance in config_generator(global_config):
        # Configure the instance
        config_function = CONFIGURATION_FUNCTIONS[instance[ROLE]]
        config_function(instance[INSTANCE_NAME], global_config)


def apply_puppet(host_string, key_file, local_module, remote_location=TEMPORARY_MANIFEST_LOCATION):
    """
    Apply a puppet manifest to the given host. It is your responsibility to install
    any puppet module dependencies, and to ensure puppet is installed.

    :param host_string:     The host to connect to: in the form 'user@host'
    :type  host_string:     str
    :param key_file:        The absolute path to the private key to use when connecting as 'user'
    :type  key_file:        str
    :param local_module:    The absolute path to the puppet module to put on the remote host
    :param remote_location: the location to put this puppet module on the remote host

    :raise SystemExit: if the applying the puppet module fails
    """
    with settings(host_string=host_string, key_filename=key_file, ok_ret_codes=[0, 2]):
        put(local_module, remote_location)
        run('sudo puppet apply --verbose --detailed-exitcodes ' + remote_location)
    fabric_network.disconnect_all()


def fabric_confirm_ssh_key(host_string, key_file):
    """
    This is a utility to make sure fabric can ssh into the host with the given key. This is useful
    when a remote host is being set up by cloud-init, which can bring the ssh server up before
    installing the public key. It will try for 300 seconds, after which it will raise a SystemExit.

    :param host_string:     The host to connect to: in the form 'user@host'
    :type  host_string:     str
    :param key_file:        The absolute path to the private key to use when connecting as 'user'
    :type  key_file:        str

    :raises SystemExit: if it was unable to ssh in after 300 seconds
    """
    # It can take some time for sshd to start and for cloud-init to insert the public key into an instance
    # This waits until ssh works
    print 'Waiting for ' + host_string + ' to become accessible via ssh...'
    with settings(host_string=host_string, key_filename=key_file):
        for x in xrange(0, 30):
            try:
                run('whoami', warn_only=True)
                break
            except (RuntimeError, NetworkError):
                time.sleep(10)
        else:
            run('whoami')


def add_external_fact(host_string, key_file, facts):
    """
    Make Puppet facts available to a remote host. Note that this will simply dump
    the file in /etc/facter/facts.d/facts.json which might overwrite other facts.

    :param host_string: remote host to add facts to; the expected format is 'user@ip'
    :param key_file: the absolute or relative path to the ssh key to use
    :param facts: a dictionary of facts; each key is a Puppet fact. The key
    names must follow the Puppet fact name rules.

    :raise SystemExit: if adding the external fact fails
    """
    with settings(host_string=host_string, key_filename=key_file):
        # Write the temporary json file to dump
        file_descriptor, path = tempfile.mkstemp()
        os.write(file_descriptor, json.dumps(facts))
        os.close(file_descriptor)

        # Place it on the remote host and clean up
        put(path)
        temp_filename = os.path.basename(path)
        run('sudo mkdir -p /etc/facter/facts.d/')
        run('sudo mv ' + temp_filename + ' /etc/facter/facts.d/facts.json')
        os.remove(path)


def configure_pulp_server(instance_name, global_config):
    """
    Set up a Pulp server using Fabric and a puppet module. Fabric will apply the given
    host name, ensure puppet and any modules declared in PUPPET_MODULES are installed,
    and will then apply the puppet manifest.

    :raise RuntimeError: if the server could not be successfully configured. This could be
    for any number of reasons. Currently fabric is set to be quite verbose, so see its output
    """
    config = get_instance_config(instance_name, global_config)
    host_string = config[HOST_STRING]
    private_key = config[PRIVATE_KEY]

    with settings(host_string=host_string, key_filename=private_key):
        # Confirm the server is available
        fabric_confirm_ssh_key(host_string, private_key)

        # Set the hostname
        run('sudo hostname ' + config[HOSTNAME])

        # Ensure the puppet modules are installed
        for module in PUPPET_MODULES:
            run(PUPPET_MODULE_INSTALL % module)

        # Add external facts to the server
        puppet_external_facts = {PULP_REPO_FACT: config[REPOSITORY_URL]}
        add_external_fact(host_string, private_key, puppet_external_facts)

        # Apply the manifest to the server
        apply_puppet(host_string, private_key, PULP_SERVER_MANIFEST)

        fabric_network.disconnect_all()


def configure_consumer(instance_name, global_config):
    """
    Set up a Pulp consumer using Fabric and a puppet module. Fabric will apply the given consumer
    hostname, ensure root can ssh into the consumer, ensure puppet and all modules in PUPPET_MODULES
    are installed, then apply the puppet manifest. Finally, it will write an /etc/hosts entry for the
    server

    :raise SystemExit: if the consumer could not be successfully configured. This could be
    for any number of reasons. Currently fabric is set to be quite verbose, so see its output
    """
    config = get_instance_config(instance_name, global_config)
    parent_config = get_parent_config(instance_name, global_config)

    with settings(host_string=config[HOST_STRING], key_filename=config[PRIVATE_KEY]):
        fabric_confirm_ssh_key(config[HOST_STRING], config[PRIVATE_KEY])

        # Set the hostname
        run('sudo hostname ' + config[HOSTNAME])

        # Ensure puppet modules are installed
        for module in PUPPET_MODULES:
            run(PUPPET_MODULE_INSTALL % module)

        # Add external facts to the consumer so it can find the server
        puppet_external_facts = {
            PULP_SERVER_FACT: parent_config[HOSTNAME],
            PULP_REPO_FACT: config[REPOSITORY_URL],
        }
        add_external_fact(config[HOST_STRING], config[PRIVATE_KEY], puppet_external_facts)

        apply_puppet(config[HOST_STRING], config[PRIVATE_KEY], PULP_CONSUMER_MANIFEST)

        # Write /etc/hosts
        server_ip = parent_config[HOST_STRING].split('@')[1]
        run(HOSTS_TEMPLATE % {'ip': server_ip, 'hostname':  parent_config[HOSTNAME]})
        fabric_network.disconnect_all()


def configure_tester(instance_name, global_config):
    """
    Set up the server that runs the integration tests. The basic steps performed are to clone
    the pulp-automation repository, run setup.py, ensure there are entries in /etc/hosts,
    place the ssh key on the tester so it can SSH into the consumer, and write the .yml file
    for the tests.

    :raise RuntimeError: if the tester could not be successfully configured. This could be
    for any number of reasons. Currently fabric is set to be quite verbose, so see its output.
    """
    config = get_instance_config(instance_name, global_config)
    flattened_configs = flatten_structure(global_config)
    server_config = filter(lambda conf: conf[ROLE] == PULP_SERVER_ROLE, flattened_configs)[0]
    consumer_config = filter(lambda conf: conf[ROLE] == PULP_CONSUMER_ROLE, flattened_configs)[0]

    with settings(host_string=config[HOST_STRING], key_filename=config[PRIVATE_KEY]):
        fabric_confirm_ssh_key(config[HOST_STRING], config[PRIVATE_KEY])

        run('sudo hostname ' + config[INSTANCE_NAME])

        # This is OS1 specific, but it's common for yum to not work without it
        run('echo "http_caching=packages" | sudo tee -a /etc/yum.conf')

        # Install necessary dependencies.
        print 'Installing necessary test dependencies... '
        with hide('stdout'):
            for dependency in PULP_AUTO_DEPS:
                run(YUM_INSTALL_TEMPLATE % dependency)

        # Install the test suite
        branch = config.get(TEST_SUITE_BRANCH, 'master')
        run(INSTALL_TEST_SUITE % branch)

        # Write to /etc/hosts
        server_ip = server_config[HOST_STRING].split('@')[1]
        consumer_ip = consumer_config[HOST_STRING].split('@')[1]
        run(HOSTS_TEMPLATE % {'ip': server_ip, 'hostname': server_config[HOSTNAME]})
        run(HOSTS_TEMPLATE % {'ip': consumer_ip, 'hostname': consumer_config[HOSTNAME]})

        # Generate a key pair so the test machine can ssh as root to the consumer
        local('ssh-keygen -f consumer_temp_rsa -N ""')
        with settings(host_string=consumer_config[HOST_STRING], key_filename=consumer_config[PRIVATE_KEY]):
            # Authorize the generated key for root access
            put('consumer_temp_rsa.pub', '~/authorized_keys')
            run('sudo cp ~/authorized_keys /root/.ssh/authorized_keys')

        # Put the private key on the test machine and clean up
        key_path = '/home/' + config[HOST_STRING].split('@')[0] + '/.ssh/id_rsa'
        key_path = key_path.encode('ascii')
        put('consumer_temp_rsa', key_path)
        run('chmod 0600 ' + key_path)
        local('rm consumer_temp_rsa consumer_temp_rsa.pub')

        # Write the YAML configuration file
        get('~/pulp-automation/tests/inventory.yml', 'template_inventory.yml')
        with open('template_inventory.yml', 'r') as template_config:
            config_yaml = yaml.load(template_config)

            # Write the server configuration
            server = {
                'url': 'https://' + server_config[HOSTNAME] + '/',
                'hostname': server_config[HOSTNAME],
                'verify_api_ssl': False,
            }
            server_yaml = dict(config_yaml[ROLES_KEY][SERVER_YAML_KEY].items() + server.items())
            config_yaml[ROLES_KEY][SERVER_YAML_KEY] = server_yaml

            # Write the qpid configuration
            config_yaml[ROLES_KEY]['qpid'] = {'url': server_config[HOSTNAME]}

            # Write the consumer configuration
            consumer = {
                'hostname': consumer_config[HOSTNAME],
                'ssh_key': key_path,
                'os': {'name': config['os_name'], 'version': config['os_version']},
                'pulp': server_yaml,
                'verify': False
            }
            consumer_yaml = dict(config_yaml[ROLES_KEY][CONSUMER_YAML_KEY][0].items() + consumer.items())
            config_yaml[ROLES_KEY][CONSUMER_YAML_KEY][0] = consumer_yaml

            with open('inventory.yml', 'w') as test_config:
                yaml.dump(config_yaml, test_config)

        # Place the config file on the server and clean up
        put('inventory.yml', '~/pulp-automation/inventory.yml')
        os.remove('inventory.yml')
        os.remove('template_inventory.yml')
        fabric_network.disconnect_all()


# This maps roles to setup functions
CONFIGURATION_FUNCTIONS = {
    PULP_SERVER_ROLE: configure_pulp_server,
    PULP_CONSUMER_ROLE: configure_consumer,
    PULP_TESTER_ROLE: configure_tester,
}
