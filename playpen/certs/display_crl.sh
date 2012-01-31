if [ $# -lt 1 ]; then
    echo "Usage: $0 crl"
    exit 1
fi
openssl crl -text -in $1 -noout
