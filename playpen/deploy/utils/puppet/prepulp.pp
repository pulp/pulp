# This manifest installs and configures Pulp's dependencies

class prepulp {
    include stdlib

    $base_packages = [
        'redhat-lsb',
        'java-1.7.0-openjdk-devel',
        'wget'
    ]
    package { $base_packages:
        ensure => 'installed'
    }

    if ($::operatingsystem == 'RedHat' or $::operatingsystem == 'CentOS')
        and $::lsbmajdistrelease == 5 {
        # Get the latest puppet verson from puppetlabs. This should pull in
        # the json ruby gem for facter to use.
        $el5_packages = [
            'git',
            'ruby-devel',
            'rubygems',
            'puppet',
            'pymongo',
            'python-qpid',
            'python-setuptools',
        ]

        exec { 'install puppet repo':
            command => '/bin/rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-5.noarch.rpm'
        } -> package { $el5_packages:
            ensure => 'installed'
        } -> exec { 'install pip':
            # This depends on the el5_packages because python-setuptools must be installed before this step
            command => '/usr/bin/curl -O https://pypi.python.org/packages/source/p/pip/pip-1.1.tar.gz && /bin/tar xfz pip-1.1.tar.gz && pushd pip-1.1 && /usr/bin/python setup.py install && popd && rm -rf pip-*'
        }
    } elsif ($::operatingsystem == 'RedHat' or $::operatingsystem == 'CentOS')
        and $::lsbmajdistrelease == 6 {
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

        exec { 'install puppet repo':
            command => '/bin/rpm -ivh http://yum.puppetlabs.com/puppetlabs-release-el-6.noarch.rpm'
        } -> package { $el6_packages:
            ensure => 'installed'
        } -> exec { 'gem install json':
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
            auth        => 'no'
        }
    }
}

include prepulp
