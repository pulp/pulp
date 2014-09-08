# This manifest installs and configures Pulp's dependencies

class prepulp {
    include stdlib
    
    package { 'redhat-lsb':
        ensure => 'installed'
    }

    if $::operatingsystem == 'RedHat' and $::lsbmajdistrelease == 5 {
        # Get the latest puppet verson from puppetlabs. This should pull in
        # the json ruby gem for facter to use.
        $el5_packages = [
            'ruby-devel',
            'rubygems',
            'puppet',
        ]

        exec { "install puppet repo":
            command => '/bin/rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-5.noarch.rpm'
        } -> package { $el5_packages:
            ensure => 'installed'
        }
    } elsif $::operatingsystem == 'RedHat' and $::lsbmajdistrelease == 6 {
        # Qpid is provided by Pulp, so don't install it right now. Also update
        # to the latest Puppet version from puppetlabs
        $el6_packages = [
            'gcc',
            'git',
            'python-devel',
            'ruby-devel',
            'rubygems',
            'puppet',
            'python-pip',
        ]

        exec { "install puppet repo":
            command => '/bin/rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-6.noarch.rpm'
        } -> package { $el6_packages:
            ensure => 'installed'
        } -> exec { "gem install json":
            command => '/usr/bin/gem install json'
        }

        class {'::mongodb::server':}
    } else {
        $packages_qpid = [
            'gcc',
            'git',
            'python-devel',
            'python-pip',
            'python-qpid',
            'python-qpid-qmf',
            'qpid-cpp-server-store',
        ]

        package { $packages_qpid:
            ensure => 'installed'
        }

        class {'::mongodb::server':}

        class {'::qpid::server':
            config_file => '/etc/qpid/qpidd.conf',
            auth => 'no'
        }
    }
}

include prepulp
