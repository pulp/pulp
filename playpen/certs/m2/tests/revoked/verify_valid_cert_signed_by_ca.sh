export CERT_DIR=./certs
export CA_CERT=${CERT_DIR}/revoking_ca.pem
export VALID_CERT=${CERT_DIR}/valid_cert.pem
if [ $# -lt 2 ]; then
    echo "Usage: $0 ${CA_CERT} ${VALID_CERT}"
else
    export CA_CERT=$1
    export VALID_CERT=$2
fi
openssl verify -CAfile ${CA_CERT} ${VALID_CERT}

