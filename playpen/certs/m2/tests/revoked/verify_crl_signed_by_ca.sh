export CERT_DIR=./certs
export CA_CERT=${CERT_DIR}/revoking_ca.pem
export CRL_FILE=${CERT_DIR}/revoking_crl.pem

if [ $# -lt 2 ]; then
    echo "Usage: $0 ${CRL_FILE} ${CA_CERT}"
else
    CRL_FILE=$1
    CA_CERT=$2
fi
openssl crl -in ${CRL_FILE} -CAfile ${CA_CERT} -noout
