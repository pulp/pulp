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


class pulp_prereq {

  if $::operatingsystem == "RedHat" {
    $major_release_num = regsubst("${::operatingsystemrelease}", '^(\d+)\.(\d+)', '\1')
    $os_pathname = "${major_release_num}Server"
  }
  elsif $::operatingsystem == "Fedora" {
    $os_pathname = "downcase($::operatingsystem)-${::operatingsystemrelease}"
  }

  if ($::operatingsystem == 'RedHat' and $::operatingsystemrelease <= 6) or
      ($::operatingsystem == 'Fedora' and $::operatingsystemrelease <= 19) {
    yumrepo { "pulp-stable":
      name     => "pulp-stable",
      baseurl  => "http://repos.fedorapeople.org/repos/pulp/pulp/stable/latest/\
$os_pathname/${::architecture}/",
      enabled  => 1,
      gpgcheck => 0,
    }
  }

  yumrepo { "pulp-2.4-beta":
    name     => "pulp-2.4-beta",
    baseurl  => "http://repos.fedorapeople.org/repos/pulp/pulp/beta/2.4/\
$os_pathname/${::architecture}/",
    enabled  => 1,
    gpgcheck => 0,
  }

  yumrepo { "pulp-testing":
    name     => "pulp-testing",
    baseurl  => "http://repos.fedorapeople.org/repos/pulp/pulp/testing/\
$os_pathname/${::architecture}/",
    enabled  => 1,
    gpgcheck => 0,
  }

  #packages needed for pulp server
  $base_packages = [
    'httpd',
    'mongodb-server',
    'qpid-cpp-server',
    'qpid-cpp-client',
    'qpid-cpp-client-ssl',
    'qpid-cpp-client-rdma']

  $pulp_server_packages = [
    'acl',
    'createrepo', # >= 0.9.9-21
    'crontabs',
    'genisoimage',
    'gofer', #  >= 0.76
    'm2crypto', # >= 0.21.1.pulp-7
    'mod_ssl',
    'mod_wsgi', # >= 3.4-1.pulp
    'mongodb',
    'nss-tools',
    'openssl',
    'policycoreutils-python',
    'pyliblzma',
    'python-celery',
    'python-isodate', # >= 0.5.0-1.pulp
    'python-iniparse',
    'python-gofer',
    'python-httplib2',
    'python-ldap',
    'python-oauth2', # >= 1.5.170-2.pulp
    'python-okaara',
    'python-pycurl',
    'python-pymongo',
    'python-qpid',
    'python-rhsm', # >= 1.8.0
    'python-semantic-version',
    'python-setuptools',
    'python-webpy',
    'selinux-policy-targeted',
    'yum'
  ]

  $build_requires = [
    'checkpolicy',
    'hardlink',
    'make',
    'redhat-lsb',
    'rpm-python',
    'selinux-policy-devel'
    ]

  # These are things that are nice to have
  $extras = [
    'vim',
    ]

  $list_to_flatten = [$base_packages,$build_requires,$extras,$pulp_server_packages]
  $package_list = flatten($list_to_flatten)
  #only install if RHEL 6
  $pulp_rhel_packages = ['nss']
  if $::operatingsystem == 'RedHat' and $::operatingsystemrelease == 6 {
    $package_list = concat($package_list,$pulp_rhel_packages)
  }

  package { $package_list:
      ensure => 'installed'
  }

  #setup the base services for the server
  service {
    'mongod':
    ensure => 'running',
    enable => true
  }

  #set the servername to localhost so apache doesn't complain
  service {
    'httpd':
    ensure => 'running',
    enable => true
  }
  service {
    'qpidd':
    ensure => 'running',
    enable => true
  }
  #disable SELinux, still requires a reboot to take effect
  augeas { 'selinux_disable':
      changes => ['set /files/etc/selinux/config/SELINUX disabled']
  }
}


class pulp_test_prereq {
  #packages needed to run unit tests
  $testPackages = ['python-nose','python-coverage','python-mock','git','python-pip','gcc','python-devel','python-paste']
  package { $testPackages:
      ensure => 'installed'
  }

  exec { "pip install":
    command => "pip install nosexcover",
    path    => "/usr/local/bin/:/bin/",
  }
}


include pulp_prereq
include pulp_test_prereq

