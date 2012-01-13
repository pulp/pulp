#!/bin/sh
export USERNAME='admin'
export PASSWORD='admin'

if [ $# -lt 1 ]; then
    echo "Usage: $0 Package ID"
    exit 1
fi

if [ -n $1 ]; then
    PKG_ID=$1
    echo "Will list package with id ${PKG_ID}"
fi

export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`

curl -s -S -k -H "Authorization: Basic $AUTH" -X DELETE https://localhost/pulp/api/packages/${PKG_ID}/ | python -mjson.tool
