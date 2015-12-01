#!/usr/bin/env python2
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

# Determine if the fedora-23 repo is available yet
proc = subprocess.Popen(
    '/usr/bin/curl -s -f https://repos.fedorapeople.org/repos/pulp/pulp/beta/2.7/fedora-23/',
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
pulp_27_beta_f23_repo_available = (proc.wait() == 0)

# Determine if selinux is Enforcing or not
pipe = subprocess.Popen('/usr/sbin/getenforce', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
selinux_enabled = 'Enforcing' in stdout

# Build the facts for Ansible
facts = {
    'ansible_facts': {
        'pulp_27_beta_repo_enabled': pulp_27_beta_repo_enabled,
        'pulp_27_beta_f23_repo_available': pulp_27_beta_f23_repo_available,
        'selinux_enabled': selinux_enabled}}


# "return" the facts to Ansible
print json.dumps(facts)
