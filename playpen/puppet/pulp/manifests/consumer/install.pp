# This is a private class that should not be called directly.
# Use pulp::consumer instead.

class pulp::consumer::install {
    # Not elegant, but Puppet doesn't support yum groups
    exec {
        "yum install pulp-consumer":
        command => '/usr/bin/yum -y groupinstall "Pulp Consumer"',
        unless  => '/usr/bin/yum grouplist "Pulp Consumer" | /bin/grep "^Installed groups"',                         
        timeout => 600
    }
}
