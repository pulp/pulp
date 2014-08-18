#!/usr/bin/python
import argparse

from fabric.api import settings, run

import os1_utils
import setup_utils


YUM_UPDATE_COMMAND = 'sudo  yum -y update'
DEPENDENCY_LIST = ['puppet']
PUPPET_MODULE_LIST = [
    'puppetlabs-stdlib',
    'puppetlabs-mongodb',
    'dprince-qpid',
    'jcline-pulp'
]

description = 'Update one or more pulp images'
os1_username_help = 'username on OS1; this is not necessary if using OS_USERNAME environment variable'
os1_password_help = 'password on OS1; this is not necessary if using OS_PASSWORD environment variable'
os1_tenant_id_help = 'tenant ID on OS1; this is not necessary if using OS_TENANT_ID environment variable'
os1_tenant_name_help = 'tenant name on OS1; this is not necessary if using OS_TENANT_NAME environment variable'
os1_auth_url_help = 'authentication URL on OS1; this is not necessary if using OS_AUTH_URL environment variable'

parser = argparse.ArgumentParser(description=description)
parser.add_argument('--key-file', help='the path to the private key of the OS1 key pair', required=True)
parser.add_argument('--os1-key', help='the name of the key pair in OS1 to use', required=True)
parser.add_argument('--puppet-manifest', help='path to a puppet puppet manifest to apply')
parser.add_argument('--os1-username', help=os1_username_help)
parser.add_argument('--os1-password', help=os1_password_help)
parser.add_argument('--os1-tenant-id', help=os1_tenant_id_help)
parser.add_argument('--os1-tenant-name', help=os1_tenant_name_help)
parser.add_argument('--os1-auth-url', help=os1_auth_url_help)
args = parser.parse_args()
# Boot, update, apply puppet module, reboot, snapshot, delete instances, apply metadata, remove old image
# TODO remove logs

os1 = os1_utils.OS1Manager(args.os1_username, args.os1_password, args.os1_tenant_id,
                           args.os1_tenant_name, args.os1_auth_url)

pulp_images = os1.get_pulp_images()
instance_list = []
for image in pulp_images:

    instance = os1.create_instance(image, image.name, os1_utils.DEFAULT_SEC_GROUP,
                                   os1_utils.DEFAULT_FLAVOR, args.os1_key)
    instance_list.append(instance)

os1.wait_for_active_instances(instance_list)


def update(instance):
    host_string = os1.get_instance_user(instance) + '@' + os1.get_instance_ip(instance)

    with settings(host_string=host_string, key_file=args.key_file):
        run(YUM_UPDATE_COMMAND)

        for package in DEPENDENCY_LIST:
            run('sudo yum -y install ' + package)

        for module in PUPPET_MODULE_LIST:
            run('sudo puppet module install --force ' + module)

    if args.puppet_manifest:
        setup_utils.apply_puppet(host_string, args.key_file, args.puppet_manifest)

    os1.reboot_instance(instance)

    snapshot = os1.take_snapshot(instance, image.name)

    msg = "Review the new image [%s] before removing the old image [%s]" % snapshot.id, image.id
    return snapshot, msg

snapshot_list = []
msg_list = []
for instance in instance_list:
    snapshot, msg = update(instance)
    msg_list.append(msg)
    snapshot_list.append(snapshot)

os1.wait_for_snapshots(snapshot_list)

for instance in instance_list:
    os1.delete_instance(instance)
