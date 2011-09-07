TEMP_CA_CRL_FILE=./temp_CA_CRL.pem
if [ $# -lt 3 ]; then
    echo "Usage: $0 CA CRL revoked_cert"
    exit 1
fi

cat $1 $2 > ${TEMP_CA_CRL_FILE}
openssl verify -extended_crl -verbose -CAfile ${TEMP_CA_CRL_FILE} -crl_check $3
