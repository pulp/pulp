
class pulp::server::config {
    # Write server.conf file
    file { '/etc/pulp/server.conf':
        content => template('pulp/server.conf.erb'),
        owner   => 'root',
        group   => 'apache',
        mode    => '0644'
    } -> exec { "Migrate DB":
        command => "/usr/bin/pulp-manage-db",
        user    => "apache"
    }

    # Configure Apache
    if $wsgi_processes {
        augeas { "WSGI processes":
            changes => "set /files/etc/httpd/conf.d/pulp.conf/*[self::directive='WSGIDaemonProcess']/arg[4] processes=$wsgi_processes",
        }
    }
}
