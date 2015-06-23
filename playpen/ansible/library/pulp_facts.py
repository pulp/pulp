#!/usr/bin/python
"""
This module gathers Pulp specific Ansible facts about the remote machine.
"""

import json
import subprocess


# Determine if the pulp-2.7-beta repository is enabled or not
pipe = subprocess.Popen('/usr/bin/yum-config-manager pulp-2.7-beta', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
pulp_27_beta_repo_enabled = 'enabled = True' in stdout

# Determine if selinux is Enforcing or not
pipe = subprocess.Popen('/usr/sbin/getenforce', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
selinux_enabled = 'Enforcing' in stdout


# Build the facts for Ansible
facts = {
    'ansible_facts': {
        'pulp_27_beta_repo_enabled': pulp_27_beta_repo_enabled,
        'selinux_enabled': selinux_enabled}}


# "return" the facts to Ansible
print json.dumps(facts)
