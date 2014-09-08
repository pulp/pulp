# This class installs and configures a Pulp server the repository specified
# by the pulp_repo fact. This fact is retrieved from the FACTER_PULP_REPO
# environment variable

class pulp_server {
    include stdlib

    augeas { "yum.conf":
        changes => "set /files/etc/yum.conf/main/http_caching packages",
    } -> service { 'iptables':
        enable => false,
        ensure => 'stopped'
    } -> service { 'mongod':
        enable => true,
        ensure => 'running'
    } -> service { 'qpidd':
        enable => true,
        ensure => 'running'
    } -> class {'::pulp::globals':
        repo_baseurl => $::pulp_repo
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
