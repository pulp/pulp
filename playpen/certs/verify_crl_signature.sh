if [ $# -lt 2 ]; then
    echo "Usage: $0 CRL_path revoked_cert"
    exit 1
fi
openssl verify -CAfile $1 -crl_check $2
