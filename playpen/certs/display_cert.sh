if [ $# -lt 1 ]; then
    echo "Usage: $0 certificate"
    exit 1
fi
openssl x509 -purpose -text -in $1 -noout -fingerprint

