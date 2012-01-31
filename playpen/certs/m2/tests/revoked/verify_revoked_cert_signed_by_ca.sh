export CERT_DIR=./certs
export CA_CERT=${CERT_DIR}/revoking_ca.pem
export REVOKED_CERT=${CERT_DIR}/revoked_cert.pem
if [ $# -lt 2 ]; then
    echo "Usage: $0 ${CA_CERT} ${REVOKED_CERT}"
else
    export CA_CERT=$1
    export REVOKED_CERT=$2
fi
openssl verify -CAfile ${CA_CERT} ${REVOKED_CERT}

