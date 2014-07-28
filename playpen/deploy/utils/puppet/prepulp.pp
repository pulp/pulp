# This manifest installs and configures Pulp's dependencies

class prepulp {
    include stdlib

    $packages = [
        'gcc',
        'git',
        'm2crypto',
        'python-devel',
        'python-pip',
        'python-qpid',
        'python-qpid-qmf',
        'qpid-cpp-server-store',
        'redhat-lsb',
    ]

    package { $packages:
        ensure => 'installed'
    }

    class {'::mongodb::server':
        smallfiles => true,
        noprealloc => true,
    }

    class {'::qpid::server':
        config_file => '/etc/qpid/qpidd.conf',
        auth => 'no'
    }
}

include prepulp
