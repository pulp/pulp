if [ $# -lt 1 ]; then
    echo "Usage: $0 CRL_path"
    exit 1
fi
ln -s $1 `openssl crl -hash -noout -in $1`.r0

