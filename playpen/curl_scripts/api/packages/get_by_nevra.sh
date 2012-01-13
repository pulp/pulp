#!/bin/sh
export USERNAME='admin'
export PASSWORD='admin'

if [ $# -lt 5 ]; then
    echo "Usage: $0 Name Epoch Version Release Arch"
    exit 1
fi

if [ -n $1 ]; then
    NAME=$1
    echo "Will list package with name ${NAME}"
fi
if [ -n $2 ]; then
    EPOCH=$2
    echo "Will list package with epoch ${EPOCH}"
fi
if [ -n $3 ]; then
    VER=$3
    echo "Will list package with version ${VER}"
fi
if [ -n $4 ]; then
    REL=$4
    echo "Will list package with release ${REL}"
fi
if [ -n $5 ]; then
    ARCH=$5
    echo "Will list package with arch ${ARCH}"
fi


export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`

echo "curl -s -S -k -H \"Authorization: Basic $AUTH\" https://localhost/pulp/api/packages/${NAME}/${VER}/${REL}/${EPOCH}/${ARCH}/"
curl -s -S -k -H "Authorization: Basic $AUTH" https://localhost/pulp/api/packages/${NAME}/${VER}/${REL}/${EPOCH}/${ARCH}/ | python -mjson.tool
