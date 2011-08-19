if [ $# -lt 3 ]; then
    echo "Usage: $0 CA CRL revoked_cert"
    exit 1
fi

cat $1 $2 > ./certs/CA_CRL.pem
openssl verify -extended_crl -verbose -CAfile ./certs/CA_CRL.pem -crl_check $3
