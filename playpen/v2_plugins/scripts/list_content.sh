#!/bin/sh

export HOSTNAME=`hostname`
export USERNAME='admin'
export PASSWORD='admin'
export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`


if [ $# -lt 1 ]; then
    echo "Usage: $0 CONTENT_TYPE"
    exit 1
fi
CONTENT_TYPE=$1

curl -s -k -H "Authorization: Basic $AUTH" https://${HOSTNAME}/pulp/api/v2/content/${CONTENT_TYPE}/units/ | python -mjson.tool

