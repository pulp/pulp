#!/us/bin/python
import argparse

import os1_utils
from playpen.deploy.common import setup_utils


DEPENDENCY_LIST = ['puppet']
PUPPET_MODULE_LIST = [
    'puppetlabs-stdlib',
    'puppetlabs-mongodb',
    'dprince-qpid',
    'jcline-pulp'
]

description = 'Update all Pulp images'
os1_username_help = 'username on OS1; this is not necessary if using OS_USERNAME environment variable'
os1_password_help = 'password on OS1; this is not necessary if using OS_PASSWORD environment variable'
os1_tenant_id_help = 'tenant ID on OS1; this is not necessary if using OS_TENANT_ID environment variable'
os1_tenant_name_help = 'tenant name on OS1; this is not necessary if using OS_TENANT_NAME environment variable'
os1_auth_url_help = 'authentication URL on OS1; this is not necessary if using OS_AUTH_URL environment variable'

parser = argparse.ArgumentParser(description=description)
parser.add_argument('--key-file', help='the path to the private key of the OS1 key pair', required=True)
parser.add_argument('--os1-key', help='the name of the key pair in OS1 to use', required=True)
parser.add_argument('--puppet-manifest', help='path to a puppet puppet manifest to apply')
parser.add_argument('--security-group', default='pulp', help='security group to apply in OS1')
parser.add_argument('--flavor', default='m1.medium', help='instance flavor to use')
parser.add_argument('--os1-username', help=os1_username_help)
parser.add_argument('--os1-password', help=os1_password_help)
parser.add_argument('--os1-tenant-id', help=os1_tenant_id_help)
parser.add_argument('--os1-tenant-name', help=os1_tenant_name_help)
parser.add_argument('--os1-auth-url', help=os1_auth_url_help)
arguments = parser.parse_args()

glance, keystone, nova = os1_utils.authenticate()

pulp_images = os1_utils.get_pulp_images(nova)
for image in pulp_images:
    # Boot, update, apply puppet module, reboot, snapshot, delete instances, apply metadata, remove old image
    # TODO remove logs
    instance = os1_utils.create_instance(nova, image, image.name, os1_utils.DEFAULT_SEC_GROUP,
                                         os1_utils.DEFAULT_FLAVOR, arguments.key_name)

    host_string = image.metadata['user'] + '@' + os1_utils.get_instance_ip(instance)
    setup_utils.yum_update(host_string, arguments.key_file)
    setup_utils.yum_install(host_string, arguments.key_file, DEPENDENCY_LIST)
    setup_utils.install_puppet_modules(host_string, arguments.key_file, PUPPET_MODULE_LIST)
    if arguments.puppet_manifest:
        setup_utils.apply_puppet(host_string, arguments.key_file, arguments.puppet_manifest)

    os1_utils.reboot_instance(nova, instance)

    snapshot = os1_utils.take_snapshot(nova, instance, image.name)
    instance.delete()

    msg = "Review the new image [%s] before removing the old image [%s]" % snapshot.id, image.id
    print msg
