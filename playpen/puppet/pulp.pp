class pulp_prereq {
  $os_downcase = downcase($::operatingsystem)
  
  if $::operatingsystem == 'Fedora' and $::operatingsystemrelease == 19 {
    $os_release = 18
  } else {
    $os_release = $::operatingsystemrelease
  }
  yumrepo {
    'pulp-v2-stable':
    name     =>'pulp-v2-stable',
    baseurl  =>"http://repos.fedorapeople.org/repos/pulp/pulp/v2/stable/\
${os_downcase}-${os_release}/${::architecture}/",
    enabled  =>1,
    gpgcheck =>0,
  }
  yumrepo {
    'pulp-v2-testing':
    name     =>'pulp-v2-testing',
    baseurl  =>"http://rsepos.fedorapeople.org/repos/pulp/pulp/v2/testing/\
${os_downcase}-${os_release}/${::architecture}/",
    enabled  =>0,
    gpgcheck =>0,
  }
  yumrepo {
    'pulp-v1-stable':
    name     =>'pulp-v1-stable',
    baseurl  =>"http://repos.fedorapeople.org/repos/pulp/pulp/v1/stable/\
${os_downcase}-${os_release}/${::architecture}/",
    enabled  =>0,
    gpgcheck =>0,
  }


  #packages needed for pulp server
  $base_packages = [
    'mongodb-server',
    'httpd',
    'qpid-cpp-server',
    'qpid-cpp-client',
    #'python-qpid',
    'qpid-cpp-client-ssl',
    'qpid-cpp-client-rdma']
  $pulp_server_packages = [
    #server section
    'python-pymongo',
    'python-setuptools',
    'python-webpy',
    'python-okaara',
    'python-oauth2', # >= 1.5.170-2.pulp
    'python-httplib2',
    'python-isodate', # >= 0.5.0-1.pulp
    'python-BeautifulSoup',
    'python-qpid',
    #'python-nectar', #nectar is installed as part of the build
    'mod_ssl',
    'openssl',
    'nss-tools',
    'python-ldap',
    'python-gofer',
    'crontabs',
    'acl',
    'mod_wsgi', # >= 3.4-1.pulp
    'mongodb',
    'm2crypto', # >= 0.21.1.pulp-7
    'genisoimage',
    # common section
    'python-iniparse',
    # agent section
    'gofer', #  >= 0.76
    # selinux
    'policycoreutils-python',
    'selinux-policy-targeted',
    #pulp_puppet
    'python-pycurl',
    #pulp_rpm
    'createrepo', # >= 0.9.9-21
    'python-rhsm', # >= 1.8.0
    'grinder', # >= 0.1.16
    'pyliblzma',
    'yum'
  ]

  $build_requires = [
    #pulp
    'rpm-python',
    'make',
    'checkpolicy',
    'selinux-policy-devel',
    'hardlink'
    #pulp_puppet
    #'python2-devel', # should maybe be python26-devel
    ]
  $list_to_flatten = [$base_packages,$build_requires,$pulp_server_packages]
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
  $testPackages = ['python-nose','python-coverage','python-mock']
  package { $testPackages:
      ensure => 'installed'
  }
}

include pulp_prereq
include pulp_test_prereq

