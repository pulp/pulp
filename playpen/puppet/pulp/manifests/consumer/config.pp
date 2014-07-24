# This is a private class and should be be called directly. Use pulp::consumer instead

class pulp::consumer::config {
    # Write consumer.conf file
    file { '/etc/pulp/consumer/consumer.conf':
        content => template('pulp/consumer.conf.erb'),
        owner   => 'root',
        group   => 'root',
        mode    => '0644'
    }

    # Add the Pulp server's CA cert to the system trusted CA certs
    file { '/etc/pki/tls/certs/pulp.crt':
        content => $pulp_server_ca_cert,
        owner   => 'root',
        group   => 'root',
        mode    => '0644'
    } -> exec { "Trust server CA certificate":
        path    => "/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/bin:/sbin",
        # TODO Make sure we're not overwriting a cert (which would be quite bad)
        command => "mv /etc/pki/tls/certs/pulp.crt /etc/pki/tls/certs/`openssl x509 -noout -hash -in /etc/pki/tls/certs/pulp.crt`.0"
    }
}
