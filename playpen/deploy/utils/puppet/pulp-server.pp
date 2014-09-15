# This class installs and configures a Pulp server the repository specified
# by the pulp_repo fact. This fact is retrieved from the FACTER_PULP_REPO
# environment variable

class pulp_server {
    include stdlib

    $qpid_packages = [
        'python-qpid-qmf',
        'qpid-cpp-server-store'
    ]

    # The Pulp repo provides qpid for RHEL6, so we have to install it now
    augeas { "yum.conf":
        changes => "set /files/etc/yum.conf/main/http_caching packages",
    } -> service { 'iptables':
        enable => false,
        ensure => 'stopped'
    } -> service { 'mongod':
        enable => true,
        ensure => 'running'
    } -> class {'::pulp::globals':
        repo_baseurl => $::pulp_repo
    } -> package {$qpid_packages:
        ensure => present
    } -> class {'::qpid::server':
        # Because (on RHEL6) we provide qpid, we have to make sure it's installed
        # after the pulp repository is added.
        config_file => '/etc/qpid/qpidd.conf',
        auth        => 'no'
    } -> class {'::pulp::server':
        wsgi_processes => 1,
        node_parent   => true,
        oauth_enabled  => true,
        oauth_key      => 'key',
        oauth_secret   => 'secret',
    } -> exec { "http-restart":
        command => "/sbin/service httpd restart"
    }
}

include pulp_server
