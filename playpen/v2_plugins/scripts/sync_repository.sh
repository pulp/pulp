#!/bin/sh

export HOSTNAME=`hostname`
export USERNAME='admin'
export PASSWORD='admin'
export AUTH=`python -c "import base64; print base64.encodestring(\"admin:admin\")[:-1]"`


if [ $# -lt 1 ]; then
    echo "Usage: $0 REPO_ID"
    exit 1
fi
REPO_ID=$1

curl -s -k -H "Authorization: Basic $AUTH" -X POST https://${HOSTNAME}/pulp/api/v2/repositories/${REPO_ID}/actions/sync/ | python -mjson.tool

