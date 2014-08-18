# Call this class to install, configure, and start a pulp server.
# Customize configuration via parameters. For more information see
# the README.md

class pulp::server (
    $db_name                            = $pulp::server::params::db_name,
    $db_seed_list                       = $pulp::server::params::db_seed_list,
    $db_operation_retries               = $pulp::server::params::db_operation_retries,
    $db_username                        = $pulp::server::params::db_username,
    $db_password                        = $pulp::server::params::db_password,
    $db_replica_set                     = $pulp::server::params::db_replica_set,
    $server_name                        = $pulp::server::params::server_name,
    $server_key_url                     = $pulp::server::params::server_key_url,
    $server_ks_url                      = $pulp::server::params::server_ks_url,
    $default_login                      = $pulp::server::params::default_login,
    $default_password                   = $pulp::server::params::default_password,
    $debugging_mode                     = $pulp::server::params::debugging_mode,
    $log_level                          = $pulp::server::params::log_level,
    $auth_rsa_key                       = $pulp::server::params::auth_rsa_key,
    $auth_rsa_pub                       = $pulp::server::params::auth_rsa_pub,
    $cacert                             = $pulp::server::params::cacert,
    $cakey                              = $pulp::server::params::cakey,
    $ssl_ca_cert                        = $pulp::server::params::ssl_ca_cert,
    $user_cert_expiration               = $pulp::server::params::user_cert_expiration,
    $consumer_cert_expiration           = $pulp::server::params::consumer_cert_expiration,
    $serial_number_path                 = $pulp::server::params::serial_number_path,
    $consumer_history_lifetime          = $pulp::server::params::consumer_history_lifetime,
    $reaper_interval                    = $pulp::server::params::reaper_interval,
    $reap_archived_calls                = $pulp::server::params::reap_archived_calls,
    $reap_consumer_history              = $pulp::server::params::reap_consumer_history,
    $reap_repo_sync_history             = $pulp::server::params::reap_repo_sync_history,
    $reap_repo_publish_history          = $pulp::server::params::reap_repo_publish_history,
    $reap_repo_group_publish_history    = $pulp::server::params::reap_repo_group_publish_history,
    $reap_task_status_history           = $pulp::server::params::reap_task_status_history,
    $reap_task_result_history           = $pulp::server::params::reap_task_result_history,
    $msg_url                            = $pulp::server::params::msg_url,
    $msg_transport                      = $pulp::server::params::msg_transport,
    $msg_auth_enabled                   = $pulp::server::params::msg_auth_enabled,
    $msg_cacert                         = $pulp::server::params::msg_cacert,
    $msg_clientcert                     = $pulp::server::params::msg_clientcert,
    $msg_topic_exchange                 = $pulp::server::params::msg_topic_exchange,
    $tasks_broker_url                   = $pulp::server::params::tasks_broker_url,
    $celery_require_ssl                 = $pulp::server::params::celery_require_ssl,
    $tasks_cacert                       = $pulp::server::params::tasks_cacert,
    $tasks_keyfile                      = $pulp::server::params::tasks_keyfile,
    $tasks_certfile                     = $pulp::server::params::tasks_certfile,
    $email_host                         = $pulp::server::params::email_host,
    $email_port                         = $pulp::server::params::email_port,
    $email_from                         = $pulp::server::params::email_from,
    $email_enabled                      = $pulp::server::params::email_enabled,
    $enable_celerybeat                  = $pulp::server::params::enable_celerybeat,
    $enable_resource_manager            = $pulp::server::params::enable_resource_manager,
    $wsgi_processes                     = $pulp::server::params::wsgi_processes,
) inherits pulp::server::params {
    # Install, configure, and start the necessary services
    anchor { 'pulp::server::start': }->
    class { 'pulp::server::install': }->
    class { 'pulp::server::config': }->
    class { 'pulp::server::service': }->
    anchor { 'pulp::server::end': }
}

