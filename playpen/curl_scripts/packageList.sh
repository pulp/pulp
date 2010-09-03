#!/bin/sh
export USERNAME='admin'
export PASSWORD='admin'

if [ $# -lt 1 ]; then
    echo "Usage: $0 REPO"
    exit 1
fi

if [ -n $1 ]; then
    REPO=$1
    echo "Will list package groups from repo ${REPO}"
fi

export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`

curl -k -H "Authorization: Basic $AUTH" https://localhost/pulp/api/repositories/${REPO}/packages/
