# This class installs a Pulp consumer from the latest scratch build

class pulp_consumer {
    include stdlib

    class {'::pulp::globals':
        repo_descr   => 'Pulp Repository',
        repo_baseurl => $::pulp_repo
    } -> class {'::pulp::consumer':
        verify_ssl => 'False',
    }
}

include pulp_consumer
