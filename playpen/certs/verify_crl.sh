if [ $# -lt 2 ]; then
    echo "Usage: $0 CRL_path CACERT_path"
    exit 1
fi
openssl crl -in $1 -CAfile $2 -noout
