if [ $# -lt 2 ]; then
    echo "Usage: $0 ca_cert ent_cert"
    exit 1
fi
openssl verify -CAfile $1 $2

