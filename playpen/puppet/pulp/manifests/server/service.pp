# This is a private class that should never be called directly

class pulp::server::service {

    service { 'httpd':
        enable => 'true',
        ensure => 'running'
    }
    service { 'pulp_workers':
        enable => 'true',
        ensure => 'running'
    }

    if $pulp::server::enable_celerybeat  == true {
        service { 'pulp_celerybeat':
            enable => 'true',
            ensure => 'running'
        }
    } else {
        service { 'pulp_celerybeat':
            enable => 'false',
            ensure => 'stopped'
        }
    }

    if $pulp::server::enable_resource_manager == true {
        service { 'pulp_resource_manager':
            enable => 'true',
            ensure => 'running'
        }
    } else {
        service { 'pulp_resource_manager':
            enable => 'false',
            ensure => 'stopped'
        }
    }
}
