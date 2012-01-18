export CERT_DIR=./certs
export REVOKED_CERT=${CERT_DIR}/revoked_cert.pem
export CA_CERT=${CERT_DIR}/revoking_ca.pem
export CRL_FILE=${CERT_DIR}/revoking_crl.pem
export TEMP_CA_CRL_FILE=${CERT_DIR}/temp_CA_CRL.pem
if [ $# -lt 3 ]; then
    echo "Usage: $0 ${CA_CERT} ${CRL_FILE} ${REVOKED_CERT}"
else
    export CA_CERT=$1
    export CRL_FILE=$2
    export REVOKED_CERT=$3
fi

cat ${CA_CERT} ${CRL_FILE} > ${TEMP_CA_CRL_FILE}
openssl verify -extended_crl -verbose -CAfile ${TEMP_CA_CRL_FILE} -crl_check ${REVOKED_CERT}
