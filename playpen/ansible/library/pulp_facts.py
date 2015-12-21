#!/usr/bin/env python2
"""
This module gathers Pulp specific Ansible facts about the remote machine.
"""
import json
import os
import pwd
import subprocess


pipe = subprocess.Popen('/usr/bin/yum-config-manager pulp-nightlies', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
pulp_nightly_repo_enabled = 'enabled = True' in stdout

# Determine if selinux is Enforcing or not
pipe = subprocess.Popen('/usr/sbin/getenforce', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
selinux_enabled = 'Enforcing' in stdout

# Determine the list of RPM dependencies
projects = [
    'crane',
    'pulp',
    'pulp_deb',
    'pulp_docker',
    'pulp_openstack',
    'pulp_ostree',
    'pulp_puppet',
    'pulp_python',
    'pulp_rpm'
]
rpm_dependency_list = []
# This is run using sudo, but the code is checked out in the normal user directory.
user_homedir = pwd.getpwuid(int(os.environ['SUDO_UID'])).pw_dir
for project in projects:
    project_path = os.path.join(user_homedir, 'devel', project)
    if os.path.isdir(project_path):
        # Determine the dependencies by inspecting the 'Requires' in each spec file.
        # The results are then filtered to only include packages not provided by Pulp.
        rpmspec_command = r"rpmspec -q --queryformat '[%{REQUIRENEVRS}\n]' " + project_path + \
                          '/*.spec' + r'| grep -v "/.*" | grep -v "python-pulp.*" | ' \
                          r'grep -v "^pulp.*"'
        proc = subprocess.Popen(rpmspec_command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, shell=True)
        stdout, stderr = proc.communicate()
        rpm_dependency_list += [rpm.split()[0] for rpm in stdout.splitlines()]

# Remove any duplicates
rpm_dependency_list = list(set(rpm_dependency_list))

# Build the facts for Ansible
facts = {
    'ansible_facts': {
        'pulp_nightly_repo_enabled': pulp_nightly_repo_enabled,
        'selinux_enabled': selinux_enabled,
        'pulp_rpm_dependencies': rpm_dependency_list,
    }
}


# "return" the facts to Ansible
print json.dumps(facts)
