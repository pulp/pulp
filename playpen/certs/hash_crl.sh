if [ $# -lt 1 ]; then
    echo "Usage: $0 CRL_path"
    exit 1
fi
openssl crl -in $1 -noout -hash

