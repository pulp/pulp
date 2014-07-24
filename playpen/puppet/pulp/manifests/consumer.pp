# Call this class to install, configure, and start a pulp consumer.
# Customize configuration via parameters. For more information see
# the README.md

class pulp::consumer (
    $pulp_server_ca_cert        = $pulp::consumer::params::pulp_server_ca_cert,
    $pulp_server                = $pulp::consumer::params::pulp_server,
    $pulp_port                  = $pulp::consumer::params::pulp_port,
    $pulp_api_prefix            = $pulp::consumer::params::pulp_api_prefix,
    $pulp_rsa_pub               = $pulp::consumer::params::pulp_rsa_pub,
    $consumer_rsa_key           = $pulp::consumer::params::consumer_rsa_key,
    $consumer_rsa_pub           = $pulp::consumer::params::consumer_rsa_pub,
    $consumer_client_role       = $pulp::consumer::params::consumer_client_role,
    $consumer_extensions_dir    = $pulp::consumer::params::consumer_extensions_dir,
    $consumer_repo_file         = $pulp::consumer::params::consumer_repo_file,
    $consumer_mirror_list_dir   = $pulp::consumer::params::consumer_mirror_list_dir,
    $consumer_gpg_keys_dir      = $pulp::consumer::params::consumer_gpg_keys_dir,
    $consumer_cert_dir          = $pulp::consumer::params::consumer_cert_dir,
    $consumer_id_cert_dir       = $pulp::consumer::params::consumer_id_cert_dir,
    $consumer_id_cert_filename  = $pulp::consumer::params::consumer_id_cert_filename,
    $consumer_reboot            = $pulp::consumer::params::consumer_reboot,
    $consumer_reboot_delay      = $pulp::consumer::params::consumer_reboot_delay,
    $consumer_log_filename      = $pulp::consumer::params::consumer_log_filename,
    $consumer_call_log_filename = $pulp::consumer::params::consumer_call_log_filename,
    $consumer_poll_freq         = $pulp::consumer::params::consumer_poll_freq,
    $consumer_color_output      = $pulp::consumer::params::consumer_color_output,
    $consumer_wrap_terminal     = $pulp::consumer::params::consumer_wrap_width,
    $consumer_wrap_width        = $pulp::consumer::params::consumer_wrap_width,
    $consumer_msg_scheme        = $pulp::consumer::params::consumer_msg_scheme,
    $consumer_msg_host          = $pulp::consumer::params::consumer_msg_host,
    $consumer_msg_port          = $pulp::consumer::params::consumer_msg_port,
    $consumer_msg_transport     = $pulp::consumer::params::consumer_msg_transport,
    $consumer_msg_cacert        = $pulp::consumer::params::consumer_msg_cacert,
    $consumer_msg_clientcert    = $pulp::consumer::params::consumer_msg_clientcert,
    $consumer_profile_minutes   = $pulp::consumer::params::consumer_profile_minutes,
) inherits pulp::consumer::params {
    # Install, configure, and start the necessary services
    anchor { 'pulp::consumer::start': } ->
    class { 'pulp::consumer::install': } ->
    class { 'pulp::consumer::config': } ->
    class { 'pulp::consumer::service': } ->
    anchor { 'pulp::consumer::end': }
}

