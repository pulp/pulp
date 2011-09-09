if [ $# -lt 2 ]; then
    echo "Usage: $0 ca_cert cert"
    exit 1
fi
openssl verify -CAfile $1 $2

